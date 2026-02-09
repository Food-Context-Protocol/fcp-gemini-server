"""Local authentication for FCP server.

Token-based authentication with demo mode support.
Demo mode: Unauthenticated users get read-only access to shared sample data.
"""

from __future__ import annotations

import logging
import os

from fastapi import Header

from fcp.auth.permissions import (
    DEMO_MODE,
    DEMO_USER_ID,
    AuthenticatedUser,
    UserRole,
)
from fcp.utils.metrics import record_auth_failure

logger = logging.getLogger(__name__)


async def verify_token(token: str) -> dict:
    """Verify authentication token and return user info."""
    if not token:
        record_auth_failure("empty_token")
        return {"uid": "anonymous"}
    return {"uid": token}


async def get_current_user(authorization: str | None = Header(None)) -> AuthenticatedUser:
    """FastAPI dependency to extract user from Authorization header.

    Demo mode behavior:
    - If DEMO_MODE env var is set to true: Always returns demo user
    - If no/invalid Authorization header: Returns demo user with read-only access
    - If valid Authorization header: Returns authenticated user with full access
    """
    # Demo mode bypass
    if DEMO_MODE:
        logger.info("Demo mode (env): using demo user %s", DEMO_USER_ID)
        return AuthenticatedUser(user_id=DEMO_USER_ID, role=UserRole.DEMO)

    # No authorization header
    if not authorization:
        logger.info("No auth header: using demo user %s (read-only)", DEMO_USER_ID)
        return AuthenticatedUser(user_id=DEMO_USER_ID, role=UserRole.DEMO)

    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.info("Invalid auth format: using demo user %s (read-only)", DEMO_USER_ID)
        return AuthenticatedUser(user_id=DEMO_USER_ID, role=UserRole.DEMO)

    token = parts[1]

    # Validate token against FCP_TOKEN if configured
    expected_token = os.environ.get("FCP_TOKEN")
    if expected_token:
        if token != expected_token:
            logger.warning("Invalid token provided, falling back to demo user")
            record_auth_failure("invalid_token")
            return AuthenticatedUser(user_id=DEMO_USER_ID, role=UserRole.DEMO)
        # Valid token - use a consistent admin user ID
        return AuthenticatedUser(user_id="admin", role=UserRole.AUTHENTICATED)

    # No FCP_TOKEN configured - treat token as user_id (backward compatible)
    return AuthenticatedUser(user_id=token, role=UserRole.AUTHENTICATED)
