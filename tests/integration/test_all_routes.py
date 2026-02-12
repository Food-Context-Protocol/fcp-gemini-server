"""Integration tests for all API routes.

These tests verify that all routes are accessible with proper authentication.
They require Firebase emulators to be running.

Run with:
    firebase emulators:start --only firestore,auth &
    pytest tests/integration/test_all_routes.py -v
"""

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration, pytest.mark.firestore]


class TestHealthRoutes:
    """Tests for health check endpoints."""

    async def test_health_root(self, integration_client, auth_headers):
        response = await integration_client.get("/health/", headers=auth_headers)
        assert response.status_code == 200

    async def test_health_ready(self, integration_client, auth_headers):
        response = await integration_client.get("/health/ready", headers=auth_headers)
        assert response.status_code == 200

    async def test_health_live(self, integration_client, auth_headers):
        response = await integration_client.get("/health/live", headers=auth_headers)
        assert response.status_code == 200

    async def test_health_deps(self, integration_client, auth_headers):
        response = await integration_client.get("/health/deps", headers=auth_headers)
        assert response.status_code == 200


class TestMealRoutes:
    """Tests for meal CRUD endpoints."""

    async def test_list_meals(self, integration_client, auth_headers):
        response = await integration_client.get("/meals", headers=auth_headers)
        assert response.status_code == 200

    async def test_create_meal(self, integration_client, auth_headers):
        response = await integration_client.post(
            "/meals",
            headers=auth_headers,
            json={"dish_name": "Test Meal", "venue": "Test Kitchen"},
        )
        assert response.status_code in (200, 201)

    async def test_get_meal(self, integration_client, auth_headers):
        # First create a meal
        create_response = await integration_client.post(
            "/meals",
            headers=auth_headers,
            json={"dish_name": "Get Test Meal"},
        )
        if create_response.status_code in (200, 201):
            if log_id := create_response.json().get("log_id"):
                response = await integration_client.get(f"/meals/{log_id}", headers=auth_headers)
                assert response.status_code in (200, 404)


class TestAnalyzeRoutes:
    """Tests for analyze endpoints."""

    async def test_analyze_requires_auth_not_403(self, integration_client, auth_headers):
        """Test that analyze endpoint accepts authenticated requests (doesn't return 403)."""
        response = await integration_client.post(
            "/analyze",
            headers=auth_headers,
            json={"image_url": "https://example.com/test.jpg"},
        )
        # May fail due to invalid URL (422/500) but should not be 403 (forbidden)
        assert response.status_code != 403

    async def test_analyze_v2_requires_auth_not_403(self, integration_client, auth_headers):
        """Test that analyze/v2 endpoint accepts authenticated requests (doesn't return 403)."""
        response = await integration_client.post(
            "/analyze/v2",
            headers=auth_headers,
            json={"image_url": "https://example.com/test.jpg"},
        )
        # May fail due to invalid URL (422/500) but should not be 403 (forbidden)
        assert response.status_code != 403


class TestAgentRoutes:
    """Tests for agent endpoints."""

    async def test_daily_insight(self, integration_client, auth_headers):
        response = await integration_client.get("/agents/daily-insight", headers=auth_headers)
        assert response.status_code == 200

    async def test_food_tip(self, integration_client, auth_headers):
        response = await integration_client.get("/agents/food-tip", headers=auth_headers)
        assert response.status_code == 200

    async def test_monthly_review(self, integration_client, auth_headers):
        response = await integration_client.get("/agents/monthly-review", headers=auth_headers)
        assert response.status_code == 200

    async def test_seasonal_reminder(self, integration_client, auth_headers):
        response = await integration_client.get(
            "/agents/seasonal-reminder",
            headers=auth_headers,
            params={"location": "San Francisco"},
        )
        assert response.status_code == 200

    async def test_streak_celebration(self, integration_client, auth_headers):
        response = await integration_client.get("/agents/streak/7", headers=auth_headers)
        assert response.status_code == 200

    async def test_delegate_to_agent(self, integration_client, auth_headers):
        response = await integration_client.post(
            "/agents/delegate",
            headers=auth_headers,
            json={"agent_name": "discovery", "objective": "find restaurants"},
        )
        assert response.status_code != 403


class TestInventoryRoutes:
    """Tests for inventory/pantry endpoints."""

    async def test_get_pantry(self, integration_client, auth_headers):
        response = await integration_client.get("/inventory/pantry", headers=auth_headers)
        assert response.status_code == 200

    async def test_add_pantry_item(self, integration_client, auth_headers):
        response = await integration_client.post(
            "/inventory/pantry",
            headers=auth_headers,
            json={"items": ["Test Item", "Another Item"]},
        )
        # Should return 200 with added_ids, not 403 (forbidden) or 422 (validation error)
        assert response.status_code == 200

    async def test_get_suggestions(self, integration_client, auth_headers):
        response = await integration_client.get("/inventory/suggestions", headers=auth_headers)
        assert response.status_code == 200

    async def test_get_expiring(self, integration_client, auth_headers):
        response = await integration_client.get("/inventory/pantry/expiring", headers=auth_headers)
        assert response.status_code == 200


class TestAnalyticsRoutes:
    """Tests for analytics endpoints."""

    async def test_analytics_report(self, integration_client, auth_headers):
        response = await integration_client.get("/analytics/report", headers=auth_headers)
        assert response.status_code == 200

    async def test_nutrition_analytics(self, integration_client, auth_headers):
        response = await integration_client.post(
            "/analytics/nutrition",
            headers=auth_headers,
            json={"period": "week"},
        )
        assert response.status_code != 403


