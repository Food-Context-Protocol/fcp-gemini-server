"""Agents Routes.

Autonomous AI agent endpoints:
- /agents/delegate - Delegate to food agent
- /agents/discover - Food discovery agent
- /agents/discover/restaurants - Restaurant discovery
- /agents/discover/recipes - Recipe discovery
- /agents/daily-insight - Daily personalized insights
- /agents/streak/{streak_days} - Streak celebrations
- /agents/food-tip - Daily food tips
- /agents/seasonal-reminder - Seasonal recommendations
- /agents/process-media - Batch photo processing
    - /agents/filter-food-images - Filter food images
- /agents/generate-blog - Weekly food digest
- /agents/social-post - Social media posts
- /agents/food-story - Narrative food stories
- /agents/monthly-review - Monthly reviews
- /agents/recipe-card - Recipe cards
"""

from typing import Any

from fastapi import Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from fcp.agents import ContentGeneratorAgent, FoodDiscoveryAgent, FreshnessAgent, MediaProcessingAgent
from fcp.auth import AuthenticatedUser, get_current_user, require_write_access
from fcp.routes.router import APIRouter
from fcp.security.rate_limit import RATE_LIMIT_ANALYZE, RATE_LIMIT_PROFILE, RATE_LIMIT_SUGGEST, limiter
from fcp.tools import delegate_to_food_agent, get_meal, get_meals, get_taste_profile

router = APIRouter()


# --- Request Models ---


class DelegateAgentRequest(BaseModel):
    agent_name: str
    objective: str


class DiscoveryRequest(BaseModel):
    location: str | None = Field(default=None, max_length=200)
    discovery_type: str = Field(default="all", pattern=r"^(restaurant|recipe|ingredient|all)$")
    count: int = Field(default=5, ge=1, le=10)


class RestaurantDiscoveryRequest(BaseModel):
    location: str = Field(..., min_length=1, max_length=200)
    occasion: str | None = Field(default=None, max_length=100)


class RecipeDiscoveryRequest(BaseModel):
    available_ingredients: list[str] | None = Field(default=None)
    dietary_restrictions: list[str] | None = Field(default=None)


class MediaBatchRequest(BaseModel):
    image_urls: list[str] = Field(..., min_length=1, max_length=20)
    auto_log: bool = Field(default=False)


class FilterImagesRequest(BaseModel):
    image_urls: list[str] = Field(..., min_length=1, max_length=50)
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class SocialPostRequest(BaseModel):
    log_id: str = Field(..., min_length=1, max_length=100)
    platform: str = Field(default="instagram", pattern=r"^(instagram|twitter|facebook)$")
    style: str = Field(default="casual", pattern=r"^(casual|foodie|professional)$")


class FoodStoryRequest(BaseModel):
    log_ids: list[str] = Field(..., min_length=1, max_length=10)
    theme: str | None = Field(default=None, max_length=100)


class RecipeCardRequest(BaseModel):
    log_id: str = Field(..., min_length=1, max_length=100)
    include_instructions: bool = Field(default=True)


# Backward compatible alias.
FilterPhotosRequest = FilterImagesRequest


# --- Routes ---


