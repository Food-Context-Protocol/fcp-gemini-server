"""Tests for Safety Routes Module.

Tests the safety routes extracted to routes/safety.py.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fcp.auth import get_current_user, require_write_access
from fcp.routes.safety import router
from tests.constants import TEST_AUTH_HEADER, TEST_USER  # sourcery skip: dont-import-test-modules

# Create test app with safety router
safety_test_app = FastAPI()
safety_test_app.include_router(router, prefix="/safety")

# Mock auth dependency - use centralized constant
AUTH_HEADER = TEST_AUTH_HEADER


def override_get_current_user():
    """Override get_current_user for tests."""
    return TEST_USER


def override_require_write_access():
    """Override require_write_access for tests."""
    return TEST_USER


@pytest.fixture(autouse=True)
def mock_auth():
    """Mock authentication for all tests using FastAPI dependency overrides."""
    safety_test_app.dependency_overrides[get_current_user] = override_get_current_user
    safety_test_app.dependency_overrides[require_write_access] = override_require_write_access
    yield
    safety_test_app.dependency_overrides.clear()


@pytest.fixture
def client():
    """Create test client."""
    with TestClient(safety_test_app) as client:
        yield client


class TestRecallsEndpoint:
    """Tests for /safety/recalls endpoint."""

    def test_check_recalls_success(self, client):
        """Test successful recall check."""
        with patch("fcp.routes.safety.check_food_recalls", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "food_item": "romaine",
                "recall_info": "No active recalls found",
                "has_active_recall": False,
                "sources": [],
            }

            response = client.get(
                "/safety/recalls",
                params={"food_name": "romaine"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["food_item"] == "romaine"
            mock.assert_called_once_with("romaine")

    def test_check_recalls_missing_food_name(self, client):
        """Test recall check without food_name parameter."""
        response = client.get("/safety/recalls", headers=AUTH_HEADER)
        assert response.status_code == 422

    def test_post_recalls_success(self, client):
        """Test POST recall check for CLI compatibility."""
        with patch("fcp.routes.safety.check_food_recalls", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "food_item": "chicken, eggs",
                "recall_info": "No active recalls found",
                "has_active_recall": False,
                "sources": [],
            }

            response = client.post(
                "/safety/recalls",
                json={"food_items": ["chicken", "eggs"]},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            mock.assert_called_once_with("chicken, eggs")


class TestAllergensEndpoint:
    """Tests for /safety/allergens endpoint."""

    def test_check_allergens_success(self, client):
        """Test successful allergen check."""
        with patch("fcp.routes.safety.check_allergen_alerts", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "food_item": "pad thai",
                "allergen_info": "Contains peanuts",
                "sources": [],
            }

            response = client.get(
                "/safety/allergens",
                params={"food_name": "pad thai", "allergens": "peanuts,shellfish"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            mock.assert_called_once_with("pad thai", ["peanuts", "shellfish"])

    def test_check_allergens_parses_comma_separated_list(self, client):
        """Test that allergens are parsed correctly."""
        with patch("fcp.routes.safety.check_allergen_alerts", new_callable=AsyncMock) as mock:
            mock.return_value = {}

            client.get(
                "/safety/allergens",
                params={"food_name": "dish", "allergens": "eggs, dairy , nuts"},
                headers=AUTH_HEADER,
            )

            # Should strip whitespace
            mock.assert_called_once_with("dish", ["eggs", "dairy", "nuts"])

    def test_post_allergens_success(self, client):
        """Test POST allergen check for CLI compatibility."""
        with patch("fcp.routes.safety.check_allergen_alerts", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "food_item": "peanut butter",
                "allergen_info": "Contains peanuts",
                "sources": [],
            }

            response = client.post(
                "/safety/allergens",
                json={"food_items": ["peanut butter"], "allergies": ["peanuts", "tree nuts"]},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            mock.assert_called_once_with("peanut butter", ["peanuts", "tree nuts"])


class TestRestaurantEndpoint:
    """Tests for /safety/restaurant/{restaurant_name} endpoint."""

    def test_get_restaurant_safety(self, client):
        """Test restaurant safety check."""
        with patch("fcp.routes.safety.get_restaurant_safety_info", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "restaurant": "Thai Palace",
                "safety_info": "A rating",
            }

            response = client.get(
                "/safety/restaurant/Thai Palace",
                params={"location": "Seattle"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            mock.assert_called_once_with("Thai Palace", "Seattle")

    def test_get_restaurant_safety_no_location(self, client):
        """Test restaurant check without location."""
        with patch("fcp.routes.safety.get_restaurant_safety_info", new_callable=AsyncMock) as mock:
            mock.return_value = {}

            response = client.get(
                "/safety/restaurant/Some Restaurant",
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            mock.assert_called_once_with("Some Restaurant", None)


class TestDrugInteractionsEndpoint:
    """Tests for /safety/drug-interactions endpoint."""

    def test_check_drug_interactions(self, client):
        """Test drug-food interaction check."""
        with patch("fcp.routes.safety.check_drug_food_interactions", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "food": "grapefruit",
                "interaction_info": "Avoid with statins",
            }

            response = client.get(
                "/safety/drug-interactions",
                params={"food_name": "grapefruit", "medications": "statin,warfarin"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            mock.assert_called_once_with("grapefruit", ["statin", "warfarin"])

    def test_post_drug_interactions_success(self, client):
        """Test POST drug-food interaction check for CLI compatibility."""
        with patch("fcp.routes.safety.check_drug_food_interactions", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "food": "grapefruit",
                "interaction_info": "Avoid with statins",
            }

            response = client.post(
                "/safety/drug-interactions",
                json={"food_items": ["grapefruit"], "medications": ["statin"]},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            mock.assert_called_once_with("grapefruit", ["statin"])


class TestSeasonalEndpoint:
    """Tests for /safety/seasonal endpoint."""

    def test_get_seasonal_safety(self, client):
        """Test seasonal safety tips."""
        with patch("fcp.routes.safety.get_seasonal_food_safety", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "location": "Seattle",
                "seasonal_tips": ["Store at cool temps"],
            }

            response = client.get(
                "/safety/seasonal",
                params={"location": "Seattle"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            mock.assert_called_once_with("Seattle")


class TestVerifyClaimEndpoint:
    """Tests for /safety/verify-claim endpoint."""

    def test_verify_claim_success(self, client):
        """Test nutrition claim verification."""
        with patch("fcp.routes.safety.verify_nutrition_claim", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "claim": "High in protein",
                "verification": "Supported",
            }

            response = client.post(
                "/safety/verify-claim",
                json={"claim": "High in protein", "food_name": "chicken"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            mock.assert_called_once_with("High in protein", "chicken")

    def test_verify_claim_invalid_request(self, client):
        """Test verification with missing fields."""
        response = client.post(
            "/safety/verify-claim",
            json={"claim": "Some claim"},  # Missing food_name
            headers=AUTH_HEADER,
        )
        assert response.status_code == 422


class TestRouterIntegration:
    """Tests for router integration."""

    def test_router_has_correct_prefix(self, client):
        """Test that routes use correct prefix."""
        # All endpoints should be under /safety
        with patch("fcp.routes.safety.check_food_recalls", new_callable=AsyncMock) as mock:
            mock.return_value = {}

            # Should work with /safety prefix
            response = client.get(
                "/safety/recalls",
                params={"food_name": "test"},
                headers=AUTH_HEADER,
            )
            assert response.status_code == 200

            # Should not work without prefix
            response = client.get(
                "/recalls",
                params={"food_name": "test"},
                headers=AUTH_HEADER,
            )
            assert response.status_code == 404
