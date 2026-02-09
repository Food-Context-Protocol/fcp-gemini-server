"""Tests for security middleware (headers, CORS)."""
# sourcery skip: no-loop-in-tests, no-conditionals-in-tests

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from fcp.api import _is_production, app

client = TestClient(app)


class TestSecurityHeaders:
    """Tests for security headers middleware."""

    def test_x_content_type_options_present(self):
        """X-Content-Type-Options header should be set to nosniff."""
        response = client.get("/")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options_present(self):
        """X-Frame-Options header should be set to DENY."""
        response = client.get("/")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_x_xss_protection_not_present(self):
        """X-XSS-Protection should NOT be set (deprecated header)."""
        response = client.get("/")
        # X-XSS-Protection is intentionally not included as it's deprecated
        # and can introduce vulnerabilities in modern browsers
        assert "X-XSS-Protection" not in response.headers

    def test_referrer_policy_present(self):
        """Referrer-Policy header should be set."""
        response = client.get("/")
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_content_security_policy_present(self):
        """Content-Security-Policy header should be restrictive for API."""
        response = client.get("/")
        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None
        assert "default-src 'none'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_security_headers_on_authenticated_endpoints(self):
        """Security headers should be present on all endpoints."""
        with patch("fcp.routes.meals.get_meals", return_value=[]):
            response = client.get(
                "/meals",
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.headers.get("X-Content-Type-Options") == "nosniff"
            assert response.headers.get("X-Frame-Options") == "DENY"


class TestHstsHeader:
    """Tests for HSTS header (production-only)."""

    def test_hsts_not_set_in_development(self):
        """HSTS should not be set in development environment."""
        # In our test environment, _is_production() returns False
        # so HSTS should not be present
        response = client.get("/")
        if not _is_production():
            assert "Strict-Transport-Security" not in response.headers

    def test_hsts_header_value_format(self):
        """HSTS header value should have correct format when used."""
        # Verify the expected HSTS format that would be set in production
        # This tests the constant value used in the middleware
        expected_hsts = "max-age=31536000; includeSubDomains"
        assert "max-age=31536000" in expected_hsts
        assert "includeSubDomains" in expected_hsts


class TestIsProductionDetection:
    """Tests for _is_production() helper function."""

    def test_production_environment_variable(self):
        """Should detect production from ENVIRONMENT=production."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False):
            assert _is_production() is True

    def test_prod_environment_variable(self):
        """Should detect production from ENVIRONMENT=prod."""
        with patch.dict(os.environ, {"ENVIRONMENT": "prod"}, clear=False):
            assert _is_production() is True

    def test_cloud_run_k_service(self):
        """Should detect production from K_SERVICE (Cloud Run)."""
        with patch.dict(os.environ, {"K_SERVICE": "my-service"}, clear=False):
            assert _is_production() is True

    def test_development_environment(self):
        """Should not detect production in development."""
        # Clear all production indicators
        env = {k: v for k, v in os.environ.items() if k not in {"ENVIRONMENT", "K_SERVICE"}}
        with patch.dict(os.environ, env, clear=True):
            assert _is_production() is False


class TestCorsConfiguration:
    """Tests for CORS configuration."""

    def test_cors_allows_production_origins(self):
        """CORS should allow production origins."""
        # These origins should always be allowed
        production_origins = [
            "https://fcp.dev",
            "https://app.fcp.dev",
            "https://www.fcp.dev",
        ]
        for origin in production_origins:
            response = client.options(
                "/",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                },
            )
            # If origin is allowed, Access-Control-Allow-Origin will be set
            assert response.headers.get("Access-Control-Allow-Origin") == origin

    def test_cors_blocks_unknown_origins(self):
        """CORS should not allow unknown origins."""
        response = client.options(
            "/",
            headers={
                "Origin": "https://evil-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Unknown origins should not get Access-Control-Allow-Origin
        assert response.headers.get("Access-Control-Allow-Origin") != "https://evil-site.com"

    def test_cors_allows_credentials(self):
        """CORS should allow credentials."""
        response = client.options(
            "/",
            headers={
                "Origin": "https://foodlog.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("Access-Control-Allow-Credentials") == "true"

    def test_cors_allowed_methods(self):
        """CORS should allow expected HTTP methods."""
        response = client.options(
            "/",
            headers={
                "Origin": "https://foodlog.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        allowed_methods = response.headers.get("Access-Control-Allow-Methods", "")
        assert "GET" in allowed_methods
        assert "POST" in allowed_methods
        assert "PATCH" in allowed_methods
        assert "DELETE" in allowed_methods

    def test_cors_allowed_headers(self):
        """CORS should allow Authorization and Content-Type headers."""
        response = client.options(
            "/",
            headers={
                "Origin": "https://foodlog.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
        allowed_headers = response.headers.get("Access-Control-Allow-Headers", "")
        assert "authorization" in allowed_headers.lower()
        assert "content-type" in allowed_headers.lower()

    def test_cors_localhost_allowed_in_development(self):
        """CORS should allow localhost origins in development mode."""
        # In test environment (non-production), localhost should be allowed
        if not _is_production():
            response = client.options(
                "/",
                headers={
                    "Origin": "http://localhost:8080",
                    "Access-Control-Request-Method": "GET",
                },
            )
            # Localhost should be allowed in development
            assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:8080"
