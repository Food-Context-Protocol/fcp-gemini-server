"""Dispatch MCP tool calls for the FCP server."""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass
from typing import Any

from mcp.types import TextContent

from fcp.auth.permissions import AuthenticatedUser
from fcp.mcp.container import resolve_dependencies
from fcp.mcp.registry import ToolMetadata, tool_registry

logger = logging.getLogger(__name__)


def _resolve_handler(meta: ToolMetadata):
    """Resolve the handler from its defining module.

    Looks up the handler by ``__name__`` in the module where it was
    originally defined (``__module__``).  This enables standard
    ``unittest.mock.patch`` at the source-module level to take effect.
    Falls back to the stored reference when the module or attribute is
    unavailable.
    """
    handler = meta.handler
    mod_name = getattr(handler, "__module__", None)
    fn_name = getattr(handler, "__name__", None)
    if mod_name and fn_name:
        mod = sys.modules.get(mod_name)
        if mod is not None:
            return getattr(mod, fn_name, handler)
    return handler


@dataclass
class ToolExecutionResult:
    """Result wrapper for MCP tool execution."""

    contents: list[TextContent]
    status: str = "success"
    error_message: str | None = None
    result_data: Any = None


def _ok(payload: Any, *, indent: int | None = 2) -> ToolExecutionResult:
    text = json.dumps(payload, indent=indent) if indent is not None else str(payload)
    return ToolExecutionResult([TextContent(type="text", text=text)])


def _error(message: str) -> ToolExecutionResult:
    return ToolExecutionResult(
        contents=[TextContent(type="text", text=json.dumps({"error": message}))],
        status="error",
        error_message=message,
    )


def _check_write_permission(user: AuthenticatedUser, tool_name: str) -> ToolExecutionResult | None:
    if not user.can_write:
        return ToolExecutionResult(
            contents=[
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": "write_permission_denied",
                            "message": f"Demo mode: {tool_name} requires write access. Sign in for full access.",
                        }
                    ),
                )
            ],
            status="error",
            error_message="write_permission_denied",
        )
    return None


async def dispatch_tool_call(
    name: str,
    arguments: dict[str, Any],
    user: AuthenticatedUser,
) -> ToolExecutionResult:
    """Execute an MCP tool and return standardized results."""
    try:
        # Check if tool is registered in the new registry
        tool_metadata = tool_registry.get(name)

        # Fallback for short names (e.g., "get_recent_meals" -> "dev.fcp.nutrition.get_recent_meals")
        if not tool_metadata:
            tool_metadata = tool_registry.get_by_short_name(name)

        if tool_metadata:
            # Check permissions
            if tool_metadata.requires_write:
                if error := _check_write_permission(user, name):
                    return error

            # Inject user_id (if accepted) and resolve dependencies
            call_args = dict(arguments)
            if tool_metadata.inject_user_id:
                call_args["user_id"] = user.user_id

            dependencies = resolve_dependencies(tool_metadata.handler, container=None)
            call_args.update(dependencies)

            # Call the registered handler (resolved from its source module
            # so that unittest.mock.patch at the source module is visible)
            handler = _resolve_handler(tool_metadata)
            result = await handler(**call_args)
            return _ok(result)

        return _error(f"Unknown tool: {name}")

    except Exception as e:
        logger.exception("MCP tool execution failed: %s", name)
        return ToolExecutionResult(
            contents=[TextContent(type="text", text=json.dumps({"error": "Tool execution failed"}))],
            status="error",
            error_message=str(e),
        )
