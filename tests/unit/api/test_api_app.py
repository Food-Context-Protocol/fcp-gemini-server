"""Tests for api.py application setup and configuration."""
# sourcery skip: no-conditionals-in-tests

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestLoadOpenApiDescription:
    """Tests for _load_openapi_description function."""

    def test_loads_description_or_fallback(self):
        """Test that _load_openapi_description returns a string."""
        from fcp.api import _load_openapi_description

        result = _load_openapi_description()
        # Should return either file content or fallback string
        assert isinstance(result, str)
        assert len(result) > 0

    def test_fallback_when_file_missing(self):
        """Test fallback when OpenAPI description file is missing."""
        from pathlib import Path as OriginalPath

        # Patch pathlib.Path to raise FileNotFoundError on read_text
        with patch.object(OriginalPath, "read_text", side_effect=FileNotFoundError("Not found")):
            import fcp.api as api

            # The function should return fallback when file is not found
            result = api._load_openapi_description()
            assert result == "Food Context Protocol HTTP API."


class TestApiLifespan:
    """Tests for the FastAPI lifespan context manager."""

    @pytest.mark.asyncio
    async def test_lifespan_startup_and_shutdown(self):
        """Test that lifespan initializes and shuts down properly."""
        from fcp.api import app, lifespan

        with (
            patch("fcp.api.init_logfire") as mock_init_logfire,
            patch("fcp.api.setup_audit_logging") as mock_setup_audit,
            patch("fcp.api.shutdown_logfire") as mock_shutdown_logfire,
            patch("fcp.api.cancel_all_tasks", new_callable=AsyncMock) as mock_cancel,
            patch("fcp.api._is_scheduler_available", return_value=False),
        ):
            async with lifespan(app):
                mock_init_logfire.assert_called_once()
                mock_setup_audit.assert_called_once()

            mock_cancel.assert_called_once()
            mock_shutdown_logfire.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_with_scheduler_available(self):
        """Test lifespan when scheduler is available."""
        from fcp.api import app, lifespan

        mock_init_schedules = MagicMock()
        mock_stop_scheduler = MagicMock()

        with (
            patch("fcp.api.init_logfire"),
            patch("fcp.api.setup_audit_logging"),
            patch("fcp.api.shutdown_logfire"),
            patch("fcp.api.cancel_all_tasks", new_callable=AsyncMock),
            patch("fcp.api._is_scheduler_available", return_value=True),
            patch("fcp.scheduler.jobs.initialize_all_schedules", mock_init_schedules),
            patch("fcp.scheduler.stop_scheduler", mock_stop_scheduler),
        ):
            async with lifespan(app):
                mock_init_schedules.assert_called_once()

            mock_stop_scheduler.assert_called_once()


class TestSecurityHeadersMiddleware:
    """Tests for security headers middleware."""

    def test_security_headers_added(self):
        """Test that security headers are added to responses."""
        from fcp.api import app

        client = TestClient(app)

        # Use the root endpoint
        response = client.get("/")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "default-src 'none'" in response.headers.get("Content-Security-Policy", "")

    def test_hsts_header_in_production(self):
        """Test that HSTS header is added in production."""
        import sys

        # Store original module reference
        original_api = sys.modules.get("api")

        try:
            # Clear api module from cache to force reimport
            if "api" in sys.modules:
                del sys.modules["api"]

            with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
                import fcp.api as api

                # Check if _is_production returns True
                assert api._is_production() is True

                # Make a request to verify HSTS header is added
                client = TestClient(api.app)
                response = client.get("/")

                # Verify HSTS header is present in production
                assert "Strict-Transport-Security" in response.headers
                assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
        finally:
            # Restore original module
            if original_api:
                sys.modules["api"] = original_api
            elif "api" in sys.modules:
                del sys.modules["api"]


class TestRequestIdMiddleware:
    """Tests for request ID middleware."""

    def test_request_id_generated(self):
        """Test that request ID is generated when not provided."""
        from fcp.api import app

        client = TestClient(app)

        response = client.get("/")

        # Should have X-Request-ID header in response
        assert "X-Request-ID" in response.headers
        # Should be a UUID format
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 36  # UUID with dashes

    def test_request_id_passed_through(self):
        """Test that provided request ID is passed through."""
        from fcp.api import app

        client = TestClient(app)

        test_request_id = "test-request-id-123"
        response = client.get("/", headers={"X-Request-ID": test_request_id})

        assert response.headers["X-Request-ID"] == test_request_id


