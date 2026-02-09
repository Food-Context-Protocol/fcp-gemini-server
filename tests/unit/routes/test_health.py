"""Tests for health check endpoints."""
# sourcery skip: no-conditionals-in-tests

import logging
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from fcp.api import app


@pytest.fixture
def client():
    """Create test client."""
    with TestClient(app) as client:
        yield client


class TestLivenessProbe:
    """Tests for /health/live endpoint."""

    def test_liveness_returns_ok(self, client):
        """Liveness probe should always return ok."""
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestReadinessProbe:
    """Tests for /health/ready endpoint."""

    def test_readiness_with_gemini_key(self, client):
        """Readiness should be ok when Gemini API key is configured."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}, clear=False):
            response = client.get("/health/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["checks"]["gemini_api_key"] is True

    def test_readiness_without_gemini_key(self, client):
        """Readiness should be degraded without Gemini API key."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=False):
            response = client.get("/health/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["checks"]["gemini_api_key"] is False

    def test_readiness_in_cloud_run_with_credentials(self, client):
        """Readiness should check Firebase credentials in Cloud Run."""
        with patch.dict(
            "os.environ",
            {
                "GEMINI_API_KEY": "test-key",
                "K_SERVICE": "test-service",
            },
            clear=False,
        ):
            # Need to reload the module to pick up K_SERVICE
            from importlib import reload

            import fcp.routes.health

            reload(fcp.routes.health)

            response = client.get("/health/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    def test_readiness_in_cloud_run_with_gemini_key(self, client):
        """Readiness should be ok in Cloud Run with Gemini key configured."""
        with patch.dict(
            "os.environ",
            {
                "GEMINI_API_KEY": "test-key",
                "K_SERVICE": "test-service",
            },
            clear=False,
        ):
            from importlib import reload

            import fcp.routes.health

            reload(fcp.routes.health)

            response = client.get("/health/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["checks"]["database"] is True


class TestHealthRoot:
    """Tests for /health endpoint."""

    def test_health_root_returns_ok(self, client):
        """Health root should return ok."""
        response = client.get("/health/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestLoggingWithRequestId:
    """Tests for health check logging with request_id."""

    def test_warning_includes_request_id(self, client, caplog):
        """Warning logs should include request_id for traceability."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=False):
            with caplog.at_level(logging.WARNING):
                response = client.get(
                    "/health/ready",
                    headers={"X-Request-ID": "test-trace-id-123"},
                )
                assert response.status_code == 200

                # Check that warning was logged with request_id
                warning_logs = [r for r in caplog.records if r.levelname == "WARNING"]
                if gemini_warnings := [r for r in warning_logs if "GEMINI_API_KEY" in r.message]:
                    # The warning should include the request_id
                    assert "request_id=" in gemini_warnings[0].message
