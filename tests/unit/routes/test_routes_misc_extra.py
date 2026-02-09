"""Coverage tests for misc routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fcp.auth.permissions import AuthenticatedUser, UserRole
from fcp.routes.misc import DonateMealRequest, post_donate_meal


@pytest.mark.asyncio
async def test_post_donate_meal_success_and_error():
    user = AuthenticatedUser(user_id="u1", role=UserRole.AUTHENTICATED)
    req = DonateMealRequest(log_id="log1", organization="Org")

    with patch("fcp.routes.misc.donate_meal", new=AsyncMock(return_value={"success": True})):
        result = await post_donate_meal(req, user=user)
        assert result["success"] is True

    with patch("fcp.routes.misc.donate_meal", new=AsyncMock(return_value={"success": False, "error": "nope"})):
        with pytest.raises(Exception):
            await post_donate_meal(req, user=user)
