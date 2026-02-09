"""Liquid Intelligence - Specialized beverage tracking for Beer, Wine, and Coffee."""

from typing import Any

from fcp.services.gemini import gemini


async def analyze_beverage(description: str, beverage_type: str = "auto") -> dict[str, Any]:
    """
    Extract specialized metadata for beverages.

    Args:
        description: User's notes or beverage name.
        beverage_type: 'beer', 'wine', 'coffee', or 'auto'.

    Returns:
        Structured beverage metadata.
    """
    system_instruction = f"""
    You are a professional sommelier and cicerone.
    Analyze the beverage: "{description}".

    Identify:
    1. Type: (Beer, Wine, Coffee, Spirits)
    2. Style: (e.g., Hazy IPA, Cabernet Sauvignon, Ethiopia Yirgacheffe)
    3. Technical Stats:
       - Beer: ABV, IBU (estimate if not provided)
       - Wine: Vintage, Varietal, Region
       - Coffee: Roast Level, Origin, Processing Method
    4. Sensory Notes: Professional tasting notes.

    Return as JSON:
    {{
        "type": "...",
        "style": "...",
        "stats": {{ ... }},
        "tasting_notes": "..."
    }}
    """

    try:
        return await gemini.generate_json(system_instruction)
    except Exception as e:
        return {"error": str(e)}
