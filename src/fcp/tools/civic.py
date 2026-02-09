"""Civic and community planning tools for FCP."""

import logging
from typing import Any

from fcp.mcp.registry import tool
from fcp.services.gemini import gemini

logger = logging.getLogger(__name__)


@tool(
    name="dev.fcp.business.plan_food_festival",
    description="Plan a food festival by curating vendors and layout",
    category="business",
)
async def plan_food_festival(
    city_name: str,
    theme: str,
    target_vendor_count: int = 10,
    location_description: str | None = None,
) -> dict[str, Any]:
    """
    Plan a food festival by curating vendors and layout based on local engagement data.

    Args:
        city_name: Name of the city/neighborhood.
        theme: Theme of the festival (e.g., 'Spicy Food', 'Summer Harvest').
        target_vendor_count: Desired number of food vendors.
        location_description: Description of the park or venue.

    Returns:
        Structured festival plan with vendor types, layout suggestions, and marketing hooks.
    """

    system_instruction = """
    You are a City Event Weaver and Economic Developer.
    Design a comprehensive food festival plan that maximizes community engagement and economic impact.

    PLANNING REQUIREMENTS:
    1. Vendor Curation: Recommend specific cuisine types that are trending or high-rated in this area.
    2. Theme Alignment: Ensure all vendors and activities match the chosen theme.
    3. Layout Strategy: Suggest where to place high-traffic vendors vs niche ones (spatial reasoning).
    4. Economic Impact: Estimate how this drives local restaurant visibility.

    Return as a JSON object:
    {
        "festival_name": "...",
        "vendor_lineup": [
            { "cuisine": "...", "reason": "...", "ideal_spot": "..." }
        ],
        "layout_notes": "...",
        "marketing_hook": "...",
        "community_impact_score": 0.0-1.0
    }
    """

    prompt = f"""
    City: {city_name}
    Theme: {theme}
    Vendors: {target_vendor_count}
    Location: {location_description or "Local City Park"}
    """

    try:
        # Use Gemini with thinking for complex spatial and economic reasoning
        json_response = await gemini.generate_json(f"{system_instruction}\n\n{prompt}")
        if isinstance(json_response, list) and json_response:
            return json_response[0]
        return json_response
    except Exception as e:
        logger.exception("Error planning festival")
        return {"error": str(e), "status": "failed"}


@tool(
    name="dev.fcp.business.detect_economic_gaps",
    description="Identify culinary gaps in a neighborhood to help new businesses plan",
    category="business",
)
async def detect_economic_gaps(neighborhood: str, existing_cuisines: list[str]) -> dict[str, Any]:
    """
    Identify culinary gaps in a neighborhood to help new businesses plan.
    """
    system_instruction = """
    You are an Economic Development Agent. Analyze the existing food landscape
    and identify "Culinary Deserts" or gaps where demand is high but supply is low.
    """

    prompt = f"Neighborhood: {neighborhood}\nExisting: {', '.join(existing_cuisines)}"

    try:
        json_response = await gemini.generate_json(f"{system_instruction}\n\n{prompt}")
        if isinstance(json_response, list) and json_response:
            return json_response[0]
        return json_response
    except Exception as e:
        logger.exception("Error detecting gaps")
        return {"error": str(e)}
