"""Coverage tests for MCP tool dispatch."""

from __future__ import annotations

import json

import pytest

from fcp.auth.permissions import AuthenticatedUser, UserRole
from fcp.mcp.registry import ToolMetadata
from fcp.mcp_tool_dispatch import _resolve_handler, dispatch_tool_call


@pytest.mark.asyncio
async def test_dispatch_registered_tool():
    """Test dispatching a registered tool."""
    user = AuthenticatedUser(user_id="user-1", role=UserRole.AUTHENTICATED)
    from fcp.mcp.registry import tool, tool_registry

    @tool(name="dev.fcp.test.echo", description="Echo tool")
    async def echo_tool(user_id: str, text: str) -> dict:
        return {"user": user_id, "echo": text}

    try:
        result = await dispatch_tool_call("dev.fcp.test.echo", {"text": "hello"}, user)
        assert result.status == "success"
        data = json.loads(result.contents[0].text)
        assert data["user"] == "user-1"
        assert data["echo"] == "hello"
    finally:
        tool_registry._tools.pop("dev.fcp.test.echo", None)


@pytest.mark.asyncio
async def test_dispatch_unknown_tool():
    """Test dispatching an unknown tool."""
    user = AuthenticatedUser(user_id="user-1", role=UserRole.AUTHENTICATED)
    result = await dispatch_tool_call("dev.fcp.test.unknown", {}, user)
    assert result.status == "error"
    assert result.error_message is not None
    assert "Unknown tool" in result.error_message


@pytest.mark.asyncio
async def test_registry_tool_without_user_id():
    """Registry tools without user_id param should not receive it."""
    from fcp.mcp.registry import tool, tool_registry

    @tool(name="dev.fcp.test.no_user_id", description="Test tool")
    async def no_user_id_tool(input_text: str) -> dict:
        return {"echo": input_text}

    try:
        user = AuthenticatedUser(user_id="user-1", role=UserRole.AUTHENTICATED)
        result = await dispatch_tool_call("dev.fcp.test.no_user_id", {"input_text": "hello"}, user)
        assert result.status == "success"
        data = json.loads(result.contents[0].text)
        assert data["echo"] == "hello"
    finally:
        tool_registry._tools.pop("dev.fcp.test.no_user_id", None)


@pytest.mark.asyncio
async def test_dispatch_write_permission_denied():
    """Test write permission check in dispatch."""
    from fcp.mcp.registry import tool, tool_registry

    @tool(name="dev.fcp.test.write", description="Write tool", requires_write=True)
    async def write_tool() -> dict:
        return {"status": "written"}

    try:
        # Demo user has no write access
        user = AuthenticatedUser(user_id="demo", role=UserRole.DEMO)
        result = await dispatch_tool_call("dev.fcp.test.write", {}, user)
        assert result.status == "error"
        assert result.error_message is not None
        assert "write_permission_denied" in result.error_message
    finally:
        tool_registry._tools.pop("dev.fcp.test.write", None)


def test_resolve_handler_fallback_no_module():
    """_resolve_handler returns stored handler when __module__ is missing."""

    async def _dummy():
        return {}

    handler = _dummy
    handler.__module__ = None  # type: ignore[assignment]

    meta = ToolMetadata(name="test.fallback", description="test", handler=handler)
    assert _resolve_handler(meta) is handler


def test_resolve_handler_fallback_module_not_loaded():
    """_resolve_handler returns stored handler when module is not in sys.modules."""

    async def _dummy():
        return {}

    handler = _dummy
    handler.__module__ = "nonexistent.fake.module"

    meta = ToolMetadata(name="test.fallback2", description="test", handler=handler)
    assert _resolve_handler(meta) is handler
