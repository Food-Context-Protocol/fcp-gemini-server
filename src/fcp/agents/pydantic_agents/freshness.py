"""Pydantic AI-based Freshness Agent.

This agent provides the same functionality as the original FreshnessAgent
but with type-safe Pydantic models for inputs and outputs.

Features:
- Daily personalized insights with grounding
- Streak celebrations with milestone tiers
- Food tips and seasonal reminders
- Achievement notifications
"""

import json
from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from fcp.services.gemini import GeminiClient, gemini

# ============================================================================
# Pydantic Models for Type-Safe Inputs
# ============================================================================


class TasteProfile(BaseModel):
    """User's taste preferences for personalization."""

    top_cuisines: list[str] = Field(default_factory=list)
    spice_preference: str = Field(default="medium")
    dietary_restrictions: list[str] = Field(default_factory=list)
    favorite_dishes: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class FoodLog(BaseModel):
    """A food log entry."""

    dish_name: str = Field(default="")
    cuisine: str = Field(default="")
    created_at: str = Field(default="")
    venue_name: str | None = None
    notes: str | None = None

    model_config = ConfigDict(extra="allow")


class DailyInsightRequest(BaseModel):
    """Request for daily insight generation."""

    taste_profile: TasteProfile
    recent_logs: list[FoodLog] = Field(default_factory=list)
    location: str | None = None


class StreakCelebrationRequest(BaseModel):
    """Request for streak celebration message."""

    streak_days: int = Field(ge=1, description="Consecutive days logged")
    user_name: str | None = None


class WeeklyTeaserRequest(BaseModel):
    """Request for weekly summary teaser."""

    food_logs: list[FoodLog] = Field(default_factory=list)


class MealReminderRequest(BaseModel):
    """Request for meal reminder."""

    meal_type: str = Field(description="breakfast, lunch, dinner, or snack")
    taste_profile: TasteProfile
    last_meal_hours_ago: float = Field(ge=0)


class AchievementRequest(BaseModel):
    """Request for achievement unlock content."""

    achievement_type: str = Field(description="Type of achievement unlocked")
    achievement_data: dict[str, Any] = Field(default_factory=dict)


class FoodTipRequest(BaseModel):
    """Request for food tip of the day."""

    taste_profile: TasteProfile


class SeasonalReminderRequest(BaseModel):
    """Request for seasonal food reminder."""

    location: str = Field(description="User's location")
    taste_profile: TasteProfile


# ============================================================================
# Pydantic Models for Type-Safe Outputs
# ============================================================================


class GroundingSource(BaseModel):
    """Source from Google Search grounding."""

    uri: str = Field(default="")
    title: str = Field(default="")


class DailyInsightResult(BaseModel):
    """Result from daily insight generation."""

    user_id: str
    date: str
    insight: str
    sources: list[GroundingSource] = Field(default_factory=list)
    type: str = "daily_insight"


class CelebrationContent(BaseModel):
    """Content for streak celebration."""

    headline: str = Field(default="")
    message: str = Field(default="")
    achievement_name: str = Field(default="")
    achievement_description: str = Field(default="")
    encouragement: str = Field(default="")
    fun_fact: str = Field(default="")

    model_config = ConfigDict(extra="allow")


class StreakCelebrationResult(BaseModel):
    """Result from streak celebration generation."""

    user_id: str
    streak_days: int
    milestone: str
    celebration: CelebrationContent
    type: str = "streak_celebration"


class TeaserContent(BaseModel):
    """Content for weekly teaser."""

    teaser_text: str = Field(default="")
    highlight_stat: str = Field(default="")
    call_to_action: str = Field(default="")

    model_config = ConfigDict(extra="allow")


class WeeklyTeaserResult(BaseModel):
    """Result from weekly teaser generation."""

    user_id: str
    week_entries: int
    teaser: TeaserContent
    type: str = "weekly_teaser"


class ReminderContent(BaseModel):
    """Content for meal reminder."""

    message: str = Field(default="")
    suggestions: list[str] = Field(default_factory=list)
    quick_log_prompt: str = Field(default="")

    model_config = ConfigDict(extra="allow")


class MealReminderResult(BaseModel):
    """Result from meal reminder generation."""

    user_id: str
    meal_type: str
    hours_since_meal: float
    reminder: ReminderContent
    type: str = "meal_reminder"


class AchievementContent(BaseModel):
    """Content for achievement unlock."""

    name: str = Field(default="")
    badge: str = Field(default="")
    message: str = Field(default="")
    significance: str = Field(default="")
    next_goal: str = Field(default="")

    model_config = ConfigDict(extra="allow")


class AchievementResult(BaseModel):
    """Result from achievement unlock generation."""

    user_id: str
    achievement_type: str
    achievement_data: dict[str, Any]
    content: AchievementContent
    type: str = "achievement_unlock"
    unlocked_at: str


