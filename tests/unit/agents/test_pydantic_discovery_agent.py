"""Tests for Pydantic AI-based Food Discovery Agent."""

from unittest.mock import AsyncMock, patch

import pytest

from fcp.agents.pydantic_agents.discovery import (
    DiscoveryRequest,
    DiscoveryResult,
    GroundingSource,
    PydanticDiscoveryAgent,
    RecipeDiscoveryRequest,
    RecipeResult,
    Recommendation,
    RestaurantDiscoveryRequest,
    RestaurantResult,
    SeasonalDiscoveryRequest,
    SeasonalResult,
    TasteProfile,
)


class TestTasteProfileModel:
    """Tests for TasteProfile Pydantic model."""

    def test_taste_profile_defaults(self):
        """Should have sensible defaults."""
        profile = TasteProfile()
        assert profile.top_cuisines == []
        assert profile.spice_preference == "medium"
        assert profile.dietary_restrictions == []

    def test_taste_profile_with_values(self):
        """Should accept provided values."""
        profile = TasteProfile(
            top_cuisines=["Italian", "Japanese"],
            spice_preference="high",
            dietary_restrictions=["vegetarian"],
            favorite_dishes=["Ramen", "Pizza"],
        )
        assert profile.top_cuisines == ["Italian", "Japanese"]
        assert profile.spice_preference == "high"

    def test_taste_profile_to_dict(self):
        """Should convert to dictionary."""
        profile = TasteProfile(top_cuisines=["Thai"])
        d = profile.to_dict()
        assert d["top_cuisines"] == ["Thai"]
        assert "spice_preference" in d


class TestRecommendationModel:
    """Tests for Recommendation Pydantic model."""

    def test_recommendation_minimal(self):
        """Should work with minimal data."""
        rec = Recommendation(name="Test Restaurant")
        assert rec.name == "Test Restaurant"
        assert rec.reason == ""
        assert rec.match_score == 0.0

    def test_recommendation_full(self):
        """Should accept all fields."""
        rec = Recommendation(
            name="Sushi Place",
            reason="Matches your preference for Japanese",
            match_score=0.95,
            cuisine="Japanese",
            price_range="$$",
            address="123 Main St",
            highlights=["Fresh fish", "Great service"],
        )
        assert rec.name == "Sushi Place"
        assert rec.match_score == 0.95
        assert len(rec.highlights) == 2

    def test_recommendation_allows_extra_fields(self):
        """Should allow extra fields from API response."""
        # Extra fields allowed via model_config extra="allow"
        data = {"name": "Test", "extra_field": "value"}
        rec = Recommendation.model_validate(data)
        assert rec.name == "Test"
        assert rec.extra_field == "value"  # type: ignore[attr-defined]


class TestGroundingSourceModel:
    """Tests for GroundingSource Pydantic model."""

    def test_grounding_source(self):
        """Should store source information."""
        source = GroundingSource(uri="https://example.com", title="Example Site")
        assert source.uri == "https://example.com"
        assert source.title == "Example Site"


class TestDiscoveryRequestModel:
    """Tests for DiscoveryRequest Pydantic model."""

    def test_discovery_request_defaults(self):
        """Should have sensible defaults."""
        request = DiscoveryRequest(taste_profile=TasteProfile())
        assert request.location is None
        assert request.discovery_type == "all"
        assert request.count == 5

    def test_discovery_request_count_validation(self):
        """Should validate count range."""
        # Valid range
        request = DiscoveryRequest(taste_profile=TasteProfile(), count=10)
        assert request.count == 10

        # Invalid count should raise
        with pytest.raises(ValueError):
            DiscoveryRequest(taste_profile=TasteProfile(), count=0)

        with pytest.raises(ValueError):
            DiscoveryRequest(taste_profile=TasteProfile(), count=25)


