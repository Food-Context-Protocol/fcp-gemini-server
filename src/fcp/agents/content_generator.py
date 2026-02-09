"""Content Generator Agent.

This agent generates shareable content from food logs including:
- Weekly digests
- Social media posts
- Blog content (SEO-optimized)
- Food stories

Uses extended thinking for creative content generation.
"""

import json
import re
from typing import Any

from fcp.prompts import PROMPTS
from fcp.services.gemini import GeminiClient, gemini


class ContentGeneratorAgent:
    """Agent that generates shareable content from food logs."""

    def __init__(self, user_id: str, gemini: GeminiClient | None = None):
        self.user_id = user_id
        self._gemini = gemini

    def _gemini_client(self) -> GeminiClient:
        return self._gemini or gemini

    async def generate_weekly_digest(
        self,
        food_logs: list[dict],
        user_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate a weekly food digest for sharing.

        Args:
            food_logs: Food logs from the past week
            user_name: Optional user name for personalization

        Returns:
            dict with digest content
        """
        name_context = f"for {user_name}" if user_name else ""

        prompt = f"""Create an engaging weekly food digest {name_context}.

THIS WEEK'S MEALS ({len(food_logs)} entries):
{json.dumps(food_logs, indent=2)}

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

        return {
            "user_id": self.user_id,
            "period": "week",
            "entry_count": len(food_logs),
            "digest": result,
        }

    async def generate_social_post(
        self,
        food_log: dict,
        platform: str = "instagram",
        style: str = "casual",
    ) -> dict[str, Any]:
        """
        Generate a social media post for a meal.

        Args:
            food_log: Single food log entry
            platform: Target platform (instagram, twitter, facebook)
            style: Writing style (casual, foodie, professional)

        Returns:
            dict with post content
        """
        platform_limits = {
            "instagram": {"caption": 2200, "hashtags": 30},
            "twitter": {"caption": 280, "hashtags": 5},
            "facebook": {"caption": 500, "hashtags": 10},
        }
        limits = platform_limits.get(platform, platform_limits["instagram"])

        prompt = f"""Create a {platform} post for this meal.

MEAL DETAILS:
{json.dumps(food_log, indent=2)}

PLATFORM: {platform}
STYLE: {style}
CHARACTER LIMIT: {limits["caption"]}
MAX HASHTAGS: {limits["hashtags"]}

Generate:
1. CAPTION
   - Engaging, matches the {style} style
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

        return {
            "platform": platform,
            "style": style,
            "content": result,
        }

    async def generate_food_story(
        self,
        food_logs: list[dict],
        theme: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate a narrative food story from multiple logs.

        Args:
            food_logs: Food logs to weave into a story
            theme: Optional theme (adventure, comfort, culture, etc.)

        Returns:
            dict with story content
        """
        theme_context = f" with a '{theme}' theme" if theme else ""

        prompt = f"""Create a food story{theme_context} from these meals.

MEALS TO INCLUDE:
{json.dumps(food_logs, indent=2)}

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

        return {
            "user_id": self.user_id,
            "theme": theme,
            "entry_count": len(food_logs),
            "story": result,
        }

    async def generate_monthly_review(
        self,
        food_logs: list[dict],
        taste_profile: dict | None = None,
    ) -> dict[str, Any]:
        """
        Generate a comprehensive monthly food review.

        Args:
            food_logs: Food logs from the month
            taste_profile: Optional taste profile for context

        Returns:
            dict with monthly review content
        """
        profile_context = ""
        if taste_profile:
            profile_context = f"""
TASTE PROFILE:
{json.dumps(taste_profile, indent=2)}
Reference this to highlight growth and patterns."""

        prompt = f"""Create a comprehensive monthly food review.

THIS MONTH'S MEALS ({len(food_logs)} entries):
{json.dumps(food_logs, indent=2)}
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

        return {
            "user_id": self.user_id,
            "period": "month",
            "entry_count": len(food_logs),
            "review": result,
        }

    async def generate_recipe_card(
        self,
        food_log: dict,
        include_instructions: bool = True,
    ) -> dict[str, Any]:
        """
        Generate a shareable recipe card from a logged meal.

        Args:
            food_log: Food log entry to create recipe from
            include_instructions: Whether to generate cooking instructions

        Returns:
            dict with recipe card content
        """
        instructions_request = ""
        if include_instructions:
            instructions_request = """
5. INSTRUCTIONS
   - Step-by-step cooking instructions
   - Estimated based on the dish type"""

        prompt = f"""Create a recipe card from this logged meal.

MEAL:
{json.dumps(food_log, indent=2)}

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

        return {
            "source_log": food_log.get("id"),
            "recipe_card": result,
        }

    async def generate_blog_post(
        self,
        food_logs: list[dict],
        theme: str = "culinary_journey",
        style: str = "conversational",
    ) -> dict[str, Any]:
        """
        Generate an SEO-optimized blog post from food logs.

        Args:
            food_logs: List of food log entries to include
            theme: Content theme (culinary_journey, nutrition_focus, cultural_exploration)
            style: Writing style (conversational, professional, casual)

        Returns:
            dict with title, slug, content, excerpt, metadata, and suggestions
        """
        # Prepare log summaries for the prompt
        # Support both field naming conventions for backwards compatibility
        log_summaries = [
            {
                "dish": log.get("dish_name", "Unknown dish"),
                "cuisine": log.get("cuisine", "Unknown"),
                "date": log.get("created_at", ""),
                "highlights": log.get("ai_description", ""),
                "nutrition": log.get("nutrition") or log.get("nutrition_info", {}),
                "venue": log.get("venue") or log.get("venue_name", ""),
            }
            for log in food_logs
        ]

        prompt = PROMPTS["generate_blog_post"].format(
            logs=json.dumps(log_summaries, indent=2),
            theme=theme,
            style=style,
        )

        result = await self._gemini_client().generate_json_with_thinking(
            prompt=prompt,
            thinking_level="high",
        )

        # Generate slug from title if not provided
        if "slug" not in result or not result["slug"]:
            result["slug"] = self._slugify(result.get("title", "untitled"))

        return result

    def _slugify(self, text: str | None) -> str:
        """Convert text to URL-safe slug."""
        if not text:
            return "untitled"
        slug = text.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_-]+", "-", slug)
        return slug.strip("-")[:100]
