"""MCP Server with SSE (Server-Sent Events) transport for HTTP access.

This allows MCP clients to connect over HTTP instead of stdio.
Deployed at mcp.fcp.dev for remote access.
"""

import hmac
import logging
import os
from typing import Any

from fastapi import FastAPI, Request, Response
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool
from starlette.routing import Mount, Route

from fcp.auth.permissions import DEMO_USER_ID, AuthenticatedUser, UserRole
from fcp.mcp.initialize import initialize_tools
from fcp.mcp.registry import tool_registry
from fcp.mcp_tool_dispatch import dispatch_tool_call
from fcp.settings import settings

logger = logging.getLogger(__name__)


def _get_env_user() -> AuthenticatedUser:
    """Get user based on FCP_TOKEN environment variable.

    Used by call_tool to authenticate without HTTP headers (SSE transport).
    - FCP_TOKEN set -> authenticated admin user (full access)
    - FCP_TOKEN not set -> demo user (read-only)
    """
    token = os.environ.get("FCP_TOKEN")
    if token:
        return AuthenticatedUser(user_id="admin", role=UserRole.AUTHENTICATED)
    return AuthenticatedUser(user_id=DEMO_USER_ID, role=UserRole.DEMO)


def get_sse_user(authorization: str | None = None) -> AuthenticatedUser:
    """Authenticate SSE requests using Bearer token.

    Mirrors the auth pattern from fcp.auth.local.get_current_user:
    - No authorization header -> demo user (read-only)
    - Invalid bearer format -> demo user (read-only)
    - Wrong token -> demo user (read-only)
    - Valid token matching FCP_TOKEN -> authenticated admin user
    - No FCP_TOKEN configured -> use token as user_id (backward compat)
    """
    if not authorization:
        return AuthenticatedUser(user_id=DEMO_USER_ID, role=UserRole.DEMO)

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return AuthenticatedUser(user_id=DEMO_USER_ID, role=UserRole.DEMO)

    token = parts[1]

    expected_token = os.environ.get("FCP_TOKEN")
    if expected_token:
        if not hmac.compare_digest(token.encode(), expected_token.encode()):
            logger.warning("SSE: invalid token rejected")
            return AuthenticatedUser(user_id=DEMO_USER_ID, role=UserRole.DEMO)
        return AuthenticatedUser(user_id="admin", role=UserRole.AUTHENTICATED)

    # No FCP_TOKEN configured — deny write access in production
    from fcp.settings import settings

    if settings.is_production:
        return AuthenticatedUser(user_id=DEMO_USER_ID, role=UserRole.DEMO)
    return AuthenticatedUser(user_id=token, role=UserRole.AUTHENTICATED)


# Initialize tools
initialize_tools()

# Create MCP server
mcp_server = Server("fcp-mcp-server")

# Create SSE transport singleton — maps SSE sessions to /messages/ POSTs
sse_transport = SseServerTransport("/messages/")


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools."""
    return tool_registry.get_mcp_tool_list()


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute an MCP tool."""
    user = _get_env_user()
    result = await dispatch_tool_call(name, arguments, user)
    return result.contents


async def handle_sse(request: Request):
    """MCP SSE endpoint — raw ASGI handler (no StreamingResponse wrapper).

    SseServerTransport.connect_sse takes over the response via send().
    """
    async with sse_transport.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp_server.run(
            streams[0],
            streams[1],
            mcp_server.create_initialization_options(),
        )
    # Ensure Starlette always receives a Response object even after SSE disconnect.
    return Response(status_code=204)


# Build the FastAPI app with Starlette routes for ASGI endpoints
app = FastAPI(
    title="FCP MCP Server (SSE)",
    description="Model Context Protocol server with SSE transport",
    version="1.0.0",
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse_transport.handle_post_message),
    ],
)


@app.get("/health")
@app.get("/")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "transport": "sse", "tools": len(tool_registry.list_tools())}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(settings.port),
        log_level="info",
    )
