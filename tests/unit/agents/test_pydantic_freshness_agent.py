"""Tests for Pydantic AI-based Freshness Agent."""

from unittest.mock import AsyncMock, patch

import pytest

from fcp.agents.pydantic_agents.freshness import (
    AchievementRequest,
    AchievementResult,
    CelebrationContent,
    DailyInsightRequest,
    DailyInsightResult,
    FoodLog,
    FoodTipRequest,
    FoodTipResult,
    GroundingSource,
    MealReminderRequest,
    MealReminderResult,
    PydanticFreshnessAgent,
    ReminderContent,
    SeasonalReminderRequest,
    SeasonalReminderResult,
    StreakCelebrationRequest,
    StreakCelebrationResult,
    TasteProfile,
    WeeklyTeaserRequest,
    WeeklyTeaserResult,
)


class TestTasteProfileModel:
    """Tests for TasteProfile Pydantic model."""

    def test_taste_profile_defaults(self):
        """Should have sensible defaults."""
        profile = TasteProfile()
        assert profile.top_cuisines == []
        assert profile.spice_preference == "medium"

    def test_taste_profile_to_dict(self):
        """Should convert to dictionary."""
        profile = TasteProfile(top_cuisines=["Thai", "Japanese"])
        d = profile.to_dict()
        assert d["top_cuisines"] == ["Thai", "Japanese"]


class TestFoodLogModel:
    """Tests for FoodLog Pydantic model."""

    def test_food_log_minimal(self):
        """Should work with minimal data."""
        log = FoodLog()
        assert log.dish_name == ""

    def test_food_log_full(self):
        """Should accept all fields."""
        log = FoodLog(
            dish_name="Ramen",
            cuisine="Japanese",
            created_at="2026-02-03",
            venue_name="Noodle House",
        )
        assert log.dish_name == "Ramen"
        assert log.venue_name == "Noodle House"


class TestRequestModels:
    """Tests for request Pydantic models."""

    def test_daily_insight_request(self):
        """Should create daily insight request."""
        request = DailyInsightRequest(
            taste_profile=TasteProfile(top_cuisines=["Italian"]),
            recent_logs=[FoodLog(dish_name="Pizza")],
            location="New York",
        )
        assert request.location == "New York"
        assert len(request.recent_logs) == 1

    def test_streak_celebration_request_validation(self):
        """Should validate streak days."""
        request = StreakCelebrationRequest(streak_days=7, user_name="John")
        assert request.streak_days == 7

        with pytest.raises(ValueError):
            StreakCelebrationRequest(streak_days=0)

    def test_meal_reminder_request(self):
        """Should create meal reminder request."""
        request = MealReminderRequest(
            meal_type="lunch",
            taste_profile=TasteProfile(),
            last_meal_hours_ago=4.5,
        )
        assert request.meal_type == "lunch"
        assert request.last_meal_hours_ago == 4.5


class TestResultModels:
    """Tests for result Pydantic models."""

    def test_daily_insight_result(self):
        """Should create daily insight result."""
        result = DailyInsightResult(
            user_id="user123",
            date="2026-02-03",
            insight="Try the seasonal butternut squash!",
            sources=[GroundingSource(uri="https://example.com", title="Example")],
        )
        assert result.type == "daily_insight"
        assert len(result.sources) == 1

    def test_streak_celebration_result(self):
        """Should create streak celebration result."""
        result = StreakCelebrationResult(
            user_id="user123",
            streak_days=30,
            milestone="amazing",
            celebration=CelebrationContent(headline="30 Days!"),
        )
        assert result.milestone == "amazing"

    def test_content_models_allow_extra(self):
        """Should allow extra fields in content models."""
        data = {"headline": "Test", "extra_field": "value"}
        content = CelebrationContent.model_validate(data)
        assert content.headline == "Test"
        assert content.extra_field == "value"  # type: ignore[attr-defined]


