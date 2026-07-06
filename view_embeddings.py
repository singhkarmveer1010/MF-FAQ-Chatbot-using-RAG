#!/usr/bin/env python3
"""
View Embeddings Utility Script for Mutual Fund FAQ Assistant.

This script allows users to view, inspect, and verify embeddings for text chunks.
It can retrieve existing indexed embeddings directly from the local ChromaDB vector store
or generate them on-the-fly for any processed chunk JSON file (e.g., data/processed/9_chunks.json)
using the BGE-small-en-v1.5 embedding model.
"""

import argparse
import json
import logging
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path for clean imports
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.settings import VECTOR_STORE_PATH, EMBEDDING_MODEL
from src.ingestion.embedder import (
    DEFAULT_COLLECTION_NAME,
    get_embedding_model,
    get_vector_store_client,
    generate_embeddings,
    load_all_processed_chunks,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("view_embeddings")

# Default: if no file specified, we load all processed chunks across all schemes


def calculate_l2_norm(vector: List[float]) -> float:
    """Calculate the L2 norm (Euclidean norm) of a vector."""
    if not vector:
        return 0.0
    return math.sqrt(sum(x * x for x in vector))


def format_vector_preview(vector: List[float], full: bool = False, head: int = 6, tail: int = 2) -> str:
    """Format an embedding vector for clean display."""
    if not vector:
        return "[]"
    if full or len(vector) <= (head + tail):
        return "[" + ", ".join(f"{x: .4f}" for x in vector) + "]"
    
    head_str = ", ".join(f"{x: .4f}" for x in vector[:head])
    tail_str = ", ".join(f"{x: .4f}" for x in vector[-tail:])
    return f"[{head_str}, ..., {tail_str}]"


def get_embeddings_from_chroma(
    chunk_ids: List[str],
    collection_name: str = DEFAULT_COLLECTION_NAME,
    persist_dir: str | Path = VECTOR_STORE_PATH,
) -> Dict[str, List[float]]:
    """Retrieve existing embeddings from ChromaDB by chunk IDs."""
    client = get_vector_store_client(persist_directory=persist_dir)
    try:
        collection = client.get_collection(name=collection_name)
    except Exception as e:
        logger.debug(f"Could not connect to ChromaDB collection '{collection_name}': {e}")
        return {}

    try:
        res = collection.get(ids=chunk_ids, include=["embeddings"])
        ids = res.get("ids", [])
        embs = res.get("embeddings", [])
        if embs is None:
            return {}
        
        id_to_emb = {}
        for i, cid in enumerate(ids):
            if i < len(embs) and embs[i] is not None:
                # Convert numpy array / list to standard python list of floats
                id_to_emb[cid] = [float(x) for x in embs[i]]
        return id_to_emb
    except Exception as e:
        logger.warning(f"Error querying ChromaDB for embeddings: {e}")
        return {}


def load_chunks_to_view(
    file_path: Optional[str | Path] = None,
    chunk_id: Optional[str] = None,
    scheme_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Load chunks from a specific JSON file or all processed JSON files."""
    chunks = []
    
    if file_path:
        p = Path(file_path)
        if not p.exists():
            logger.error(f"Specified file not found: {p}")
            return []
        logger.info(f"Loading chunks from file: {p}")
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    chunks = data
                else:
                    logger.error(f"Expected a JSON array in {p}, got {type(data).__name__}")
        except Exception as e:
            logger.error(f"Error reading {p}: {e}")
            return []
    else:
        logger.info("No file specified. Loading all processed chunks across all schemes...")
        chunks = load_all_processed_chunks()

    # Filter by chunk_id if specified
    if chunk_id:
        chunks = [c for c in chunks if str(c.get("chunk_id")) == chunk_id]
        if not chunks:
            logger.warning(f"No chunk found with chunk_id: '{chunk_id}'")

    # Filter by scheme name if specified
    if scheme_filter:
        scheme_lower = scheme_filter.lower()
        chunks = [
            c for c in chunks 
            if scheme_lower in str(c.get("scheme_name", "")).lower() or scheme_lower in str(c.get("category", "")).lower()
        ]
        if not chunks:
            logger.warning(f"No chunks matching scheme/category filter: '{scheme_filter}'")

    return chunks


def display_embeddings(
    chunks: List[Dict[str, Any]],
    source_mode: str = "auto",
    limit: int = 5,
    show_full: bool = False,
    output_file: Optional[str | Path] = None,
):
    """Fetch/compute embeddings for chunks and display formatted summaries."""
    if not chunks:
        print("\n[!] No chunks available to view.")
        return

    display_chunks = chunks[:limit] if limit > 0 else chunks
    chunk_ids = [str(c.get("chunk_id", f"chunk_{i}")) for i, c in enumerate(display_chunks)]
    
    embeddings_map: Dict[str, List[float]] = {}
    
    # 1. Try fetching from ChromaDB if requested or in auto mode
    if source_mode in ("auto", "chromadb"):
        logger.info(f"Checking ChromaDB collection '{DEFAULT_COLLECTION_NAME}' for existing embeddings...")
        embeddings_map = get_embeddings_from_chroma(chunk_ids)
        logger.info(f"Found {len(embeddings_map)}/{len(chunk_ids)} embeddings in ChromaDB.")
        
        if source_mode == "chromadb" and len(embeddings_map) < len(chunk_ids):
            logger.warning("Some chunks were not found in ChromaDB. Use --source auto or --source model to generate them on-the-fly.")

    # 2. Generate missing embeddings using BGE model if needed
    missing_chunks = [c for c in display_chunks if str(c.get("chunk_id")) not in embeddings_map]
    if missing_chunks and source_mode in ("auto", "model"):
        logger.info(f"Generating embeddings on-the-fly for {len(missing_chunks)} chunks using '{EMBEDDING_MODEL}'...")
        model = get_embedding_model(model_name=EMBEDDING_MODEL)
        generated_embs = generate_embeddings(missing_chunks, model=model)
        for c, emb in zip(missing_chunks, generated_embs):
            embeddings_map[str(c.get("chunk_id"))] = emb

    # Display Output
    print("\n" + "=" * 80)
    print(f"=== EMBEDDING VIEWER (Showing {len(display_chunks)} of {len(chunks)} matching chunks) ===")
    print("=" * 80)

    export_data = []

    for idx, c in enumerate(display_chunks, 1):
        cid = str(c.get("chunk_id", "N/A"))
        scheme = c.get("scheme_name", "Unknown Scheme")
        category = c.get("category", "Unknown Category")
        c_index = c.get("chunk_index", "N/A")
        text = str(c.get("text", ""))
        snippet = (text[:140] + "...") if len(text) > 140 else text
        snippet_clean = snippet.replace("\n", " ")

        emb = embeddings_map.get(cid, [])
        dim = len(emb)
        norm = calculate_l2_norm(emb)
        status = "CHROMA_STORED" if source_mode == "chromadb" or (source_mode == "auto" and cid in get_embeddings_from_chroma([cid])) else "MODEL_GENERATED"
        if not emb:
            status = "NOT_FOUND"

        print(f"\n[{idx}] Chunk ID: {cid}")
        print(f"    Scheme:   {scheme} ({category}) | Index: #{c_index}")
        print(f"    Status:   {status} | Dimension: {dim} | L2 Norm: {norm:.4f}")
        print(f"    Snippet:  \"{snippet_clean}\"")
        print(f"    Vector:   {format_vector_preview(emb, full=show_full)}")
        print("-" * 80)

        if output_file:
            export_data.append({
                "chunk_id": cid,
                "scheme_name": scheme,
                "category": category,
                "chunk_index": c_index,
                "embedding_dim": dim,
                "l2_norm": round(norm, 4),
                "embedding_status": status,
                "text": text,
                "embedding": emb,
            })

    # Save to file if requested
    if output_file:
        out_path = Path(output_file).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2)
            print(f"\n[+] Successfully exported {len(export_data)} chunks with full embeddings to: {out_path}")
        except Exception as e:
            logger.error(f"Failed to save output to {out_path}: {e}")

    print("\nTip: Use `--full` to print all 384 dimensions, or `--output embs.json` to export to JSON.")
    print("     Use `--file <path>` to view a different JSON file or `--limit <N>` to change count.")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="View and inspect embeddings for processed text chunks in the RAG pipeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        default=None,
        help="Path to a processed chunk JSON file (e.g., data/processed/9_chunks.json). If omitted, scans all processed JSON files.",
    )
    parser.add_argument(
        "-c", "--chunk-id",
        type=str,
        default=None,
        help="Filter and view embedding for a specific chunk UUID.",
    )
    parser.add_argument(
        "-s", "--scheme",
        type=str,
        default=None,
        help="Filter chunks by scheme name or category (case-insensitive substring match).",
    )
    parser.add_argument(
        "-n", "--limit",
        type=int,
        default=5,
        help="Maximum number of chunks to display (use 0 to display all matching chunks).",
    )
    parser.add_argument(
        "--source",
        type=str,
        choices=["auto", "chromadb", "model"],
        default="auto",
        help="Where to retrieve embeddings: 'chromadb' (existing store), 'model' (compute on the fly), or 'auto' (try ChromaDB, fallback to model).",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Print the full 384-dimensional vector in the terminal instead of a shortened preview.",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Export selected chunks along with their full 384-dimensional embedding vectors to a JSON file.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    chunks_to_view = load_chunks_to_view(
        file_path=args.file,
        chunk_id=args.chunk_id,
        scheme_filter=args.scheme,
    )
    display_embeddings(
        chunks=chunks_to_view,
        source_mode=args.source,
        limit=args.limit,
        show_full=args.full,
        output_file=args.output,
    )
