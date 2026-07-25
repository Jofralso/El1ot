"""
ELIOT Core Service - Main Entry Point

Phase 2: Foundation + AI Agent Framework
- FastAPI application
- Configuration loader
- Hardware detection
- Health checks
- Monitoring hooks
- Request instrumentation
- Agent API routes
- Knowledge API routes
- Tool API routes
- Touch UI
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from core.config import settings
from core.hardware import detect_hardware
from core.monitoring import setup_prometheus, get_uptime
from core.middleware import PrometheusMiddleware
from core.routes import router_health, router_system


logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""

    logger.info("=" * 60)
    logger.info("ELIOT CORE SERVICE STARTING")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.env}")
    logger.info(f"Log Level: {settings.log_level}")

    hardware_info = detect_hardware()
    logger.info(f"Hardware: {hardware_info['target']}")
    logger.info(f"CPU Cores: {hardware_info['cpu_count']}")
    logger.info(f"Memory: {hardware_info['memory_gb']:.2f} GB")

    app.state.hardware_info = hardware_info
    app.state.start_time = __import__("time").time()

    setup_prometheus()
    logger.info("Prometheus metrics initialized")

    # Initialize subsystems
    try:
        from security import get_security_manager
        get_security_manager()
        logger.info("Security subsystem initialized")
    except Exception as e:
        logger.warning(f"Security init skipped: {e}")

    try:
        from knowledge import get_knowledge_engine
        get_knowledge_engine()
        logger.info("Knowledge engine initialized")
    except Exception as e:
        logger.warning(f"Knowledge engine init skipped: {e}")

    try:
        from tools.builtin import register_builtin_tools
        register_builtin_tools()
        logger.info("Tool system initialized")
    except Exception as e:
        logger.warning(f"Tool system init skipped: {e}")

    try:
        from core.inference import get_inference_engine
        engine = get_inference_engine()
        import asyncio
        loop = asyncio.get_event_loop()
        loop.create_task(engine.initialize())
        logger.info("Inference engine initialized")
    except Exception as e:
        logger.warning(f"Inference engine init skipped: {e}")

    logger.info("ELIOT CORE SERVICE READY")
    logger.info("=" * 60)

    yield

    logger.info("ELIOT CORE SERVICE SHUTTING DOWN")


app = FastAPI(
    title="ELIOT Core Service",
    description="Embedded Local Intelligence Operations Terminal",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(PrometheusMiddleware)

app.include_router(router_health.router, tags=["health"])
app.include_router(router_system.router, tags=["system"])

from core.routes import router_agent, router_knowledge, router_tools  # noqa: E402
from ui import router as ui_router  # noqa: E402

app.include_router(router_agent.router, tags=["agents"])
app.include_router(router_knowledge.router, tags=["knowledge"])
app.include_router(router_tools.router, tags=["tools"])
app.include_router(ui_router, tags=["ui"])


from fastapi import WebSocket

@app.websocket("/avatar/ws")
async def avatar_ws(websocket: WebSocket):
    """WebSocket endpoint for real-time avatar state synchronization."""
    from avatar.engine import get_avatar_engine
    engine = get_avatar_engine()
    await websocket.accept()
    await engine.ws_handler(websocket)


@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return PlainTextResponse(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.core_host,
        port=settings.core_port,
        log_level=settings.log_level.lower(),
    )
