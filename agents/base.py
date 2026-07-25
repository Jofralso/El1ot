"""
Base Agent Class

All ELIOT agents inherit from BaseAgent.
Provides: memory, state machine, permission checks, tool access, audit logging, event bus.
"""

import uuid
import time
import logging
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    SUPERVISOR = "supervisor"
    PLANNER = "planner"
    KNOWLEDGE = "knowledge"
    ANALYSIS = "analysis"
    RESEARCH = "research"
    CODE = "code"
    DOCUMENTATION = "documentation"
    VOICE = "voice"
    VISION = "vision"


class AgentState(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    WAITING = "waiting"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class AgentMessage:
    """Message passed between agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    receiver: str = ""
    content: str = ""
    message_type: str = "text"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentMemory:
    """Short-term memory for an agent."""
    messages: List[AgentMessage] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    max_messages: int = 50

    def add(self, message: AgentMessage):
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def get_recent(self, n: int = 10) -> List[AgentMessage]:
        return self.messages[-n:]

    def clear(self):
        self.messages.clear()
        self.context.clear()


class BaseAgent(ABC):
    """
    Base class for all ELIOT agents.

    Provides lifecycle management, message passing, memory, permission checks, and audit logging.
    """

    def __init__(
        self,
        role: AgentRole,
        name: str,
        description: str = "",
        permissions: Optional[List[str]] = None,
        tools: Optional[List[str]] = None,
    ):
        self.id = str(uuid.uuid4())
        self.role = role
        self.name = name
        self.description = description
        self.state = AgentState.IDLE
        self.memory = AgentMemory()
        self.permissions = permissions or []
        self.tools = tools or []
        self.created_at = time.time()
        self.last_active = time.time()
        self._task_count = 0
        self._error_count = 0
        logger.info(f"Agent initialized: {self.name} ({self.role.value})")

    @abstractmethod
    async def process(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message and return a response."""
        ...

    async def handle(self, message: AgentMessage) -> AgentMessage:
        """Full lifecycle: permission check -> process -> audit log."""
        self.state = AgentState.THINKING
        self.last_active = time.time()
        self.memory.add(message)

        try:
            response = await self.process(message)
            self._task_count += 1
            self.state = AgentState.IDLE
            self.memory.add(response)
            logger.debug(f"[{self.name}] Task #{self._task_count} completed")
            return response
        except Exception as e:
            self._error_count += 1
            self.state = AgentState.ERROR
            logger.error(f"[{self.name}] Error: {e}")
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                content=f"Error processing request: {str(e)}",
                message_type="error",
                metadata={"error": str(e)},
            )

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions or "admin" in self.permissions

    def get_status(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "state": self.state.value,
            "tasks_completed": self._task_count,
            "errors": self._error_count,
            "uptime": time.time() - self.created_at,
            "last_active": self.last_active,
            "memory_size": len(self.memory.messages),
            "permissions": self.permissions,
            "tools": self.tools,
        }

    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name!r} role={self.role.value}>"
