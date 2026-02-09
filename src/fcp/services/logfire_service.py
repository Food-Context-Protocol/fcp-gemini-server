"""Logfire observability integration.

Provides enhanced observability using Logfire (from the Pydantic team):
- Native Pydantic AI agent tracing
- OpenTelemetry-compatible spans
- Structured logging with rich context
- Request/response body logging

Usage:
    from fcp.services.logfire_service import init_logfire, shutdown_logfire, log_info, log_span

    # Call once at startup
    init_logfire()

    # Structured logging
    log_info("Processing request", user_id="123", action="search")

    # Manual spans
    with log_span("custom_operation", food="salmon"):
        # do work
        pass

Environment Variables:
    LOGFIRE_TOKEN: Logfire API token for cloud export (optional)
    LOGFIRE_PROJECT_NAME: Project name (default: fcp-gemini-server)
    LOGFIRE_SEND_TO_LOGFIRE: Set to "false" to disable cloud export (default: true if token set)
    FCP_LOGFIRE_CONSOLE: Set to "true" for rich console output (default: true in dev)
    FCP_LOGFIRE_CAPTURE_BODIES: Set to "true" to capture HTTP request/response bodies
        (DISABLED by default to prevent secrets/PII leakage - only enable for debugging)
"""

import logging
import os
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)

_initialized = False


def init_logfire(project_name: str = "fcp-gemini-server") -> bool:
    """Initialize Logfire for observability.

    Logfire automatically:
    - Integrates with existing OpenTelemetry setup
    - Traces Pydantic AI agent calls
    - Provides structured logging

    Args:
        project_name: The project name for Logfire dashboard.

    Returns:
        True if initialization succeeded, False otherwise.
    """
    global _initialized

    if _initialized:
        logger.debug("Logfire already initialized")
        return True

    try:
        import logfire

        # Check if token is set (for cloud export)
        logfire_token = os.environ.get("LOGFIRE_TOKEN")
        send_to_logfire = os.environ.get("LOGFIRE_SEND_TO_LOGFIRE", "true").lower() == "true"

        # Check for console mode (rich terminal output)
        console_mode = os.environ.get("FCP_LOGFIRE_CONSOLE", "true").lower() == "true"

        # Configure Logfire with enhanced options
        logfire.configure(
            service_name=project_name,
            send_to_logfire=send_to_logfire and bool(logfire_token),
            console=logfire.ConsoleOptions(
                colors="auto",
                verbose=console_mode,
                include_timestamps=True,
            )
            if console_mode
            else False,
        )

        # Instrument Pydantic AI if available
        try:
            logfire.instrument_pydantic_ai()
            logger.info("Logfire Pydantic AI instrumentation enabled")
        except Exception as e:
            logger.debug("Pydantic AI instrumentation not available: %s", e)

        # Instrument FastAPI
        try:
            logfire.instrument_fastapi()
            logger.info("Logfire FastAPI instrumentation enabled")
        except Exception as e:
            logger.debug("FastAPI instrumentation not available: %s", e)

        # Instrument HTTPX (used by Gemini client)
        # Body capture DISABLED by default to prevent secrets/PII leakage
        capture_bodies = os.environ.get("FCP_LOGFIRE_CAPTURE_BODIES", "false").lower() == "true"
        try:
            logfire.instrument_httpx(
                capture_request_body=capture_bodies,
                capture_response_body=capture_bodies,
            )
            if capture_bodies:
                logger.warning(
                    "Logfire HTTPX body capture ENABLED - request/response bodies will be logged. "
                    "Ensure no secrets/PII are sent to observability backend in production."
                )
            else:
                logger.info("Logfire HTTPX instrumentation enabled (body capture disabled for security)")
        except Exception as e:
            logger.debug("HTTPX instrumentation not available: %s", e)

        # Instrument asyncio for async operation tracing
        try:
            logfire.instrument_asyncio()
            logger.info("Logfire asyncio instrumentation enabled")
        except Exception as e:
            logger.debug("asyncio instrumentation not available: %s", e)

        # Instrument aiohttp if available
        try:
            logfire.instrument_aiohttp_client()
            logger.info("Logfire aiohttp client instrumentation enabled")
        except Exception as e:
            logger.debug("aiohttp instrumentation not available: %s", e)

        if logfire_token and send_to_logfire:
            logger.info("Logfire initialized with cloud export enabled")
        else:
            logger.info("Logfire initialized (local mode - set LOGFIRE_TOKEN for cloud export)")

        _initialized = True
        return True

    except ImportError as e:
        logger.warning("Logfire not installed. Run: pip install logfire. Error: %s", e)
        return False
    except Exception as e:
        logger.warning("Failed to initialize Logfire: %s", e)
        return False


def shutdown_logfire() -> None:
    """Shutdown Logfire and flush any pending data."""
    global _initialized

    if not _initialized:
        return

    try:
        import logfire

        logfire.shutdown()
        logger.info("Logfire shutdown complete")
    except Exception as e:
        logger.warning("Error during Logfire shutdown: %s", e)
    finally:
        _initialized = False


def is_logfire_initialized() -> bool:
    """Check if Logfire has been initialized."""
    return _initialized


# Convenience functions for structured logging
def log_info(message: str, **attributes: Any) -> None:
    """Log an info message with structured attributes.

    Args:
        message: Log message (can use {key} placeholders for attributes).
        **attributes: Key-value pairs to include in the log.
    """
    if not _initialized:
        logger.info(message, extra=attributes)
        return

    try:
        import logfire

        logfire.info(message, **attributes)
    except Exception:
        logger.info(message, extra=attributes)


def log_warn(message: str, **attributes: Any) -> None:
    """Log a warning message with structured attributes."""
    if not _initialized:
        logger.warning(message, extra=attributes)
        return

    try:
        import logfire

        logfire.warn(message, **attributes)
    except Exception:
        logger.warning(message, extra=attributes)


def log_error(message: str, **attributes: Any) -> None:
    """Log an error message with structured attributes."""
    if not _initialized:
        logger.error(message, extra=attributes)
        return

    try:
        import logfire

        logfire.error(message, **attributes)
    except Exception:
        logger.error(message, extra=attributes)


def log_debug(message: str, **attributes: Any) -> None:
    """Log a debug message with structured attributes."""
    if not _initialized:
        logger.debug(message, extra=attributes)
        return

    try:
        import logfire

        logfire.debug(message, **attributes)
    except Exception:
        logger.debug(message, extra=attributes)


@contextmanager
def log_span(name: str, **attributes: Any):
    """Create a logfire span for timing/grouping operations.

    Usage:
        with log_span("process_food", food_name="salmon"):
            # do work
            pass

    Args:
        name: Span name.
        **attributes: Attributes to attach to the span.
    """
    if not _initialized:
        yield
        return

    try:
        import logfire

        with logfire.span(name, **attributes):
            yield
    except Exception:
        yield
