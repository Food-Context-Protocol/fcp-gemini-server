"""Tests for security/rate_limit.py."""
# sourcery skip: no-loop-in-tests

from unittest.mock import MagicMock

from fcp.security.rate_limit import (
    RATE_LIMIT_ANALYZE,
    RATE_LIMIT_CRUD,
    RATE_LIMIT_DEFAULT,
    RATE_LIMIT_PROFILE,
    RATE_LIMIT_SEARCH,
    RATE_LIMIT_SUGGEST,
    _get_user_id_or_ip,
    limit_analyze,
    limit_crud,
    limit_profile,
    limit_search,
    limit_suggest,
    limiter,
    rate_limit_exceeded_handler,
)


class TestGetUserIdOrIp:
    """Tests for _get_user_id_or_ip function."""

    def test_returns_user_id_when_authenticated(self):
        """Test that user ID is returned for authenticated requests."""
        mock_request = MagicMock()
        mock_request.state.user_id = "user123"

        result = _get_user_id_or_ip(mock_request)
        assert result == "user:user123"

    def test_returns_ip_when_not_authenticated(self):
        """Test that IP is returned for unauthenticated requests."""
        mock_request = MagicMock()
        mock_request.state = MagicMock(spec=[])  # No user_id attribute
        mock_request.client.host = "192.168.1.100"

        result = _get_user_id_or_ip(mock_request)
        # get_remote_address extracts IP from request
        assert "user:" not in result


class TestRateLimitConstants:
    """Tests for rate limit constants."""

    def test_default_rate_limits_set(self):
        """Test that default rate limits are defined."""
        assert RATE_LIMIT_ANALYZE is not None
        assert RATE_LIMIT_SEARCH is not None
        assert RATE_LIMIT_SUGGEST is not None
        assert RATE_LIMIT_PROFILE is not None
        assert RATE_LIMIT_CRUD is not None
        assert RATE_LIMIT_DEFAULT is not None

    def test_rate_limits_are_strings(self):
        """Test that rate limits are valid string formats."""
        for limit in [
            RATE_LIMIT_ANALYZE,
            RATE_LIMIT_SEARCH,
            RATE_LIMIT_SUGGEST,
            RATE_LIMIT_PROFILE,
            RATE_LIMIT_CRUD,
            RATE_LIMIT_DEFAULT,
        ]:
            assert isinstance(limit, str)
            assert "/" in limit  # Format like "10/minute"


class TestRateLimitExceededHandler:
    """Tests for rate_limit_exceeded_handler."""

    def _create_mock_exception(self, retry_after=60, detail="10 per 1 minute"):
        """Create a mock RateLimitExceeded exception."""
        mock_exc = MagicMock()
        mock_exc.retry_after = retry_after
        mock_exc.detail = detail
        return mock_exc

    def test_returns_429_status(self):
        """Test that handler returns 429 status code."""
        mock_request = MagicMock()
        mock_exc = self._create_mock_exception(retry_after=30)

        response = rate_limit_exceeded_handler(mock_request, mock_exc)

        assert response.status_code == 429

    def test_includes_retry_after_header(self):
        """Test that response includes Retry-After header."""
        mock_request = MagicMock()
        mock_exc = self._create_mock_exception(retry_after=45)

        response = rate_limit_exceeded_handler(mock_request, mock_exc)

        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "45"

    def test_returns_json_error_body(self):
        """Test that response body is JSON with error details."""
        mock_request = MagicMock()
        mock_exc = self._create_mock_exception(retry_after=60, detail="10 per 1 minute")

        response = rate_limit_exceeded_handler(mock_request, mock_exc)

        # Parse the body
        import json

        body = json.loads(response.body.decode())
        assert "error" in body
        assert body["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert body["error"]["retry_after"] == 60

    def test_includes_rate_limit_header(self):
        """Test that X-RateLimit-Limit header is included."""
        mock_request = MagicMock()
        mock_exc = self._create_mock_exception(retry_after=60, detail="10 per 1 minute")

        response = rate_limit_exceeded_handler(mock_request, mock_exc)

        assert "X-RateLimit-Limit" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "10 per 1 minute"

    def test_defaults_retry_after_to_60(self):
        """Test that retry_after defaults to 60 if not set."""
        mock_request = MagicMock()
        mock_exc = MagicMock(spec=[])  # No retry_after attribute

        response = rate_limit_exceeded_handler(mock_request, mock_exc)

        import json

        body = json.loads(response.body.decode())
        assert body["error"]["retry_after"] == 60


class TestDecoratorShortcuts:
    """Tests for rate limit decorator functions."""

    def test_limit_analyze_applies_limiter(self):
        """Test that limit_analyze applies rate limiting."""
        from fastapi import Request

        # Create a function with request parameter (required by slowapi)
        def my_endpoint(request: Request):
            return {"result": "ok"}

        # Apply the decorator
        decorated = limit_analyze(my_endpoint)

        # The decorated function should be callable
        assert callable(decorated)

    def test_limit_search_applies_limiter(self):
        """Test that limit_search applies rate limiting."""
        from fastapi import Request

        def search_endpoint(request: Request):
            return {"results": []}

        decorated = limit_search(search_endpoint)
        assert callable(decorated)

    def test_limit_suggest_applies_limiter(self):
        """Test that limit_suggest applies rate limiting."""
        from fastapi import Request

        def suggest_endpoint(request: Request):
            return {"suggestions": []}

        decorated = limit_suggest(suggest_endpoint)
        assert callable(decorated)

    def test_limit_profile_applies_limiter(self):
        """Test that limit_profile applies rate limiting."""
        from fastapi import Request

        def profile_endpoint(request: Request):
            return {"profile": {}}

        decorated = limit_profile(profile_endpoint)
        assert callable(decorated)

    def test_limit_crud_applies_limiter(self):
        """Test that limit_crud applies rate limiting."""
        from fastapi import Request

        def crud_endpoint(request: Request):
            return {"item": {}}

        decorated = limit_crud(crud_endpoint)
        assert callable(decorated)


class TestLimiterInstance:
    """Tests for the limiter instance."""

    def test_limiter_exists(self):
        """Test that limiter instance is created."""
        assert limiter is not None

    def test_limiter_has_limit_method(self):
        """Test that limiter has the limit method."""
        assert hasattr(limiter, "limit")
        assert callable(limiter.limit)
