"""
Pydantic Schemas for Mutual Fund FAQ Assistant API (Phase 5.1).

Defines strongly typed request and response contracts for FastAPI endpoints:
1. QueryRequest: Validates input question length and parameters.
2. FactualResponse & RefusalResponse: Typed JSON contracts adhering to §5.2 specification.
3. HealthResponse, SchemesResponse, IngestResponse: System and metadata responses.
"""

from typing import List, Optional, Union
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request schema for POST /api/query endpoint."""
    query: str = Field(..., min_length=3, max_length=500, description="Natural language question about mutual funds")
    use_llm_intent: bool = Field(True, description="Whether to use LLM for intent classification (False for keyword heuristics)")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is the NAV and expense ratio of HDFC Nifty 50 Index Fund?",
                "use_llm_intent": True
            }
        }


class BaseQueryResponse(BaseModel):
    """Base schema sharing mandatory fields across query response types."""
    status: str = Field(..., description="Response status (success, refused, no_context, pii_blocked, rate_limited, error)")
    intent: str = Field(..., description="Classified query intent (FACTUAL, ADVISORY, BLOCKED)")
    answer: str = Field(..., description="Formatted answer text or polite refusal/disclaimer")
    last_updated: str = Field("2026-07-05", description="Latest scraped attribution date")
    disclaimer: str = Field("Facts-only. No investment advice.", description="Mandatory SEBI compliance disclaimer")


class FactualResponse(BaseQueryResponse):
    """Response schema for successful factual queries (§5.2)."""
    status: str = "success"
    intent: str = "FACTUAL"
    source_url: str = Field(..., description="Official Groww source citation URL")


class RefusalResponse(BaseQueryResponse):
    """Response schema for advisory or subjective queries (§5.2)."""
    status: str = "refused"
    intent: str = "ADVISORY"
    educational_link: str = Field(..., description="Official Groww educational resource URL")


class PIIBlockedResponse(BaseModel):
    """Response schema when PII guard blocks the query (§5.6)."""
    status: str = "pii_blocked"
    intent: str = "BLOCKED"
    answer: str = Field(..., description="Security warning explaining why input was blocked")
    disclaimer: str = Field("Facts-only. No investment advice.", description="Mandatory SEBI compliance disclaimer")


class GenericQueryResponse(BaseQueryResponse):
    """Response schema for fallback statuses (no_context, rate_limited, error)."""
    source_url: Optional[str] = None
    educational_link: Optional[str] = None


class HealthResponse(BaseModel):
    """Response schema for GET /api/health endpoint (§5.3)."""
    status: str = "ok"
    version: str = "1.0.0"
    engine: str = "llama-3.3-70b-versatile"


class SchemesResponse(BaseModel):
    """Response schema for GET /api/schemes endpoint (§5.4)."""
    status: str = "success"
    total_count: int = Field(..., description="Total number of supported schemes")
    schemes: List[str] = Field(..., description="List of scheme display names")


class IngestResponse(BaseModel):
    """Response schema for admin POST /api/ingest endpoint (§5.5)."""
    status: str = "success"
    message: str = Field(..., description="Summary of ingestion pipeline execution")
    chunks_count: int = Field(..., description="Number of vector chunks generated and stored")


class SchedulerStatusResponse(BaseModel):
    """Response schema for GET /api/ingest/status endpoint (Phase 7)."""
    status: str = "success"
    is_running: bool = Field(..., description="Whether the background scheduler daemon is active")
    last_run_status: str = Field(..., description="Status of the last automated ingestion run (idle, running, success, failed)")
    last_run_time: Optional[str] = Field(None, description="ISO timestamp of last execution")
    next_scheduled_run: Optional[str] = Field(None, description="ISO timestamp of next scheduled execution")
    cron_expression: str = Field(..., description="Configured cron trigger schedule")
    interval_hours: int = Field(..., description="Configured interval loop in hours")
    last_run_stats: dict = Field(..., description="Execution summary statistics from the last ingestion run")
