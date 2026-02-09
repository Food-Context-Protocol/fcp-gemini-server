"""Rate limiting for MCP (Model Context Protocol) server.

MCP servers communicate via stdio, so traditional HTTP rate limiting
doesn't apply. This module provides in-memory rate limiting for
MCP tool calls to prevent abuse from local processes.

Security context: MCP is typically used by trusted local tools
(Claude Desktop, Cursor), but rate limiting still prevents:
- Runaway loops from buggy AI agents
- Excessive API costs from repeated tool calls
- Resource exhaustion on the local machine
"""

import threading
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any


@dataclass
class RateLimitConfig:
    """Configuration for MCP rate limiting."""

    # Maximum calls per window
    max_calls: int = 60

    # Window size in seconds
    window_seconds: int = 60

    # Per-tool overrides (tool_name -> max_calls)
    # More expensive operations get lower limits
    tool_limits: dict[str, int] | None = None

    def get_limit_for_tool(self, tool_name: str) -> int:
        """Get the rate limit for a specific tool."""
        if self.tool_limits and tool_name in self.tool_limits:
            return self.tool_limits[tool_name]
        return self.max_calls


# Default configuration with per-tool limits
DEFAULT_MCP_CONFIG = RateLimitConfig(
    max_calls=60,  # 60 calls per minute default
    window_seconds=60,
    tool_limits={
        # Expensive AI operations - lower limits
        "get_taste_profile": 10,
        "get_meal_suggestions": 20,
        "generate_dietitian_report": 5,
        "generate_blog_post": 10,
        "generate_social_post": 20,
        "generate_cottage_label": 10,
        "generate_image_prompt": 20,
        "delegate_to_food_agent": 10,
        "identify_emerging_trends": 10,
        "plan_food_festival": 5,
        "detect_economic_gaps": 10,
        "standardize_recipe": 20,
        "parse_menu": 10,
        "parse_receipt": 10,
        "log_meal_from_audio": 10,
        # Cheaper operations - higher limits
        "get_recent_meals": 60,
        "search_meals": 60,
        "add_meal": 30,
        "lookup_product": 60,
        "find_nearby_food": 30,
        "add_to_pantry": 30,
        "get_pantry_suggestions": 20,
        "check_pantry_expiry": 30,
        "check_dietary_compatibility": 30,
        "get_flavor_pairings": 30,
        "scale_recipe": 60,
        "donate_meal": 30,
        "sync_to_calendar": 20,
        "save_to_drive": 20,
    },
)


class MCPRateLimitError(Exception):
    """Raised when MCP rate limit is exceeded."""

    def __init__(self, tool_name: str, limit: int, window: int, retry_after: float):
        self.tool_name = tool_name
        self.limit = limit
        self.window = window
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded for '{tool_name}': {limit} calls per {window}s. Retry after {retry_after:.1f}s"
        )


class MCPRateLimiter:
    """In-memory rate limiter for MCP tool calls.

    Uses a sliding window algorithm to track call counts.
    Thread-safe for use with async MCP server.
    """

    def __init__(self, config: RateLimitConfig | None = None):
        self.config = config or DEFAULT_MCP_CONFIG
        # tool_name -> list of timestamps
        self._call_times: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _cleanup_old_calls(self, tool_name: str, now: float) -> None:
        """Remove call timestamps outside the current window."""
        cutoff = now - self.config.window_seconds
        self._call_times[tool_name] = [t for t in self._call_times[tool_name] if t > cutoff]

    def check_rate_limit(self, tool_name: str) -> None:
        """Check if a tool call is allowed.

        Args:
            tool_name: The name of the MCP tool being called.

        Raises:
            MCPRateLimitError: If the rate limit is exceeded.
        """
        with self._lock:
            now = time.time()
            self._cleanup_old_calls(tool_name, now)

            limit = self.config.get_limit_for_tool(tool_name)
            current_count = len(self._call_times[tool_name])

            if current_count >= limit:
                # Calculate retry_after based on oldest call in window
                oldest_call = min(self._call_times[tool_name])
                retry_after = oldest_call + self.config.window_seconds - now
                raise MCPRateLimitError(
                    tool_name=tool_name,
                    limit=limit,
                    window=self.config.window_seconds,
                    retry_after=max(0, retry_after),
                )

    def record_call(self, tool_name: str) -> None:
        """Record a tool call for rate limiting."""
        with self._lock:
            now = time.time()
            self._cleanup_old_calls(tool_name, now)
            self._call_times[tool_name].append(now)

    def check_and_record(self, tool_name: str) -> None:
        """Atomically check and record a tool call for rate limiting."""
        with self._lock:
            now = time.time()
            self._cleanup_old_calls(tool_name, now)
            limit = self.config.get_limit_for_tool(tool_name)
            current_count = len(self._call_times[tool_name])

            if current_count >= limit:
                oldest_call = min(self._call_times[tool_name])
                retry_after = oldest_call + self.config.window_seconds - now
                raise MCPRateLimitError(
                    tool_name=tool_name,
                    limit=limit,
                    window=self.config.window_seconds,
                    retry_after=max(0, retry_after),
                )

            self._call_times[tool_name].append(now)

    def get_remaining(self, tool_name: str) -> int:
        """Get remaining calls allowed for a tool in the current window."""
        with self._lock:
            now = time.time()
            self._cleanup_old_calls(tool_name, now)
            limit = self.config.get_limit_for_tool(tool_name)
            return max(0, limit - len(self._call_times[tool_name]))

    def reset(self, tool_name: str | None = None) -> None:
        """Reset rate limit counters.

        Args:
            tool_name: Reset only this tool, or all tools if None.
        """
        with self._lock:
            if tool_name:
                self._call_times[tool_name] = []
            else:
                self._call_times.clear()


# Global rate limiter instance for MCP server
_mcp_rate_limiter: MCPRateLimiter | None = None


def get_mcp_rate_limiter() -> MCPRateLimiter:
    """Get the global MCP rate limiter instance."""
    global _mcp_rate_limiter
    if _mcp_rate_limiter is None:
        _mcp_rate_limiter = MCPRateLimiter()
    return _mcp_rate_limiter


def check_mcp_rate_limit(tool_name: str) -> None:
    """Check rate limit for an MCP tool call.

    Args:
        tool_name: The name of the tool being called.

    Raises:
        MCPRateLimitError: If rate limit exceeded.
    """
    limiter = get_mcp_rate_limiter()
    limiter.check_and_record(tool_name)


def mcp_rate_limited(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to apply MCP rate limiting to a tool handler.

    Usage:
        @mcp_rate_limited
        async def my_tool_handler(name: str, arguments: dict) -> list[TextContent]:
            ...

    The decorator extracts the tool name from the first argument.
    """

    @wraps(func)
    async def wrapper(name: str, *args: Any, **kwargs: Any) -> Any:
        check_mcp_rate_limit(name)
        return await func(name, *args, **kwargs)

    return wrapper  # type: ignore[return-value]
