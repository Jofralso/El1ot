# ELIOT Architecture

## Phase 1: Foundation Overview

ELIOT is a microservice-based AI system running on containerized infrastructure. Phase 1 establishes the core platform.

### Service Architecture (Phase 1)

```
┌─────────────────────────────────────────────────────┐
│                   ELIOT Core Service                │
│  (FastAPI, Configuration, Hardware Detection)       │
└──────────────────────┬──────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   ┌────v────┐    ┌────v──────┐  ┌──v────────┐
   │  Redis  │    │ Prometheus│  │ (Future:  │
   │  Broker │    │ Monitoring│  │ Agents,   │
   │         │    │           │  │ Models)   │
   └─────────┘    └───────────┘  └───────────┘
```

### Service Responsibilities (Phase 1)

| Service | Role | Status |
|---------|------|--------|
| **ELIOT Core** | API, config, hardware detection, health | ✓ Active |
| **Redis** | Message broker, caching | ✓ Active |
| **Prometheus** | Metrics collection | ✓ Active |

### Communication Patterns

**HTTP/REST**
- Client → Core Service: Commands, queries
- Core → External APIs: (Phase 2+)

**Redis Pub/Sub** (Phase 2+)
- Inter-agent messaging
- Event distribution

**WebSockets** (Phase 4+)
- Voice streaming
- Real-time UI updates

### Data Flow (Phase 1)

```
Health Check Request
   ↓
FastAPI Route Handler
   ↓
Hardware Detection Module
   ↓
Redis Connection Check
   ↓
Response (JSON)
```

### Configuration Hierarchy

1. **Environment Variables** (.env)
2. **Pydantic Settings** (core/config.py)
3. **Defaults** (fallback values)

### Hardware Abstraction Layer

```python
# Phase 1: Detection only
hardware_info = {
    "target": "jetson-orin-nano",
    "cpu_count": 8,
    "memory_gb": 8.0,
    "cuda_available": true,
    "has_camera": true,
    "has_microphone": true,
}

# Phase 2+: Runtime optimization
# - CUDA device selection
# - Memory management
# - GPU scheduling
```

### Monitoring Strategy

**Phase 1:**
- Service health checks
- System resource monitoring (CPU, memory, disk)
- Redis connectivity

**Phase 2+:**
- Agent health and activity
- Model inference latency
- Memory usage per component
- Database performance

### Error Handling

1. **Service-level** – Try/except with structured logging
2. **HTTP-level** – FastAPI exception handlers
3. **System-level** – Graceful degradation (e.g., Redis unavailable)

### Scalability Considerations

- **Horizontal** – Multiple Core instances behind load balancer (future)
- **Vertical** – Jetson Orin Nano optimization (GPU, memory limits)
- **Async** – FastAPI + asyncio for concurrent requests

### Security (Phase 1+)

- [See SecurityModel.md](SecurityModel.md)
- Hardware-based attestation (Jetson TrustZone, future)
- Audit logging to Redis
- Target whitelist enforcement (Phase 2+)

---

## Next Phase: Phase 2 - AI & Agents

Phase 2 will add:

- **llama.cpp** integration with CUDA
- **Model Management** – quantized model loading, switching
- **LangGraph Framework** – supervisor + specialized agents
- **Memory System** – conversation history, context management
- **Tool Integration** – MCP-compatible tool layer

See [DeveloperGuide.md](DeveloperGuide.md) for Phase 2 planning.
