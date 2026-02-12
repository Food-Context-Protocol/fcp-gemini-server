"""Analyze meal images with Gemini.

This module provides two analysis methods:
1. analyze_meal() - Uses JSON mode (original, reliable)
2. analyze_meal_v2() - Uses Function Calling (Gemini 3 feature)

Function calling provides more structured extraction with explicit
tool definitions, while JSON mode is simpler and works well for
straightforward analysis.
"""

import base64
from typing import Any

from fcp.mcp.registry import tool
from fcp.prompts import PROMPTS
from fcp.services.gemini import gemini
from fcp.tools.function_definitions import FOOD_ANALYSIS_TOOLS


def _normalize_analysis_result(result: dict | list) -> dict[str, Any]:
    """Normalize Gemini analysis result to standard format with defaults."""
    # Handle case where Gemini returns a list instead of dict
    if isinstance(result, list):
        result = result[0] if result else {}

    # Ensure required fields have defaults
    return {
        "dish_name": result.get("dish_name", "Unknown Dish"),
        "cuisine": result.get("cuisine"),
        "ingredients": result.get("ingredients", []),
        "nutrition": result.get("nutrition", {}),
        "dietary_tags": result.get("dietary_tags", []),
        "allergens": result.get("allergens", []),
        "spice_level": result.get("spice_level", 0),
        "cooking_method": result.get("cooking_method"),
        "translations": result.get("translations", {}),
        "foodon": result.get("foodon", {}),
    }


async def analyze_meal(image_url: str) -> dict[str, Any]:
    """
    Analyze a food image using Gemini JSON mode.

    This is the original implementation using JSON mode for
    guaranteed structured output.

    Args:
        image_url: URL of the food image to analyze

    Returns:
        dict with dish_name, cuisine, ingredients, nutrition, etc.
    """
    prompt = PROMPTS["analyze_meal"]
    result = await gemini.generate_json(prompt, image_url=image_url)
    return _normalize_analysis_result(result)


async def analyze_meal_from_bytes(image_bytes: bytes, mime_type: str) -> dict[str, Any]:
    """
    Analyze a food image from raw bytes using Gemini JSON mode.

    This is useful when you have image data in memory (e.g., from an upload)
    and don't need to store it first. Enables analysis without Firebase Storage.

    Args:
        image_bytes: Raw image data
        mime_type: MIME type of the image (e.g., "image/jpeg", "image/png")

    Returns:
        dict with dish_name, cuisine, ingredients, nutrition, etc.
    """
    prompt = PROMPTS["analyze_meal"]
    result = await gemini.generate_json(
        prompt,
        image_bytes=image_bytes,
        image_mime_type=mime_type,
    )
    return _normalize_analysis_result(result)


@tool(
    name="dev.fcp.media.analyze_meal",
    description="Analyze a meal image from URL",
    category="media",
)
async def analyze_meal_tool(image_url: str) -> dict[str, Any]:
    """MCP wrapper for URL-based meal analysis."""
    return await analyze_meal(image_url)


@tool(
    name="dev.fcp.media.analyze_meal_from_bytes",
    description="Analyze a meal image from base64-encoded bytes",
    category="media",
)
async def analyze_meal_from_bytes_tool(
    image_data: str,
    mime_type: str = "image/jpeg",
) -> dict[str, Any]:
    """MCP wrapper for byte-based meal analysis."""
    raw_bytes = base64.b64decode(image_data)
    return await analyze_meal_from_bytes(raw_bytes, mime_type)


async def analyze_meal_v2(image_url: str) -> dict[str, Any]:
    """
    Analyze a food image using Gemini 3 Function Calling.

    This version uses Gemini's function calling feature where
    the model calls structured tool functions to report its analysis.
    This provides more explicit, typed extraction.

    Args:
        image_url: URL of the food image to analyze

    Returns:
        dict with comprehensive analysis from all tool calls
    """
    prompt = """Analyze this food image thoroughly.

You have access to several tools to report your analysis. Use ALL relevant tools:

1. identify_dish - Identify what dish this is and its cuisine
2. identify_ingredients - List all visible/likely ingredients
3. extract_nutrition - Estimate nutritional values
4. identify_allergens - Flag any potential allergens
5. classify_dietary_tags - Classify dietary compatibility
6. rate_spice_level - Rate the spiciness

Analyze the image and call each tool with your findings."""

    result = await gemini.generate_with_tools(
        prompt=prompt,
        tools=FOOD_ANALYSIS_TOOLS,
        image_url=image_url,
    )

    # Parse function calls into structured result
    analysis = {
        "dish_name": "Unknown Dish",
        "cuisine": None,
        "cooking_method": None,
        "ingredients": [],
        "nutrition": {},
        "allergens": [],
        "dietary_tags": [],
        "spice_level": 0,
        "dietary_flags": {},
        "confidence": 0.0,
    }

    for call in result.get("function_calls", []):
        name = call["name"]
        args = call["args"]

        if name == "identify_dish":
            analysis["dish_name"] = args.get("dish_name", analysis["dish_name"])
            analysis["cuisine"] = args.get("cuisine")
            analysis["cooking_method"] = args.get("cooking_method")
            analysis["confidence"] = args.get("confidence", 0.0)

        elif name == "identify_ingredients":
            analysis["ingredients"] = args.get("ingredients", [])

        elif name == "extract_nutrition":
            analysis["nutrition"] = {
                "calories": args.get("calories"),
                "protein_g": args.get("protein_g"),
                "carbs_g": args.get("carbs_g"),
                "fat_g": args.get("fat_g"),
                "fiber_g": args.get("fiber_g"),
                "sodium_mg": args.get("sodium_mg"),
                "sugar_g": args.get("sugar_g"),
                "serving_size": args.get("serving_size"),
            }

        elif name == "identify_allergens":
            analysis["allergens"] = args.get("allergens", [])
            if args.get("warnings"):
                analysis["allergen_warnings"] = args["warnings"]

        elif name == "classify_dietary_tags":
            analysis["dietary_tags"] = args.get("tags", [])
            analysis["dietary_flags"] = {
                "vegetarian": args.get("vegetarian", False),
                "vegan": args.get("vegan", False),
                "gluten_free": args.get("gluten_free", False),
                "dairy_free": args.get("dairy_free", False),
                "keto_friendly": args.get("keto_friendly", False),
            }

        elif name == "rate_spice_level":
            analysis["spice_level"] = args.get("spice_level", 0)
            if args.get("spice_notes"):
                analysis["spice_notes"] = args["spice_notes"]

    return analysis


