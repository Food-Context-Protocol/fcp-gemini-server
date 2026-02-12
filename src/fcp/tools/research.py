"""Deep research report generation.

Uses Gemini's Deep Research Agent to generate comprehensive
research reports on food-related topics.
"""

from typing import Any

from fcp.mcp.registry import tool
from fcp.services.gemini import gemini


async def generate_research_report(
    topic: str,
    context: str | None = None,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """
    Generate a comprehensive research report on a food topic.

    Uses the Deep Research Agent which autonomously:
    - Plans research approach
    - Executes multiple search queries
    - Synthesizes findings into a report

    Args:
        topic: Research topic (e.g., "Mediterranean diet health benefits")
        context: Optional user context (dietary restrictions, goals)
        timeout_seconds: Max wait time for research completion

    Returns:
        dict with:
        - report: The research report text (if completed)
        - interaction_id: ID for follow-up queries
        - status: "completed", "failed", or "timeout"
        - topic: Original research topic
    """
    # Build research query with optional context
    query = f"Research topic: {topic}"
    if context:
        query += f"\n\nUser context: {context}"

    result = await gemini.generate_deep_research(
        query=query,
        timeout_seconds=timeout_seconds,
    )

    # Add topic to result for reference
    result["topic"] = topic

    return result


@tool(
    name="dev.fcp.research.generate_report",
    description="Generate a deep research report for a food topic",
    category="research",
)
async def generate_report_tool(
    topic: str,
    context: str | None = None,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """MCP wrapper for deep research report generation."""
    return await generate_research_report(
        topic=topic,
        context=context,
        timeout_seconds=timeout_seconds,
    )
