# Multi-stage build for ELIOT Core Service

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Create wheels
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt


# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /build/wheels /wheels
COPY --from=builder /build/requirements.txt .

# Install Python packages from wheels
RUN pip install --no-cache /wheels/*

# Copy application modules
COPY core /app/core
COPY agents /app/agents
COPY knowledge /app/knowledge
COPY tools /app/tools
COPY voice /app/voice
COPY vision /app/vision
COPY avatar /app/avatar
COPY ui /app/ui
COPY hardware /app/hardware
COPY security /app/security
COPY config /app/config

# Create data, logs, and security directories
RUN mkdir -p /app/data /app/logs /app/security /app/models /app/data/vectordb

# Health check script
COPY core/healthcheck.sh /app/

# Non-root user
RUN useradd -m -u 1000 eliot && chown -R eliot:eliot /app
USER eliot

# Expose API port
EXPOSE 8000

# Start ELIOT core service
CMD ["python", "-m", "core.main"]
