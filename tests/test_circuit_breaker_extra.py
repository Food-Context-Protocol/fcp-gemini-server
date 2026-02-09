"""Extra coverage for circuit breaker branches used in CI."""

from __future__ import annotations

import pytest

from fcp.utils.circuit_breaker import CircuitBreakerState, CircuitState


@pytest.mark.asyncio
async def test_half_open_success_below_threshold():
    cb = CircuitBreakerState(name="extra", failure_threshold=2, recovery_timeout=1.0, half_open_max_calls=2)
    cb.state = CircuitState.HALF_OPEN
    cb.success_count = 0

    await cb.record_success()

    assert cb.state == CircuitState.HALF_OPEN
    assert cb.success_count == 1


@pytest.mark.asyncio
async def test_half_open_success_closes_at_threshold():
    cb = CircuitBreakerState(name="extra-close", failure_threshold=2, recovery_timeout=1.0, half_open_max_calls=1)
    cb.state = CircuitState.HALF_OPEN
    cb.success_count = 0

    await cb.record_success()

    assert cb.state == CircuitState.CLOSED
    assert cb.success_count == 0


@pytest.mark.asyncio
async def test_closed_success_resets_failure_count():
    cb = CircuitBreakerState(name="extra-closed", failure_threshold=2, recovery_timeout=1.0, half_open_max_calls=2)
    cb.state = CircuitState.CLOSED
    cb.failure_count = 1

    await cb.record_success()

    assert cb.failure_count == 0


@pytest.mark.asyncio
async def test_open_success_is_noop():
    cb = CircuitBreakerState(name="extra-open", failure_threshold=2, recovery_timeout=1.0, half_open_max_calls=2)
    cb.state = CircuitState.OPEN
    cb.success_count = 0
    cb.failure_count = 3

    await cb.record_success()

    assert cb.state == CircuitState.OPEN
    assert cb.success_count == 0
    assert cb.failure_count == 3
