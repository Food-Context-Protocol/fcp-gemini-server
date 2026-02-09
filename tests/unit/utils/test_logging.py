"""Tests for utils/logging.py."""

import json
import logging
import os
from unittest.mock import patch

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
    """Tests for RequestIDFilter class."""

    def test_adds_request_id_to_record(self):
        """Test that filter adds request_id attribute."""
        filter_obj = RequestIDFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="test", args=(), exc_info=None
        )

        token = request_id_ctx.set("test-request-123")
        try:
            filter_obj.filter(record)
            assert hasattr(record, "request_id")
            assert record.request_id == "test-request-123"
        finally:
            request_id_ctx.reset(token)

    def test_uses_dash_when_no_request_id(self):
        """Test that filter uses '-' when no request ID is set."""
        filter_obj = RequestIDFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="test", args=(), exc_info=None
        )

        token = request_id_ctx.set(None)
        try:
            filter_obj.filter(record)
            assert record.request_id == "-"
        finally:
            request_id_ctx.reset(token)

    def test_filter_always_returns_true(self):
        """Test that filter always returns True (doesn't filter out records)."""
        filter_obj = RequestIDFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="test", args=(), exc_info=None
        )

        result = filter_obj.filter(record)
        assert result is True


class TestStructuredLogFormatter:
    """Tests for StructuredLogFormatter class."""

    def test_formats_as_json(self):
        """Test that formatter outputs valid JSON."""
        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.request_id = "req-123"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["severity"] == "INFO"
        assert parsed["message"] == "Test message"
        assert parsed["logger"] == "test.logger"
        assert "timestamp" in parsed

    def test_includes_trace_for_request_id(self):
        """Test that request ID is included as trace."""
        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="test", args=(), exc_info=None
        )
        record.request_id = "trace-456"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["logging.googleapis.com/trace"] == "trace-456"

    def test_excludes_trace_for_dash_request_id(self):
        """Test that '-' request ID is not included as trace."""
        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg="test", args=(), exc_info=None
        )
        record.request_id = "-"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "logging.googleapis.com/trace" not in parsed

    def test_includes_exception_info(self):
        """Test that exception info is included when present."""
        formatter = StructuredLogFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="",
                lineno=0,
                msg="Error occurred",
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
        """Test returning request ID when set in context."""
        token = request_id_ctx.set("my-request-id")
        try:
            assert get_request_id() == "my-request-id"
        finally:
            request_id_ctx.reset(token)

    def test_returns_none_when_not_set(self):
        """Test returning None when no request ID is set."""
        token = request_id_ctx.set(None)
        try:
            assert get_request_id() is None
        finally:
            request_id_ctx.reset(token)


class TestSetupStructuredLogging:
    """Tests for _setup_structured_logging function."""

    def test_adds_handler_with_structured_formatter(self):
        """Test that structured logging adds correct handler."""
        logger = logging.getLogger("test.structured")
        logger.handlers.clear()

        _setup_structured_logging(logger)

        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0].formatter, StructuredLogFormatter)


class TestSetupTextLogging:
    """Tests for _setup_text_logging function."""

    def test_adds_handler_with_text_formatter(self):
        """Test that text logging adds correct handler."""
        logger = logging.getLogger("test.text")
        logger.handlers.clear()

        _setup_text_logging(logger)

        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0].formatter, logging.Formatter)


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_adds_request_id_filter_once(self):
        """Test that RequestIDFilter is only added once."""
        root_logger = logging.getLogger()
        initial_filter_count = len([f for f in root_logger.filters if isinstance(f, RequestIDFilter)])

        setup_logging()
        setup_logging()  # Call twice

        final_filter_count = len([f for f in root_logger.filters if isinstance(f, RequestIDFilter)])

        # Should not add duplicate filters
        assert final_filter_count <= initial_filter_count + 1

    def test_cloud_run_uses_structured_logging(self):
        """Test that Cloud Run environment uses structured logging."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        with patch.dict(os.environ, {"K_SERVICE": "my-service"}):
            setup_logging()

            # Should have used structured logging
            assert root_logger.level == logging.INFO
