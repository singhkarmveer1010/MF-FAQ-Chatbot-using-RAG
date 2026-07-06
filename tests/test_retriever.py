"""
Unit Tests for Retriever Module (§8.0 Phase 8).

Verifies metadata-aware cosine retrieval:
- test_returns_chunks: Factual query about HDFC Nifty 50 returns >= 1 chunk.
- test_chunk_has_source_url: Each returned chunk has a source_url in metadata.
- test_threshold_filters: Very unrelated query or strict threshold returns 0 chunks.
- test_scheme_filter_extraction: Asserts word-boundary regex mapping works accurately.
"""

import pytest
from src.retrieval.retriever import retrieve, extract_scheme_filter, check_unsupported_scheme


def test_scheme_filter_extraction():
    assert extract_scheme_filter("Tell me about HDFC Nifty 50 Index Fund") == "HDFC Nifty 50 Index Fund"
    assert extract_scheme_filter("What is the NAV of sensex fund?") == "HDFC BSE Sensex Index Fund"
    assert extract_scheme_filter("How is the children fund performing?") == "HDFC Childrens Fund"
    assert extract_scheme_filter("random general query without scheme") is None


def test_unsupported_scheme_check():
    assert check_unsupported_scheme("What about small cap fund?") == "HDFC Small Cap Fund"
    assert check_unsupported_scheme("Tell me about flexi cap") == "HDFC Flexi Cap Fund"
    assert check_unsupported_scheme("What is HDFC Nifty 50?") is None


def test_returns_chunks():
    query = "What is the expense ratio of HDFC Nifty 50 Index Fund?"
    chunks = retrieve(query, top_k=3, similarity_threshold=0.30)
    assert len(chunks) >= 1
    assert any("Nifty 50" in c["metadata"].get("scheme_name", "") for c in chunks)


def test_chunk_has_source_url():
    query = "Who is the fund manager of HDFC Childrens Fund?"
    chunks = retrieve(query, top_k=2, similarity_threshold=0.30)
    assert len(chunks) >= 1
    for c in chunks:
        assert "source_url" in c["metadata"]
        assert "groww.in" in c["metadata"]["source_url"]


def test_threshold_filters():
    # An unrelated query with high threshold should yield 0 results
    query = "quantum physics relativity equation alien spaceship syntax"
    chunks = retrieve(query, top_k=5, similarity_threshold=0.85)
    assert len(chunks) == 0
