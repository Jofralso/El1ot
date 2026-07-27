"""
Tamagotchi API Routes

Endpoints for the autonomous intelligence agent:
notifications, authorization, crack management, knowledge, and live feed.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tamagotchi", tags=["tamagotchi"])


class AuthorizeRequest(BaseModel):
    notification_id: str


class CrackRequest(BaseModel):
    hash_file: str
    tool: str = "john"
    gpu: bool = False


@router.get("/status")
async def get_status():
    from agents.tamagotchi import get_tamagotchi_engine
    return get_tamagotchi_engine().get_status()


@router.get("/notifications")
async def get_notifications(status: Optional[str] = None):
    from agents.tamagotchi import get_tamagotchi_engine, AuthStatus
    engine = get_tamagotchi_engine()
    auth_status = None
    if status:
        try:
            auth_status = AuthStatus(status)
        except ValueError:
            pass
    return {"notifications": engine.get_notifications(status=auth_status)}


@router.post("/authorize")
async def authorize(req: AuthorizeRequest):
    from agents.tamagotchi import get_tamagotchi_engine
    engine = get_tamagotchi_engine()
    if engine.authorize_notification(req.notification_id):
        return {"status": "authorized", "id": req.notification_id}
    raise HTTPException(status_code=404, detail="Notification not found or not pending")


@router.post("/deny")
async def deny(req: AuthorizeRequest):
    from agents.tamagotchi import get_tamagotchi_engine
    engine = get_tamagotchi_engine()
    if engine.deny_notification(req.notification_id):
        return {"status": "denied", "id": req.notification_id}
    raise HTTPException(status_code=404, detail="Notification not found or not pending")


@router.get("/exploits")
async def get_exploit_queue():
    from agents.tamagotchi import get_tamagotchi_engine
    return {"exploits": get_tamagotchi_engine().get_exploit_queue()}


@router.post("/crack")
async def start_crack(req: CrackRequest):
    from agents.tamagotchi import get_tamagotchi_engine
    engine = get_tamagotchi_engine()
    session = await engine.start_crack(req.hash_file, req.tool, req.gpu)
    return session.to_dict()


@router.get("/cracks")
async def get_cracks():
    from agents.tamagotchi import get_tamagotchi_engine
    return {"sessions": get_tamagotchi_engine().get_crack_sessions()}


@router.get("/knowledge")
async def get_knowledge(category: Optional[str] = None, limit: int = 50):
    from agents.tamagotchi import get_tamagotchi_engine
    engine = get_tamagotchi_engine()
    return {
        "entries": engine.get_knowledge(category=category, limit=limit),
        "stats": engine.get_knowledge_stats(),
    }


@router.get("/suggestions")
async def get_suggestions():
    from agents.tamagotchi import get_tamagotchi_engine
    return {"suggestions": get_tamagotchi_engine().get_prompt_suggestions()}


@router.post("/start")
async def start_engine():
    from agents.tamagotchi import get_tamagotchi_engine
    engine = get_tamagotchi_engine()
    await engine.start()
    return {"status": "started"}


@router.post("/stop")
async def stop_engine():
    from agents.tamagotchi import get_tamagotchi_engine
    engine = get_tamagotchi_engine()
    await engine.stop()
    return {"status": "stopped"}


@router.post("/pause")
async def pause_engine():
    from agents.tamagotchi import get_tamagotchi_engine
    get_tamagotchi_engine().pause()
    return {"status": "paused"}


@router.post("/resume")
async def resume_engine():
    from agents.tamagotchi import get_tamagotchi_engine
    get_tamagotchi_engine().resume()
    return {"status": "resumed"}


@router.post("/clear-notifications")
async def clear_old(max_age_hours: int = 24):
    from agents.tamagotchi import get_tamagotchi_engine
    get_tamagotchi_engine().clear_old_notifications(max_age_hours)
    return {"status": "cleared"}


@router.get("/gamification")
async def get_gamification():
    from agents.tamagotchi import get_tamagotchi_engine
    return get_tamagotchi_engine().get_gamification()


@router.get("/events")
async def get_events(limit: int = 100, type: Optional[str] = None):
    from agents.tamagotchi import get_tamagotchi_engine
    return {"events": get_tamagotchi_engine().get_event_log(limit=limit, event_type=type)}


@router.get("/mistakes")
async def get_mistakes(limit: int = 50):
    from agents.tamagotchi import get_tamagotchi_engine
    return {"mistakes": get_tamagotchi_engine().get_mistakes(limit=limit)}


@router.get("/reports")
async def get_reports(limit: int = 10):
    from agents.tamagotchi import get_tamagotchi_engine
    engine = get_tamagotchi_engine()
    return {"reports": engine._reports[-limit:]}


class IngestRequest(BaseModel):
    command: str
    stdout: str
    source: str = "api"


@router.post("/ingest")
async def ingest_scan(req: IngestRequest):
    from agents.tamagotchi import get_tamagotchi_engine
    engine = get_tamagotchi_engine()
    await engine.ingest_scan_result(req.command, req.stdout, source=req.source)
    return {"status": "ingested", "source": req.source}
