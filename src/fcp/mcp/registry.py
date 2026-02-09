"""Tool registry for FCP MCP tools.

Provides decorator-based tool registration with automatic schema generation
and dependency injection support.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from inspect import Parameter, signature
from typing import TYPE_CHECKING, Any, get_args, get_origin

if TYPE_CHECKING:
    from mcp.types import Tool

logger = logging.getLogger(__name__)


@dataclass
class ToolMetadata:
    """Metadata for a registered tool.

    Attributes:
        name: Fully qualified tool name (e.g., "dev.fcp.nutrition.add_meal")
        handler: The async function that implements the tool
        requires_write: Whether the tool requires write permission
        requires_admin: Whether the tool requires admin permission
        description: Human-readable description of what the tool does
        category: Tool category for organization (e.g., "nutrition", "recipes")
        dependencies: Parameter names that should be injected (not from MCP arguments)
        schema: JSON schema for tool input validation (auto-generated if not provided)
    """

    name: str
    handler: Callable
    requires_write: bool = False
    requires_admin: bool = False
    description: str = ""
    category: str = "general"
    dependencies: set[str] = field(default_factory=set)
    schema: dict[str, Any] | None = None
    inject_user_id: bool = False

    def __post_init__(self):
        """Auto-generate schema if not provided."""
        sig = signature(self.handler)
        self.inject_user_id = "user_id" in sig.parameters

        if self.schema is None:
            self.schema = self._infer_schema()

    def _infer_schema(self) -> dict[str, Any]:
        """Infer JSON schema from function signature.

        Generates a JSON schema by inspecting the function's type annotations.
        Skips dependency parameters (those in self.dependencies).

        Returns:
            JSON schema dict with properties and required fields
        """
        sig = signature(self.handler)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            # Skip dependency injection parameters
            if param_name in self.dependencies:
                continue

            # Skip user_id (injected by dispatcher)
            if param_name == "user_id":
                continue

            # Get parameter type
            param_type = param.annotation

            # Handle Optional types (Union[X, None])
            is_optional = False
            if get_origin(param_type) is type(None) or (get_origin(param_type) in (type(type(None)), type(None | int))):
                # It's Optional[X] or X | None
                args = get_args(param_type)
                if args:
                    param_type = args[0]  # Get the non-None type
                is_optional = True

            # Map Python types to JSON schema types
            if param_type is str or param_type == "str":
                properties[param_name] = {"type": "string"}
            elif param_type is int or param_type == "int":
                properties[param_name] = {"type": "integer"}
            elif param_type is float or param_type == "float":
                properties[param_name] = {"type": "number"}
            elif param_type is bool or param_type == "bool":
                properties[param_name] = {"type": "boolean"}
            elif get_origin(param_type) is list:
                # Handle list[X] types
                item_type = get_args(param_type)[0] if get_args(param_type) else str
                item_schema = "string"
                if item_type is int:
                    item_schema = "integer"
                elif item_type is float:
                    item_schema = "number"
                elif item_type is bool:
                    item_schema = "boolean"
                properties[param_name] = {"type": "array", "items": {"type": item_schema}}
            elif get_origin(param_type) is dict:
                properties[param_name] = {"type": "object"}
            else:
                # Fallback for unknown types
                logger.warning(
                    "Falling back to string schema for parameter '%s' with unknown type %r in tool '%s'",
                    param_name,
                    param_type,
                    self.name,
                )
                properties[param_name] = {"type": "string"}

            # Add to required list if no default value and not optional
            if param.default == Parameter.empty and not is_optional:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }


class ToolRegistry:
    """Central registry for all FCP tools.

    The registry maintains a mapping of tool names to their metadata.
    Tools register themselves using the @tool decorator.

    Example:
        from fcp.mcp.registry import tool, tool_registry

        @tool(name="dev.fcp.example.hello", description="Say hello")
        async def hello_world(name: str):
            return f"Hello, {name}!"

        # Later, lookup the tool
        metadata = tool_registry.get("dev.fcp.example.hello")
        result = await metadata.handler(name="World")
    """

    def __init__(self):
        self._tools: dict[str, ToolMetadata] = {}
        self._short_names: dict[str, str] = {}

    def register(self, metadata: ToolMetadata) -> None:
        """Register a tool in the registry.

        Args:
            metadata: Tool metadata including name, handler, and configuration

        Raises:
            ValueError: If a tool with the same name is already registered
        """
        if metadata.name in self._tools:
            raise ValueError(f"Tool '{metadata.name}' is already registered")

        self._tools[metadata.name] = metadata
        short = metadata.name.rsplit(".", 1)[-1]
        self._short_names[short] = metadata.name
        logger.debug("Registered tool: %s (category=%s)", metadata.name, metadata.category)

    def get(self, name: str) -> ToolMetadata | None:
        """Get tool metadata by name.

        Args:
            name: Fully qualified tool name

        Returns:
            Tool metadata if found, None otherwise
        """
        return self._tools.get(name)

    def get_all_names(self) -> set[str]:
        """Return all registered tool names."""
        return set(self._tools.keys())

    def get_by_short_name(self, short_name: str) -> ToolMetadata | None:
        """Look up a tool by its short name (last segment). O(1)."""
        full_name = self._short_names.get(short_name)
        if full_name:
            return self._tools.get(full_name)
        return None

    def list_tools(
        self,
        category: str | None = None,
        requires_write: bool | None = None,
        requires_admin: bool | None = None,
    ) -> list[ToolMetadata]:
        """List all registered tools with optional filters.

        Args:
            category: Filter by category (e.g., "nutrition", "recipes")
            requires_write: Filter by write permission requirement
            requires_admin: Filter by admin permission requirement

        Returns:
            List of tool metadata matching the filters
        """
        tools = list(self._tools.values())

        if category is not None:
            tools = [t for t in tools if t.category == category]
        if requires_write is not None:
            tools = [t for t in tools if t.requires_write == requires_write]
        if requires_admin is not None:
            tools = [t for t in tools if t.requires_admin == requires_admin]

        return tools

    def get_mcp_tool_list(self) -> list[Tool]:
        """Generate MCP-compatible tool list for clients.

        Returns a list of tools in the format expected by MCP clients,
        with name, description, and JSON schema for validation.

        Returns:
            List of tool definitions for MCP protocol
        """
        from mcp.types import Tool

        return [
            Tool(
                name=t.name,
                description=t.description or f"Execute {t.name}",
                inputSchema=t.schema or {"type": "object", "properties": {}},
            )
            for t in sorted(self._tools.values(), key=lambda x: x.name)
        ]

    def get_categories(self) -> list[str]:
        """Get all unique tool categories.

        Returns:
            Sorted list of category names
        """
        return sorted({t.category for t in self._tools.values()})

    def clear(self) -> None:
        """Clear all registered tools (for testing)."""
        self._tools.clear()
        self._short_names.clear()


# Global registry instance
tool_registry = ToolRegistry()


def tool(
    name: str,
    *,
    requires_write: bool = False,
    requires_admin: bool = False,
    description: str = "",
    category: str = "general",
    dependencies: set[str] | None = None,
):
    """Decorator to register a tool with the registry.

    This decorator registers a function as an FCP tool with metadata.
    The function's signature is inspected to auto-generate a JSON schema
    for input validation.

    Args:
        name: Fully qualified tool name (e.g., "dev.fcp.nutrition.add_meal")
        requires_write: Whether the tool requires write permission (default: False)
        requires_admin: Whether the tool requires admin permission (default: False)
        description: Human-readable description of what the tool does
        category: Tool category for organization (e.g., "nutrition")
        dependencies: Set of parameter names to be injected (not from MCP arguments)

    Example:
        @tool(
            name="dev.fcp.nutrition.add_meal",
            requires_write=True,
            description="Log a meal to nutrition history",
            category="nutrition",
            dependencies={"db"},
        )
        async def add_meal(
            user_id: str,
            dish_name: str,
            venue: str | None = None,
            db: Database = None,  # ← Injected dependency
        ):
            log_id = await db.create_log(user_id, {"dish_name": dish_name})
            return {"success": True, "log_id": log_id}
    """

    def decorator(func: Callable) -> Callable:
        # Auto-detect dependencies if not explicitly provided
        deps = dependencies or set()

        # Create metadata
        metadata = ToolMetadata(
            name=name,
            handler=func,
            requires_write=requires_write,
            requires_admin=requires_admin,
            description=description,
            category=category,
            dependencies=deps,
        )

        # Register the tool
        tool_registry.register(metadata)

        # Return the original function unchanged
        return func

    return decorator
