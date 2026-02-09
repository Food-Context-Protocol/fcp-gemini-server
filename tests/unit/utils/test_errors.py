"""Tests for standardized error handling."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from fcp.utils.errors import (
    APIErrorCodes,
    APIErrorDetail,
    APIErrorResponse,
    _format_field_path,
    generic_exception_handler,
    http_exception_handler,
    register_exception_handlers,
    validation_exception_handler,
)


class TestFormatFieldPath:
    """Tests for _format_field_path function."""

    def test_simple_field(self):
        """Should format simple field path."""
        assert _format_field_path(("body", "name")) == "body.name"

    def test_single_field(self):
        """Should format single field without prefix."""
        assert _format_field_path(("query",)) == "query"

    def test_array_index(self):
        """Should use bracket notation for array indices."""
        assert _format_field_path(("body", "items", 0, "name")) == "body.items[0].name"

    def test_multiple_array_indices(self):
        """Should handle multiple array indices."""
        assert _format_field_path(("body", "matrix", 0, 1)) == "body.matrix[0][1]"

    def test_nested_objects(self):
        """Should handle deeply nested objects."""
        assert _format_field_path(("body", "user", "address", "street")) == "body.user.address.street"

    def test_mixed_nesting(self):
        """Should handle mixed object and array nesting."""
        assert _format_field_path(("body", "users", 0, "roles", 1)) == "body.users[0].roles[1]"

    def test_empty_tuple(self):
        """Should handle empty tuple."""
        assert _format_field_path(()) == ""


class TestAPIErrorCodes:
    """Tests for APIErrorCodes class."""

    def test_error_codes_defined(self):
        """All error codes should be defined."""
        assert APIErrorCodes.BAD_REQUEST == "BAD_REQUEST"
        assert APIErrorCodes.UNAUTHORIZED == "UNAUTHORIZED"
        assert APIErrorCodes.FORBIDDEN == "FORBIDDEN"
        assert APIErrorCodes.NOT_FOUND == "NOT_FOUND"
        assert APIErrorCodes.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert APIErrorCodes.RATE_LIMITED == "RATE_LIMITED"
        assert APIErrorCodes.INTERNAL_ERROR == "INTERNAL_ERROR"
        assert APIErrorCodes.SERVICE_UNAVAILABLE == "SERVICE_UNAVAILABLE"
        assert APIErrorCodes.GEMINI_ERROR == "GEMINI_ERROR"
        assert APIErrorCodes.FIREBASE_ERROR == "FIREBASE_ERROR"
        assert APIErrorCodes.IMAGE_ERROR == "IMAGE_ERROR"

    def test_from_status_maps_correctly(self):
        """from_status should map HTTP status codes to error codes."""
        assert APIErrorCodes.from_status(400) == "BAD_REQUEST"
        assert APIErrorCodes.from_status(401) == "UNAUTHORIZED"
        assert APIErrorCodes.from_status(403) == "FORBIDDEN"
        assert APIErrorCodes.from_status(404) == "NOT_FOUND"
        assert APIErrorCodes.from_status(422) == "VALIDATION_ERROR"
        assert APIErrorCodes.from_status(429) == "RATE_LIMITED"
        assert APIErrorCodes.from_status(500) == "INTERNAL_ERROR"
        assert APIErrorCodes.from_status(503) == "SERVICE_UNAVAILABLE"

    def test_from_status_returns_internal_for_unknown(self):
        """from_status should return INTERNAL_ERROR for unknown codes."""
        assert APIErrorCodes.from_status(418) == "INTERNAL_ERROR"
        assert APIErrorCodes.from_status(999) == "INTERNAL_ERROR"


class TestAPIErrorModels:
    """Tests for error Pydantic models."""

    def test_api_error_detail_minimal(self):
        """APIErrorDetail should work with minimal fields."""
        error = APIErrorDetail(code="TEST_ERROR", message="Test message")
        assert error.code == "TEST_ERROR"
        assert error.message == "Test message"
        assert error.details is None
        assert error.request_id is None

    def test_api_error_detail_full(self):
        """APIErrorDetail should work with all fields."""
        error = APIErrorDetail(
            code="TEST_ERROR",
            message="Test message",
            details={"field": "value"},
            request_id="test-123",
        )
        assert error.code == "TEST_ERROR"
        assert error.message == "Test message"
        assert error.details == {"field": "value"}
        assert error.request_id == "test-123"

    def test_api_error_response_serialization(self):
        """APIErrorResponse should serialize correctly."""
        response = APIErrorResponse(
            error=APIErrorDetail(
                code="NOT_FOUND",
                message="Resource not found",
                request_id="abc-123",
            )
        )
        data = response.model_dump()
        assert data["error"]["code"] == "NOT_FOUND"
        assert data["error"]["message"] == "Resource not found"
        assert data["error"]["request_id"] == "abc-123"


class TestExceptionHandlers:
    """Tests for exception handlers."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request with request_id."""
        request = MagicMock()
        request.state.request_id = "test-request-id"
        return request

    @pytest.fixture
    def mock_request_no_id(self):
        """Create a mock request without request_id."""
        request = MagicMock()
        # Simulate no request_id attribute
        del request.state.request_id
        return request

    @pytest.mark.asyncio
    async def test_http_exception_handler(self, mock_request):
        """http_exception_handler should return standardized error."""
        exc = HTTPException(status_code=404, detail="Item not found")
        response = await http_exception_handler(mock_request, exc)

        assert response.status_code == 404
        body_bytes = response.body
        data = body_bytes.decode()
        import json

        body = json.loads(data)
        assert body["error"]["code"] == "NOT_FOUND"
        assert body["error"]["message"] == "Item not found"
        assert body["error"]["request_id"] == "test-request-id"

    @pytest.mark.asyncio
    async def test_http_exception_handler_without_request_id(self, mock_request_no_id):
        """http_exception_handler should work without request_id."""
        exc = HTTPException(status_code=401, detail="Unauthorized")
        response = await http_exception_handler(mock_request_no_id, exc)

        assert response.status_code == 401
        import json

        body_bytes = response.body
        body = json.loads(body_bytes.decode())
        assert body["error"]["code"] == "UNAUTHORIZED"
        assert body["error"]["request_id"] is None

    @pytest.mark.asyncio
    async def test_validation_exception_handler(self, mock_request):
        """validation_exception_handler should return validation errors."""

        # Create a validation error
        class TestModel(BaseModel):
            name: str
            age: int

        try:
            TestModel(name=123, age="not-an-int")
        except ValidationError as ve:
            # Create RequestValidationError from Pydantic error
            exc = RequestValidationError(ve.errors())

        response = await validation_exception_handler(mock_request, exc)

        assert response.status_code == 422
        import json

        body_bytes = response.body
        body = json.loads(body_bytes.decode())
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert body["error"]["message"] == "Request validation failed"
        assert "validation_errors" in body["error"]["details"]
        assert body["error"]["request_id"] == "test-request-id"

    @pytest.mark.asyncio
    async def test_generic_exception_handler(self, mock_request):
        """generic_exception_handler should not expose internal details."""
        exc = Exception("Internal database error with sensitive info")
        response = await generic_exception_handler(mock_request, exc)

        assert response.status_code == 500
        import json

        body_bytes = response.body
        body = json.loads(body_bytes.decode())
        assert body["error"]["code"] == "INTERNAL_ERROR"
        assert body["error"]["message"] == "An unexpected error occurred"
        # Should NOT contain the original error message
        assert "database" not in body["error"]["message"]
        assert body["error"]["request_id"] == "test-request-id"


