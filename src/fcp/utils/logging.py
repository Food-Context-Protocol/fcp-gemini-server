"""Logging utilities with request ID and Cloud Logging support.

Provides:
- Request ID tracing for security auditing and debugging
- Automatic Cloud Logging integration on Cloud Run
- Structured JSON logging for production
- Standard text logging for development

Uses ContextVar to propagate request IDs across async boundaries.
"""

import datetime
import json
import logging
import os
import sys
from contextvars import ContextVar
from typing import Any

# Context variable to store request ID across async boundaries
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIDFilter(logging.Filter):
    """Inject request_id into all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request_id attribute to log record."""
        record.request_id = request_id_ctx.get() or "-"
        return True


class StructuredLogFormatter(logging.Formatter):
    """Format logs as JSON for Cloud Logging.

    Outputs JSON with fields that Cloud Logging recognizes:
    - severity: Log level
    - message: Log message
    - logging.googleapis.com/trace: Request ID for correlation
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Use RFC3339/ISO 8601 timestamp for Cloud Logging compatibility
        timestamp = datetime.datetime.fromtimestamp(record.created, tz=datetime.UTC).isoformat(timespec="milliseconds")

        log_entry: dict[str, Any] = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": timestamp,
        }

        # Add request ID for trace correlation
        request_id = getattr(record, "request_id", None)
        if request_id and request_id != "-":
            log_entry["logging.googleapis.com/trace"] = request_id

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def get_request_id() -> str | None:
    """Get the current request ID from context.

    Returns:
        The request ID if set, None otherwise.
    """
    return request_id_ctx.get()


def _setup_structured_logging(logger: logging.Logger) -> None:
    """Configure structured JSON logging."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredLogFormatter())
    logger.addHandler(handler)


def _setup_text_logging(logger: logging.Logger) -> None:
    """Configure text logging for development."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] %(message)s"))
    logger.addHandler(handler)


def setup_logging() -> None:
    """Configure logging based on environment.

    Cloud Run (K_SERVICE set):
    - Uses google-cloud-logging for automatic integration
    - Falls back to structured JSON if library unavailable

    Local development:
    - Adds RequestIDFilter to root logger
    - Does NOT modify formatter to avoid breaking third-party loggers
    """
    root_logger = logging.getLogger()

    # Only add filter if not already added
    if not any(isinstance(f, RequestIDFilter) for f in root_logger.filters):
        root_logger.addFilter(RequestIDFilter())

    # Cloud Run: use enhanced logging
    if os.environ.get("K_SERVICE"):
        root_logger.setLevel(logging.INFO)
        for handler in root_logger.handlers:
            handler.close()
        root_logger.handlers.clear()
        _setup_structured_logging(root_logger)
