"""
Application Configuration and Settings

Loads environment variables from .env using python-dotenv and defines typed configuration
constants for the RAG chatbot (LLM provider, embedding model, vector store, retrieval, and API server).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from root project directory if present
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    load_dotenv(override=True)

# --- LLM Provider (Groq) ---
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# --- Model Selection ---
LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

# --- Vector Store ---
VECTOR_STORE_TYPE: str = os.getenv("VECTOR_STORE_TYPE", "chromadb")
VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", str(BASE_DIR / "vectorstore"))

# --- Retrieval Parameters ---
RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "5"))
SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))

# --- Response Parameters ---
MAX_RESPONSE_SENTENCES: int = int(os.getenv("MAX_RESPONSE_SENTENCES", "3"))
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))

# --- Server Configuration ---
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))

# --- Automated Ingestion Scheduler Configuration (Phase 7 & GitHub Actions) ---
INGESTION_CRON: str = os.getenv("INGESTION_CRON", "0 5 * * *")  # 05:00 UTC = 10:30 AM IST
INGESTION_INTERVAL_HOURS: int = int(os.getenv("INGESTION_INTERVAL_HOURS", "24"))
INGEST_ADMIN_TOKEN: str = os.getenv("INGEST_ADMIN_TOKEN", "")

# Ensure vector store directory exists
os.makedirs(VECTOR_STORE_PATH, exist_ok=True)
