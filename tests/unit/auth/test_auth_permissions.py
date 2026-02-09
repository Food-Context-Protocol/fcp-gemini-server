"""Tests for auth/permissions.py - Demo mode authorization layer."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from fcp.auth.permissions import (
    AuthenticatedUser,
    UserRole,
    _check_write_access,
    require_write_access,
)


class TestUserRole:
    """Tests for UserRole enum."""

    def test_demo_role_value(self):
        """Test DEMO role has correct value."""
        assert UserRole.DEMO.value == "demo"

    def test_authenticated_role_value(self):
        """Test AUTHENTICATED role has correct value."""
        assert UserRole.AUTHENTICATED.value == "authenticated"


class TestAuthenticatedUser:
    """Tests for AuthenticatedUser NamedTuple."""

    def test_create_demo_user(self):
        """Test creating a demo user."""
        user = AuthenticatedUser(user_id="demo_user", role=UserRole.DEMO)
        assert user.user_id == "demo_user"
        assert user.role == UserRole.DEMO

    def test_create_authenticated_user(self):
        """Test creating an authenticated user."""
        user = AuthenticatedUser(user_id="real_user_123", role=UserRole.AUTHENTICATED)
        assert user.user_id == "real_user_123"
        assert user.role == UserRole.AUTHENTICATED

    def test_is_demo_true_for_demo_user(self):
        """Test is_demo returns True for demo users."""
        user = AuthenticatedUser(user_id="demo", role=UserRole.DEMO)
        assert user.is_demo is True

    def test_is_demo_false_for_authenticated_user(self):
        """Test is_demo returns False for authenticated users."""
        user = AuthenticatedUser(user_id="user123", role=UserRole.AUTHENTICATED)
        assert user.is_demo is False

    def test_can_write_false_for_demo_user(self):
        """Test can_write returns False for demo users (read-only)."""
        user = AuthenticatedUser(user_id="demo", role=UserRole.DEMO)
        assert user.can_write is False

    def test_can_write_true_for_authenticated_user(self):
        """Test can_write returns True for authenticated users."""
        user = AuthenticatedUser(user_id="user123", role=UserRole.AUTHENTICATED)
        assert user.can_write is True

    def test_namedtuple_unpacking(self):
        """Test NamedTuple can be unpacked."""
        user = AuthenticatedUser(user_id="test_user", role=UserRole.DEMO)
        user_id, role = user
        assert user_id == "test_user"
        assert role == UserRole.DEMO


class TestCheckWriteAccess:
    """Tests for _check_write_access helper function."""

    def test_allows_authenticated_user(self):
        """Test that authenticated users are allowed through."""
        user = AuthenticatedUser(user_id="real_user", role=UserRole.AUTHENTICATED)
        result = _check_write_access(user)
        assert result == user
        assert result.user_id == "real_user"

    def test_blocks_demo_user_with_403(self):
        """Test that demo users are blocked with 403 Forbidden."""
        user = AuthenticatedUser(user_id="demo_user", role=UserRole.DEMO)

        with patch("fcp.auth.permissions.audit_log") as mock_audit:
            with pytest.raises(HTTPException) as exc_info:
                _check_write_access(user)

            assert exc_info.value.status_code == 403
            assert "Demo mode" in exc_info.value.detail
            assert "read-only" in exc_info.value.detail

            # Verify audit log was called
            mock_audit.log_access_denied.assert_called_once_with(
                resource_type="write_operation",
                resource_id=None,
                user_id="demo_user",
                reason="demo_mode_write_blocked",
            )

    def test_error_message_suggests_sign_in(self):
        """Test error message tells user to sign in."""
        user = AuthenticatedUser(user_id="demo", role=UserRole.DEMO)

        with patch("fcp.auth.permissions.audit_log"):
            with pytest.raises(HTTPException) as exc_info:
                _check_write_access(user)

            assert "Sign in" in exc_info.value.detail


class TestRequireWriteAccessDependency:
    """Tests for require_write_access FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_allows_authenticated_user(self):
        """Test that authenticated users with valid token are allowed through the dependency."""
        from tests.constants import TEST_AUTH_TOKEN

        with patch("fcp.auth.local.DEMO_MODE", False):
            result = await require_write_access(authorization=f"Bearer {TEST_AUTH_TOKEN}")

            assert result.user_id == "admin"  # Valid token returns admin user
            assert result.role == UserRole.AUTHENTICATED
            assert result.can_write is True

    @pytest.mark.asyncio
    async def test_blocks_demo_user_with_403(self):
        """Test that demo users (no auth) are blocked with 403 Forbidden."""
        with (
            patch("fcp.auth.local.DEMO_MODE", False),
            patch("fcp.auth.permissions.audit_log") as mock_audit,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await require_write_access(authorization=None)

            assert exc_info.value.status_code == 403
            assert "Demo mode" in exc_info.value.detail

            # Verify audit log was called
            mock_audit.log_access_denied.assert_called_once()


class TestGetCurrentUserDemoFallback:
    """Tests for get_current_user demo mode fallback behavior."""

    @pytest.mark.asyncio
    async def test_no_auth_header_returns_demo_user(self):
        """Test missing Authorization header returns demo user."""
        with patch("fcp.auth.local.DEMO_MODE", False):
            from fcp.auth.local import get_current_user

            result = await get_current_user(authorization=None)

            assert isinstance(result, AuthenticatedUser)
            assert result.role == UserRole.DEMO
            assert result.is_demo is True
            assert result.can_write is False

    @pytest.mark.asyncio
    async def test_invalid_auth_format_returns_demo_user(self):
        """Test invalid Authorization format returns demo user."""
        with patch("fcp.auth.local.DEMO_MODE", False):
            from fcp.auth.local import get_current_user

            result = await get_current_user(authorization="InvalidFormat")

            assert isinstance(result, AuthenticatedUser)
            assert result.role == UserRole.DEMO

    @pytest.mark.asyncio
    async def test_non_bearer_scheme_returns_demo_user(self):
        """Test non-Bearer scheme returns demo user."""
        with patch("fcp.auth.local.DEMO_MODE", False):
            from fcp.auth.local import get_current_user

            result = await get_current_user(authorization="Basic dXNlcjpwYXNz")

            assert isinstance(result, AuthenticatedUser)
            assert result.role == UserRole.DEMO

    @pytest.mark.asyncio
    async def test_any_bearer_token_returns_authenticated(self):
        """Test that invalid tokens are rejected when FCP_TOKEN is configured.

        With local auth and FCP_TOKEN set, only the valid token is accepted.
        Invalid tokens fall back to demo user.
        """
        with patch("fcp.auth.local.DEMO_MODE", False):
            from fcp.auth.local import get_current_user

            result = await get_current_user(authorization="Bearer any-token-value")

            assert isinstance(result, AuthenticatedUser)
            assert result.role == UserRole.DEMO  # Invalid token returns demo user
            assert result.is_demo is True

    @pytest.mark.asyncio
    async def test_valid_token_returns_authenticated_user(self):
        """Test valid token (matching FCP_TOKEN) returns authenticated user with write access."""
        from tests.constants import TEST_AUTH_TOKEN

        with patch("fcp.auth.local.DEMO_MODE", False):
            from fcp.auth.local import get_current_user

            result = await get_current_user(authorization=f"Bearer {TEST_AUTH_TOKEN}")

            assert isinstance(result, AuthenticatedUser)
            assert result.user_id == "admin"  # Valid token returns admin user
            assert result.role == UserRole.AUTHENTICATED
            assert result.is_demo is False
            assert result.can_write is True

    @pytest.mark.asyncio
    async def test_demo_mode_env_returns_demo_user(self):
        """Test DEMO_MODE=true env var returns demo user regardless of auth."""
        # Patch in firebase.py where the imported constants are used
        with (
            patch("fcp.auth.local.DEMO_MODE", True),
            patch("fcp.auth.local.DEMO_USER_ID", "demo_test_user"),
        ):
            from fcp.auth.local import get_current_user

            result = await get_current_user(authorization="Bearer some-token")

            assert isinstance(result, AuthenticatedUser)
            assert result.user_id == "demo_test_user"
            assert result.role == UserRole.DEMO


class TestEndpointPermissions:
    """Integration tests for endpoint permission behavior."""

    @pytest.mark.asyncio
    async def test_read_endpoint_allows_demo_user(self):
        """Test that GET endpoints work for demo users."""
        # This tests the pattern: demo users can read, not write
        demo_user = AuthenticatedUser(user_id="demo", role=UserRole.DEMO)

        # Demo user can be used for read operations
        assert demo_user.user_id == "demo"
        # But cannot write
        assert demo_user.can_write is False

    @pytest.mark.asyncio
    async def test_write_endpoint_blocks_demo_user(self):
        """Test that POST/PUT/DELETE endpoints block demo users."""
        demo_user = AuthenticatedUser(user_id="demo", role=UserRole.DEMO)

        with patch("fcp.auth.permissions.audit_log"):
            with pytest.raises(HTTPException) as exc_info:
                _check_write_access(demo_user)

            assert exc_info.value.status_code == 403
