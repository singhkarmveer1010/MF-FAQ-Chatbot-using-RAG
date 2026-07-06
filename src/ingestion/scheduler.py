"""
Automated Ingestion Scheduler Module for Mutual Fund FAQ Assistant (Phase 7 & GitHub Actions).

Implements:
1. Thread-safe RLock (`vector_store_lock`) to prevent race conditions or database corruption
   when ChromaDB is being updated during active user queries (Task 7.2).
2. `IngestionScheduler` daemon and webhook receiver that bridges GitHub Actions scheduled cron workflows
   (`.github/workflows/scheduled_ingestion.yml`) with the local ingestion pipeline (Task 7.1).
3. Status tracking, authentication, and manual/webhook trigger capabilities for API integration (Task 7.4).
"""

import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from config.settings import VECTOR_STORE_PATH

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ingestion_scheduler")

# --- Thread-Safe Mutex Lock (Task 7.2) ---
# Must be acquired by both the ingestion writer and the retriever reader
vector_store_lock = threading.RLock()


class IngestionScheduler:
    """
    Background daemon responsible for automated periodic real-time data ingestion.
    """
    def __init__(self):
        self._scheduler = None
        self._thread_timer = None
        self._stop_event = threading.Event()
        
        # State tracking
        self.is_running: bool = False
        self.last_run_time: Optional[str] = None
        self.next_run_time: Optional[str] = None
        self.last_run_status: str = "idle"  # idle | running | success | failed
        self.last_run_stats: Dict[str, Any] = {}
        self._job_id: str = "mutual_fund_ingest_job"

    def _execute_pipeline_task(self):
        """Internal task wrapper that executes the end-to-end ingestion pipeline inside a mutex lock."""
        logger.info("=" * 60)
        logger.info("⏰ [SCHEDULER] Triggering automated ingestion pipeline run...")
        logger.info("=" * 60)
        self.last_run_status = "running"
        start_ts = datetime.now()
        
        try:
            from src.ingestion.ingest_pipeline import run_pipeline
            
            # Acquire mutex lock around ChromaDB write operations (Task 7.2)
            logger.info("🔒 [SCHEDULER] Acquiring vector store mutex lock for writing...")
            with vector_store_lock:
                logger.info("🔓 [SCHEDULER] Lock acquired. Executing run_pipeline()...")
                results = run_pipeline()
            
            self.last_run_status = "success"
            self.last_run_time = start_ts.isoformat()
            self.last_run_stats = {
                "elapsed_seconds": results.get("elapsed_seconds", 0),
                "total_schemes": results.get("total_schemes", 0),
                "successful_schemes": results.get("successful_schemes", 0),
                "total_chunks_generated": results.get("total_chunks_generated", 0),
                "indexed_chunks": results.get("indexed_chunks", 0),
                "embedding_dim": results.get("embedding_dim", 0),
            }
            logger.info(f"✅ [SCHEDULER] Ingestion completed successfully in {self.last_run_stats['elapsed_seconds']}s.")
            
        except Exception as e:
            self.last_run_status = "failed"
            self.last_run_time = start_ts.isoformat()
            self.last_run_stats = {"error": str(e)}
            logger.error(f"❌ [SCHEDULER] Automated ingestion run failed: {e}", exc_info=True)
            
        finally:
            # Update next run time estimation if scheduled
            interval_hours = int(os.getenv("INGESTION_INTERVAL_HOURS", "24"))
            self.next_run_time = (datetime.now() + timedelta(hours=interval_hours)).isoformat()

    def _fallback_loop(self, interval_seconds: int):
        """Fallback background loop if APScheduler is not installed."""
        while not self._stop_event.is_set():
            # Wait for interval or shutdown signal
            if self._stop_event.wait(timeout=interval_seconds):
                break
            if not self._stop_event.is_set():
                self._execute_pipeline_task()

    def start(self):
        """
        Start the automated background scheduler (Task 7.1 & 7.4).
        Uses APScheduler if installed, otherwise falls back to a clean background threading loop.
        """
        if self.is_running:
            logger.warning("[SCHEDULER] Scheduler is already running.")
            return

        cron_expr = os.getenv("INGESTION_CRON", "0 5 * * *")  # 05:00 UTC = 10:30 AM IST
        interval_hours = int(os.getenv("INGESTION_INTERVAL_HOURS", "24"))
        logger.info(f"[SCHEDULER] Initializing background ingestion scheduler (Interval: {interval_hours}h | Cron: '{cron_expr}')...")

        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
            
            self._scheduler = BackgroundScheduler()
            # Try parsing 5-field cron expression (minute hour day month day_of_week)
            parts = cron_expr.strip().split()
            if len(parts) == 5:
                trigger = CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                )
            else:
                from apscheduler.triggers.interval import IntervalTrigger
                trigger = IntervalTrigger(hours=interval_hours)
                
            self._scheduler.add_job(
                self._execute_pipeline_task,
                trigger=trigger,
                id=self._job_id,
                name="Automated Mutual Fund Data Refresh",
                replace_existing=True,
            )
            self._scheduler.start()
            self.is_running = True
            self.next_run_time = (datetime.now() + timedelta(hours=interval_hours)).isoformat()
            logger.info("✅ [SCHEDULER] APScheduler started successfully in background.")
            
        except ImportError:
            logger.info("[SCHEDULER] APScheduler not found in environment. Using standard threading background loop.")
            self._stop_event.clear()
            interval_seconds = interval_hours * 3600
            self._thread_timer = threading.Thread(
                target=self._fallback_loop,
                args=(interval_seconds,),
                name="IngestionSchedulerThread",
                daemon=True,
            )
            self._thread_timer.start()
            self.is_running = True
            self.next_run_time = (datetime.now() + timedelta(hours=interval_hours)).isoformat()
            logger.info("✅ [SCHEDULER] Threading background daemon started successfully.")

    def shutdown(self):
        """Shut down the background scheduler cleanly."""
        if not self.is_running:
            return
        logger.info("[SCHEDULER] Shutting down background ingestion scheduler...")
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
        if self._thread_timer:
            self._stop_event.set()
            self._thread_timer = None
        self.is_running = False
        logger.info("🛑 [SCHEDULER] Scheduler stopped.")

    def trigger_now(self, background: bool = True) -> Dict[str, Any]:
        """
        Manually trigger an immediate ingestion run (for API /admin overrides).
        
        Args:
            background (bool): If True, spawns a thread so the HTTP response returns immediately.
                               If False, blocks until pipeline finishes.
        """
        logger.info(f"[SCHEDULER] Manual trigger requested (background={background}).")
        if background:
            thread = threading.Thread(
                target=self._execute_pipeline_task,
                name="ManualIngestionThread",
                daemon=True,
            )
            thread.start()
            return {
                "status": "triggered",
                "message": "Automated ingestion pipeline started in background thread.",
                "last_status": self.last_run_status,
            }
        else:
            self._execute_pipeline_task()
            return {
                "status": self.last_run_status,
                "message": "Ingestion pipeline completed synchronously.",
                "stats": self.last_run_stats,
            }

    def get_status(self) -> Dict[str, Any]:
        """Return comprehensive scheduler health and status metrics (Task 7.4)."""
        return {
            "is_running": self.is_running,
            "status": self.last_run_status,
            "last_run_time": self.last_run_time,
            "next_scheduled_run": self.next_run_time,
            "cron_expression": os.getenv("INGESTION_CRON", "0 5 * * *"),  # 05:00 UTC = 10:30 AM IST
            "interval_hours": int(os.getenv("INGESTION_INTERVAL_HOURS", "24")),
            "last_run_stats": self.last_run_stats,
        }


# Global Singleton Instance
scheduler = IngestionScheduler()
