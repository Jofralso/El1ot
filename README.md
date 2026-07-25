# ELIOT
## Embedded Local Intelligence Operations Terminal

A fully local, offline-capable AI cybersecurity companion inspired by Mr. Robot.

**Status**: Phase 2 Complete (v0.2) - Agent framework, knowledge engine, tool system, security, touch UI

---

## What is ELIOT?

ELIOT is a physical AI appliance running on an NVIDIA Jetson Orin Nano, featuring:

- **Local-first AI** – Qwen2.5-Coder-3B-Pentest + DeepSeek-R1-Distill reasoning
- **Offline-capable** – Zero dependency on cloud services
- **Multi-agent reasoning** – 8 specialized agents coordinated by a supervisor
- **Knowledge engine** – ChromaDB vector store, semantic search, document ingestion
- **Voice interaction** – Wake word detection, speech-to-text, text-to-speech (all local)
- **Vision system** – Face recognition, OCR, visual analysis
- **Cyberpunk avatar** – 3D animated character with emotional states (Godot)
- **Touch interface** – Web-based UI with 6 pages
- **Tool system** – MCP-compatible with permission checks and audit logging
- **Security model** – User/target whitelist, RBAC, audit trail

ELIOT assists with authorized cybersecurity assessments, CTF environments, and personal laboratories.

---

## Core Principles

- ✓ Local first
- ✓ Privacy focused
- ✓ Offline capable
- ✓ Modular
- ✓ Extensible
- ✓ Hardware aware
- ✓ AI driven
- ✓ Human controlled

---

## Hardware Stack

| Component | Role |
|-----------|------|
| NVIDIA Jetson Orin Nano 8GB | Brain – AI inference, agent orchestration |
| Raspberry Pi + 7" SPI TFT | Face – Avatar rendering, touch interface |
| Camera + Microphone + Speaker | Sensors – Vision, voice input/output |
| NVMe storage | Knowledge database, model cache |

---

## Development Phases

- [x] **Phase 1 – Foundation** (v0.1)
  - Repository scaffolding, Docker Compose, core service, configuration, health, monitoring

- [x] **Phase 2 – AI Models & Agents** (v0.2) ← **Current**
  - Agent framework (8 agents), tool system, knowledge engine, security, touch UI, hardware abstraction

- [ ] Phase 3 – Voice & Vision Integration (v0.3)
  - Whisper.cpp, Piper TTS, OpenWakeWord, face recognition, OCR

- [ ] Phase 4 – Avatar Engine (v0.4)
  - Godot Engine integration, WebSocket bridge, animations, emotions

- [ ] Phase 5 – Deployment (v0.5)
  - Production optimization, Jetson-specific tweaks, Raspberry Pi TFT

---

## Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/yourusername/eliot.git
cd eliot

cp .env.example .env
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

### Local Development

```bash
pip install -r requirements.txt
uvicorn core.main:app --reload
```

### Touch UI

Open `http://localhost:8000/ui/` in a browser.

---

## API Highlights

```bash
# Chat with agents
curl -X POST http://localhost:8000/agents/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "create a plan for network reconnaissance"}'

# Search knowledge
curl -X POST http://localhost:8000/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{"query": "buffer overflow vulnerability"}'

# List tools
curl http://localhost:8000/tools/

# Execute tool
curl -X POST http://localhost:8000/tools/system_info/execute \
  -H "Content-Type: application/json" \
  -d '{"params": {}, "user_permissions": ["admin"]}'
```

---

## Project Structure

```
ELIOT/
├── core/                  # Core service (FastAPI, routes, config)
├── agents/                # Multi-agent system (8 agents + supervisor)
├── knowledge/             # Knowledge engine (ChromaDB, embeddings, ingestion)
├── tools/                 # MCP-compatible tool system
├── voice/                 # Voice system (STT, TTS, wake word)
├── vision/                # Vision system (camera, face, OCR)
├── avatar/                # Avatar engine (Godot integration)
├── ui/                    # Touch interface (web-based)
├── hardware/              # Hardware abstraction layer
├── security/              # Users, targets, permissions, audit
├── monitoring/            # Prometheus + Grafana
├── docs/                  # Documentation
├── tests/                 # Test suite (30+ tests)
├── config/                # Mosquitto, runtime config
├── .github/               # CI/CD workflows
├── docker-compose.yml     # Service orchestration (6 services)
└── Makefile               # Developer commands
```

---

## Documentation

- **[Architecture](docs/Architecture.md)** – System design, microservices, data flow
- **[Installation](docs/Installation.md)** – Detailed setup for Jetson & dev
- **[Hardware](docs/Hardware.md)** – Component specs, detection, thermal
- **[Developer Guide](docs/DeveloperGuide.md)** – Contributing, coding standards
- **[User Manual](docs/UserManual.md)** – How to use ELIOT
- **[API Reference](docs/API.md)** – REST endpoints, message formats
- **[Security Model](docs/SecurityModel.md)** – Authentication, authorization, audit
- **[Troubleshooting](docs/Troubleshooting.md)** – Common issues and fixes

---

## License

MIT
