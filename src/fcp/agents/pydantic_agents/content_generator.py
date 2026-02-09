"""Pydantic AI-based Content Generator Agent.

This agent generates shareable content from food logs with type-safe models:
- Weekly digests
- Social media posts
- Blog content (SEO-optimized)
- Food stories
- Recipe cards
- Monthly reviews

Uses extended thinking for creative content generation.
"""

import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from fcp.prompts import PROMPTS
from fcp.services.gemini import GeminiClient, gemini

# ============================================================================
# Pydantic Models for Type-Safe Inputs
# ============================================================================


class FoodLog(BaseModel):
    """A food log entry."""

    dish_name: str = Field(default="")
    cuisine: str = Field(default="")
    created_at: str = Field(default="")
    venue_name: str = Field(default="")
    ai_description: str = Field(default="")
    nutrition: dict[str, Any] = Field(default_factory=dict)
    nutrition_info: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class TasteProfile(BaseModel):
    """User's taste preferences."""

    top_cuisines: list[str] = Field(default_factory=list)
    spice_preference: str = Field(default="medium")
    dietary_restrictions: list[str] = Field(default_factory=list)
    favorite_dishes: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump(exclude_none=True)


class WeeklyDigestRequest(BaseModel):
    """Request parameters for weekly digest generation."""

    food_logs: list[FoodLog]
    user_name: str | None = Field(default=None, description="User name for personalization")


class SocialPostRequest(BaseModel):
    """Request parameters for social media post generation."""

    food_log: FoodLog
    platform: str = Field(default="instagram", description="Target platform")
    style: str = Field(default="casual", description="Writing style")


class FoodStoryRequest(BaseModel):
    """Request parameters for food story generation."""

    food_logs: list[FoodLog]
    theme: str | None = Field(default=None, description="Story theme")


class MonthlyReviewRequest(BaseModel):
    """Request parameters for monthly review generation."""

    food_logs: list[FoodLog]
    taste_profile: TasteProfile | None = Field(default=None)


class RecipeCardRequest(BaseModel):
    """Request parameters for recipe card generation."""

    food_log: FoodLog
    include_instructions: bool = Field(default=True)


class BlogPostRequest(BaseModel):
    """Request parameters for blog post generation."""

    food_logs: list[FoodLog]
    theme: str = Field(default="culinary_journey")
    style: str = Field(default="conversational")


# ============================================================================
# Pydantic Models for Type-Safe Outputs
# ============================================================================


class DigestHighlight(BaseModel):
    """Highlight from a weekly digest."""

    dish: str = Field(default="")
    story: str = Field(default="")
    image_url: str = Field(default="")

    model_config = ConfigDict(extra="allow")


class DigestStats(BaseModel):
    """Statistics for a weekly digest."""

    total_meals: int = Field(default=0)
    cuisines: int = Field(default=0)
    new_dishes: int = Field(default=0)

    model_config = ConfigDict(extra="allow")


class DigestContent(BaseModel):
    """Content of a weekly digest."""

    title: str = Field(default="")
    subtitle: str = Field(default="")
    week_summary: str = Field(default="")
    highlight: DigestHighlight = Field(default_factory=DigestHighlight)
    stats: DigestStats = Field(default_factory=DigestStats)
    best_moments: list[dict[str, Any]] = Field(default_factory=list)
    suggestion: str = Field(default="")

    model_config = ConfigDict(extra="allow")


class WeeklyDigestResult(BaseModel):
    """Result from weekly digest generation."""

    user_id: str
    period: str = "week"
    entry_count: int
    digest: DigestContent


class SocialPostContent(BaseModel):
    """Content of a social media post."""

    caption: str = Field(default="")
    hashtags: list[str] = Field(default_factory=list)
    posting_tips: str = Field(default="")
    character_count: int = Field(default=0)

    model_config = ConfigDict(extra="allow")


class SocialPostResult(BaseModel):
    """Result from social post generation."""

    platform: str
    style: str
    content: SocialPostContent


