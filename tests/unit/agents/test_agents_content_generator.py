"""Tests for ContentGeneratorAgent."""

from unittest.mock import AsyncMock, patch

import pytest


class TestContentGeneratorAgentGenerateWeeklyDigest:
    """Tests for generate_weekly_digest method."""

    @pytest.mark.asyncio
    async def test_generate_weekly_digest_success(self):
        """Test successful weekly digest generation."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")

        mock_result = {
            "title": "A Week of Culinary Adventures",
            "subtitle": "From ramen to tacos",
            "week_summary": "An amazing week!",
        }

        with patch("fcp.agents.content_generator.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value=mock_result)

            result = await agent.generate_weekly_digest(
                food_logs=[{"dish_name": "Ramen"}, {"dish_name": "Tacos"}],
                user_name="Chef",
            )

            assert result["user_id"] == "user123"
            assert result["period"] == "week"
            assert result["entry_count"] == 2
            assert result["digest"]["title"] == "A Week of Culinary Adventures"

    @pytest.mark.asyncio
    async def test_generate_weekly_digest_without_user_name(self):
        """Test weekly digest generation without user name."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")

        with patch("fcp.agents.content_generator.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value={"title": "Weekly"})

            result = await agent.generate_weekly_digest(
                food_logs=[{"dish_name": "Pizza"}],
                user_name=None,
            )

            assert result["entry_count"] == 1


class TestContentGeneratorAgentGenerateSocialPost:
    """Tests for generate_social_post method."""

    @pytest.mark.asyncio
    async def test_generate_social_post_instagram(self):
        """Test Instagram post generation."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")

        mock_result = {
            "caption": "Best ramen ever!",
            "hashtags": ["#ramen", "#foodie"],
            "character_count": 20,
        }

        with patch("fcp.agents.content_generator.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value=mock_result)

            result = await agent.generate_social_post(
                food_log={"dish_name": "Ramen"},
                platform="instagram",
                style="casual",
            )

            assert result["platform"] == "instagram"
            assert result["style"] == "casual"
            assert result["content"]["caption"] == "Best ramen ever!"

    @pytest.mark.asyncio
    async def test_generate_social_post_twitter(self):
        """Test Twitter post generation."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")

        with patch("fcp.agents.content_generator.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value={"caption": "Tweet!"})

            result = await agent.generate_social_post(
                food_log={"dish_name": "Sushi"},
                platform="twitter",
                style="foodie",
            )

            assert result["platform"] == "twitter"

    @pytest.mark.asyncio
    async def test_generate_social_post_facebook(self):
        """Test Facebook post generation."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")

        with patch("fcp.agents.content_generator.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value={"caption": "Post!"})

            result = await agent.generate_social_post(
                food_log={"dish_name": "Pasta"},
                platform="facebook",
                style="professional",
            )

            assert result["platform"] == "facebook"

    @pytest.mark.asyncio
    async def test_generate_social_post_unknown_platform(self):
        """Test post generation for unknown platform uses Instagram defaults."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")

        with patch("fcp.agents.content_generator.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value={"caption": "Post!"})

            result = await agent.generate_social_post(
                food_log={"dish_name": "Tacos"},
                platform="tiktok",  # Unknown platform
                style="casual",
            )

            assert result["platform"] == "tiktok"


class TestContentGeneratorAgentGenerateFoodStory:
    """Tests for generate_food_story method."""

    @pytest.mark.asyncio
    async def test_generate_food_story_success(self):
        """Test successful food story generation."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")

        mock_result = {
            "title": "A Day of Discovery",
            "story": "It started with breakfast...",
            "featured_dishes": ["Pancakes", "Ramen"],
        }

        with patch("fcp.agents.content_generator.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value=mock_result)

            result = await agent.generate_food_story(
                food_logs=[{"dish_name": "Pancakes"}, {"dish_name": "Ramen"}],
                theme="adventure",
            )

            assert result["user_id"] == "user123"
            assert result["theme"] == "adventure"
            assert result["entry_count"] == 2

    @pytest.mark.asyncio
    async def test_generate_food_story_without_theme(self):
        """Test food story generation without theme."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")

        with patch("fcp.agents.content_generator.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value={"title": "Story"})

            result = await agent.generate_food_story(
                food_logs=[{"dish_name": "Salad"}],
                theme=None,
            )

            assert result["theme"] is None


class TestContentGeneratorAgentGenerateMonthlyReview:
    """Tests for generate_monthly_review method."""

    @pytest.mark.asyncio
    async def test_generate_monthly_review_success(self):
        """Test successful monthly review generation."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")

        mock_result = {
            "title": "January Food Review",
            "top_meals": [{"dish": "Ramen"}],
        }

        with patch("fcp.agents.content_generator.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value=mock_result)

            result = await agent.generate_monthly_review(
                food_logs=[{"dish_name": f"Meal{i}"} for i in range(30)],
                taste_profile={"favorite_cuisines": ["Japanese"]},
            )

            assert result["user_id"] == "user123"
            assert result["period"] == "month"
            assert result["entry_count"] == 30

    @pytest.mark.asyncio
    async def test_generate_monthly_review_without_profile(self):
        """Test monthly review generation without taste profile."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")

        with patch("fcp.agents.content_generator.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value={"title": "Review"})

            result = await agent.generate_monthly_review(
                food_logs=[{"dish_name": "Food"}],
                taste_profile=None,
            )

            assert result["review"]["title"] == "Review"


class TestContentGeneratorAgentGenerateRecipeCard:
    """Tests for generate_recipe_card method."""

    @pytest.mark.asyncio
    async def test_generate_recipe_card_with_instructions(self):
        """Test recipe card generation with instructions."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")

        mock_result = {
            "name": "Homemade Pasta",
            "instructions": ["Boil water", "Cook pasta"],
        }

        with patch("fcp.agents.content_generator.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value=mock_result)

            result = await agent.generate_recipe_card(
                food_log={"id": "log123", "dish_name": "Pasta"},
                include_instructions=True,
            )

            assert result["source_log"] == "log123"
            assert result["recipe_card"]["name"] == "Homemade Pasta"

    @pytest.mark.asyncio
    async def test_generate_recipe_card_without_instructions(self):
        """Test recipe card generation without instructions."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")

        with patch("fcp.agents.content_generator.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value={"name": "Recipe"})

            result = await agent.generate_recipe_card(
                food_log={"id": "log456", "dish_name": "Salad"},
                include_instructions=False,
            )

            assert result["source_log"] == "log456"


class TestContentGeneratorAgentGenerateBlogPost:
    """Tests for generate_blog_post method."""

    @pytest.mark.asyncio
    async def test_generate_blog_post_success(self):
        """Test successful blog post generation."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")

        mock_result = {
            "title": "My Food Journey",
            "slug": "my-food-journey",
            "content": "# Great content",
        }

        with patch("fcp.agents.content_generator.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value=mock_result)

            result = await agent.generate_blog_post(
                food_logs=[
                    {"dish_name": "Ramen", "cuisine": "Japanese", "venue_name": "Restaurant"},
                ],
                theme="culinary_journey",
                style="conversational",
            )

            assert result["title"] == "My Food Journey"
            assert result["slug"] == "my-food-journey"

    @pytest.mark.asyncio
    async def test_generate_blog_post_generates_slug(self):
        """Test blog post generation creates slug if missing."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")

        mock_result = {
            "title": "Amazing Food Adventures!",
            # No slug provided
        }

        with patch("fcp.agents.content_generator.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value=mock_result)

            result = await agent.generate_blog_post(
                food_logs=[{"dish_name": "Food"}],
            )

            assert result["slug"] == "amazing-food-adventures"

    @pytest.mark.asyncio
    async def test_generate_blog_post_with_nutrition_info(self):
        """Test blog post with alternate field names."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")

        with patch("fcp.agents.content_generator.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value={"title": "Post", "slug": "post"})

            result = await agent.generate_blog_post(
                food_logs=[
                    {
                        "dish_name": "Pizza",
                        "nutrition_info": {"calories": 500},  # Alternate field name
                        "venue": "Home",  # Alternate field name
                    },
                ],
            )

            assert result["title"] == "Post"


class TestContentGeneratorAgentSlugify:
    """Tests for _slugify helper method."""

    def test_slugify_basic(self):
        """Test basic slug generation."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")
        assert agent._slugify("Hello World") == "hello-world"

    def test_slugify_special_characters(self):
        """Test slug generation with special characters."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")
        assert agent._slugify("Hello! World?") == "hello-world"

    def test_slugify_empty_string(self):
        """Test slug generation with empty string."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")
        assert agent._slugify("") == "untitled"

    def test_slugify_none(self):
        """Test slug generation with None."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")
        assert agent._slugify(None) == "untitled"

    def test_slugify_multiple_spaces(self):
        """Test slug generation with multiple spaces."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")
        assert agent._slugify("Hello   World") == "hello-world"

    def test_slugify_truncates_long_titles(self):
        """Test slug generation truncates long titles."""
        from fcp.agents.content_generator import ContentGeneratorAgent

        agent = ContentGeneratorAgent("user123")
        long_title = "a" * 150
        result = agent._slugify(long_title)
        assert len(result) <= 100
