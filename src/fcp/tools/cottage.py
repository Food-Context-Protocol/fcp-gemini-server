"""Cottage Industry tools for home-based food businesses."""

import logging
from typing import Any

from fcp.mcp.registry import tool
from fcp.services.gemini import gemini

logger = logging.getLogger(__name__)


@tool(
    name="dev.fcp.business.generate_cottage_label",
    description="Generate a legally compliant label for Cottage Food operations",
    category="business",
)
async def generate_cottage_label(
    product_name: str,
    ingredients: list[str],
    net_weight: str | None = None,
    business_name: str | None = None,
    business_address: str | None = None,
    is_refrigerated: bool = False,
) -> dict[str, Any]:
    """
    Generate a legally compliant label for Cottage Food operations.

    Args:
        product_name: Name of the food product.
        ingredients: List of ingredients used.
        net_weight: Net weight (e.g., '8 oz', '250g').
        business_name: Name of the home business.
        business_address: Physical address of the home kitchen.
        is_refrigerated: Whether the product requires refrigeration.

    Returns:
        Structured label data including required legal warnings and allergen flags.
    """

    system_instruction = """
    You are a regulatory compliance expert for Cottage Food laws (US-based).
    Generate a product label that includes all legally required elements for home-produced food.

    Required Elements:
    1. Product Name (Prominent).
    2. Net Weight (US and Metric if possible).
    3. Ingredient List (Descending order of predominance).
    4. Allergen Declaration (Major 9 allergens).
    5. Home Kitchen Warning: "Made in a Home Kitchen that has not been inspected by the [State/Local] Health Department."
    6. Business Name and Address.

    Return as a JSON object:
    {
        "label_text": "Formatted text for the label",
        "ingredients_formatted": "...",
        "allergens_identified": ["..."],
        "legal_warnings": ["..."],
        "storage_instructions": "..."
    }
    """

    weight_str = net_weight or "Not specified"
    business_str = f"{business_name or 'Not specified'} at {business_address or 'Not specified'}"

    prompt = f"""
    Product: {product_name}
    Ingredients: {", ".join(ingredients)}
    Weight: {weight_str}
    Business: {business_str}
    Refrigerated: {is_refrigerated}
    """

    try:
        json_response = await gemini.generate_json(f"{system_instruction}\n\n{prompt}")
        if isinstance(json_response, list) and json_response:
            return json_response[0]
        return json_response
    except Exception as e:
        logger.exception("Error generating cottage label")
        return {"error": str(e), "status": "failed"}
