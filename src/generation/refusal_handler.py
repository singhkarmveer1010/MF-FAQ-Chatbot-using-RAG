"""
Refusal Handler Module for Mutual Fund FAQ Assistant (Phase 4.4).

Implements rule-compliant refusal handling for advisory, subjective, or comparison queries:
1. Generates polite, SEBI-compliant refusal responses (§4.4.1).
2. Attaches official Groww educational resource links based on query context (§4.4.2).
3. Enforces the required 'Last updated from sources: <date>' footer (§3.4).
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.prompts import EDUCATIONAL_LINKS_POOL, REFUSAL_TEMPLATE

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("refusal_handler")


def select_educational_link(query: str) -> str:
    """
    Select the most relevant educational resource link from Groww based on query keywords.

    Args:
        query (str): The advisory user query.

    Returns:
        str: Selected official Groww educational URL.
    """
    query_lower = query.lower()
    
    # If comparison or filtering between funds
    if any(kw in query_lower for kw in ("compare", "better", "best", "top", "filter", "vs")):
        return "https://groww.in/mutual-funds/filter"
        
    # If general guidance or safety questions
    if any(kw in query_lower for kw in ("safe", "how to", "guide", "help", "support", "start")):
        return "https://groww.in/help/mutual-funds"
        
    # Default to Groww mutual funds blog category
    return "https://groww.in/blog/category/mutual-funds"


def generate_refusal(
    query: str,
    reason: str = "Classified as advisory or subjective query.",
    date: str = "2026-07-05",
) -> Dict[str, Any]:
    """
    Generate a polite refusal response for an advisory or subjective query.

    Args:
        query (str): The natural language user query.
        reason (str): Explanation from the intent classifier.
        date (str): Latest scraped date for footer attribution.

    Returns:
        dict: Structured refusal response:
            {
              "answer": str,
              "citations": list[str],
              "intent": "ADVISORY",
              "reason": str,
              "status": "REFUSED"
            }
    """
    logger.info(f"Generating refusal for query: '{query}' (Reason: {reason})")
    
    edu_link = select_educational_link(query)
    logger.debug(f"Selected educational link: {edu_link}")
    
    refusal_text = REFUSAL_TEMPLATE.format(
        educational_link=edu_link,
        date=date,
    ).strip()

    return {
        "answer": refusal_text,
        "citations": [edu_link],
        "intent": "ADVISORY",
        "reason": reason,
        "status": "REFUSED",
    }


if __name__ == "__main__":
    print("=== Testing Refusal Handler Module (Phase 4.4) ===")
    test_advisory_queries = [
        ("Should I invest in HDFC Small Cap Fund right now?", "Matched advisory keyword: 'should i'"),
        ("Which fund is better between Nifty 50 and Sensex?", "Matched comparison pattern: 'which fund is better'"),
        ("Is HDFC Gold ETF safe for beginners?", "Matched subjective safety pattern: 'safe for'"),
    ]
    
    for q, r in test_advisory_queries:
        print("\n" + "=" * 80)
        print(f"Query:  \"{q}\"")
        print(f"Reason: {r}")
        print("-" * 80)
        res = generate_refusal(q, reason=r)
        print(f"Status:    {res['status']} | Intent: {res['intent']}")
        print(f"Citations: {res['citations']}")
        print(f"\nGenerated Refusal:\n{res['answer']}")
