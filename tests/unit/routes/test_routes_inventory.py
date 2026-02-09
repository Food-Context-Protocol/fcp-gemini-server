"""Tests for routes/inventory.py endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from fcp.api import app
from fcp.auth.permissions import AuthenticatedUser, UserRole
from tests.constants import TEST_AUTH_HEADER, TEST_USER_ID

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _close_client():
    """Ensure the shared TestClient is properly closed."""
    yield
    client.close()


@pytest.fixture
def mock_auth():
    """Mock authentication to return test user."""
    from fcp.auth.local import get_current_user
    from fcp.auth.permissions import require_write_access

    user = AuthenticatedUser(user_id=TEST_USER_ID, role=UserRole.AUTHENTICATED)

    async def override_get_current_user(authorization=None):
        return user

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_write_access] = override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_write_access, None)


class TestGetUserPantry:
    """Tests for GET /inventory/pantry endpoint."""

    def test_get_pantry_success(self, mock_auth):
        """Test successfully fetching user's pantry."""
        mock_items = [
            {"name": "eggs", "quantity": 12, "expiry": "2026-02-10"},
            {"name": "milk", "quantity": 1, "expiry": "2026-02-05"},
        ]

        with patch("fcp.services.firestore.get_firestore_client") as mock_get_client:
            mock_db = AsyncMock()
            mock_db.get_pantry = AsyncMock(return_value=mock_items)
            mock_get_client.return_value = mock_db

            response = client.get(
                "/inventory/pantry",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert len(data["items"]) == 2
            assert data["items"][0]["name"] == "eggs"

    def test_get_pantry_empty(self, mock_auth):
        """Test fetching empty pantry."""
        with patch("fcp.services.firestore.get_firestore_client") as mock_get_client:
            mock_db = AsyncMock()
            mock_db.get_pantry = AsyncMock(return_value=[])
            mock_get_client.return_value = mock_db

            response = client.get(
                "/inventory/pantry",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            assert response.json()["items"] == []


class TestPostAddToPantry:
    """Tests for POST /inventory/pantry endpoint."""

    def test_add_to_pantry_success(self, mock_auth):
        """Test adding items to pantry."""
        with patch("fcp.routes.inventory.add_to_pantry", new_callable=AsyncMock) as mock_add:
            mock_add.return_value = ["id1", "id2", "id3"]

            response = client.post(
                "/inventory/pantry",
                json={"items": ["eggs", "milk", "bread"]},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert "added_ids" in data
            assert len(data["added_ids"]) == 3


class TestPatchPantryItem:
    """Tests for PATCH /inventory/pantry/{item_id} endpoint."""

    def test_patch_pantry_item_success(self, mock_auth):
        """Test successfully updating a pantry item."""
        with patch("fcp.routes.inventory.update_pantry_item", new_callable=AsyncMock) as mock_update:
            mock_update.return_value = {"success": True, "item_id": "eggs"}

            response = client.patch(
                "/inventory/pantry/eggs",
                json={"quantity": 24},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            mock_update.assert_called_once()

    def test_patch_pantry_item_no_updates(self, mock_auth):
        """Test patching with empty updates returns error."""
        response = client.patch(
            "/inventory/pantry/eggs",
            json={},
            headers=TEST_AUTH_HEADER,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "No update fields" in data["error"]


class TestDeletePantryItemRoute:
    """Tests for DELETE /inventory/pantry/{item_id} endpoint."""

    def test_delete_pantry_item_success(self, mock_auth):
        """Test successfully deleting a pantry item."""
        with patch("fcp.routes.inventory.delete_pantry_item", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = {"success": True}

            response = client.delete(
                "/inventory/pantry/eggs",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            mock_delete.assert_called_once_with("admin", "eggs")


class TestGetPantryRecipeSuggestions:
    """Tests for GET /inventory/suggestions endpoint."""

    def test_get_suggestions_default_context(self, mock_auth):
        """Test getting recipe suggestions with default context."""
        mock_result = {"suggestions": [{"name": "Pasta Carbonara", "ingredients": ["eggs", "bacon"]}]}

        with patch("fcp.routes.inventory.suggest_recipe_from_pantry", new_callable=AsyncMock) as mock_suggest:
            mock_suggest.return_value = mock_result

            response = client.get(
                "/inventory/suggestions",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_suggest.assert_called_once_with("admin", "dinner")

    def test_get_suggestions_custom_context(self, mock_auth):
        """Test getting recipe suggestions with custom context."""
        with patch("fcp.routes.inventory.suggest_recipe_from_pantry", new_callable=AsyncMock) as mock_suggest:
            mock_suggest.return_value = {"suggestions": []}

            response = client.get(
                "/inventory/suggestions?context=breakfast",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_suggest.assert_called_once_with("admin", "breakfast")


class TestGetPantryExpiryCheck:
    """Tests for GET /inventory/expiry endpoint."""

    def test_get_expiry_check_success(self, mock_auth):
        """Test checking expiring items."""
        mock_result = {"expiring_soon": [{"name": "milk", "days_until_expiry": 2}]}

        with patch("fcp.routes.inventory.check_pantry_expiry", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_result

            response = client.get(
                "/inventory/expiry",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_check.assert_called_once_with("admin")


class TestPostDeductIngredients:
    """Tests for POST /inventory/pantry/deduct endpoint."""

    def test_deduct_ingredients_success(self, mock_auth):
        """Test deducting ingredients from pantry."""
        mock_result = {"deducted": ["eggs", "milk"], "not_found": []}

        with patch("fcp.routes.inventory.deduct_from_pantry", new_callable=AsyncMock) as mock_deduct:
            mock_deduct.return_value = mock_result

            response = client.post(
                "/inventory/pantry/deduct",
                json={"ingredients": ["eggs", "milk"], "servings": 2},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_deduct.assert_called_once_with("admin", ["eggs", "milk"], 2)

    def test_deduct_ingredients_default_servings(self, mock_auth):
        """Test deducting with default servings."""
        with patch("fcp.routes.inventory.deduct_from_pantry", new_callable=AsyncMock) as mock_deduct:
            mock_deduct.return_value = {"deducted": ["eggs"]}

            response = client.post(
                "/inventory/pantry/deduct",
                json={"ingredients": ["eggs"]},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            # Default servings is 1
            mock_deduct.assert_called_once_with("admin", ["eggs"], 1)


class TestGetExpiringItems:
    """Tests for GET /inventory/pantry/expiring endpoint."""

    def test_get_expiring_items_default_days(self, mock_auth):
        """Test getting expiring items with default days threshold."""
        mock_result = {"expiring": [{"name": "yogurt", "days": 2}]}

        with patch("fcp.routes.inventory.check_expiring_items", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_result

            response = client.get(
                "/inventory/pantry/expiring",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_check.assert_called_once_with("admin", days_threshold=3)

    def test_get_expiring_items_custom_days(self, mock_auth):
        """Test getting expiring items with custom days threshold."""
        with patch("fcp.routes.inventory.check_expiring_items", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {"expiring": []}

            response = client.get(
                "/inventory/pantry/expiring?days=7",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_check.assert_called_once_with("admin", days_threshold=7)


class TestGetPantryMealSuggestions:
    """Tests for GET /inventory/pantry/meal-suggestions endpoint."""

    def test_get_meal_suggestions_prioritize_expiring(self, mock_auth):
        """Test getting meal suggestions prioritizing expiring items."""
        mock_result = {"suggestions": [{"name": "Omelette", "reason": "Uses expiring eggs"}]}

        with patch("fcp.routes.inventory.suggest_meals_from_pantry", new_callable=AsyncMock) as mock_suggest:
            mock_suggest.return_value = mock_result

            response = client.get(
                "/inventory/pantry/meal-suggestions",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_suggest.assert_called_once_with("admin", True)

    def test_get_meal_suggestions_no_prioritize(self, mock_auth):
        """Test getting meal suggestions without prioritizing expiring items."""
        with patch("fcp.routes.inventory.suggest_meals_from_pantry", new_callable=AsyncMock) as mock_suggest:
            mock_suggest.return_value = {"suggestions": []}

            response = client.get(
                "/inventory/pantry/meal-suggestions?prioritize_expiring=false",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_suggest.assert_called_once_with("admin", False)
