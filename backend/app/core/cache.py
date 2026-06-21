"""
cache.py

AIVOP Redis Cache Layer.
Provides high-performance TTL caching for project resources.
Gracefully falls back to a thread-safe in-memory cache if Redis is unavailable.
Tracks cache hit and miss performance metrics.
"""

import json
import os
import logging
import time
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Try to import redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Global Metrics Counter
class CacheMetrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def record_hit(self):
        with self._lock:
            self.hits += 1

    def record_miss(self):
        with self._lock:
            self.misses += 1

    def get_and_reset(self):
        with self._lock:
            h, m = self.hits, self.misses
            self.hits = 0
            self.misses = 0
            return h, m

cache_metrics = CacheMetrics()

# Thread-safe In-Memory fallback cache
class InMemoryCache:
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            val, expiry = entry
            if expiry < time.time():
                del self._cache[key]
                return None
            return val

    def set(self, key: str, val: str, ttl: int):
        with self._lock:
            self._cache[key] = (val, time.time() + ttl)

    def delete(self, key: str):
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def keys_pattern(self, pattern: str) -> list:
        # e.g. "project:123:*" -> starts with "project:123:"
        prefix = pattern.rstrip("*")
        with self._lock:
            return [k for k in self._cache.keys() if k.startswith(prefix)]

in_memory_cache = InMemoryCache()

# Initialize Redis client
redis_client = None
if REDIS_AVAILABLE:
    try:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_url = os.getenv("REDIS_URL", f"redis://{redis_host}:{redis_port}/0")
        
        # Connect to Redis
        redis_client = redis.Redis.from_url(
            redis_url, 
            socket_connect_timeout=2.0, 
            socket_timeout=2.0,
            decode_responses=True
        )
        # Test connection
        redis_client.ping()
        logger.info(f"Connected to Redis successfully at {redis_url}")
    except Exception as e:
        logger.warning(f"Redis not available, falling back to in-memory caching. Error: {e}")
        redis_client = None
else:
    logger.info("redis-py client not installed. Falling back to in-memory caching.")


def _get_redis() -> Optional[Any]:
    global redis_client
    if not redis_client:
        return None
    try:
        redis_client.ping()
        return redis_client
    except Exception:
        logger.warning("Redis ping failed, fallback to in-memory cache for this request.")
        return None


def get_cached_data(project_id: str, resource: str) -> Optional[Any]:
    """Retrieves JSON-deserialized data from cache."""
    key = f"project:{project_id}:{resource}"
    client = _get_redis()
    
    try:
        if client:
            val = client.get(key)
        else:
            val = in_memory_cache.get(key)
            
        if val:
            cache_metrics.record_hit()
            return json.loads(val)
    except Exception as e:
        logger.error(f"Error reading from cache key {key}: {e}")
        
    cache_metrics.record_miss()
    return None


def set_cached_data(project_id: str, resource: str, data: Any, ttl: int = 3600):
    """Serializes and saves data to cache with TTL (default 1 hour)."""
    key = f"project:{project_id}:{resource}"
    client = _get_redis()
    
    try:
        val = json.dumps(data)
        if client:
            client.set(key, val, ex=ttl)
        else:
            in_memory_cache.set(key, val, ttl)
    except Exception as e:
        logger.error(f"Error writing to cache key {key}: {e}")


def invalidate_project_cache(project_id: str):
    """Invalidates all cached keys belonging to the given project."""
    pattern = f"project:{project_id}:*"
    logger.info(f"Invalidating cache for project {project_id}...")
    client = _get_redis()
    
    try:
        if client:
            # Find and delete keys using pattern
            keys = client.keys(pattern)
            if keys:
                client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} Redis cache keys for project {project_id}")
        else:
            keys = in_memory_cache.keys_pattern(pattern)
            for k in keys:
                in_memory_cache.delete(k)
            logger.info(f"Invalidated {len(keys)} in-memory cache keys for project {project_id}")
    except Exception as e:
        logger.error(f"Error invalidating cache for project {project_id}: {e}")
