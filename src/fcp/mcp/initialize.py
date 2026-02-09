"""Tool initialization for FCP MCP server.

Imports all tool modules to ensure they are registered with the tool registry.
"""

import logging

logger = logging.getLogger(__name__)


def initialize_tools() -> int:
    """Initialize all tools by importing their modules.

    Returns:
        The number of registered tools.
    """
    import fcp.tools  # noqa: F401
    import fcp.tools.external.open_food_facts  # noqa: F401
    from fcp.mcp.registry import tool_registry

    tool_count = len(tool_registry.list_tools())
    logger.info("Initialized %d FCP tools", tool_count)
    return tool_count
