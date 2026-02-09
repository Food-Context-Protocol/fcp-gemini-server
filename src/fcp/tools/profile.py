"""Generate taste profiles from food history."""

import json
from typing import Any

from fcp.mcp.registry import tool
from fcp.prompts import PROMPTS
from fcp.services.firestore import firestore_client
from fcp.services.gemini import gemini


@tool(
    name="dev.fcp.profile.get_taste_profile",
    description="Analyze user's food preferences and eating patterns",
    category="profile",
)
async def get_taste_profile_tool(
    user_id: str,
    period: str = "all_time",
) -> dict[str, Any]:
    """MCP tool wrapper for get_taste_profile."""
    profile = await get_taste_profile(user_id, period)
    return {"profile": profile}


async def get_taste_profile(
    user_id: str,
    period: str = "all_time",
) -> dict[str, Any]:
    """
    Analyze user's eating patterns to build a taste profile.

    Args:
        user_id: The user's ID
        period: Time period - week, month, quarter, year, all_time

    Returns:
        dict with cuisine preferences, spice level, patterns, etc.
    """
    # Map period to days
    period_days = {
        "week": 7,
        "month": 30,
        "quarter": 90,
        "year": 365,
        "all_time": None,
    }
    days = period_days.get(period)

    # Fetch logs
    logs = await firestore_client.get_user_logs(user_id, limit=500, days=days)

    if not logs:
        return {
            "total_meals": 0,
            "message": "No food logs found for this period",
        }

    # Prepare logs for the prompt
    logs_summary = json.dumps(
        [
            {
                "dish_name": log.get("dish_name", ""),
                "venue": log.get("venue_name", ""),
                "cuisine": log.get("cuisine", ""),
                "spice_level": log.get("spice_level"),
                "date": log.get("created_at", ""),
                "dietary_tags": log.get("dietary_tags", []),
            }
            for log in logs
        ],
        indent=2,
    )

    prompt = PROMPTS["taste_profile"].format(logs=logs_summary)

    try:
        result = await gemini.generate_json(prompt)
        return {
            "period": period,
            "total_meals": len(logs),
            **result,
        }

    except Exception:
        # Fallback to simple aggregation
        return _simple_profile(logs, period)


def _simple_profile(logs: list[dict], period: str) -> dict[str, Any]:
    """Simple aggregation fallback."""
    cuisines: dict[str, int] = {}
    venues: dict[str, int] = {}
    total_spice = 0
    spice_count = 0

    for log in logs:
        if cuisine := log.get("cuisine"):
            cuisines[cuisine] = cuisines.get(cuisine, 0) + 1
        if venue := log.get("venue_name"):
            venues[venue] = venues.get(venue, 0) + 1
        if (spice := log.get("spice_level")) is not None:
            total_spice += spice
            spice_count += 1

    total = len(logs)
    top_cuisines = sorted(cuisines.items(), key=lambda x: -x[1])[:5]
    top_venues = sorted(venues.items(), key=lambda x: -x[1])[:5]

    avg_spice = total_spice / spice_count if spice_count else None
    spice_pref = "mild" if not avg_spice else "mild" if avg_spice < 2 else "medium" if avg_spice < 3.5 else "hot"

    return {
        "period": period,
        "total_meals": total,
        "top_cuisines": [
            {"name": c, "count": n, "percentage": round(n / total * 100) if total else 0} for c, n in top_cuisines
        ],
        "spice_preference": spice_pref,
        "favorite_venues": [{"name": v, "visits": n} for v, n in top_venues],
    }
