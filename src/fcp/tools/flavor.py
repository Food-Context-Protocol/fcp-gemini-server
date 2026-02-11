"""Culinary pairing and flavor sommelier tools."""

import logging
from typing import Any

from fcp.mcp.registry import tool
from fcp.services.gemini import gemini
from fcp.utils.errors import tool_error

logger = logging.getLogger(__name__)


@tool(
    name="dev.fcp.trends.get_flavor_pairings",
    description="Get perfect culinary pairings for an ingredient or dish",
    category="trends",
)
async def get_flavor_pairings(subject: str, pairing_type: str = "ingredient") -> dict[str, Any]:
    """
    Get perfect culinary pairings for an ingredient or dish.

    Args:
        subject: The ingredient or dish (e.g., 'Fennel', 'Ribeye').
        pairing_type: 'ingredient' or 'beverage'.

    Returns:
        Structured pairing suggestions with flavor notes.
    """
    system_instruction = f"""
    You are a world-class culinary sommelier and flavor scientist.
    Suggest perfect {pairing_type} pairings for '{subject}'.

    Rules:
    1. Provide 3-5 high-fidelity pairings.
    2. For each pairing, explain the 'Flavor Chemistry' (why it works).
    3. Include a 'Wildcard' pairing that is unexpected but brilliant.

    Return as JSON:
    {{
        "subject": "...",
        "pairings": [
            {{ "name": "...", "reason": "...", "flavor_profile": "..." }}
        ],
        "serving_suggestion": "..."
    }}
    """

    try:
        json_response = await gemini.generate_json(system_instruction)
        if isinstance(json_response, list) and json_response:
            return json_response[0]
        return json_response
    except Exception as e:
        return tool_error(e, "getting flavor pairings")
