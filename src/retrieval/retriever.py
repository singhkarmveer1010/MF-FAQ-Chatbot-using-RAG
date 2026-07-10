"""
Retriever Module for Mutual Fund FAQ Assistant (Phase 4.2).

Implements the Metadata-Aware Cosine Retrieval Strategy:
1. Connects to persisted ChromaDB collection 'mutual_fund_chunks' (§4.2.1).
2. Generates query embeddings using BGE-small with mandatory asymmetric prefix (§4.2.2).
3. Extracts scheme names/aliases to construct ChromaDB metadata filters (§4.2.3).
4. Executes cosine distance query, converts to similarity (1 - d), and filters by threshold (§4.2.4).
5. Automatic fallback mechanism to unfiltered corpus search if filtered results are sparse (§4.2.5).
"""

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.settings import RETRIEVAL_TOP_K, SIMILARITY_THRESHOLD, VECTOR_STORE_PATH, EMBEDDING_MODEL
from src.ingestion.scheduler import vector_store_lock

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("retriever")

# Mandatory BGE query instruction prefix for asymmetric retrieval (§3.2.1)
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
DEFAULT_COLLECTION_NAME = "mutual_fund_chunks"
DEFAULT_PROCESSED_DIR = BASE_DIR / "data" / "processed"
ENABLE_VECTOR_RETRIEVAL = os.getenv("ENABLE_VECTOR_RETRIEVAL", "false").lower() in {"1", "true", "yes", "on"}
_LEXICAL_CHUNK_CACHE: Optional[List[Dict[str, Any]]] = None

# Scheme Alias Mapping for Smart Metadata Filtering (§4.2.3)
SCHEME_ALIAS_MAP = [
    (["next 50", "nifty next 50"], "HDFC Nifty Next 50 Index Fund"),
    (["nifty500", "multicap", "50:25:25", "nifty 500"], "HDFC Nifty500 Multicap 50:25:25 Index Fund"),
    (["nifty 50", "nifty50", "nifty index"], "HDFC Nifty 50 Index Fund"),
    (["sensex", "bse sensex"], "HDFC BSE Sensex Index Fund"),
    (["children", "child fund", "childrens"], "HDFC Childrens Fund"),
    (["banking", "financial services"], "HDFC Banking and Financial Services Fund"),
    (["corporate debt", "corporate bond"], "HDFC Corporate Debt Opportunities Fund"),
    (["gold", "gold etf", "gold fund"], "HDFC Gold ETF Fund of Fund"),
    (["diversified equity", "all cap active", "all cap fof", "active fof"], "HDFC Diversified Equity All Cap Active FoF"),
    (["digital", "india digital", "tech fund"], "HDFC Nifty India Digital Index Fund"),
]

UNSUPPORTED_SCHEME_MAP = [
    (["small cap", "small-cap", "smallcap"], "HDFC Small Cap Fund"),
    (["flexi cap", "flexi-cap", "flexicap"], "HDFC Flexi Cap Fund"),
    (["liquid fund", "liquid"], "HDFC Liquid Fund"),
    (["balanced advantage", "baf"], "HDFC Balanced Advantage Fund"),
    (["mid cap", "mid-cap", "midcap"], "HDFC Mid-Cap Opportunities Fund"),
    (["large cap", "large-cap", "large and mid"], "HDFC Large and Mid Cap Fund"),
    (["multi asset", "multi-asset"], "HDFC Multi Asset Fund"),
    (["top 100", "top100"], "HDFC Top 100 Fund"),
    (["tax saver", "elss"], "HDFC Tax Saver Fund"),
    (["infrastructure", "infra"], "HDFC Infrastructure Fund"),
]


def extract_scheme_filter(query: str) -> Optional[str]:
    """
    Analyze user query to detect if a specific HDFC scheme is being referenced.
    Uses word-boundary regex matching to avoid substring false positives (e.g. 'all cap' in 'small cap').
    Returns the exact scheme name to use in ChromaDB metadata filtering.

    Args:
        query (str): Natural language query.

    Returns:
        str | None: Exact scheme name if detected, otherwise None.
    """
    query_lower = query.lower()
    for aliases, scheme_name in SCHEME_ALIAS_MAP:
        for alias in aliases:
            pattern = r"\b" + re.escape(alias) + r"\b"
            if re.search(pattern, query_lower):
                logger.debug(f"Detected scheme alias '{alias}' -> Filtering for '{scheme_name}'")
                return scheme_name
    return None


def check_unsupported_scheme(query: str) -> Optional[str]:
    """
    Check if query asks about a common HDFC mutual fund that is NOT in our 10 indexed schemes.
    """
    query_lower = query.lower()
    for aliases, scheme_name in UNSUPPORTED_SCHEME_MAP:
        for alias in aliases:
            pattern = r"\b" + re.escape(alias) + r"\b"
            if re.search(pattern, query_lower):
                return scheme_name
    return None


