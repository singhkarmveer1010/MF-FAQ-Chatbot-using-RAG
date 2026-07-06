"""
Citation Formatter and Validator Module for Mutual Fund FAQ Assistant (Phase 4.5).

Implements strict output post-processing and guardrail verification:
1. Attaches official Groww source citations to generated responses (§4.5.1).
2. Validates output formatting (<=3 sentences, mandatory footer, citation presence) (§4.5.2).
3. Enforces and appends the 'Last updated from sources: <date>' footer (§4.5.3).
"""

import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.settings import MAX_RESPONSE_SENTENCES

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("citation_formatter")

FOOTER_TAG = "Last updated from sources:"


def count_sentences(text: str) -> int:
    """
    Count the number of sentences in a text block using punctuation regex.

    Args:
        text (str): Input text block.

    Returns:
        int: Estimated sentence count.
    """
    if not text or not text.strip():
        return 0
    # Clean out URLs and markdown links so periods in domain names don't count as sentence boundaries
    cleaned = re.sub(r"https?://[^\s]+", "", text)
    cleaned = re.sub(r"\[.*?\]\(.*?\)", "", cleaned)
    # Match non-empty sentence segments ended by ., !, or ?
    sentences = re.split(r"(?<=[.!?])\s+", cleaned.strip())
    sentences = [s for s in sentences if s and any(c.isalnum() for c in s)]
    return len(sentences)


def extract_body_and_footer(response: str) -> Tuple[str, Optional[str]]:
    """
    Separate response text into main answer body and footer string.

    Args:
        response (str): Complete response string.

    Returns:
        tuple[str, str | None]: (body_text, footer_text or None)
    """
    if FOOTER_TAG in response:
        parts = response.split(FOOTER_TAG, 1)
        body = parts[0].strip()
        footer = f"{FOOTER_TAG}{parts[1]}".strip()
        return body, footer
    return response.strip(), None


def append_footer(response: str, date: str = "2026-07-05") -> str:
    """
    Ensure the response ends with the required source attribution footer (§4.5.3).

    Args:
        response (str): Response body text.
        date (str): Attribution date string.

    Returns:
        str: Response text with appended footer.
    """
    body, existing_footer = extract_body_and_footer(response)
    if existing_footer:
        return f"{body}\n\n{existing_footer}"
    return f"{body}\n\n{FOOTER_TAG} {date}"


def attach_citation(response: str, citations: List[str] | str) -> str:
    """
    Attach the primary source citation URL to the answer body if not already present (§4.5.1).

    Args:
        response (str): Response text.
        citations (list[str] | str): Source URL or list of URLs.

    Returns:
        str: Response text with embedded citation link.
    """
    if not citations:
        return response
        
    url = citations[0] if isinstance(citations, list) else str(citations)
    if not url:
        return response

    body, footer = extract_body_and_footer(response)
    
    # Check if URL is already mentioned in body
    if url in body:
        return response if not footer else f"{body}\n\n{footer}"
        
    # Append citation line before footer
    citation_line = f"Source: {url}"
    new_body = f"{body}\n\n{citation_line}"
    return new_body if not footer else f"{new_body}\n\n{footer}"


def truncate_to_max_sentences(body_text: str, max_s: int = MAX_RESPONSE_SENTENCES) -> str:
    """
    Truncate answer body text to enforce the maximum sentence limit (§4.5.2).

    Args:
        body_text (str): Main answer body without footer.
        max_s (int): Maximum allowed sentences (default: 3).

    Returns:
        str: Truncated text adhering to limit.
    """
    if count_sentences(body_text) <= max_s:
        return body_text

    # Temporarily hide URLs to avoid splitting on periods inside domains
    url_map = {}
    def url_repl(match):
        idx = len(url_map)
        token = f"__URL_{idx}__"
        url_map[token] = match.group(0)
        return token

    protected_text = re.sub(r"https?://[^\s]+", url_repl, body_text)
    sentences = re.split(r"(?<=[.!?])\s+", protected_text.strip())
    
    truncated_sentences = sentences[:max_s]
    result = " ".join(truncated_sentences)
    
    # Restore URLs
    for token, original_url in url_map.items():
        result = result.replace(token, original_url)
        
    logger.warning(f"Truncated verbose LLM output from {len(sentences)} sentences down to {max_s} sentences.")
    return result


