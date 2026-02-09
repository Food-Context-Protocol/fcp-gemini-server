"""MCP resources and prompts for the FCP server."""

from mcp.types import Prompt, PromptArgument, Resource
from pydantic import AnyUrl


def get_resources() -> list[Resource]:
    """Return the list of MCP resources exposed by the FCP server."""
    return [
        Resource(
            uri=AnyUrl("foodlog://journal"),
            name="Food Journal",
            mimeType="application/json",
            description="The user's complete food journal history",
        ),
        Resource(
            uri=AnyUrl("foodlog://profile"),
            name="Taste Profile",
            mimeType="application/json",
            description="Aggregated analysis of user's food preferences",
        ),
    ]


def get_prompts() -> list[Prompt]:
    """Return the list of MCP prompts exposed by the FCP server."""
    return [
        Prompt(
            name="foodlog.plan",
            description="Help plan meals for the week based on user's preferences",
            arguments=[
                PromptArgument(
                    name="days",
                    description="Number of days to plan",
                    required=False,
                ),
                PromptArgument(
                    name="constraints",
                    description="Dietary constraints or preferences",
                    required=False,
                ),
            ],
        ),
        Prompt(
            name="foodlog.diary",
            description="Summarize recent eating habits",
            arguments=[
                PromptArgument(
                    name="period",
                    description="Time period (week, month)",
                    required=False,
                ),
            ],
        ),
    ]
