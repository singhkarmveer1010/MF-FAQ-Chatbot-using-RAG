"""
Text Chunker and Metadata Tagger Module for Mutual Fund FAQ Assistant.

This module implements Phase 2.4 - 2.6 of the implementation plan:
1. Splits raw scraped text into semantically meaningful chunks using RecursiveCharacterTextSplitter.
2. Prepends Contextual Header Enrichment to every chunk to optimize RAG vector retrieval.
3. Attaches comprehensive metadata conforming to the Chunk Metadata Schema.
4. Persists processed chunks as JSON files in data/processed/.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Default paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_RAW_DIR = BASE_DIR / "data" / "raw"
DEFAULT_PROCESSED_DIR = BASE_DIR / "data" / "processed"
DEFAULT_URLS_JSON = BASE_DIR / "data" / "urls.json"

# Default chunking parameters
DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def chunk_text(
    text: str,
    metadata: Dict[str, Any],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    separators: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Split raw text into chunks, prepend contextual header, and attach metadata.

    Args:
        text (str): Raw scraped text content.
        metadata (dict): Scheme metadata containing at least 'scheme_name', 'url', 'category', 'id'.
        chunk_size (int): Target maximum character length for each chunk.
        chunk_overlap (int): Number of characters to overlap between contiguous chunks.
        separators (list[str], optional): List of structural separator strings for RecursiveCharacterTextSplitter.

    Returns:
        list[dict]: List of processed chunk dictionaries conforming to Chunk Metadata Schema.
    """
    if not text or not text.strip():
        logger.warning(f"Empty text provided for chunking scheme: {metadata.get('scheme_name')}")
        return []

    if separators is None:
        separators = DEFAULT_SEPARATORS

    # Initialize LangChain splitter
    splitter = RecursiveCharacterTextSplitter(
        separators=separators,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )

    raw_chunks = splitter.split_text(text)
    logger.debug(f"Split raw text into {len(raw_chunks)} base chunks for scheme: {metadata.get('scheme_name')}")

    # Extract metadata fields with fallbacks
    scheme_name = metadata.get("scheme_name", "Unknown Scheme")
    source_url = metadata.get("url", "")
    category = metadata.get("category", "General")
    amc_name = metadata.get("amc_name", "HDFC Mutual Fund")
    last_scraped_date = metadata.get("last_scraped_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Build contextual header for RAG optimization
    header = f"[Scheme: {scheme_name} | AMC: {amc_name} | Category: {category} | Source: {source_url}]"

    processed_chunks = []
    for idx, chunk_str in enumerate(raw_chunks):
        # Prepend contextual header enrichment
        enriched_text = f"{header}\n\n{chunk_str.strip()}"

        chunk_obj = {
            "chunk_id": str(uuid.uuid4()),
            "text": enriched_text,
            "source_url": source_url,
            "document_type": "groww_scheme_page",
            "scheme_name": scheme_name,
            "amc_name": amc_name,
            "category": category,
            "last_scraped_date": last_scraped_date,
            "chunk_index": idx,
            "char_count": len(enriched_text),
        }
        processed_chunks.append(chunk_obj)

    logger.info(f"Created {len(processed_chunks)} enriched chunks for '{scheme_name}' (Avg chars: {sum(c['char_count'] for c in processed_chunks) // len(processed_chunks) if processed_chunks else 0})")
    return processed_chunks


def process_file(
    file_path: Union[str, Path],
    metadata: Dict[str, Any],
    output_dir: Optional[Union[str, Path]] = DEFAULT_PROCESSED_DIR,
) -> List[Dict[str, Any]]:
    """
    Read a raw text file, chunk it, attach metadata, and optionally save to JSON.

    Args:
        file_path (str | Path): Path to the raw text file (e.g., data/raw/1.txt).
        metadata (dict): Scheme metadata from data/urls.json.
        output_dir (str | Path, optional): Directory to save processed JSON file. If None, does not save to disk.

    Returns:
        list[dict]: List of processed chunk dictionaries.
    """
    path = Path(file_path)
    if not path.exists():
        logger.error(f"Raw file not found: {path}")
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        logger.error(f"Failed to read file {path}: {str(e)}")
        return []

    chunks = chunk_text(text=text, metadata=metadata)

    if output_dir and chunks:
        out_dir_path = Path(output_dir)
        out_dir_path.mkdir(parents=True, exist_ok=True)
        scheme_id = metadata.get("id", path.stem)
        out_file = out_dir_path / f"{scheme_id}_chunks.json"

        try:
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(chunks, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(chunks)} chunks to {out_file}")
        except Exception as e:
            logger.error(f"Failed to save JSON file {out_file}: {str(e)}")

    return chunks


def process_all(
    raw_dir: Union[str, Path] = DEFAULT_RAW_DIR,
    urls_json: Union[str, Path] = DEFAULT_URLS_JSON,
    output_dir: Union[str, Path] = DEFAULT_PROCESSED_DIR,
) -> List[Dict[str, Any]]:
    """
    Process all raw scheme files in data/raw/ based on data/urls.json.

    Args:
        raw_dir (str | Path): Directory containing raw scraped text files.
        urls_json (str | Path): Path to data/urls.json containing corpus definitions.
        output_dir (str | Path): Directory to save processed JSON files.

    Returns:
        list[dict]: Summary list containing chunk statistics for each scheme processed.
    """
    json_path = Path(urls_json)
    raw_path = Path(raw_dir)
    out_path = Path(output_dir)

    if not json_path.exists():
        logger.error(f"URLs configuration file not found at: {json_path}")
        return []

    try:
        with open(json_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
            corpus = data.get("corpus", [])
    except Exception as e:
        logger.error(f"Failed to load JSON from {json_path}: {str(e)}")
        return []

    out_path.mkdir(parents=True, exist_ok=True)
    summary = []
    total_chunks_all = 0

    logger.info(f"Starting batch chunking for {len(corpus)} schemes. Output directory: {out_path}")

    for item in corpus:
        scheme_id = item.get("id")
        scheme_name = item.get("scheme_name", f"Scheme {scheme_id}")
        raw_file = raw_path / f"{scheme_id}.txt"

        if not raw_file.exists():
            logger.warning(f"Raw file missing for ID {scheme_id} ({scheme_name}): {raw_file}")
            summary.append({
                "id": scheme_id,
                "scheme_name": scheme_name,
                "status": "missing_raw_file",
                "chunk_count": 0,
            })
            continue

        chunks = process_file(file_path=raw_file, metadata=item, output_dir=out_path)
        chunk_count = len(chunks)
        total_chunks_all += chunk_count

        summary.append({
            "id": scheme_id,
            "scheme_name": scheme_name,
            "status": "success" if chunk_count > 0 else "failed",
            "chunk_count": chunk_count,
            "avg_char_count": sum(c["char_count"] for c in chunks) // chunk_count if chunk_count > 0 else 0,
            "output_file": str(out_path / f"{scheme_id}_chunks.json") if chunk_count > 0 else None,
        })

    logger.info(f"Batch chunking completed. Total schemes processed: {len(summary)}, Total chunks generated: {total_chunks_all}")
    return summary


if __name__ == "__main__":
    print("Executing standalone batch chunking...")
    res_summary = process_all()
    print("\n--- Chunking Summary ---")
    for res in res_summary:
        status_str = "OK  " if res["status"] == "success" else "FAIL"
        print(f"[{status_str}] ID {res.get('id')}: {res.get('scheme_name')} -> {res.get('chunk_count')} chunks (Avg chars: {res.get('avg_char_count')})")
