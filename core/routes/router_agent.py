"""
Agent API Routes

Endpoints for interacting with the ELIOT multi-agent system.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from agents.supervisor import SupervisorAgent
from agents.planner import PlannerAgent
from agents.knowledge import KnowledgeAgent
from agents.analysis import AnalysisAgent
from agents.research import ResearchAgent
from agents.code import CodeAgent
from agents.documentation import DocumentationAgent
from agents.voice import VoiceAgent
from agents.vision import VisionAgent
from agents.base import AgentMessage

router = APIRouter(prefix="/agents", tags=["agents"])
logger = logging.getLogger(__name__)

_supervisor: Optional[SupervisorAgent] = None


def get_supervisor() -> SupervisorAgent:
    global _supervisor
    if _supervisor is None:
        _supervisor = SupervisorAgent()
        _supervisor.register_agent(PlannerAgent())
        _supervisor.register_agent(KnowledgeAgent())
        _supervisor.register_agent(AnalysisAgent())
        _supervisor.register_agent(ResearchAgent())
        _supervisor.register_agent(CodeAgent())
        _supervisor.register_agent(DocumentationAgent())
        _supervisor.register_agent(VoiceAgent())
        _supervisor.register_agent(VisionAgent())
        logger.info("Supervisor initialized with all agents")
    return _supervisor


class ChatRequest(BaseModel):
    message: str
    agent: Optional[str] = None
    user_id: str = "anonymous"
    metadata: Dict[str, Any] = {}


class ChatResponse(BaseModel):
    sender: str
    content: str
    message_type: str
    metadata: Dict[str, Any] = {}


class AgentStatusResponse(BaseModel):
    name: str
    role: str
    state: str
    tasks_completed: int
    errors: int


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(request: ChatRequest):
    """
    Send a message to the ELIOT agent system.
    Routes to the appropriate agent based on content or explicit agent selection.
    """
    supervisor = get_supervisor()

    message = AgentMessage(
        sender="user",
        receiver=request.agent or "supervisor",
        content=request.message,
        metadata=request.metadata,
    )

    if request.agent:
        agent = supervisor.get_agent(request.agent)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent '{request.agent}' not found")
        response = await agent.handle(message)
    else:
        response = await supervisor.handle(message)

    return ChatResponse(
        sender=response.sender,
        content=response.content,
        message_type=response.message_type,
        metadata=response.metadata,
    )


@router.get("/", response_model=List[AgentStatusResponse])
async def list_agents():
    """List all registered agents and their status."""
    supervisor = get_supervisor()
    return [
        AgentStatusResponse(
            name=a["name"],
            role=a["role"],
            state=a["state"],
            tasks_completed=a["tasks_completed"],
            errors=a["errors"],
        )
        for a in supervisor.list_agents()
    ]


@router.get("/{agent_name}")
async def get_agent_status(agent_name: str):
    """Get detailed status of a specific agent."""
    supervisor = get_supervisor()
    agent = supervisor.get_agent(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    return agent.get_status()


@router.post("/workflow/{workflow_name}")
async def execute_workflow(workflow_name: str, request: ChatRequest):
    """Execute a predefined multi-agent workflow."""
    supervisor = get_supervisor()
    message = AgentMessage(
        sender="user",
        content=request.message,
        metadata=request.metadata,
    )
    response = await supervisor.execute_workflow(workflow_name, message)
    return ChatResponse(
        sender=response.sender,
        content=response.content,
        message_type=response.message_type,
        metadata=response.metadata,
    )