class TestPydanticFreshnessAgent:
    """Tests for PydanticFreshnessAgent."""

    @pytest.fixture
    def agent(self):
        """Create agent instance."""
        return PydanticFreshnessAgent(user_id="test_user")

    @pytest.fixture
    def mock_grounding_response(self):
        """Create mock grounding response."""
        return {
            "text": "Try the seasonal butternut squash! It's perfect for fall.",
            "sources": [{"uri": "https://example.com", "title": "Example"}],
        }

    @pytest.fixture
    def mock_json_response(self):
        """Create mock JSON thinking response."""
        return {
            "headline": "Congratulations!",
            "message": "You've been logging consistently!",
            "achievement_name": "Week Warrior",
            "achievement_description": "7 days of food logging",
            "encouragement": "Keep it up!",
            "fun_fact": "Did you know...",
        }

    @pytest.mark.asyncio
    async def test_generate_daily_insight_typed(self, agent, mock_grounding_response):
        """Should generate daily insight with typed response."""
        with patch(
            "fcp.agents.pydantic_agents.freshness.gemini.generate_with_grounding",
            new_callable=AsyncMock,
            return_value=mock_grounding_response,
        ):
            request = DailyInsightRequest(
                taste_profile=TasteProfile(top_cuisines=["Italian"]),
                recent_logs=[FoodLog(dish_name="Pizza")],
            )
            result = await agent.generate_daily_insight_typed(request)

            assert isinstance(result, DailyInsightResult)
            assert result.user_id == "test_user"
            assert "butternut squash" in result.insight
            assert len(result.sources) == 1

    @pytest.mark.asyncio
    async def test_generate_streak_celebration_typed(self, agent, mock_json_response):
        """Should generate streak celebration with typed response."""
        with patch(
            "fcp.agents.pydantic_agents.freshness.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_json_response,
        ):
            request = StreakCelebrationRequest(streak_days=7, user_name="Alice")
            result = await agent.generate_streak_celebration_typed(request)

            assert isinstance(result, StreakCelebrationResult)
            assert result.streak_days == 7
            assert result.milestone == "great"
            assert result.celebration.headline == "Congratulations!"

    @pytest.mark.asyncio
    async def test_generate_weekly_teaser_typed(self, agent):
        """Should generate weekly teaser with typed response."""
        mock_response = {
            "teaser_text": "You had an amazing week!",
            "highlight_stat": "5 different cuisines",
            "call_to_action": "View your full summary",
        }
        with patch(
            "fcp.agents.pydantic_agents.freshness.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            request = WeeklyTeaserRequest(food_logs=[FoodLog(dish_name="Ramen"), FoodLog(dish_name="Tacos")])
            result = await agent.generate_weekly_teaser_typed(request)

            assert isinstance(result, WeeklyTeaserResult)
            assert result.week_entries == 2
            assert result.teaser.teaser_text == "You had an amazing week!"

    @pytest.mark.asyncio
    async def test_generate_meal_reminder_typed(self, agent):
        """Should generate meal reminder with typed response."""
        mock_response = {
            "message": "Time for lunch!",
            "suggestions": ["Salad", "Sandwich", "Soup"],
            "quick_log_prompt": "What did you eat?",
        }
        with patch(
            "fcp.agents.pydantic_agents.freshness.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            request = MealReminderRequest(
                meal_type="lunch",
                taste_profile=TasteProfile(),
                last_meal_hours_ago=5.0,
            )
            result = await agent.generate_meal_reminder_typed(request)

            assert isinstance(result, MealReminderResult)
            assert result.meal_type == "lunch"
            assert len(result.reminder.suggestions) == 3

    @pytest.mark.asyncio
    async def test_generate_achievement_typed(self, agent):
        """Should generate achievement with typed response."""
        mock_response = {
            "name": "Cuisine Explorer",
            "badge": "Globe icon",
            "message": "You've explored 10 cuisines!",
            "significance": "Shows culinary adventure",
            "next_goal": "Try 5 more",
        }
        with patch(
            "fcp.agents.pydantic_agents.freshness.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            request = AchievementRequest(
                achievement_type="cuisine_explorer",
                achievement_data={"cuisines_count": 10},
            )
            result = await agent.generate_achievement_typed(request)

            assert isinstance(result, AchievementResult)
            assert result.achievement_type == "cuisine_explorer"
            assert result.content.name == "Cuisine Explorer"
            assert result.unlocked_at  # Should have timestamp

    @pytest.mark.asyncio
    async def test_generate_food_tip_typed(self, agent):
        """Should generate food tip with typed response."""
        mock_response = {
            "data": {
                "tip_title": "Knife Skills",
                "tip_content": "Keep your knife sharp!",
                "category": "cooking",
                "source": "Chef Tips",
            },
            "sources": [{"uri": "https://cooking.com", "title": "Cooking Tips"}],
        }
        with patch(
            "fcp.agents.pydantic_agents.freshness.gemini.generate_json_with_grounding",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            request = FoodTipRequest(taste_profile=TasteProfile())
            result = await agent.generate_food_tip_typed(request)

            assert isinstance(result, FoodTipResult)
            assert result.tip_title == "Knife Skills"
            assert result.category == "cooking"

    @pytest.mark.asyncio
    async def test_generate_seasonal_reminder_typed(self, agent, mock_grounding_response):
        """Should generate seasonal reminder with typed response."""
        with patch(
            "fcp.agents.pydantic_agents.freshness.gemini.generate_with_grounding",
            new_callable=AsyncMock,
            return_value=mock_grounding_response,
        ):
            request = SeasonalReminderRequest(
                location="Portland, OR",
                taste_profile=TasteProfile(),
            )
            result = await agent.generate_seasonal_reminder_typed(request)

            assert isinstance(result, SeasonalReminderResult)
            assert result.location == "Portland, OR"
            assert result.month  # Should have month

    # Backward compatibility tests
    @pytest.mark.asyncio
    async def test_backward_compat_daily_insight(self, agent, mock_grounding_response):
        """Should work with dict interface."""
        with patch(
            "fcp.agents.pydantic_agents.freshness.gemini.generate_with_grounding",
            new_callable=AsyncMock,
            return_value=mock_grounding_response,
        ):
            result = await agent.generate_daily_insight(
                taste_profile={"top_cuisines": ["Thai"]},
                recent_logs=[{"dish_name": "Pad Thai"}],
                location="Seattle",
            )

            assert isinstance(result, dict)
            assert result["user_id"] == "test_user"
            assert result["type"] == "daily_insight"

    @pytest.mark.asyncio
    async def test_backward_compat_streak_celebration(self, agent, mock_json_response):
        """Should work with dict interface."""
        with patch(
            "fcp.agents.pydantic_agents.freshness.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_json_response,
        ):
            result = await agent.generate_streak_celebration(
                streak_days=30,
                user_name="Bob",
            )

            assert isinstance(result, dict)
            assert result["milestone"] == "amazing"

    @pytest.mark.asyncio
    async def test_backward_compat_weekly_teaser(self, agent):
        """Should work with dict interface."""
        mock_response = {"teaser_text": "Great week!", "highlight_stat": "", "call_to_action": ""}
        with patch(
            "fcp.agents.pydantic_agents.freshness.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await agent.generate_weekly_summary_teaser(
                food_logs=[{"dish_name": "Sushi"}],
            )

            assert isinstance(result, dict)
            assert result["type"] == "weekly_teaser"

    @pytest.mark.asyncio
    async def test_backward_compat_meal_reminder(self, agent):
        """Should work with dict interface."""
        mock_response = {"message": "Time to eat!", "suggestions": [], "quick_log_prompt": ""}
        with patch(
            "fcp.agents.pydantic_agents.freshness.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await agent.generate_meal_reminder(
                meal_type="dinner",
                taste_profile={"top_cuisines": ["Mexican"]},
                last_meal_hours_ago=6.0,
            )

            assert isinstance(result, dict)
            assert result["meal_type"] == "dinner"

    @pytest.mark.asyncio
    async def test_backward_compat_achievement(self, agent):
        """Should work with dict interface."""
        mock_response = {"name": "Test", "badge": "", "message": "", "significance": "", "next_goal": ""}
        with patch(
            "fcp.agents.pydantic_agents.freshness.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await agent.generate_achievement_unlock(
                achievement_type="first_cuisine",
                achievement_data={"cuisine": "Thai"},
            )

            assert isinstance(result, dict)
            assert result["type"] == "achievement_unlock"

    @pytest.mark.asyncio
    async def test_backward_compat_food_tip(self, agent):
        """Should work with dict interface."""
        mock_response = {"data": {"tip_title": "Test", "tip_content": "", "category": "", "source": ""}, "sources": []}
        with patch(
            "fcp.agents.pydantic_agents.freshness.gemini.generate_json_with_grounding",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await agent.generate_food_tip_of_day(
                taste_profile={"top_cuisines": ["Japanese"]},
            )

            assert isinstance(result, dict)
            assert result["type"] == "food_tip"

    @pytest.mark.asyncio
    async def test_backward_compat_seasonal_reminder(self, agent, mock_grounding_response):
        """Should work with dict interface."""
        with patch(
            "fcp.agents.pydantic_agents.freshness.gemini.generate_with_grounding",
            new_callable=AsyncMock,
            return_value=mock_grounding_response,
        ):
            result = await agent.generate_seasonal_reminder(
                location="San Francisco",
                taste_profile={"top_cuisines": ["California"]},
            )

            assert isinstance(result, dict)
            assert result["type"] == "seasonal_reminder"


class TestMilestoneLogic:
    """Tests for milestone calculation."""

    @pytest.fixture
    def agent(self):
        return PydanticFreshnessAgent(user_id="test")

    def test_milestone_legendary(self, agent):
        """365+ days should be legendary."""
        milestone, achievement = agent._get_milestone(365)
        assert milestone == "legendary"
        assert achievement == "FOOD LOGGING LEGEND"

    def test_milestone_incredible(self, agent):
        """100-364 days should be incredible."""
        milestone, achievement = agent._get_milestone(100)
        assert milestone == "incredible"

    def test_milestone_amazing(self, agent):
        """30-99 days should be amazing."""
        milestone, achievement = agent._get_milestone(30)
        assert milestone == "amazing"

    def test_milestone_great(self, agent):
        """7-29 days should be great."""
        milestone, achievement = agent._get_milestone(7)
        assert milestone == "great"

    def test_milestone_nice(self, agent):
        """1-6 days should be nice."""
        milestone, achievement = agent._get_milestone(1)
        assert milestone == "nice"

    def test_milestone_zero_days(self, agent):
        """0 days should hit fallback case."""
        milestone, achievement = agent._get_milestone(0)
        assert milestone == "nice"
        assert achievement == "STREAK STARTED"


class TestHelperMethods:
    """Tests for helper methods."""

    @pytest.fixture
    def agent(self):
        return PydanticFreshnessAgent(user_id="test")

    def test_parse_sources_valid(self, agent):
        """Should parse valid sources."""
        sources = [
            {"uri": "https://a.com", "title": "A"},
            {"uri": "https://b.com", "title": "B"},
        ]
        result = agent._parse_sources(sources)
        assert len(result) == 2
        assert result[0].uri == "https://a.com"

    def test_parse_sources_empty(self, agent):
        """Should handle empty sources."""
        assert agent._parse_sources(None) == []
        assert agent._parse_sources([]) == []

    def test_parse_sources_skip_invalid(self, agent):
        """Should skip sources without URI."""
        sources = [{"title": "No URI"}, {"uri": "https://valid.com"}]
        result = agent._parse_sources(sources)
        assert len(result) == 1

    def test_parse_content_safely_valid(self, agent):
        """Should parse valid content."""
        data = {"headline": "Test", "message": "Hello"}
        result = agent._parse_content_safely(data, CelebrationContent)
        assert result.headline == "Test"

    def test_parse_content_safely_invalid(self, agent):
        """Should return empty model for invalid data."""
        result = agent._parse_content_safely("not a dict", CelebrationContent)
        assert result.headline == ""

    def test_parse_content_safely_partial(self, agent):
        """Should handle partial data with defaults."""
        data = {"headline": "Only this"}
        result = agent._parse_content_safely(data, CelebrationContent)
        assert result.headline == "Only this"
        assert result.message == ""

    def test_parse_content_safely_validation_error(self, agent):
        """Should return empty model when validation fails."""
        # ReminderContent.suggestions expects list[str], passing a dict forces validation error
        data = {"suggestions": {"invalid": "not_a_list"}}
        result = agent._parse_content_safely(data, ReminderContent)
        # Should fall back to empty model
        assert result.suggestions == []


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.fixture
    def agent(self):
        return PydanticFreshnessAgent(user_id="test")

    @pytest.mark.asyncio
    async def test_food_tip_non_dict_response(self, agent):
        """Should handle non-dict response for food tip."""
        with patch(
            "fcp.agents.pydantic_agents.freshness.gemini.generate_json_with_grounding",
            new_callable=AsyncMock,
            return_value="invalid",
        ):
            request = FoodTipRequest(taste_profile=TasteProfile())
            result = await agent.generate_food_tip_typed(request)

            assert isinstance(result, FoodTipResult)
            assert result.tip == ""
            assert result.tip_title == "Food Tip"

    @pytest.mark.asyncio
    async def test_food_tip_missing_data_key(self, agent):
        """Should handle response without data key."""
        with patch(
            "fcp.agents.pydantic_agents.freshness.gemini.generate_json_with_grounding",
            new_callable=AsyncMock,
            return_value={"sources": []},
        ):
            request = FoodTipRequest(taste_profile=TasteProfile())
            result = await agent.generate_food_tip_typed(request)

            assert result.tip == ""

    @pytest.mark.asyncio
    async def test_daily_insight_empty_response(self, agent):
        """Should handle empty grounding response."""
        with patch(
            "fcp.agents.pydantic_agents.freshness.gemini.generate_with_grounding",
            new_callable=AsyncMock,
            return_value={},
        ):
            request = DailyInsightRequest(
                taste_profile=TasteProfile(),
                recent_logs=[],
            )
            result = await agent.generate_daily_insight_typed(request)

            assert result.insight == ""
            assert result.sources == []
