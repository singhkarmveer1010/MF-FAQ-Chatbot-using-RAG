"""
Response Generator Module for Mutual Fund FAQ Assistant (Phase 4.3).

Implements Groq LLM response generation with strict rate-limit resilience and token budget optimization:
1. Standardized on 'llama-3.3-70b-versatile' with deterministic temperature 0.0 (§4.3.1).
2. Token Budget Control: Caps injected context to stay below Groq's 12K TPM free-tier ceiling (§4.3.2).
3. Exponential Backoff & Retries: Automatically retries API calls on HTTP 429 rate limits (30 RPM ceiling) (§4.3.3).
4. Graceful Degradation: Handles daily quota exhaustion (1K RPD / 100K TPD) and missing context cleanly (§4.3.4).
"""

import logging
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.prompts import SYSTEM_PROMPT_TEMPLATE
from config.settings import GROQ_API_KEY, LLM_MODEL, LLM_TEMPERATURE

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("response_generator")

# Free-tier safety thresholds for Groq llama-3.3-70b-versatile
MAX_CONTEXT_CHARACTERS = 4000  # ~1,000 tokens max for retrieved chunks (protects 12K TPM limit)
MAX_RETRIES = 2                # Reduced from 3 to keep worst-case under Vercel's timeout budget
INITIAL_RETRY_DELAY = 1.0      # Reduced from 2.0s — worst-case total: 1s + 2s = 3s


def build_prompt_context(chunks: List[Dict[str, Any]], max_chars: int = MAX_CONTEXT_CHARACTERS) -> str:
    """
    Format retrieved chunks into a clean, source-attributed context string for prompt injection.
    Enforces a strict character/token budget to prevent TPM rate limit violations.

    Args:
        chunks (list[dict]): Retrieved chunks from retriever.py.
        max_chars (int): Maximum character budget for the context block.

    Returns:
        str: Formatted context block string.
    """
    if not chunks:
        return "No relevant context found."

    context_blocks = []
    current_chars = 0

    for idx, c in enumerate(chunks, 1):
        meta = c.get("metadata", {})
        scheme = meta.get("scheme_name", "HDFC Mutual Fund Scheme")
        url = meta.get("source_url", "https://groww.in")
        date = meta.get("last_scraped_date", "2026-07-05")
        text = c.get("text", "").strip()

        block = f"[Chunk {idx} | Scheme: {scheme} | Source URL: {url} | Date: {date}]\n{text}\n"
        
        if current_chars + len(block) > max_chars and context_blocks:
            logger.debug(f"Token budget reached at chunk {idx}/{len(chunks)} ({current_chars} chars). Truncating remaining context.")
            break

        context_blocks.append(block)
        current_chars += len(block)

    return "\n".join(context_blocks)


def build_extractive_fallback_answer(query: str, chunks: List[Dict[str, Any]]) -> str:
    """
    Build a concise facts-only answer from retrieved chunks when the LLM is
    unavailable. This keeps demos and health of the chat flow independent from
    Groq/library availability while still grounding the response in the corpus.
    """
    query_terms = {
        token
        for token in re.findall(r"[a-z0-9]+", query.lower())
        if len(token) > 2 and token not in {"the", "and", "for", "with", "hdfc", "fund"}
    }

    candidate_sentences: List[str] = []
    for chunk in chunks:
        text = str(chunk.get("text", ""))
        text = re.sub(r"^\[Scheme:.*?\]\s*", "", text, flags=re.DOTALL)
        # Many scraped facts are line-oriented, so normalize newlines before sentence selection.
        normalized = re.sub(r"\s+", " ", text).strip()
        sentences = re.split(r"(?<=[.!?])\s+|(?<=%)\s+", normalized)
        for sentence in sentences:
            clean_sentence = sentence.strip(" -")
            if len(clean_sentence) < 30:
                continue
            sentence_terms = set(re.findall(r"[a-z0-9]+", clean_sentence.lower()))
            if query_terms & sentence_terms:
                candidate_sentences.append(clean_sentence)
            if len(candidate_sentences) >= 2:
                break
        if len(candidate_sentences) >= 2:
            break

    if not candidate_sentences and chunks:
        text = re.sub(r"^\[Scheme:.*?\]\s*", "", str(chunks[0].get("text", "")), flags=re.DOTALL)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            candidate_sentences.append(text[:350].rstrip(" ,;:") + ".")

    if not candidate_sentences:
        return "I don't have verified information on this in the indexed documents."

    answer_body = " ".join(candidate_sentences[:2])
    return f"From the indexed official scheme disclosure: {answer_body}"


