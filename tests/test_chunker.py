"""
Unit Tests for Text Chunker and Ingestion Pipeline (Phase 2.4 - 2.7).

Tests:
- 2.4: `chunk_text` splits text cleanly using character boundaries and overlap.
- 2.5: Contextual header enrichment is prepended and metadata schema is satisfied.
- 2.6: `process_file` and `process_all` save JSON files with correct structure.
- 2.7: `run_pipeline` orchestrates end-to-end ingestion without errors.
"""

import json
from pathlib import Path
from unittest.mock import patch
import pytest

from src.ingestion.chunker import chunk_text, process_all, process_file
from src.ingestion.ingest_pipeline import run_pipeline


@pytest.fixture
def sample_metadata():
    return {
        "id": 999,
        "scheme_name": "Test HDFC Nifty Index Fund",
        "category": "Equity Index",
        "url": "https://groww.in/mutual-funds/test-hdfc-index-fund",
        "amc_name": "HDFC Mutual Fund",
    }


@pytest.fixture
def sample_raw_text():
    # Construct text longer than 1200 characters with natural paragraph breaks
    para1 = "HDFC Nifty Index Fund Direct Growth Overview.\nNAV is ₹237.03. Expense ratio is 0.31%. Minimum SIP investment is ₹100.\n" * 5
    para2 = "\n\nHoldings breakdown:\n1. HDFC Bank Ltd - 10.5%\n2. ICICI Bank Ltd - 8.3%\n3. Reliance Industries - 8.2%\n4. Infosys Ltd - 5.1%\n" * 5
    para3 = "\n\nExit load and tax implications:\nExit load of 0.25% if redeemed within 3 days.\nReturns exceeding 1.25L are taxed at 12.5% after one year.\n" * 5
    return para1 + para2 + para3


def test_chunk_text_splits_and_enriches(sample_raw_text, sample_metadata):
    """Test Task 2.4 & 2.5: chunk_text splits correctly and prepends context header."""
    chunks = chunk_text(
        text=sample_raw_text,
        metadata=sample_metadata,
        chunk_size=1000,
        chunk_overlap=100,
    )

    assert len(chunks) > 1, "Should split text into multiple chunks"

    for idx, c in enumerate(chunks):
        # Verify required metadata fields (Task 2.5 schema)
        assert "chunk_id" in c and len(c["chunk_id"]) == 36
        assert c["source_url"] == sample_metadata["url"]
        assert c["document_type"] == "groww_scheme_page"
        assert c["scheme_name"] == sample_metadata["scheme_name"]
        assert c["amc_name"] == sample_metadata["amc_name"]
        assert c["category"] == sample_metadata["category"]
        assert "last_scraped_date" in c
        assert c["chunk_index"] == idx
        assert c["char_count"] == len(c["text"])

        # Verify Contextual Header Enrichment
        expected_header_prefix = f"[Scheme: {sample_metadata['scheme_name']} | AMC: {sample_metadata['amc_name']} | Category: {sample_metadata['category']}"
        assert c["text"].startswith(expected_header_prefix), f"Chunk {idx} missing contextual header enrichment"


def test_chunk_text_empty_input(sample_metadata):
    """Test handling of empty or whitespace-only text."""
    assert chunk_text("", sample_metadata) == []
    assert chunk_text("   ", sample_metadata) == []


def test_process_file_saves_json(tmp_path, sample_raw_text, sample_metadata):
    """Test Task 2.6: process_file reads text and saves formatted JSON chunks."""
    raw_file = tmp_path / "999.txt"
    raw_file.write_text(sample_raw_text, encoding="utf-8")

    out_dir = tmp_path / "processed"
    chunks = process_file(file_path=raw_file, metadata=sample_metadata, output_dir=out_dir)

    assert len(chunks) > 0
    saved_json = out_dir / "999_chunks.json"
    assert saved_json.exists(), "Should save JSON output file"

    with open(saved_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == len(chunks)
        assert data[0]["scheme_name"] == sample_metadata["scheme_name"]


def test_process_all_batch(tmp_path, sample_raw_text):
    """Test batch processing over multiple scheme files."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    out_dir = tmp_path / "processed"

    # Create mock urls.json
    corpus = [
        {"id": 101, "scheme_name": "Fund One", "category": "Equity", "url": "http://example.com/101"},
        {"id": 102, "scheme_name": "Fund Two", "category": "Debt", "url": "http://example.com/102"},
    ]
    urls_json = tmp_path / "urls.json"
    with open(urls_json, "w", encoding="utf-8-sig") as f:
        json.dump({"corpus": corpus}, f)

    # Write one raw file, leave second missing to test resilience
    (raw_dir / "101.txt").write_text(sample_raw_text, encoding="utf-8")

    summary = process_all(raw_dir=raw_dir, urls_json=urls_json, output_dir=out_dir)
    assert len(summary) == 2

    res_101 = next(r for r in summary if r["id"] == 101)
    res_102 = next(r for r in summary if r["id"] == 102)

    assert res_101["status"] == "success"
    assert res_101["chunk_count"] > 0
    assert (out_dir / "101_chunks.json").exists()

    assert res_102["status"] == "missing_raw_file"
    assert res_102["chunk_count"] == 0
    assert not (out_dir / "102_chunks.json").exists()


def test_run_pipeline_skip_scrape(tmp_path, sample_raw_text):
    """Test Task 2.7: ingest_pipeline runner orchestrating offline processing."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    out_dir = tmp_path / "processed"

    corpus = [{"id": 1, "scheme_name": "Test Fund", "category": "Equity", "url": "http://example.com/1"}]
    urls_json = tmp_path / "urls.json"
    with open(urls_json, "w", encoding="utf-8-sig") as f:
        json.dump({"corpus": corpus}, f)

    (raw_dir / "1.txt").write_text(sample_raw_text, encoding="utf-8")

    results = run_pipeline(
        skip_scrape=True,
        skip_index=True,
        raw_dir=raw_dir,
        processed_dir=out_dir,
        urls_json=urls_json,
        vectorstore_dir=tmp_path / "vectorstore",
    )

    assert results["total_schemes"] == 1
    assert results["successful_schemes"] == 1
    assert results["total_chunks_generated"] > 0
    assert (out_dir / "1_chunks.json").exists()


@patch("src.ingestion.scraper.scrape_url")
def test_run_pipeline_with_scrape(mock_scrape, tmp_path, sample_raw_text):
    """Test Task 2.7: ingest_pipeline runner executing scrape step without keyword argument errors."""
    mock_scrape.return_value = sample_raw_text
    raw_dir = tmp_path / "raw"
    out_dir = tmp_path / "processed"

    corpus = [{"id": 1, "scheme_name": "Test Fund", "category": "Equity", "url": "http://example.com/1"}]
    urls_json = tmp_path / "urls.json"
    with open(urls_json, "w", encoding="utf-8-sig") as f:
        json.dump({"corpus": corpus}, f)

    results = run_pipeline(
        skip_scrape=False,
        skip_index=True,
        raw_dir=raw_dir,
        processed_dir=out_dir,
        urls_json=urls_json,
        vectorstore_dir=tmp_path / "vectorstore",
    )

    assert results["total_schemes"] == 1
    assert results["successful_schemes"] == 1
    assert results["total_chunks_generated"] > 0
    assert (raw_dir / "1.txt").exists()
    assert (out_dir / "1_chunks.json").exists()