def embed_query(query_text: str, model: Any = None) -> List[float]:
    """
    Encode query string into a 384-dim L2-normalized BGE vector using the asymmetric search prefix.

    Args:
        query_text (str): Raw user query.
        model (SentenceTransformer, optional): Pre-loaded BGE model.

    Returns:
        list[float]: 384-dimensional normalized embedding vector.
    """
    if model is None:
        from src.ingestion.embedder import get_embedding_model

        model = get_embedding_model(model_name=EMBEDDING_MODEL)
        
    prefixed_query = f"{BGE_QUERY_PREFIX}{query_text.strip()}"
    logger.debug(f"Encoding prefixed query (Length: {len(prefixed_query)} chars)...")
    
    embedding_array = model.encode(
        [prefixed_query],
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return embedding_array[0].tolist()


def _tokenize(text: str) -> List[str]:
    """Return simple normalized tokens for fallback corpus retrieval."""
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in {"the", "and", "for", "with", "hdfc", "fund"}
    ]


def _load_processed_chunks(processed_dir: Path = DEFAULT_PROCESSED_DIR) -> List[Dict[str, Any]]:
    """Load checked-in processed chunks without touching ChromaDB or embedding models."""
    global _LEXICAL_CHUNK_CACHE
    if _LEXICAL_CHUNK_CACHE is not None:
        return _LEXICAL_CHUNK_CACHE

    chunks: List[Dict[str, Any]] = []
    if not processed_dir.exists():
        logger.error("Processed chunks directory not found: %s", processed_dir)
        _LEXICAL_CHUNK_CACHE = chunks
        return chunks

    for file_path in sorted(processed_dir.glob("*_chunks.json")):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                chunks.extend(item for item in data if isinstance(item, dict))
        except Exception as exc:
            logger.warning("Failed to load processed chunks from %s: %s", file_path, exc)

    logger.info("Loaded %d processed chunks for lightweight retrieval.", len(chunks))
    _LEXICAL_CHUNK_CACHE = chunks
    return chunks


