"""Recipe scaling and unit conversion tools."""

import logging
from typing import Any

from fcp.mcp.registry import tool
from fcp.services.gemini import gemini
from fcp.utils.errors import tool_error

logger = logging.getLogger(__name__)


@tool(
    name="dev.fcp.recipes.scale",
    description="Scale a recipe JSON object to a new number of servings",
    category="recipes",
)
async def scale_recipe(recipe_json: dict[str, Any], target_servings: int) -> dict[str, Any]:
    """
    Scale a Schema.org/Recipe JSON object to a new number of servings.

    Args:
        recipe_json: The original recipe in Schema.org format.
        target_servings: The desired number of servings.

    Returns:
        The scaled recipe JSON.
    """
    system_instruction = f"""
    You are a kitchen math expert. Scale the following Schema.org/Recipe to {target_servings} servings.

    Rules:
    1. Adjust all quantities in 'recipeIngredient' accurately.
    2. Update 'recipeYield' to reflecting the new serving count.
    3. Ensure units make sense (e.g., instead of 12 teaspoons, use 1/4 cup).
    4. Return the complete updated JSON object.
    """

    prompt = f"Original Recipe:\n{recipe_json}"

    try:
        json_response = await gemini.generate_json(f"{system_instruction}\n\n{prompt}")
        if isinstance(json_response, list) and json_response:
            return json_response[0]
        return json_response
    except Exception as e:
        return {**tool_error(e, "scaling recipe"), "status": "failed"}
