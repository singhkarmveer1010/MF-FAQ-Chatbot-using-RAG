"""
FastAPI Application Entry Point for Mutual Fund FAQ Assistant (Phase 5.7 & 5.8).

1. Initializes FastAPI application with metadata and auto-generated Swagger documentation (§5.7).
2. Configures CORS middleware to allow cross-origin requests from frontend (§5.8).
3. Pre-warms embedding model and vector store connections during startup lifecycle.
"""

import logging
import os
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import API_HOST, API_PORT
from src.api.routes import router
from src.ingestion.embedder import get_embedding_model
from src.ingestion.scheduler import scheduler

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("api_main")


def _prewarm_model():
    """Background thread: load BGE model and ensure ChromaDB collection is indexed."""
    try:
        logger.info("🔥 [Prewarm] Loading BGE embedding model in background thread...")
        get_embedding_model()
        logger.info("✅ [Prewarm] Embedding model loaded and cached successfully.")
        
        # Verify vector store collection exists and has chunks
        from src.ingestion.embedder import get_vector_store_client, DEFAULT_COLLECTION_NAME, index_all_processed_chunks
        client = get_vector_store_client()
        try:
            col = client.get_collection(DEFAULT_COLLECTION_NAME)
            count = col.count()
            logger.info(f"📊 [Prewarm] Found existing collection '{DEFAULT_COLLECTION_NAME}' with {count} chunks.")
            if count == 0:
                raise ValueError("Collection empty")
        except Exception:
            logger.warning("⚠️ [Prewarm] Vector store collection missing or empty. Auto-indexing now...")
            index_all_processed_chunks()
            logger.info("✅ [Prewarm] Auto-indexing complete!")
    except Exception as e:
        logger.error(f"❌ [Prewarm] Failed during prewarm/auto-index: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle management (§5.7).
    Pre-warms embedding models in a background thread so the server
    starts instantly and passes Railway's healthcheck before the
    model finishes loading. Initializes the Automated Ingestion
    Scheduler (Phase 7) the same way.
    """
    logger.info("=== Starting Mutual Fund FAQ Assistant API Server ===")

    # Non-blocking: pre-warm model in background thread so healthcheck
    # at /api/health passes immediately without waiting for model load.
    prewarm_thread = threading.Thread(target=_prewarm_model, daemon=True, name="ModelPrewarm")
    prewarm_thread.start()

    # Start automated background ingestion scheduler (Phase 7)
    try:
        scheduler.start()
    except Exception as e:
        logger.error(f"Failed to start ingestion scheduler: {e}")

    yield

    logger.info("=== Shutting down API Server ===")
    scheduler.shutdown()


# Initialize FastAPI application
app = FastAPI(
    title="Mutual Fund FAQ Assistant — Facts-Only RAG API",
    description="SEBI-compliant, facts-only RAG chatbot API powered by Groq (llama-3.3-70b-versatile) and ChromaDB.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS Middleware (§5.8)
# ─────────────────────────────────────────────────────────────────────────────
# IMPORTANT: Browsers enforce that allow_credentials=True CANNOT be combined
# with allow_origins=["*"]. We read explicit origins from ALLOWED_ORIGINS env
# var (comma-separated). In production, set this to your Vercel frontend URL.
# Example: ALLOWED_ORIGINS=https://your-app.vercel.app
# ─────────────────────────────────────────────────────────────────────────────
_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
if _raw_origins.strip():
    allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
    # Auto-include common Vercel preview deployment patterns
    _vercel_patterns = [
        "https://*.vercel.app",
    ]
    # Also add localhost origins for development convenience
    _dev_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]
    for origin in _dev_origins:
        if origin not in allowed_origins:
            allowed_origins.append(origin)
    allow_credentials = True
    allow_origin_regex = r"https://.*\.vercel\.app"
else:
    # Development fallback — allow all origins without credentials
    allowed_origins = ["*"]
    allow_credentials = False
    allow_origin_regex = None

logger.info(f"CORS configured: origins={allowed_origins}, credentials={allow_credentials}")

cors_kwargs = dict(
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)
if allow_origin_regex:
    cors_kwargs["allow_origin_regex"] = allow_origin_regex

app.add_middleware(CORSMiddleware, **cors_kwargs)

# Include API Router
app.include_router(router)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Mount static frontend files (§6)
ui_dir = BASE_DIR / "src" / "ui"
if ui_dir.exists():
    app.mount("/static", StaticFiles(directory=str(ui_dir)), name="static")


@app.get("/", summary="Serve Frontend Chat Interface (§6)")
async def root():
    """Serve the Groww-inspired interactive RAG chat frontend UI."""
    index_file = ui_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Welcome to Mutual Fund FAQ Assistant API. Access interactive documentation at /docs"}


@app.get("/ui", summary="Serve Frontend Chat Interface")
async def get_ui():
    """Alias route to serve the frontend UI."""
    return await root()


@app.get("/health", summary="Root Health Probe Endpoint")
@app.head("/health")
async def root_health():
    """Root health endpoint alias for deployment probes."""
    return {"status": "ok", "version": "1.0.0", "engine": "llama-3.3-70b-versatile"}



if __name__ == "__main__":
    import uvicorn
    logger.info(f"Launching Uvicorn server on http://{API_HOST}:{API_PORT} ...")
    uvicorn.run("src.api.main:app", host=API_HOST, port=API_PORT, reload=True)
