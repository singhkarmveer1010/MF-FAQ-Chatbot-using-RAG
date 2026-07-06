"""
Unit Tests for Refusal Handler Module (§8.0 Phase 8).

Verifies refusal handling:
- test_refusal_response: Advisory query refusal has status REFUSED/refused.
- test_refusal_has_edu_link: Advisory query refusal includes an official groww.in educational link.
- test_refusal_no_advice: Refusal text does not contain subjective investment recommendations or opinions.
- test_select_educational_link: Asserts link selection logic picks appropriate Groww resource based on query keywords.
"""

import pytest
from src.generation.refusal_handler import generate_refusal, select_educational_link


def test_select_educational_link():
    assert "filter" in select_educational_link("Which is better between HDFC and SBI?")
    assert "help" in select_educational_link("Is it safe for beginners?")
    assert "groww.in" in select_educational_link("random advisory query")


def test_refusal_response():
    query = "Should I invest in HDFC Nifty 50?"
    res = generate_refusal(query, reason="Advisory query detected.")
    assert res["status"] == "REFUSED"
    assert res["intent"] == "ADVISORY"


def test_refusal_has_edu_link():
    query = "Which fund do you recommend?"
    res = generate_refusal(query, reason="Advisory query detected.")
    assert len(res["citations"]) >= 1
    assert "groww.in" in res["citations"][0]
    assert "groww.in" in res["answer"]


def test_refusal_no_advice():
    query = "Should I buy or sell HDFC Gold ETF?"
    res = generate_refusal(query, reason="Advisory query detected.")
    answer_lower = res["answer"].lower()
    # Ensure it doesn't give advice to buy or sell
    assert "you should buy" not in answer_lower
    assert "you should sell" not in answer_lower
    assert "recommend buying" not in answer_lower
    assert "facts-only" in answer_lower or "cannot provide investment advice" in answer_lower
