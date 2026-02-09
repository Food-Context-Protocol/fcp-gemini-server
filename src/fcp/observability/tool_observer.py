"""Tool execution observability context manager and helpers.

Provides unified observability for MCP tool execution:
- Prometheus metrics (latency, call count)
- OpenTelemetry tracing (spans)
- PostHog analytics (events)
- Demo recording (for allowlisted tools)

Usage (context manager):
    async with ToolExecutionContext(
        tool_name="get_recent_meals",
        arguments={"limit": 10},
        user=authenticated_user,
    ) as ctx:
        result = await execute_tool()
        ctx.set_result(result)

Usage (manual):
    observe_tool_execution(
        tool_name="get_recent_meals",
        arguments={"limit": 10},
        user=authenticated_user,
        duration_seconds=0.5,
        status="success",
        result={"meals": [...]},
    )
"""

import logging
import time
from typing import Any

from fcp.auth.permissions import AuthenticatedUser
from fcp.utils.demo_recording import DemoRecording, save_recording, should_record_tool
from fcp.utils.metrics import record_tool_call

logger = logging.getLogger(__name__)


def observe_tool_execution(
    tool_name: str,
    arguments: dict[str, Any],
    user: AuthenticatedUser,
    duration_seconds: float,
    status: str,
    result: Any = None,
    error_message: str | None = None,
) -> None:
    """Record tool execution observability after the fact.

    Use this when you can't use the context manager pattern.

    Args:
        tool_name: Name of the MCP tool
        arguments: Tool arguments
        user: The authenticated user
        duration_seconds: How long the tool took
        status: "success" or "error"
        result: The tool result (for demo recording)
        error_message: Error message if status is "error"
    """
    user_role = "authenticated" if user.can_write else "demo"

    # Record Prometheus metrics
    record_tool_call(
        tool_name=tool_name,
        status=status,
        user_role=user_role,
        duration_seconds=duration_seconds,
    )

    # Demo recording (for allowlisted tools only)
    if should_record_tool(tool_name):
        recording = DemoRecording(
            tool_name=tool_name,
            arguments=arguments,
            response=result,
            duration_seconds=duration_seconds,
            status=status,
            error_message=error_message,
        )
        save_recording(recording)


class ToolExecutionContext:
    """Async context manager for tool execution observability.

    Handles:
    - Prometheus metrics recording
    - OpenTelemetry span creation
    - PostHog event tracking
    - Demo recording (for allowlisted tools)

    Usage:
        async with ToolExecutionContext(
            tool_name="get_recent_meals",
            arguments={"limit": 10},
            user=authenticated_user,
        ) as ctx:
            result = await tool_implementation()
            ctx.set_result(result)
    """

    def __init__(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        user: AuthenticatedUser,
    ):
        self.tool_name = tool_name
        self.arguments = arguments
        self.user = user
        self.user_role = "authenticated" if user.can_write else "demo"

        self._start_time: float | None = None
        self._status = "success"
        self._error_message: str | None = None
        self._result: Any = None

    async def __aenter__(self) -> "ToolExecutionContext":
        self._start_time = time.perf_counter()
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: Any) -> bool:
        duration = time.perf_counter() - (self._start_time or 0)

        # Handle exceptions
        if exc_type is not None:
            self._status = "error"
            self._error_message = str(exc_val)[:500] if exc_val else "Unknown error"

        # Record Prometheus metrics
        record_tool_call(
            tool_name=self.tool_name,
            status=self._status,
            user_role=self.user_role,
            duration_seconds=duration,
        )

        # Demo recording (for allowlisted tools only)
        if should_record_tool(self.tool_name):
            recording = DemoRecording(
                tool_name=self.tool_name,
                arguments=self.arguments,
                response=self._result,
                duration_seconds=duration,
                status=self._status,
                error_message=self._error_message,
            )
            save_recording(recording)

        # Don't suppress exceptions
        return False

    def set_result(self, result: Any) -> None:
        """Set the tool execution result for recording.

        Args:
            result: The tool's return value (will be sanitized for demo recording)
        """
        self._result = result

    def set_error(self, message: str) -> None:
        """Mark execution as error with message.

        Args:
            message: Error description
        """
        self._status = "error"
        self._error_message = message[:500]

    def _get_result_summary(self) -> str | None:
        """Get a brief summary of the result for tracing."""
        if self._result is None:
            return None

        if isinstance(self._result, dict):
            keys = list(self._result.keys())[:5]
            return f"dict keys: {keys}"
        elif isinstance(self._result, list):
            return f"list len: {len(self._result)}"
        else:
            return f"type: {type(self._result).__name__}"