class TestPydanticDiscoveryAgent:
    """Tests for PydanticDiscoveryAgent."""

    @pytest.fixture
    def agent(self):
        """Create agent instance."""
        return PydanticDiscoveryAgent(user_id="test_user")

    @pytest.fixture
    def mock_gemini_response(self):
        """Create mock Gemini response."""
        return {
            "data": {
                "recommendations": [
                    {
                        "name": "Italian Bistro",
                        "reason": "Great pasta",
                        "match_score": 0.9,
                        "cuisine": "Italian",
                    },
                    {
                        "name": "Sushi Bar",
                        "reason": "Fresh sushi",
                        "match_score": 0.85,
                        "cuisine": "Japanese",
                    },
                ]
            },
            "sources": [
                {"uri": "https://example.com", "title": "Example"},
            ],
        }

    @pytest.mark.asyncio
    async def test_discover_success(self, agent, mock_gemini_response):
        """Should return typed DiscoveryResult."""
        with patch.object(
            agent,
            "_extract_recommendations",
            return_value=mock_gemini_response["data"]["recommendations"],
        ):
            with patch(
                "fcp.agents.pydantic_agents.discovery.gemini.generate_json_with_grounding",
                new_callable=AsyncMock,
                return_value=mock_gemini_response,
            ):
                request = DiscoveryRequest(
                    taste_profile=TasteProfile(top_cuisines=["Italian"]),
                    location="San Francisco",
                    discovery_type="restaurant",
                    count=5,
                )

                result = await agent.discover(request)

                assert isinstance(result, DiscoveryResult)
                assert result.user_id == "test_user"
                assert result.discovery_type == "restaurant"
                assert result.location == "San Francisco"
                assert len(result.recommendations) == 2
                assert result.recommendations[0].name == "Italian Bistro"
                assert len(result.sources) == 1

    @pytest.mark.asyncio
    async def test_discover_empty_response(self, agent):
        """Should handle empty/invalid response."""
        with patch(
            "fcp.agents.pydantic_agents.discovery.gemini.generate_json_with_grounding",
            new_callable=AsyncMock,
            return_value="invalid",
        ):
            request = DiscoveryRequest(
                taste_profile=TasteProfile(),
                discovery_type="all",
            )

            result = await agent.discover(request)

            assert isinstance(result, DiscoveryResult)
            assert result.recommendations == []
            assert result.sources == []

    @pytest.mark.asyncio
    async def test_discover_restaurants_typed(self, agent, mock_gemini_response):
        """Should discover restaurants with typed response."""
        with patch(
            "fcp.agents.pydantic_agents.discovery.gemini.generate_json_with_grounding",
            new_callable=AsyncMock,
            return_value=mock_gemini_response,
        ):
            request = RestaurantDiscoveryRequest(
                taste_profile=TasteProfile(top_cuisines=["Italian"]),
                location="New York",
                occasion="date night",
            )

            result = await agent.discover_restaurants_typed(request)

            assert isinstance(result, RestaurantResult)
            assert result.user_id == "test_user"
            assert result.location == "New York"
            assert result.occasion == "date night"
            assert len(result.restaurants) == 2

    @pytest.mark.asyncio
    async def test_discover_recipes_typed(self, agent, mock_gemini_response):
        """Should discover recipes with typed response."""
        with patch(
            "fcp.agents.pydantic_agents.discovery.gemini.generate_json_with_grounding",
            new_callable=AsyncMock,
            return_value=mock_gemini_response,
        ):
            request = RecipeDiscoveryRequest(
                taste_profile=TasteProfile(top_cuisines=["Mexican"]),
                available_ingredients=["chicken", "rice"],
                dietary_restrictions=["gluten-free"],
            )

            result = await agent.discover_recipes_typed(request)

            assert isinstance(result, RecipeResult)
            assert result.user_id == "test_user"
            assert len(result.recipes) == 2

    @pytest.mark.asyncio
    async def test_discover_seasonal_typed(self, agent, mock_gemini_response):
        """Should discover seasonal foods with typed response."""
        with patch(
            "fcp.agents.pydantic_agents.discovery.gemini.generate_json_with_grounding",
            new_callable=AsyncMock,
            return_value=mock_gemini_response,
        ):
            request = SeasonalDiscoveryRequest(
                taste_profile=TasteProfile(),
                location="Portland",
                current_month=6,
            )

            result = await agent.discover_seasonal_typed(request)

            assert isinstance(result, SeasonalResult)
            assert result.user_id == "test_user"
            assert result.location == "Portland"
            assert result.month == "June"
            assert len(result.seasonal_discoveries) == 2

    @pytest.mark.asyncio
    async def test_backward_compatible_run_discovery(self, agent, mock_gemini_response):
        """Should work with dict interface for backward compatibility."""
        with patch(
            "fcp.agents.pydantic_agents.discovery.gemini.generate_json_with_grounding",
            new_callable=AsyncMock,
            return_value=mock_gemini_response,
        ):
            result = await agent.run_discovery(
                taste_profile={"top_cuisines": ["Thai"]},
                location="Seattle",
                discovery_type="all",
                count=5,
            )

            assert isinstance(result, dict)
            assert result["user_id"] == "test_user"
            assert result["discovery_type"] == "all"
            assert "recommendations" in result

    @pytest.mark.asyncio
    async def test_backward_compatible_discover_restaurants(self, agent, mock_gemini_response):
        """Should work with dict interface for restaurants."""
        with patch(
            "fcp.agents.pydantic_agents.discovery.gemini.generate_json_with_grounding",
            new_callable=AsyncMock,
            return_value=mock_gemini_response,
        ):
            result = await agent.discover_restaurants(
                taste_profile={"top_cuisines": ["Italian"]},
                location="Chicago",
                occasion="business lunch",
            )

            assert isinstance(result, dict)
            assert result["location"] == "Chicago"
            assert "restaurants" in result

    @pytest.mark.asyncio
    async def test_backward_compatible_discover_recipes(self, agent, mock_gemini_response):
        """Should work with dict interface for recipes."""
        with patch(
            "fcp.agents.pydantic_agents.discovery.gemini.generate_json_with_grounding",
            new_callable=AsyncMock,
            return_value=mock_gemini_response,
        ):
            result = await agent.discover_recipes(
                taste_profile={"top_cuisines": ["Japanese"]},
                available_ingredients=["tofu", "miso"],
            )

            assert isinstance(result, dict)
            assert "recipes" in result

    @pytest.mark.asyncio
    async def test_backward_compatible_discover_seasonal(self, agent, mock_gemini_response):
        """Should work with dict interface for seasonal."""
        with patch(
            "fcp.agents.pydantic_agents.discovery.gemini.generate_json_with_grounding",
            new_callable=AsyncMock,
            return_value=mock_gemini_response,
        ):
            result = await agent.discover_seasonal(
                taste_profile={"top_cuisines": ["French"]},
                location="Paris",
                current_month=10,
            )

            assert isinstance(result, dict)
            assert result["month"] == "October"
            assert "seasonal_discoveries" in result