@router.post("/agents/delegate")
async def post_delegate_to_agent(
    delegate_request: DelegateAgentRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Handoff a complex food-related task to a specialized agent."""
    from fcp.services.firestore import get_firestore_client

    db = get_firestore_client()
    context = await db.get_user_preferences(user.user_id)
    return await delegate_to_food_agent(delegate_request.agent_name, delegate_request.objective, context)


@router.post("/agents/discover")
@limiter.limit(RATE_LIMIT_SUGGEST)
async def run_food_discovery(
    request: Request,
    discovery_request: DiscoveryRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """
    Run autonomous food discovery agent.

    Combines:
    - Google Search grounding for real-time data
    - Extended thinking for preference matching
    - Function calling for structured recommendations
    """
    # Get user's taste profile
    profile = await get_taste_profile(user.user_id)

    agent = FoodDiscoveryAgent(user.user_id)
    return await agent.run_discovery(
        taste_profile=profile,
        location=discovery_request.location,
        discovery_type=discovery_request.discovery_type,
        count=discovery_request.count,
    )


@router.post("/agents/discover/restaurants")
@limiter.limit(RATE_LIMIT_SUGGEST)
async def discover_restaurants(
    request: Request,
    discovery_request: RestaurantDiscoveryRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """
    Discover new restaurants matching user preferences.
    """
    profile = await get_taste_profile(user.user_id)
    agent = FoodDiscoveryAgent(user.user_id)
    return await agent.discover_restaurants(
        taste_profile=profile,
        location=discovery_request.location,
        occasion=discovery_request.occasion,
    )


@router.post("/agents/discover/recipes")
@limiter.limit(RATE_LIMIT_SUGGEST)
async def discover_recipes(
    request: Request,
    discovery_request: RecipeDiscoveryRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """
    Discover new recipes based on preferences and available ingredients.
    """
    profile = await get_taste_profile(user.user_id)
    agent = FoodDiscoveryAgent(user.user_id)
    return await agent.discover_recipes(
        taste_profile=profile,
        available_ingredients=discovery_request.available_ingredients,
        dietary_restrictions=discovery_request.dietary_restrictions,
    )


@router.get("/agents/daily-insight")
@limiter.limit(RATE_LIMIT_PROFILE)
async def get_daily_insight(
    request: Request,
    location: str | None = Query(default=None, max_length=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get today's personalized food insight.

    Uses grounding for timely, relevant content:
    - What's in season
    - Food holidays
    - Weather-appropriate suggestions
    """
    profile = await get_taste_profile(user.user_id)
    recent_logs = await get_meals(user.user_id, days=7)

    agent = FreshnessAgent(user.user_id)
    return await agent.generate_daily_insight(
        taste_profile=profile,
        recent_logs=recent_logs,
        location=location,
    )


@router.get("/agents/streak/{streak_days}")
@limiter.limit(RATE_LIMIT_PROFILE)
async def get_streak_celebration(
    request: Request,
    streak_days: int,
    user_name: str | None = Query(default=None, max_length=100),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Generate a celebration message for a logging streak.
    """
    agent = FreshnessAgent(user.user_id)
    return await agent.generate_streak_celebration(
        streak_days=streak_days,
        user_name=user_name,
    )


@router.get("/agents/food-tip")
@limiter.limit(RATE_LIMIT_PROFILE)
async def get_food_tip(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get today's food tip based on user preferences.

    Uses grounding for fresh, relevant tips.
    """
    profile = await get_taste_profile(user.user_id)
    agent = FreshnessAgent(user.user_id)
    return await agent.generate_food_tip_of_day(taste_profile=profile)


@router.get("/agents/seasonal-reminder")
@limiter.limit(RATE_LIMIT_PROFILE)
async def get_seasonal_reminder(
    request: Request,
    location: str = Query(..., min_length=1, max_length=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get seasonal food recommendations for a location.
    """
    profile = await get_taste_profile(user.user_id)
    agent = FreshnessAgent(user.user_id)
    return await agent.generate_seasonal_reminder(
        location=location,
        taste_profile=profile,
    )


@router.post("/agents/process-media")
@limiter.limit(RATE_LIMIT_ANALYZE)
async def process_media_batch(
    request: Request,
    media_request: MediaBatchRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """
    Process a batch of photos to detect and analyze food.

    Uses:
    - Multimodal analysis for food detection
    - Function calling for structured extraction
    """
    agent = MediaProcessingAgent()
    return await agent.process_photo_batch(
        image_urls=media_request.image_urls,
        auto_log=media_request.auto_log,
    )


@router.post("/agents/filter-food-images")
@router.post("/agents/filter-food-photos")
@limiter.limit(RATE_LIMIT_ANALYZE)
async def filter_food_images(
    request: Request,
    filter_request: FilterImagesRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """
    Filter images to identify which contain food.

    Faster than full analysis - only checks food presence.
    """
    agent = MediaProcessingAgent()
    return await agent.filter_food_images(
        image_urls=filter_request.image_urls,
        confidence_threshold=filter_request.confidence_threshold,
    )


@router.post("/agents/generate-blog")
@limiter.limit(RATE_LIMIT_PROFILE)
async def generate_blog_content(
    request: Request,
    user_name: str | None = Query(default=None, max_length=100),
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """
    Generate a shareable weekly food digest.

    Uses extended thinking for creative content generation.
    """
    food_logs = await get_meals(user.user_id, days=7)
    agent = ContentGeneratorAgent(user.user_id)
    return await agent.generate_weekly_digest(
        food_logs=food_logs,
        user_name=user_name,
    )


@router.post("/agents/social-post")
@limiter.limit(RATE_LIMIT_PROFILE)
async def create_social_post(
    request: Request,
    post_request: SocialPostRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Generate a social media post."""
    meal = await get_meal(user.user_id, post_request.log_id)
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")

    agent = ContentGeneratorAgent(user.user_id)
    return await agent.generate_social_post(
        food_log=meal,
        platform=post_request.platform,
        style=post_request.style,
    )


@router.post("/agents/food-story")
@limiter.limit(RATE_LIMIT_PROFILE)
async def generate_food_story(
    request: Request,
    story_request: FoodStoryRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """
    Generate a narrative food story from multiple meals.
    """
    # Fetch all requested meals
    food_logs = []
    for log_id in story_request.log_ids:
        meal = await get_meal(user.user_id, log_id)
        if meal:
            food_logs.append(meal)

    if not food_logs:
        raise HTTPException(status_code=404, detail="No meals found")

    agent = ContentGeneratorAgent(user.user_id)
    return await agent.generate_food_story(
        food_logs=food_logs,
        theme=story_request.theme,
    )


@router.get("/agents/monthly-review")
@limiter.limit(RATE_LIMIT_PROFILE)
async def generate_monthly_review(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Generate a comprehensive monthly food review.
    """
    food_logs = await get_meals(user.user_id, days=30)
    profile = await get_taste_profile(user.user_id)

    agent = ContentGeneratorAgent(user.user_id)
    return await agent.generate_monthly_review(
        food_logs=food_logs,
        taste_profile=profile,
    )


@router.post("/agents/recipe-card")
@limiter.limit(RATE_LIMIT_PROFILE)
async def generate_recipe_card(
    request: Request,
    card_request: RecipeCardRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """
    Generate a shareable recipe card from a logged meal.
    """
    meal = await get_meal(user.user_id, card_request.log_id)
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")

    agent = ContentGeneratorAgent(user.user_id)
    return await agent.generate_recipe_card(
        food_log=meal,
        include_instructions=card_request.include_instructions,
    )
