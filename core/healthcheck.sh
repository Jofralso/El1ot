#!/bin/bash

# Docker health check script for ELIOT Core Service

set -e

HEALTH_ENDPOINT="http://localhost:8000/health"
TIMEOUT=5

# Try to reach health endpoint
if curl -sf --max-time $TIMEOUT $HEALTH_ENDPOINT > /dev/null; then
    exit 0
else
    exit 1
fi
