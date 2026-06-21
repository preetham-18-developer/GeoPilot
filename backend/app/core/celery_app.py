"""
celery_app.py

Celery Configuration & Background Worker Layer.
Supports asynchronous analysis execution, progress tracking, and retries.
Gracefully handles missing Celery/Redis dependencies with transparent synchronous fallback.
"""

import os
import time
import logging
import asyncio
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Try to import Celery
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    Celery = None
    CELERY_AVAILABLE = False

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_url = os.getenv("REDIS_URL", f"redis://{redis_host}:{redis_port}/0")

# Task execution metric logger
def _save_task_metric(duration: float):
    try:
        from app.core.supabase import supabase_client
        import psutil
        process = psutil.Process(os.getpid())
        mem_mb = process.memory_info().rss / 1024 / 1024
    except Exception:
        mem_mb = 0.0

    try:
        supabase_client.table("system_metrics").insert({
            "request_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "queue_size": 0,
            "task_execution_time": duration,
            "memory_usage": mem_mb
        }).execute()
    except Exception as ex:
        logger.warning(f"Failed to save Celery task execution time metric: {ex}")

# Helper to run async function in Celery sync worker
def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # Eager execution running in same loop
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()
    else:
        return loop.run_until_complete(coro)


if CELERY_AVAILABLE:
    celery_app = Celery("aivop", broker=redis_url, backend=redis_url)
    
    # Configure Celery settings
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        broker_connection_retry_on_startup=True
    )
    
    # Verify Redis availability
    try:
        import redis
        test_client = redis.Redis.from_url(redis_url, socket_connect_timeout=2.0)
        test_client.ping()
        logger.info("Celery Redis broker connection check passed.")
    except Exception as e:
        logger.warning(f"Celery Redis broker offline. Forcing eager mode execution. Error: {e}")
        celery_app.conf.task_always_eager = True
else:
    logger.info("Celery package not installed. Background tasks will run using local fallback.")
    celery_app = None


# Define standard wrapper task if Celery is available
if CELERY_AVAILABLE:
    @celery_app.task(bind=True, max_retries=3)
    def run_analysis_pipeline_task(self, project_id: str, run_id: str, website_url: str):
        logger.info(f"Celery worker running pipeline run {run_id} for project {project_id}...")
        from app.routers.analysis import execute_bg_analysis
        
        start_time = time.time()
        try:
            self.update_state(state="PROGRESS", meta={"progress": 10, "stage": "crawling"})
            _run_async(execute_bg_analysis(project_id, run_id, website_url))
            
            self.update_state(state="SUCCESS", meta={"progress": 100, "stage": "completed"})
            duration = time.time() - start_time
            _save_task_metric(duration)
            logger.info(f"Celery pipeline execution finished successfully in {duration:.1f}s.")
        except Exception as exc:
            duration = time.time() - start_time
            _save_task_metric(duration)
            logger.error(f"Celery task failed: {exc}. Retrying...")
            try:
                # Retry in 10 seconds
                self.retry(exc=exc, countdown=10)
            except Exception:
                raise exc
else:
    # Dummy mock class for clean import
    class CeleryAppMock:
        def task(self, *args, **kwargs):
            return lambda fn: fn
            
    celery_app = CeleryAppMock()
    run_analysis_pipeline_task = None