class FoodTipResult(BaseModel):
    """Result from food tip generation."""

    user_id: str
    date: str
    tip: str
    tip_title: str
    category: str
    source: str
    sources: list[GroundingSource] = Field(default_factory=list)
    type: str = "food_tip"


class SeasonalReminderResult(BaseModel):
    """Result from seasonal reminder generation."""

    user_id: str
    location: str
    month: str
    reminder: str
    sources: list[GroundingSource] = Field(default_factory=list)
    type: str = "seasonal_reminder"


# ============================================================================
# Pydantic AI Freshness Agent
# ============================================================================


class PydanticFreshnessAgent:
    """Type-safe freshness agent using Pydantic models.

    Provides the same functionality as FreshnessAgent with:
    - Type-safe inputs and outputs via Pydantic models
    - Backward-compatible dict interface
    - Structured validation and parsing

    Usage:
        agent = PydanticFreshnessAgent(user_id="user123")

        # Type-safe API
        request = DailyInsightRequest(
            taste_profile=TasteProfile(top_cuisines=["Italian"]),
            recent_logs=[FoodLog(dish_name="Pizza")],
        )
        result = await agent.generate_daily_insight_typed(request)

        # Backward-compatible API
        result = await agent.generate_daily_insight(
            taste_profile={"top_cuisines": ["Italian"]},
            recent_logs=[{"dish_name": "Pizza"}],
        )
    """

    MILESTONE_THRESHOLDS = [
        (365, "legendary", "FOOD LOGGING LEGEND"),
        (100, "incredible", "CENTURY CLUB"),
        (30, "amazing", "MONTH MASTER"),
        (7, "great", "WEEK WARRIOR"),
        (1, "nice", "STREAK STARTED"),
    ]

    def __init__(self, user_id: str, gemini: GeminiClient | None = None):
        self.user_id = user_id
        self._gemini = gemini

    def _gemini_client(self) -> GeminiClient:
        return self._gemini or gemini

    def _get_milestone(self, streak_days: int) -> tuple[str, str]:
        """Get milestone tier and achievement name for streak days."""
        return next(
            (
                (milestone, achievement)
                for threshold, milestone, achievement in self.MILESTONE_THRESHOLDS
                if streak_days >= threshold
            ),
            ("nice", "STREAK STARTED"),
        )

    def _parse_sources(self, sources: list[dict[str, Any]] | None) -> list[GroundingSource]:
        """Parse grounding sources into Pydantic models."""
        if not sources:
            return []
        return [GroundingSource(uri=s.get("uri", ""), title=s.get("title", "")) for s in sources if s.get("uri")]

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

    async def generate_daily_insight_typed(self, request: DailyInsightRequest) -> DailyInsightResult:
        """Generate daily insight with type-safe request/response."""
        today = date.today()
        location_context = f" in {request.location}" if request.location else ""

        logs_data = [log.model_dump() for log in request.recent_logs]

        prompt = f"""Generate a personalized daily food insight for today ({today.strftime("%B %d, %Y")}).

USER'S TASTE PROFILE:
{json.dumps(request.taste_profile.to_dict(), indent=2)}

RECENT MEALS (last few days):
{json.dumps(logs_data, indent=2)}

Search for and consider:
1. What's in season right now{location_context}?
2. Any food holidays or observances today?
3. Trending food topics?
4. Weather-appropriate food suggestions?

Generate a brief, engaging daily insight that:
- Feels personal and timely
- References something from their recent eating
- Suggests something new or seasonal
- Includes an interesting food fact if relevant

Keep it to 2-3 short paragraphs. Make it feel like a friend's recommendation."""

        result = await self._gemini_client().generate_with_grounding(prompt)

        return DailyInsightResult(
            user_id=self.user_id,
            date=today.isoformat(),
            insight=result.get("text", ""),
            sources=self._parse_sources(result.get("sources")),
        )

    async def generate_streak_celebration_typed(self, request: StreakCelebrationRequest) -> StreakCelebrationResult:
        """Generate streak celebration with type-safe request/response."""
        name = request.user_name or "foodie"
        milestone, achievement = self._get_milestone(request.streak_days)

        prompt = f"""Generate a fun, encouraging celebration message for {name} who has logged food for {request.streak_days} consecutive days!

Milestone: {milestone}
Achievement: {achievement}

Create:
1. A celebratory headline
2. A personalized congratulations message (2-3 sentences)
3. An achievement badge description
4. An encouragement to keep going
5. A fun food fact related to consistency or habits

Make it feel special and motivating. Use food puns if appropriate!

Return as JSON:
{{
    "headline": "...",
    "message": "...",
    "achievement_name": "...",
    "achievement_description": "...",
    "encouragement": "...",
    "fun_fact": "..."
}}"""

        result = await self._gemini_client().generate_json_with_thinking(prompt=prompt, thinking_level="low")

        return StreakCelebrationResult(
            user_id=self.user_id,
            streak_days=request.streak_days,
            milestone=milestone,
            celebration=self._parse_content_safely(result, CelebrationContent),
        )

    async def generate_weekly_teaser_typed(self, request: WeeklyTeaserRequest) -> WeeklyTeaserResult:
        """Generate weekly teaser with type-safe request/response."""
        logs_data = [log.model_dump() for log in request.food_logs]

        prompt = f"""Create a teaser for a weekly food summary.

THIS WEEK'S DATA ({len(request.food_logs)} meals):
{json.dumps(logs_data, indent=2)}

Generate a short, intriguing teaser that:
1. Highlights one surprising stat
2. Mentions a "best moment"
3. Creates curiosity to view the full summary

Keep it to 2-3 sentences. Make people want to click "View Full Summary".

Return as JSON:
{{
    "teaser_text": "...",
    "highlight_stat": "...",
    "call_to_action": "..."
}}"""

        result = await self._gemini_client().generate_json_with_thinking(prompt=prompt, thinking_level="low")

        return WeeklyTeaserResult(
            user_id=self.user_id,
            week_entries=len(request.food_logs),
            teaser=self._parse_content_safely(result, TeaserContent),
        )

    async def generate_meal_reminder_typed(self, request: MealReminderRequest) -> MealReminderResult:
        """Generate meal reminder with type-safe request/response."""
        prompt = f"""Generate a friendly meal reminder for {request.meal_type}.

It's been {request.last_meal_hours_ago:.1f} hours since they last logged a meal.

USER'S PREFERENCES:
{json.dumps(request.taste_profile.to_dict(), indent=2)}

Create a gentle, non-pushy reminder that:
1. Acknowledges the time since last meal
2. Suggests 2-3 quick {request.meal_type} options based on preferences
3. Encourages logging (not just eating)

Keep it friendly and helpful, not nagging.

Return as JSON:
{{
    "message": "...",
    "suggestions": ["...", "...", "..."],
    "quick_log_prompt": "..."
}}"""

        result = await self._gemini_client().generate_json_with_thinking(prompt=prompt, thinking_level="low")

        return MealReminderResult(
            user_id=self.user_id,
            meal_type=request.meal_type,
            hours_since_meal=request.last_meal_hours_ago,
            reminder=self._parse_content_safely(result, ReminderContent),
        )

    async def generate_achievement_typed(self, request: AchievementRequest) -> AchievementResult:
        """Generate achievement unlock with type-safe request/response."""
        prompt = f"""Generate content for a newly unlocked food achievement.

ACHIEVEMENT TYPE: {request.achievement_type}
ACHIEVEMENT DATA:
{json.dumps(request.achievement_data, indent=2)}

Common achievement types:
- first_cuisine: First time logging a cuisine
- cuisine_explorer: Tried X different cuisines
- home_chef: Logged X home-cooked meals
- adventurous_eater: Tried X new dishes
- consistent_logger: Logged every day for X days
- photo_collector: Logged X meals with photos
- balanced_eater: Hit nutrition goals X times

Generate:
1. Achievement name (catchy title)
2. Badge description
3. Congratulations message
4. What this means / why it matters
5. Next goal to aim for

Return as JSON:
{{
    "name": "...",
    "badge": "...",
    "message": "...",
    "significance": "...",
    "next_goal": "..."
}}"""

        result = await self._gemini_client().generate_json_with_thinking(prompt=prompt, thinking_level="low")

        return AchievementResult(
            user_id=self.user_id,
            achievement_type=request.achievement_type,
            achievement_data=request.achievement_data,
            content=self._parse_content_safely(result, AchievementContent),
            unlocked_at=datetime.now(UTC).isoformat(),
        )

    async def generate_food_tip_typed(self, request: FoodTipRequest) -> FoodTipResult:
        """Generate food tip with type-safe request/response."""
        today = date.today()

        prompt = f"""Generate a helpful food tip for today ({today.strftime("%A, %B %d")}).

USER PREFERENCES:
{json.dumps(request.taste_profile.to_dict(), indent=2)}

Search for and generate a tip that:
1. Is relevant to their cuisine preferences
2. Is timely (seasonal, day-appropriate)
3. Is practical and actionable
4. Teaches something useful

Could be about:
- Cooking techniques
- Ingredient selection
- Food pairing
- Kitchen hacks
- Nutrition tips
- Restaurant ordering tips

Return as JSON:
{{
    "tip_title": "...",
    "tip_content": "...",
    "category": "...",
    "source": "..."
}}"""

        result = await self._gemini_client().generate_json_with_grounding(prompt)

        tip_data = result.get("data", {}) if isinstance(result, dict) else {}

        return FoodTipResult(
            user_id=self.user_id,
            date=today.isoformat(),
            tip=tip_data.get("tip_content", "") if isinstance(tip_data, dict) else "",
            tip_title=tip_data.get("tip_title", "Food Tip") if isinstance(tip_data, dict) else "Food Tip",
            category=tip_data.get("category", "") if isinstance(tip_data, dict) else "",
            source=tip_data.get("source", "") if isinstance(tip_data, dict) else "",
            sources=self._parse_sources(result.get("sources") if isinstance(result, dict) else None),
        )

    async def generate_seasonal_reminder_typed(self, request: SeasonalReminderRequest) -> SeasonalReminderResult:
        """Generate seasonal reminder with type-safe request/response."""
        today = date.today()
        month = today.strftime("%B")

        prompt = f"""Generate a seasonal food reminder for {month} in {request.location}.

USER PREFERENCES:
{json.dumps(request.taste_profile.to_dict(), indent=2)}

Search for what's in season now and generate:
1. Top 3 ingredients in peak season
2. Why they're special right now
3. Quick suggestions for using each
4. One "don't miss" seasonal dish

Make it feel urgent/exciting - these won't last forever!

Focus on items that match their cuisine preferences."""

        result = await self._gemini_client().generate_with_grounding(prompt)

        return SeasonalReminderResult(
            user_id=self.user_id,
            location=request.location,
            month=month,
            reminder=result.get("text", ""),
            sources=self._parse_sources(result.get("sources")),
        )

    # ========================================================================
    # Backward-compatible API (dict inputs, dict outputs)
    # ========================================================================

    async def generate_daily_insight(
        self,
        taste_profile: dict,
        recent_logs: list[dict],
        location: str | None = None,
    ) -> dict[str, Any]:
        """Generate daily insight with dict interface (backward compatible)."""
        request = DailyInsightRequest(
            taste_profile=TasteProfile(**taste_profile) if taste_profile else TasteProfile(),
            recent_logs=[FoodLog.model_validate(log) for log in recent_logs],
            location=location,
        )
        result = await self.generate_daily_insight_typed(request)
        return result.model_dump()

    async def generate_streak_celebration(
        self,
        streak_days: int,
        user_name: str | None = None,
    ) -> dict[str, Any]:
        """Generate streak celebration with dict interface (backward compatible)."""
        request = StreakCelebrationRequest(streak_days=streak_days, user_name=user_name)
        result = await self.generate_streak_celebration_typed(request)
        return result.model_dump()

    async def generate_weekly_summary_teaser(
        self,
        food_logs: list[dict],
    ) -> dict[str, Any]:
        """Generate weekly teaser with dict interface (backward compatible)."""
        request = WeeklyTeaserRequest(food_logs=[FoodLog.model_validate(log) for log in food_logs])
        result = await self.generate_weekly_teaser_typed(request)
        return result.model_dump()

    async def generate_meal_reminder(
        self,
        meal_type: str,
        taste_profile: dict,
        last_meal_hours_ago: float,
    ) -> dict[str, Any]:
        """Generate meal reminder with dict interface (backward compatible)."""
        request = MealReminderRequest(
            meal_type=meal_type,
            taste_profile=TasteProfile(**taste_profile) if taste_profile else TasteProfile(),
            last_meal_hours_ago=last_meal_hours_ago,
        )
        result = await self.generate_meal_reminder_typed(request)
        return result.model_dump()

    async def generate_achievement_unlock(
        self,
        achievement_type: str,
        achievement_data: dict,
    ) -> dict[str, Any]:
        """Generate achievement with dict interface (backward compatible)."""
        request = AchievementRequest(achievement_type=achievement_type, achievement_data=achievement_data)
        result = await self.generate_achievement_typed(request)
        return result.model_dump()

    async def generate_food_tip_of_day(
        self,
        taste_profile: dict,
    ) -> dict[str, Any]:
        """Generate food tip with dict interface (backward compatible)."""
        request = FoodTipRequest(taste_profile=TasteProfile(**taste_profile) if taste_profile else TasteProfile())
        result = await self.generate_food_tip_typed(request)
        return result.model_dump()

    async def generate_seasonal_reminder(
        self,
        location: str,
        taste_profile: dict,
    ) -> dict[str, Any]:
        """Generate seasonal reminder with dict interface (backward compatible)."""
        request = SeasonalReminderRequest(
            location=location,
            taste_profile=TasteProfile(**taste_profile) if taste_profile else TasteProfile(),
        )
        result = await self.generate_seasonal_reminder_typed(request)
        return result.model_dump()
