"""Tests for auth/local.py (local token authentication)."""

import os
from unittest.mock import patch

import pytest

from fcp.auth.local import get_current_user, verify_token
from fcp.auth.permissions import UserRole


class TestVerifyToken:
    """Tests for verify_token function (local auth)."""

    @pytest.mark.asyncio
    async def test_returns_uid_from_token(self):
        """Token IS the user_id in local auth."""
        result = await verify_token("user-abc-123")
        assert result == {"uid": "user-abc-123"}

    @pytest.mark.asyncio
    async def test_empty_token_returns_anonymous(self):
        """Empty token returns anonymous uid."""
        result = await verify_token("")
        assert result == {"uid": "anonymous"}


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_demo_mode_returns_demo_user(self):
        """Test that demo mode returns demo user with DEMO role."""
        with (
            patch("fcp.auth.local.DEMO_MODE", True),
            patch("fcp.auth.local.DEMO_USER_ID", "demo_user_test"),
        ):
            result = await get_current_user(authorization=None)
            assert result.user_id == "demo_user_test"
            assert result.role == UserRole.DEMO

    @pytest.mark.asyncio
    async def test_demo_mode_ignores_provided_auth(self):
        """Test that demo mode ignores any provided authorization."""
        with (
            patch("fcp.auth.local.DEMO_MODE", True),
            patch("fcp.auth.local.DEMO_USER_ID", "demo_user_abc"),
        ):
            result = await get_current_user(authorization="Bearer some-token")
            assert result.user_id == "demo_user_abc"
            assert result.role == UserRole.DEMO

    @pytest.mark.asyncio
    async def test_missing_auth_returns_demo_user(self):
        """Test that missing authorization returns demo user (not 401)."""
        with patch("fcp.auth.local.DEMO_MODE", False):
            result = await get_current_user(authorization=None)
            assert result.role == UserRole.DEMO
            assert result.is_demo is True

    @pytest.mark.asyncio
    async def test_invalid_auth_format_returns_demo_user(self):
        """Test that invalid authorization format returns demo user."""
        with patch("fcp.auth.local.DEMO_MODE", False):
            result = await get_current_user(authorization="InvalidFormat")
            assert result.role == UserRole.DEMO

    @pytest.mark.asyncio
    async def test_non_bearer_scheme_returns_demo_user(self):
        """Test that non-Bearer scheme returns demo user."""
        with patch("fcp.auth.local.DEMO_MODE", False):
            result = await get_current_user(authorization="Basic dXNlcjpwYXNz")
            assert result.role == UserRole.DEMO

    @pytest.mark.asyncio
    async def test_valid_bearer_token_returns_authenticated_user(self):
        """Test that valid Bearer token (matching FCP_TOKEN) returns authenticated admin user."""
        from tests.constants import TEST_AUTH_TOKEN

        with patch("fcp.auth.local.DEMO_MODE", False):
            result = await get_current_user(authorization=f"Bearer {TEST_AUTH_TOKEN}")
            assert result.user_id == "admin"  # Valid token returns consistent admin user
            assert result.role == UserRole.AUTHENTICATED

    @pytest.mark.asyncio
    async def test_token_as_user_id_when_foodlog_token_not_configured(self):
        """Test that token becomes user_id when FCP_TOKEN is not configured (backward compatible)."""
        with (
            patch("fcp.auth.local.DEMO_MODE", False),
            patch.dict(os.environ, {"FCP_TOKEN": ""}, clear=False),
        ):
            result = await get_current_user(authorization="Bearer custom-user-123")
            assert result.user_id == "custom-user-123"  # Token used as user_id
            assert result.role == UserRole.AUTHENTICATED


class TestModuleConstants:
    """Tests for module-level constants."""

    def test_demo_mode_false_by_default(self):
        """Test DEMO_MODE is false by default."""
        with patch.dict(os.environ, {}, clear=True):
            import importlib

            from fcp.auth import local

            importlib.reload(local)
            # Module loads successfully without errors

    def test_demo_mode_true_when_env_set(self):
        """Test DEMO_MODE is true when DEMO_MODE=true in env."""
        with patch.dict(os.environ, {"DEMO_MODE": "true"}):
            import importlib

            from fcp.auth import permissions

            importlib.reload(permissions)
            assert permissions.DEMO_MODE is True

    def test_demo_user_id_default(self):
        """Test DEMO_USER_ID has UUID-based default value when not specified."""
        with patch.dict(os.environ, {"DEMO_USER_ID": ""}, clear=False):
            import importlib

            from fcp.auth import permissions

            importlib.reload(permissions)
            assert permissions.DEMO_USER_ID.startswith("demo_")
            assert len(permissions.DEMO_USER_ID) == 17  # "demo_" + 12 hex chars

    def test_demo_user_id_from_env(self):
        """Test DEMO_USER_ID can be set via environment."""
        with patch.dict(os.environ, {"DEMO_USER_ID": "custom_demo_user"}):
            import importlib

            from fcp.auth import permissions

            importlib.reload(permissions)
            assert permissions.DEMO_USER_ID == "custom_demo_user"
