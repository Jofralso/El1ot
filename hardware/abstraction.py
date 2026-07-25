"""
Hardware Abstraction Layer

Provides unified interface for hardware resources across different targets:
- GPU detection and monitoring (CUDA, Jetson)
- Thermal monitoring
- Camera management
- Audio input/output
- Display management
- Power management (Jetson-specific)
"""

import os
import time
import platform
import logging
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class HardwareTarget(str, Enum):
    JETSON_ORIN_NANO = "jetson-orin-nano"
    JETSON_ORIN = "jetson-orin"
    RASPBERRY_PI = "raspberry-pi"
    DEV_MACHINE = "dev-machine"


@dataclass
class GPUInfo:
    available: bool = False
    name: str = "none"
    memory_total_mb: float = 0
    memory_used_mb: float = 0
    utilization_percent: float = 0
    temperature_celsius: float = 0
    driver_version: str = ""
    cuda_version: str = ""


@dataclass
class ThermalInfo:
    cpu_temperature: float = 0.0
    gpu_temperature: float = 0.0
    board_temperature: float = 0.0
    thermal_throttled: bool = False


@dataclass
class AudioInfo:
    input_devices: List[Dict[str, Any]] = None
    output_devices: List[Dict[str, Any]] = None
    default_input: int = 0
    default_output: int = 0

    def __post_init__(self):
        if self.input_devices is None:
            self.input_devices = []
        if self.output_devices is None:
            self.output_devices = []


class HardwareAbstraction:
    """Unified hardware interface."""

    def __init__(self, target: HardwareTarget = HardwareTarget.DEV_MACHINE):
        self.target = target
        self._gpu = GPUInfo()
        self._thermal = ThermalInfo()
        self._audio = AudioInfo()
        self._init_time = time.time()

    def get_full_status(self) -> Dict[str, Any]:
        return {
            "target": self.target.value,
            "gpu": self._get_gpu_info(),
            "thermal": self._get_thermal_info(),
            "uptime": time.time() - self._init_time,
        }

    def _get_gpu_info(self) -> Dict[str, Any]:
        if self.target in (HardwareTarget.JETSON_ORIN_NANO, HardwareTarget.JETSON_ORIN):
            return self._get_jetson_gpu()
        return self._get_desktop_gpu()

    def _get_jetson_gpu(self) -> Dict[str, Any]:
        info = {"available": True, "type": "integrated"}
        try:
            with open("/sys/devices/50000000.gpu/devfreq/50000000.gpu/cur_freq", "r") as f:
                info["current_freq_mhz"] = int(f.read().strip()) / 1_000_000
        except Exception:
            pass
        return info

    def _get_desktop_gpu(self) -> Dict[str, Any]:
        info = {"available": False}
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu,driver_version",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(", ")
                if len(parts) >= 7:
                    info.update({
                        "available": True,
                        "name": parts[0],
                        "memory_total_mb": float(parts[1]),
                        "memory_used_mb": float(parts[2]),
                        "utilization_percent": float(parts[3]),
                        "temperature_celsius": float(parts[4]),
                        "driver_version": parts[5],
                        "cuda_version": parts[6] if len(parts) > 6 else "",
                    })
        except Exception:
            pass
        return info

    def _get_thermal_info(self) -> Dict[str, Any]:
        if self.target in (HardwareTarget.JETSON_ORIN_NANO, HardwareTarget.JETSON_ORIN):
            return self._get_jetson_thermal()
        return self._get_generic_thermal()

    def _get_jetson_thermal(self) -> Dict[str, Any]:
        temps = {}
        thermal_zones = {
            "cpu": "/sys/class/thermal/thermal_zone0/temp",
            "gpu": "/sys/class/thermal/thermal_zone1/temp",
            "board": "/sys/class/thermal/thermal_zone2/temp",
        }
        for name, path in thermal_zones.items():
            try:
                with open(path, "r") as f:
                    temps[name] = int(f.read().strip()) / 1000.0
            except Exception:
                temps[name] = 0.0
        return temps

    def _get_generic_thermal(self) -> Dict[str, Any]:
        temps = {}
        try:
            import psutil
            temps["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        except Exception:
            pass
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temps["cpu"] = int(f.read().strip()) / 1000.0
        except Exception:
            pass
        return temps


_hardware: Optional[HardwareAbstraction] = None


def get_hardware_abstraction() -> HardwareAbstraction:
    global _hardware
    if _hardware is None:
        from core.config import settings
        target_map = {
            "jetson-orin-nano": HardwareTarget.JETSON_ORIN_NANO,
            "jetson-orin": HardwareTarget.JETSON_ORIN,
            "raspberry-pi": HardwareTarget.RASPBERRY_PI,
            "dev-machine": HardwareTarget.DEV_MACHINE,
        }
        target = target_map.get(settings.hardware_target, HardwareTarget.DEV_MACHINE)
        _hardware = HardwareAbstraction(target=target)
    return _hardware
