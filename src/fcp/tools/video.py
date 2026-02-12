"""Video generation for recipes and food content.

Uses Veo 3.1 to generate short videos of dishes, cooking processes,
and food-related content.
"""

from typing import Any

from fcp.mcp.registry import tool
from fcp.services.firestore import get_firestore_client
from fcp.services.gemini import gemini

# Style prompts for different video types
STYLE_PROMPTS = {
    "cinematic": "Cinematic food photography style, shallow depth of field, warm lighting, appetizing presentation",
    "tutorial": "Overhead cooking tutorial view, clear step-by-step demonstration, clean workspace",
    "social": "Trendy social media style, quick cuts, vibrant colors, mouth-watering close-ups",
    "lifestyle": "Lifestyle food content, person enjoying meal, warm ambient lighting, cozy atmosphere",
}


async def generate_recipe_video(
    dish_name: str,
    description: str | None = None,
    style: str = "cinematic",
    duration_seconds: int = 8,
    aspect_ratio: str = "16:9",
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """
    Generate a short video for a dish or recipe.

    Uses Veo 3.1 to create AI-generated video content
    for food presentations, recipe showcases, and social media.

    Args:
        dish_name: Name of the dish (e.g., "Spaghetti Carbonara")
        description: Optional additional context or specific shots desired
        style: Video style (cinematic, tutorial, social, lifestyle)
        duration_seconds: Video length (4-8 seconds)
        aspect_ratio: "16:9" (landscape) or "9:16" (portrait/stories)
        timeout_seconds: Max wait time for video generation

    Returns:
        dict with:
        - status: "completed", "timeout", or "failed"
        - video_bytes: Raw video data (if completed)
        - dish_name: Original dish name
        - style: Video style used
    """
    # Build prompt with style
    style_description = STYLE_PROMPTS.get(style, STYLE_PROMPTS["cinematic"])
    prompt = f"{dish_name}. {style_description}"

    if description:
        prompt += f" {description}"

    result = await gemini.generate_video(
        prompt=prompt,
        duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
        timeout_seconds=timeout_seconds,
    )

    # Add metadata to result
    result["dish_name"] = dish_name
    result["style"] = style

    return result


async def generate_cooking_clip(
    action: str,
    ingredients: list[str] | None = None,
    duration_seconds: int = 8,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """
    Generate a short cooking action clip.

    Creates B-roll style clips of cooking actions like chopping,
    sautéing, plating, etc.

    Args:
        action: Cooking action (e.g., "chopping vegetables", "flipping pancakes")
        ingredients: Optional list of ingredients being used
        duration_seconds: Video length (4-8 seconds)
        timeout_seconds: Max wait time for video generation

    Returns:
        dict with video data and metadata
    """
    # Build descriptive prompt
    prompt = f"Close-up of {action}"

    if ingredients:
        ingredients_str = ", ".join(ingredients[:3])  # Limit to 3 for clarity
        prompt += f" with {ingredients_str}"

    prompt += ". Professional kitchen setting, warm lighting, shallow depth of field."

    result = await gemini.generate_video(
        prompt=prompt,
        duration_seconds=duration_seconds,
        aspect_ratio="16:9",
        timeout_seconds=timeout_seconds,
    )

    result["action"] = action
    result["ingredients"] = ingredients

    return result


@tool(
    name="dev.fcp.publishing.generate_recipe_video",
    description="Generate a short recipe video from recipe ID or dish name",
    category="publishing",
)
async def generate_recipe_video_tool(
    recipe_id: str | None = None,
    dish_name: str | None = None,
    description: str | None = None,
    style: str = "cinematic",
    duration_seconds: int = 8,
    aspect_ratio: str = "16:9",
    timeout_seconds: int = 300,
    user_id: str | None = None,
) -> dict[str, Any]:
    """MCP wrapper for recipe video generation with app-compatible arguments."""
    resolved_dish_name = dish_name

    if resolved_dish_name is None and recipe_id and user_id:
        db = get_firestore_client()
        recipe = await db.get_recipe(user_id, recipe_id)
        if recipe:
            resolved_dish_name = recipe.get("name") or recipe.get("recipe_name")
            if description is None:
                description = recipe.get("description")

    if not resolved_dish_name:
        return {
            "success": False,
            "error": "Provide dish_name or a valid recipe_id",
        }

    result = await generate_recipe_video(
        dish_name=resolved_dish_name,
        description=description,
        style=style,
        duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
        timeout_seconds=timeout_seconds,
    )
    if recipe_id is not None:
        result["recipe_id"] = recipe_id
    return result
