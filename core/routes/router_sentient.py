"""
Sentient API Routes — now delegates to TamagotchiEngine (the sole engine).
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sentient", tags=["sentient"])


def _tama():
    from agents.tamagotchi import get_tamagotchi_engine
    return get_tamagotchi_engine()


@router.get("/status")
async def get_status():
    return _tama().get_status()


@router.post("/scan")
async def trigger_scan():
    engine = _tama()
    engine.award_xp("manual_scan", detail="Manual scan triggered via API")
    return {"status": "scan_running", "message": "Tamagotchi is scanning"}


@router.get("/devices")
async def get_devices():
    return {"devices": _tama().get_devices()}


@router.get("/devices/{ip}")
async def get_device(ip: str):
    device = _tama().get_device(ip)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.get("/networks")
async def get_networks():
    return {"networks": _tama().get_networks()}


@router.get("/topology")
async def get_topology():
    return _tama().get_topology()


@router.get("/wifi")
async def get_wifi_aps():
    return {"access_points": _tama().get_wifi_aps()}


@router.get("/events")
async def get_events(since: float = 0):
    return {"events": _tama().get_live_events(since)}


@router.get("/history")
async def get_history():
    return {"history": _tama().get_scan_history()}


@router.post("/search")
async def search_devices(query: str):
    return {"results": _tama().search_devices(query)}


@router.post("/start")
async def start_engine():
    engine = _tama()
    await engine.start()
    return {"status": "started"}


@router.post("/stop")
async def stop_engine():
    engine = _tama()
    await engine.stop()
    return {"status": "stopped"}
