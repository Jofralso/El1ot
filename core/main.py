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
    import asyncio

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

    # References for shutdown cleanup
    sentient_engine = None
    tamagotchi_engine = None

    # Initialize subsystems
    try:
        from security import get_security_manager
        get_security_manager()
        logger.info("Security subsystem initialized")
    except Exception as e:
        logger.warning(f"Security init skipped: {e}")

    try:
        from knowledge import get_knowledge_engine
        kengine = get_knowledge_engine()
        logger.info("Knowledge engine initialized")
        # Auto-ingest if empty
        if kengine.store.count() == 0:
            from knowledge.ingestion import IngestionPipeline
            pipeline = IngestionPipeline(kengine)
            loop = asyncio.get_running_loop()
            loop.create_task(pipeline.ingest_directory("./data/knowledge"))
            logger.info("Knowledge auto-ingestion started")
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
        loop = asyncio.get_running_loop()
        loop.create_task(engine.initialize())
        logger.info("Inference engine initialized")
    except Exception as e:
        logger.warning(f"Inference engine init skipped: {e}")

    # Transition avatar from BOOTING to IDLE after service is ready
    try:
        from avatar.engine import get_avatar_engine
        avatar = get_avatar_engine()
        avatar.complete_boot()
        loop = asyncio.get_running_loop()
        loop.create_task(avatar.start_broadcast_loop(interval=0.1))
        logger.info("Avatar engine boot completed, broadcast loop started")
    except Exception as e:
        logger.warning(f"Avatar boot completion skipped: {e}")

    # Initialize Stealth Engine
    try:
        from agents.stealth import get_stealth_engine
        stealth = get_stealth_engine()
        stealth.active = settings.stealth_active
        # Auto-rotate MAC on Jetson built-in interfaces for anonymity
        rotate_results = await stealth.auto_rotate_jetson()
        if rotate_results:
            logger.info(f"[ANONYMITY] MAC rotation: {rotate_results}")
        logger.info(f"Stealth engine initialized (active={stealth.active}, profile={stealth.profile.value})")
    except Exception as e:
        logger.warning(f"Stealth engine init skipped: {e}")

    # Initialize Sentient Engine (no auto-loop — tamagotchi is the sole engine)
    try:
        from agents.sentient import get_sentient_engine
        sentient_engine = get_sentient_engine()
        logger.info("Sentient engine initialized (utility only, no auto-scan)")
    except Exception as e:
        logger.warning(f"Sentient engine init skipped: {e}")

    # Initialize Tamagotchi Engine
    try:
        from agents.tamagotchi import get_tamagotchi_engine
        tamagotchi_engine = get_tamagotchi_engine()
        if settings.tamagotchi_enabled:
            loop = asyncio.get_running_loop()
            loop.create_task(tamagotchi_engine.start(scan_interval=settings.tamagotchi_scan_interval))
            logger.info(f"Tamagotchi engine started (interval={settings.tamagotchi_scan_interval}s)")
        else:
            logger.info("Tamagotchi engine disabled")
    except Exception as e:
        logger.warning(f"Tamagotchi engine init skipped: {e}")

    logger.info("ELIOT CORE SERVICE READY")
    logger.info("=" * 60)

    yield

    # ── Shutdown ──────────────────────────────────────────────
    logger.info("ELIOT CORE SERVICE SHUTTING DOWN")

    # Restore MAC addresses on shutdown
    try:
        from agents.stealth import get_stealth_engine
        stealth = get_stealth_engine()
        restore_results = await stealth.restore_all_macs()
        if restore_results:
            logger.info(f"[ANONYMITY] MAC restored on shutdown: {restore_results}")
    except Exception:
        pass

    if tamagotchi_engine:
        try:
            await tamagotchi_engine.stop()
            logger.info("Tamagotchi engine stopped")
        except Exception as e:
            logger.warning(f"Tamagotchi stop error: {e}")

    if sentient_engine:
        try:
            await sentient_engine.stop()
            logger.info("Sentient engine stopped")
        except Exception as e:
            logger.warning(f"Sentient stop error: {e}")

    logger.info("ELIOT CORE SERVICE STOPPED")


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
from core.routes import router_sentient, router_tamagotchi  # noqa: E402
from ui import router as ui_router  # noqa: E402

app.include_router(router_agent.router, tags=["agents"])
app.include_router(router_knowledge.router, tags=["knowledge"])
app.include_router(router_tools.router, tags=["tools"])
app.include_router(router_sentient.router, tags=["sentient"])
app.include_router(router_tamagotchi.router, tags=["tamagotchi"])
app.include_router(ui_router, tags=["ui"])


from fastapi import WebSocket

@app.websocket("/avatar/ws")
async def avatar_ws(websocket: WebSocket):
    """WebSocket endpoint for real-time avatar state synchronization."""
    from avatar.engine import get_avatar_engine
    engine = get_avatar_engine()
    await websocket.accept()
    await engine.ws_handler(websocket)


@app.websocket("/sentient/live")
async def sentient_live_ws(websocket: WebSocket):
    """WebSocket endpoint for real-time sentient scan events."""
    await websocket.accept()
    from agents.sentient import get_sentient_engine
    engine = get_sentient_engine()
    last_ts = 0.0
    try:
        while True:
            events = engine.get_live_events(last_ts)
            if events:
                import json
                for event in events:
                    await websocket.send_json(event)
                last_ts = events[-1]["timestamp"]
            import asyncio
            await asyncio.sleep(1)
    except Exception:
        pass


@app.websocket("/tamagotchi/ws")
async def tamagotchi_ws(websocket: WebSocket):
    """WebSocket endpoint for real-time tamagotchi phase transitions and think messages."""
    await websocket.accept()
    from agents.tamagotchi import get_tamagotchi_engine
    tama = get_tamagotchi_engine()
    tama._ws_clients.add(websocket)
    try:
        while True:
            import asyncio
            await asyncio.sleep(30)
    except Exception:
        pass
    finally:
        tama._ws_clients.discard(websocket)


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
