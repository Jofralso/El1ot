# Installation Guide

## Phase 1: Development Environment

### Prerequisites

- **Docker** & **Docker Compose** (v2.0+)
- **Python** 3.10+ (for local development without Docker)
- **Git**
- **curl** (for health checks)

### Supported Platforms

| Platform | Docker | Native | Status |
|----------|--------|--------|--------|
| Linux (Ubuntu 22.04+) | ✓ | ✓ | Recommended |
| macOS | ✓ | ✓ | Works |
| Windows (WSL2) | ✓ | ✓ | Works |
| NVIDIA Jetson Orin Nano | ✓ | ✓ | Optimized for Phase 2+ |

### Quick Start (Docker)

#### 1. Clone Repository

```bash
git clone https://github.com/yourusername/eliot.git
cd eliot
```

#### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env for your setup (optional – defaults work)
```

#### 3. Start Services

```bash
docker-compose up -d
```

This starts:
- **ELIOT Core** (http://localhost:8000)
- **Redis** (localhost:6379)
- **Prometheus** (http://localhost:9090)

#### 4. Verify Health

```bash
# Check service status
docker-compose ps

# Test health endpoint
curl http://localhost:8000/health

# Check metrics
curl http://localhost:8000/system/metrics
```

#### 5. View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f core
```

#### 6. Stop Services

```bash
docker-compose down
```

---

## Development Setup (Local Python)

If developing without Docker:

### 1. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Update .env to point to local Redis
# REDIS_HOST=localhost
```

### 4. Start Redis (Docker only)

```bash
docker run -d -p 6379:6379 --name eliot-redis redis:7-alpine
```

### 5. Run Core Service

```bash
cd core
python -m main
```

Service runs on http://localhost:8000

### 6. Run Tests

```bash
pytest tests/ -v
```

---

## Docker Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ELIOT_ENV` | development | Environment (development, testing, production) |
| `ELIOT_LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `HARDWARE_TARGET` | dev-machine | Hardware target (dev-machine, jetson-orin-nano, etc.) |
| `CORE_PORT` | 8000 | API port |
| `REDIS_HOST` | redis | Redis hostname |
| `REDIS_PORT` | 6379 | Redis port |

---

## Jetson Orin Nano Installation (Phase 2+)

### Prerequisites

- Jetson Orin Nano 8GB developer kit
- NVMe storage (recommended)
- 7" Raspberry Pi TFT display
- Power supply (25W+)

### JetPack Setup

```bash
# Flash latest JetPack OS (6.0+)
# https://developer.nvidia.com/embedded/jetpack

# Verify CUDA is available
nvidia-smi
```

### ELIOT Installation on Jetson

```bash
# Clone repo
git clone https://github.com/yourusername/eliot.git
cd eliot

# Update environment
echo "HARDWARE_TARGET=jetson-orin-nano" >> .env

# Start services (may take longer on first run)
docker-compose up -d

# Verify
docker-compose ps
curl http://localhost:8000/health
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Or use different port
docker-compose up -p "9000:8000" core
```

### Redis Connection Fails

```bash
# Check Redis is running
docker-compose ps redis

# Restart Redis
docker-compose restart redis

# Check logs
docker-compose logs redis
```

### Health Check Fails

```bash
# Check service logs
docker-compose logs core

# Manually test endpoint
curl -v http://localhost:8000/health

# If Docker: check network
docker network inspect eliot-network
```

### Permission Denied on Linux

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Apply group changes
newgrp docker
```

---

## Next Steps

1. **Verify Installation** – Run all health checks
2. **Review Logs** – Check for warnings or errors
3. **Run Tests** – `pytest tests/ -v`
4. **Explore API** – `curl http://localhost:8000/docs` (Swagger UI)
5. **Phase 2 Planning** – See [DeveloperGuide.md](DeveloperGuide.md)

---

## Getting Help

- Check [Troubleshooting.md](Troubleshooting.md)
- Review service logs: `docker-compose logs core`
- Open GitHub issue with full error output
