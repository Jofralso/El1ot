"""
System Information Routes

Provides system metrics and status information.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any
import psutil
import logging

from core.hardware import get_hardware_info
from core.deps import get_redis_client

router = APIRouter(prefix="/system", tags=["system"])
logger = logging.getLogger(__name__)


class SystemMetricsResponse(BaseModel):
    """System metrics response"""
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    disk_percent: float
    disk_available_gb: float


class SystemInfoResponse(BaseModel):
    """System information response"""
    hardware: Dict[str, Any]
    metrics: SystemMetricsResponse


@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_metrics():
    """
    Get current system metrics (CPU, memory, disk).
    
    Used by monitoring dashboards and resource-aware scheduling.
    """
    
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return SystemMetricsResponse(
        cpu_percent=cpu_percent,
        memory_percent=memory.percent,
        memory_available_gb=memory.available / (1024 ** 3),
        disk_percent=disk.percent,
        disk_available_gb=disk.free / (1024 ** 3)
    )


@router.get("/info", response_model=SystemInfoResponse)
async def get_system_info():
    """
    Get complete system information including hardware and current metrics.
    
    Used for system dashboards and debugging.
    """
    
    hardware_info = get_hardware_info()
    
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    metrics = SystemMetricsResponse(
        cpu_percent=cpu_percent,
        memory_percent=memory.percent,
        memory_available_gb=memory.available / (1024 ** 3),
        disk_percent=disk.percent,
        disk_available_gb=disk.free / (1024 ** 3)
    )
    
    return SystemInfoResponse(
        hardware=hardware_info,
        metrics=metrics
    )


@router.get("/ready")
async def readiness_probe():
    """
    Kubernetes/Orchestration readiness probe.
    
    Returns 200 if service is ready to accept traffic.
    """
    return {"status": "ready"}
