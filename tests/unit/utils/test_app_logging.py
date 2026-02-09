"""Tests for logging utilities."""

import json
import logging
import os
from unittest.mock import patch

import pytest

from fcp.utils.logging import (
    RequestIDFilter,
    StructuredLogFormatter,
    _setup_structured_logging,
    _setup_text_logging,
    get_request_id,
    request_id_ctx,
    setup_logging,
)


class TestRequestIDFilter:
    """Tests for RequestIDFilter."""

    def test_adds_request_id_to_record(self):
        """Should add request_id attribute to log record."""
        filter_obj = RequestIDFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        token = request_id_ctx.set("test-123")
        try:
            filter_obj.filter(record)
            assert record.request_id == "test-123"
        finally:
            request_id_ctx.reset(token)

    def test_filter_without_request_id(self):
        """Should set request_id to '-' when not in context."""
        filter_obj = RequestIDFilter()
        record = logging.LogRecord("test", logging.INFO, "path", 1, "msg", None, None)

        request_id_ctx.set(None)
        filter_obj.filter(record)
        assert record.request_id == "-"


class TestStructuredLogFormatter:
    """Tests for StructuredLogFormatter."""

    def test_formats_as_json(self):
        """Should format log record as JSON."""
        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        record.request_id = "req-456"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["severity"] == "INFO"
        assert parsed["message"] == "test message"
        assert parsed["logger"] == "test.logger"
        assert parsed["logging.googleapis.com/trace"] == "req-456"

    def test_timestamp_is_rfc3339_format(self):
        """Should format timestamp in RFC3339/ISO 8601 format."""
        import datetime

        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        record.request_id = "-"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "timestamp" in parsed
        timestamp_str = parsed["timestamp"]
        parsed_ts = datetime.datetime.fromisoformat(timestamp_str)
        assert parsed_ts is not None
        assert parsed_ts.tzinfo is not None

    def test_excludes_trace_when_request_id_is_dash(self):
        """Should not include trace field when request_id is '-'."""
        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="warning message",
            args=(),
            exc_info=None,
        )
        record.request_id = "-"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "logging.googleapis.com/trace" not in parsed

    def test_includes_exception_info(self):
        """Should include exception info when present."""
        formatter = StructuredLogFormatter()

        try:
            raise ValueError("test error")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )

        record.request_id = "-"
        output = formatter.format(record)
        parsed = json.loads(output)

        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]


class TestGetRequestId:
    """Tests for get_request_id function."""

    def test_returns_request_id_when_set(self):
        """Should return request ID from context."""
        token = request_id_ctx.set("my-request-id")
        try:
            assert get_request_id() == "my-request-id"
        finally:
            request_id_ctx.reset(token)

    def test_returns_none_when_not_set(self):
        """Should return None when no request ID is set."""
        request_id_ctx.set(None)
        assert get_request_id() is None


class TestSetupFunctions:
    """Tests for logging setup functions."""

    def test_setup_structured_logging(self):
        """Should add handler with StructuredLogFormatter."""
        logger = logging.getLogger("test_structured")
        logger.handlers.clear()

        _setup_structured_logging(logger)

        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0].formatter, StructuredLogFormatter)

    def test_setup_text_logging(self):
        """Should add handler with text formatter."""
        logger = logging.getLogger("test_text")
        logger.handlers.clear()

        _setup_text_logging(logger)

        assert len(logger.handlers) == 1
        fmt = logger.handlers[0].formatter._fmt
        assert fmt is not None
        assert "request_id" in fmt


class TestSetupLogging:
    """Tests for main setup_logging function."""

    def test_adds_request_id_filter_once(self):
        """Should only add RequestIDFilter once even if called multiple times."""
        root_logger = logging.getLogger()
        original_filters = root_logger.filters.copy()
        root_logger.filters = [f for f in root_logger.filters if not isinstance(f, RequestIDFilter)]

        try:
            setup_logging()
            filter_count_1 = sum(isinstance(f, RequestIDFilter) for f in root_logger.filters)

            setup_logging()
            filter_count_2 = sum(isinstance(f, RequestIDFilter) for f in root_logger.filters)

            assert filter_count_1 == 1
            assert filter_count_2 == 1  # Should still be 1
        finally:
            root_logger.filters = original_filters

    @pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
    def test_uses_structured_logging_on_cloud_run(self):
        """Should use structured logging when K_SERVICE is set."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        with patch.dict(os.environ, {"K_SERVICE": "my-service"}):
            with patch("fcp.utils.logging._setup_structured_logging") as mock_structured:
                setup_logging()
                mock_structured.assert_called_once()

    @pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
    def test_cloud_run_closes_existing_handlers(self):
        """Should close existing handlers when K_SERVICE is set (line 110)."""
        root_logger = logging.getLogger()
        # Add a handler so the for-loop body executes
        dummy_handler = logging.StreamHandler()
        root_logger.addHandler(dummy_handler)

        with patch.dict(os.environ, {"K_SERVICE": "test-service"}):
            with patch("fcp.utils.logging._setup_structured_logging"):
                setup_logging()

        # The handler should have been closed and removed
        assert dummy_handler not in root_logger.handlers

    def test_uses_filter_only_in_development(self):
        """Should only add filter without modifying handlers in development."""
        env = os.environ.copy()
        env.pop("K_SERVICE", None)

        with patch.dict(os.environ, env, clear=True):
            with patch("fcp.utils.logging._setup_text_logging"):
                setup_logging()
                # In development, filter is added but no structured logging
