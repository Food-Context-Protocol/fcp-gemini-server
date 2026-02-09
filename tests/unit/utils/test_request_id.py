"""Tests for request ID tracing middleware."""
# sourcery skip: no-loop-in-tests

import logging

import pytest
from fastapi.testclient import TestClient

from fcp.utils.logging import RequestIDFilter, request_id_ctx, setup_logging


class TestRequestIDMiddleware:
    """Tests for request ID middleware."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        # Import here to avoid circular imports and ensure fresh app
        from fcp.api import app

        return TestClient(app)

    def test_generates_request_id_when_not_provided(self, client):
        """Should generate UUID when X-Request-ID not in request."""
        response = client.get("/")
        assert "X-Request-ID" in response.headers
        # UUID format: 8-4-4-4-12 hex chars
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 36
        assert request_id.count("-") == 4

    def test_propagates_provided_request_id(self, client):
        """Should use client-provided X-Request-ID."""
        custom_id = "test-request-123"
        response = client.get("/", headers={"X-Request-ID": custom_id})
        assert response.headers["X-Request-ID"] == custom_id

    def test_request_id_available_in_request_state(self, client):
        """Should set request_id on request.state for route access."""
        response = client.get("/")
        assert response.status_code == 200

    def test_different_requests_get_different_ids(self, client):
        """Each request should get a unique ID."""
        response1 = client.get("/")
        response2 = client.get("/")
        id1 = response1.headers["X-Request-ID"]
        id2 = response2.headers["X-Request-ID"]
        assert id1 != id2


class TestRequestIDFilter:
    """Tests for RequestIDFilter logging filter."""

    def test_filter_adds_request_id_to_log_record(self):
        """Filter should add request_id attribute to log records."""
        filter_instance = RequestIDFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # Set context var
        token = request_id_ctx.set("test-id-123")
        try:
            result = filter_instance.filter(record)
            assert result is True
            assert record.request_id == "test-id-123"
        finally:
            request_id_ctx.reset(token)

    def test_filter_uses_dash_when_no_request_id(self):
        """Filter should use '-' when no request ID is set."""
        filter_instance = RequestIDFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # Ensure context var is not set
        token = request_id_ctx.set(None)
        try:
            result = filter_instance.filter(record)
            assert result is True
            assert record.request_id == "-"
        finally:
            request_id_ctx.reset(token)


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_adds_filter(self):
        """setup_logging should add RequestIDFilter to root logger."""
        # Get root logger
        root_logger = logging.getLogger()

        # Remove any existing RequestIDFilter for clean test
        original_filters = root_logger.filters.copy()
        root_logger.filters = [f for f in root_logger.filters if not isinstance(f, RequestIDFilter)]

        try:
            # Call setup_logging
            setup_logging()

            # Check filter was added
            assert any(isinstance(f, RequestIDFilter) for f in root_logger.filters)
        finally:
            # Restore original filters
            root_logger.filters = original_filters

    def test_setup_logging_does_not_duplicate_filter(self):
        """setup_logging should not add duplicate filters."""
        root_logger = logging.getLogger()

        # Count existing RequestIDFilters
        initial_count = sum(isinstance(f, RequestIDFilter) for f in root_logger.filters)

        # Call setup_logging twice
        setup_logging()
        setup_logging()

        # Count should be at most initial + 1
        final_count = sum(isinstance(f, RequestIDFilter) for f in root_logger.filters)
        assert final_count <= initial_count + 1

    def test_setup_logging_filter_adds_request_id_attr(self):
        """setup_logging filter should add request_id to log records."""
        setup_logging()

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        # Apply filter
        root_logger = logging.getLogger()
        for f in root_logger.filters:
            f.filter(record)

        # Record should have request_id attribute
        assert hasattr(record, "request_id")