class TestExtractRecommendations:
    """Tests for recommendation extraction logic."""

    @pytest.fixture
    def agent(self):
        return PydanticDiscoveryAgent(user_id="test")

    def test_extract_from_list(self, agent):
        """Should extract from top-level list."""
        data = [{"name": "A"}, {"name": "B"}]
        result = agent._extract_recommendations(data)
        assert len(result) == 2

    def test_extract_from_recommendations_key(self, agent):
        """Should extract from 'recommendations' key."""
        data = {"recommendations": [{"name": "A"}]}
        result = agent._extract_recommendations(data)
        assert len(result) == 1

    def test_extract_from_restaurants_key(self, agent):
        """Should extract from 'restaurants' key."""
        data = {"restaurants": [{"name": "A"}]}
        result = agent._extract_recommendations(data)
        assert len(result) == 1

    def test_extract_from_recipes_key(self, agent):
        """Should extract from 'recipes' key."""
        data = {"recipes": [{"name": "A"}]}
        result = agent._extract_recommendations(data)
        assert len(result) == 1

    def test_extract_single_item(self, agent):
        """Should handle single item without list."""
        data = {"name": "Single Item"}
        result = agent._extract_recommendations(data)
        assert len(result) == 1
        assert result[0]["name"] == "Single Item"

    def test_flatten_details(self, agent):
        """Should flatten nested 'details' field."""
        data = [
            {
                "name": "Restaurant",
                "details": {"cuisine": "Italian", "price": "$$"},
            }
        ]
        result = agent._extract_recommendations(data)
        assert result[0]["name"] == "Restaurant"
        assert result[0]["cuisine"] == "Italian"
        assert result[0]["price"] == "$$"

    def test_skip_non_dict_items(self, agent):
        """Should skip non-dict items in list."""
        data = [{"name": "Valid"}, "invalid", 123, None]
        result = agent._extract_recommendations(data)
        assert len(result) == 1

    def test_extract_empty_dict_without_known_keys(self, agent):
        """Should return empty list for dict without known keys or name/title."""
        data = {"unknown_key": [{"value": 1}], "other": "stuff"}
        result = agent._extract_recommendations(data)
        assert len(result) == 0


