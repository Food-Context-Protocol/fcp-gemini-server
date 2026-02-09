#!/usr/bin/env python3
"""FoodLog Food Context Protocol (FCP) Server - MCP Implementation.

This server exposes FoodLog functionality to AI assistants via MCP.
Gemini CLI, Claude Desktop, Cursor, and other MCP-compatible tools can use this
to access and interact with a user's food journal.
"""

import base64
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Icon, Prompt, Resource, TextContent, Tool

from fcp.auth.local import DEMO_USER_ID
from fcp.auth.permissions import AuthenticatedUser, UserRole
from fcp.mcp.initialize import initialize_tools
from fcp.mcp.registry import tool_registry
from fcp.mcp_resources import get_prompts, get_resources
from fcp.mcp_tool_dispatch import dispatch_tool_call
from fcp.observability.tool_observer import observe_tool_execution
from fcp.security.mcp_rate_limit import MCPRateLimitError, check_mcp_rate_limit

initialize_tools()

# Configure logging to file (stdout reserved for MCP protocol, stderr often discarded by clients)
# Avoid file writes in restricted locations when running in test environments.
if os.environ.get("ENVIRONMENT") == "test" or os.environ.get("PYTEST_CURRENT_TEST"):
    logging.getLogger().addHandler(logging.NullHandler())
else:
    _root_dir = Path(__file__).resolve().parents[2]
    _logs_dir = _root_dir / "logs"
    _logs_dir.mkdir(parents=True, exist_ok=True)
    _log_file = _logs_dir / "mcp-server.log"
    _file_handler = logging.FileHandler(_log_file, mode="a")
    _file_handler.setLevel(logging.DEBUG)
    _file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logging.getLogger().addHandler(_file_handler)
    logging.getLogger().setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


def _load_icon() -> list[Icon] | None:
    """Load the FoodLog icon from assets if available."""
    try:
        # Load logo from package assets (relative to this file)
        # Structure: src/foodlog/fcp/server.py -> src/foodlog/fcp/assets/logo.png
        icon_path = Path(__file__).parent / "assets" / "logo.png"

        if icon_path.exists():
            with open(icon_path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")
                return [Icon(src=f"data:image/png;base64,{b64_data}", mimeType="image/png")]
    except Exception as e:
        logger.warning("Failed to load icon: %s", e)
    return None


# Create MCP server
server = Server("fcp-server", version="1.0.0", icons=_load_icon())


def get_user_id() -> AuthenticatedUser:
    """Get user from environment/token.

    Returns an AuthenticatedUser with either AUTHENTICATED or DEMO role.
    - Missing/invalid token -> Demo user (read-only access)
    - Valid Firebase token -> Authenticated user (full access)
    - Dev mode with token -> Authenticated user (for development)
    """
    token = os.environ.get("FCP_TOKEN", "")
    if not token:
        # No token -> demo mode (read-only)
        logger.debug("No FCP_TOKEN provided, returning demo user")
        return AuthenticatedUser(user_id=DEMO_USER_ID, role=UserRole.DEMO)

    # Security: Only allow fallback in explicit dev mode
    dev_mode = os.environ.get("FCP_DEV_MODE", "").lower() == "true"

    if dev_mode:
        logger.warning("DEV MODE: Using token as user_id. DO NOT use in production!")
        return AuthenticatedUser(user_id=token, role=UserRole.AUTHENTICATED)

    # With local auth, the token IS the user_id
    return AuthenticatedUser(user_id=token, role=UserRole.AUTHENTICATED)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available FCP tools for AI assistants."""
    logger.debug("MCP list_tools called")
    return tool_registry.get_mcp_tool_list()


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute an FCP tool and return results."""
    logger.info("MCP call_tool: %s", name)
    logger.debug("MCP call_tool args: %s", arguments)
    _obs_start_time = time.perf_counter()
    _obs_status = "success"
    _obs_error_message: str | None = None
    _obs_result_data: Any = None

    # Check rate limit before processing
    try:
        check_mcp_rate_limit(name)
    except MCPRateLimitError as e:
        logger.warning("MCP rate limit exceeded: %s", e)
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": "rate_limit_exceeded",
                        "message": str(e),
                        "retry_after": e.retry_after,
                    }
                ),
            )
        ]

    user = get_user_id()

    try:
        result = await dispatch_tool_call(name, arguments, user)
        _obs_status = result.status
        _obs_error_message = result.error_message
        _obs_result_data = result.result_data
        return result.contents

    except Exception as e:
        _obs_status = "error"
        _obs_error_message = str(e)
        logger.exception("MCP tool execution failed: %s", name)
        return [TextContent(type="text", text=json.dumps({"error": "Internal server error"}))]

    finally:
        # Record observability metrics for all tool executions
        _obs_duration = time.perf_counter() - _obs_start_time
        observe_tool_execution(
            tool_name=name,
            arguments=arguments,
            user=user,
            duration_seconds=_obs_duration,
            status=_obs_status,
            result=_obs_result_data,
            error_message=_obs_error_message,
        )


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available FCP resources."""
    return get_resources()


@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available FCP prompts."""
    return get_prompts()


async def run_mcp_server():
    """Run the FCP MCP server."""
    logger.info("MCP server starting on stdio...")
    async with stdio_server() as (read_stream, write_stream):
        logger.info("MCP server ready, waiting for connections")
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )
    logger.info("MCP server shutting down")


def main():
    """CLI entry point for fcp-server command.

    Supports both MCP (stdio) and HTTP modes via command-line arguments.
    If no arguments provided, defaults to MCP mode.
    """
    import argparse
    import asyncio
    import sys

    parser = argparse.ArgumentParser(description="FCP Server - Food Context Protocol Reference Implementation")
    parser.add_argument("--mcp", action="store_true", help="Run MCP server on stdio (default if no mode specified)")
    parser.add_argument("--http", action="store_true", help="Run HTTP API server on port 8080")
    parser.add_argument("--port", type=int, default=8080, help="Port for HTTP server (default: 8080)")

    args = parser.parse_args()

    # Default to MCP if no mode specified
    if not args.mcp and not args.http:
        args.mcp = True

    # Can't run both at once
    if args.mcp and args.http:
        print("Error: Cannot run both --mcp and --http simultaneously", file=sys.stderr)
        sys.exit(1)

    if args.mcp:
        # Run MCP server
        asyncio.run(run_mcp_server())
    elif args.http:
        # Run HTTP server via uvicorn
        import uvicorn

        from fcp.api import app

        logger.info(f"Starting HTTP server on port {args.port}...")
        uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
