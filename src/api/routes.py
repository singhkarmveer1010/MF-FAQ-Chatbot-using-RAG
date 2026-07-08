"""
FastAPI Routes and PII Guard Module for Mutual Fund FAQ Assistant (Phase 5.2 - 5.6).

Implements REST endpoints and security guardrails:
1. PII Detection Guard (§5.6): Regex filtering for PAN, Aadhaar, phone, email, and OTPs.
2. POST /api/query (§5.2): Orchestrates PII verification and end-to-end RAG pipeline execution.
3. GET /api/health (§5.3): Liveness probe returning engine version and status.
4. GET /api/schemes (§5.4): Returns list of supported HDFC Mutual Fund scheme names.
5. POST /api/ingest (§5.5): Admin-only trigger to re-run data ingestion and vector indexing.
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import APIRouter, Header, HTTPException, status
from config.settings import INGEST_ADMIN_TOKEN
from src.api.schemas import (
    FactualResponse,
    GenericQueryResponse,
    HealthResponse,
    IngestResponse,
    PIIBlockedResponse,
    QueryRequest,
    RefusalResponse,
    SchemesResponse,
    SchedulerStatusResponse,
)
from src.retrieval.retriever import check_unsupported_scheme, extract_scheme_filter
from src.generation.rag_pipeline import answer_query
from src.ingestion.scheduler import scheduler

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("api_routes")

router = APIRouter(prefix="/api", tags=["Mutual Fund FAQ RAG Engine"])

# --- PII Regex Guard Patterns (§5.6) ---
PII_PATTERNS = {
    "PAN Card Number": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b"),
    "Aadhaar Number": re.compile(r"\b\d{4}[\-\s]?\d{4}[\-\s]?\d{4}\b"),
    "Indian Phone Number": re.compile(r"\b(\+91[\-\s]?)?[6-9]\d{9}\b"),
    "Email Address": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "Security PIN / OTP": re.compile(r"\b(otp|pin|cvv|pwd|password|secret)\s*[:=-]?\s*\d{4,8}\b", re.IGNORECASE),
}


def detect_pii(text: str) -> Optional[str]:
    """
    Scan user input for Personally Identifiable Information (PII) before processing (§5.6).

    Args:
        text (str): Input query text.

    Returns:
        str | None: Name of detected PII pattern, or None if safe.
    """
    for pii_name, pattern in PII_PATTERNS.items():
        if pattern.search(text):
            logger.warning(f"PII Guard triggered: Detected {pii_name} in query.")
            return pii_name
    return None


@router.get("/health", response_model=HealthResponse, summary="Health Probe Endpoint (§5.3)")
async def get_health():
    """Returns service liveness status and underlying LLM engine version."""
    return HealthResponse(status="ok", version="1.0.0", engine="llama-3.3-70b-versatile")


@router.get("/schemes", response_model=SchemesResponse, summary="List Supported Schemes Endpoint (§5.4)")
async def get_schemes():
    """Returns the list of 10 supported HDFC Mutual Fund scheme names indexed in the system."""
    urls_path = BASE_DIR / "data" / "urls.json"
    schemes = []
    
    if urls_path.exists():
        try:
            with open(urls_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                corpus_list = data.get("corpus", data) if isinstance(data, dict) else data
                if isinstance(corpus_list, list):
                    schemes = [item.get("scheme_name") for item in corpus_list if isinstance(item, dict) and item.get("scheme_name")]
        except Exception as e:
            logger.error(f"Failed to load urls.json: {e}")

    if not schemes:
        # Fallback default 10 scheme list matching exact vector database corpus (§3.1.1)
        schemes = [
            "HDFC Nifty 50 Index Fund",
            "HDFC BSE Sensex Index Fund",
            "HDFC Childrens Fund",
            "HDFC Banking and Financial Services Fund",
            "HDFC Corporate Debt Opportunities Fund",
            "HDFC Gold ETF Fund of Fund",
            "HDFC Nifty Next 50 Index Fund",
            "HDFC Nifty500 Multicap 50:25:25 Index Fund",
            "HDFC Diversified Equity All Cap Active FoF",
            "HDFC Nifty India Digital Index Fund",
        ]

    return SchemesResponse(status="success", total_count=len(schemes), schemes=schemes)


@router.post(
    "/query",
    response_model=Union[FactualResponse, RefusalResponse, PIIBlockedResponse, GenericQueryResponse],
    summary="Main RAG Query Processing Endpoint (§5.2)",
)
async def post_query(request: QueryRequest):
    """
    Executes the complete facts-only RAG pipeline:
    1. PII Regex Verification (§5.6)
    2. Intent Classification (FACTUAL vs. ADVISORY) (§4.1)
    3. Metadata-Aware Retrieval (§4.2)
    4. Groq LLM Response Generation or Refusal Handling (§4.3 & §4.4)
    5. Formatting & Citation Guardrails (§4.5)
    """
    logger.info(f"API Request received: '{request.query}' (LLM Intent: {request.use_llm_intent})")

    # Step 1: PII Guard (§5.6)
    pii_found = detect_pii(request.query)
    if pii_found:
        warning_msg = (
            f"Security Alert: Your query was blocked because it contains potential Personally Identifiable Information "
            f"({pii_found}). Please remove any phone numbers, email addresses, PAN, Aadhaar, or passwords and try again."
        )
        return PIIBlockedResponse(
            status="pii_blocked",
            intent="BLOCKED",
            answer=warning_msg,
            disclaimer="Facts-only. No investment advice.",
        )

    # Step 1.5: Unsupported Scheme Guard
    unsupported_scheme = check_unsupported_scheme(request.query)
    if unsupported_scheme and not extract_scheme_filter(request.query):
        msg = (
            f"We currently do not have verified data for {unsupported_scheme} in our database. "
            f"Our facts-only RAG assistant is currently indexed with 10 specific HDFC schemes (including Nifty 50, Sensex, Gold ETF, Children's Fund, Banking & Financial Services, Corporate Debt Opportunities, Nifty Next 50, Multicap 50:25:25, Diversified Equity All Cap FoF, and India Digital Index). "
            f"Please visit Groww directly for details on other schemes."
        )
        return FactualResponse(
            status="success",
            intent="FACTUAL",
            answer=msg,
            source_url="https://groww.in/mutual-funds/amc/hdfc-mutual-funds",
            last_updated="2026-07-05",
            disclaimer="Facts-only. No investment advice.",
        )

    # Step 2 & 3: Execute Pipeline (§4 Integration)
    try:
        res = answer_query(request.query, use_llm_intent=request.use_llm_intent)
    except Exception as e:
        logger.error(f"Pipeline execution error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal processing error while generating response: {str(e)}")

    stat = res["status"]
    intent = res["intent"]
    ans = res["answer"]
    cits = res["citations"]

    # Step 4: Map to strongly typed Pydantic response models (§5.2)
    if stat == "SUCCESS":
        return FactualResponse(
            status="success",
            intent="FACTUAL",
            answer=ans,
            source_url=cits[0] if cits else "https://groww.in/mutual-funds",
            last_updated="2026-07-05",
            disclaimer="Facts-only. No investment advice.",
        )
    elif stat == "REFUSED":
        return RefusalResponse(
            status="refused",
            intent="ADVISORY",
            answer=ans,
            educational_link=cits[0] if cits else "https://groww.in/blog/category/mutual-funds",
            last_updated="2026-07-05",
            disclaimer="Facts-only. No investment advice.",
        )
    else:
        return GenericQueryResponse(
            status=stat.lower(),
            intent=intent,
            answer=ans,
            source_url=cits[0] if cits else None,
            last_updated="2026-07-05",
            disclaimer="Facts-only. No investment advice.",
        )


@router.post("/ingest", response_model=IngestResponse, summary="Admin Ingestion Trigger Endpoint (§5.5 & Phase 7)")
async def post_ingest(background: bool = True, authorization: Optional[str] = Header(None)):
    """Admin-only endpoint to trigger web scraping, cleaning, chunking, and ChromaDB vector indexing under a mutex lock."""
    if INGEST_ADMIN_TOKEN:
        expected_bearer = f"Bearer {INGEST_ADMIN_TOKEN}"
        if authorization != expected_bearer and authorization != INGEST_ADMIN_TOKEN:
            logger.warning("Unauthorized ingestion trigger attempt blocked.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token for ingestion trigger")

    logger.info(f"Triggering admin ingestion pipeline via API (background={background})...")
    try:
        res = scheduler.trigger_now(background=background)
        stats = res.get("stats", {})
        chunks_cnt = stats.get("total_chunks_generated", 0) if not background else 0
        return IngestResponse(
            status="success",
            message=res.get("message", "Ingestion triggered successfully."),
            chunks_count=chunks_cnt,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingestion pipeline failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to execute ingestion pipeline: {e}")


@router.get("/ingest/status", response_model=SchedulerStatusResponse, summary="Scheduler Status Endpoint (Phase 7)")
async def get_ingest_status():
    """Returns real-time status and execution statistics of the Automated Ingestion Scheduler."""
    status_data = scheduler.get_status()
    return SchedulerStatusResponse(
        status="success",
        is_running=status_data["is_running"],
        last_run_status=status_data["status"],
        last_run_time=status_data["last_run_time"],
        next_scheduled_run=status_data["next_scheduled_run"],
        cron_expression=status_data["cron_expression"],
        interval_hours=status_data["interval_hours"],
        last_run_stats=status_data["last_run_stats"],
    )