class TestParseRecommendations:
    """Tests for recommendation parsing logic."""

    @pytest.fixture
    def agent(self):
        return PydanticDiscoveryAgent(user_id="test")

    def test_parse_standard_fields(self, agent):
        """Should parse standard field names."""
        raw = [{"name": "Test", "reason": "Good", "match_score": 0.9}]
        result = agent._parse_recommendations(raw)
        assert len(result) == 1
        assert result[0].name == "Test"
        assert result[0].reason == "Good"
        assert result[0].match_score == 0.9

    def test_parse_alternative_field_names(self, agent):
        """Should handle alternative field names."""
        raw = [{"title": "Test", "why": "Because", "score": 0.8}]
        result = agent._parse_recommendations(raw)
        assert result[0].name == "Test"
        assert result[0].reason == "Because"
        assert result[0].match_score == 0.8

    def test_parse_missing_fields(self, agent):
        """Should handle missing fields gracefully."""
        raw = [{"name": "Only Name"}]
        result = agent._parse_recommendations(raw)
        assert result[0].name == "Only Name"
        assert result[0].reason == ""
        assert result[0].match_score == 0.0

    def test_parse_includes_extra_fields(self, agent):
        """Should preserve extra fields."""
        raw = [{"name": "Test", "custom_field": "custom_value"}]
        result = agent._parse_recommendations(raw)
        assert result[0].custom_field == "custom_value"

    def test_parse_handles_invalid_match_score(self, agent):
        """Should handle items that cause parsing errors gracefully."""
        # Create an item that will cause an error during parsing
        # match_score that can't be converted to float
        raw = [{"name": "Test", "match_score": "not_a_number"}]
        result = agent._parse_recommendations(raw)
        # Should still return a recommendation with minimal data
        assert len(result) == 1
        assert result[0].name == "Test"


class TestParseSources:
    """Tests for source parsing logic."""

    @pytest.fixture
    def agent(self):
        return PydanticDiscoveryAgent(user_id="test")

    def test_parse_valid_sources(self, agent):
        """Should parse valid sources."""
        sources = [
            {"uri": "https://a.com", "title": "A"},
            {"uri": "https://b.com", "title": "B"},
        ]
        result = agent._parse_sources(sources)
        assert len(result) == 2
        assert result[0].uri == "https://a.com"

    def test_parse_empty_sources(self, agent):
        """Should handle empty sources."""
        assert agent._parse_sources(None) == []
        assert agent._parse_sources([]) == []

    def test_skip_sources_without_uri(self, agent):
        """Should skip sources without URI."""
        sources = [{"title": "No URI"}, {"uri": "https://valid.com"}]
        result = agent._parse_sources(sources)
        assert len(result) == 1
        assert result[0].uri == "https://valid.com"


class TestEmptyResponses:
    """Tests for handling empty/invalid responses."""

    @pytest.fixture
    def agent(self):
        return PydanticDiscoveryAgent(user_id="test")

    @pytest.mark.asyncio
    async def test_discover_restaurants_empty_response(self, agent):
        """Should handle empty restaurant response."""
        with patch(
            "fcp.agents.pydantic_agents.discovery.gemini.generate_json_with_grounding",
            new_callable=AsyncMock,
            return_value="not a dict",
        ):
            request = RestaurantDiscoveryRequest(
                taste_profile=TasteProfile(),
                location="Test City",
            )
            result = await agent.discover_restaurants_typed(request)

            assert isinstance(result, RestaurantResult)
            assert result.restaurants == []

    @pytest.mark.asyncio
    async def test_discover_recipes_empty_response(self, agent):
        """Should handle empty recipe response."""
        with patch(
            "fcp.agents.pydantic_agents.discovery.gemini.generate_json_with_grounding",
            new_callable=AsyncMock,
            return_value=None,
        ):
            request = RecipeDiscoveryRequest(taste_profile=TasteProfile())
            result = await agent.discover_recipes_typed(request)

            assert isinstance(result, RecipeResult)
            assert result.recipes == []

    @pytest.mark.asyncio
    async def test_discover_seasonal_empty_response(self, agent):
        """Should handle empty seasonal response."""
        with patch(
            "fcp.agents.pydantic_agents.discovery.gemini.generate_json_with_grounding",
            new_callable=AsyncMock,
            return_value=[],
        ):
            request = SeasonalDiscoveryRequest(
                taste_profile=TasteProfile(),
                location="Test",
                current_month=1,
            )
            result = await agent.discover_seasonal_typed(request)

            assert isinstance(result, SeasonalResult)
            assert result.seasonal_discoveries == []
            assert result.month == "January"
