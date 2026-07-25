# Hardware Guide

## Target Hardware

### NVIDIA Jetson Orin Nano 8GB (Primary)

| Spec | Value |
|------|-------|
| GPU | 1024-core NVIDIA Ampere |
| GPU Memory | 8 GB |
| CPU | 6-core Arm Cortex-A78AE |
| Memory | 8 GB LPDDR5 |
| Storage | NVMe SSD (recommended 256GB+) |
| Power | 7-15W |

### Raspberry Pi (Face Module)

| Spec | Value |
|------|-------|
| Model | Raspberry Pi 4/5 |
| Display | 7" SPI TFT (800x480) |
| Connection | WiFi/Bluetooth to Jetson |
| Role | Avatar rendering + touch UI |

### Peripherals

| Component | Interface | Purpose |
|-----------|-----------|---------|
| Camera | USB/CSI | Face recognition, OCR |
| Microphone | USB/I2S | Voice input |
| Speaker | 3.5mm/USB | Voice output |
| NVMe SSD | M.2 | Storage |
| Touchscreen | SPI | UI interaction |

## Hardware Detection

ELIOT auto-detects hardware on startup:

```python
from core.hardware import detect_hardware
info = detect_hardware()
# Returns: target, cpu_count, memory_gb, cuda_available, etc.
```

## Jetson-Specific

- CUDA acceleration detected via `CUDA_HOME` or `/usr/local/cuda`
- Temperature read from `/sys/class/thermal/thermal_zone*/temp`
- GPU frequency from `/sys/devices/50000000.gpu/devfreq/`
- Power modes via `nvpmodel`

## GPU Memory Management

For Jetson Orin Nano with 8GB shared memory:

- Reserve 2GB for system
- AI models: up to 5GB (quantized)
- Avatar rendering: up to 1GB

## Thermal Monitoring

```python
from hardware.abstraction import get_hardware_abstraction
hw = get_hardware_abstraction()
status = hw.get_full_status()
# Includes thermal readings for CPU, GPU, board
```

## Raspberry Pi Communication

The Pi connects to the Jetson via MQTT:

- Avatar state updates: `eliot/avatar/state`
- Touch events: `eliot/ui/touch`
- Status sync: `eliot/system/status`
