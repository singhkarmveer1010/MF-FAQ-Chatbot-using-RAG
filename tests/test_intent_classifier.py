"""
Unit Tests for Intent Classifier Module (§8.0 Phase 8).

Verifies intent classification (FACTUAL vs. ADVISORY):
- test_factual_nav: "What is the NAV of HDFC Nifty 50?" -> FACTUAL
- test_factual_expense: "What is the expense ratio?" -> FACTUAL
- test_advisory_should_i: "Should I invest in HDFC Nifty 50?" -> ADVISORY
- test_advisory_recommend: "Which fund do you recommend?" -> ADVISORY
- test_advisory_compare: "Which is better, HDFC or SBI?" -> ADVISORY
"""

import pytest
from src.generation.intent_classifier import classify_intent, classify_by_keywords


def test_factual_nav():
    query = "What is the NAV of HDFC Nifty 50?"
    res = classify_intent(query, use_llm=False)
    assert res["intent"] == "FACTUAL"
    assert res["confidence"] >= 0.8


def test_factual_expense():
    query = "What is the expense ratio?"
    res = classify_intent(query, use_llm=False)
    assert res["intent"] == "FACTUAL"
    assert res["confidence"] >= 0.8


def test_advisory_should_i():
    query = "Should I invest in HDFC Nifty 50?"
    res = classify_intent(query, use_llm=False)
    assert res["intent"] == "ADVISORY"
    assert "should i" in res["reason"].lower() or res["confidence"] >= 0.9


def test_advisory_recommend():
    query = "Which fund do you recommend?"
    res = classify_intent(query, use_llm=False)
    assert res["intent"] == "ADVISORY"
    assert "recommend" in res["reason"].lower() or res["confidence"] >= 0.9


def test_advisory_compare():
    query = "Which is better, HDFC or SBI?"
    res = classify_intent(query, use_llm=False)
    assert res["intent"] == "ADVISORY"
    assert "which is better" in res["reason"].lower() or res["confidence"] >= 0.9


def test_empty_query():
    res = classify_intent("", use_llm=False)
    assert res["intent"] == "FACTUAL"
    assert res["confidence"] == 1.0


def test_keyword_fallback_directly():
    res = classify_by_keywords("Is this fund safe for my retirement?")
    assert res["intent"] == "ADVISORY"
