"""Recipe generation from ingredients."""

import logging
from typing import Any

from fcp.mcp.registry import tool
from fcp.services.gemini import gemini

logger = logging.getLogger(__name__)

RECIPE_GENERATION_PROMPT = """Generate a creative and delicious recipe using these ingredients: {ingredients}
{context}

Return a valid JSON object with this structure:
{{
  "recipe_name": "Creative name for the recipe",
  "description": "A brief, appetizing description",
  "prep_time": "15 minutes",
  "cook_time": "30 minutes",
  "servings": 4,
  "difficulty": "Easy/Medium/Hard",
  "ingredients_list": [
    {{"item": "ingredient name", "amount": "1 cup", "notes": "optional note"}}
  ],
  "instructions": [
    "Step 1: Do this...",
    "Step 2: Then do this..."
  ],
  "tips": ["Optional cooking tip 1", "Optional tip 2"],
  "nutrition_per_serving": {{
    "calories": 350,
    "protein": "25g",
    "carbs": "30g",
    "fat": "15g"
  }},
  "variations": ["Optional variation 1", "Optional variation 2"]
}}

Rules:
- Use the provided ingredients as the main components
- You can suggest common pantry staples (salt, pepper, oil, butter, etc.) as additions
- Be creative but practical
- Instructions should be clear and detailed
- Do not include markdown formatting. Just raw JSON.
"""


async def generate_recipe(
    ingredients: list[str],
    dish_name: str | None = None,
    cuisine: str | None = None,
    dietary_restrictions: str | None = None,
) -> dict[str, Any]:
    """
    Generate a recipe from ingredients.

    Args:
        ingredients: List of available ingredients
        dish_name: Optional dish name for inspiration
        cuisine: Optional cuisine type
        dietary_restrictions: Optional dietary restrictions

    Returns:
        Generated recipe as a dictionary
    """
    ingredients_str = ", ".join(ingredients)

    context_parts = []
    if dish_name:
        context_parts.append(f"inspired by: {dish_name}")
    if cuisine:
        context_parts.append(f"cuisine: {cuisine}")
    if dietary_restrictions:
        context_parts.append(f"dietary restrictions: {dietary_restrictions}")

    context = f"\nContext: {', '.join(context_parts)}" if context_parts else ""

    prompt = RECIPE_GENERATION_PROMPT.format(
        ingredients=ingredients_str,
        context=context,
    )

    try:
        logger.info(
            "Generating recipe from %d ingredients (dish=%s, cuisine=%s)",
            len(ingredients),
            dish_name,
            cuisine,
        )

        result = await gemini.generate_json(prompt)

        logger.info("Recipe generated: %s", result.get("recipe_name", "Unknown"))
        return result

    except ValueError as e:
        logger.error("Failed to parse recipe JSON: %s", e)
        raise ValueError("Failed to generate recipe: Invalid response format") from e
    except Exception as e:
        logger.error("Recipe generation failed: %s", e)
        raise


@tool(
    name="dev.fcp.recipes.generate_recipe",
    description="Generate a recipe from ingredients or a free-form prompt",
    category="recipes",
)
async def generate_recipe_tool(
    ingredients: list[str] | None = None,
    prompt: str | None = None,
    dish_name: str | None = None,
    cuisine: str | None = None,
    dietary_restrictions: str | None = None,
) -> dict[str, Any]:
    """MCP wrapper for recipe generation with prompt compatibility."""
    ingredient_list = ingredients

    if ingredient_list is None:
        ingredient_list = []

    if prompt and not ingredient_list:
        ingredient_list = [prompt]

    if not ingredient_list:
        return {
            "success": False,
            "error": "Provide either ingredients or prompt",
        }

    return await generate_recipe(
        ingredients=ingredient_list,
        dish_name=dish_name,
        cuisine=cuisine,
        dietary_restrictions=dietary_restrictions,
    )
