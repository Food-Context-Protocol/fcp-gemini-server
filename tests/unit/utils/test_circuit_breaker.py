"""Tests for circuit breaker implementation."""

import time

import pytest

from fcp.utils.circuit_breaker import (
    CircuitBreakerError,
    CircuitBreakerState,
    CircuitState,
    circuit_breaker,
    gemini_circuit_breaker,
    get_all_circuit_breakers,
    get_circuit_breaker,
    reset_circuit_breaker,
)


class TestCircuitBreakerState:
    """Tests for CircuitBreakerState."""

    @pytest.fixture
    def cb(self):
        """Create a fresh circuit breaker for each test."""
        return CircuitBreakerState(
            name="test",
            failure_threshold=3,
            recovery_timeout=1.0,
            half_open_max_calls=2,
        )

    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self, cb):
        """Circuit breaker starts in closed state."""
        assert cb.state == CircuitState.CLOSED
        assert await cb.can_execute() is True

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self, cb):
        """Successful calls reset failure count."""
        cb.failure_count = 2
        await cb.record_success()
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_failures_open_circuit(self, cb):
        """Circuit opens after threshold failures."""
        for i in range(3):
            await cb.record_failure(Exception(f"Error {i}"))

        assert cb.state == CircuitState.OPEN
        assert await cb.can_execute() is False

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(self, cb):
        """Circuit transitions to half-open after recovery timeout."""
        # Open the circuit
        for i in range(3):
            await cb.record_failure(Exception(f"Error {i}"))

        assert cb.state == CircuitState.OPEN

        # Simulate timeout passing
        cb.last_failure_time -= 2.0  # Move time back

        # Should transition to half-open
        can_exec = await cb.can_execute()
        assert can_exec is True
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_closes_on_success(self, cb):
        """Circuit closes after successful calls in half-open state."""
        cb.state = CircuitState.HALF_OPEN
        cb.half_open_max_calls = 2

        await cb.record_success()
        await cb.record_success()

        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_does_not_close_before_threshold(self, cb):
        """Half-open state remains until success threshold is met."""
        cb.state = CircuitState.HALF_OPEN
        cb.half_open_max_calls = 3
        cb.success_count = 1

        await cb.record_success()

        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_reopens_on_failure(self, cb):
        """Circuit re-opens on failure in half-open state."""
        cb.state = CircuitState.HALF_OPEN

        await cb.record_failure(Exception("Error"))

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_half_open_limits_calls(self, cb):
        """Half-open state limits concurrent calls."""
        cb.state = CircuitState.HALF_OPEN
        cb.half_open_max_calls = 2
        cb.half_open_calls = 2

        # Should reject additional calls
        assert await cb.can_execute() is False

    @pytest.mark.asyncio
    async def test_half_open_allows_calls_within_limit(self, cb):
        """Half-open state allows calls within limit."""
        cb.state = CircuitState.HALF_OPEN
        cb.half_open_max_calls = 3
        cb.half_open_calls = 1  # Below limit

        # Should allow call
        assert await cb.can_execute() is True
        assert cb.half_open_calls == 2  # Incremented

    @pytest.mark.asyncio
    async def test_success_in_closed_state_resets_failures(self, cb):
        """Success in closed state resets failure count."""
        cb.state = CircuitState.CLOSED
        cb.failure_count = 2  # Some failures

        await cb.record_success()

        assert cb.failure_count == 0  # Reset

    @pytest.mark.asyncio
    async def test_success_in_open_state_is_ignored(self, cb):
        """Success in open state is ignored (circuit stays open)."""
        cb.state = CircuitState.OPEN
        cb.failure_count = 5

        await cb.record_success()

        # State and failure count should not change
        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 5

    def test_get_time_remaining_when_open(self, cb):
        """Time remaining is calculated when open."""
        cb.state = CircuitState.OPEN
        cb.last_failure_time = time.monotonic() - 0.5
        cb.recovery_timeout = 1.0

        remaining = cb.get_time_remaining()
        assert 0.4 <= remaining <= 0.6

    def test_get_time_remaining_when_closed(self, cb):
        """Time remaining is 0 when closed."""
        cb.state = CircuitState.CLOSED
        assert cb.get_time_remaining() == 0.0

    def test_get_status(self, cb):
        """Get status returns correct information."""
        cb.failure_count = 2
        status = cb.get_status()

        assert status["name"] == "test"
        assert status["state"] == "closed"
        assert status["failure_count"] == 2
        assert status["failure_threshold"] == 3


