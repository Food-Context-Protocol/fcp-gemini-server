"""MCP Server with SSE (Server-Sent Events) transport for HTTP access.

This allows MCP clients to connect over HTTP instead of stdio.
Deployed at mcp.fcp.dev for remote access.
"""

import json
import logging
import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

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
    # No authorization header
    if not authorization:
        return AuthenticatedUser(user_id=DEMO_USER_ID, role=UserRole.DEMO)

    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return AuthenticatedUser(user_id=DEMO_USER_ID, role=UserRole.DEMO)

    token = parts[1]

    # Validate token against FCP_TOKEN if configured
    expected_token = os.environ.get("FCP_TOKEN")
    if expected_token:
        if token != expected_token:
            return AuthenticatedUser(user_id=DEMO_USER_ID, role=UserRole.DEMO)
        return AuthenticatedUser(user_id="admin", role=UserRole.AUTHENTICATED)

    # No FCP_TOKEN configured - treat token as user_id (backward compatible)
    return AuthenticatedUser(user_id=token, role=UserRole.AUTHENTICATED)


# Initialize tools
initialize_tools()

# Create FastAPI app
app = FastAPI(
    title="FCP MCP Server (SSE)",
    description="Model Context Protocol server with SSE transport",
    version="1.0.0",
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# Create MCP server
mcp_server = Server("fcp-mcp-server")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "transport": "sse", "tools": len(tool_registry.list_tools())}


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


@app.get("/")
async def sse_endpoint(request: Request):
    """MCP over SSE endpoint.

    This endpoint establishes an SSE connection for MCP communication.
    Clients send messages to /messages and receive responses via SSE.
    """

    async def event_generator():
        """Generate SSE events."""
        # Create SSE transport
        transport = SseServerTransport("/messages")

        try:
            # Connect SSE streams
            async with transport.connect_sse(
                request.scope,
                request.receive,
                request._send,
            ) as streams:
                # Run MCP server
                await mcp_server.run(
                    streams[0],  # read stream
                    streams[1],  # write stream
                    mcp_server.create_initialization_options(),
                )
        except Exception as e:
            logger.error("SSE connection error: %s", e)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@app.post("/messages")
async def messages_endpoint(request: Request):
    """Receive messages from SSE clients.

    Clients send JSON-RPC messages here, responses come via SSE.
    """
    message = await request.json()
    logger.info("Received SSE message")
    logger.debug("SSE message content: %s", message)

    # Process message through MCP server
    # (Handled by SSE transport internally)

    return {"status": "received"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(settings.port),
        log_level="info",
    )