class StoryContent(BaseModel):
    """Content of a food story."""

    title: str = Field(default="")
    story: str = Field(default="")
    featured_dishes: list[str] = Field(default_factory=list)
    mood: str = Field(default="")
    word_count: int = Field(default=0)

    model_config = ConfigDict(extra="allow")


class FoodStoryResult(BaseModel):
    """Result from food story generation."""

    user_id: str
    theme: str | None
    entry_count: int
    story: StoryContent


class MonthlyReviewContent(BaseModel):
    """Content of a monthly review."""

    title: str = Field(default="")
    summary: str = Field(default="")
    top_meals: list[dict[str, Any]] = Field(default_factory=list)
    cuisine_breakdown: dict[str, Any] = Field(default_factory=dict)
    discoveries: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")


class MonthlyReviewResult(BaseModel):
    """Result from monthly review generation."""

    user_id: str
    period: str = "month"
    entry_count: int
    review: MonthlyReviewContent


class RecipeCardContent(BaseModel):
    """Content of a recipe card."""

    name: str = Field(default="")
    description: str = Field(default="")
    prep_time: str = Field(default="")
    cook_time: str = Field(default="")
    servings: int = Field(default=0)
    difficulty: str = Field(default="")
    cuisine: str = Field(default="")
    ingredients: list[str] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)
    tips: list[str] = Field(default_factory=list)
    variations: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class RecipeCardResult(BaseModel):
    """Result from recipe card generation."""

    source_log: str | None
    recipe_card: RecipeCardContent


class BlogPostContent(BaseModel):
    """Content of a blog post."""

    title: str = Field(default="")
    slug: str = Field(default="")
    content: str = Field(default="")
    excerpt: str = Field(default="")
    metadata: dict[str, Any] = Field(default_factory=dict)
    suggestions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class BlogPostResult(BaseModel):
    """Result from blog post generation."""

    title: str
    slug: str
    content: str
    excerpt: str
    metadata: dict[str, Any]
    suggestions: list[str]


# ============================================================================
# Pydantic AI Content Generator Agent
# ============================================================================


