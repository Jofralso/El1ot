"""
Hardware Detection and Abstraction

Detects hardware target (Jetson, Raspberry Pi, dev machine).
Abstracts hardware capabilities for Phase 2+ (GPU, camera, microphone).
"""

import os
import platform
import psutil
from typing import Dict, Any

from core.config import settings


def detect_hardware() -> Dict[str, Any]:
    """
    Detect and characterize hardware environment.
    
    Returns:
        Dictionary with hardware capabilities and specs
    """
    
    hardware_info = {
        "target": settings.hardware_target,
        "os": platform.system(),
        "architecture": platform.machine(),
        "cpu_count": psutil.cpu_count(logical=False),
        "memory_gb": psutil.virtual_memory().total / (1024 ** 3),
        "cuda_available": False,
        "has_camera": False,
        "has_microphone": False,
        "has_speaker": False,
        "has_display": False,
    }
    
    # Detect CUDA (Phase 2+)
    if _detect_cuda():
        hardware_info["cuda_available"] = True
    
    # Jetson-specific detection
    if settings.hardware_target in ["jetson-orin-nano", "jetson-orin"]:
        hardware_info.update(_detect_jetson_info())
    
    return hardware_info


def _detect_cuda() -> bool:
    """Check if CUDA is available (Phase 2+)"""
    try:
        # Try importing pycuda or check for CUDA libraries
        cuda_home = os.environ.get("CUDA_HOME")
        if cuda_home and os.path.exists(cuda_home):
            return True
        
        # Check common paths
        if os.path.exists("/usr/local/cuda"):
            return True
        
        return False
    except Exception:
        return False


def _detect_jetson_info() -> Dict[str, Any]:
    """Detect Jetson-specific hardware info"""
    info = {}
    
    # Read Jetson model from /proc
    try:
        with open("/proc/device-tree/model", "r") as f:
            info["jetson_model"] = f.read().strip()
    except Exception:
        info["jetson_model"] = "Unknown"
    
    # Jetson has integrated GPU (CUDA)
    info["cuda_available"] = True
    
    # Typically has camera and audio on Jetson dev kits
    info["has_camera"] = True
    info["has_microphone"] = True
    info["has_speaker"] = True
    
    return info


def get_hardware_info() -> Dict[str, Any]:
    """Get cached hardware info (set during startup)"""
    from core.main import app
    if hasattr(app, "state") and hasattr(app.state, "hardware_info"):
        return app.state.hardware_info
    return detect_hardware()