class TestCircuitBreakerDecorator:
    """Tests for circuit_breaker decorator."""

    @pytest.mark.asyncio
    async def test_decorator_passes_through_on_success(self):
        """Decorator passes through successful calls."""
        call_count = 0

        @circuit_breaker("test_success", failure_threshold=3)
        async def successful_call():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_call()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_decorator_tracks_failures(self):
        """Decorator tracks failures and opens circuit."""

        @circuit_breaker("test_failures", failure_threshold=2, recovery_timeout=10.0)
        async def failing_call():
            raise ValueError("Test error")

        # First two failures should pass through
        for _ in range(2):
            with pytest.raises(ValueError):
                await failing_call()

        # Third call should be blocked by circuit breaker
        with pytest.raises(CircuitBreakerError) as exc_info:
            await failing_call()

        assert "test_failures" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_decorator_only_catches_specified_exceptions(self):
        """Decorator only catches specified exception types."""

        @circuit_breaker("test_specific", failure_threshold=1, exceptions=(ValueError,))
        async def mixed_call(raise_type: bool):
            if raise_type:
                raise TypeError("Type error")
            raise ValueError("Value error")

        # TypeError should pass through without affecting circuit
        with pytest.raises(TypeError):
            await mixed_call(raise_type=True)

        # Circuit should still be closed
        cb = get_circuit_breaker("test_specific")
        assert cb.state == CircuitState.CLOSED


class TestCircuitBreakerManagement:
    """Tests for circuit breaker management functions."""

    def test_get_circuit_breaker_creates_new(self):
        """get_circuit_breaker creates new circuit breaker."""
        cb = get_circuit_breaker("new_cb", failure_threshold=10)
        assert cb.name == "new_cb"
        assert cb.failure_threshold == 10

    def test_get_circuit_breaker_returns_existing(self):
        """get_circuit_breaker returns existing circuit breaker."""
        cb1 = get_circuit_breaker("existing_cb")
        cb2 = get_circuit_breaker("existing_cb")
        assert cb1 is cb2

    def test_get_all_circuit_breakers(self):
        """get_all_circuit_breakers returns all circuit breakers."""
        get_circuit_breaker("cb_a")
        get_circuit_breaker("cb_b")

        all_cbs = get_all_circuit_breakers()
        assert "cb_a" in all_cbs
        assert "cb_b" in all_cbs

    def test_reset_circuit_breaker_existing(self):
        """reset_circuit_breaker resets existing circuit breaker."""
        cb = get_circuit_breaker("reset_test")
        cb.state = CircuitState.OPEN
        cb.failure_count = 5

        result = reset_circuit_breaker("reset_test")

        assert result is True
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_reset_circuit_breaker_nonexistent(self):
        """reset_circuit_breaker returns False for nonexistent circuit breaker."""
        result = reset_circuit_breaker("nonexistent_cb")
        assert result is False


class TestCircuitBreakerError:
    """Tests for CircuitBreakerError."""

    def test_error_message(self):
        """CircuitBreakerError has correct message."""
        error = CircuitBreakerError("test_cb", 5.5)
        assert error.name == "test_cb"
        assert error.time_remaining == 5.5
        assert "test_cb" in str(error)
        assert "5.5" in str(error)


class TestGeminiCircuitBreaker:
    """Tests for pre-configured Gemini circuit breaker."""

    @pytest.mark.asyncio
    async def test_gemini_circuit_breaker_decorator(self):
        """gemini_circuit_breaker decorator wraps function correctly."""

        @gemini_circuit_breaker
        async def test_function():
            return "success"

        result = await test_function()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_gemini_circuit_breaker_catches_httpx_errors(self):
        """gemini_circuit_breaker catches httpx errors."""
        import httpx

        @gemini_circuit_breaker
        async def failing_function():
            raise httpx.ConnectError("Connection failed")

        # Should raise the error (circuit not yet open)
        with pytest.raises(httpx.ConnectError):
            await failing_function()
