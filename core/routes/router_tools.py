"""
Tools API Routes

Endpoints for listing and executing tools.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from tools.registry import tool_registry, ToolCategory, ToolResult
from tools.builtin import register_builtin_tools

router = APIRouter(prefix="/tools", tags=["tools"])
logger = logging.getLogger(__name__)

_builtins_registered = False


def ensure_builtins():
    global _builtins_registered
    if not _builtins_registered:
        register_builtin_tools()
        _builtins_registered = True


class ToolInfo(BaseModel):
    name: str
    description: str
    category: str
    permissions_required: List[str]
    requires_target: bool
    enabled: bool


class ExecuteRequest(BaseModel):
    params: Dict[str, Any] = {}
    user_permissions: List[str] = ["admin"]
    target_whitelist: Optional[List[str]] = None


class ExecuteResponse(BaseModel):
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time: float
    audit_id: str


@router.get("/", response_model=List[ToolInfo])
async def list_tools(category: Optional[str] = None):
    """List all registered tools."""
    ensure_builtins()
    cat = ToolCategory(category) if category else None
    tools = tool_registry.list_tools(category=cat)
    return [
        ToolInfo(
            name=t.name,
            description=t.description,
            category=t.category.value,
            permissions_required=[p.value for p in t.permissions_required],
            requires_target=t.requires_target,
            enabled=t.enabled,
        )
        for t in tools
    ]


@router.post("/{tool_name}/execute", response_model=ExecuteResponse)
async def execute_tool(tool_name: str, request: ExecuteRequest):
    """Execute a registered tool."""
    ensure_builtins()
    result: ToolResult = await tool_registry.execute(
        name=tool_name,
        params=request.params,
        user_permissions=request.user_permissions,
        target_whitelist=request.target_whitelist,
    )
    return ExecuteResponse(
        success=result.success,
        output=result.output,
        error=result.error,
        execution_time=result.execution_time,
        audit_id=result.audit_id,
    )


@router.get("/audit")
async def tool_audit_log(limit: int = 50):
    """Get the tool execution audit log."""
    ensure_builtins()
    return {"entries": tool_registry.get_audit_log(limit)}
