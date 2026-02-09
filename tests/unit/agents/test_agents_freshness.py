"""Tests for FreshnessAgent."""

from unittest.mock import AsyncMock, patch

import pytest


class TestFreshnessAgentGenerateDailyInsight:
    """Tests for generate_daily_insight method."""

    @pytest.mark.asyncio
    async def test_generate_daily_insight_success(self):
        """Test successful daily insight generation."""
        from fcp.agents.freshness import FreshnessAgent

        agent = FreshnessAgent("user123")

        mock_grounding_result = {
            "text": "Today is a great day for soup! The weather is perfect.",
            "sources": [{"title": "Source", "url": "http://example.com"}],
        }

        with patch("fcp.agents.freshness.gemini") as mock_gemini:
            mock_gemini.generate_with_grounding = AsyncMock(return_value=mock_grounding_result)

            result = await agent.generate_daily_insight(
                taste_profile={"favorite_cuisines": ["Japanese"]},
                recent_logs=[{"dish_name": "Ramen"}],
                location="Seattle",
            )

            assert result["user_id"] == "user123"
            assert result["insight"] == mock_grounding_result["text"]
            assert result["type"] == "daily_insight"
            assert "date" in result

    @pytest.mark.asyncio
    async def test_generate_daily_insight_without_location(self):
        """Test daily insight generation without location."""
        from fcp.agents.freshness import FreshnessAgent

        agent = FreshnessAgent("user123")

        with patch("fcp.agents.freshness.gemini") as mock_gemini:
            mock_gemini.generate_with_grounding = AsyncMock(return_value={"text": "Great insight!", "sources": []})

            result = await agent.generate_daily_insight(
                taste_profile={},
                recent_logs=[],
                location=None,
            )

            assert result["insight"] == "Great insight!"


