"""Tests for FoodDiscoveryAgent."""

from unittest.mock import AsyncMock, patch

import pytest


class TestFoodDiscoveryAgentRunDiscovery:
    """Tests for run_discovery method."""

    @pytest.mark.asyncio
    async def test_run_discovery_success(self):
        """Test successful discovery run."""
        from fcp.agents.discovery import FoodDiscoveryAgent

        agent = FoodDiscoveryAgent("user123")

        with (
            patch("fcp.agents.discovery.gemini") as mock_gemini,
            patch("fcp.agents.discovery.build_discovery_prompt") as mock_build,
        ):
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {"recommendations": [{"name": "Ramen Shop", "type": "restaurant"}]},
                    "sources": [{"title": "Source", "url": "http://example.com"}],
                }
            )
            mock_build.return_value = "Test prompt"

            result = await agent.run_discovery(
                taste_profile={"favorite_cuisines": ["Japanese"]},
                location="Seattle",
                discovery_type="restaurant",
                count=5,
            )

            assert result["user_id"] == "user123"
            assert result["discovery_type"] == "restaurant"
            assert result["location"] == "Seattle"
            assert len(result["recommendations"]) == 1

    @pytest.mark.asyncio
    async def test_run_discovery_empty_recommendations(self):
        """Test discovery with no recommendations found."""
        from fcp.agents.discovery import FoodDiscoveryAgent

        agent = FoodDiscoveryAgent("user123")

        with (
            patch("fcp.agents.discovery.gemini") as mock_gemini,
            patch("fcp.agents.discovery.build_discovery_prompt") as mock_build,
        ):
            mock_gemini.generate_json_with_grounding = AsyncMock(return_value={"data": {}, "sources": []})
            mock_build.return_value = "Test prompt"

            result = await agent.run_discovery(
                taste_profile={},
                discovery_type="all",
                count=5,
            )

            assert result["recommendations"] == []

    @pytest.mark.asyncio
    async def test_run_discovery_non_dict_result(self):
        """Test discovery with non-dict result from gemini."""

        from fcp.agents.discovery import FoodDiscoveryAgent

        agent = FoodDiscoveryAgent("user123")

        with (
            patch("fcp.agents.discovery.gemini") as mock_gemini,
            patch("fcp.agents.discovery.build_discovery_prompt") as mock_build,
        ):
            mock_gemini.generate_json_with_grounding = AsyncMock(return_value="not a dict")

            mock_build.return_value = "Test prompt"

            result = await agent.run_discovery(
                taste_profile={},
                discovery_type="all",
                count=5,
            )

            assert result["recommendations"] == []


class TestFoodDiscoveryAgentDiscoverRestaurants:
    """Tests for discover_restaurants method."""

    @pytest.mark.asyncio
    async def test_discover_restaurants_success(self):
        """Test successful restaurant discovery."""

        from fcp.agents.discovery import FoodDiscoveryAgent

        agent = FoodDiscoveryAgent("user123")

        mock_data = {
            "restaurants": [
                {"name": "Taqueria", "type": "restaurant"},
                {"name": "Sushi Bar", "type": "restaurant"},
            ]
        }

        with (
            patch("fcp.agents.discovery.gemini") as mock_gemini,
            patch("fcp.agents.discovery.build_restaurant_discovery_prompt") as mock_build,
        ):
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={"data": mock_data, "sources": [{"title": "Source", "url": "http://example.com"}]}
            )

            mock_build.return_value = "Test prompt"

            result = await agent.discover_restaurants(
                taste_profile={"favorite_cuisines": ["Mexican"]},
                location="NYC",
                occasion="date night",
            )

            assert result["user_id"] == "user123"

            assert result["location"] == "NYC"

            assert result["occasion"] == "date night"

            assert len(result["restaurants"]) == 2

    @pytest.mark.asyncio
    async def test_discover_restaurants_no_occasion(self):
        """Test restaurant discovery without occasion."""

        from fcp.agents.discovery import FoodDiscoveryAgent

        agent = FoodDiscoveryAgent("user123")

        with (
            patch("fcp.agents.discovery.gemini") as mock_gemini,
            patch("fcp.agents.discovery.build_restaurant_discovery_prompt") as mock_build,
        ):
            mock_gemini.generate_json_with_grounding = AsyncMock(return_value={"data": {}, "sources": []})

            mock_build.return_value = "Test prompt"

            result = await agent.discover_restaurants(
                taste_profile={},
                location="LA",
                occasion=None,
            )

            assert result["occasion"] is None

    @pytest.mark.asyncio
    async def test_discover_restaurants_non_dict_result(self):
        """Test restaurant discovery with non-dict result."""

        from fcp.agents.discovery import FoodDiscoveryAgent

        agent = FoodDiscoveryAgent("user123")

        with (
            patch("fcp.agents.discovery.gemini") as mock_gemini,
            patch("fcp.agents.discovery.build_restaurant_discovery_prompt") as mock_build,
        ):
            mock_gemini.generate_json_with_grounding = AsyncMock(return_value=None)

            mock_build.return_value = "Test prompt"

            result = await agent.discover_restaurants(
                taste_profile={},
                location="LA",
            )

            assert result["restaurants"] == []


