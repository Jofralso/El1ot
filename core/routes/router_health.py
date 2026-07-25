"""
Health Check Routes

Provides health status endpoints for monitoring and orchestration.
"""

import time
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any
import logging

from core.hardware import get_hardware_info
from core.config import settings
from core.monitoring import get_uptime

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    services: Dict[str, str]


@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    Used by Docker health checks and load balancers.
    """
    services = {"core": "healthy"}

    try:
        import redis.asyncio as redis
        from core.deps import get_redis_url

        client = await redis.from_url(get_redis_url())
        await client.ping()
        services["redis"] = "healthy"
        await client.aclose()
    except Exception:
        services["redis"] = "degraded"

    overall = "healthy" if all(v == "healthy" for v in services.values()) else "degraded"

    return HealthResponse(
        status=overall,
        version=settings.core_port and "0.2.0",
        environment=settings.env,
        services=services,
    )


class DetailedHealthResponse(HealthResponse):
    hardware: Dict[str, Any]
    uptime_seconds: float


@router.get("/detailed", response_model=DetailedHealthResponse)
async def health_detailed():
    """
    Detailed health check with hardware info.
    For debugging and status dashboards.
    """
    hardware_info = get_hardware_info()

    services = {"core": "healthy"}

    try:
        import redis.asyncio as redis
        from core.deps import get_redis_url

        client = await redis.from_url(get_redis_url())
        await client.ping()
        services["redis"] = "healthy"
        await client.aclose()
    except Exception:
        services["redis"] = "degraded"

    overall = "healthy" if all(v == "healthy" for v in services.values()) else "degraded"

    return DetailedHealthResponse(
        status=overall,
        version="0.2.0",
        environment=settings.env,
        services=services,
        hardware=hardware_info,
        uptime_seconds=get_uptime(),
    )
