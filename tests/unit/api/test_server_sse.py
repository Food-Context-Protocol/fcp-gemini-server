"""Tests for MCP SSE server (server_sse.py)."""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from fcp.auth.permissions import DEMO_USER_ID, UserRole


@pytest.fixture
def sse_client():
    """Create test client for SSE server."""
    from fcp.server_sse import app

    return TestClient(app)


@pytest.fixture
def mock_mcp_tools():
    """Mock MCP tool list."""
    return [
        MagicMock(name="dev.fcp.nutrition.analyze_meal"),
        MagicMock(name="dev.fcp.recipes.search"),
        MagicMock(name="dev.fcp.safety.check_recalls"),
    ]


class TestGetSseUser:
    """Tests for get_sse_user function."""

    def test_get_sse_user_no_token_returns_demo(self):
        from fcp.server_sse import get_sse_user

        result = get_sse_user()
        assert result.user_id == DEMO_USER_ID
        assert result.role.value == UserRole.DEMO.value

    def test_get_sse_user_none_returns_demo(self):
        from fcp.server_sse import get_sse_user

        result = get_sse_user(None)
        assert result.user_id == DEMO_USER_ID
        assert result.role.value == UserRole.DEMO.value

    def test_get_sse_user_empty_string_returns_demo(self):
        from fcp.server_sse import get_sse_user

        result = get_sse_user("")
        assert result.user_id == DEMO_USER_ID
        assert result.role.value == UserRole.DEMO.value

    def test_get_sse_user_invalid_bearer_returns_demo(self):
        from fcp.server_sse import get_sse_user

        result = get_sse_user("InvalidToken")
        assert result.user_id == DEMO_USER_ID
        assert result.role.value == UserRole.DEMO.value

    def test_get_sse_user_wrong_prefix_returns_demo(self):
        from fcp.server_sse import get_sse_user

        result = get_sse_user("Basic abc123")
        assert result.user_id == DEMO_USER_ID
        assert result.role.value == UserRole.DEMO.value

    def test_get_sse_user_too_many_parts_returns_demo(self):
        from fcp.server_sse import get_sse_user

        result = get_sse_user("Bearer token extra")
        assert result.user_id == DEMO_USER_ID
        assert result.role.value == UserRole.DEMO.value

    def test_get_sse_user_wrong_token_returns_demo(self):
        from fcp.server_sse import get_sse_user

        with patch.dict(os.environ, {"FCP_TOKEN": "correct-secret"}):
            result = get_sse_user("Bearer wrong-secret")
            assert result.user_id == DEMO_USER_ID
            assert result.role.value == UserRole.DEMO.value

    def test_get_sse_user_valid_token_returns_authenticated(self):
        from fcp.server_sse import get_sse_user

        with patch.dict(os.environ, {"FCP_TOKEN": "my-secret-token"}):
            result = get_sse_user("Bearer my-secret-token")
            assert result.user_id == "admin"
            assert result.role.value == UserRole.AUTHENTICATED.value

    def test_get_sse_user_valid_token_case_insensitive_bearer(self):
        from fcp.server_sse import get_sse_user

        with patch.dict(os.environ, {"FCP_TOKEN": "my-secret-token"}):
            result = get_sse_user("bearer my-secret-token")
            assert result.user_id == "admin"
            assert result.role.value == UserRole.AUTHENTICATED.value

    def test_get_sse_user_no_fcp_token_configured_uses_token_as_id(self):
        from fcp.server_sse import get_sse_user

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("FCP_TOKEN", None)
            result = get_sse_user("Bearer custom-user-id")
            assert result.user_id == "custom-user-id"
            assert result.role.value == UserRole.AUTHENTICATED.value


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_status(self, sse_client, mock_mcp_tools):
        with patch("fcp.server_sse.tool_registry") as mock_registry:
            mock_registry.list_tools.return_value = mock_mcp_tools
            response = sse_client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["transport"] == "sse"
            assert data["tools"] == 3

    def test_health_with_no_tools(self, sse_client):
        with patch("fcp.server_sse.tool_registry") as mock_registry:
            mock_registry.list_tools.return_value = []
            response = sse_client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["tools"] == 0

    def test_root_returns_health(self, sse_client):
        """Root / returns the same health info."""
        with patch("fcp.server_sse.tool_registry") as mock_registry:
            mock_registry.list_tools.return_value = []
            response = sse_client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"


