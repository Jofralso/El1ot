"""
ELIOT Tool Integration Layer

MCP-compatible tool system with permission checks, target whitelist verification,
and audit logging. Every tool execution goes through:
1. Permission check
2. Target whitelist verification
3. Audit logging
"""

import time
import uuid
import logging
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    NETWORK = "network"
    SYSTEM = "system"
    KNOWLEDGE = "knowledge"
    DOCUMENTATION = "documentation"
    ANALYSIS = "analysis"
    CODE = "code"
    SECURITY = "security"
    VISION = "vision"
    VOICE = "voice"


class ToolPermission(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    ADMIN = "admin"


@dataclass
class ToolDefinition:
    name: str
    description: str
    category: ToolCategory
    permissions_required: List[ToolPermission]
    parameters: Dict[str, Any] = field(default_factory=dict)
    requires_target: bool = False
    enabled: bool = True


@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    tool_name: str = ""
    audit_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class ToolRegistry:
    """Registry of all available tools with their definitions and handlers."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable] = {}
        self._audit_log: List[Dict[str, Any]] = []

    def register(
        self,
        definition: ToolDefinition,
        handler: Callable,
    ):
        self._tools[definition.name] = definition
        self._handlers[definition.name] = handler
        logger.info(f"Tool registered: {definition.name} ({definition.category.value})")

    def unregister(self, name: str):
        self._tools.pop(name, None)
        self._handlers.pop(name, None)

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self, category: Optional[ToolCategory] = None) -> List[ToolDefinition]:
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools

    def list_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    async def execute(
        self,
        name: str,
        params: Dict[str, Any],
        user_permissions: List[str],
        target_whitelist: Optional[List[str]] = None,
    ) -> ToolResult:
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(success=False, error=f"Tool '{name}' not found")

        if not tool.enabled:
            return ToolResult(success=False, error=f"Tool '{name}' is disabled")

        for perm in tool.permissions_required:
            if perm.value not in user_permissions and "admin" not in user_permissions:
                return ToolResult(
                    success=False,
                    error=f"Permission denied: requires '{perm.value}'",
                )

        if tool.requires_target:
            target = params.get("target", "")
            if target_whitelist and target not in target_whitelist:
                return ToolResult(
                    success=False,
                    error=f"Target '{target}' is not in the whitelist",
                )

        handler = self._handlers.get(name)
        if not handler:
            return ToolResult(success=False, error=f"No handler for tool '{name}'")

        start = time.perf_counter()
        try:
            output = await handler(**params) if _is_coroutine(handler) else handler(**params)
            elapsed = time.perf_counter() - start
            result = ToolResult(
                success=True,
                output=output,
                execution_time=elapsed,
                tool_name=name,
            )
        except Exception as e:
            elapsed = time.perf_counter() - start
            result = ToolResult(
                success=False,
                error=str(e),
                execution_time=elapsed,
                tool_name=name,
            )

        self._audit(result, params, user_permissions)
        return result

    def _audit(self, result: ToolResult, params: Dict, permissions: List[str]):
        entry = {
            "audit_id": result.audit_id,
            "tool": result.tool_name,
            "success": result.success,
            "execution_time": result.execution_time,
            "timestamp": time.time(),
            "params": {k: v for k, v in params.items() if k != "audio_data"},
        }
        self._audit_log.append(entry)
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-5000:]

    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        return self._audit_log[-limit:]


def _is_coroutine(func: Callable) -> bool:
    import asyncio
    return asyncio.iscoroutinefunction(func)


# Global registry instance
tool_registry = ToolRegistry()