def _retrieve_from_processed_chunks(
    query: str,
    top_k: int = RETRIEVAL_TOP_K,
    scheme_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fallback retriever for small deployments where vector dependencies are too heavy."""
    chunks = _load_processed_chunks()
    if not chunks:
        return []

    query_tokens = set(_tokenize(query))
    if not query_tokens:
        return []

    if scheme_filter is None:
        scheme_filter = extract_scheme_filter(query)

    scored: List[Dict[str, Any]] = []
    for idx, chunk in enumerate(chunks):
        chunk_scheme = str(chunk.get("scheme_name", ""))
        if scheme_filter and chunk_scheme != scheme_filter:
            continue

        searchable_text = " ".join(
            str(chunk.get(key, ""))
            for key in ("scheme_name", "category", "document_type", "text")
        )
        chunk_tokens = set(_tokenize(searchable_text))
        overlap = query_tokens & chunk_tokens
        if not overlap:
            continue

        scheme_bonus = 3 if scheme_filter and chunk_scheme == scheme_filter else 0
        score = len(overlap) + scheme_bonus
        scored.append(
            {
                "score": score,
                "chunk": chunk,
                "idx": idx,
            }
        )

    # If a strict scheme filter produced no hits, search the whole checked-in corpus.
    if not scored and scheme_filter:
        return _retrieve_from_processed_chunks(query=query, top_k=top_k, scheme_filter=None)

    scored.sort(key=lambda item: item["score"], reverse=True)

    results: List[Dict[str, Any]] = []
    for rank, item in enumerate(scored[:top_k], 1):
        chunk = item["chunk"]
        score = item["score"]
        similarity = min(0.99, 0.55 + (score * 0.05))
        results.append(
            {
                "chunk_id": str(chunk.get("chunk_id", f"processed_{item['idx']}")),
                "similarity": round(similarity, 4),
                "distance": round(1.0 - similarity, 4),
                "text": str(chunk.get("text", "")),
                "metadata": {
                    "source_url": chunk.get("source_url", ""),
                    "document_type": chunk.get("document_type", ""),
                    "scheme_name": chunk.get("scheme_name", ""),
                    "amc_name": chunk.get("amc_name", ""),
                    "category": chunk.get("category", ""),
                    "last_scraped_date": chunk.get("last_scraped_date", ""),
                    "chunk_index": chunk.get("chunk_index", rank),
                    "char_count": chunk.get("char_count", len(str(chunk.get("text", "")))),
                },
            }
        )

    logger.info("Lightweight retrieval returned %d chunks for query: '%s'", len(results), query)
    return results


def retrieve(
    query: str,
    top_k: int = RETRIEVAL_TOP_K,
    similarity_threshold: float = SIMILARITY_THRESHOLD,
    scheme_filter: Optional[str] = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    persist_dir: str | Path = VECTOR_STORE_PATH,
    model: Any = None,
) -> List[Dict[str, Any]]:
    """
    Execute semantic similarity retrieval against ChromaDB vector store.
    Converts cosine distance to similarity, applies threshold filtering, and handles fallback.

    Args:
        query (str): User question.
        top_k (int): Maximum number of top chunks to return.
        similarity_threshold (float): Minimum cosine similarity score (0.0 to 1.0).
        scheme_filter (str, optional): Explicit scheme name filter. If None, auto-detected.
        collection_name (str): ChromaDB collection name.
        persist_dir (str | Path): Path to vector store directory.
        model (SentenceTransformer, optional): Pre-loaded BGE embedding model.

    Returns:
        list[dict]: List of retrieved chunk dictionaries sorted by similarity descending.
    """
    if not query or not query.strip():
        logger.warning("Empty query provided to retriever.")
        return []

    if not ENABLE_VECTOR_RETRIEVAL:
        return _retrieve_from_processed_chunks(query=query, top_k=top_k, scheme_filter=scheme_filter)

    try:
        # Step 1: Embed query
        query_embedding = embed_query(query, model=model)
    except Exception as exc:
        logger.warning("Vector embedding unavailable; falling back to processed-chunk retrieval: %s", exc)
        return _retrieve_from_processed_chunks(query=query, top_k=top_k, scheme_filter=scheme_filter)

    # Step 2: Auto-detect scheme filter if not specified
    if scheme_filter is None:
        scheme_filter = extract_scheme_filter(query)

    # Step 3: Connect to ChromaDB (under read/write mutex lock for thread safety vs background ingestion)
    with vector_store_lock:
        from src.ingestion.embedder import get_vector_store_client

        client = get_vector_store_client(persist_directory=persist_dir)
        try:
            collection = client.get_collection(name=collection_name)
        except Exception as e:
            logger.error(f"Failed to load collection '{collection_name}': {e}")
            return _retrieve_from_processed_chunks(query=query, top_k=top_k, scheme_filter=scheme_filter)

        # Helper for querying ChromaDB and formatting results
        def query_chroma(where_clause: Optional[Dict[str, Any]] = None, fetch_k: int = top_k) -> List[Dict[str, Any]]:
            res = collection.query(
                query_embeddings=[query_embedding],
                n_results=fetch_k,
                where=where_clause,
                include=["documents", "metadatas", "distances"],
            )
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[]])[0]
            ids = res.get("ids", [[]])[0]

            formatted = []
            for i in range(len(docs)):
                dist = dists[i] if i < len(dists) else 0.0
                sim = 1.0 - dist  # Cosine similarity = 1 - cosine distance
                if sim >= similarity_threshold:
                    formatted.append({
                        "chunk_id": ids[i] if i < len(ids) else f"res_{i}",
                        "similarity": round(sim, 4),
                        "distance": round(dist, 4),
                        "text": docs[i] if i < len(docs) else "",
                        "metadata": metas[i] if i < len(metas) else {},
                    })
            return sorted(formatted, key=lambda x: x["similarity"], reverse=True)

        # Step 4: Execute query with metadata filter if applicable
        results = []
        if scheme_filter:
            logger.info(f"Executing retrieval with metadata filter: scheme_name == '{scheme_filter}'")
            where_filter = {"scheme_name": {"$eq": scheme_filter}}
            results = query_chroma(where_clause=where_filter, fetch_k=top_k)
            
            # Step 5: Fallback mechanism (§4.2.5)
            if not results:
                logger.warning(f"0 chunks found above threshold ({similarity_threshold}) with filter '{scheme_filter}'. Falling back to unfiltered search...")
                results = query_chroma(where_clause=None, fetch_k=top_k)
        else:
            logger.info("Executing unfiltered corpus-wide retrieval...")
            results = query_chroma(where_clause=None, fetch_k=top_k)

    logger.info(f"Retrieved {len(results)} chunks above similarity threshold {similarity_threshold} for query: '{query}'")
    for idx, r in enumerate(results, 1):
        logger.debug(f"  [{idx}] Sim: {r['similarity']:.4f} | Scheme: {r['metadata'].get('scheme_name')} | URL: {r['metadata'].get('source_url')}")

    return results


if __name__ == "__main__":
    print("=== Testing Retriever Module (Phase 4.2) ===")
    test_queries = [
        "What is the expense ratio of HDFC Nifty 50 Index Fund?",
        "Who manages the HDFC Childrens Fund and what is his qualification?",
        "What is the exit load for HDFC Gold ETF if redeemed early?",
        "Tell me about corporate bond holdings in HDFC Corporate Debt Opportunities Fund.",
    ]
    
    for q in test_queries:
        print("\n" + "=" * 80)
        print(f"Query: \"{q}\"")
        detected_scheme = extract_scheme_filter(q)
        print(f"Detected Scheme Filter: {detected_scheme}")
        print("-" * 80)
        
        chunks = retrieve(q, top_k=3, similarity_threshold=0.50)  # Use 0.50 for test visibility
        if not chunks:
            print("  [No chunks retrieved above threshold]")
        else:
            for i, c in enumerate(chunks, 1):
                scheme = c["metadata"].get("scheme_name", "Unknown")
                cat = c["metadata"].get("category", "Unknown")
                sim = c["similarity"]
                snippet = c["text"][:150].replace("\n", " ") + "..."
                print(f"  [{i}] Sim: {sim:.4f} | {scheme} ({cat})")
                print(f"      Snippet: \"{snippet}\"")
