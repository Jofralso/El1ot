# Developer Guide

## Phase 1 - Foundation Overview

You're starting with a minimal but complete foundation:

- ✓ Repository scaffolding
- ✓ Docker Compose orchestration
- ✓ FastAPI core service skeleton
- ✓ Configuration management
- ✓ Hardware detection
- ✓ Health check endpoints
- ✓ Basic monitoring (Prometheus)
- ✓ CI/CD pipeline (GitHub Actions)
- ✓ Unit tests

Next: Move to **Phase 2** (AI Models & Agents).

---

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/agent-framework
```

### 2. Make Changes

Typical iteration:
```bash
# Update code
# Run tests
pytest tests/ -v

# Check linting
flake8 core/

# View logs
docker-compose logs -f core
```

### 3. Test in Docker

```bash
docker-compose up -d
curl http://localhost:8000/health
docker-compose logs core
```

### 4. Commit & Push

```bash
git add .
git commit -m "Feature: Add agent framework skeleton"
git push origin feature/agent-framework
```

### 5. CI/CD Runs Automatically

- GitHub Actions lints, tests, builds Docker images
- Merge to main only after all checks pass

---

## Code Structure

### Core Service (`core/`)

```
core/
├── main.py              # FastAPI app, lifespan
├── config.py            # Settings (Pydantic)
├── hardware.py          # Hardware detection
├── monitoring.py        # Prometheus metrics
├── deps.py              # Dependency injection
├── routes/              # API route handlers
│   ├── router_health.py
│   ├── router_system.py
│   └── __init__.py
└── __init__.py
```

### Adding New Routes

1. Create new file in `core/routes/router_*.py`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/agents", tags=["agents"])

@router.get("/")
async def list_agents():
    return {"agents": []}
```

2. Import in `core/main.py`:

```python
from core.routes import router_agents

app.include_router(router_agents.router)
```

3. Add tests in `tests/test_agents.py`

---

## Testing Strategy

### Unit Tests

Test individual functions in isolation:

```python
# tests/test_hardware.py
from core.hardware import detect_hardware

def test_hardware_detection():
    hardware = detect_hardware()
    assert hardware["cpu_count"] > 0
```

### Integration Tests

Test services working together:

```python
# tests/test_integration.py
def test_health_check_with_redis(client, redis_client):
    response = client.get("/health")
    assert response.status_code == 200
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test
pytest tests/test_core.py::TestHealthEndpoints::test_health_check -v

# With coverage
pytest tests/ --cov=core
```

---

## Logging Best Practices

```python
import logging

logger = logging.getLogger(__name__)

# Structured logging
logger.info("Service started", extra={
    "service": "core",
    "version": "0.1.0"
})

logger.error("Redis connection failed", exc_info=True)
```

---

## Phase 2 Planning: Agent Framework

Next phase will add:

### LangGraph Integration

```
supervisor (ELIOT CORE)
├── planner_agent
├── knowledge_agent
├── analysis_agent
├── research_agent
├── code_agent
├── documentation_agent
├── voice_agent
└── vision_agent
```

### New Modules

```
agents/
├── supervisor.py        # Main controller
├── planner.py           # Planning agent
├── knowledge.py         # Knowledge agent
├── __init__.py
└── utils/
    ├── memory.py
    ├── tools.py
    └── state.py
```

### Key Changes

1. **New route** – `/agents/plan` – accept user goals
2. **State management** – Persist agent conversations in Redis
3. **Tool system** – MCP-compatible tool layer
4. **Model loading** – llama.cpp + CUDA integration

### Estimated Scope

- ~500 LOC agents module
- ~300 LOC tests
- ~1-2 weeks development

---

## Jetson Optimization (Phase 2+)

When moving to Jetson hardware:

1. **GPU Memory** – CUDA device selection, memory limits
2. **Quantization** – Load 3B/7B models efficiently
3. **Scheduling** – Pin inference to GPU, keep inference lightweight
4. **Thermal** – Monitor temperature, thermal throttling

---

## Documentation Standards

- **Architecture** – Data flow diagrams, service responsibilities
- **Installation** – Step-by-step setup for different platforms
- **API** – Endpoint descriptions, request/response examples
- **Security** – Authentication flows, audit logging

---

## Git Workflow

```bash
# Keep main stable
# Develop on feature branches
# PR requires:
# - Passing tests
# - Code review
# - Documentation updated
# - CHANGELOG entry
```

## Deployment Checklist (Phase 8)

- [ ] All tests pass
- [ ] Linting passes (flake8)
- [ ] Documentation complete
- [ ] Docker images build successfully
- [ ] Tested on Jetson hardware
- [ ] Security audit complete
- [ ] Performance benchmarked

---

## Useful Commands

```bash
# Start dev environment
docker-compose up -d

# View service logs
docker-compose logs -f core

# Run tests
pytest tests/ -v

# Lint code
flake8 core/ tests/

# Type check
mypy core/ --ignore-missing-imports

# Kill all services
docker-compose down -v

# Build images
docker-compose build --no-cache
```

---

## Getting Help

- Check existing issues/discussions
- Review documentation in `docs/`
- Examine test files for usage examples
- Contact maintainers

---

## Contributing Guidelines

1. Fork repository
2. Create feature branch
3. Follow code style (see examples)
4. Add tests for new features
5. Update documentation
6. Submit PR with clear description

See [Architecture.md](Architecture.md) for system design details.
