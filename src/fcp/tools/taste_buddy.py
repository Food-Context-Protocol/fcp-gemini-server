"""Real-time dietary guidance tools.

Provides Taste Buddy functionality to check dishes against user dietary profiles,
detecting allergen risks and diet compliance with actionable suggestions.
"""

import logging
from typing import Any

from fcp.mcp.registry import tool
from fcp.services.gemini import gemini

logger = logging.getLogger(__name__)


@tool(
    name="dev.fcp.safety.check_dietary_compatibility",
    description="Check if a dish is compatible with a user's dietary profile",
    category="safety",
)
async def check_dietary_compatibility(
    dish_name: str, ingredients: list[str], user_allergies: list[str], user_diet: list[str]
) -> dict[str, Any]:
    """
    Check if a dish is compatible with a user's dietary profile.

    This is a safety-first analysis that:
    1. Checks for allergen cross-contamination risks
    2. Validates diet compliance (vegan, keto, halal, etc.)
    3. Suggests modifications to make the dish safe/compliant

    Args:
        dish_name: Name of the dish to analyze
        ingredients: List of ingredients in the dish
        user_allergies: User's declared food allergies (e.g., Peanuts, Shellfish)
        user_diet: User's dietary preferences (e.g., Vegan, Keto, Halal)

    Returns:
        Dictionary with compatibility analysis:
        {
            "is_safe": bool,  # No allergen risks detected
            "is_compliant": bool,  # Meets all dietary preferences
            "warnings": list[str],  # Specific concerns found
            "modifications_suggested": str | None  # How to make it safe/compliant
        }
    """
    system_instruction = """You are a safety-first dietary advisor specializing in food allergies and dietary compliance.

Analyze the dish against the user's allergies and dietary preferences with extreme care.

ALLERGEN ANALYSIS (is_safe):
- Check for direct allergen presence in ingredients
- Consider common cross-contamination risks (e.g., peanut oil, shared equipment)
- Flag hidden allergens (e.g., soy lecithin, milk derivatives, wheat-based soy sauce)
- When in doubt about an ingredient, flag it as a warning

DIET COMPLIANCE (is_compliant):
- Vegetarian: No meat, poultry, or fish
- Vegan: No animal products including dairy, eggs, honey
- Pescatarian: Allows fish/seafood, no other meat
- Keto: Very low carb, high fat
- Paleo: No processed foods, grains, legumes, dairy
- Gluten-Free: No wheat, barley, rye, or cross-contaminated items
- Dairy-Free: No milk, cheese, butter, cream
- Low-Sodium: Limited salt content
- Low-Sugar: Limited added sugars
- Halal: No pork, alcohol, properly slaughtered meat
- Kosher: No pork/shellfish, no mixing meat/dairy

RESPONSE FORMAT (JSON):
{
    "is_safe": true/false,
    "is_compliant": true/false,
    "warnings": ["Specific warning 1", "Specific warning 2"],
    "modifications_suggested": "Optional suggestion to make dish safe/compliant"
}

If is_safe is false, include specific allergen warnings.
If is_compliant is false, explain which diet rules are violated.
If both are true, warnings can be empty and modifications_suggested can be null."""

    # Handle empty profiles
    allergies_text = ", ".join(user_allergies) if user_allergies else "None declared"
    diets_text = ", ".join(user_diet) if user_diet else "None declared"
    ingredients_text = ", ".join(ingredients) if ingredients else "[no ingredient list available]"

    prompt = f"""Dish: {dish_name}
Ingredients: {ingredients_text}
User Allergies: {allergies_text}
User Dietary Preferences: {diets_text}

Analyze this dish for safety and compliance."""

    try:
        json_response = await gemini.generate_json(f"{system_instruction}\n\n{prompt}")

        # Handle array response (sometimes Gemini returns [{}])
        if isinstance(json_response, list) and json_response:
            json_response = json_response[0]

        # Handle non-dict response (safety-first: treat as unsafe)
        if not isinstance(json_response, dict):
            return {
                "is_safe": False,
                "is_compliant": False,
                "warnings": ["Unable to analyze dish - unexpected response format"],
                "modifications_suggested": None,
            }

        # Normalize warnings to always be a list
        warnings_raw = json_response.get("warnings")
        if warnings_raw is None:
            warnings = []
        elif isinstance(warnings_raw, str):
            warnings = [warnings_raw] if warnings_raw else []
        elif isinstance(warnings_raw, list):
            warnings = [str(w) for w in warnings_raw if w]
        else:
            warnings = []

        # Safety-first defaults: if fields are missing, assume unsafe/non-compliant
        is_safe = json_response.get("is_safe", False)
        is_compliant = json_response.get("is_compliant", False)
        return {
            "is_safe": is_safe,
            "is_compliant": is_compliant,
            "compatible": is_safe and is_compliant,
            "warnings": warnings,
            "modifications_suggested": json_response.get("modifications_suggested"),
        }

    except Exception as e:
        logger.exception("Error in Taste Buddy check")
        return {
            "is_safe": False,
            "is_compliant": False,
            "compatible": False,
            "warnings": [],
            "modifications_suggested": None,
            "error": str(e),
        }
