"""Tests for Pydantic AI-based Content Generator Agent."""

from unittest.mock import AsyncMock, patch

import pytest

from fcp.agents.pydantic_agents.content_generator import (
    BlogPostRequest,
    BlogPostResult,
    DigestContent,
    DigestHighlight,
    DigestStats,
    FoodLog,
    FoodStoryRequest,
    FoodStoryResult,
    MonthlyReviewContent,
    MonthlyReviewRequest,
    MonthlyReviewResult,
    PydanticContentGeneratorAgent,
    RecipeCardContent,
    RecipeCardRequest,
    RecipeCardResult,
    SocialPostContent,
    SocialPostRequest,
    SocialPostResult,
    StoryContent,
    TasteProfile,
    WeeklyDigestRequest,
    WeeklyDigestResult,
)


class TestFoodLogModel:
    """Tests for FoodLog Pydantic model."""

    def test_food_log_defaults(self):
        """Should have sensible defaults."""
        log = FoodLog()
        assert log.dish_name == ""
        assert log.cuisine == ""

    def test_food_log_full(self):
        """Should accept all fields."""
        log = FoodLog(
            dish_name="Ramen",
            cuisine="Japanese",
            created_at="2026-02-03",
            venue_name="Noodle House",
            ai_description="Delicious ramen",
        )
        assert log.dish_name == "Ramen"
        assert log.venue_name == "Noodle House"

    def test_food_log_extra_fields(self):
        """Should allow extra fields."""
        data = {"dish_name": "Test", "extra_field": "value"}
        log = FoodLog.model_validate(data)
        assert log.dish_name == "Test"
        assert log.extra_field == "value"  # type: ignore[attr-defined]


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


class TestRequestModels:
    """Tests for request Pydantic models."""

    def test_weekly_digest_request(self):
        """Should create weekly digest request."""
        request = WeeklyDigestRequest(
            food_logs=[FoodLog(dish_name="Pizza")],
            user_name="Alice",
        )
        assert request.user_name == "Alice"
        assert len(request.food_logs) == 1

    def test_social_post_request(self):
        """Should create social post request."""
        request = SocialPostRequest(
            food_log=FoodLog(dish_name="Sushi"),
            platform="twitter",
            style="professional",
        )
        assert request.platform == "twitter"
        assert request.style == "professional"

    def test_food_story_request(self):
        """Should create food story request."""
        request = FoodStoryRequest(
            food_logs=[FoodLog(dish_name="Tacos")],
            theme="adventure",
        )
        assert request.theme == "adventure"

    def test_monthly_review_request(self):
        """Should create monthly review request."""
        request = MonthlyReviewRequest(
            food_logs=[FoodLog(dish_name="Ramen")],
            taste_profile=TasteProfile(top_cuisines=["Japanese"]),
        )
        assert request.taste_profile is not None
        assert request.taste_profile.top_cuisines == ["Japanese"]

    def test_recipe_card_request(self):
        """Should create recipe card request."""
        request = RecipeCardRequest(
            food_log=FoodLog(dish_name="Pasta"),
            include_instructions=False,
        )
        assert request.include_instructions is False

    def test_blog_post_request(self):
        """Should create blog post request."""
        request = BlogPostRequest(
            food_logs=[FoodLog(dish_name="Curry")],
            theme="nutrition_focus",
            style="professional",
        )
        assert request.theme == "nutrition_focus"
        assert request.style == "professional"


