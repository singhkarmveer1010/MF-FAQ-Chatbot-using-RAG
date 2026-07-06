"""
RAG Pipeline Orchestration Module (Phase 4 Complete Integration).

Unifies all Phase 4 modules into a seamless, end-to-end query processing engine:
1. Intent Classification (§4.1): Gates queries as FACTUAL or ADVISORY.
2. Retrieval Engine (§4.2): Fetches top-k semantic chunks from ChromaDB with smart metadata scoping.
3. Response Generation (§4.3): Calls Groq llama-3.3-70b-versatile with token budget control and retry resilience.
4. Refusal Handling (§4.4): Polite refusal responses with Groww educational links for advisory queries.
5. Citation Formatter (§4.5): Enforces 3-sentence limit, single citation rule, and mandatory footer attribution.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.generation.citation_formatter import format_and_enforce, validate_format
from src.generation.intent_classifier import classify_intent
from src.generation.refusal_handler import generate_refusal
from src.generation.response_generator import generate_answer
from src.retrieval.retriever import retrieve

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("rag_pipeline")


def answer_query(query: str, use_llm_intent: bool = True) -> Dict[str, Any]:
    """
    Execute the end-to-end RAG pipeline for a user question.

    Args:
        query (str): Natural language query.
        use_llm_intent (bool): Use LLM for intent classification (default: True).

    Returns:
        dict: Complete structured response dictionary:
            {
              "query": str,
              "intent": "FACTUAL" | "ADVISORY",
              "intent_reason": str,
              "intent_method": str,
              "answer": str,
              "citations": list[str],
              "status": "SUCCESS" | "REFUSED" | "NO_CONTEXT" | "RATE_LIMITED" | "ERROR",
              "model": str,
              "retrieved_chunks_count": int,
              "validation": dict
            }
    """
    logger.info(f"Processing query through RAG pipeline: '{query}'")
    
    # Step 1: Intent Classification (§4.1)
    intent_res = classify_intent(query, use_llm=use_llm_intent)
    intent = intent_res["intent"]
    reason = intent_res.get("reason", "")
    method = intent_res.get("method", "unknown")
    logger.info(f"Gate 1 (Intent): {intent} ({method} | {reason})")

    # Step 2: Route based on intent
    if intent == "ADVISORY":
        # Route to Refusal Handler (§4.4)
        refusal_res = generate_refusal(query, reason=reason)
        raw_ans = refusal_res["answer"]
        cits = refusal_res["citations"]
        stat = refusal_res["status"]
        model = "rule-engine"
        chunks_count = 0
    else:
        # Route to Retrieval & Response Generation (§4.2 & §4.3)
        chunks = retrieve(query)
        chunks_count = len(chunks)
        logger.info(f"Gate 2 (Retrieval): Found {chunks_count} relevant chunks above similarity threshold.")
        
        gen_res = generate_answer(query, chunks)
        raw_ans = gen_res["answer"]
        cits = gen_res["citations"]
        stat = gen_res["status"]
        model = gen_res.get("model", "unknown")

    # Step 3: Citation Formatting & Post-Processing Guardrails (§4.5)
    final_answer = format_and_enforce(
        response_text=raw_ans,
        citations=cits,
        status=stat,
    )
    
    # Verify formatting adherence
    val_report = validate_format(final_answer, status=stat)

    result = {
        "query": query,
        "intent": intent,
        "intent_reason": reason,
        "intent_method": method,
        "answer": final_answer,
        "citations": cits if stat in ("SUCCESS", "REFUSED") else [],
        "status": stat,
        "model": model,
        "retrieved_chunks_count": chunks_count,
        "validation": val_report,
    }
    
    logger.info(f"Pipeline finished with status: {stat} | Valid: {val_report['is_valid']}")
    return result


if __name__ == "__main__":
    print("=== Testing End-to-End RAG Pipeline (Phase 4 Verification) ===")
    
    test_queries = [
        "What is the NAV and expense ratio of HDFC Nifty 50 Index Fund?",
        "Should I invest in HDFC Small Cap Fund or is it too risky?",
        "What is the exit load for HDFC Gold ETF if redeemed early?",
        "Which fund is better: Nifty 50 or BSE Sensex?",
        "Tell me about the fund manager of HDFC Childrens Fund and his educational background.",
    ]
    
    for idx, q in enumerate(test_queries, 1):
        print("\n" + "=" * 80)
        print(f"Test Query [{idx}]: \"{q}\"")
        print("-" * 80)
        
        res = answer_query(q, use_llm_intent=False)  # Using keyword heuristics for quick, reliable test execution
        
        print(f"Status:    {res['status']} | Intent: {res['intent']} ({res['intent_method']})")
        print(f"Model:     {res['model']} | Chunks Retrieved: {res['retrieved_chunks_count']}")
        print(f"Citations: {res['citations']}")
        print(f"Valid:     {res['validation']['is_valid']} (Sentences: {res['validation']['sentence_count']})")
        print("-" * 80)
        safe_ans = res['answer'].encode('ascii', 'replace').decode('ascii') if sys.platform == 'win32' else res['answer']
        print(f"Generated Answer:\n{safe_ans}")