class TestFreshnessAgentGenerateStreakCelebration:
    """Tests for generate_streak_celebration method."""

    @pytest.mark.asyncio
    async def test_generate_streak_celebration_legendary(self):
        """Test streak celebration for legendary milestone."""
        from fcp.agents.freshness import FreshnessAgent

        agent = FreshnessAgent("user123")

        mock_result = {
            "headline": "LEGENDARY!",
            "message": "365 days!",
            "achievement_name": "FOOD LOGGING LEGEND",
        }

        with patch("fcp.agents.freshness.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value=mock_result)

            result = await agent.generate_streak_celebration(
                streak_days=365,
                user_name="Chef Master",
            )

            assert result["milestone"] == "legendary"
            assert result["streak_days"] == 365

    @pytest.mark.asyncio
    async def test_generate_streak_celebration_century(self):
        """Test streak celebration for century milestone."""
        from fcp.agents.freshness import FreshnessAgent

        agent = FreshnessAgent("user123")

        with patch("fcp.agents.freshness.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value={"message": "100 days!"})

            result = await agent.generate_streak_celebration(streak_days=100)

            assert result["milestone"] == "incredible"

    @pytest.mark.asyncio
    async def test_generate_streak_celebration_month(self):
        """Test streak celebration for month milestone."""
        from fcp.agents.freshness import FreshnessAgent

        agent = FreshnessAgent("user123")

        with patch("fcp.agents.freshness.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value={"message": "30 days!"})

            result = await agent.generate_streak_celebration(streak_days=30)

            assert result["milestone"] == "amazing"

    @pytest.mark.asyncio
    async def test_generate_streak_celebration_week(self):
        """Test streak celebration for week milestone."""
        from fcp.agents.freshness import FreshnessAgent

        agent = FreshnessAgent("user123")

        with patch("fcp.agents.freshness.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value={"message": "7 days!"})

            result = await agent.generate_streak_celebration(streak_days=7)

            assert result["milestone"] == "great"

    @pytest.mark.asyncio
    async def test_generate_streak_celebration_starter(self):
        """Test streak celebration for starter milestone."""
        from fcp.agents.freshness import FreshnessAgent

        agent = FreshnessAgent("user123")

        with patch("fcp.agents.freshness.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value={"message": "3 days!"})

            result = await agent.generate_streak_celebration(streak_days=3)

            assert result["milestone"] == "nice"

    @pytest.mark.asyncio
    async def test_generate_streak_celebration_default_name(self):
        """Test streak celebration with default username."""
        from fcp.agents.freshness import FreshnessAgent

        agent = FreshnessAgent("user123")

        with patch("fcp.agents.freshness.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value={"message": "Great!"})

            result = await agent.generate_streak_celebration(
                streak_days=7,
                user_name=None,  # Should default to "foodie"
            )

            assert result["type"] == "streak_celebration"


class TestFreshnessAgentGenerateWeeklySummaryTeaser:
    """Tests for generate_weekly_summary_teaser method."""

    @pytest.mark.asyncio
    async def test_generate_weekly_summary_teaser_success(self):
        """Test weekly summary teaser generation."""
        from fcp.agents.freshness import FreshnessAgent

        agent = FreshnessAgent("user123")

        mock_result = {
            "teaser_text": "Your week was amazing!",
            "highlight_stat": "You tried 5 new cuisines!",
            "call_to_action": "See your full summary",
        }

        with patch("fcp.agents.freshness.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value=mock_result)

            result = await agent.generate_weekly_summary_teaser(
                food_logs=[{"dish_name": "Pizza"}, {"dish_name": "Ramen"}]
            )

            assert result["user_id"] == "user123"
            assert result["week_entries"] == 2
            assert result["teaser"] == mock_result
            assert result["type"] == "weekly_teaser"


class TestFreshnessAgentGenerateMealReminder:
    """Tests for generate_meal_reminder method."""

    @pytest.mark.asyncio
    async def test_generate_meal_reminder_success(self):
        """Test meal reminder generation."""
        from fcp.agents.freshness import FreshnessAgent

        agent = FreshnessAgent("user123")

        mock_result = {
            "message": "Time for lunch!",
            "suggestions": ["Salad", "Sandwich", "Soup"],
            "quick_log_prompt": "Log your lunch now!",
        }

        with patch("fcp.agents.freshness.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value=mock_result)

            result = await agent.generate_meal_reminder(
                meal_type="lunch",
                taste_profile={"favorite_cuisines": ["Italian"]},
                last_meal_hours_ago=5.5,
            )

            assert result["user_id"] == "user123"
            assert result["meal_type"] == "lunch"
            assert result["hours_since_meal"] == 5.5
            assert result["type"] == "meal_reminder"


class TestFreshnessAgentGenerateAchievementUnlock:
    """Tests for generate_achievement_unlock method."""

    @pytest.mark.asyncio
    async def test_generate_achievement_unlock_success(self):
        """Test achievement unlock content generation."""
        from fcp.agents.freshness import FreshnessAgent

        agent = FreshnessAgent("user123")

        mock_result = {
            "name": "Cuisine Explorer",
            "badge": "Bronze Explorer",
            "message": "You've explored 5 cuisines!",
            "significance": "Variety is the spice of life!",
            "next_goal": "Try 10 cuisines",
        }

        with patch("fcp.agents.freshness.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value=mock_result)

            result = await agent.generate_achievement_unlock(
                achievement_type="cuisine_explorer",
                achievement_data={"cuisines_tried": 5},
            )

            assert result["user_id"] == "user123"
            assert result["achievement_type"] == "cuisine_explorer"
            assert result["content"] == mock_result
            assert result["type"] == "achievement_unlock"
            assert "unlocked_at" in result


class TestFreshnessAgentGenerateFoodTipOfDay:
    """Tests for generate_food_tip_of_day method."""

    @pytest.mark.asyncio
    async def test_generate_food_tip_of_day_success(self):
        """Test food tip generation."""
        from fcp.agents.freshness import FreshnessAgent

        agent = FreshnessAgent("user123")

        mock_grounding_result = {
            "data": {
                "tip_title": "Tasting Tips",
                "tip_content": "Always taste while cooking!",
                "category": "Cooking Techniques",
                "source": "Chef's Guide",
            },
            "sources": [{"title": "Cooking Tips", "url": "http://example.com"}],
        }

        with patch("fcp.agents.freshness.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(return_value=mock_grounding_result)

            result = await agent.generate_food_tip_of_day(taste_profile={"favorite_cuisines": ["Japanese"]})

            assert result["user_id"] == "user123"
            assert result["tip"] == "Always taste while cooking!"
            assert result["tip_title"] == "Tasting Tips"
            assert result["category"] == "Cooking Techniques"
            assert result["source"] == "Chef's Guide"
            assert result["sources"] == mock_grounding_result["sources"]
            assert result["type"] == "food_tip"
            assert "date" in result


class TestFreshnessAgentGenerateSeasonalReminder:
    """Tests for generate_seasonal_reminder method."""

    @pytest.mark.asyncio
    async def test_generate_seasonal_reminder_success(self):
        """Test seasonal reminder generation."""
        from fcp.agents.freshness import FreshnessAgent

        agent = FreshnessAgent("user123")

        mock_grounding_result = {
            "text": "Apples are in season! Try making apple pie.",
            "sources": [{"title": "Seasonal Foods", "url": "http://example.com"}],
        }

        with patch("fcp.agents.freshness.gemini") as mock_gemini:
            mock_gemini.generate_with_grounding = AsyncMock(return_value=mock_grounding_result)

            result = await agent.generate_seasonal_reminder(
                location="Seattle",
                taste_profile={"favorite_cuisines": ["American"]},
            )

            assert result["user_id"] == "user123"
            assert result["location"] == "Seattle"
            assert result["reminder"] == mock_grounding_result["text"]
            assert result["type"] == "seasonal_reminder"
            assert "month" in result
