"""Circuit breaker implementation for external service calls.

Prevents cascade failures by stopping calls to failing services temporarily.
Uses a simple state machine: CLOSED -> OPEN -> HALF_OPEN -> CLOSED.

Usage:
    from fcp.utils.circuit_breaker import gemini_circuit_breaker

    @gemini_circuit_breaker
    async def call_gemini(prompt: str):
        ...
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Failing, requests are rejected immediately
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, name: str, time_remaining: float):
        self.name = name
        self.time_remaining = time_remaining
        super().__init__(f"Circuit breaker '{name}' is open. Retry in {time_remaining:.1f}s")


@dataclass
class CircuitBreakerState:
    """Tracks circuit breaker state."""

    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 3

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    half_open_calls: int = 0

    # Lock for thread safety
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.half_open_max_calls:
                    self._close()
                    logger.info(
                        "Circuit breaker '%s' closed after %d successful calls",
                        self.name,
                        self.success_count,
                    )
                else:
                    # Explicit no-op for below-threshold success.
                    pass
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0
            else:
                # No-op when circuit is open.
                pass

    async def record_failure(self, error: Exception) -> None:
        """Record a failed call."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.monotonic()

            if self.state == CircuitState.HALF_OPEN:
                self._open()
                logger.warning(
                    "Circuit breaker '%s' re-opened after failure in half-open state: %s",
                    self.name,
                    str(error)[:100],
                )
            elif self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
                self._open()
                logger.warning(
                    "Circuit breaker '%s' opened after %d failures: %s",
                    self.name,
                    self.failure_count,
                    str(error)[:100],
                )

    async def can_execute(self) -> bool:
        """Check if a call can be executed."""
        async with self._lock:
            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._half_open()
                    logger.info(
                        "Circuit breaker '%s' entering half-open state",
                        self.name,
                    )
                    return True
                return False

            # HALF_OPEN: allow limited calls
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False

    def get_time_remaining(self) -> float:
        """Get time remaining before circuit breaker resets."""
        if self.state != CircuitState.OPEN:
            return 0.0
        elapsed = time.monotonic() - self.last_failure_time
        return max(0.0, self.recovery_timeout - elapsed)

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        elapsed = time.monotonic() - self.last_failure_time
        return elapsed >= self.recovery_timeout

    def _open(self) -> None:
        """Open the circuit breaker."""
        self.state = CircuitState.OPEN
        self.half_open_calls = 0
        self.success_count = 0

    def _half_open(self) -> None:
        """Move to half-open state."""
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0
        self.success_count = 0

    def _close(self) -> None:
        """Close the circuit breaker."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0

    def get_status(self) -> dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "time_remaining": self.get_time_remaining(),
        }


# Global circuit breaker instances
_circuit_breakers: dict[str, CircuitBreakerState] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
) -> CircuitBreakerState:
    """Get or create a circuit breaker by name."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreakerState(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
    return _circuit_breakers[name]


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to add circuit breaker protection to an async function.

    Args:
        name: Unique name for this circuit breaker
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        exceptions: Exception types that count as failures

    Example:
        @circuit_breaker("gemini", failure_threshold=5, recovery_timeout=30)
        async def call_gemini(prompt: str):
            ...
    """
    cb = get_circuit_breaker(name, failure_threshold, recovery_timeout)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not await cb.can_execute():
                raise CircuitBreakerError(name, cb.get_time_remaining())

            try:
                result = await func(*args, **kwargs)
                await cb.record_success()
                return result
            except exceptions as e:
                await cb.record_failure(e)
                raise

        return wrapper

    return decorator


# Pre-configured circuit breaker for Gemini API
def gemini_circuit_breaker(func: Callable[..., Any]) -> Callable[..., Any]:
    """Circuit breaker specifically configured for Gemini API calls.

    Configuration:
    - Opens after 5 consecutive failures
    - Waits 30 seconds before attempting recovery
    - Catches common Gemini/HTTP errors
    """
    import httpx

    return circuit_breaker(
        name="gemini",
        failure_threshold=5,
        recovery_timeout=30.0,
        exceptions=(
            httpx.ConnectError,
            httpx.TimeoutException,
            httpx.HTTPStatusError,
            RuntimeError,  # For "GEMINI_API_KEY not configured"
        ),
    )(func)


def get_all_circuit_breakers() -> dict[str, dict[str, Any]]:
    """Get status of all circuit breakers."""
    return {name: cb.get_status() for name, cb in _circuit_breakers.items()}


def reset_circuit_breaker(name: str) -> bool:
    """Manually reset a circuit breaker to closed state."""
    if name in _circuit_breakers:
        cb = _circuit_breakers[name]
        cb._close()
        logger.info("Circuit breaker '%s' manually reset", name)
        return True
    return False


def reset_all_circuit_breakers() -> None:
    """Reset all circuit breakers. Used for testing."""
    global _circuit_breakers
    _circuit_breakers.clear()
