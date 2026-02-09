"""Tests for MCP rate limit decorator in security/mcp_rate_limit.py."""

import pytest

from fcp.security.mcp_rate_limit import (
    MCPRateLimitError,
    get_mcp_rate_limiter,
    mcp_rate_limited,
)


class TestMCPRateLimitedDecorator:
    """Tests for mcp_rate_limited decorator."""

    @pytest.fixture(autouse=True)
    def reset_limiter(self):
        """Reset rate limiter before each test."""
        limiter = get_mcp_rate_limiter()
        limiter.reset()
        yield

    @pytest.mark.asyncio
    async def test_decorator_allows_call_under_limit(self):
        """Test that decorator allows calls under the rate limit."""

        @mcp_rate_limited
        async def my_tool(name: str, arguments: dict) -> str:
            return f"Called {name}"

        result = await my_tool("get_recent_meals", {"limit": 10})
        assert result == "Called get_recent_meals"

    @pytest.mark.asyncio
    async def test_decorator_records_calls(self):
        """Test that decorator records calls for rate limiting."""
        limiter = get_mcp_rate_limiter()

        @mcp_rate_limited
        async def my_tool(name: str, arguments: dict) -> str:
            return "ok"

        # Make a call
        await my_tool("test_tool", {})

        # Check that remaining is reduced
        remaining = limiter.get_remaining("test_tool")
        assert remaining < limiter.config.get_limit_for_tool("test_tool")

    @pytest.mark.asyncio
    async def test_decorator_raises_when_limit_exceeded(self):
        """Test that decorator raises error when limit exceeded."""

        @mcp_rate_limited
        async def expensive_tool(name: str, arguments: dict) -> str:
            return "ok"

        # Use a tool with a low limit (generate_dietitian_report has limit of 5)
        tool_name = "generate_dietitian_report"

        # Exhaust the limit
        for _ in range(5):
            await expensive_tool(tool_name, {})

        # Next call should raise
        with pytest.raises(MCPRateLimitError) as exc_info:
            await expensive_tool(tool_name, {})

        assert exc_info.value.tool_name == tool_name
        assert exc_info.value.limit == 5

    @pytest.mark.asyncio
    async def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves original function name."""

        @mcp_rate_limited
        async def original_function(name: str, arguments: dict) -> str:
            """Original docstring."""
            return "ok"

        # functools.wraps should preserve __name__ and __doc__
        assert original_function.__name__ == "original_function"

    @pytest.mark.asyncio
    async def test_decorator_passes_all_arguments(self):
        """Test that decorator passes through all arguments."""

        @mcp_rate_limited
        async def my_tool(name: str, arg1: str, arg2: int, kwarg1: str = "default") -> dict:
            return {
                "name": name,
                "arg1": arg1,
                "arg2": arg2,
                "kwarg1": kwarg1,
            }

        result = await my_tool("tool_name", "value1", 42, kwarg1="custom")

        assert result["name"] == "tool_name"
        assert result["arg1"] == "value1"
        assert result["arg2"] == 42
        assert result["kwarg1"] == "custom"