class TestRegisterExceptionHandlers:
    """Tests for register_exception_handlers function."""

    def test_register_adds_handlers(self):
        """register_exception_handlers should add HTTPException and validation handlers."""
        app = FastAPI()

        # Initially no custom handlers
        initial_handlers = len(app.exception_handlers)

        register_exception_handlers(app)

        # Should have added handlers
        assert len(app.exception_handlers) > initial_handlers
        assert HTTPException in app.exception_handlers
        assert RequestValidationError in app.exception_handlers
        # Note: generic Exception handler is NOT registered globally


class TestIntegration:
    """Integration tests with real FastAPI app."""

    @pytest.fixture
    def client(self):
        """Create test client with api app."""
        from fcp.api import app

        return TestClient(app, raise_server_exceptions=False)

    def test_all_responses_have_request_id_header(self, client):
        """All responses should include X-Request-ID header."""
        response = client.get("/")
        assert "X-Request-ID" in response.headers
        # UUID format validation
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 36
        assert request_id.count("-") == 4

    def test_http_exception_uses_standardized_format(self, client):
        """HTTPException raised by routes should use standardized format."""
        # Use a write endpoint that requires auth - demo users get 403
        # POST /meals requires authentication (write access)
        response = client.post("/meals", json={"dish_name": "Test"})
        # Demo users get 403 for write operations
        assert response.status_code == 403
        data = response.json()
        # Should have standardized error format
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert data["error"]["code"] == "FORBIDDEN"
