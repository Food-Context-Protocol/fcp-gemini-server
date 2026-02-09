"""Recipe standardization tool using Gemini."""

import logging
from typing import Any

from fcp.mcp.registry import tool
from fcp.services.gemini import gemini

logger = logging.getLogger(__name__)


@tool(
    name="dev.fcp.recipes.standardize",
    description="Convert unstructured recipe text into standard Schema.org/Recipe JSON-LD",
    category="recipes",
)
async def standardize_recipe(raw_text: str) -> dict[str, Any]:
    """
    Convert unstructured recipe text into standard Schema.org/Recipe JSON-LD.

    Args:
        raw_text: The unstructured recipe notes, ingredients, or instructions.

    Returns:
        Dictionary conforming to Schema.org/Recipe structure.
    """
    # We need a specific prompt for this.
    # Since prompts are usually in prompts/__init__.py, I'll assume we pass it directly
    # or add it there. For now, I'll construct it here to keep it self-contained
    # but ideally it should move to PROMPTS.

    system_instruction = """
    You are a culinary data expert. Convert the following unstructured recipe text into a strictly formatted Schema.org/Recipe JSON object.

    Rules:
    1. Extract 'name', 'description', 'recipeCategory', 'recipeCuisine'.
    2. Format 'recipeIngredient' as a list of strings (quantity + unit + item).
    3. Format 'recipeInstructions' as a list of Step objects: [{"@type": "HowToStep", "text": "..."}].
    4. Estimate 'prepTime', 'cookTime', 'totalTime' in ISO 8601 duration format (PT20M) if mentioned or implied.
    5. Estimate 'nutrition' (calories) if possible, otherwise omit.
    6. Return ONLY the JSON object.
    """

    prompt = f"{system_instruction}\n\nInput Text:\n{raw_text}"

    try:
        # We leverage the existing gemini service which handles the LLM interaction
        result = await gemini.generate_json(prompt)

        # Ensure we add the context if missing
        if "@context" not in result:
            result["@context"] = "https://schema.org"
        if "@type" not in result:
            result["@type"] = "Recipe"

        return result

    except Exception:
        logger.exception("Error standardizing recipe")
        return {"error": "Failed to standardize recipe", "raw_text": raw_text}
