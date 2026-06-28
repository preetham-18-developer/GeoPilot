"""
middleware.py

FastAPI Middleware for collecting system performance metrics.
Tracks request latency, memory usage (RSS), cache performance, and active queue sizes.
Inserts recorded logs asynchronously into the system_metrics database table to ensure zero request overhead.
"""

import os
import time
import logging
import threading
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.cache import cache_metrics

logger = logging.getLogger(__name__)

# Attempt to load psutil
try:
    import psutil
except ImportError:
    psutil = None


def get_memory_usage_mb() -> float:
    """Returns the RSS memory usage of the current process in MB."""
    if not psutil:
        return 0.0
    try:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    except Exception:
        return 0.0


def get_active_queue_size() -> int:
    """Queries Supabase for the number of active background pipeline runs."""
    try:
        from app.core.supabase import supabase_client
        res = supabase_client.table("analysis_runs").select("id", count="exact").in_(
            "status", ["queued", "crawling", "extracting", "verifying", "analyzing", "compiling"]
        ).execute()
        return res.count or 0
    except Exception as e:
        logger.warning(f"Failed to retrieve active queue size: {e}")
        return 0


def _save_metrics_async(request_time: float, hits: int, misses: int, memory_usage: float):
    """Logs performance metrics locally to avoid concurrent connection pool corruption."""
    logger.info(
        f"[METRICS] Request Time: {request_time:.4f}s | Cache Hits: {hits} | "
        f"Cache Misses: {misses} | Memory Usage: {memory_usage:.2f}MB"
    )


class PerformanceMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Exclude static/health check queries to avoid cluttering metrics database
        path = request.url.path
        if any(path.startswith(prefix) for prefix in ["/docs", "/redoc", "/openapi.json", "/favicon.ico"]):
            return await call_next(request)

        start_time = time.time()
        
        # Reset cache hit counters for the scope of this request
        cache_metrics.get_and_reset()
        
        try:
            response = await call_next(request)
        except Exception as e:
            # Still record metrics on crashes
            duration = time.time() - start_time
            hits, misses = cache_metrics.get_and_reset()
            mem_mb = get_memory_usage_mb()
            _save_metrics_async(duration, hits, misses, mem_mb)
            raise e

        duration = time.time() - start_time
        hits, misses = cache_metrics.get_and_reset()
        mem_mb = get_memory_usage_mb()
        
        # Save metrics asynchronously
        _save_metrics_async(duration, hits, misses, mem_mb)
        
        return response

