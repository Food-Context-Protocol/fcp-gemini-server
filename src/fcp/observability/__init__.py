"""Observability package for FCP server.

Provides unified tool execution observability including:
- Prometheus metrics
- OpenTelemetry tracing
- PostHog analytics
- Demo recording
"""

from fcp.observability.tool_observer import ToolExecutionContext, observe_tool_execution

__all__ = ["ToolExecutionContext", "observe_tool_execution"]
