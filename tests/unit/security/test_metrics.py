"""Tests for security event metrics."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


class TestSecurityMetrics:
    """Tests for security event recording functions."""

    def test_record_auth_failure(self):
        """Test recording authentication failures."""
        from fcp.utils.metrics import SECURITY_EVENTS, record_auth_failure

        # Get the initial value
        initial = SECURITY_EVENTS.labels(event_type="auth_failure", outcome="invalid_token")._value.get()

        record_auth_failure("invalid_token")

        # Verify the counter was incremented
        new_value = SECURITY_EVENTS.labels(event_type="auth_failure", outcome="invalid_token")._value.get()
        assert new_value == initial + 1

    def test_record_auth_failure_expired(self):
        """Test recording expired token failures."""
        from fcp.utils.metrics import SECURITY_EVENTS, record_auth_failure

        initial = SECURITY_EVENTS.labels(event_type="auth_failure", outcome="expired_token")._value.get()

        record_auth_failure("expired_token")

        new_value = SECURITY_EVENTS.labels(event_type="auth_failure", outcome="expired_token")._value.get()
        assert new_value == initial + 1

    def test_record_auth_failure_revoked(self):
        """Test recording revoked token failures."""
        from fcp.utils.metrics import SECURITY_EVENTS, record_auth_failure

        initial = SECURITY_EVENTS.labels(event_type="auth_failure", outcome="revoked_token")._value.get()

        record_auth_failure("revoked_token")

        new_value = SECURITY_EVENTS.labels(event_type="auth_failure", outcome="revoked_token")._value.get()
        assert new_value == initial + 1

    def test_record_permission_denied(self):
        """Test recording permission denied events."""
        from fcp.utils.metrics import SECURITY_EVENTS, record_permission_denied

        initial = SECURITY_EVENTS.labels(event_type="permission_denied", outcome="write_operation")._value.get()

        record_permission_denied("write_operation")

        new_value = SECURITY_EVENTS.labels(event_type="permission_denied", outcome="write_operation")._value.get()
        assert new_value == initial + 1

    def test_record_rate_limit_exceeded(self):
        """Test recording rate limit exceeded events."""
        from fcp.utils.metrics import (
            SECURITY_EVENTS,
            record_rate_limit_exceeded,
        )

        initial = SECURITY_EVENTS.labels(event_type="rate_limit", outcome="/api/meals")._value.get()

        record_rate_limit_exceeded("/api/meals")

        new_value = SECURITY_EVENTS.labels(event_type="rate_limit", outcome="/api/meals")._value.get()
        assert new_value == initial + 1


class TestAuthFailureMetricsIntegration:
    """Tests for auth failure metrics integration with local auth."""

    @pytest.mark.asyncio
    async def test_empty_token_records_metric(self):
        """Test that empty token records auth_failure metric."""
        from fcp.auth.local import verify_token
        from fcp.utils.metrics import SECURITY_EVENTS

        initial = SECURITY_EVENTS.labels(event_type="auth_failure", outcome="empty_token")._value.get()

        result = await verify_token("")

        assert result == {"uid": "anonymous"}

        new_value = SECURITY_EVENTS.labels(event_type="auth_failure", outcome="empty_token")._value.get()
        assert new_value == initial + 1

    @pytest.mark.asyncio
    async def test_empty_token_calls_record_auth_failure(self):
        """Test that empty token calls record_auth_failure with correct argument."""
        from fcp.auth.local import verify_token

        with patch("fcp.auth.local.record_auth_failure") as mock_record:
            await verify_token("")
            mock_record.assert_called_once_with("empty_token")

    @pytest.mark.asyncio
    async def test_valid_token_does_not_record_metric(self):
        """Test that a valid token does not record any auth failure metric."""
        from fcp.auth.local import verify_token

        with patch("fcp.auth.local.record_auth_failure") as mock_record:
            result = await verify_token("valid-user-id")

            assert result == {"uid": "valid-user-id"}
            mock_record.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_token_metric_increments_multiple_times(self):
        """Test that repeated empty tokens increment the metric counter."""
        from fcp.auth.local import verify_token
        from fcp.utils.metrics import SECURITY_EVENTS

        initial = SECURITY_EVENTS.labels(event_type="auth_failure", outcome="empty_token")._value.get()

        await verify_token("")
        await verify_token("")
        await verify_token("")

        new_value = SECURITY_EVENTS.labels(event_type="auth_failure", outcome="empty_token")._value.get()
        assert new_value == initial + 3

    @pytest.mark.asyncio
    async def test_token_is_used_as_uid(self):
        """Test that local auth uses the token directly as the uid."""
        from fcp.auth.local import verify_token

        result = await verify_token("my-custom-user-123")
        assert result == {"uid": "my-custom-user-123"}


class TestPermissionDeniedMetricsIntegration:
    """Tests for permission denied metrics integration in permissions.py."""

    def test_check_write_access_records_metric_on_denial(self):
        """Test that permission denial records metric."""
        from fcp.auth.permissions import (
            AuthenticatedUser,
            UserRole,
            _check_write_access,
        )
        from fcp.utils.metrics import SECURITY_EVENTS

        initial = SECURITY_EVENTS.labels(event_type="permission_denied", outcome="write_operation")._value.get()

        demo_user = AuthenticatedUser(user_id="demo_user", role=UserRole.DEMO)

        with pytest.raises(HTTPException) as exc_info:
            _check_write_access(demo_user)

        assert exc_info.value.status_code == 403

        new_value = SECURITY_EVENTS.labels(event_type="permission_denied", outcome="write_operation")._value.get()
        assert new_value == initial + 1

    def test_check_write_access_no_metric_on_success(self):
        """Test that successful write access doesn't record denial metric."""
        from fcp.auth.permissions import (
            AuthenticatedUser,
            UserRole,
            _check_write_access,
        )
        from fcp.utils.metrics import SECURITY_EVENTS

        initial = SECURITY_EVENTS.labels(event_type="permission_denied", outcome="write_operation")._value.get()

        auth_user = AuthenticatedUser(user_id="real_user", role=UserRole.AUTHENTICATED)
        result = _check_write_access(auth_user)

        # Should return the user without raising
        assert result == auth_user

        # Metric should not have been incremented
        new_value = SECURITY_EVENTS.labels(event_type="permission_denied", outcome="write_operation")._value.get()
        assert new_value == initial


