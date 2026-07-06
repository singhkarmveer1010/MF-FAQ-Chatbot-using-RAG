"""
Unit Tests for Response Formatter Module (§8.0 Phase 8).

Verifies format compliance:
- test_max_sentences: Any factual query response is truncated/enforced to <= 3 sentences.
- test_citation_present: Response contains a valid groww.in URL.
- test_footer_present: Response ends with 'Last updated from sources:'.
- test_validate_format_report: Asserts the validation reporter detects format violations.
"""

import pytest
from src.generation.citation_formatter import format_and_enforce, validate_format, count_sentences


def test_max_sentences():
    long_text = "Sentence one is here. Sentence two is here. Sentence three is here. This fourth sentence is extra. This fifth sentence is also extra."
    formatted = format_and_enforce(
        long_text,
        citations=["https://groww.in/mutual-funds/hdfc-nifty-50-index-fund-direct-growth"],
        status="SUCCESS"
    )
    val = validate_format(formatted, status="SUCCESS")
    assert val["is_valid"] is True
    assert val["sentence_count"] <= 3
    assert "fourth sentence" not in formatted


def test_citation_present():
    raw_text = "The expense ratio is 0.20%."
    formatted = format_and_enforce(
        raw_text,
        citations=["https://groww.in/mutual-funds/hdfc-nifty-50-index-fund-direct-growth"],
        status="SUCCESS"
    )
    assert "https://groww.in/" in formatted
    val = validate_format(formatted, status="SUCCESS")
    assert val["has_citation"] is True


def test_footer_present():
    raw_text = "The exit load is nil after 3 days."
    formatted = format_and_enforce(
        raw_text,
        citations=["https://groww.in/mutual-funds/hdfc-nifty-50-index-fund-direct-growth"],
        date="2026-07-06",
        status="SUCCESS"
    )
    assert "Last updated from sources: 2026-07-06" in formatted
    val = validate_format(formatted, status="SUCCESS")
    assert val["has_footer"] is True


def test_validate_format_report():
    invalid_text = "Only one sentence here without footer or citation."
    val = validate_format(invalid_text, status="SUCCESS")
    assert val["is_valid"] is False
    assert len(val["issues"]) >= 1
