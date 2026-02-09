"""Tests for SSE server authentication helpers."""

from __future__ import annotations

from unittest.mock import patch

from fcp.auth.permissions import DEMO_USER_ID, UserRole
from fcp.server_sse import _get_env_user, get_sse_user

# ---------- _get_env_user tests ----------


@patch.dict("os.environ", {"FCP_TOKEN": "my-secret"})
def test_get_env_user_with_token():
    user = _get_env_user()
    assert user.user_id == "admin"
    assert user.role == UserRole.AUTHENTICATED


@patch.dict("os.environ", {}, clear=True)
def test_get_env_user_without_token():
    user = _get_env_user()
    assert user.user_id == DEMO_USER_ID
    assert user.role == UserRole.DEMO


@patch.dict("os.environ", {"FCP_TOKEN": ""})
def test_get_env_user_empty_token():
    """Empty string FCP_TOKEN is treated as not set."""
    user = _get_env_user()
    assert user.user_id == DEMO_USER_ID
    assert user.role == UserRole.DEMO


# ---------- get_sse_user tests ----------


def test_get_sse_user_no_header():
    user = get_sse_user(None)
    assert user.user_id == DEMO_USER_ID
    assert user.role == UserRole.DEMO


def test_get_sse_user_invalid_format():
    user = get_sse_user("Token abc")
    assert user.user_id == DEMO_USER_ID
    assert user.role == UserRole.DEMO


def test_get_sse_user_single_word():
    user = get_sse_user("abc")
    assert user.user_id == DEMO_USER_ID
    assert user.role == UserRole.DEMO


@patch.dict("os.environ", {"FCP_TOKEN": "secret123"})
def test_get_sse_user_valid_token():
    user = get_sse_user("Bearer secret123")
    assert user.user_id == "admin"
    assert user.role == UserRole.AUTHENTICATED


@patch.dict("os.environ", {"FCP_TOKEN": "secret123"})
def test_get_sse_user_wrong_token():
    user = get_sse_user("Bearer wrong")
    assert user.user_id == DEMO_USER_ID
    assert user.role == UserRole.DEMO


@patch.dict("os.environ", {}, clear=True)
def test_get_sse_user_no_fcp_token_configured():
    """When no FCP_TOKEN env var, token is used as user_id (backward compat)."""
    user = get_sse_user("Bearer my-user-id")
    assert user.user_id == "my-user-id"
    assert user.role == UserRole.AUTHENTICATED