async def analyze_meal_with_agentic_vision(image_url: str) -> dict[str, Any]:
    """
    Analyze meal image using Agentic Vision (code execution).

    Uses Gemini's code execution to actively investigate the image:
    - Zoom into specific areas to identify ingredients
    - Count discrete items (sushi pieces, dumplings, etc.)
    - Calculate portion sizes based on visual analysis
    - Annotate regions to identify components

    Best for:
    - Complex dishes with multiple components
    - Portion size estimation
    - Counting discrete items
    - Detecting small details (garnishes, sauces)

    Args:
        image_url: URL of the food image to analyze

    Returns:
        dict with analysis plus _agentic_vision metadata
    """
    prompt = PROMPTS["analyze_meal_agentic_vision"]

    result = await gemini.generate_json_with_agentic_vision(
        prompt=prompt,
        image_url=image_url,
    )

    analysis = result.get("analysis", {})

    # Handle case where Gemini returns a list instead of dict
    if isinstance(analysis, list):
        analysis = analysis[0] if analysis and isinstance(analysis[0], dict) else {}

    # Normalize to standard analysis format with defaults
    return {
        "dish_name": analysis.get("dish_name", "Unknown Dish"),
        "cuisine": analysis.get("cuisine"),
        "ingredients": analysis.get("ingredients", []),
        "nutrition": analysis.get("nutrition", {}),
        "dietary_tags": analysis.get("dietary_tags", []),
        "allergens": analysis.get("allergens", []),
        "spice_level": analysis.get("spice_level", 0),
        "cooking_method": analysis.get("cooking_method"),
        "portion_analysis": analysis.get("portion_analysis"),
        "confidence_notes": analysis.get("confidence_notes"),
        # Include Agentic Vision metadata for transparency
        "_agentic_vision": {
            "code_executed": result.get("code"),
            "execution_result": result.get("execution_result"),
        },
    }


async def analyze_meal_with_thinking(image_url: str, thinking_level: str = "high") -> dict[str, Any]:
    """
    Analyze a food image with extended thinking for complex dishes.

    Uses Gemini 3's thinking feature for deeper analysis of:
    - Complex multi-component dishes
    - Fusion cuisines
    - Unusual ingredients
    - Detailed nutrition estimation

    Args:
        image_url: URL of the food image to analyze
        thinking_level: Level of thinking to use (minimal, low, medium, high)

    Returns:
        dict with detailed analysis using extended reasoning
    """
    prompt = """Analyze this food image in detail.

Think carefully about:
1. What dish is this? Consider fusion cuisines and regional variations.
2. What ingredients are visible? What ingredients are likely hidden?
3. How was this prepared? What cooking methods were used?
4. Estimate nutrition carefully based on portion size and ingredients.
5. What allergens might be present, including hidden ones?
6. What dietary restrictions would this satisfy or violate?

Provide a comprehensive analysis in JSON format with these fields:
{
    "dish_name": "Name of the dish",
    "cuisine": "Cuisine type or fusion description",
    "cooking_method": "How it was prepared",
    "ingredients": [{"name": "ingredient", "amount": "estimate", "is_visible": true/false}],
    "nutrition": {"calories": N, "protein_g": N, "carbs_g": N, "fat_g": N, "fiber_g": N},
    "allergens": ["list of allergens"],
    "dietary_tags": ["vegetarian", "etc"],
    "spice_level": 0-5,
    "analysis_notes": "Any additional observations about the dish"
}"""

    response = await gemini.generate_json_with_thinking(
        prompt=prompt,
        thinking_level=thinking_level,
        image_url=image_url,
        include_thinking_output=True,
    )

    # Extract analysis and thinking from response
    result = response.get("analysis", {})
    thinking = response.get("thinking")

    # Ensure required fields have defaults
    return {
        "dish_name": result.get("dish_name", "Unknown Dish"),
        "cuisine": result.get("cuisine"),
        "cooking_method": result.get("cooking_method"),
        "ingredients": result.get("ingredients", []),
        "nutrition": result.get("nutrition", {}),
        "allergens": result.get("allergens", []),
        "dietary_tags": result.get("dietary_tags", []),
        "spice_level": result.get("spice_level", 0),
        "analysis_notes": result.get("analysis_notes"),
        "thinking": thinking,  # Include AI reasoning when available
    }