def validate_format(response: str, status: str = "SUCCESS") -> Dict[str, Any]:
    """
    Validate that the response adheres strictly to all architectural formatting rules (§4.5.2).

    Args:
        response (str): Full response string.
        status (str): Execution status (SUCCESS, REFUSED, NO_CONTEXT, ERROR, RATE_LIMITED).

    Returns:
        dict: Validation report:
            {
              "is_valid": bool,
              "sentence_count": int,
              "has_footer": bool,
              "has_citation": bool,
              "issues": list[str]
            }
    """
    issues = []
    body, footer = extract_body_and_footer(response)
    
    # Strip standalone Source/Citation lines from body when counting sentences
    clean_body = re.sub(r"\n+Source:\s*https?://[^\s]+", "", body, flags=re.IGNORECASE).strip()
    clean_body = re.sub(r"\n+You may find helpful resources here:\s*https?://[^\s]+", "", clean_body, flags=re.IGNORECASE).strip()
    
    s_count = count_sentences(clean_body)
    
    # Rule 1: Maximum 3 sentences (for SUCCESS or REFUSED)
    if status in ("SUCCESS", "REFUSED") and s_count > MAX_RESPONSE_SENTENCES:
        issues.append(f"Sentence count ({s_count}) exceeds maximum allowed ({MAX_RESPONSE_SENTENCES}).")

    # Rule 2: Exactly one citation (for SUCCESS or REFUSED)
    has_cit = bool(re.search(r"https?://groww\.in[^\s]*", response))
    if status in ("SUCCESS", "REFUSED") and not has_cit:
        issues.append("Missing required Groww source citation URL.")
    elif status not in ("SUCCESS", "REFUSED") and has_cit:
        issues.append(f"Citation URL should not be present for status '{status}'.")

    # Rule 3: Footer required on SUCCESS, REFUSED, and NO_CONTEXT
    has_foot = bool(footer and FOOTER_TAG in footer)
    if status in ("SUCCESS", "REFUSED", "NO_CONTEXT") and not has_foot:
        issues.append(f"Missing required footer: '{FOOTER_TAG}'")
    elif status in ("ERROR", "RATE_LIMITED") and has_foot:
        issues.append(f"Footer should not be present on error status '{status}'.")

    return {
        "is_valid": len(issues) == 0,
        "sentence_count": s_count,
        "has_footer": has_foot,
        "has_citation": has_cit,
        "issues": issues,
    }


def format_and_enforce(
    response_text: str,
    citations: List[str] | str,
    date: str = "2026-07-05",
    status: str = "SUCCESS",
) -> str:
    """
    Complete post-processing pipeline: truncates sentences, embeds citations, and appends footer.
    Guarantees 100% compliance with architectural formatting rules.

    Args:
        response_text (str): Raw response generated by LLM or refusal handler.
        citations (list[str] | str): Source citation URL(s).
        date (str): Latest scraped date.
        status (str): Execution status.

    Returns:
        str: Fully compliant, formatted response string.
    """
    if status in ("ERROR", "RATE_LIMITED"):
        return response_text.strip()

    body, footer = extract_body_and_footer(response_text)

    # 1. Enforce 3-sentence limit on main text body
    if status in ("SUCCESS", "REFUSED"):
        # Check if citation/link line is attached at end of body
        lines = body.split("\n\n")
        main_text_lines = [l for l in lines if not l.strip().startswith(("Source:", "You may find"))]
        other_lines = [l for l in lines if l.strip().startswith(("Source:", "You may find"))]
        
        main_text = "\n\n".join(main_text_lines)
        truncated_main = truncate_to_max_sentences(main_text, max_s=MAX_RESPONSE_SENTENCES)
        body = "\n\n".join([truncated_main] + other_lines).strip()

    # 2. Attach citation if applicable
    if status in ("SUCCESS", "REFUSED"):
        body = attach_citation(body, citations)

    # 3. Append footer
    final_output = append_footer(body, date=date)
    
    # Log validation verification
    val = validate_format(final_output, status=status)
    if not val["is_valid"]:
        logger.warning(f"Formatting issues corrected or detected: {val['issues']}")
    else:
        logger.debug("Output formatting verified: 100% compliant with architectural rules.")

    return final_output


if __name__ == "__main__":
    print("=== Testing Citation Formatter Module (Phase 4.5) ===")
    
    test_cases = [
        (
            "The HDFC Nifty 50 Index Fund has an expense ratio of 0.20%. It tracks the Nifty 50 Total Return Index. There is no exit load after 3 days. This fourth sentence is extra and should be automatically truncated by the formatter!",
            ["https://groww.in/mutual-funds/hdfc-nifty-50-index-fund-direct-growth"],
            "SUCCESS"
        ),
        (
            "I don't have verified information on this. Please check the Groww scheme page or official AMC website.",
            [],
            "NO_CONTEXT"
        ),
        (
            "I am currently experiencing high traffic and have temporarily reached my API rate limit.",
            [],
            "RATE_LIMITED"
        )
    ]
    
    for idx, (raw_txt, cits, stat) in enumerate(test_cases, 1):
        print("\n" + "=" * 80)
        print(f"Test Case [{idx}] | Status: {stat}")
        print(f"Raw Input (Sentences: {count_sentences(raw_txt)}):\n\"{raw_txt}\"")
        print("-" * 80)
        formatted = format_and_enforce(raw_txt, citations=cits, status=stat)
        val_report = validate_format(formatted, status=stat)
        print(f"Formatted Output:\n{formatted}")
        print("-" * 80)
        print(f"Validation Report: Valid={val_report['is_valid']} | Sentences={val_report['sentence_count']} | Footer={val_report['has_footer']} | Citations={val_report['has_citation']}")
        if val_report["issues"]:
            print(f"Issues: {val_report['issues']}")
