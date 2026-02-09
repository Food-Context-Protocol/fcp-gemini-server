"""Freshness Agent.

This agent keeps the app feeling alive and updated with:
- Daily personalized insights
- Streak celebrations
- Food facts and tips
- Seasonal reminders
- Achievement notifications

Uses Google Search grounding for real-time, relevant content.
"""

import json
from datetime import UTC, date, datetime
from typing import Any

from fcp.services.gemini import GeminiClient, gemini


class FreshnessAgent:
    """Agent that keeps the app feeling alive with daily insights."""

    def __init__(self, user_id: str, gemini: GeminiClient | None = None):
        self.user_id = user_id
        self._gemini = gemini

    def _gemini_client(self) -> GeminiClient:
        return self._gemini or gemini

    async def generate_daily_insight(
        self,
        taste_profile: dict,
        recent_logs: list[dict],
        location: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate a personalized daily insight.

        Uses Google Search grounding for real-time relevance.

        Args:
            taste_profile: User's taste profile
            recent_logs: Recent food logs (last 3-7 days)
            location: Optional location for local context

        Returns:
            dict with daily insight content
        """
        today = date.today()
        location_context = f" in {location}" if location else ""

        prompt = f"""Generate a personalized daily food insight for today ({today.strftime("%B %d, %Y")}).

USER'S TASTE PROFILE:
{json.dumps(taste_profile, indent=2)}

RECENT MEALS (last few days):
{json.dumps(recent_logs, indent=2)}

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

        return {
            "user_id": self.user_id,
            "date": today.isoformat(),
            "insight": result["text"],
            "sources": result["sources"],
            "type": "daily_insight",
        }

    async def generate_streak_celebration(
        self,
        streak_days: int,
        user_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate a celebration message for logging streaks.

        Args:
            streak_days: Number of consecutive days logged
            user_name: Optional user name for personalization

        Returns:
            dict with celebration content
        """
        name = user_name or "foodie"

        # Determine milestone type
        if streak_days >= 365:
            milestone = "legendary"
            achievement = "FOOD LOGGING LEGEND"
        elif streak_days >= 100:
            milestone = "incredible"
            achievement = "CENTURY CLUB"
        elif streak_days >= 30:
            milestone = "amazing"
            achievement = "MONTH MASTER"
        elif streak_days >= 7:
            milestone = "great"
            achievement = "WEEK WARRIOR"
        else:
            milestone = "nice"
            achievement = "STREAK STARTED"

        prompt = f"""Generate a fun, encouraging celebration message for {name} who has logged food for {streak_days} consecutive days!

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

        result = await self._gemini_client().generate_json_with_thinking(
            prompt=prompt,
            thinking_level="low",  # Quick, creative response
        )

        return {
            "user_id": self.user_id,
            "streak_days": streak_days,
            "milestone": milestone,
            "celebration": result,
            "type": "streak_celebration",
        }

    async def generate_weekly_summary_teaser(
        self,
        food_logs: list[dict],
    ) -> dict[str, Any]:
        """
        Generate a teaser for the weekly summary.

        Encourages users to view their full weekly digest.

        Args:
            food_logs: Food logs from the past week

        Returns:
            dict with teaser content
        """
        prompt = f"""Create a teaser for a weekly food summary.

THIS WEEK'S DATA ({len(food_logs)} meals):
{json.dumps(food_logs, indent=2)}

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

        result = await self._gemini_client().generate_json_with_thinking(
            prompt=prompt,
            thinking_level="low",
        )

        return {
            "user_id": self.user_id,
            "week_entries": len(food_logs),
            "teaser": result,
            "type": "weekly_teaser",
        }

    async def generate_meal_reminder(
        self,
        meal_type: str,
        taste_profile: dict,
        last_meal_hours_ago: float,
    ) -> dict[str, Any]:
        """
        Generate a gentle meal reminder with suggestions.

        Args:
            meal_type: Type of meal (breakfast, lunch, dinner, snack)
            taste_profile: User's taste profile
            last_meal_hours_ago: Hours since last logged meal

        Returns:
            dict with reminder content
        """
        prompt = f"""Generate a friendly meal reminder for {meal_type}.

It's been {last_meal_hours_ago:.1f} hours since they last logged a meal.

USER'S PREFERENCES:
{json.dumps(taste_profile, indent=2)}

Create a gentle, non-pushy reminder that:
1. Acknowledges the time since last meal
2. Suggests 2-3 quick {meal_type} options based on preferences
3. Encourages logging (not just eating)

Keep it friendly and helpful, not nagging.

Return as JSON:
{{
    "message": "...",
    "suggestions": ["...", "...", "..."],
    "quick_log_prompt": "..."
}}"""

        result = await self._gemini_client().generate_json_with_thinking(
            prompt=prompt,
            thinking_level="low",
        )

        return {
            "user_id": self.user_id,
            "meal_type": meal_type,
            "hours_since_meal": last_meal_hours_ago,
            "reminder": result,
            "type": "meal_reminder",
        }

    async def generate_achievement_unlock(
        self,
        achievement_type: str,
        achievement_data: dict,
    ) -> dict[str, Any]:
        """
        Generate content for a newly unlocked achievement.

        Args:
            achievement_type: Type of achievement
            achievement_data: Data about the achievement

        Returns:
            dict with achievement content
        """
        prompt = f"""Generate content for a newly unlocked food achievement.

ACHIEVEMENT TYPE: {achievement_type}
ACHIEVEMENT DATA:
{json.dumps(achievement_data, indent=2)}

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

        result = await self._gemini_client().generate_json_with_thinking(
            prompt=prompt,
            thinking_level="low",
        )

        return {
            "user_id": self.user_id,
            "achievement_type": achievement_type,
            "achievement_data": achievement_data,
            "content": result,
            "type": "achievement_unlock",
            "unlocked_at": datetime.now(UTC).isoformat(),
        }

    async def generate_food_tip_of_day(
        self,
        taste_profile: dict,
    ) -> dict[str, Any]:
        """
        Generate a food tip of the day based on preferences.

        Uses grounding for fresh, relevant tips.

        Args:
            taste_profile: User's taste profile

        Returns:
            dict with tip content
        """
        today = date.today()

        prompt = f"""Generate a helpful food tip for today ({today.strftime("%A, %B %d")}).

USER PREFERENCES:
{json.dumps(taste_profile, indent=2)}

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

        # Extract tip content from parsed JSON
        tip_data = result.get("data", {})
        return {
            "user_id": self.user_id,
            "date": today.isoformat(),
            "tip": tip_data.get("tip_content", ""),
            "tip_title": tip_data.get("tip_title", "Food Tip"),
            "category": tip_data.get("category", ""),
            "source": tip_data.get("source", ""),
            "sources": result.get("sources", []),
            "type": "food_tip",
        }

    async def generate_seasonal_reminder(
        self,
        location: str,
        taste_profile: dict,
    ) -> dict[str, Any]:
        """
        Generate a seasonal food reminder.

        Uses grounding to find what's currently in season.

        Args:
            location: User's location
            taste_profile: User's taste profile

        Returns:
            dict with seasonal reminder content
        """
        today = date.today()
        month = today.strftime("%B")

        prompt = f"""Generate a seasonal food reminder for {month} in {location}.

USER PREFERENCES:
{json.dumps(taste_profile, indent=2)}

Search for what's in season now and generate:
1. Top 3 ingredients in peak season
2. Why they're special right now
3. Quick suggestions for using each
4. One "don't miss" seasonal dish

Make it feel urgent/exciting - these won't last forever!

Focus on items that match their cuisine preferences."""

        result = await self._gemini_client().generate_with_grounding(prompt)

        return {
            "user_id": self.user_id,
            "location": location,
            "month": month,
            "reminder": result["text"],
            "sources": result["sources"],
            "type": "seasonal_reminder",
        }
