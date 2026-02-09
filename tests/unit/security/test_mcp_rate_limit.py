"""Tests for MCP rate limiting."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from fcp.security.mcp_rate_limit import (
    DEFAULT_MCP_CONFIG,
    MCPRateLimiter,
    MCPRateLimitError,
    RateLimitConfig,
    check_mcp_rate_limit,
    get_mcp_rate_limiter,
    mcp_rate_limited,
)


class FakeTime:
    """Simple controllable clock for time-based tests."""

    def __init__(self, start: float = 0.0) -> None:
        self._current = start

    def time(self) -> float:
        return self._current

    def advance(self, seconds: float) -> None:
        self._current += seconds


@pytest.fixture
def fake_time(monkeypatch: pytest.MonkeyPatch) -> FakeTime:
    """Patch rate limiter time source to avoid real sleeping."""
    fake = FakeTime()
    monkeypatch.setattr("fcp.security.mcp_rate_limit.time.time", fake.time)
    return fake


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_default_config_values(self) -> None:
        config = RateLimitConfig()
        assert config.max_calls == 60
        assert config.window_seconds == 60
        assert config.tool_limits is None

    def test_get_limit_for_tool_default(self) -> None:
        config = RateLimitConfig(max_calls=100)
        assert config.get_limit_for_tool("unknown_tool") == 100

    def test_get_limit_for_tool_override(self) -> None:
        config = RateLimitConfig(
            max_calls=100,
            tool_limits={"expensive_tool": 10},
        )
        assert config.get_limit_for_tool("expensive_tool") == 10
        assert config.get_limit_for_tool("other_tool") == 100

    def test_default_mcp_config_has_tool_limits(self) -> None:
        assert DEFAULT_MCP_CONFIG.tool_limits is not None
        assert "get_taste_profile" in DEFAULT_MCP_CONFIG.tool_limits
        assert DEFAULT_MCP_CONFIG.tool_limits["get_taste_profile"] == 10


class TestMCPRateLimiter:
    """Tests for MCPRateLimiter."""

    def test_allows_calls_under_limit(self) -> None:
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=5, window_seconds=60))
        for _ in range(5):
            limiter.check_rate_limit("test_tool")
            limiter.record_call("test_tool")

    def test_blocks_calls_over_limit(self) -> None:
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=3, window_seconds=60))
        for _ in range(3):
            limiter.check_rate_limit("test_tool")
            limiter.record_call("test_tool")
        with pytest.raises(MCPRateLimitError) as exc_info:
            limiter.check_rate_limit("test_tool")
        assert exc_info.value.tool_name == "test_tool"
        assert exc_info.value.limit == 3
        assert exc_info.value.window == 60
        assert exc_info.value.retry_after >= 0

    def test_separate_limits_per_tool(self) -> None:
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=2, window_seconds=60))
        for _ in range(2):
            limiter.check_rate_limit("tool_a")
            limiter.record_call("tool_a")
        with pytest.raises(MCPRateLimitError):
            limiter.check_rate_limit("tool_a")
        limiter.check_rate_limit("tool_b")
        limiter.record_call("tool_b")

    def test_window_expiration(self, fake_time: FakeTime) -> None:
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=2, window_seconds=1))
        for _ in range(2):
            limiter.check_rate_limit("test_tool")
            limiter.record_call("test_tool")
        with pytest.raises(MCPRateLimitError):
            limiter.check_rate_limit("test_tool")
        fake_time.advance(1.1)
        limiter.check_rate_limit("test_tool")
        limiter.record_call("test_tool")

    def test_get_remaining(self) -> None:
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=5, window_seconds=60))
        assert limiter.get_remaining("test_tool") == 5
        limiter.record_call("test_tool")
        assert limiter.get_remaining("test_tool") == 4
        limiter.record_call("test_tool")
        limiter.record_call("test_tool")
        assert limiter.get_remaining("test_tool") == 2

    def test_reset_single_tool(self) -> None:
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=2, window_seconds=60))
        limiter.record_call("tool_a")
        limiter.record_call("tool_a")
        limiter.record_call("tool_b")
        assert limiter.get_remaining("tool_a") == 0
        assert limiter.get_remaining("tool_b") == 1
        limiter.reset("tool_a")
        assert limiter.get_remaining("tool_a") == 2
        assert limiter.get_remaining("tool_b") == 1

    def test_reset_all_tools(self) -> None:
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=5, window_seconds=60))
        limiter.record_call("tool_a")
        limiter.record_call("tool_b")
        limiter.reset()
        assert limiter.get_remaining("tool_a") == 5
        assert limiter.get_remaining("tool_b") == 5

    def test_tool_specific_limits(self) -> None:
        limiter = MCPRateLimiter(
            RateLimitConfig(
                max_calls=10,
                window_seconds=60,
                tool_limits={"expensive_tool": 2},
            )
        )
        limiter.record_call("expensive_tool")
        limiter.record_call("expensive_tool")
        with pytest.raises(MCPRateLimitError) as exc_info:
            limiter.check_rate_limit("expensive_tool")
        assert exc_info.value.limit == 2
        for _ in range(10):
            limiter.check_rate_limit("regular_tool")
            limiter.record_call("regular_tool")


class TestMCPRateLimitError:
    """Tests for MCPRateLimitError."""

    def test_error_message_format(self) -> None:
        error = MCPRateLimitError(
            tool_name="test_tool",
            limit=10,
            window=60,
            retry_after=5.5,
        )
        assert "test_tool" in str(error)
        assert "10" in str(error)
        assert "60" in str(error)
        assert "5.5" in str(error)

    def test_error_attributes(self) -> None:
        error = MCPRateLimitError(
            tool_name="my_tool",
            limit=5,
            window=30,
            retry_after=10.0,
        )
        assert error.tool_name == "my_tool"
        assert error.limit == 5
        assert error.window == 30
        assert error.retry_after == 10.0


class TestGlobalRateLimiter:
    """Tests for global rate limiter functions."""

    def test_get_mcp_rate_limiter_singleton(self) -> None:
        limiter1 = get_mcp_rate_limiter()
        limiter2 = get_mcp_rate_limiter()
        assert limiter1 is limiter2

    def test_check_mcp_rate_limit_records_call(self) -> None:
        limiter = get_mcp_rate_limiter()
        limiter.reset()
        initial = limiter.get_remaining("test_check_tool")
        check_mcp_rate_limit("test_check_tool")
        assert limiter.get_remaining("test_check_tool") == initial - 1

    def test_check_mcp_rate_limit_raises_on_exceeded(self) -> None:
        limiter = get_mcp_rate_limiter()
        tool_name = "generate_dietitian_report"
        limiter.reset(tool_name)
        config = limiter.config
        for _ in range(config.get_limit_for_tool(tool_name)):
            check_mcp_rate_limit(tool_name)
        with pytest.raises(MCPRateLimitError):
            check_mcp_rate_limit(tool_name)
        limiter.reset(tool_name)


class TestRateLimiterConcurrency:
    """Tests for rate limiter concurrency behavior."""

    @pytest.mark.asyncio
    async def test_concurrent_asyncio_tasks_count_all_calls(self) -> None:
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=100, window_seconds=60))
        tool_name = "async_test_tool"
        num_tasks = 50

        async def make_call() -> None:
            limiter.check_rate_limit(tool_name)
            limiter.record_call(tool_name)

        await asyncio.gather(*[make_call() for _ in range(num_tasks)])
        assert limiter.get_remaining(tool_name) == 100 - num_tasks

    @pytest.mark.asyncio
    async def test_concurrent_asyncio_tasks_block_when_exceeded(self) -> None:
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=10, window_seconds=60))
        tool_name = "async_block_tool"
        num_tasks = 20
        successful_calls = []
        blocked_calls = []

        async def make_call() -> None:
            try:
                limiter.check_rate_limit(tool_name)
                limiter.record_call(tool_name)
                successful_calls.append(1)
            except MCPRateLimitError:
                blocked_calls.append(1)

        await asyncio.gather(*[make_call() for _ in range(num_tasks)])
        assert len(successful_calls) == 10
        assert len(blocked_calls) == 10

    def test_concurrent_threads_count_all_calls(self) -> None:
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=100, window_seconds=60))
        tool_name = "thread_test_tool"
        num_threads = 50

        def make_call() -> None:
            limiter.check_rate_limit(tool_name)
            limiter.record_call(tool_name)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_call) for _ in range(num_threads)]
            for future in futures:
                future.result()

        remaining = limiter.get_remaining(tool_name)
        assert remaining == 100 - num_threads

    def test_concurrent_threads_atomic_increments(self) -> None:
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=1000, window_seconds=60))
        tool_name = "atomic_test_tool"
        num_threads = 100
        calls_per_thread = 10

        def make_calls() -> None:
            for _ in range(calls_per_thread):
                limiter.record_call(tool_name)

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_calls) for _ in range(num_threads)]
            for future in futures:
                future.result()

        expected_calls = num_threads * calls_per_thread
        actual_calls = 1000 - limiter.get_remaining(tool_name)
        assert actual_calls == expected_calls

    def test_expired_timestamps_cleanup(self, fake_time: FakeTime) -> None:
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=10, window_seconds=1))
        tool_name = "cleanup_test_tool"
        for _ in range(5):
            limiter.record_call(tool_name)
        assert len(limiter._call_times[tool_name]) == 5
        fake_time.advance(1.1)
        limiter.get_remaining(tool_name)
        assert len(limiter._call_times[tool_name]) == 0

    def test_partial_cleanup_of_expired_timestamps(self, fake_time: FakeTime) -> None:
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=10, window_seconds=1))
        tool_name = "partial_cleanup_tool"
        for _ in range(3):
            limiter.record_call(tool_name)
        fake_time.advance(0.6)
        for _ in range(2):
            limiter.record_call(tool_name)
        fake_time.advance(0.5)
        limiter.get_remaining(tool_name)
        assert len(limiter._call_times[tool_name]) == 2

    def test_float_precision_boundary_conditions(self) -> None:
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=5, window_seconds=60))
        tool_name = "precision_test_tool"
        now = time.time()
        limiter._call_times[tool_name] = [
            now - 0.000001,
            now - 0.0000001,
            now,
            now + 0.000001,
        ]
        assert limiter.get_remaining(tool_name) == 1

    def test_float_precision_at_window_boundary(self) -> None:
        window_seconds = 60
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=10, window_seconds=window_seconds))
        tool_name = "boundary_precision_tool"
        now = time.time()
        cutoff = now - window_seconds
        limiter._call_times[tool_name] = [
            cutoff,
            cutoff + 0.0001,
            cutoff + 0.001,
        ]
        remaining = limiter.get_remaining(tool_name)
        assert len(limiter._call_times[tool_name]) == 2
        assert remaining == 8

    def test_concurrent_check_and_record_race_condition(self) -> None:
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=5, window_seconds=60))
        tool_name = "race_test_tool"
        errors = []
        successes = []

        def check_then_record() -> None:
            try:
                limiter.check_rate_limit(tool_name)
                limiter.record_call(tool_name)
                successes.append(1)
            except MCPRateLimitError:
                errors.append(1)

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(check_then_record) for _ in range(10)]
            for future in futures:
                future.result()

        assert len(successes) + len(errors) == 10
        assert len(successes) >= 5

    @pytest.mark.asyncio
    async def test_high_frequency_async_calls(self) -> None:
        limiter = MCPRateLimiter(RateLimitConfig(max_calls=1000, window_seconds=60))
        tool_name = "high_freq_tool"

        async def burst_calls(count: int) -> None:
            for _ in range(count):
                limiter.record_call(tool_name)

        await asyncio.gather(*[burst_calls(100) for _ in range(5)])
        assert limiter.get_remaining(tool_name) == 500


class TestMCPRateLimitedDecorator:
    """Tests for the mcp_rate_limited decorator."""

    @pytest.mark.asyncio
    async def test_decorator_allows_call_under_limit(self) -> None:
        limiter = get_mcp_rate_limiter()
        tool_name = "decorator_test_tool"
        limiter.reset(tool_name)
        call_count = 0

        @mcp_rate_limited
        async def test_handler(name: str, arg1: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"Result for {name}: {arg1}"

        result = await test_handler(tool_name, "test_arg")
        assert result == f"Result for {tool_name}: test_arg"
        assert call_count == 1
        limiter.reset(tool_name)

    @pytest.mark.asyncio
    async def test_decorator_blocks_when_limit_exceeded(self) -> None:
        limiter = get_mcp_rate_limiter()
        tool_name = "generate_dietitian_report"
        limiter.reset(tool_name)

        @mcp_rate_limited
        async def test_handler(name: str) -> str:
            return "OK"

        limit = limiter.config.get_limit_for_tool(tool_name)
        for _ in range(limit):
            await test_handler(tool_name)

        with pytest.raises(MCPRateLimitError) as exc_info:
            await test_handler(tool_name)

        assert exc_info.value.tool_name == tool_name
        limiter.reset(tool_name)

    @pytest.mark.asyncio
    async def test_decorator_preserves_function_metadata(self) -> None:
        @mcp_rate_limited
        async def my_handler_with_docs(name: str, value: int) -> dict:
            """This is the docstring."""
            return {"name": name, "value": value}

        assert my_handler_with_docs.__name__ == "my_handler_with_docs"
        assert my_handler_with_docs.__doc__ == "This is the docstring."

    @pytest.mark.asyncio
    async def test_decorator_with_kwargs(self) -> None:
        limiter = get_mcp_rate_limiter()
        tool_name = "kwargs_test_tool"
        limiter.reset(tool_name)

        @mcp_rate_limited
        async def handler_with_kwargs(name: str, *, option: bool = False) -> dict:
            return {"name": name, "option": option}

        result = await handler_with_kwargs(tool_name, option=True)
        assert result == {"name": tool_name, "option": True}
        limiter.reset(tool_name)
