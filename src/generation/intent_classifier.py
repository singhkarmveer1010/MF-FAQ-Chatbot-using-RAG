"""
Intent Classifier Module for Mutual Fund FAQ Assistant.

This module implements Phase 4.1 of the implementation plan:
1. Keyword-heuristic classifier matching advisory/subjective patterns (§4.1.1).
2. Primary LLM-based classifier using Groq via LangChain (§4.1.2).
3. Structured output returning intent, confidence score, and classification rationale (§4.1.3).
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.prompts import INTENT_CLASSIFICATION_PROMPT
from config.settings import GROQ_API_KEY, LLM_MODEL, LLM_TEMPERATURE

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("intent_classifier")

# Advisory and subjective keywords/phrases (§4.1.1 & §3.3.1)
ADVISORY_KEYWORDS = [
    "should i",
    "which is better",
    "which fund is better",
    "recommend",
    "good time to",
    "safe for",
    "is it safe",
    "can i invest",
    "should we invest",
    "how much should i",
    "best fund",
    "top fund",
    "future returns",
    "will it grow",
    "buy or sell",
    "worth buying",
    "should i buy",
    "should i sell",
    "should i redeem",
    "suggest a fund",
    "suggest me",
    "portfolio advice",
    "is this fund good",
    "compare",
]


def classify_by_keywords(query: str) -> Dict[str, Any]:
    """
    Classify user query intent using rule-based keyword heuristics.

    Args:
        query (str): The raw user query string.

    Returns:
        dict: Structured intent dictionary with 'intent', 'confidence', 'reason', and 'method'.
    """
    query_lower = query.lower().strip()
    
    for kw in ADVISORY_KEYWORDS:
        # Use word boundary or substring checking for phrase matches
        if kw in query_lower:
            logger.debug(f"Keyword classifier detected advisory pattern: '{kw}' in query: '{query}'")
            return {
                "intent": "ADVISORY",
                "confidence": 0.95,
                "reason": f"Matched advisory pattern: '{kw}'",
                "method": "keyword",
            }
            
    return {
        "intent": "FACTUAL",
        "confidence": 0.85,
        "reason": "No advisory keywords or subjective patterns detected.",
        "method": "keyword",
    }


def classify_intent(query: str, use_llm: bool = True) -> Dict[str, Any]:
    """
    Classify user query intent as either FACTUAL or ADVISORY.
    Uses LLM classification via Groq as primary method, falling back to keyword heuristics.

    Args:
        query (str): The natural language user query.
        use_llm (bool): Whether to attempt LLM classification (default: True).

    Returns:
        dict: Structured dictionary:
            {
              "intent": "FACTUAL" | "ADVISORY",
              "confidence": float,
              "reason": str,
              "method": "llm" | "keyword"
            }
    """
    if not query or not query.strip():
        return {
            "intent": "FACTUAL",
            "confidence": 1.0,
            "reason": "Empty query defaulted to FACTUAL.",
            "method": "keyword",
        }

    # If LLM is disabled or API key is missing, use keyword fallback directly
    if not use_llm or not GROQ_API_KEY:
        if not GROQ_API_KEY and use_llm:
            logger.debug("GROQ_API_KEY not found in environment. Falling back to keyword heuristics.")
        return classify_by_keywords(query)

    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage
        
        logger.debug(f"Classifying query intent via Groq LLM ({LLM_MODEL}): '{query}'...")
        llm = ChatGroq(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            groq_api_key=GROQ_API_KEY,
            max_tokens=150,
        )
        
        prompt_text = INTENT_CLASSIFICATION_PROMPT.format(user_query=query)
        response = llm.invoke([HumanMessage(content=prompt_text)])
        content_str = response.content.strip()
        
        # Extract JSON from response (handling potential markdown code blocks)
        json_match = re.search(r"\{.*?\}", content_str, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            intent = str(data.get("intent", "")).upper()
            reason = str(data.get("reason", "Classified by Groq LLM."))
            
            if intent in ("FACTUAL", "ADVISORY"):
                logger.info(f"LLM classified '{query}' as {intent} (Reason: {reason})")
                return {
                    "intent": intent,
                    "confidence": 0.98,
                    "reason": reason,
                    "method": "llm",
                }
        
        logger.warning(f"Could not parse valid JSON from LLM response: '{content_str}'. Falling back to keywords.")
        return classify_by_keywords(query)

    except Exception as e:
        logger.warning(f"LLM intent classification failed ({str(e)}). Falling back to keyword heuristics.")
        return classify_by_keywords(query)


if __name__ == "__main__":
    test_queries = [
        "What is the expense ratio of HDFC Nifty 50 Index Fund?",
        "Should I invest my life savings in HDFC Small Cap Fund?",
        "Which fund is better: HDFC BSE Sensex or Nifty 50 Index?",
        "Who is the fund manager of HDFC Childrens Fund?",
        "Is it a good time to buy HDFC Gold ETF?",
        "What is the exit load if I redeem before 1 year?",
    ]
    
    print("=== Testing Intent Classifier Module ===")
    for q in test_queries:
        res = classify_intent(q, use_llm=False)  # Test keyword fallback first
        print(f"\nQuery:  \"{q}\"")
        print(f"Result: {res['intent']} (Conf: {res['confidence']} | Method: {res['method']})")
        print(f"Reason: {res['reason']}")
