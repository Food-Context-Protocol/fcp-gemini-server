"""Agent orchestration tools for FCP."""

import json
import logging
from typing import Any

from fcp.mcp.registry import tool
from fcp.services.gemini import gemini

logger = logging.getLogger(__name__)


@tool(
    name="dev.fcp.agents.delegate_to_food_agent",
    description="Delegate a complex objective to a specialized food agent",
    category="agents",
)
async def delegate_to_food_agent_tool(user_id: str, agent_name: str, objective: str) -> dict[str, Any]:
    """MCP tool wrapper for delegate_to_food_agent."""
    from fcp.services.firestore import firestore_client

    context = await firestore_client.get_user_preferences(user_id)
    return await delegate_to_food_agent(agent_name=agent_name, objective=objective, user_context=context)


async def delegate_to_food_agent(
    agent_name: str, objective: str, user_context: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Delegate a complex objective to a specialized food agent.

    Args:
        agent_name: Name of the specialized agent (visual_agent, civic_agent, etc.)
        objective: The high-level goal to achieve.
        user_context: Optional additional user context (allergies, preferences).

    Returns:
        Structured response from the specialized agent.
    """

    # In a real implementation, this would switch to a specific system prompt
    # and a reduced toolset for the specialist.

    system_instructions = {
        "visual_agent": "You are an Art Director. Focus on visual design, editing, and storyboards.",
        "civic_agent": "You are a City Planner and Economic Developer. Focus on festivals, vendors, and community impact.",
        "discovery_agent": "You are a Food Explorer. Focus on finding new restaurants, recipes, and hidden gems.",
        "social_agent": "You are a Digital Publisher. Focus on blog posts, social media, and community engagement.",
        "nutrition_agent": "You are a Clinical Dietitian. Focus on macros, health goals, and medical safety.",
        "cottage_agent": "You are a Small Business Consultant. Focus on compliance, costs, and labels.",
        "inventory_agent": "You are a Pantry Manager. Focus on inventory, waste reduction, and home cooking.",
    }

    instruction = system_instructions.get(agent_name, "You are a specialized Food AI.")

    prompt = f"""
    ROLE: {instruction}
    OBJECTIVE: {objective}
    USER CONTEXT: {json.dumps(user_context or {}, indent=2)}

    Execute your specialized task and return a structured JSON report.
    """

    try:
        # Use Gemini generate_json for structured delegation
        result = await gemini.generate_json(prompt)
        return {"agent": agent_name, "status": "completed", "result": result}
    except Exception as e:
        logger.exception("Error during agent delegation")
        return {"agent": agent_name, "status": "failed", "error": str(e)}
