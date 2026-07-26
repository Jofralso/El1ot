"""
Sentient API Routes

Endpoints for autonomous network discovery, device mapping,
and topology visualization.
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sentient", tags=["sentient"])


@router.get("/status")
async def get_status():
    from agents.sentient import get_sentient_engine
    return get_sentient_engine().get_status()


@router.post("/scan")
async def trigger_scan():
    from agents.sentient import get_sentient_engine
    engine = get_sentient_engine()
    try:
        result = await engine.run_full_scan()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices")
async def get_devices():
    from agents.sentient import get_sentient_engine
    return {"devices": get_sentient_engine().get_devices()}


@router.get("/devices/{ip}")
async def get_device(ip: str):
    from agents.sentient import get_sentient_engine
    device = get_sentient_engine().get_device(ip)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.get("/networks")
async def get_networks():
    from agents.sentient import get_sentient_engine
    return {"networks": get_sentient_engine().get_networks()}


@router.get("/topology")
async def get_topology():
    from agents.sentient import get_sentient_engine
    return get_sentient_engine().get_topology()


@router.get("/wifi")
async def get_wifi_aps():
    from agents.sentient import get_sentient_engine
    return {"access_points": get_sentient_engine().get_wifi_aps()}


@router.get("/events")
async def get_events(since: float = 0):
    from agents.sentient import get_sentient_engine
    return {"events": get_sentient_engine().get_live_events(since)}


@router.get("/history")
async def get_history():
    from agents.sentient import get_sentient_engine
    return {"history": get_sentient_engine().get_scan_history()}


@router.post("/search")
async def search_devices(query: str):
    from agents.sentient import get_sentient_engine
    return {"results": get_sentient_engine().search_devices(query)}


@router.post("/start")
async def start_engine():
    from agents.sentient import get_sentient_engine
    engine = get_sentient_engine()
    await engine.start()
    return {"status": "started"}


@router.post("/stop")
async def stop_engine():
    from agents.sentient import get_sentient_engine
    engine = get_sentient_engine()
    await engine.stop()
    return {"status": "stopped"}