class TestResultModels:
    """Tests for result Pydantic models."""

    def test_weekly_digest_result(self):
        """Should create weekly digest result."""
        result = WeeklyDigestResult(
            user_id="user123",
            period="week",
            entry_count=7,
            digest=DigestContent(title="Great Week!"),
        )
        assert result.period == "week"
        assert result.digest.title == "Great Week!"

    def test_social_post_result(self):
        """Should create social post result."""
        result = SocialPostResult(
            platform="instagram",
            style="casual",
            content=SocialPostContent(caption="Delicious!"),
        )
        assert result.content.caption == "Delicious!"

    def test_food_story_result(self):
        """Should create food story result."""
        result = FoodStoryResult(
            user_id="user123",
            theme="comfort",
            entry_count=5,
            story=StoryContent(title="A Comforting Journey"),
        )
        assert result.story.title == "A Comforting Journey"

    def test_monthly_review_result(self):
        """Should create monthly review result."""
        result = MonthlyReviewResult(
            user_id="user123",
            period="month",
            entry_count=30,
            review=MonthlyReviewContent(title="January Delights"),
        )
        assert result.review.title == "January Delights"

    def test_recipe_card_result(self):
        """Should create recipe card result."""
        result = RecipeCardResult(
            source_log="log123",
            recipe_card=RecipeCardContent(name="Homemade Pasta"),
        )
        assert result.recipe_card.name == "Homemade Pasta"

    def test_blog_post_result(self):
        """Should create blog post result."""
        result = BlogPostResult(
            title="My Food Journey",
            slug="my-food-journey",
            content="Long content here...",
            excerpt="Short excerpt",
            metadata={"author": "test"},
            suggestions=["Add images"],
        )
        assert result.slug == "my-food-journey"

    def test_content_models_allow_extra(self):
        """Should allow extra fields in content models."""
        data = {"title": "Test", "extra_field": "value"}
        content = DigestContent.model_validate(data)
        assert content.title == "Test"
        assert content.extra_field == "value"  # type: ignore[attr-defined]


