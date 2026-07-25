# Configuration Directory

This directory holds ELIOT configuration files for different environments and hardware targets.

## Phase 1 (Current)

Configuration is managed via environment variables (see `.env` and `core/config.py`).

## Phase 2+

Will add hardware-specific configs:
- `jetson-orin-nano.yaml` – Jetson memory/GPU limits
- `development.yaml` – Dev machine settings
- `production.yaml` – Production deployment settings

## Usage

```python
from core.config import settings
print(settings.hardware_target)
```
