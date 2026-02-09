"""Social syndication tools."""

from typing import Any

from fcp.mcp.registry import tool
from fcp.services.gemini import gemini


@tool(
    name="dev.fcp.publishing.generate_social_post",
    description="Generate a social media post based on a food log",
    category="publishing",
)
async def generate_social_post_tool(
    user_id: str, log_id: str, platform: str = "twitter", tone: str = "casual"
) -> dict[str, Any]:
    """MCP tool wrapper for generate_social_post."""
    from fcp.tools.crud import get_meal

    log = await get_meal(user_id, log_id)
    if not log:
        return {"error": f"Log {log_id} not found"}
    return await generate_social_post(log_data=log, platform=platform, style=tone)


async def generate_social_post(
    log_data: dict[str, Any], platform: str = "twitter", style: str = "casual"
) -> dict[str, Any]:
    """
    Generate a social media post based on a food log.
    """
    system_instruction = f"""
    You are a social media manager for a food lover.
    Create a post for {platform} with a {style} style.
    Return JSON: {{ "content": "...", "hashtags": ["#tag"], "image_concept": "..." }}
    """

    log_context = f"""
    Dish: {log_data.get("dish_name")}
    Venue: {log_data.get("venue_name", "Home")}
    Rating: {log_data.get("rating", "N/A")}/5
    Notes: {log_data.get("notes", "")}
    """

    try:
        result = await gemini.generate_json(f"{system_instruction}\n\nContext:\n{log_context}")
        if result and isinstance(result, dict) and "content" in result:
            result["text"] = result["content"]
        return result
    except Exception as e:
        return {
            "content": f"Just had {log_data.get('dish_name')}! #FoodLog",
            "text": f"Just had {log_data.get('dish_name')}! #FoodLog",
            "hashtags": ["#food"],
            "error": str(e),
        }


async def generate_weekly_digest(food_logs: list[dict[str, Any]], user_name: str | None = None) -> dict[str, Any]:
    """
    Summarize a week of eating into a cohesive story.
    """
    system_instruction = """
    Analyze the user's meals from the past week.
    Identify the "Hero Meal", the most frequent cuisine, and a "Discovery of the Week".

    Return JSON:
    {
        "title": "...",
        "weekly_summary": "...",
        "hero_meal_id": "...",
        "stats": {{ "top_cuisine": "...", "meal_count": 0 }},
        "image_concept": "..."
    }
    """

    prompt = f"User: {user_name or 'Foodie'}\nMeals:\n{food_logs}"

    try:
        return await gemini.generate_json(f"{system_instruction}\n\n{prompt}")
    except Exception:
        return {"title": "My Week in Food", "weekly_summary": "Another great week of eating!"}


async def generate_food_story(food_logs: list[dict[str, Any]], theme: str | None = None) -> dict[str, Any]:
    """Generate a visual food story from multiple logs."""
    system_instruction = f"Create a narrative story theme: {theme or 'culinary journey'} for these logs."
    try:
        return await gemini.generate_json(f"{system_instruction}\n\nLogs: {food_logs}")
    except Exception:
        return {"story": "A collection of great meals."}
