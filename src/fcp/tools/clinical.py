"""Clinical and Dietitian tools for FCP."""

import json
import logging
from typing import Any

from fcp.mcp.registry import tool
from fcp.services.firestore import firestore_client
from fcp.services.gemini import gemini
from fcp.utils.errors import tool_error

logger = logging.getLogger(__name__)


@tool(
    name="dev.fcp.clinical.generate_dietitian_report",
    description="Generate a professional clinical summary of a user's food intake",
    category="clinical",
)
async def generate_dietitian_report(user_id: str, days: int = 7, focus_area: str | None = None) -> dict[str, Any]:
    """
    Generate a professional clinical summary of a user's food intake.

    Args:
        user_id: The user ID.
        days: Number of recent days to analyze.
        focus_area: Specific health focus (e.g., 'high protein', 'diabetes', 'IBS').

    Returns:
        Structured dietitian report with macro/micro analysis and trigger identification.
    """

    # 1. Fetch user data
    logs = await firestore_client.get_user_logs(user_id, days=days)
    preferences = await firestore_client.get_user_preferences(user_id)

    if not logs:
        return {"error": "No food logs found for the specified period."}

    # 2. Prepare summary for Gemini
    logs_summary = [
        {
            "date": log.get("created_at"),
            "dish": log.get("dish_name"),
            "nutrition": log.get("nutrition"),
            "notes": log.get("notes"),
        }
        for log in logs
    ]

    system_instruction = f"""
    You are a registered dietitian (RD).
    Analyze the provided food logs and generate a professional clinical report.

    REPORT STRUCTURE:
    1. Nutritional Summary: Aggregate macro analysis (Protein, Carbs, Fat).
    2. Focus Area Analysis: Evaluate adherence to '{focus_area or "general wellness"}'.
    3. Pattern Identification: Note any frequent ingredients or potential trigger foods.
    4. Clinical Recommendations: 3 actionable steps for the patient.

    Return as a JSON object:
    {{
        "report_title": "...",
        "macro_analysis": {{ "avg_protein": 0, "avg_carbs": 0, "avg_fat": 0 }},
        "findings": ["..."],
        "recommendations": ["..."],
        "trigger_warnings": ["..."]
    }}
    """

    prompt = f"""
    USER LOGS (Last {days} days):
    {json.dumps(logs_summary, indent=2)}

    USER GOALS:
    {json.dumps(preferences.get("dietary_patterns", []), indent=2)}
    """

    try:
        json_response = await gemini.generate_json(f"{system_instruction}\n\n{prompt}")
        if isinstance(json_response, list) and json_response:
            return json_response[0]
        return json_response
    except Exception as e:
        return {**tool_error(e, "generating dietitian report"), "status": "failed"}
