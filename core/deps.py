"""
Dependency Injection for ELIOT Core Service

Provides shared resources (Redis client, etc.) to routes.
"""

import redis.asyncio as redis
import logging
from functools import lru_cache

from core.config import settings

logger = logging.getLogger(__name__)


@lru_cache()
def get_redis_url() -> str:
    """Get Redis connection URL"""
    return f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"


async def get_redis_client():
    """
    Get Redis async client (FastAPI dependency).
    
    Usage:
        @app.get("/endpoint")
        async def my_route(redis_client = Depends(get_redis_client)):
            ...
    """
    try:
        redis_url = get_redis_url()
        client = await redis.from_url(redis_url)
        await client.ping()
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


# Cache for Redis connection (phase 2+ for performance)
_redis_cache = None


async def get_cached_redis_client():
    """Get cached Redis client for better performance"""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = await get_redis_client()
    return _redis_cache
