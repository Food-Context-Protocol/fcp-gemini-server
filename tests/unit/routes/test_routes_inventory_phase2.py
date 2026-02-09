"""Tests for Phase 2 inventory routes."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fcp.auth import get_current_user, require_write_access
from fcp.routes.inventory import router
from tests.constants import TEST_AUTH_HEADER, TEST_USER  # sourcery skip: dont-import-test-modules

# Create test app with inventory router
inventory_test_app = FastAPI()
inventory_test_app.include_router(router, prefix="")

AUTH_HEADER = TEST_AUTH_HEADER


@pytest.fixture(autouse=True)
def mock_auth():
    """Mock authentication for all tests."""
    inventory_test_app.dependency_overrides[get_current_user] = lambda: TEST_USER
    inventory_test_app.dependency_overrides[require_write_access] = lambda: TEST_USER
    yield
    inventory_test_app.dependency_overrides.pop(get_current_user, None)
    inventory_test_app.dependency_overrides.pop(require_write_access, None)


@pytest.fixture
def client():
    """Create test client."""
    with TestClient(inventory_test_app) as client:
        yield client


class TestDeductIngredientsRoute:
    """Tests for POST /inventory/pantry/deduct endpoint."""

    def test_deduct_success(self, client):
        """Should deduct ingredients successfully."""
        mock_result = {
            "success": True,
            "deducted": [{"item": "Chicken", "quantity": 1, "remaining": 4}],
            "not_found": [],
            "low_stock": [],
        }

        with patch("fcp.routes.inventory.deduct_from_pantry", new_callable=AsyncMock) as mock_deduct:
            mock_deduct.return_value = mock_result

            response = client.post(
                "/inventory/pantry/deduct",
                json={"ingredients": ["chicken"], "servings": 1},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["deducted"]) == 1

    def test_deduct_with_multiple_servings(self, client):
        """Should pass servings to deduction function."""
        mock_result = {
            "success": True,
            "deducted": [],
            "not_found": [],
            "low_stock": [],
        }

        with patch("fcp.routes.inventory.deduct_from_pantry", new_callable=AsyncMock) as mock_deduct:
            mock_deduct.return_value = mock_result

            response = client.post(
                "/inventory/pantry/deduct",
                json={"ingredients": ["rice"], "servings": 4},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_deduct.assert_called_once()
            call_args = mock_deduct.call_args
            assert call_args[0][2] == 4  # servings


class TestExpiringItemsRoute:
    """Tests for GET /inventory/pantry/expiring endpoint."""

    def test_get_expiring_items(self, client):
        """Should return expiring items."""
        mock_result = {
            "expiring_soon": [{"id": "1", "name": "Milk", "days_left": 2}],
            "expired": [],
        }

        with patch("fcp.routes.inventory.check_expiring_items", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_result

            response = client.get("/inventory/pantry/expiring", headers=AUTH_HEADER)

            assert response.status_code == 200
            data = response.json()
            assert len(data["expiring_soon"]) == 1

    def test_get_expiring_items_custom_days(self, client):
        """Should pass custom days threshold."""
        mock_result = {"expiring_soon": [], "expired": []}

        with patch("fcp.routes.inventory.check_expiring_items", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_result

            response = client.get("/inventory/pantry/expiring?days=7", headers=AUTH_HEADER)

            assert response.status_code == 200
            mock_check.assert_called_once()
            call_args = mock_check.call_args
            assert call_args.kwargs["days_threshold"] == 7

    def test_days_below_min_returns_422(self, client):
        """days=0 should be rejected by validation (ge=1)."""
        response = client.get(
            "/inventory/pantry/expiring",
            params={"days": 0},
            headers=AUTH_HEADER,
        )

        assert response.status_code == 422

    def test_days_above_max_returns_422(self, client):
        """days=31 should be rejected by validation (le=30)."""
        response = client.get(
            "/inventory/pantry/expiring",
            params={"days": 31},
            headers=AUTH_HEADER,
        )

        assert response.status_code == 422


class TestMealSuggestionsRoute:
    """Tests for GET /inventory/pantry/meal-suggestions endpoint."""

    def test_get_meal_suggestions(self, client):
        """Should return meal suggestions."""
        mock_result = {
            "suggestions": [
                {
                    "meal": "Chicken Stir Fry",
                    "uses_ingredients": ["Chicken", "Rice"],
                    "difficulty": "easy",
                }
            ]
        }

        with patch("fcp.routes.inventory.suggest_meals_from_pantry", new_callable=AsyncMock) as mock_suggest:
            mock_suggest.return_value = mock_result

            response = client.get("/inventory/pantry/meal-suggestions", headers=AUTH_HEADER)

            assert response.status_code == 200
            data = response.json()
            assert len(data["suggestions"]) == 1

    def test_get_meal_suggestions_without_priority(self, client):
        """Should pass prioritize_expiring parameter."""
        mock_result = {"suggestions": []}

        with patch("fcp.routes.inventory.suggest_meals_from_pantry", new_callable=AsyncMock) as mock_suggest:
            mock_suggest.return_value = mock_result

            response = client.get(
                "/inventory/pantry/meal-suggestions?prioritize_expiring=false",
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_suggest.assert_called_once()
            call_args = mock_suggest.call_args
            assert call_args[0][1] is False  # prioritize_expiring
