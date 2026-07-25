# Troubleshooting

## Common Issues

### Core service won't start

```bash
# Check logs
docker-compose logs core

# Verify Redis is running
docker-compose ps redis

# Check port availability
lsof -i :8000
```

### Redis connection failed

```bash
# Test Redis
docker-compose exec redis redis-cli ping

# Restart Redis
docker-compose restart redis
```

### ChromaDB not available

Knowledge engine falls back to in-memory store if ChromaDB is unavailable.

```bash
# Check ChromaDB
docker-compose ps chromadb

# Restart
docker-compose restart chromadb
```

### GPU not detected

```bash
# Check CUDA
nvidia-smi

# Verify CUDA_HOME
echo $CUDA_HOME

# On Jetson, check nvpmodel
nvpmodel -q
```

### Voice system not working

1. Verify microphone is connected: `arecord -l`
2. Check speaker: `aplay -l`
3. Install voice dependencies: `pip install faster-whisper openwakeword`

### Camera not detected

```bash
# Check camera devices
ls /dev/video*

# Test capture
python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
```

### MQTT connection issues

```bash
# Check Mosquitto
docker-compose ps mqtt

# Test publish/subscribe
mosquitto_sub -t "test" &
mosquitto_pub -t "test" -m "hello"
```

## Performance

### High memory usage

- Reduce model quantization level
- Lower `chunk_size` in knowledge engine
- Reduce agent memory buffer size

### Slow inference

- Ensure CUDA is enabled
- Use smaller quantized models (Q4_K_M)
- Check GPU temperature for throttling

## Logs

```bash
# All logs
docker-compose logs -f

# Core only
docker-compose logs -f core

# System logs
journalctl -u eliot
```

## Reset

```bash
# Full reset
make clean-all

# Reset security (keep data)
rm -rf security/*
make setup
```
