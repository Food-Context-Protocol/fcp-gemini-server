"""Tests for enhanced health check endpoints."""
# sourcery skip: no-conditionals-in-tests

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from fcp.api import app


@pytest.fixture
def client():
    """Create test client."""
    with TestClient(app) as client:
        yield client


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_liveness_probe(self, client):
        """Liveness probe returns ok."""
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_root_health(self, client):
        """Root health endpoint returns ok."""
        response = client.get("/health/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_readiness_probe_success(self, client):
        """Readiness probe returns ok when configured."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            response = client.get("/health/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["checks"]["gemini_api_key"] is True

    def test_readiness_probe_degraded(self, client):
        """Readiness probe returns degraded when misconfigured."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=False):
            # Need to clear the key
            import os

            original = os.environ.get("GEMINI_API_KEY")
            os.environ.pop("GEMINI_API_KEY", None)
            try:
                response = client.get("/health/ready")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "degraded"
                assert data["checks"]["gemini_api_key"] is False
            finally:
                if original:
                    os.environ["GEMINI_API_KEY"] = original


class TestDependencyHealth:
    """Tests for /health/deps endpoint."""

    def test_deps_healthy(self, client):
        """Dependency health returns healthy when all services ok."""
        mock_gemini_client = MagicMock()
        mock_gemini_client.client = MagicMock()  # Not None

        mock_firestore_client = MagicMock()
        mock_firestore_client.db = MagicMock()  # Not None

        with patch(
            "fcp.services.gemini.get_gemini_client",
            return_value=mock_gemini_client,
        ):
            with patch(
                "fcp.services.firestore.get_firestore_client",
                return_value=mock_firestore_client,
            ):
                response = client.get("/health/deps")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"]["gemini"]["healthy"] is True
        assert data["checks"]["firestore"]["healthy"] is True

    def test_deps_unhealthy_gemini(self, client):
        """Dependency health returns unhealthy when Gemini fails."""
        mock_gemini_client = MagicMock()
        mock_gemini_client.client = None  # Not configured

        mock_firestore_client = MagicMock()
        mock_firestore_client.db = MagicMock()

        with patch(
            "fcp.services.gemini.get_gemini_client",
            return_value=mock_gemini_client,
        ):
            with patch(
                "fcp.services.firestore.get_firestore_client",
                return_value=mock_firestore_client,
            ):
                response = client.get("/health/deps")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["gemini"]["healthy"] is False

    def test_deps_unhealthy_firestore(self, client):
        """Dependency health returns unhealthy when Firestore fails."""
        mock_gemini_client = MagicMock()
        mock_gemini_client.client = MagicMock()

        mock_firestore_client = MagicMock()
        mock_firestore_client.db = None  # Not initialized

        with patch(
            "fcp.services.gemini.get_gemini_client",
            return_value=mock_gemini_client,
        ):
            with patch(
                "fcp.services.firestore.get_firestore_client",
                return_value=mock_firestore_client,
            ):
                response = client.get("/health/deps")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["firestore"]["healthy"] is False

    def test_deps_handles_gemini_exception(self, client):
        """Dependency health handles Gemini exceptions gracefully."""
        mock_firestore_client = MagicMock()
        mock_firestore_client.db = MagicMock()

        with patch(
            "fcp.services.gemini.get_gemini_client",
            side_effect=Exception("Connection failed"),
        ):
            with patch(
                "fcp.services.firestore.get_firestore_client",
                return_value=mock_firestore_client,
            ):
                response = client.get("/health/deps")

        assert response.status_code == 200
        data = response.json()
        assert data["checks"]["gemini"]["healthy"] is False
        assert "Connection failed" in data["checks"]["gemini"]["error"]

    def test_deps_handles_firestore_exception(self, client):
        """Dependency health handles Firestore exceptions gracefully."""
        mock_gemini_client = MagicMock()
        mock_gemini_client.client = MagicMock()

        with patch(
            "fcp.services.gemini.get_gemini_client",
            return_value=mock_gemini_client,
        ):
            with patch(
                "fcp.services.firestore.get_firestore_client",
                side_effect=Exception("DB connection failed"),
            ):
                response = client.get("/health/deps")

        assert response.status_code == 200
        data = response.json()
        assert data["checks"]["firestore"]["healthy"] is False

    def test_deps_includes_circuit_breakers(self, client):
        """Dependency health includes circuit breaker status."""
        mock_gemini_client = MagicMock()
        mock_gemini_client.client = MagicMock()

        mock_firestore_client = MagicMock()
        mock_firestore_client.db = MagicMock()

        with patch(
            "fcp.services.gemini.get_gemini_client",
            return_value=mock_gemini_client,
        ):
            with patch(
                "fcp.services.firestore.get_firestore_client",
                return_value=mock_firestore_client,
            ):
                response = client.get("/health/deps")

        assert response.status_code == 200
        data = response.json()
        assert "circuit_breakers" in data["checks"]

    def test_deps_degraded_with_open_circuit_breaker(self, client):
        """Dependency health returns degraded when circuit breaker is open."""
        mock_gemini_client = MagicMock()
        mock_gemini_client.client = MagicMock()

        mock_firestore_client = MagicMock()
        mock_firestore_client.db = MagicMock()

        mock_circuit_breakers = {
            "gemini": {
                "name": "gemini",
                "state": "open",
                "failure_count": 5,
            }
        }

        with patch(
            "fcp.services.gemini.get_gemini_client",
            return_value=mock_gemini_client,
        ):
            with patch(
                "fcp.services.firestore.get_firestore_client",
                return_value=mock_firestore_client,
            ):
                # Patch where imported in health.py
                with patch(
                    "fcp.routes.health.get_all_circuit_breakers",
                    return_value=mock_circuit_breakers,
                ):
                    response = client.get("/health/deps")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"  # Core healthy but circuit open

    def test_deps_unhealthy_firestore_offline_status(self, client):
        """Dependency health reports offline mode when Firestore credentials missing."""
        mock_gemini_client = MagicMock()
        mock_gemini_client.client = MagicMock()

        with patch(
            "fcp.services.gemini.get_gemini_client",
            return_value=mock_gemini_client,
        ):
            with patch(
                "fcp.services.firestore.get_firestore_status",
                return_value={"available": False, "error": "no creds"},
            ):
                response = client.get("/health/deps")

        assert response.status_code == 200
        data = response.json()
        assert data["checks"]["firestore"]["mode"] == "offline"
        assert data["checks"]["firestore"]["healthy"] is False