class TestRateLimitMetricsIntegration:
    """Tests for rate limit metrics integration in rate_limit.py."""

    def test_rate_limit_handler_records_metric(self):
        """Test that rate limit handler records metric."""

        from fcp.security.rate_limit import rate_limit_exceeded_handler
        from fcp.utils.metrics import SECURITY_EVENTS

        initial = SECURITY_EVENTS.labels(event_type="rate_limit", outcome="/api/analyze")._value.get()

        mock_request = MagicMock()
        mock_request.url.path = "/api/analyze"

        mock_exc = MagicMock()
        mock_exc.retry_after = 60
        mock_exc.detail = "10/minute"

        response = rate_limit_exceeded_handler(mock_request, mock_exc)

        assert response.status_code == 429

        new_value = SECURITY_EVENTS.labels(event_type="rate_limit", outcome="/api/analyze")._value.get()
        assert new_value == initial + 1

    def test_rate_limit_handler_different_endpoints(self):
        """Test that rate limit metrics track different endpoints separately."""

        from fcp.security.rate_limit import rate_limit_exceeded_handler
        from fcp.utils.metrics import SECURITY_EVENTS

        # Record for two different endpoints
        mock_exc = MagicMock()
        mock_exc.retry_after = 60
        mock_exc.detail = "10/minute"

        mock_request1 = MagicMock()
        mock_request1.url.path = "/api/meals"

        mock_request2 = MagicMock()
        mock_request2.url.path = "/api/search"

        initial_meals = SECURITY_EVENTS.labels(event_type="rate_limit", outcome="/api/meals")._value.get()
        initial_search = SECURITY_EVENTS.labels(event_type="rate_limit", outcome="/api/search")._value.get()

        rate_limit_exceeded_handler(mock_request1, mock_exc)
        rate_limit_exceeded_handler(mock_request2, mock_exc)
        rate_limit_exceeded_handler(mock_request1, mock_exc)

        # Meals should have 2, search should have 1
        new_meals = SECURITY_EVENTS.labels(event_type="rate_limit", outcome="/api/meals")._value.get()
        new_search = SECURITY_EVENTS.labels(event_type="rate_limit", outcome="/api/search")._value.get()

        assert new_meals == initial_meals + 2
        assert new_search == initial_search + 1
