"""
Data Ingestion Pipeline Runner for Mutual Fund FAQ Assistant.

This module implements Phase 2.7 & Phase 3.6 of the implementation plan:
Orchestrates the offline data ingestion pipeline from end to end:
1. Scrapes HDFC Mutual Fund scheme overview pages from Groww (Phase 2.1 - 2.3).
2. Cleans and extracts raw text into data/raw/.
3. Chunks text using RecursiveCharacterTextSplitter and prepends Contextual Headers (Phase 2.4 - 2.6).
4. Attaches comprehensive metadata conforming to the Chunk Metadata Schema.
5. Saves processed chunks to data/processed/<id>_chunks.json.
6. Generates L2-normalized BGE embeddings and indexes all chunks into local ChromaDB vector store (Phase 3.1 - 3.6).
"""

import argparse
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

from config.settings import VECTOR_STORE_PATH
from src.ingestion.chunker import process_all as chunk_all_schemes
from src.ingestion.embedder import index_all_processed_chunks
from src.ingestion.scraper import scrape_all as scrape_all_schemes
from src.ingestion.scheduler import vector_store_lock

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ingest_pipeline")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_RAW_DIR = BASE_DIR / "data" / "raw"
DEFAULT_PROCESSED_DIR = BASE_DIR / "data" / "processed"
DEFAULT_URLS_JSON = BASE_DIR / "data" / "urls.json"
DEFAULT_VECTORSTORE_DIR = BASE_DIR / "vectorstore"


def run_pipeline(
    skip_scrape: bool = False,
    skip_index: bool = False,
    raw_dir: Path | str = DEFAULT_RAW_DIR,
    processed_dir: Path | str = DEFAULT_PROCESSED_DIR,
    urls_json: Path | str = DEFAULT_URLS_JSON,
    vectorstore_dir: Path | str = VECTOR_STORE_PATH,
) -> Dict[str, Any]:
    """
    Execute the end-to-end data ingestion pipeline: scrape -> chunk -> embed -> index.

    Args:
        skip_scrape (bool): If True, skips fetching URLs from web and uses existing files in raw_dir.
        skip_index (bool): If True, skips generating BGE embeddings and indexing into ChromaDB.
        raw_dir (Path | str): Directory for raw scraped text files.
        processed_dir (Path | str): Directory for output processed chunk JSON files.
        urls_json (Path | str): Path to data/urls.json containing corpus scheme definitions.
        vectorstore_dir (Path | str): Directory for ChromaDB persistence.

    Returns:
        dict: Overall execution summary with statistics and scheme-level results.
    """
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("STARTING MUTUAL FUND FAQ ASSISTANT INGESTION PIPELINE")
    logger.info("=" * 60)

    # Step 1: Web Scraping & Raw Text Storage
    scrape_results = []
    if skip_scrape:
        logger.info("[Step 1/3] Skipping web scraping step (--skip-scrape enabled). Using existing raw files.")
    else:
        logger.info(f"[Step 1/3] Scraping corpus from {urls_json} into {raw_dir}...")
        scrape_results = scrape_all_schemes(json_path=urls_json, output_dir=raw_dir)
        success_scrapes = sum(1 for r in scrape_results if r["status"] == "success")
        logger.info(f"[Step 1/3] Scraping complete. Successfully scraped {success_scrapes}/{len(scrape_results)} schemes.")

    # Step 2: Text Chunking, Header Enrichment & Metadata Tagging
    logger.info(f"[Step 2/3] Chunking raw text and enriching metadata into {processed_dir}...")
    chunk_results = chunk_all_schemes(raw_dir=raw_dir, urls_json=urls_json, output_dir=processed_dir)
    total_chunks = sum(r["chunk_count"] for r in chunk_results)
    success_chunks = sum(1 for r in chunk_results if r["status"] == "success")
    logger.info(f"[Step 2/3] Chunking complete. Generated {total_chunks} enriched chunks across {success_chunks} schemes.")

    # Step 3: BGE Embedding & ChromaDB Indexing
    index_results = {}
    if skip_index:
        logger.info("[Step 3/3] Skipping embedding generation and ChromaDB indexing (--skip-index enabled).")
    else:
        logger.info(f"[Step 3/3] Generating BGE embeddings and indexing into ChromaDB ({vectorstore_dir})...")
        logger.info("[Step 3/3] Acquiring vector store mutex lock for safe indexing...")
        with vector_store_lock:
            index_results = index_all_processed_chunks(
                processed_dir=processed_dir,
                persist_directory=vectorstore_dir,
                reset_collection=True,
            )
        indexed_count = index_results.get("indexed_count", 0)
        embedding_dim = index_results.get("embedding_dim", 0)
        logger.info(f"[Step 3/3] Indexing complete. Successfully indexed {indexed_count} chunks (Dim: {embedding_dim}).")

    elapsed_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info(f"PIPELINE COMPLETED in {elapsed_time:.2f} seconds | Total Enriched Chunks: {total_chunks} | Indexed: {index_results.get('indexed_count', 0)}")
    logger.info("=" * 60)

    return {
        "elapsed_seconds": round(elapsed_time, 2),
        "total_schemes": len(chunk_results),
        "successful_schemes": success_chunks,
        "total_chunks_generated": total_chunks,
        "indexed_chunks": index_results.get("indexed_count", 0),
        "embedding_dim": index_results.get("embedding_dim", 0),
        "vectorstore_dir": str(Path(vectorstore_dir).resolve()),
        "scheme_details": chunk_results,
    }


