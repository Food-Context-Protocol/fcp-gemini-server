"""AI-powered meal suggestions."""

import json
import logging
from typing import Any

from fcp.mcp.registry import tool
from fcp.prompts import PROMPTS
from fcp.services.firestore import firestore_client
from fcp.services.gemini import gemini
from fcp.tools.profile import get_taste_profile

logger = logging.getLogger(__name__)


@tool(
    name="dev.fcp.planning.get_meal_suggestions",
    description="Get AI-powered meal recommendations based on user's history and preferences",
    category="planning",
)
async def get_meal_suggestions_tool(
    user_id: str,
    context: str = "",
    exclude_recent_days: int = 3,
) -> dict[str, Any]:
    """MCP tool wrapper for suggest_meal."""
    suggestions = await suggest_meal(user_id, context, exclude_recent_days)
    return {"suggestions": suggestions}


async def suggest_meal(
    user_id: str,
    context: str = "",
    exclude_recent_days: int = 3,
) -> list[dict[str, Any]]:
    """
    Generate meal suggestions based on user history and preferences.

    Args:
        user_id: The user's ID
        context: Optional context like "date night", "quick lunch"
        exclude_recent_days: Don't suggest dishes from this many recent days

    Returns:
        List of 3 suggestions with reasons
    """
    # Get taste profile
    profile = await get_taste_profile(user_id, period="month")

    # Get recent meals to exclude
    recent_logs = await firestore_client.get_user_logs(user_id, limit=20, days=exclude_recent_days)
    recent_dishes = [log.get("dish_name", "").lower() for log in recent_logs]

    # Get historical favorites
    all_logs = await firestore_client.get_user_logs(user_id, limit=200)

    # Build prompt
    prompt = PROMPTS["suggest_meal"].format(
        profile=json.dumps(profile, indent=2),
        recent=json.dumps(
            [{"dish_name": log.get("dish_name"), "venue": log.get("venue_name")} for log in recent_logs[:5]],
            indent=2,
        ),
        context=context or "any meal",
    )

    try:
        logger.info("Calling Gemini for meal suggestions (user=%s, context=%s)", user_id, context)
        logger.debug(
            "Gemini prompt: %s",
            f"{prompt[:500]}..." if len(prompt) > 500 else prompt,
        )

        result = await gemini.generate_json(prompt)

        logger.info("Gemini response received: %d suggestions", len(result.get("suggestions", [])))
        logger.debug("Gemini response: %s", result)
        return result.get("suggestions", [])

    except Exception as e:
        # Log the error so we know Gemini failed
        logger.warning("Gemini call failed, using fallback suggestions: %s", e)
        # Fallback to simple history-based suggestions
        return _simple_suggestions(all_logs, recent_dishes)


def _simple_suggestions(
    logs: list[dict],
    recent_dishes: list[str],
) -> list[dict[str, Any]]:
    """Simple suggestions from history."""
    # Count dish frequency
    dish_counts: dict[str, dict] = {}

    for log in logs:
        dish = log.get("dish_name")
        if not dish or dish.lower() in recent_dishes:
            continue

        if dish not in dish_counts:
            dish_counts[dish] = {
                "dish_name": dish,
                "venue": log.get("venue_name"),
                "count": 0,
            }
        dish_counts[dish]["count"] += 1

    # Sort by frequency
    sorted_dishes = sorted(dish_counts.values(), key=lambda x: -x["count"])

    return [
        {
            "dish_name": dish["dish_name"],
            "venue": dish.get("venue"),
            "type": "favorite",
            "reason": f"You've had this {dish['count']} times",
        }
        for dish in sorted_dishes[:3]
    ]
