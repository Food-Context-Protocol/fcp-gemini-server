"""Tests for MCP SSE server (server_sse.py)."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from fcp.auth.permissions import DEMO_USER_ID, AuthenticatedUser, UserRole


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
        """No authorization header returns demo user."""
        from fcp.server_sse import get_sse_user

        result = get_sse_user()
        assert result.user_id == DEMO_USER_ID
        assert result.role.value == UserRole.DEMO.value

    def test_get_sse_user_none_returns_demo(self):
        """Explicit None authorization returns demo user."""
        from fcp.server_sse import get_sse_user

        result = get_sse_user(None)
        assert result.user_id == DEMO_USER_ID
        assert result.role.value == UserRole.DEMO.value

    def test_get_sse_user_empty_string_returns_demo(self):
        """Empty string authorization returns demo user."""
        from fcp.server_sse import get_sse_user

        result = get_sse_user("")
        assert result.user_id == DEMO_USER_ID
        assert result.role.value == UserRole.DEMO.value

    def test_get_sse_user_invalid_bearer_returns_demo(self):
        """Invalid bearer format returns demo user."""
        from fcp.server_sse import get_sse_user

        # Only one part (no space)
        result = get_sse_user("InvalidToken")
        assert result.user_id == DEMO_USER_ID
        assert result.role.value == UserRole.DEMO.value

    def test_get_sse_user_wrong_prefix_returns_demo(self):
        """Non-Bearer prefix returns demo user."""
        from fcp.server_sse import get_sse_user

        result = get_sse_user("Basic abc123")
        assert result.user_id == DEMO_USER_ID
        assert result.role.value == UserRole.DEMO.value

    def test_get_sse_user_too_many_parts_returns_demo(self):
        """Too many parts in authorization returns demo user."""
        from fcp.server_sse import get_sse_user

        result = get_sse_user("Bearer token extra")
        assert result.user_id == DEMO_USER_ID
        assert result.role.value == UserRole.DEMO.value

    def test_get_sse_user_wrong_token_returns_demo(self):
        """Wrong token returns demo user when FCP_TOKEN is configured."""
        from fcp.server_sse import get_sse_user

        with patch.dict(os.environ, {"FCP_TOKEN": "correct-secret"}):
            result = get_sse_user("Bearer wrong-secret")
            assert result.user_id == DEMO_USER_ID
            assert result.role.value == UserRole.DEMO.value

    def test_get_sse_user_valid_token_returns_authenticated(self):
        """Correct token returns authenticated admin user."""
        from fcp.server_sse import get_sse_user

        with patch.dict(os.environ, {"FCP_TOKEN": "my-secret-token"}):
            result = get_sse_user("Bearer my-secret-token")
            assert result.user_id == "admin"
            assert result.role.value == UserRole.AUTHENTICATED.value

    def test_get_sse_user_valid_token_case_insensitive_bearer(self):
        """Bearer prefix is case-insensitive."""
        from fcp.server_sse import get_sse_user

        with patch.dict(os.environ, {"FCP_TOKEN": "my-secret-token"}):
            result = get_sse_user("bearer my-secret-token")
            assert result.user_id == "admin"
            assert result.role.value == UserRole.AUTHENTICATED.value

    def test_get_sse_user_no_fcp_token_configured_uses_token_as_id(self):
        """When no FCP_TOKEN is configured, token is used as user_id."""
        from fcp.server_sse import get_sse_user

        with patch.dict(os.environ, {}, clear=True):
            # Ensure FCP_TOKEN is not set
            os.environ.pop("FCP_TOKEN", None)
            result = get_sse_user("Bearer custom-user-id")
            assert result.user_id == "custom-user-id"
            assert result.role.value == UserRole.AUTHENTICATED.value


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_status(self, sse_client, mock_mcp_tools):
        """Health endpoint returns healthy status with tool count."""
        with patch("fcp.server_sse.tool_registry") as mock_registry:
            mock_registry.list_tools.return_value = mock_mcp_tools
            response = sse_client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["transport"] == "sse"
            assert data["tools"] == 3

    def test_health_with_no_tools(self, sse_client):
        """Health endpoint works even with no tools."""
        with patch("fcp.server_sse.tool_registry") as mock_registry:
            mock_registry.list_tools.return_value = []
            response = sse_client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["tools"] == 0

    def test_health_returns_tool_count(self, sse_client):
        """Health endpoint returns the correct tool count."""
        with patch("fcp.server_sse.tool_registry") as mock_registry:
            mock_registry.list_tools.return_value = [MagicMock() for _ in range(5)]
            response = sse_client.get("/health")

            data = response.json()
            assert data["tools"] == 5


class TestMessagesEndpoint:
    """Tests for /messages endpoint."""

    def test_messages_endpoint_accepts_json_rpc(self, sse_client):
        """Messages endpoint accepts JSON-RPC messages."""
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }

        response = sse_client.post("/messages", json=message)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"

    def test_messages_endpoint_logs_message(self, sse_client):
        """Messages endpoint logs received messages."""
        message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "test_tool"},
        }

        with patch("fcp.server_sse.logger") as mock_logger:
            response = sse_client.post("/messages", json=message)

            assert response.status_code == 200
            mock_logger.info.assert_called_once()

    def test_messages_endpoint_with_empty_params(self, sse_client):
        """Messages endpoint handles messages with no params."""
        message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "initialize",
        }

        response = sse_client.post("/messages", json=message)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"


class TestMCPServerIntegration:
    """Tests for MCP server integration."""

    @pytest.mark.asyncio
    async def test_list_tools_handler(self, mock_mcp_tools):
        """Test list_tools handler returns tool list."""
        from fcp.server_sse import list_tools

        with patch("fcp.server_sse.tool_registry") as mock_registry:
            mock_registry.get_mcp_tool_list.return_value = mock_mcp_tools
            tools = await list_tools()

            assert len(tools) == 3
            assert tools == mock_mcp_tools

    @pytest.mark.asyncio
    async def test_call_tool_handler(self):
        """Test call_tool handler dispatches and returns result contents."""
        from mcp.types import TextContent

        from fcp.mcp_tool_dispatch import ToolExecutionResult
        from fcp.server_sse import call_tool

        mock_contents = [TextContent(type="text", text='{"success": true, "data": "meal analyzed"}')]
        mock_result = ToolExecutionResult(contents=mock_contents)

        with patch("fcp.server_sse.dispatch_tool_call", return_value=mock_result) as mock_dispatch:
            result = await call_tool(
                name="dev.fcp.nutrition.analyze_meal",
                arguments={"image_url": "https://example.com/food.jpg"},
            )

            # Verify dispatch was called correctly
            mock_dispatch.assert_called_once()
            call_args = mock_dispatch.call_args
            assert call_args[0][0] == "dev.fcp.nutrition.analyze_meal"
            assert call_args[0][1]["image_url"] == "https://example.com/food.jpg"

            # Verify result is the contents from ToolExecutionResult
            assert len(result) == 1
            assert result[0].type == "text"
            assert "success" in result[0].text
            assert "meal analyzed" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_uses_env_user(self):
        """Test call_tool delegates to _get_env_user for authentication."""
        from mcp.types import TextContent

        from fcp.mcp_tool_dispatch import ToolExecutionResult
        from fcp.server_sse import call_tool

        mock_result = ToolExecutionResult(contents=[TextContent(type="text", text="{}")])

        # Without FCP_TOKEN -> demo user
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("fcp.server_sse.dispatch_tool_call", return_value=mock_result) as mock_dispatch,
        ):
            await call_tool(name="test_tool", arguments={})
            user_arg = mock_dispatch.call_args[0][2]
            assert isinstance(user_arg, AuthenticatedUser)
            assert user_arg.user_id == DEMO_USER_ID
            assert user_arg.role.value == UserRole.DEMO.value

        # With FCP_TOKEN -> authenticated admin
        with (
            patch.dict("os.environ", {"FCP_TOKEN": "secret"}),
            patch("fcp.server_sse.dispatch_tool_call", return_value=mock_result) as mock_dispatch,
        ):
            await call_tool(name="test_tool", arguments={})
            user_arg = mock_dispatch.call_args[0][2]
            assert isinstance(user_arg, AuthenticatedUser)
            assert user_arg.user_id == "admin"
            assert user_arg.role.value == UserRole.AUTHENTICATED.value


class TestSSEEndpoint:
    """Tests for / endpoint (SSE)."""

    def test_sse_endpoint_returns_event_stream(self, sse_client):
        """SSE endpoint returns event stream content type."""
        with patch("fcp.server_sse.SseServerTransport") as mock_transport:
            # Mock the transport to avoid actual SSE connection
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = (AsyncMock(), AsyncMock())  # read/write streams
            mock_context.__aexit__.return_value = None
            mock_transport.return_value.connect_sse.return_value = mock_context

            with patch("fcp.server_sse.mcp_server.run", new=AsyncMock()):
                response = sse_client.get("/")

                assert response.status_code == 200
                assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
                assert response.headers["cache-control"] == "no-cache"
                assert response.headers["connection"] == "keep-alive"

    def test_sse_endpoint_has_correct_headers(self, sse_client):
        """SSE endpoint sets correct streaming headers."""
        with patch("fcp.server_sse.SseServerTransport") as mock_transport:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = (AsyncMock(), AsyncMock())
            mock_context.__aexit__.return_value = None
            mock_transport.return_value.connect_sse.return_value = mock_context

            with patch("fcp.server_sse.mcp_server.run", new=AsyncMock()):
                response = sse_client.get("/")

                # Check anti-buffering headers
                assert "x-accel-buffering" in response.headers
                assert response.headers["x-accel-buffering"] == "no"

    def test_sse_endpoint_error_handling(self, sse_client):
        """SSE endpoint handles connection errors gracefully."""
        with patch("fcp.server_sse.SseServerTransport") as mock_transport:
            # Simulate connection error
            mock_context = MagicMock()
            mock_context.__aenter__.side_effect = RuntimeError("Connection failed")
            mock_transport.return_value.connect_sse.return_value = mock_context

            response = sse_client.get("/")

            assert response.status_code == 200
            # Error should be in the stream, not raise exception


class TestAppConfiguration:
    """Tests for FastAPI app configuration."""

    def test_app_title_and_description(self, sse_client):
        """App has correct title and description."""
        from fcp.server_sse import app

        assert app.title == "FCP MCP Server (SSE)"
        assert "Model Context Protocol" in app.description
        assert app.version == "1.0.0"

    def test_app_has_required_routes(self, sse_client):
        """App has all required routes."""
        from fcp.server_sse import app

        routes = {route.path for route in app.routes}

        assert "/health" in routes
        assert "/" in routes
        assert "/messages" in routes

    def test_mcp_server_name(self):
        """MCP server has correct name."""
        from fcp.server_sse import mcp_server

        assert mcp_server.name == "fcp-mcp-server"


class TestMainEntrypoint:
    """Tests for __main__ entrypoint."""

    def test_main_block_exists(self):
        """Module has __main__ block for CLI usage."""
        # Simply verify the module can be imported and has the expected structure
        from fcp import server_sse

        assert hasattr(server_sse, "app")
        assert hasattr(server_sse, "mcp_server")

        # Verify app is configured correctly for uvicorn
        assert server_sse.app.title == "FCP MCP Server (SSE)"