class TestProfileRoutes:
    """Tests for profile endpoints."""

    async def test_get_profile(self, integration_client, auth_headers):
        response = await integration_client.get("/profile", headers=auth_headers)
        assert response.status_code == 200

    async def test_get_lifetime_profile(self, integration_client, auth_headers):
        response = await integration_client.get("/profile/lifetime", headers=auth_headers)
        assert response.status_code == 200


class TestSafetyRoutes:
    """Tests for food safety endpoints."""

    async def test_allergen_alerts(self, integration_client, auth_headers):
        response = await integration_client.get(
            "/safety/allergens",
            headers=auth_headers,
            params={"food_name": "peanuts", "allergens": "nuts"},
        )
        assert response.status_code == 200

    async def test_drug_interactions(self, integration_client, auth_headers):
        response = await integration_client.get(
            "/safety/drug-interactions",
            headers=auth_headers,
            params={"food_name": "grapefruit", "medications": "statins"},
        )
        assert response.status_code == 200

    @pytest.mark.external
    async def test_food_recalls(self, integration_client, auth_headers):
        response = await integration_client.get(
            "/safety/recalls",
            headers=auth_headers,
            params={"food_name": "lettuce"},
        )
        assert response.status_code == 200


class TestRecipeRoutes:
    """Tests for recipe endpoints."""

    async def test_list_recipes(self, integration_client, auth_headers):
        response = await integration_client.get("/recipes", headers=auth_headers)
        assert response.status_code == 200

    async def test_generate_recipe(self, integration_client, auth_headers):
        response = await integration_client.post(
            "/recipes/generate",
            headers=auth_headers,
            json={"ingredients": ["chicken", "rice"]},
        )
        assert response.status_code != 403


class TestMiscRoutes:
    """Tests for miscellaneous endpoints."""

    async def test_suggest_meal(self, integration_client, auth_headers):
        response = await integration_client.post(
            "/suggest",
            headers=auth_headers,
            json={"context": "dinner"},
        )
        assert response.status_code == 200

    async def test_flavor_pairings(self, integration_client, auth_headers):
        response = await integration_client.get(
            "/flavor/pairings",
            headers=auth_headers,
            params={"subject": "chicken"},
        )
        assert response.status_code == 200

    async def test_trends(self, integration_client, auth_headers):
        response = await integration_client.get("/trends/identify", headers=auth_headers)
        assert response.status_code == 200

    async def test_clinical_report(self, integration_client, auth_headers):
        response = await integration_client.get("/clinical/report", headers=auth_headers)
        assert response.status_code == 200


class TestKnowledgeRoutes:
    """Tests for knowledge graph endpoints."""
    pytestmark = [pytest.mark.external]

    async def test_compare_foods(self, integration_client, auth_headers):
        response = await integration_client.get(
            "/knowledge/compare",
            headers=auth_headers,
            params={"food1": "apple", "food2": "banana"},
        )
        # External USDA availability varies by environment; verify auth path, not dataset guarantees.
        assert response.status_code != 403

    async def test_search_foods(self, integration_client, auth_headers):
        response = await integration_client.get(
            "/knowledge/search/chicken",
            headers=auth_headers,
        )
        # External USDA availability varies by environment; verify auth path, not dataset guarantees.
        assert response.status_code != 403


class TestExternalRoutes:
    """Tests for external data endpoints."""
    pytestmark = [pytest.mark.external]

    async def test_lookup_product(self, integration_client, auth_headers):
        response = await integration_client.get(
            "/external/lookup-product/012345678901",
            headers=auth_headers,
        )
        # May return 404 for unknown barcode, but not 403
        assert response.status_code != 403

    async def test_restaurant_info(self, integration_client, auth_headers):
        response = await integration_client.get(
            "/external/restaurant/test-restaurant",
            headers=auth_headers,
        )
        assert response.status_code != 403


class TestPublishRoutes:
    """Tests for content publishing endpoints."""

    async def test_list_drafts(self, integration_client, auth_headers):
        response = await integration_client.get("/publish/drafts", headers=auth_headers)
        assert response.status_code == 200

    async def test_list_published(self, integration_client, auth_headers):
        response = await integration_client.get("/publish/published", headers=auth_headers)
        assert response.status_code == 200

    async def test_generate_content(self, integration_client, auth_headers):
        response = await integration_client.post(
            "/publish/generate",
            headers=auth_headers,
            json={"content_type": "blog", "topic": "healthy eating"},
        )
        assert response.status_code != 403


class TestDiscoveryRoutes:
    """Tests for discovery endpoints."""

    @pytest.mark.external
    async def test_discover_nearby(self, integration_client, auth_headers):
        response = await integration_client.post(
            "/discovery/nearby",
            headers=auth_headers,
            json={"location": "San Francisco", "cuisine": "Italian"},
        )
        assert response.status_code != 403

    async def test_discover_recipes(self, integration_client, auth_headers):
        response = await integration_client.post(
            "/agents/discover/recipes",
            headers=auth_headers,
            json={"ingredients": ["tomato", "basil"]},
        )
        assert response.status_code != 403

    @pytest.mark.external
    async def test_discover_restaurants(self, integration_client, auth_headers):
        response = await integration_client.post(
            "/agents/discover/restaurants",
            headers=auth_headers,
            json={"location": "NYC", "cuisine": "Japanese"},
        )
        assert response.status_code != 403