def main():
    parser = argparse.ArgumentParser(description="Run Mutual Fund FAQ Assistant Data Ingestion Pipeline.")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip web scraping and use existing files in data/raw/")
    parser.add_argument("--skip-index", action="store_true", help="Skip BGE embedding generation and ChromaDB indexing")
    parser.add_argument("--raw-dir", type=str, default=str(DEFAULT_RAW_DIR), help="Directory for raw scraped text files")
    parser.add_argument("--processed-dir", type=str, default=str(DEFAULT_PROCESSED_DIR), help="Directory for processed chunk JSON files")
    parser.add_argument("--urls-json", type=str, default=str(DEFAULT_URLS_JSON), help="Path to data/urls.json configuration")
    parser.add_argument("--vectorstore-dir", type=str, default=str(VECTOR_STORE_PATH), help="Directory for persistent ChromaDB storage")

    args = parser.parse_args()

    results = run_pipeline(
        skip_scrape=args.skip_scrape,
        skip_index=args.skip_index,
        raw_dir=args.raw_dir,
        processed_dir=args.processed_dir,
        urls_json=args.urls_json,
        vectorstore_dir=args.vectorstore_dir,
    )

    print("\n" + "=" * 70)
    print(" " * 20 + "INGESTION PIPELINE SUMMARY")
    print("=" * 70)
    print(f"Execution Time     : {results['elapsed_seconds']}s")
    print(f"Total Schemes      : {results['total_schemes']}")
    print(f"Successful Schemes : {results['successful_schemes']}")
    print(f"Total Chunks       : {results['total_chunks_generated']}")
    print(f"Indexed Chunks     : {results['indexed_chunks']} (Dim: {results['embedding_dim']})")
    print(f"Vector Store Path  : {results['vectorstore_dir']}")
    print("-" * 70)
    print(f"{'ID':<4} | {'Scheme Name':<42} | {'Status':<8} | {'Chunks':<8} | {'Avg Chars'}")
    print("-" * 70)
    for s in results["scheme_details"]:
        status_str = "OK" if s["status"] == "success" else "FAIL"
        print(f"{s['id']:<4} | {s['scheme_name']:<42} | {status_str:<8} | {s['chunk_count']:<8} | {s['avg_char_count']}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
