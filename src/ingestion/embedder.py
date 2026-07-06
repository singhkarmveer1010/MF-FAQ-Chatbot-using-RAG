"""
BGE Embedder and ChromaDB Indexer Module for Mutual Fund FAQ Assistant.

This module implements Phase 3 of the implementation plan:
1. Loads BAAI/bge-small-en-v1.5 embedding model via sentence-transformers (Phase 3.1).
2. Generates L2-normalized 384-dimensional dense vectors for all enriched chunks (Phase 3.2).
3. Initializes and manages local ChromaDB vector store collection 'mutual_fund_chunks' with cosine distance metric (Phase 3.3).
4. Upserts text chunks with embeddings and sanitized metadata into PersistentClient storage (Phase 3.4 & 3.5).
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import chromadb
from sentence_transformers import SentenceTransformer

from config.settings import EMBEDDING_MODEL, VECTOR_STORE_PATH

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("embedder")

DEFAULT_COLLECTION_NAME = "mutual_fund_chunks"
DEFAULT_BATCH_SIZE = 64
DEFAULT_PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"


_MODEL_CACHE: Dict[str, SentenceTransformer] = {}

def get_embedding_model(model_name: str = EMBEDDING_MODEL) -> SentenceTransformer:
    """
    Load and return the BGE embedding model via sentence-transformers (cached in memory).

    Args:
        model_name (str): HuggingFace model name or path (default: BAAI/bge-small-en-v1.5).

    Returns:
        SentenceTransformer: Loaded sentence transformer instance.
    """
    if model_name in _MODEL_CACHE:
        return _MODEL_CACHE[model_name]

    logger.info(f"Loading embedding model '{model_name}' via sentence-transformers...")
    start = time.time()
    model = SentenceTransformer(model_name)
    dim = getattr(model, "get_embedding_dimension", model.get_sentence_embedding_dimension)()
    logger.info(f"Loaded model '{model_name}' in {time.time() - start:.2f}s (Dim: {dim})")
    _MODEL_CACHE[model_name] = model
    return model


def generate_embeddings(
    chunks: List[Dict[str, Any]],
    model: Optional[SentenceTransformer] = None,
    model_name: str = EMBEDDING_MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> List[List[float]]:
    """
    Generate L2-normalized BGE embeddings for a list of chunk dictionaries.

    Args:
        chunks (list[dict]): List of chunk dictionaries, each containing a 'text' field.
        model (SentenceTransformer, optional): Pre-loaded model instance. If None, loads automatically.
        model_name (str): Model name to load if model is None.
        batch_size (int): Batch size for encoding.

    Returns:
        list[list[float]]: List of 384-dimensional L2-normalized float embedding vectors.
    """
    if not chunks:
        logger.warning("Empty chunk list provided to generate_embeddings.")
        return []

    if model is None:
        model = get_embedding_model(model_name=model_name)

    texts = [str(c.get("text", "")) for c in chunks]
    logger.info(f"Generating embeddings for {len(texts)} chunks (Batch size: {batch_size}, L2 normalized)...")
    start = time.time()

    # Pass normalize_embeddings=True so that vector L2 norms equal 1.0 (enabling exact Cosine Similarity)
    embeddings_array = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    embeddings = [emb.tolist() for emb in embeddings_array]
    elapsed = time.time() - start
    logger.info(f"Generated {len(embeddings)} embeddings in {elapsed:.2f}s ({len(embeddings) / elapsed:.1f} chunks/sec)")
    return embeddings


def sanitize_metadata(meta: Dict[str, Any]) -> Dict[str, Union[str, int, float, bool]]:
    """
    Sanitize chunk metadata dictionary for ChromaDB storage.
    ChromaDB requires all metadata values to be primitive types (str, int, float, bool).

    Args:
        meta (dict): Raw chunk dictionary.

    Returns:
        dict: Cleaned metadata containing only primitive types.
    """
    clean_meta = {}
    allowed_keys = [
        "source_url", "document_type", "scheme_name", "amc_name",
        "category", "last_scraped_date", "chunk_index", "char_count"
    ]
    for k in allowed_keys:
        if k in meta:
            val = meta[k]
            if val is None:
                clean_meta[k] = ""
            elif isinstance(val, (str, int, float, bool)):
                clean_meta[k] = val
            else:
                clean_meta[k] = str(val)
    return clean_meta


def get_vector_store_client(persist_directory: Union[str, Path] = VECTOR_STORE_PATH) -> chromadb.PersistentClient:
    """
    Initialize and return a ChromaDB PersistentClient.

    Args:
        persist_directory (str | Path): Local directory path for vector store persistence.

    Returns:
        chromadb.PersistentClient: Initialized persistent client.
    """
    persist_dir = Path(persist_directory).resolve()
    persist_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Connecting to ChromaDB PersistentClient at: {persist_dir}")
    return chromadb.PersistentClient(path=str(persist_dir))


def index_chunks(
    chunks: List[Dict[str, Any]],
    embeddings: Optional[List[List[float]]] = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    persist_directory: Union[str, Path] = VECTOR_STORE_PATH,
    model: Optional[SentenceTransformer] = None,
    model_name: str = EMBEDDING_MODEL,
    batch_size: int = 100,
    reset_collection: bool = True,
) -> Dict[str, Any]:
    """
    Upsert chunks and their embeddings into ChromaDB vector store collection.

    Args:
        chunks (list[dict]): Processed chunk dictionaries with metadata and UUIDs.
        embeddings (list[list[float]], optional): Pre-computed embedding vectors. If None, generates automatically.
        collection_name (str): Name of ChromaDB collection.
        persist_directory (str | Path): Path to save persistent vector store.
        model (SentenceTransformer, optional): Pre-loaded embedding model.
        model_name (str): Model name if generation is needed.
        batch_size (int): Batch size for database upserts.
        reset_collection (bool): If True, deletes existing collection before indexing to prevent stale chunk IDs.

    Returns:
        dict: Summary of indexing operations.
    """
    start_time = time.time()
    if not chunks:
        logger.warning("No chunks provided for indexing.")
        return {"status": "failed", "reason": "empty_chunks", "indexed_count": 0}

    # Step 1: Ensure embeddings exist
    if embeddings is None:
        if model is None:
            model = get_embedding_model(model_name=model_name)
        embeddings = generate_embeddings(chunks, model=model, batch_size=batch_size)

    if len(chunks) != len(embeddings):
        raise ValueError(f"Mismatch between chunks ({len(chunks)}) and embeddings ({len(embeddings)})")

    # Step 2: Initialize ChromaDB client and collection
    client = get_vector_store_client(persist_directory=persist_directory)

    if reset_collection:
        try:
            client.delete_collection(name=collection_name)
            logger.info(f"Deleted existing collection '{collection_name}' for clean re-indexing.")
        except Exception:
            logger.debug(f"Collection '{collection_name}' did not exist yet; creating new.")

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    # Step 3: Prepare batch data for ChromaDB upsert
    ids = [str(c.get("chunk_id", f"chunk_{i}")) for i, c in enumerate(chunks)]
    documents = [str(c.get("text", "")) for c in chunks]
    metadatas = [sanitize_metadata(c) for c in chunks]

    logger.info(f"Upserting {len(ids)} chunks into collection '{collection_name}' (Batch size: {batch_size})...")
    total_upserted = 0
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i : i + batch_size]
        batch_embs = embeddings[i : i + batch_size]
        batch_docs = documents[i : i + batch_size]
        batch_metas = metadatas[i : i + batch_size]

        collection.upsert(
            ids=batch_ids,
            embeddings=batch_embs,
            documents=batch_docs,
            metadatas=batch_metas,
        )
        total_upserted += len(batch_ids)

    elapsed_time = time.time() - start_time
    embedding_dim = len(embeddings[0]) if embeddings else 0
    logger.info(f"Successfully indexed {total_upserted} chunks into '{collection_name}' in {elapsed_time:.2f}s (Dim: {embedding_dim})")

    return {
        "status": "success",
        "collection_name": collection_name,
        "persist_directory": str(Path(persist_directory).resolve()),
        "indexed_count": total_upserted,
        "embedding_dim": embedding_dim,
        "elapsed_seconds": round(elapsed_time, 2),
    }


def load_all_processed_chunks(processed_dir: Union[str, Path] = DEFAULT_PROCESSED_DIR) -> List[Dict[str, Any]]:
    """
    Load all processed chunk dictionaries from JSON files in data/processed/.

    Args:
        processed_dir (str | Path): Path to data/processed directory.

    Returns:
        list[dict]: Flattened list of all chunk dictionaries across all scheme files.
    """
    p_dir = Path(processed_dir)
    if not p_dir.exists():
        logger.error(f"Processed directory not found: {p_dir}")
        return []

    json_files = sorted(p_dir.glob("*_chunks.json"))
    all_chunks = []
    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                chunks = json.load(f)
                if isinstance(chunks, list):
                    all_chunks.extend(chunks)
        except Exception as e:
            logger.error(f"Error reading {file_path}: {str(e)}")

    logger.info(f"Loaded {len(all_chunks)} total chunks from {len(json_files)} files in {p_dir}")
    return all_chunks


def index_all_processed_chunks(
    processed_dir: Union[str, Path] = DEFAULT_PROCESSED_DIR,
    persist_directory: Union[str, Path] = VECTOR_STORE_PATH,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    model_name: str = EMBEDDING_MODEL,
    reset_collection: bool = True,
) -> Dict[str, Any]:
    """
    Helper function to load all JSON chunks from disk, generate embeddings, and index into ChromaDB.

    Args:
        processed_dir (str | Path): Path to data/processed/ containing chunk JSONs.
        persist_directory (str | Path): Path to persist ChromaDB vector store.
        collection_name (str): ChromaDB collection name.
        model_name (str): BGE model name.
        reset_collection (bool): Whether to reset existing collection.

    Returns:
        dict: Summary of indexing operation.
    """
    chunks = load_all_processed_chunks(processed_dir=processed_dir)
    if not chunks:
        return {"status": "failed", "reason": "no_processed_chunks_found", "indexed_count": 0}

    return index_chunks(
        chunks=chunks,
        collection_name=collection_name,
        persist_directory=persist_directory,
        model_name=model_name,
        reset_collection=reset_collection,
    )


def test_similarity_query(
    query_text: str = "What is the expense ratio of HDFC Nifty 50 Index Fund?",
    top_k: int = 3,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    persist_directory: Union[str, Path] = VECTOR_STORE_PATH,
    model: Optional[SentenceTransformer] = None,
    model_name: str = EMBEDDING_MODEL,
) -> List[Dict[str, Any]]:
    """
    Execute a test similarity query against the indexed ChromaDB vector store.
    Demonstrates the BGE asymmetric search rule by prepending the instruction prefix to the query.

    Args:
        query_text (str): The natural language user query.
        top_k (int): Number of top matching chunks to retrieve.
        collection_name (str): ChromaDB collection name.
        persist_directory (str | Path): Vector store persistence path.
        model (SentenceTransformer, optional): Pre-loaded embedding model.
        model_name (str): Model name if model is None.

    Returns:
        list[dict]: Top-K retrieved chunks with similarity scores and metadata.
    """
    logger.info(f"Executing test similarity query: '{query_text}' (Top-K: {top_k})...")
    if model is None:
        model = get_embedding_model(model_name=model_name)

    client = get_vector_store_client(persist_directory=persist_directory)
    try:
        collection = client.get_collection(name=collection_name)
    except Exception as e:
        logger.error(f"Collection '{collection_name}' not found: {str(e)}")
        return []

    # Mandatory BGE asymmetric query prefixing
    prefixed_query = f"Represent this sentence for searching relevant passages: {query_text}"
    query_embedding = model.encode([prefixed_query], normalize_embeddings=True, show_progress_bar=False)[0].tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    retrieved = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    for i in range(len(docs)):
        # ChromaDB returns cosine distance (0.0 is identical, 2.0 is opposite)
        # Cosine similarity = 1 - cosine_distance
        similarity = 1.0 - dists[i] if i < len(dists) else 0.0
        retrieved.append({
            "rank": i + 1,
            "similarity": round(similarity, 4),
            "distance": round(dists[i], 4) if i < len(dists) else 0.0,
            "metadata": metas[i] if i < len(metas) else {},
            "text_snippet": (docs[i][:250] + "...") if i < len(docs) and len(docs[i]) > 250 else (docs[i] if i < len(docs) else ""),
        })

    logger.info(f"Retrieved {len(retrieved)} results for query: '{query_text}'")
    for r in retrieved:
        logger.info(f"  [Rank {r['rank']} | Sim: {r['similarity']:.4f}] Scheme: {r['metadata'].get('scheme_name')} | Source: {r['metadata'].get('source_url')}")

    return retrieved


if __name__ == "__main__":
    print("=== Executing Standalone BGE Embedding & ChromaDB Indexing ===")
    res = index_all_processed_chunks()
    print("\n--- Indexing Summary ---")
    print(json.dumps(res, indent=2))

    if res.get("status") == "success" and res.get("indexed_count", 0) > 0:
        print("\n=== Executing Test Similarity Query ===")
        test_res = test_similarity_query()
        print("\n--- Top-3 Retrieved Chunks ---")
        for item in test_res:
            print(f"\n[Rank {item['rank']}] Similarity: {item['similarity']:.4f} (Distance: {item['distance']:.4f})")
            print(f"Scheme: {item['metadata'].get('scheme_name')} | Category: {item['metadata'].get('category')}")
            print(f"Source: {item['metadata'].get('source_url')}")
            print(f"Snippet:\n{item['text_snippet']}")
