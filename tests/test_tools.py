"""
Tests for the Tool System.
"""

import pytest
from tools.registry import ToolRegistry, ToolDefinition, ToolCategory, ToolPermission, ToolResult
from tools.builtin import register_builtin_tools, system_info, process_list, list_directory


class TestToolRegistry:
    def test_register_tool(self):
        registry = ToolRegistry()
        def dummy(): return "ok"
        registry.register(
            ToolDefinition(
                name="test_tool",
                description="test",
                category=ToolCategory.SYSTEM,
                permissions_required=[ToolPermission.READ],
            ),
            dummy,
        )
        assert registry.get("test_tool") is not None
        assert "test_tool" in registry.list_tool_names()

    @pytest.mark.asyncio
    async def test_execute_tool(self):
        registry = ToolRegistry()
        async def async_hello(name: str = "world"):
            return f"hello {name}"
        registry.register(
            ToolDefinition(
                name="hello",
                description="test",
                category=ToolCategory.SYSTEM,
                permissions_required=[ToolPermission.READ],
            ),
            async_hello,
        )
        result = await registry.execute("hello", {"name": "test"}, ["read"])
        assert result.success is True
        assert result.output == "hello test"

    @pytest.mark.asyncio
    async def test_permission_denied(self):
        registry = ToolRegistry()
        async def admin_tool(): return "secret"
        registry.register(
            ToolDefinition(
                name="admin_only",
                description="test",
                category=ToolCategory.SYSTEM,
                permissions_required=[ToolPermission.ADMIN],
            ),
            admin_tool,
        )
        result = await registry.execute("admin_only", {}, ["read"])
        assert result.success is False
        assert "Permission denied" in result.error

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        registry = ToolRegistry()
        result = await registry.execute("nonexistent", {}, ["admin"])
        assert result.success is False
        assert "not found" in result.error

    def test_audit_log(self):
        registry = ToolRegistry()
        log = registry.get_audit_log()
        assert isinstance(log, list)


class TestBuiltinTools:
    @pytest.mark.asyncio
    async def test_system_info(self):
        result = await system_info()
        assert "cpu_percent" in result
        assert "memory_percent" in result
        assert "platform" in result

    @pytest.mark.asyncio
    async def test_process_list(self):
        result = await process_list(top_n=5)
        assert isinstance(result, list)
        assert len(result) <= 5
        if result:
            assert "pid" in result[0]

    @pytest.mark.asyncio
    async def test_list_directory(self):
        result = await list_directory("/tmp")
        assert isinstance(result, list)

    def test_register_builtins(self):
        register_builtin_tools()
        from tools.registry import tool_registry
        tools = tool_registry.list_tool_names()
        assert "system_info" in tools
        assert "process_list" in tools
        assert "read_file" in tools
        assert "network_connections" in tools
