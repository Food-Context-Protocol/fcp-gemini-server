"""Advanced multimodal recipe extraction.

Extract structured recipes from images, videos, and audio using Gemini's
multimodal capabilities. Supports photos of recipe cards, cookbook pages,
cooking videos, and voice recordings.
"""

import logging
from typing import Any

from fcp.mcp.registry import tool
from fcp.security.input_sanitizer import sanitize_user_input
from fcp.services.gemini import gemini

logger = logging.getLogger(__name__)


@tool(
    name="dev.fcp.media.extract_recipe",
    description="Extract a recipe from an image or video",
    category="media",
)
async def extract_recipe_from_media(
    image_url: str | None = None, media_url: str | None = None, additional_notes: str | None = None
) -> dict[str, Any]:
    """
    Extract a structured recipe from an image, video, or audio file.

    This function uses Gemini's multimodal capabilities to:
    1. Analyze images of recipes (handwritten cards, cookbook pages, screenshots)
    2. Extract recipes from cooking videos (YouTube, TikTok, etc.)
    3. Transcribe and structure recipes from audio recordings

    Args:
        image_url: URL to an image of a recipe (e.g., cookbook page, recipe card)
        media_url: URL to video or audio content with cooking instructions
        additional_notes: User-provided context (e.g., "This is a vegan version")

    Returns:
        Dictionary with extracted recipe:
        {
            "title": str,
            "description": str | None,
            "servings": int | None,
            "prep_time": str | None,  # Human-readable (e.g., "20 minutes")
            "cook_time": str | None,
            "total_time": str | None,
            "ingredients": list[str],
            "instructions": list[str],
            "tags": list[str],
            "nutrition": dict | None
        }
    """
    system_instruction = """You are a professional recipe transcription expert.
Analyze the provided media (photo, video, or audio) and extract a complete, structured recipe.

EXTRACTION GUIDELINES:
1. Title: Extract or infer the recipe name
2. Description: Brief 1-2 sentence overview of the dish
3. Servings: Number of portions (as integer)
4. Times: Express as human-readable strings (e.g., "20 minutes", "1 hour 30 minutes")
   - prep_time: Time for preparation before cooking
   - cook_time: Active cooking/baking time
   - total_time: Complete time from start to finish
5. Ingredients: Full list with quantities and units
   - Format: "2 cups all-purpose flour"
   - Be specific about ingredient names
6. Instructions: Step-by-step cooking directions
   - Each step should be a clear, actionable sentence
   - Number of steps varies by complexity
7. Tags: Relevant categories (e.g., "dessert", "vegetarian", "quick", "comfort food")
8. Nutrition: If visible/mentioned, include per-serving values
   - calories, protein, carbs, fat, fiber, sodium

RESPONSE FORMAT (JSON):
{
    "title": "Recipe Name",
    "description": "Brief description of the dish",
    "servings": 4,
    "prep_time": "15 minutes",
    "cook_time": "30 minutes",
    "total_time": "45 minutes",
    "ingredients": [
        "2 cups flour",
        "1 cup sugar"
    ],
    "instructions": [
        "Preheat oven to 350°F.",
        "Mix dry ingredients.",
        "Add wet ingredients and stir."
    ],
    "tags": ["dessert", "baking", "comfort food"],
    "nutrition": {
        "calories": 250,
        "protein": "5g",
        "carbs": "40g",
        "fat": "8g"
    }
}

If information is not available or visible, omit the field or set to null.
For nutrition, only include if clearly shown in the source material."""

    # Build prompt with optional context
    prompt_parts = [system_instruction, "\nExtract the recipe from the provided media."]

    if additional_notes:
        sanitized_notes = sanitize_user_input(additional_notes, max_length=500, field_name="additional_notes")
        prompt_parts.append(f"\nUser notes: {sanitized_notes}")

    prompt = "\n".join(prompt_parts)

    try:
        # Use generate_json with multimodal support
        json_response = await gemini.generate_json(
            prompt,
            image_url=image_url,
            media_url=media_url,
        )

        # Handle array response (including empty array)
        if isinstance(json_response, list):
            json_response = json_response[0] if json_response else {}

        # Handle non-dict response
        if not isinstance(json_response, dict):
            json_response = {}

        # Normalize and validate response
        return {
            "title": json_response.get("title", "Untitled Recipe"),
            "description": json_response.get("description"),
            "servings": _parse_int(json_response.get("servings")),
            "prep_time": json_response.get("prep_time"),
            "cook_time": json_response.get("cook_time"),
            "total_time": json_response.get("total_time"),
            "ingredients": _ensure_list(json_response.get("ingredients", [])),
            "instructions": _ensure_list(json_response.get("instructions", [])),
            "tags": _ensure_list(json_response.get("tags", [])),
            "nutrition": json_response.get("nutrition"),
        }

    except Exception as e:
        logger.exception("Error extracting recipe from media")
        return {"error": str(e)}


def _parse_int(value: Any) -> int | None:
    """Safely parse an integer value."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _ensure_list(value: Any) -> list[str]:
    """Ensure value is a list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]