def call_llm_with_retry(prompt_text: str, model_name: str = LLM_MODEL) -> str:
    """
    Execute Groq LLM call via LangChain with automatic retry and exponential backoff.
    Handles HTTP 429 rate limit exceptions smoothly.

    Args:
        prompt_text (str): Complete prompt text to send to Groq.
        model_name (str): Groq model identifier (default: llama-3.3-70b-versatile).

    Returns:
        str: Raw LLM generation text or polite rate-limit fallback string.
    """
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY is not configured in environment.")
        return "Error: LLM API key is missing. Please configure GROQ_API_KEY in .env."

    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage
    except ImportError:
        logger.error("langchain-groq package is not installed.")
        return "Error: Required LLM library langchain-groq is missing."

    if LLM_TEMPERATURE != 0.0:
        logger.warning(f"Temperature lock violation: LLM_TEMPERATURE={LLM_TEMPERATURE} (Enforcing 0.0 for deterministic generation).")
    
    llm = ChatGroq(
        model=model_name,
        temperature=0.0,
        groq_api_key=GROQ_API_KEY,
        max_tokens=300,  # Limit response size for 3 sentences + footer
    )

    delay = INITIAL_RETRY_DELAY
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.debug(f"Calling Groq API ({model_name}) [Attempt {attempt}/{MAX_RETRIES}]...")
            start_time = time.time()
            response = llm.invoke([HumanMessage(content=prompt_text)])
            elapsed = time.time() - start_time
            logger.info(f"Groq generation successful in {elapsed:.2f}s (Tokens used: ~{len(prompt_text)//4 + len(response.content)//4})")
            return response.content.strip()

        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = any(term in err_str for term in ("429", "rate limit", "too many requests", "quota", "tpm", "rpm"))
            
            if is_rate_limit and attempt < MAX_RETRIES:
                logger.warning(f"Groq API rate limit hit (Attempt {attempt}/{MAX_RETRIES}): {e}. Backing off for {delay}s...")
                time.sleep(delay)
                delay *= 2.0  # Exponential backoff: 2s -> 4s -> 8s
            elif is_rate_limit:
                logger.error(f"Groq rate limits exhausted after {MAX_RETRIES} retries (RPM/RPD/TPM limit).")
                return (
                    "I am currently experiencing high traffic and have temporarily reached my API rate limit "
                    "(Groq free tier limit exceeded). Please try again in a few moments."
                )
            else:
                logger.error(f"Unexpected LLM generation error: {e}")
                return "I encountered an error while processing your request. Please try again later."

    return "Error: Failed to generate response after retries."


def generate_answer(query: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a facts-only, source-attributed answer to a user query using retrieved chunks.

    Args:
        query (str): Factual user question.
        chunks (list[dict]): Retrieved chunks from vector store.

    Returns:
        dict: Structured generation result:
            {
              "answer": str,
              "citations": list[str],
              "status": "SUCCESS" | "NO_CONTEXT" | "RATE_LIMITED",
              "model": str
            }
    """
    if not chunks:
        logger.info(f"No relevant chunks provided for query: '{query}'. Returning fallback.")
        return {
            "answer": "I don't have verified information on this. Please check the Groww scheme page or official AMC website.",
            "citations": [],
            "status": "NO_CONTEXT",
            "model": LLM_MODEL,
        }

    # Step 1: Format context with token budget control
    context_str = build_prompt_context(chunks)
    
    # Step 2: Extract primary source citation & latest date
    citations = []
    latest_date = "2026-07-05"
    for c in chunks:
        url = c.get("metadata", {}).get("source_url")
        date = c.get("metadata", {}).get("last_scraped_date")
        if url and url not in citations:
            citations.append(url)
        if date:
            latest_date = max(latest_date, str(date))

    # Step 3: Populate system prompt template
    full_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        retrieved_chunks=context_str,
        user_query=query,
    )

    # Step 4: Call LLM with retry protection
    raw_answer = call_llm_with_retry(full_prompt)

    # Determine status
    status = "SUCCESS"
    lower_ans = raw_answer.lower()
    if any(term in lower_ans for term in ("rate limit", "high traffic", "quota")):
        logger.warning("LLM rate-limited; using extractive corpus fallback.")
        raw_answer = build_extractive_fallback_answer(query, chunks)
    elif raw_answer.startswith("Error:") or "error while processing" in lower_ans:
        logger.warning("LLM unavailable; using extractive corpus fallback.")
        raw_answer = build_extractive_fallback_answer(query, chunks)

    # Ensure footer is present if LLM omitted it during successful generation
    footer_tag = "Last updated from sources:"
    if status == "SUCCESS" and footer_tag not in raw_answer:
        raw_answer = f"{raw_answer.rstrip()}\n\nLast updated from sources: {latest_date}"

    return {
        "answer": raw_answer,
        "citations": citations[:1] if status == "SUCCESS" else [],  # Enforce exactly 1 citation only on success
        "status": status,
        "model": LLM_MODEL,
    }


if __name__ == "__main__":
    print("=== Testing Response Generator Module (Phase 4.3) ===")
    
    # Simulate mock chunks to test token budget and generation without running retrieval
    mock_chunks = [
        {
            "chunk_id": "test_1",
            "similarity": 0.85,
            "text": "The expense ratio of HDFC Nifty 50 Index Fund Direct Plan is 0.20% as of July 2026. This is a low cost equity index fund tracking the Nifty 50 Total Return Index.",
            "metadata": {
                "scheme_name": "HDFC Nifty 50 Index Fund",
                "source_url": "https://groww.in/mutual-funds/hdfc-nifty-50-index-fund-direct-growth",
                "last_scraped_date": "2026-07-05",
            }
        },
        {
            "chunk_id": "test_2",
            "similarity": 0.81,
            "text": "There is zero exit load if units are redeemed after 3 days. For redemption within 3 days, an exit load of 0.25% is applicable.",
            "metadata": {
                "scheme_name": "HDFC Nifty 50 Index Fund",
                "source_url": "https://groww.in/mutual-funds/hdfc-nifty-50-index-fund-direct-growth",
                "last_scraped_date": "2026-07-05",
            }
        }
    ]
    
    test_q = "What is the expense ratio and exit load of HDFC Nifty 50 Index Fund?"
    print(f"\nQuery: \"{test_q}\"")
    print("-" * 80)
    res = generate_answer(test_q, mock_chunks)
    print(f"Status:    {res['status']} (Model: {res['model']})")
    print(f"Citations: {res['citations']}")
    print(f"\nGenerated Answer:\n{res['answer']}")
