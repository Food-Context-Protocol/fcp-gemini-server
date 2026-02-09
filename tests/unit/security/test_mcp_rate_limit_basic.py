"""Tests for MCP rate limiting logic."""

import time
from unittest.mock import patch

from fcp.security.mcp_rate_limit import (
    MCPRateLimiter,
    RateLimitConfig,
    check_mcp_rate_limit,
    get_mcp_rate_limiter,
)


class TestMCPRateLimiter:
    """Tests for MCPRateLimiter class."""

    def test_cleanup_old_calls(self):
        """Test that old calls are removed."""
        limiter = MCPRateLimiter(RateLimitConfig(window_seconds=1))
        limiter._call_times["tool"].append(time.time() - 2)
        limiter.check_rate_limit("tool")
        assert len(limiter._call_times["tool"]) == 0

    def test_get_remaining(self):
        """Test getting remaining calls."""
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=10))
        assert limiter.get_remaining("tool") == 10
        limiter.record_call("tool")
        assert limiter.get_remaining("tool") == 9

    def test_reset_specific_tool(self):
        """Test resetting a specific tool."""
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=10))
        limiter.record_call("tool1")
        limiter.record_call("tool2")

        limiter.reset("tool1")

        assert limiter.get_remaining("tool1") == 10
        assert limiter.get_remaining("tool2") == 9

    def test_reset_all_tools(self):
        """Test resetting all tools."""
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=10))
        limiter.record_call("tool1")
        limiter.record_call("tool2")

        limiter.reset()

        assert limiter.get_remaining("tool1") == 10
        assert limiter.get_remaining("tool2") == 10

    def test_custom_tool_limit(self):
        """Test custom limits for specific tools."""
        config = RateLimitConfig(max_calls=10, tool_limits={"expensive_tool": 2})
        limiter = MCPRateLimiter(config)

        assert limiter.config.get_limit_for_tool("normal_tool") == 10
        assert limiter.config.get_limit_for_tool("expensive_tool") == 2


class TestGlobalHelpers:
    """Tests for global helper functions."""

    def test_get_mcp_rate_limiter_singleton(self):
        """Test that get_mcp_rate_limiter returns a singleton."""
        limiter1 = get_mcp_rate_limiter()
        limiter2 = get_mcp_rate_limiter()
        assert limiter1 is limiter2

    def test_check_mcp_rate_limit_calls_limiter(self):
        """Test check_mcp_rate_limit uses the global limiter."""
        with patch("fcp.security.mcp_rate_limit.get_mcp_rate_limiter") as mock_get:
            mock_limiter = mock_get.return_value

            check_mcp_rate_limit("test_tool")

        mock_limiter.check_and_record.assert_called_once_with("test_tool")
