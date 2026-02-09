"""Pydantic AI-based agents for FoodLog.

This module provides type-safe, structured agents using Pydantic AI framework.
These agents offer the same functionality as the original agents but with:
- Type-safe inputs and outputs via Pydantic models
- Automatic Logfire tracing integration
- Cleaner separation of concerns

Available agents:
- PydanticDiscoveryAgent: Food discovery with structured recommendations
- PydanticFreshnessAgent: Daily insights, streaks, tips, and achievements
- PydanticContentGeneratorAgent: Shareable content generation
- PydanticMediaProcessingAgent: Camera roll and photo batch processing
"""

from fcp.agents.pydantic_agents.content_generator import (
    BlogPostResult,
    FoodStoryResult,
    MonthlyReviewResult,
    PydanticContentGeneratorAgent,
    RecipeCardResult,
    SocialPostResult,
    WeeklyDigestResult,
)
from fcp.agents.pydantic_agents.discovery import (
    DiscoveryResult,
    PydanticDiscoveryAgent,
    Recommendation,
    TasteProfile,
)
from fcp.agents.pydantic_agents.freshness import (
    DailyInsightResult,
    FoodTipResult,
    PydanticFreshnessAgent,
    SeasonalReminderResult,
    StreakCelebrationResult,
)
from fcp.agents.pydantic_agents.media_processor import (
    FilterImagesResult,
    FilterPhotosResult,
    MealSequenceResult,
    PhotoAnalysis,
    PhotoBatchResult,
    PydanticMediaProcessingAgent,
)

__all__ = [
    "PydanticDiscoveryAgent",
    "TasteProfile",
    "Recommendation",
    "DiscoveryResult",
    "PydanticFreshnessAgent",
    "DailyInsightResult",
    "StreakCelebrationResult",
    "FoodTipResult",
    "SeasonalReminderResult",
    "PydanticContentGeneratorAgent",
    "WeeklyDigestResult",
    "SocialPostResult",
    "FoodStoryResult",
    "MonthlyReviewResult",
    "RecipeCardResult",
    "BlogPostResult",
    "PydanticMediaProcessingAgent",
    "PhotoBatchResult",
    "PhotoAnalysis",
    "FilterImagesResult",
    "FilterPhotosResult",
    "MealSequenceResult",
]