class TestSSETransportSetup:
    """Verify transport is a module-level singleton with correct routes."""

    def test_sse_transport_is_module_singleton(self):
        from mcp.server.sse import SseServerTransport

        from fcp.server_sse import sse_transport

        assert isinstance(sse_transport, SseServerTransport)

    def test_app_has_sse_route(self):
        from fcp.server_sse import app

        route_paths = {r.path for r in app.routes}
        assert "/sse" in route_paths

    def test_app_has_messages_mount(self):
        from fcp.server_sse import app

        route_paths = {r.path for r in app.routes}
        assert any("/messages" in p for p in route_paths)


class TestMCPServerIntegration:
    """Tests for MCP server integration."""

    @pytest.mark.asyncio
    async def test_list_tools_handler(self, mock_mcp_tools):
        from fcp.server_sse import list_tools

        with patch("fcp.server_sse.tool_registry") as mock_registry:
            mock_registry.get_mcp_tool_list.return_value = mock_mcp_tools
            tools = await list_tools()

            assert len(tools) == 3
            assert tools == mock_mcp_tools

    @pytest.mark.asyncio
    async def test_call_tool_handler(self):
        from mcp.types import TextContent

        from fcp.mcp_tool_dispatch import ToolExecutionResult
        from fcp.server_sse import call_tool

        mock_contents = [TextContent(type="text", text='{"success": true}')]
        mock_result = ToolExecutionResult(contents=mock_contents)

        with patch("fcp.server_sse.dispatch_tool_call", return_value=mock_result) as mock_dispatch:
            result = await call_tool(
                name="dev.fcp.nutrition.analyze_meal",
                arguments={"image_url": "https://example.com/food.jpg"},
            )

            mock_dispatch.assert_called_once()
            assert len(result) == 1
            assert "success" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_uses_env_user(self):
        from mcp.types import TextContent

        from fcp.mcp_tool_dispatch import ToolExecutionResult
        from fcp.server_sse import call_tool

        mock_result = ToolExecutionResult(contents=[TextContent(type="text", text="{}")])

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("fcp.server_sse.dispatch_tool_call", return_value=mock_result) as mock_dispatch,
        ):
            await call_tool(name="test_tool", arguments={})
            user_arg = mock_dispatch.call_args[0][2]
            assert user_arg.user_id == DEMO_USER_ID
            assert user_arg.role.value == UserRole.DEMO.value

        with (
            patch.dict("os.environ", {"FCP_TOKEN": "secret"}),
            patch("fcp.server_sse.dispatch_tool_call", return_value=mock_result) as mock_dispatch,
        ):
            await call_tool(name="test_tool", arguments={})
            user_arg = mock_dispatch.call_args[0][2]
            assert user_arg.user_id == "admin"
            assert user_arg.role.value == UserRole.AUTHENTICATED.value


class TestAppConfiguration:
    """Tests for FastAPI app configuration."""

    def test_app_title_and_description(self):
        from fcp.server_sse import app

        assert app.title == "FCP MCP Server (SSE)"
        assert "Model Context Protocol" in app.description
        assert app.version == "1.0.0"

    def test_mcp_server_name(self):
        from fcp.server_sse import mcp_server

        assert mcp_server.name == "fcp-mcp-server"

    def test_main_block_exists(self):
        from fcp import server_sse

        assert hasattr(server_sse, "app")
        assert hasattr(server_sse, "mcp_server")
        assert hasattr(server_sse, "sse_transport")
