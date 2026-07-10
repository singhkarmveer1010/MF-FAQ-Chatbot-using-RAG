"""Ingestion package.

Keep this package initializer intentionally lightweight. Importing
``src.ingestion.embedder`` should not also import the scraper, chunker, and full
pipeline, because the FastAPI query path only needs vector-store helpers at
startup. Eager imports here make the deployed API fail to boot whenever an
offline ingestion-only dependency is unavailable or slow to import.
"""

__all__ = [
    "chunker",
    "embedder",
    "ingest_pipeline",
    "scheduler",
    "scraper",
]

