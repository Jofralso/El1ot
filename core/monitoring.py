"""
Prometheus Monitoring Setup

Initializes metrics collection for:
- API performance
- System resources (CPU, memory, temperature)
- Service health
- Agent activity
- Model inference speed
- Knowledge engine queries
"""

import time
from prometheus_client import Counter, Histogram, Gauge, Info

# Application info
app_info = Info(
    "eliot_app",
    "ELIOT application information"
)

# Request metrics
request_count = Counter(
    "eliot_requests_total",
    "Total requests",
    ["method", "endpoint", "status"],
)

request_duration = Histogram(
    "eliot_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# System metrics
cpu_usage = Gauge(
    "eliot_cpu_usage_percent",
    "CPU usage percentage",
)

memory_usage = Gauge(
    "eliot_memory_usage_percent",
    "Memory usage percentage",
)

system_temperature = Gauge(
    "eliot_system_temperature_celsius",
    "System temperature",
    ["sensor"],
)

gpu_usage = Gauge(
    "eliot_gpu_usage_percent",
    "GPU usage percentage",
)

gpu_memory_usage = Gauge(
    "eliot_gpu_memory_usage_percent",
    "GPU memory usage percentage",
)

# Service health
service_health = Gauge(
    "eliot_service_health",
    "Service health status (1=healthy, 0=unhealthy)",
    ["service"],
)

redis_connected = Gauge(
    "eliot_redis_connected",
    "Redis connection status (1=connected, 0=disconnected)",
)

# Agent metrics
agent_task_count = Counter(
    "eliot_agent_tasks_total",
    "Total agent tasks executed",
    ["agent_type", "status"],
)

agent_task_duration = Histogram(
    "eliot_agent_task_duration_seconds",
    "Agent task execution duration",
    ["agent_type"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

agent_active_tasks = Gauge(
    "eliot_agent_active_tasks",
    "Currently active agent tasks",
    ["agent_type"],
)

# Model inference metrics
inference_count = Counter(
    "eliot_inference_total",
    "Total model inference calls",
    ["model", "status"],
)

inference_duration = Histogram(
    "eliot_inference_duration_seconds",
    "Model inference duration",
    ["model"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

inference_tokens = Counter(
    "eliot_inference_tokens_total",
    "Total tokens generated",
    ["model"],
)

# Knowledge engine metrics
knowledge_query_count = Counter(
    "eliot_knowledge_queries_total",
    "Total knowledge base queries",
    ["status"],
)

knowledge_query_duration = Histogram(
    "eliot_knowledge_query_duration_seconds",
    "Knowledge query duration",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0),
)

knowledge_documents = Gauge(
    "eliot_knowledge_documents_total",
    "Total documents in knowledge base",
)

# Tool execution metrics
tool_execution_count = Counter(
    "eliot_tool_executions_total",
    "Total tool executions",
    ["tool_name", "status"],
)

tool_execution_duration = Histogram(
    "eliot_tool_execution_duration_seconds",
    "Tool execution duration",
    ["tool_name"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0),
)

# Uptime tracking
_startup_time: float = time.time()


def get_uptime() -> float:
    """Get service uptime in seconds"""
    return time.time() - _startup_time


def setup_prometheus():
    """Initialize Prometheus metrics"""
    app_info.info({
        "version": "0.1.0",
        "phase": "2",
    })