class TestFoodDiscoveryAgentDiscoverRecipes:
    """Tests for discover_recipes method."""

    @pytest.mark.asyncio
    async def test_discover_recipes_success(self):
        """Test successful recipe discovery."""

        from fcp.agents.discovery import FoodDiscoveryAgent

        agent = FoodDiscoveryAgent("user123")

        mock_data = {
            "recipes": [
                {"title": "Pasta Carbonara"},
            ]
        }

        with (
            patch("fcp.agents.discovery.gemini") as mock_gemini,
            patch("fcp.agents.discovery.build_recipe_discovery_prompt") as mock_build,
        ):
            mock_gemini.generate_json_with_grounding = AsyncMock(return_value={"data": mock_data, "sources": []})

            mock_build.return_value = "Test prompt"

            result = await agent.discover_recipes(
                taste_profile={"favorite_cuisines": ["Italian"]},
                available_ingredients=["eggs", "pasta", "bacon"],
                dietary_restrictions=["gluten-free"],
            )

            assert result["user_id"] == "user123"

            assert len(result["recipes"]) == 1

    @pytest.mark.asyncio
    async def test_discover_recipes_non_dict_result(self):
        """Test recipe discovery with non-dict result."""

        from fcp.agents.discovery import FoodDiscoveryAgent

        agent = FoodDiscoveryAgent("user123")

        with (
            patch("fcp.agents.discovery.gemini") as mock_gemini,
            patch("fcp.agents.discovery.build_recipe_discovery_prompt") as mock_build,
        ):
            mock_gemini.generate_json_with_grounding = AsyncMock(return_value=[])

            mock_build.return_value = "Test prompt"

            result = await agent.discover_recipes(
                taste_profile={},
            )

            assert result["recipes"] == []


