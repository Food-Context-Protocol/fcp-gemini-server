"""Authorization permissions for FCP server.

This module provides the authorization layer for demo mode vs authenticated users.
Demo users get read-only access, while authenticated users get full access.
"""

from __future__ import annotations

import logging
import os
import uuid
from enum import Enum
from typing import NamedTuple

from fastapi import Header, HTTPException

from fcp.utils.audit import audit_log
from fcp.utils.metrics import record_permission_denied

logger = logging.getLogger(__name__)


class UserRole(Enum):
    """User authorization role."""

    DEMO = "demo"
    AUTHENTICATED = "authenticated"


class AuthenticatedUser(NamedTuple):
    """Authenticated user with role information.

    Attributes:
        user_id: The user's unique identifier
        role: The user's authorization role
    """

    user_id: str
    role: UserRole

    @property
    def is_demo(self) -> bool:
        """Check if user is in demo mode (read-only access)."""
        # Use value comparison for robustness against module reloading issues
        return self.role.value == UserRole.DEMO.value

    @property
    def can_write(self) -> bool:
        """Check if user has write access (authenticated users only)."""
        # Use value comparison for robustness against module reloading issues
        return self.role.value == UserRole.AUTHENTICATED.value


# Demo mode configuration
# Generate a unique demo user ID per instance if not specified to avoid hardcoded public IDs
DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"
_default_demo_user_id = f"demo_{uuid.uuid4().hex[:12]}"
DEMO_USER_ID = os.environ.get("DEMO_USER_ID") or _default_demo_user_id


def _check_write_access(user: AuthenticatedUser) -> AuthenticatedUser:
    """Check if user has write access, raising 403 if not.

    Args:
        user: The authenticated user to check

    Returns:
        The authenticated user if they have write access

    Raises:
        HTTPException: 403 Forbidden if user is in demo mode
    """
    if not user.can_write:
        record_permission_denied("write_operation")
        audit_log.log_access_denied(
            resource_type="write_operation",
            resource_id=None,
            user_id=user.user_id,
            reason="demo_mode_write_blocked",
        )
        raise HTTPException(
            status_code=403,
            detail="Demo mode: read-only access. Sign in for full access.",
        )
    return user


async def require_write_access(
    authorization: str | None = Header(None),
) -> AuthenticatedUser:
    """FastAPI dependency that requires write access (authenticated users only).

    Use this dependency for endpoints that modify data (POST, PUT, PATCH, DELETE).
    Demo users will receive a 403 Forbidden response.

    This dependency combines authentication (get_current_user) with write permission
    checking in a single dependency.

    Usage:
        @app.post("/meals")
        async def create_meal(user: AuthenticatedUser = Depends(require_write_access)):
            ...

    Args:
        authorization: The Authorization header value

    Returns:
        The authenticated user if they have write access

    Raises:
        HTTPException: 403 Forbidden if user is in demo mode
    """
    # Import here to avoid circular imports (firebase.py imports from permissions.py)
    from fcp.auth.local import get_current_user

    user = await get_current_user(authorization)
    return _check_write_access(user)
