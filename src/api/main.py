"""
FastAPI Application Entry Point for Mutual Fund FAQ Assistant (Phase 5.7 & 5.8).

1. Initializes FastAPI application with metadata and auto-generated Swagger documentation (§5.7).
2. Configures CORS middleware to allow cross-origin requests from frontend (§5.8).
3. Pre-warms embedding model and vector store connections during startup lifecycle.
"""

import logging
import sys
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle management (§5.7).
    Pre-warms embedding models, checks ChromaDB persistent collection,
    and initializes the Automated Ingestion Scheduler (Phase 7).
    """
    logger.info("=== Starting Mutual Fund FAQ Assistant API Server ===")
    logger.info("Pre-warming BGE embedding model into memory cache...")
    try:
        get_embedding_model()
        logger.info("Embedding model pre-warmed successfully. Ready for instant query processing!")
    except Exception as e:
        logger.error(f"Failed to pre-warm embedding model: {e}")

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all frontend origins during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Launching Uvicorn server on http://{API_HOST}:{API_PORT} ...")
    uvicorn.run("src.api.main:app", host=API_HOST, port=API_PORT, reload=True)
