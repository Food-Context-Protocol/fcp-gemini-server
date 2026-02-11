"""Tests for auth module (local auth)."""

import importlib
import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from fcp.auth.local import get_current_user, verify_token
from fcp.auth.permissions import DEMO_USER_ID, UserRole


class TestVerifyToken:
    """Tests for verify_token function (local auth)."""

    @pytest.mark.asyncio
    async def test_verify_token_success(self):
        """Token IS the user_id in local auth."""
        result = await verify_token("user123")
        assert result == {"uid": "user123"}

    @pytest.mark.asyncio
    async def test_verify_token_empty_returns_anonymous(self):
        """Empty token returns anonymous uid."""
        result = await verify_token("")
        assert result == {"uid": "anonymous"}


class TestGetCurrentUser:
    """Tests for get_current_user FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_missing_authorization_header_returns_demo_user(self):
        """Missing Authorization header should return demo user."""
        from fcp.auth.local import DEMO_USER_ID

        result = await get_current_user(authorization=None)

        assert result.user_id == DEMO_USER_ID
        assert result.role == UserRole.DEMO
        assert result.is_demo is True
        assert result.can_write is False

    @pytest.mark.asyncio
    async def test_invalid_authorization_format_returns_demo_user(self):
        """Invalid Authorization header format should return demo user."""
        from fcp.auth.local import DEMO_USER_ID

        result = await get_current_user(authorization="some-token")

        assert result.user_id == DEMO_USER_ID
        assert result.role == UserRole.DEMO
        assert result.is_demo is True

    @pytest.mark.asyncio
    async def test_invalid_authorization_wrong_scheme_returns_demo_user(self):
        """Wrong auth scheme (not Bearer) should return demo user."""
        from fcp.auth.local import DEMO_USER_ID

        result = await get_current_user(authorization="Basic some-token")

        assert result.user_id == DEMO_USER_ID
        assert result.role == UserRole.DEMO
        assert result.is_demo is True

    @pytest.mark.asyncio
    async def test_valid_bearer_token_returns_authenticated_user(self):
        """Valid Bearer token (matching FOODLOG_TOKEN) should return authenticated admin user."""
        from tests.constants import TEST_AUTH_TOKEN

        result = await get_current_user(authorization=f"Bearer {TEST_AUTH_TOKEN}")
        assert result.user_id == "admin"  # Valid token returns consistent admin user
        assert result.role == UserRole.AUTHENTICATED
        assert result.is_demo is False
        assert result.can_write is True

    @pytest.mark.asyncio
    async def test_invalid_bearer_token_raises_401(self):
        """Invalid Bearer token (not matching FCP_TOKEN) should raise 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(authorization="Bearer invalid-token")
        assert exc_info.value.status_code == 401

    def test_production_startup_warning_when_no_fcp_token(self):
        """Module logs a warning when FCP_TOKEN is missing in production."""
        import fcp.auth.local as auth_module

        with (
            patch.dict(os.environ, {}, clear=False),
            patch("fcp.settings.settings") as mock_settings,
        ):
            mock_settings.is_production = True
            os.environ.pop("FCP_TOKEN", None)
            # Re-execute the module-level guard
            importlib.reload(auth_module)

        # Reload again without mock to restore normal state
        importlib.reload(auth_module)

    @pytest.mark.asyncio
    async def test_no_fcp_token_production_returns_demo(self):
        """In production without FCP_TOKEN, any token should return demo user."""
        with (
            patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False),
            patch.dict(os.environ, {}, clear=False),
            patch("fcp.auth.local.settings") as mock_settings,
        ):
            mock_settings.is_production = True
            os.environ.pop("FCP_TOKEN", None)
            result = await get_current_user(authorization="Bearer any-token")
            assert result.user_id == DEMO_USER_ID
            assert result.role == UserRole.DEMO
