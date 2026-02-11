"Automated trend spotting tools."

import json
import logging
from typing import Any

from fcp.mcp.registry import tool
from fcp.services.firestore import firestore_client
from fcp.services.gemini import gemini
from fcp.utils.errors import tool_error
from fcp.utils.json_extractor import extract_json

logger = logging.getLogger(__name__)


@tool(
    name="dev.fcp.trends.identify_emerging_trends",
    description="Identify emerging food trends",
    category="trends",
)
async def identify_emerging_trends(
    user_id: str, region: str = "local", cuisine_focus: str | None = None
) -> dict[str, Any]:
    """
    Identify emerging food trends by grounding global data with user history.
    """

    # 1. Fetch user context
    stats = await firestore_client.get_user_stats(user_id)
    preferences = await firestore_client.get_user_preferences(user_id)

    system_instruction = """
    You are a Culinary Futurist. Your goal is to identify "The Next Big Thing" in food.

    METHODOLOGY:
    1. Use Google Search to find current global food trends (trending ingredients, cooking styles, or viral dishes).
    2. Analyze the user's taste profile and stats to see what aligns with these trends.
    3. Identify "The Local Gap": A global trend that hasn't hit the user's logged history yet.

    Return as JSON:
    {
        "trending_dish": "...",
        "why_its_trending": "...",
        "user_alignment_score": 0.0-1.0,
        "recommendation": "A specific action for the user (e.g., 'Try this new fermentation technique')",
        "sources": ["..."]
    }
    """

    prompt = f"""
    Region: {region}
    User Stats: {json.dumps(stats, indent=2)}
    User Cuisines: {json.dumps(preferences.get("top_cuisines", []), indent=2)}
    Focus: {cuisine_focus or "General Culinary"}
    """

    try:
        # Use grounding + thinking for deep research and synthesis
        result = await gemini.generate_with_all_tools(
            prompt=f"{system_instruction}\n\n{prompt}", enable_grounding=True, thinking_level="high"
        )

        # Extract JSON using centralized robust extractor
        text = result.get("text", "")
        parsed = extract_json(text)

        if parsed and isinstance(parsed, dict):
            parsed["grounding_sources"] = result.get("sources", [])
            return parsed

        logger.warning("Failed to parse trend analysis from Gemini response")
        return {"error": "Failed to parse trend analysis", "raw_text": text}

    except Exception as e:
        return tool_error(e, "identifying emerging trends")