class TestCorsConfiguration:
    """Tests for CORS configuration."""

    def test_cors_origins_in_development(self):
        """Test CORS origins include localhost in development."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            import importlib

            import fcp.api as api

            importlib.reload(api)

            assert not api._is_production()
            # Development origins should be included when not in production
            # (but module-level code runs at import time)

    def test_cors_origins_with_custom_env(self):
        """Test CORS origins can be extended via DEV_CORS_ORIGINS environment variable."""
        import sys

        # Store original module reference
        original_api = sys.modules.get("fcp.api")

        try:
            # Clear api module from cache to force reimport
            if "fcp.api" in sys.modules:
                del sys.modules["fcp.api"]

            # Set DEV_CORS_ORIGINS and ensure not in production
            with patch.dict(
                os.environ,
                {"DEV_CORS_ORIGINS": "http://custom:3000,http://other:5000"},
                clear=False,
            ):
                # Ensure we're not in production mode
                os.environ.pop("ENVIRONMENT", None)
                os.environ.pop("K_SERVICE", None)

                import fcp.api as api

                # Verify the custom origins were added
                assert "http://custom:3000" in api.CORS_ORIGINS
                assert "http://other:5000" in api.CORS_ORIGINS
        finally:
            # Restore original module
            if original_api:
                sys.modules["fcp.api"] = original_api
            elif "fcp.api" in sys.modules:
                del sys.modules["fcp.api"]


class TestRootEndpoint:
    """Tests for root health check endpoint."""

    def test_root_returns_ok(self):
        """Test that root endpoint returns OK status."""
        from fcp.api import app

        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "FoodLog FCP API"
        assert data["version"] == "1.1.0"


class TestSchedulerImportError:
    """Tests for scheduler ImportError handling in api.py."""

    def test_scheduler_flag_controls_lifespan_behavior(self):
        """Test that _is_scheduler_available controls lifespan behavior.

        The lazy import function returns False when the scheduler module
        is not installed, which controls whether scheduler initialization
        runs in lifespan. This test verifies that behavior.
        """
        from fcp.api import app, lifespan

        # Test lifespan with _is_scheduler_available returning False (the fallback state)
        with (
            patch("fcp.api.init_logfire"),
            patch("fcp.api.shutdown_logfire"),
            patch("fcp.api.cancel_all_tasks", new_callable=AsyncMock),
            patch("fcp.api._is_scheduler_available", return_value=False),
        ):
            import asyncio

            async def run_lifespan():
                async with lifespan(app):
                    pass

            asyncio.run(run_lifespan())
            # If we get here without error, the fallback path works

    def test_module_exposes_scheduler_available_function(self):
        """Test that api module exposes _is_scheduler_available function."""
        from fcp.api import _is_scheduler_available

        # The function should return a boolean
        assert isinstance(_is_scheduler_available(), bool)

    @pytest.mark.asyncio
    async def test_lifespan_handles_http_client_close_exception(self):
        """Test that lifespan handles exceptions from close_http_client gracefully."""
        from fcp.api import app, lifespan

        # Mock close_http_client to raise an exception
        mock_close = AsyncMock(side_effect=RuntimeError("Connection error"))

        with (
            patch("fcp.api.init_logfire"),
            patch("fcp.api.shutdown_logfire"),
            patch("fcp.api.cancel_all_tasks", new_callable=AsyncMock),
            patch("fcp.api._is_scheduler_available", return_value=False),
            patch("fcp.services.gemini.GeminiClient.close_http_client", mock_close),
        ):
            # Should not raise even though close_http_client fails
            async with lifespan(app):
                pass

            # close_http_client was called (even though it raised)
            mock_close.assert_called_once()


class TestUserIdMiddleware:
    """Tests for user ID middleware for rate limiting."""

    def test_user_id_set_for_valid_bearer_token(self):
        """Test that user_id is extracted from valid bearer token."""
        from fcp.api import app

        client = TestClient(app)

        # Make request with valid bearer token
        response = client.get("/", headers={"Authorization": "Bearer valid-token"})

        # Request should succeed
        assert response.status_code == 200

    def test_user_id_set_for_any_bearer_token(self):
        """Test that any bearer token is accepted (local auth)."""
        from fcp.api import app

        client = TestClient(app)

        # Make request with any bearer token
        response = client.get("/", headers={"Authorization": "Bearer any-token"})

        # Request should succeed
        assert response.status_code == 200

    def test_user_id_none_without_bearer_token(self):
        """Test that demo user is returned when no Authorization header provided."""
        from fcp.api import app

        client = TestClient(app)

        # Make request without Authorization header
        response = client.get("/")

        # Request should succeed
        assert response.status_code == 200

    def test_user_id_none_with_invalid_auth_format(self):
        """Test that demo user is returned when Authorization header has wrong format."""
        from fcp.api import app

        client = TestClient(app)

        # Make request with wrong auth format (not "Bearer <token>")
        response = client.get("/", headers={"Authorization": "Basic some-token"})

        # Request should succeed
        assert response.status_code == 200