class TestFoodDiscoveryAgentDiscoverSeasonal:
    """Tests for discover_seasonal method."""

    @pytest.mark.asyncio
    async def test_discover_seasonal_success(self):
        """Test successful seasonal discovery."""

        from fcp.agents.discovery import FoodDiscoveryAgent

        agent = FoodDiscoveryAgent("user123")

        mock_data = {
            "seasonal_discoveries": [
                {"item": "Pumpkin", "season": "fall"},
            ]
        }

        with (
            patch("fcp.agents.discovery.gemini") as mock_gemini,
            patch("fcp.agents.discovery.build_seasonal_discovery_prompt") as mock_build,
        ):
            mock_gemini.generate_json_with_grounding = AsyncMock(return_value={"data": mock_data, "sources": []})

            mock_build.return_value = "Test prompt"

            result = await agent.discover_seasonal(
                taste_profile={"favorite_cuisines": ["American"]},
                location="Seattle",
                current_month=10,  # October
            )

            assert result["user_id"] == "user123"

            assert result["location"] == "Seattle"

            assert result["month"] == "October"

            assert len(result["seasonal_discoveries"]) == 1

    @pytest.mark.asyncio
    async def test_discover_seasonal_all_months(self):
        """Test seasonal discovery for all months."""

        from fcp.agents.discovery import FoodDiscoveryAgent

        agent = FoodDiscoveryAgent("user123")

        month_names = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]

        with (
            patch("fcp.agents.discovery.gemini") as mock_gemini,
            patch("fcp.agents.discovery.build_seasonal_discovery_prompt") as mock_build,
        ):
            mock_gemini.generate_json_with_grounding = AsyncMock(return_value={"data": {}, "sources": []})

            mock_build.return_value = "Test prompt"

            for month_num in range(1, 13):
                result = await agent.discover_seasonal(
                    taste_profile={},
                    location="Test",
                    current_month=month_num,
                )

                assert result["month"] == month_names[month_num - 1]

    @pytest.mark.asyncio
    async def test_discover_seasonal_non_dict_result(self):
        """Test seasonal discovery with non-dict result."""

        from fcp.agents.discovery import FoodDiscoveryAgent

        agent = FoodDiscoveryAgent("user123")

        with (
            patch("fcp.agents.discovery.gemini") as mock_gemini,
            patch("fcp.agents.discovery.build_seasonal_discovery_prompt") as mock_build,
        ):
            mock_gemini.generate_json_with_grounding = AsyncMock(return_value=123)

            mock_build.return_value = "Test prompt"

            result = await agent.discover_seasonal(
                taste_profile={},
                location="Test",
                current_month=1,
            )

            assert result["seasonal_discoveries"] == []


class TestFoodDiscoveryAgentHelpers:
    """Tests for helper methods."""

    def test_extract_recommendations_edge_cases(self):
        """Test edge cases in _extract_recommendations."""
        from fcp.agents.discovery import FoodDiscoveryAgent

        agent = FoodDiscoveryAgent("user123")

        # Single result dict
        assert agent._extract_recommendations({"name": "Test"}) == [{"name": "Test"}]
        assert agent._extract_recommendations({"title": "Test"}) == [{"title": "Test"}]

        # Neither list nor dict
        assert agent._extract_recommendations(None) == []
        assert agent._extract_recommendations(123) == []

        # List with non-dict items
        assert agent._extract_recommendations([{"name": "A"}, "not a dict", {"name": "B"}]) == [
            {"name": "A"},
            {"name": "B"},
        ]

        # Item with non-dict details
        assert agent._extract_recommendations([{"name": "A", "details": "not a dict"}]) == [
            {"name": "A", "details": "not a dict"}
        ]

        # Item with valid details (flattening)
        # details should override top-level fields if they conflict
        result = agent._extract_recommendations([{"name": "A", "details": {"addr": "123", "name": "B"}}])
        assert result == [{"addr": "123", "name": "B", "details": {"addr": "123", "name": "B"}}]

    def test_get_type_focus_restaurant(self):
        """Test type focus for restaurant."""
        from fcp.agents.discovery import FoodDiscoveryAgent

        agent = FoodDiscoveryAgent("user123")
        assert agent._get_type_focus("restaurant") == "restaurant"

    def test_get_type_focus_recipe(self):
        """Test type focus for recipe."""
        from fcp.agents.discovery import FoodDiscoveryAgent

        agent = FoodDiscoveryAgent("user123")
        assert agent._get_type_focus("recipe") == "recipe"

    def test_get_type_focus_ingredient(self):
        """Test type focus for ingredient."""
        from fcp.agents.discovery import FoodDiscoveryAgent

        agent = FoodDiscoveryAgent("user123")
        assert agent._get_type_focus("ingredient") == "ingredient"

    def test_get_type_focus_all(self):
        """Test type focus for all types."""
        from fcp.agents.discovery import FoodDiscoveryAgent

        agent = FoodDiscoveryAgent("user123")
        assert agent._get_type_focus("all") == "restaurant, recipe, and ingredient"

    def test_get_type_focus_unknown(self):
        """Test type focus for unknown type."""
        from fcp.agents.discovery import FoodDiscoveryAgent

        agent = FoodDiscoveryAgent("user123")
        assert agent._get_type_focus("unknown") == "food"
