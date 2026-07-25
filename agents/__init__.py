"""
ELIOT Agent Framework

Supervisor-based multi-agent architecture:
- ELIOT CORE (supervisor/controller)
- Planner Agent
- Knowledge Agent
- Analysis Agent
- Research Agent
- Code Agent
- Documentation Agent
- Voice Agent
- Vision Agent

Each agent has: memory, state, permissions, tools, logs, events.
"""

from agents.base import AgentState, AgentRole, BaseAgent
from agents.supervisor import SupervisorAgent
from agents.planner import PlannerAgent
from agents.knowledge import KnowledgeAgent
from agents.analysis import AnalysisAgent
from agents.research import ResearchAgent
from agents.code import CodeAgent
from agents.documentation import DocumentationAgent
from agents.voice import VoiceAgent
from agents.vision import VisionAgent

__all__ = [
    "AgentState",
    "AgentRole",
    "BaseAgent",
    "SupervisorAgent",
    "PlannerAgent",
    "KnowledgeAgent",
    "AnalysisAgent",
    "ResearchAgent",
    "CodeAgent",
    "DocumentationAgent",
    "VoiceAgent",
    "VisionAgent",
]
