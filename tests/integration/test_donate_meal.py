"""Integration tests for donate_meal (requires Firestore credentials)."""

import os

import pytest

requires_firestore = pytest.mark.skipif(
    not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
    reason="GOOGLE_APPLICATION_CREDENTIALS not set",
)


class TestDonateMealIntegration:
    """Integration tests for donate_meal (requires Firestore credentials)."""

    @requires_firestore
    @pytest.mark.asyncio
    async def test_donate_meal_success(self):
        """Test successful meal donation with real Firestore."""
        from fcp.tools import add_meal, donate_meal

        user_id = "test-donate-user"

        meal_result = await add_meal(
            user_id=user_id,
            dish_name="Test Donation Meal",
            venue="Test Kitchen",
        )

        if not meal_result.get("success"):
            pytest.skip("Could not create test meal")

        log_id = meal_result.get("log_id")

        result = await donate_meal(
            user_id=user_id,
            log_id=log_id,
            organization="Test Food Bank",
        )

        assert result["success"] is True
        assert result["organization"] == "Test Food Bank"
