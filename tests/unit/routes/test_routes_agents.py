"""Tests for agents route endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from fcp.auth.permissions import AuthenticatedUser, UserRole
from tests.constants import TEST_AUTH_HEADER, TEST_USER_ID  # sourcery skip: dont-import-test-modules


@pytest.fixture
def client():
    """Create test client with mocked dependencies."""
    from fcp.api import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_auth():
    """Mock authentication to return test user."""
    from fcp.api import app
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


@pytest.fixture
def mock_rate_limit():
    """Mock rate limiter to allow requests."""
    with patch("fcp.routes.agents.limiter") as mock:
        mock.limit.return_value = lambda f: f
        yield mock


class TestDelegateAgentEndpoint:
    """Tests for /agents/delegate endpoint."""

    def test_delegate_to_agent_success(self, client, mock_auth):
        """Test successful agent delegation."""
        mock_result = {
            "agent": "visual_agent",
            "status": "completed",
            "result": {"concept": "Logo design"},
        }
        mock_context = {"preferences": {"cuisine": "Japanese"}}

        with (
            patch("fcp.services.firestore.get_firestore_client") as mock_db,
            patch(
                "fcp.routes.agents.delegate_to_food_agent",
                new_callable=AsyncMock,
            ) as mock_delegate,
        ):
            mock_db.return_value.get_user_preferences = AsyncMock(return_value=mock_context)
            mock_delegate.return_value = mock_result

            response = client.post(
                "/agents/delegate",
                json={"agent_name": "visual_agent", "objective": "Create a logo"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["agent"] == "visual_agent"
            assert data["status"] == "completed"

    def test_delegate_to_agent_requires_auth(self, client):
        """Test that delegation requires authentication."""
        response = client.post(
            "/agents/delegate",
            json={"agent_name": "visual_agent", "objective": "Test"},
        )
        assert response.status_code == 403  # Demo users get 403 for write endpoints


class TestFoodDiscoveryEndpoint:
    """Tests for /agents/discover endpoint."""

    def test_run_food_discovery_success(self, client, mock_auth):
        """Test successful food discovery."""
        mock_profile = {"favorite_cuisines": ["Japanese", "Italian"]}
        mock_result = {
            "recommendations": [
                {"name": "Ramen Shop", "type": "restaurant"},
                {"name": "Pasta Recipe", "type": "recipe"},
            ],
            "discovery_type": "all",
        }

        with (
            patch(
                "fcp.routes.agents.get_taste_profile",
                new_callable=AsyncMock,
            ) as mock_get_profile,
            patch("fcp.routes.agents.FoodDiscoveryAgent") as mock_agent_class,
        ):
            mock_get_profile.return_value = mock_profile
            mock_agent = MagicMock()
            mock_agent.run_discovery = AsyncMock(return_value=mock_result)
            mock_agent_class.return_value = mock_agent

            response = client.post(
                "/agents/discover",
                json={"location": "San Francisco", "discovery_type": "all", "count": 5},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert "recommendations" in data

    def test_run_food_discovery_requires_auth(self, client):
        """Test that food discovery requires authentication."""
        response = client.post(
            "/agents/discover",
            json={"discovery_type": "restaurant"},
        )
        assert response.status_code == 403  # Demo users get 403 for write endpoints


class TestRestaurantDiscoveryEndpoint:
    """Tests for /agents/discover/restaurants endpoint."""

    def test_discover_restaurants_success(self, client, mock_auth):
        """Test successful restaurant discovery."""
        mock_profile = {"favorite_cuisines": ["Thai"]}
        mock_result = {"restaurants": [{"name": "Thai Kitchen", "rating": 4.5}]}

        with (
            patch(
                "fcp.routes.agents.get_taste_profile",
                new_callable=AsyncMock,
            ) as mock_get_profile,
            patch("fcp.routes.agents.FoodDiscoveryAgent") as mock_agent_class,
        ):
            mock_get_profile.return_value = mock_profile
            mock_agent = MagicMock()
            mock_agent.discover_restaurants = AsyncMock(return_value=mock_result)
            mock_agent_class.return_value = mock_agent

            response = client.post(
                "/agents/discover/restaurants",
                json={"location": "New York", "occasion": "date night"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

    def test_discover_restaurants_requires_auth(self, client):
        """Test that restaurant discovery requires authentication."""
        response = client.post(
            "/agents/discover/restaurants",
            json={"location": "New York"},
        )
        assert response.status_code == 403  # Demo users get 403 for write endpoints


class TestRecipeDiscoveryEndpoint:
    """Tests for /agents/discover/recipes endpoint."""

    def test_discover_recipes_success(self, client, mock_auth):
        """Test successful recipe discovery."""
        mock_profile = {"dietary_preferences": ["vegetarian"]}
        mock_result = {"recipes": [{"name": "Veggie Stir Fry"}]}

        with (
            patch(
                "fcp.routes.agents.get_taste_profile",
                new_callable=AsyncMock,
            ) as mock_get_profile,
            patch("fcp.routes.agents.FoodDiscoveryAgent") as mock_agent_class,
        ):
            mock_get_profile.return_value = mock_profile
            mock_agent = MagicMock()
            mock_agent.discover_recipes = AsyncMock(return_value=mock_result)
            mock_agent_class.return_value = mock_agent

            response = client.post(
                "/agents/discover/recipes",
                json={"available_ingredients": ["tofu", "broccoli"]},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

    def test_discover_recipes_requires_auth(self, client):
        """Test that recipe discovery requires authentication."""
        response = client.post(
            "/agents/discover/recipes",
            json={},
        )
        assert response.status_code == 403  # Demo users get 403 for write endpoints


class TestDailyInsightEndpoint:
    """Tests for /agents/daily-insight endpoint."""

    def test_get_daily_insight_success(self, client, mock_auth):
        """Test successful daily insight generation."""
        mock_profile = {"preferences": {}}
        mock_logs = [{"dish_name": "Salad"}]
        mock_result = {"insight": "Today is a great day for soup!"}

        with (
            patch(
                "fcp.routes.agents.get_taste_profile",
                new_callable=AsyncMock,
            ) as mock_get_profile,
            patch(
                "fcp.routes.agents.get_meals",
                new_callable=AsyncMock,
            ) as mock_get_meals,
            patch("fcp.routes.agents.FreshnessAgent") as mock_agent_class,
        ):
            mock_get_profile.return_value = mock_profile
            mock_get_meals.return_value = mock_logs
            mock_agent = MagicMock()
            mock_agent.generate_daily_insight = AsyncMock(return_value=mock_result)
            mock_agent_class.return_value = mock_agent

            response = client.get(
                "/agents/daily-insight?location=Seattle",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert "insight" in data

    def test_get_daily_insight_allows_demo_user(self, client, mock_auth):
        """Test that daily insight allows demo users (read endpoint)."""
        with (
            patch("fcp.routes.agents.get_taste_profile", new_callable=AsyncMock) as mock_profile,
            patch("fcp.routes.agents.get_meals", new_callable=AsyncMock) as mock_meals,
            patch("fcp.routes.agents.FreshnessAgent") as mock_agent_class,
        ):
            mock_profile.return_value = {}
            mock_meals.return_value = []
            mock_agent = MagicMock()
            mock_agent.generate_daily_insight = AsyncMock(return_value={"insight": "test"})
            mock_agent_class.return_value = mock_agent
            response = client.get("/agents/daily-insight")
            # Demo users can access read endpoints
            assert response.status_code == 200


class TestStreakCelebrationEndpoint:
    """Tests for /agents/streak/{streak_days} endpoint."""

    def test_get_streak_celebration_success(self, client, mock_auth):
        """Test successful streak celebration."""
        mock_result = {"message": "Amazing! 7 day streak!", "celebration_type": "milestone"}

        with patch("fcp.routes.agents.FreshnessAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.generate_streak_celebration = AsyncMock(return_value=mock_result)
            mock_agent_class.return_value = mock_agent

            response = client.get(
                "/agents/streak/7?user_name=John",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert "message" in data

    def test_get_streak_celebration_allows_demo_user(self, client, mock_auth):
        """Test that streak celebration allows demo users (read endpoint)."""
        with patch("fcp.routes.agents.FreshnessAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.generate_streak_celebration = AsyncMock(return_value={"message": "Great streak!"})
            mock_agent_class.return_value = mock_agent
            response = client.get("/agents/streak/7")
            # Demo users can access read endpoints
            assert response.status_code == 200


class TestFoodTipEndpoint:
    """Tests for /agents/food-tip endpoint."""

    def test_get_food_tip_success(self, client, mock_auth):
        """Test successful food tip generation."""
        mock_profile = {"preferences": {}}
        mock_result = {"tip": "Try adding lemon to your water!"}

        with (
            patch(
                "fcp.routes.agents.get_taste_profile",
                new_callable=AsyncMock,
            ) as mock_get_profile,
            patch("fcp.routes.agents.FreshnessAgent") as mock_agent_class,
        ):
            mock_get_profile.return_value = mock_profile
            mock_agent = MagicMock()
            mock_agent.generate_food_tip_of_day = AsyncMock(return_value=mock_result)
            mock_agent_class.return_value = mock_agent

            response = client.get(
                "/agents/food-tip",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

    def test_get_food_tip_allows_demo_user(self, client, mock_auth):
        """Test that food tip allows demo users (read endpoint)."""
        with (
            patch("fcp.routes.agents.get_taste_profile", new_callable=AsyncMock) as mock_profile,
            patch("fcp.routes.agents.FreshnessAgent") as mock_agent_class,
        ):
            mock_profile.return_value = {}
            mock_agent = MagicMock()
            mock_agent.generate_food_tip_of_day = AsyncMock(return_value={"tip": "test tip", "category": "nutrition"})
            mock_agent_class.return_value = mock_agent
            response = client.get("/agents/food-tip")
            # Demo users can access read endpoints
            assert response.status_code == 200


class TestSeasonalReminderEndpoint:
    """Tests for /agents/seasonal-reminder endpoint."""

    def test_get_seasonal_reminder_success(self, client, mock_auth):
        """Test successful seasonal reminder generation."""
        mock_profile = {"preferences": {}}
        mock_result = {"reminder": "Pumpkins are in season!", "season": "fall"}

        with (
            patch(
                "fcp.routes.agents.get_taste_profile",
                new_callable=AsyncMock,
            ) as mock_get_profile,
            patch("fcp.routes.agents.FreshnessAgent") as mock_agent_class,
        ):
            mock_get_profile.return_value = mock_profile
            mock_agent = MagicMock()
            mock_agent.generate_seasonal_reminder = AsyncMock(return_value=mock_result)
            mock_agent_class.return_value = mock_agent

            response = client.get(
                "/agents/seasonal-reminder?location=Portland",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

    def test_get_seasonal_reminder_allows_demo_user(self, client, mock_auth):
        """Test that seasonal reminder allows demo users (read endpoint)."""
        with (
            patch("fcp.routes.agents.get_taste_profile", new_callable=AsyncMock, return_value={}),
            patch("fcp.routes.agents.FreshnessAgent") as mock_agent_class,
        ):
            mock_agent = MagicMock()
            mock_agent.generate_seasonal_reminder = AsyncMock(return_value={"reminder": "Try seasonal produce!"})
            mock_agent_class.return_value = mock_agent
            response = client.get("/agents/seasonal-reminder?location=Portland")
            # Demo users can access read endpoints
            assert response.status_code == 200


class TestProcessMediaBatchEndpoint:
    """Tests for /agents/process-media endpoint."""

    def test_process_media_batch_success(self, client, mock_auth):
        """Test successful media batch processing."""
        mock_result = {
            "processed": 2,
            "results": [
                {"url": "http://example.com/img1.jpg", "is_food": True},
                {"url": "http://example.com/img2.jpg", "is_food": False},
            ],
        }

        with patch("fcp.routes.agents.MediaProcessingAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.process_photo_batch = AsyncMock(return_value=mock_result)
            mock_agent_class.return_value = mock_agent

            response = client.post(
                "/agents/process-media",
                json={
                    "image_urls": ["http://example.com/img1.jpg", "http://example.com/img2.jpg"],
                    "auto_log": False,
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["processed"] == 2

    def test_process_media_batch_requires_auth(self, client):
        """Test that media processing requires authentication."""
        response = client.post(
            "/agents/process-media",
            json={"image_urls": ["http://example.com/img.jpg"]},
        )
        assert response.status_code == 403  # Demo users get 403 for write endpoints


class TestFilterFoodImagesEndpoint:
    """Tests for /agents/filter-food-images endpoint."""

    def test_filter_food_images_success(self, client, mock_auth):
        """Test successful food image filtering."""
        mock_result = {
            "food_images": ["http://example.com/food.jpg"],
            "non_food_images": ["http://example.com/cat.jpg"],
        }

        with patch("fcp.routes.agents.MediaProcessingAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.filter_food_images = AsyncMock(return_value=mock_result)
            mock_agent_class.return_value = mock_agent

            response = client.post(
                "/agents/filter-food-images",
                json={
                    "image_urls": ["http://example.com/food.jpg", "http://example.com/cat.jpg"],
                    "confidence_threshold": 0.8,
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

    def test_filter_food_images_requires_auth(self, client):
        """Test that image filtering requires authentication."""
        response = client.post(
            "/agents/filter-food-images",
            json={"image_urls": ["http://example.com/img.jpg"]},
        )
        assert response.status_code == 403  # Demo users get 403 for write endpoints

    def test_filter_food_photos_backwards_compatible(self, client, mock_auth):
        """Test old /agents/filter-food-photos endpoint still works."""
        mock_result = {
            "food_images": ["http://example.com/food.jpg"],
            "non_food_images": ["http://example.com/cat.jpg"],
        }

        with patch("fcp.routes.agents.MediaProcessingAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.filter_food_images = AsyncMock(return_value=mock_result)
            mock_agent_class.return_value = mock_agent

            response = client.post(
                "/agents/filter-food-photos",
                json={
                    "image_urls": ["http://example.com/food.jpg", "http://example.com/cat.jpg"],
                    "confidence_threshold": 0.8,
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200


class TestGenerateBlogEndpoint:
    """Tests for /agents/generate-blog endpoint."""

    def test_generate_blog_success(self, client, mock_auth):
        """Test successful blog generation."""
        mock_logs = [{"dish_name": "Pizza"}, {"dish_name": "Ramen"}]
        mock_result = {"title": "My Food Week", "content": "# Great meals!"}

        with (
            patch(
                "fcp.routes.agents.get_meals",
                new_callable=AsyncMock,
            ) as mock_get_meals,
            patch("fcp.routes.agents.ContentGeneratorAgent") as mock_agent_class,
        ):
            mock_get_meals.return_value = mock_logs
            mock_agent = MagicMock()
            mock_agent.generate_weekly_digest = AsyncMock(return_value=mock_result)
            mock_agent_class.return_value = mock_agent

            response = client.post(
                "/agents/generate-blog?user_name=Chef",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

    def test_generate_blog_requires_auth(self, client):
        """Test that blog generation requires authentication."""
        response = client.post("/agents/generate-blog")
        assert response.status_code == 403  # Demo users get 403 for write endpoints


class TestSocialPostEndpoint:
    """Tests for /agents/social-post endpoint."""

    def test_create_social_post_success(self, client, mock_auth):
        """Test successful social post creation."""
        mock_meal = {"id": "log123", "dish_name": "Tacos"}
        mock_result = {"content": "Best tacos ever! #foodie", "hashtags": ["#foodie"]}

        with (
            patch(
                "fcp.routes.agents.get_meal",
                new_callable=AsyncMock,
            ) as mock_get_meal,
            patch("fcp.routes.agents.ContentGeneratorAgent") as mock_agent_class,
        ):
            mock_get_meal.return_value = mock_meal
            mock_agent = MagicMock()
            mock_agent.generate_social_post = AsyncMock(return_value=mock_result)
            mock_agent_class.return_value = mock_agent

            response = client.post(
                "/agents/social-post",
                json={"log_id": "log123", "platform": "instagram", "style": "casual"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

    def test_create_social_post_meal_not_found(self, client, mock_auth):
        """Test social post when meal is not found."""
        with patch(
            "fcp.routes.agents.get_meal",
            new_callable=AsyncMock,
        ) as mock_get_meal:
            mock_get_meal.return_value = None

            response = client.post(
                "/agents/social-post",
                json={"log_id": "nonexistent"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 404

    def test_create_social_post_requires_auth(self, client):
        """Test that social post requires authentication."""
        response = client.post(
            "/agents/social-post",
            json={"log_id": "log123"},
        )
        assert response.status_code == 403  # Demo users get 403 for write endpoints


class TestFoodStoryEndpoint:
    """Tests for /agents/food-story endpoint."""

    def test_generate_food_story_success(self, client, mock_auth):
        """Test successful food story generation."""
        mock_meals = [
            {"id": "log1", "dish_name": "Breakfast"},
            {"id": "log2", "dish_name": "Lunch"},
        ]
        mock_result = {"story": "It was a day of great meals..."}

        with (
            patch(
                "fcp.routes.agents.get_meal",
                new_callable=AsyncMock,
            ) as mock_get_meal,
            patch("fcp.routes.agents.ContentGeneratorAgent") as mock_agent_class,
        ):
            mock_get_meal.side_effect = mock_meals
            mock_agent = MagicMock()
            mock_agent.generate_food_story = AsyncMock(return_value=mock_result)
            mock_agent_class.return_value = mock_agent

            response = client.post(
                "/agents/food-story",
                json={"log_ids": ["log1", "log2"], "theme": "adventure"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

    def test_generate_food_story_no_meals_found(self, client, mock_auth):
        """Test food story when no meals are found."""
        with patch(
            "fcp.routes.agents.get_meal",
            new_callable=AsyncMock,
        ) as mock_get_meal:
            mock_get_meal.return_value = None

            response = client.post(
                "/agents/food-story",
                json={"log_ids": ["log1"]},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 404

    def test_generate_food_story_requires_auth(self, client):
        """Test that food story requires authentication."""
        response = client.post(
            "/agents/food-story",
            json={"log_ids": ["log1"]},
        )
        assert response.status_code == 403  # Demo users get 403 for write endpoints


class TestMonthlyReviewEndpoint:
    """Tests for /agents/monthly-review endpoint."""

    def test_generate_monthly_review_success(self, client, mock_auth):
        """Test successful monthly review generation."""
        mock_logs = [{"dish_name": "Pizza"} for _ in range(10)]
        mock_profile = {"preferences": {}}
        mock_result = {"summary": "A month of great food!", "highlights": []}

        with (
            patch(
                "fcp.routes.agents.get_meals",
                new_callable=AsyncMock,
            ) as mock_get_meals,
            patch(
                "fcp.routes.agents.get_taste_profile",
                new_callable=AsyncMock,
            ) as mock_get_profile,
            patch("fcp.routes.agents.ContentGeneratorAgent") as mock_agent_class,
        ):
            mock_get_meals.return_value = mock_logs
            mock_get_profile.return_value = mock_profile
            mock_agent = MagicMock()
            mock_agent.generate_monthly_review = AsyncMock(return_value=mock_result)
            mock_agent_class.return_value = mock_agent

            response = client.get(
                "/agents/monthly-review",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

    def test_generate_monthly_review_allows_demo_user(self, client, mock_auth):
        """Test that monthly review allows demo users (read endpoint)."""
        with (
            patch("fcp.routes.agents.get_taste_profile", new_callable=AsyncMock, return_value={}),
            patch("fcp.routes.agents.get_meals", new_callable=AsyncMock) as mock_meals,
            patch("fcp.routes.agents.ContentGeneratorAgent") as mock_agent_class,
        ):
            mock_meals.return_value = []
            mock_agent = MagicMock()
            mock_agent.generate_monthly_review = AsyncMock(return_value={"review": "Great month!"})
            mock_agent_class.return_value = mock_agent
            response = client.get("/agents/monthly-review")
            # Demo users can access read endpoints
            assert response.status_code == 200


class TestRecipeCardEndpoint:
    """Tests for /agents/recipe-card endpoint."""

    def test_generate_recipe_card_success(self, client, mock_auth):
        """Test successful recipe card generation."""
        mock_meal = {"id": "log123", "dish_name": "Pasta", "ingredients": ["pasta", "sauce"]}
        mock_result = {"title": "Pasta", "card_html": "<div>Recipe</div>"}

        with (
            patch(
                "fcp.routes.agents.get_meal",
                new_callable=AsyncMock,
            ) as mock_get_meal,
            patch("fcp.routes.agents.ContentGeneratorAgent") as mock_agent_class,
        ):
            mock_get_meal.return_value = mock_meal
            mock_agent = MagicMock()
            mock_agent.generate_recipe_card = AsyncMock(return_value=mock_result)
            mock_agent_class.return_value = mock_agent

            response = client.post(
                "/agents/recipe-card",
                json={"log_id": "log123", "include_instructions": True},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

    def test_generate_recipe_card_meal_not_found(self, client, mock_auth):
        """Test recipe card when meal is not found."""
        with patch(
            "fcp.routes.agents.get_meal",
            new_callable=AsyncMock,
        ) as mock_get_meal:
            mock_get_meal.return_value = None

            response = client.post(
                "/agents/recipe-card",
                json={"log_id": "nonexistent"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 404

    def test_generate_recipe_card_requires_auth(self, client):
        """Test that recipe card requires authentication."""
        response = client.post(
            "/agents/recipe-card",
            json={"log_id": "log123"},
        )
        assert response.status_code == 403  # Demo users get 403 for write endpoints