class PydanticContentGeneratorAgent:
    """Type-safe content generator agent using Pydantic models.

    This agent wraps the Gemini API with extended thinking support and provides
    type-safe inputs and outputs via Pydantic models. It's designed to be a
    drop-in replacement for the original ContentGeneratorAgent.

    Usage:
        agent = PydanticContentGeneratorAgent(user_id="user123")

        # Using Pydantic models
        request = WeeklyDigestRequest(
            food_logs=[FoodLog(dish_name="Pizza")],
            user_name="Alice",
        )
        result = await agent.generate_weekly_digest_typed(request)

        # Or with raw dict (for backward compatibility)
        result = await agent.generate_weekly_digest(
            food_logs=[{"dish_name": "Pizza"}],
            user_name="Alice",
        )
    """

    def __init__(self, user_id: str, gemini: GeminiClient | None = None):
        self.user_id = user_id
        self._gemini = gemini

    def _gemini_client(self) -> GeminiClient:
        return self._gemini or gemini

    def _slugify(self, text: str | None) -> str:
        """Convert text to URL-safe slug."""
        if not text:
            return "untitled"
        slug = text.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_-]+", "-", slug)
        return slug.strip("-")[:100]

    def _parse_content_safely(self, data: Any, model_class: type) -> Any:
        """Safely parse content into a Pydantic model."""
        if isinstance(data, dict):
            try:
                return model_class.model_validate(data)
            except Exception:
                return model_class()
        return model_class()

    # ========================================================================
    # Type-safe API using Pydantic models
    # ========================================================================

    async def generate_weekly_digest_typed(self, request: WeeklyDigestRequest) -> WeeklyDigestResult:
        """Generate a weekly food digest with type-safe request/response."""
        name_context = f"for {request.user_name}" if request.user_name else ""
        food_logs_data = [log.model_dump() for log in request.food_logs]

        prompt = f"""Create an engaging weekly food digest {name_context}.

THIS WEEK'S MEALS ({len(request.food_logs)} entries):
{json.dumps(food_logs_data, indent=2)}

Generate a fun, shareable weekly digest that includes:

1. CATCHY TITLE
   - Something engaging like "A Week of Culinary Adventures"

2. WEEK AT A GLANCE
   - Total meals logged
   - Cuisine variety
   - Most adventurous dish
   - Comfort food moment

3. HIGHLIGHT OF THE WEEK
   - Pick the most interesting/delicious meal
   - Write a short story about it

4. BY THE NUMBERS
   - Fun statistics (cuisines tried, new dishes, etc.)
   - Visualize with emojis if appropriate

5. BEST MOMENTS
   - 2-3 memorable meals with brief descriptions

6. COMING UP
   - Based on patterns, suggest what to try next week

Make it personal, fun, and shareable. Use a warm, food-loving tone.

Return as JSON:
{{
    "title": "...",
    "subtitle": "...",
    "week_summary": "...",
    "highlight": {{"dish": "...", "story": "...", "image_url": "..."}},
    "stats": {{"total_meals": N, "cuisines": N, "new_dishes": N, ...}},
    "best_moments": [...],
    "suggestion": "..."
}}"""

        result = await self._gemini_client().generate_json_with_thinking(
            prompt=prompt,
            thinking_level="high",
        )

        digest = self._parse_content_safely(result, DigestContent)

        return WeeklyDigestResult(
            user_id=self.user_id,
            period="week",
            entry_count=len(request.food_logs),
            digest=digest,
        )

    async def generate_social_post_typed(self, request: SocialPostRequest) -> SocialPostResult:
        """Generate a social media post with type-safe request/response."""
        platform_limits = {
            "instagram": {"caption": 2200, "hashtags": 30},
            "twitter": {"caption": 280, "hashtags": 5},
            "facebook": {"caption": 500, "hashtags": 10},
        }
        limits = platform_limits.get(request.platform, platform_limits["instagram"])
        food_log_data = request.food_log.model_dump()

        prompt = f"""Create a {request.platform} post for this meal.

MEAL DETAILS:
{json.dumps(food_log_data, indent=2)}

PLATFORM: {request.platform}
STYLE: {request.style}
CHARACTER LIMIT: {limits["caption"]}
MAX HASHTAGS: {limits["hashtags"]}

Generate:
1. CAPTION
   - Engaging, matches the {request.style} style
   - Within character limit
   - Includes a hook and description

2. HASHTAGS
   - Relevant food hashtags
   - Mix of popular and niche
   - Platform-appropriate count

3. POSTING TIPS
   - Best time to post
   - Engagement suggestions

Return as JSON:
{{
    "caption": "...",
    "hashtags": ["...", "..."],
    "posting_tips": "...",
    "character_count": N
}}"""

        result = await self._gemini_client().generate_json_with_thinking(
            prompt=prompt,
            thinking_level="medium",
        )

        content = self._parse_content_safely(result, SocialPostContent)

        return SocialPostResult(
            platform=request.platform,
            style=request.style,
            content=content,
        )

    async def generate_food_story_typed(self, request: FoodStoryRequest) -> FoodStoryResult:
        """Generate a narrative food story with type-safe request/response."""
        theme_context = f" with a '{request.theme}' theme" if request.theme else ""
        food_logs_data = [log.model_dump() for log in request.food_logs]

        prompt = f"""Create a food story{theme_context} from these meals.

MEALS TO INCLUDE:
{json.dumps(food_logs_data, indent=2)}

Write an engaging narrative that:
1. Connects the meals into a cohesive story
2. Highlights the culinary journey
3. Includes sensory descriptions (taste, smell, texture)
4. Captures the emotional moments
5. Has a satisfying conclusion

Structure:
- Opening hook
- Rising action (building meals)
- Climax (best meal moment)
- Resolution (what was learned/felt)

Return as JSON:
{{
    "title": "...",
    "story": "...",
    "featured_dishes": ["...", "..."],
    "mood": "...",
    "word_count": N
}}"""

        result = await self._gemini_client().generate_json_with_thinking(
            prompt=prompt,
            thinking_level="high",
        )

        story = self._parse_content_safely(result, StoryContent)

        return FoodStoryResult(
            user_id=self.user_id,
            theme=request.theme,
            entry_count=len(request.food_logs),
            story=story,
        )

    async def generate_monthly_review_typed(self, request: MonthlyReviewRequest) -> MonthlyReviewResult:
        """Generate a comprehensive monthly food review with type-safe request/response."""
        food_logs_data = [log.model_dump() for log in request.food_logs]
        profile_context = ""
        if request.taste_profile:
            profile_context = f"""
TASTE PROFILE:
{json.dumps(request.taste_profile.to_dict(), indent=2)}
Reference this to highlight growth and patterns."""

        prompt = f"""Create a comprehensive monthly food review.

THIS MONTH'S MEALS ({len(request.food_logs)} entries):
{json.dumps(food_logs_data, indent=2)}
{profile_context}

Generate a shareable monthly review:

1. MONTH TITLE
   - Creative title summarizing the month

2. EXECUTIVE SUMMARY
   - 2-3 sentence overview

3. TOP 5 MEALS
   - Ranked list with brief descriptions

4. CUISINE BREAKDOWN
   - What cuisines dominated
   - Any new cuisines tried

5. DISCOVERIES
   - New restaurants found
   - New dishes tried
   - Surprising favorites

6. PATTERNS
   - What you ate most
   - Time patterns
   - Mood-food connections

7. GOALS FOR NEXT MONTH
   - Based on this month, suggest goals

8. SHAREABLE STATS
   - Fun statistics in quotable format

Return as JSON with these sections."""

        result = await self._gemini_client().generate_json_with_thinking(
            prompt=prompt,
            thinking_level="high",
        )

        review = self._parse_content_safely(result, MonthlyReviewContent)

        return MonthlyReviewResult(
            user_id=self.user_id,
            period="month",
            entry_count=len(request.food_logs),
            review=review,
        )

    async def generate_recipe_card_typed(self, request: RecipeCardRequest) -> RecipeCardResult:
        """Generate a shareable recipe card with type-safe request/response."""
        food_log_data = request.food_log.model_dump()
        instructions_request = ""
        if request.include_instructions:
            instructions_request = """
5. INSTRUCTIONS
   - Step-by-step cooking instructions
   - Estimated based on the dish type"""

        prompt = f"""Create a recipe card from this logged meal.

MEAL:
{json.dumps(food_log_data, indent=2)}

Generate a beautiful, shareable recipe card:

1. RECIPE NAME
   - Attractive name for the dish

2. DESCRIPTION
   - Appetizing 2-sentence description

3. QUICK INFO
   - Prep time, cook time, servings
   - Difficulty level
   - Cuisine type

4. INGREDIENTS
   - List with amounts (estimate if needed)
   - Organized by category
{instructions_request}

6. CHEF'S TIPS
   - 2-3 tips for best results

7. VARIATIONS
   - Alternative ingredients or methods

Return as JSON formatted for a recipe card."""

        result = await self._gemini_client().generate_json_with_thinking(
            prompt=prompt,
            thinking_level="medium",
        )

        recipe_card = self._parse_content_safely(result, RecipeCardContent)

        return RecipeCardResult(
            source_log=request.food_log.model_dump().get("id"),
            recipe_card=recipe_card,
        )

    async def generate_blog_post_typed(self, request: BlogPostRequest) -> BlogPostResult:
        """Generate an SEO-optimized blog post with type-safe request/response."""
        log_summaries = [
            {
                "dish": log.dish_name or "Unknown dish",
                "cuisine": log.cuisine or "Unknown",
                "date": log.created_at,
                "highlights": log.ai_description,
                "nutrition": log.nutrition or log.nutrition_info,
                "venue": log.venue_name,
            }
            for log in request.food_logs
        ]

        prompt = PROMPTS["generate_blog_post"].format(
            logs=json.dumps(log_summaries, indent=2),
            theme=request.theme,
            style=request.style,
        )

        result = await self._gemini_client().generate_json_with_thinking(
            prompt=prompt,
            thinking_level="high",
        )

        if not isinstance(result, dict):
            result = {}

        # Generate slug from title if not provided
        title = result.get("title", "")
        slug = result.get("slug", "") or self._slugify(title)

        return BlogPostResult(
            title=title,
            slug=slug,
            content=result.get("content", ""),
            excerpt=result.get("excerpt", ""),
            metadata=result.get("metadata", {}),
            suggestions=result.get("suggestions", []),
        )

    # ========================================================================
    # Backward-compatible API (dict inputs, dict outputs)
    # ========================================================================

    async def generate_weekly_digest(
        self,
        food_logs: list[dict],
        user_name: str | None = None,
    ) -> dict[str, Any]:
        """Generate a weekly food digest with dict interface (backward compatible)."""
        request = WeeklyDigestRequest(
            food_logs=[FoodLog(**log) if isinstance(log, dict) else log for log in food_logs],
            user_name=user_name,
        )
        result = await self.generate_weekly_digest_typed(request)
        return {
            "user_id": result.user_id,
            "period": result.period,
            "entry_count": result.entry_count,
            "digest": result.digest.model_dump(),
        }

    async def generate_social_post(
        self,
        food_log: dict,
        platform: str = "instagram",
        style: str = "casual",
    ) -> dict[str, Any]:
        """Generate a social media post with dict interface (backward compatible)."""
        request = SocialPostRequest(
            food_log=FoodLog(**food_log) if isinstance(food_log, dict) else food_log,
            platform=platform,
            style=style,
        )
        result = await self.generate_social_post_typed(request)
        return {
            "platform": result.platform,
            "style": result.style,
            "content": result.content.model_dump(),
        }

    async def generate_food_story(
        self,
        food_logs: list[dict],
        theme: str | None = None,
    ) -> dict[str, Any]:
        """Generate a narrative food story with dict interface (backward compatible)."""
        request = FoodStoryRequest(
            food_logs=[FoodLog(**log) if isinstance(log, dict) else log for log in food_logs],
            theme=theme,
        )
        result = await self.generate_food_story_typed(request)
        return {
            "user_id": result.user_id,
            "theme": result.theme,
            "entry_count": result.entry_count,
            "story": result.story.model_dump(),
        }

    async def generate_monthly_review(
        self,
        food_logs: list[dict],
        taste_profile: dict | None = None,
    ) -> dict[str, Any]:
        """Generate a comprehensive monthly food review with dict interface (backward compatible)."""
        request = MonthlyReviewRequest(
            food_logs=[FoodLog(**log) if isinstance(log, dict) else log for log in food_logs],
            taste_profile=TasteProfile(**taste_profile) if taste_profile else None,
        )
        result = await self.generate_monthly_review_typed(request)
        return {
            "user_id": result.user_id,
            "period": result.period,
            "entry_count": result.entry_count,
            "review": result.review.model_dump(),
        }

    async def generate_recipe_card(
        self,
        food_log: dict,
        include_instructions: bool = True,
    ) -> dict[str, Any]:
        """Generate a shareable recipe card with dict interface (backward compatible)."""
        request = RecipeCardRequest(
            food_log=FoodLog(**food_log) if isinstance(food_log, dict) else food_log,
            include_instructions=include_instructions,
        )
        result = await self.generate_recipe_card_typed(request)
        return {
            "source_log": result.source_log,
            "recipe_card": result.recipe_card.model_dump(),
        }

    async def generate_blog_post(
        self,
        food_logs: list[dict],
        theme: str = "culinary_journey",
        style: str = "conversational",
    ) -> dict[str, Any]:
        """Generate an SEO-optimized blog post with dict interface (backward compatible)."""
        request = BlogPostRequest(
            food_logs=[FoodLog(**log) if isinstance(log, dict) else log for log in food_logs],
            theme=theme,
            style=style,
        )
        result = await self.generate_blog_post_typed(request)
        return result.model_dump()
