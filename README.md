# ELIOT
## Embedded Local Intelligence Operations Terminal

A fully local, offline-capable AI cybersecurity companion inspired by Mr. Robot.

**Status**: Phase 5 Complete (v0.3) - All systems operational

---

## What is ELIOT?

ELIOT is a physical AI appliance running on an NVIDIA Jetson Orin Nano, featuring:

- **Local-first AI** – Qwen2.5-Coder-3B + DeepSeek-R1-Distill reasoning (all local via llama.cpp)
- **Offline-capable** – Zero dependency on cloud services
- **Multi-agent reasoning** – 8 specialized agents coordinated by a supervisor
- **Knowledge engine** – ChromaDB vector store, semantic search, document ingestion, online/offline updates
- **Voice interaction** – Wake word detection, speech-to-text (Whisper), text-to-speech (Piper), audio capture/playback
- **Vision system** – Face recognition, OCR, camera management, frame processing
- **Cyberpunk avatar** – 3D animated character with emotional states, lip sync, WebSocket bridge (Godot)
- **Touch interface** – Web-based UI with 6 pages
- **Tool system** – MCP-compatible with permission checks and audit logging
- **Security model** – User/target whitelist, RBAC, audit trail
- **AI inference** – llama.cpp GPU-accelerated backend with model management and download
- **Knowledge updates** – Online/offline update pipeline with integrity verification
- **Hardware abstraction** – Auto-detect Jetson/Pi/Desktop, GPU, camera, audio

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

## Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/Jofralso/El1ot.git
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

### Installation Script

```bash
chmod +x scripts/install.sh
sudo ./scripts/install.sh
```

The installer auto-detects your hardware (Jetson/Pi/Desktop), downloads models, and configures services.

### Touch UI

Open `http://localhost:8000/ui/` in a browser.

---

## API Endpoints

```bash
# Health & status
curl http://localhost:8000/health/detailed
curl http://localhost:8000/metrics

# Chat with agents
curl -X POST http://localhost:8000/agents/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "create a plan for network reconnaissance"}'

# Voice interaction
curl -X POST http://localhost:8000/voice/speak \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, I am ELIOT"}'

# Vision
curl http://localhost:8000/vision/status

# Avatar WebSocket
wscat -c ws://localhost:8000/avatar/ws

# Knowledge
curl -X POST http://localhost:8000/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{"query": "buffer overflow vulnerability"}'

# Tools
curl http://localhost:8000/tools/
curl -X POST http://localhost:8000/tools/system_info/execute \
  -H "Content-Type: application/json" \
  -d '{"params": {}, "user_permissions": ["admin"]}'

# AI inference
curl -X POST http://localhost:8000/voice/converse \
  -H "Content-Type: application/json" \
  -d '{"message": "What is SQL injection?"}'
```

---

## Project Structure

```
ELIOT/
├── core/                  # Core service (FastAPI, routes, config, inference engine)
├── agents/                # Multi-agent system (8 agents + supervisor)
├── knowledge/             # Knowledge engine (ChromaDB, embeddings, ingestion, updates)
├── tools/                 # MCP-compatible tool system
├── voice/                 # Voice system (STT, TTS, wake word, audio, conversation)
├── vision/                # Vision system (camera, face recognition, OCR, frame processing)
├── avatar/                # Avatar engine (WebSocket, lip sync, emotions, animations)
├── ui/                    # Touch interface (web-based)
├── hardware/              # Hardware abstraction layer
├── security/              # Users, targets, permissions, audit
├── monitoring/            # Prometheus + Grafana
├── deployment/            # Systemd service files
├── scripts/               # Install and setup scripts
├── docs/                  # Documentation
├── tests/                 # Test suite (200+ tests)
├── config/                # Mosquitto, runtime config
├── models/                # GGUF model files (downloaded)
├── .github/               # CI/CD workflows
├── docker-compose.yml     # Service orchestration (6 services)
├── docker-compose.prod.yml # Production compose
├── Dockerfile.jetson      # Jetson-specific Docker build
└── Makefile               # Developer commands
```

---

## Development Phases

- [x] Phase 1 – Foundation (v0.1) – Repository, Docker, core service, config, health, monitoring
- [x] Phase 2 – AI Models & Agents (v0.2) – Agent framework, tools, knowledge, security, touch UI
- [x] Phase 3 – Voice & Vision (v0.3) – Whisper, Piper TTS, camera, face recognition, OCR
- [x] Phase 4 – Avatar Engine (v0.4) – Godot WebSocket, lip sync, emotions, animations
- [x] Phase 5 – Deployment (v0.5) – Jetson Dockerfile, Pi setup, systemd, installer

---

## Testing

```bash
make test              # Run all tests
make test-coverage     # Run with coverage
make lint              # Lint all modules
make type-check        # Type checking
```

---

## Deployment

### Jetson Orin Nano

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Raspberry Pi (Avatar Display)

```bash
chmod +x scripts/setup-pi.sh
sudo ./scripts/setup-pi.sh
```

### Production (Systemd)

```bash
sudo cp deployment/eliot.service /etc/systemd/system/
sudo systemctl enable eliot
sudo systemctl start eliot
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