class TestPydanticContentGeneratorAgent:
    """Tests for PydanticContentGeneratorAgent."""

    @pytest.fixture
    def agent(self):
        """Create agent instance."""
        return PydanticContentGeneratorAgent(user_id="test_user")

    @pytest.fixture
    def mock_digest_response(self):
        """Create mock digest response."""
        return {
            "title": "A Week of Culinary Adventures",
            "subtitle": "From comfort food to exotic flavors",
            "week_summary": "An amazing week of food!",
            "highlight": {"dish": "Ramen", "story": "Best meal ever", "image_url": ""},
            "stats": {"total_meals": 7, "cuisines": 3, "new_dishes": 2},
            "best_moments": [{"meal": "Ramen", "description": "Amazing"}],
            "suggestion": "Try Thai food next week!",
        }

    @pytest.fixture
    def mock_social_response(self):
        """Create mock social post response."""
        return {
            "caption": "Enjoying the best ramen in town!",
            "hashtags": ["#ramen", "#foodie", "#yummy"],
            "posting_tips": "Post during lunch hours",
            "character_count": 35,
        }

    @pytest.fixture
    def mock_story_response(self):
        """Create mock story response."""
        return {
            "title": "A Journey Through Flavors",
            "story": "Once upon a time...",
            "featured_dishes": ["Ramen", "Sushi"],
            "mood": "nostalgic",
            "word_count": 500,
        }

    @pytest.fixture
    def mock_review_response(self):
        """Create mock monthly review response."""
        return {
            "title": "January Food Highlights",
            "summary": "A great month!",
            "top_meals": [{"dish": "Ramen", "rank": 1}],
            "cuisine_breakdown": {"Japanese": 10, "Italian": 5},
            "discoveries": ["New ramen shop"],
            "patterns": ["Lunch at 12pm"],
            "goals": ["Try Korean food"],
            "stats": {"total_meals": 30},
        }

    @pytest.fixture
    def mock_recipe_response(self):
        """Create mock recipe card response."""
        return {
            "name": "Homemade Ramen",
            "description": "Delicious homemade ramen",
            "prep_time": "30 min",
            "cook_time": "2 hours",
            "servings": 4,
            "difficulty": "medium",
            "cuisine": "Japanese",
            "ingredients": ["noodles", "broth", "pork"],
            "instructions": ["Make broth", "Cook noodles"],
            "tips": ["Use fresh noodles"],
            "variations": ["Add egg"],
        }

    @pytest.fixture
    def mock_blog_response(self):
        """Create mock blog post response."""
        return {
            "title": "My Culinary Journey",
            "slug": "my-culinary-journey",
            "content": "Long blog content...",
            "excerpt": "A journey through food",
            "metadata": {"tags": ["food", "journey"]},
            "suggestions": ["Add more photos"],
        }

    @pytest.mark.asyncio
    async def test_generate_weekly_digest_typed(self, agent, mock_digest_response):
        """Should generate weekly digest with typed response."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_digest_response,
        ):
            request = WeeklyDigestRequest(
                food_logs=[FoodLog(dish_name="Ramen")],
                user_name="Alice",
            )
            result = await agent.generate_weekly_digest_typed(request)

            assert isinstance(result, WeeklyDigestResult)
            assert result.user_id == "test_user"
            assert result.entry_count == 1
            assert result.digest.title == "A Week of Culinary Adventures"

    @pytest.mark.asyncio
    async def test_generate_weekly_digest_no_name(self, agent, mock_digest_response):
        """Should generate weekly digest without user name."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_digest_response,
        ):
            request = WeeklyDigestRequest(food_logs=[FoodLog(dish_name="Ramen")])
            result = await agent.generate_weekly_digest_typed(request)

            assert isinstance(result, WeeklyDigestResult)

    @pytest.mark.asyncio
    async def test_generate_social_post_typed(self, agent, mock_social_response):
        """Should generate social post with typed response."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_social_response,
        ):
            request = SocialPostRequest(
                food_log=FoodLog(dish_name="Ramen"),
                platform="instagram",
                style="casual",
            )
            result = await agent.generate_social_post_typed(request)

            assert isinstance(result, SocialPostResult)
            assert result.platform == "instagram"
            assert "ramen" in result.content.caption.lower()

    @pytest.mark.asyncio
    async def test_generate_social_post_twitter(self, agent, mock_social_response):
        """Should handle Twitter platform limits."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_social_response,
        ):
            request = SocialPostRequest(
                food_log=FoodLog(dish_name="Ramen"),
                platform="twitter",
            )
            result = await agent.generate_social_post_typed(request)

            assert result.platform == "twitter"

    @pytest.mark.asyncio
    async def test_generate_social_post_facebook(self, agent, mock_social_response):
        """Should handle Facebook platform limits."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_social_response,
        ):
            request = SocialPostRequest(
                food_log=FoodLog(dish_name="Ramen"),
                platform="facebook",
            )
            result = await agent.generate_social_post_typed(request)

            assert result.platform == "facebook"

    @pytest.mark.asyncio
    async def test_generate_social_post_unknown_platform(self, agent, mock_social_response):
        """Should handle unknown platform with Instagram defaults."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_social_response,
        ):
            request = SocialPostRequest(
                food_log=FoodLog(dish_name="Ramen"),
                platform="tiktok",
            )
            result = await agent.generate_social_post_typed(request)

            assert result.platform == "tiktok"

    @pytest.mark.asyncio
    async def test_generate_food_story_typed(self, agent, mock_story_response):
        """Should generate food story with typed response."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_story_response,
        ):
            request = FoodStoryRequest(
                food_logs=[FoodLog(dish_name="Ramen"), FoodLog(dish_name="Sushi")],
                theme="adventure",
            )
            result = await agent.generate_food_story_typed(request)

            assert isinstance(result, FoodStoryResult)
            assert result.theme == "adventure"
            assert result.entry_count == 2

    @pytest.mark.asyncio
    async def test_generate_food_story_no_theme(self, agent, mock_story_response):
        """Should generate food story without theme."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_story_response,
        ):
            request = FoodStoryRequest(food_logs=[FoodLog(dish_name="Ramen")])
            result = await agent.generate_food_story_typed(request)

            assert result.theme is None

    @pytest.mark.asyncio
    async def test_generate_monthly_review_typed(self, agent, mock_review_response):
        """Should generate monthly review with typed response."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_review_response,
        ):
            request = MonthlyReviewRequest(
                food_logs=[FoodLog(dish_name="Ramen")],
                taste_profile=TasteProfile(top_cuisines=["Japanese"]),
            )
            result = await agent.generate_monthly_review_typed(request)

            assert isinstance(result, MonthlyReviewResult)
            assert result.period == "month"

    @pytest.mark.asyncio
    async def test_generate_monthly_review_no_profile(self, agent, mock_review_response):
        """Should generate monthly review without taste profile."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_review_response,
        ):
            request = MonthlyReviewRequest(food_logs=[FoodLog(dish_name="Ramen")])
            result = await agent.generate_monthly_review_typed(request)

            assert isinstance(result, MonthlyReviewResult)

    @pytest.mark.asyncio
    async def test_generate_recipe_card_typed(self, agent, mock_recipe_response):
        """Should generate recipe card with typed response."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_recipe_response,
        ):
            request = RecipeCardRequest(
                food_log=FoodLog(dish_name="Ramen"),
                include_instructions=True,
            )
            result = await agent.generate_recipe_card_typed(request)

            assert isinstance(result, RecipeCardResult)
            assert result.recipe_card.name == "Homemade Ramen"

    @pytest.mark.asyncio
    async def test_generate_recipe_card_no_instructions(self, agent, mock_recipe_response):
        """Should generate recipe card without instructions."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_recipe_response,
        ):
            request = RecipeCardRequest(
                food_log=FoodLog(dish_name="Ramen"),
                include_instructions=False,
            )
            result = await agent.generate_recipe_card_typed(request)

            assert isinstance(result, RecipeCardResult)

    @pytest.mark.asyncio
    async def test_generate_blog_post_typed(self, agent, mock_blog_response):
        """Should generate blog post with typed response."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_blog_response,
        ):
            request = BlogPostRequest(
                food_logs=[FoodLog(dish_name="Ramen", cuisine="Japanese")],
                theme="culinary_journey",
                style="conversational",
            )
            result = await agent.generate_blog_post_typed(request)

            assert isinstance(result, BlogPostResult)
            assert result.title == "My Culinary Journey"
            assert result.slug == "my-culinary-journey"

    @pytest.mark.asyncio
    async def test_generate_blog_post_generates_slug(self, agent):
        """Should generate slug from title if not provided."""
        mock_response = {
            "title": "My Amazing Food Blog",
            "content": "Content here",
            "excerpt": "",
            "metadata": {},
            "suggestions": [],
        }
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            request = BlogPostRequest(food_logs=[FoodLog(dish_name="Ramen")])
            result = await agent.generate_blog_post_typed(request)

            assert result.slug == "my-amazing-food-blog"

    @pytest.mark.asyncio
    async def test_generate_blog_post_non_dict_response(self, agent):
        """Should handle non-dict response for blog post."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value="invalid",
        ):
            request = BlogPostRequest(food_logs=[FoodLog(dish_name="Ramen")])
            result = await agent.generate_blog_post_typed(request)

            assert result.title == ""
            assert result.slug == "untitled"

    # Backward compatibility tests
    @pytest.mark.asyncio
    async def test_backward_compat_weekly_digest(self, agent, mock_digest_response):
        """Should work with dict interface."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_digest_response,
        ):
            result = await agent.generate_weekly_digest(
                food_logs=[{"dish_name": "Ramen"}],
                user_name="Bob",
            )

            assert isinstance(result, dict)
            assert result["user_id"] == "test_user"
            assert result["period"] == "week"

    @pytest.mark.asyncio
    async def test_backward_compat_social_post(self, agent, mock_social_response):
        """Should work with dict interface."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_social_response,
        ):
            result = await agent.generate_social_post(
                food_log={"dish_name": "Sushi"},
                platform="twitter",
                style="professional",
            )

            assert isinstance(result, dict)
            assert result["platform"] == "twitter"

    @pytest.mark.asyncio
    async def test_backward_compat_food_story(self, agent, mock_story_response):
        """Should work with dict interface."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_story_response,
        ):
            result = await agent.generate_food_story(
                food_logs=[{"dish_name": "Ramen"}],
                theme="comfort",
            )

            assert isinstance(result, dict)
            assert result["theme"] == "comfort"

    @pytest.mark.asyncio
    async def test_backward_compat_monthly_review(self, agent, mock_review_response):
        """Should work with dict interface."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_review_response,
        ):
            result = await agent.generate_monthly_review(
                food_logs=[{"dish_name": "Ramen"}],
                taste_profile={"top_cuisines": ["Japanese"]},
            )

            assert isinstance(result, dict)
            assert result["period"] == "month"

    @pytest.mark.asyncio
    async def test_backward_compat_recipe_card(self, agent, mock_recipe_response):
        """Should work with dict interface."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_recipe_response,
        ):
            result = await agent.generate_recipe_card(
                food_log={"dish_name": "Pasta"},
                include_instructions=True,
            )

            assert isinstance(result, dict)
            assert "recipe_card" in result

    @pytest.mark.asyncio
    async def test_backward_compat_blog_post(self, agent, mock_blog_response):
        """Should work with dict interface."""
        with patch(
            "fcp.agents.pydantic_agents.content_generator.gemini.generate_json_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_blog_response,
        ):
            result = await agent.generate_blog_post(
                food_logs=[{"dish_name": "Curry"}],
                theme="nutrition_focus",
                style="professional",
            )

            assert isinstance(result, dict)
            assert "title" in result


class TestHelperMethods:
    """Tests for helper methods."""

    @pytest.fixture
    def agent(self):
        return PydanticContentGeneratorAgent(user_id="test")

    def test_slugify_basic(self, agent):
        """Should slugify basic text."""
        assert agent._slugify("Hello World") == "hello-world"

    def test_slugify_special_chars(self, agent):
        """Should remove special characters."""
        assert agent._slugify("Hello! World?") == "hello-world"

    def test_slugify_empty(self, agent):
        """Should handle empty text."""
        assert agent._slugify("") == "untitled"
        assert agent._slugify(None) == "untitled"

    def test_slugify_long_text(self, agent):
        """Should truncate long slugs."""
        long_text = "a" * 200
        result = agent._slugify(long_text)
        assert len(result) <= 100

    def test_slugify_multiple_spaces(self, agent):
        """Should handle multiple spaces."""
        assert agent._slugify("Hello    World") == "hello-world"

    def test_parse_content_safely_valid(self, agent):
        """Should parse valid content."""
        data = {"title": "Test", "subtitle": "Sub"}
        result = agent._parse_content_safely(data, DigestContent)
        assert result.title == "Test"

    def test_parse_content_safely_invalid(self, agent):
        """Should return empty model for invalid data."""
        result = agent._parse_content_safely("not a dict", DigestContent)
        assert result.title == ""

    def test_parse_content_safely_validation_error(self, agent):
        """Should return empty model when validation fails."""
        # DigestStats.total_meals expects int, passing a dict forces validation error
        data = {"total_meals": {"invalid": "not_int"}}
        result = agent._parse_content_safely(data, DigestStats)
        # Should fall back to empty model
        assert result.total_meals == 0


class TestContentModelDefaults:
    """Tests for content model defaults."""

    def test_digest_highlight_defaults(self):
        """Should have empty defaults."""
        highlight = DigestHighlight()
        assert highlight.dish == ""
        assert highlight.story == ""

    def test_digest_stats_defaults(self):
        """Should have zero defaults."""
        stats = DigestStats()
        assert stats.total_meals == 0
        assert stats.cuisines == 0

    def test_digest_content_defaults(self):
        """Should have nested defaults."""
        content = DigestContent()
        assert content.title == ""
        assert isinstance(content.highlight, DigestHighlight)
        assert isinstance(content.stats, DigestStats)

    def test_social_post_content_defaults(self):
        """Should have empty defaults."""
        content = SocialPostContent()
        assert content.caption == ""
        assert content.hashtags == []

    def test_story_content_defaults(self):
        """Should have empty defaults."""
        content = StoryContent()
        assert content.title == ""
        assert content.word_count == 0

    def test_monthly_review_content_defaults(self):
        """Should have empty defaults."""
        content = MonthlyReviewContent()
        assert content.title == ""
        assert content.top_meals == []

    def test_recipe_card_content_defaults(self):
        """Should have empty defaults."""
        content = RecipeCardContent()
        assert content.name == ""
        assert content.ingredients == []
