"""FoodLog Press - Blogging engine integration."""

import logging
from typing import Any

from fcp.mcp.registry import tool
from fcp.services.gemini import gemini

logger = logging.getLogger(__name__)


@tool(
    name="dev.fcp.publishing.generate_blog_post",
    description="Generate a blog post from a food log",
    category="publishing",
)
async def generate_blog_post_tool(user_id: str, log_id: str, style: str = "lifestyle") -> dict[str, Any]:
    """MCP tool wrapper for generate_blog_post."""
    from fcp.tools.crud import get_meal

    log = await get_meal(user_id, log_id)
    if not log:
        return {"error": "Log not found"}
    content = await generate_blog_post(log_data=log, style=style)
    return {"blog_post": content}


async def generate_blog_post(log_data: dict[str, Any], style: str = "lifestyle") -> str:
    """
    Generate a full blog post (Markdown + Frontmatter) from a food log.

    Returns:
        Formatted Markdown string.
    """
    system_instruction = f"""
    You are a professional food blogger and SEO expert.
    Convert the food log into a viral, engaging blog post in '{style}' style.

    REQUIREMENTS:
    1. Include YAML frontmatter: title, date, venue, rating, tags, cuisine.
    2. Write a catchy title.
    3. Include a sensory-rich intro, a 'The Dish' section, and a 'The Vibe' section.
    4. Conclude with a 'Final Verdict'.
    5. Return ONLY the Markdown content.
    """

    prompt = f"Food Log Data:\n{log_data}"

    try:
        return await gemini.generate_content(f"{system_instruction}\n\n{prompt}")
    except Exception:
        logger.exception("Error generating blog post")
        return f"# Review: {log_data.get('dish_name')}\n\nFailed to generate full post."
