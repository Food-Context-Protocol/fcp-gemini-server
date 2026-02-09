"""Unit tests for tool registry system."""

from unittest.mock import patch

import pytest

from fcp.mcp.registry import ToolMetadata, ToolRegistry, tool, tool_registry


@pytest.fixture
def registry():
    """Create a fresh registry for each test."""
    reg = ToolRegistry()
    yield reg
    reg.clear()


@pytest.fixture(autouse=True)
def clear_global_registry():
    """Clear global registry before and after each test."""
    tool_registry.clear()
    yield
    tool_registry.clear()


class TestToolMetadata:
    """Test ToolMetadata dataclass."""

    def test_basic_metadata(self):
        """Test creating basic tool metadata."""

        async def dummy_handler():
            pass

        metadata = ToolMetadata(
            name="dev.fcp.test.dummy",
            handler=dummy_handler,
            description="A test tool",
            category="test",
        )

        assert metadata.name == "dev.fcp.test.dummy"
        assert metadata.handler == dummy_handler
        assert metadata.description == "A test tool"
        assert metadata.category == "test"
        assert metadata.requires_write is False
        assert metadata.requires_admin is False
        assert isinstance(metadata.dependencies, set)
        assert isinstance(metadata.schema, dict)

    def test_schema_generation_simple_types(self):
        """Test schema generation for simple Python types."""

        async def handler(name: str, age: int, active: bool):
            pass

        metadata = ToolMetadata(name="test", handler=handler)
        schema = metadata.schema
        assert schema is not None

        assert schema["type"] == "object"
        assert "properties" in schema
        assert schema["properties"]["name"] == {"type": "string"}
        assert schema["properties"]["age"] == {"type": "integer"}
        assert schema["properties"]["active"] == {"type": "boolean"}
        assert set(schema["required"]) == {"name", "age", "active"}

    def test_schema_generation_optional_types(self):
        """Test schema generation for optional parameters."""

        async def handler(required: str, optional: str | None = None):
            pass

        metadata = ToolMetadata(name="test", handler=handler)
        schema = metadata.schema
        assert schema is not None

        assert "required" in schema["properties"]
        assert "optional" in schema["properties"]
        assert schema["required"] == ["required"]  # Only required param

    def test_schema_generation_default_values(self):
        """Test schema generation with default values."""

        async def handler(name: str, count: int = 10, enabled: bool = True):
            pass

        metadata = ToolMetadata(name="test", handler=handler)
        schema = metadata.schema
        assert schema is not None

        # Only name is required (no default)
        assert schema["required"] == ["name"]

    def test_schema_generation_list_types(self):
        """Test schema generation for list types."""

        async def handler(tags: list[str], numbers: list[int]):
            pass

        metadata = ToolMetadata(name="test", handler=handler)
        schema = metadata.schema
        assert schema is not None

        assert schema["properties"]["tags"] == {"type": "array", "items": {"type": "string"}}
        assert schema["properties"]["numbers"] == {"type": "array", "items": {"type": "integer"}}

    def test_schema_generation_dict_types(self):
        """Test schema generation for dict types."""

        async def handler(data: dict):
            pass

        metadata = ToolMetadata(name="test", handler=handler)
        schema = metadata.schema
        assert schema is not None

        # Dict without type params falls back to string in our schema gen
        # This is fine - we can still pass objects, schema is just permissive
        assert "data" in schema["properties"]

    def test_schema_generation_skips_dependencies(self):
        """Test that dependency parameters are skipped in schema."""

        async def handler(name: str, db: str):  # db is a dependency
            pass

        metadata = ToolMetadata(
            name="test",
            handler=handler,
            dependencies={"db"},  # Mark db as dependency
        )
        schema = metadata.schema
        assert schema is not None

        # db should not appear in schema
        assert "name" in schema["properties"]
        assert "db" not in schema["properties"]
        assert schema["required"] == ["name"]

    def test_schema_generation_skips_user_id(self):
        """Test that user_id is skipped in schema (injected by dispatcher)."""

        async def handler(user_id: str, name: str):
            pass

        metadata = ToolMetadata(name="test", handler=handler)
        schema = metadata.schema
        assert schema is not None

        # user_id should not appear in schema
        assert "user_id" not in schema["properties"]
        assert "name" in schema["properties"]

    def test_schema_generation_with_float_type(self):
        """Test schema generation for float types."""

        async def handler(price: float, discount: float = 0.0):
            pass

        metadata = ToolMetadata(name="test", handler=handler)
        schema = metadata.schema
        assert schema is not None

        assert schema["properties"]["price"] == {"type": "number"}
        assert schema["properties"]["discount"] == {"type": "number"}
        assert "price" in schema["required"]
        assert "discount" not in schema["required"]

    def test_schema_generation_with_no_type_hints(self):
        """Test schema generation when parameters have no type hints."""

        async def handler(value):  # No type hint
            pass

        metadata = ToolMetadata(name="test", handler=handler)
        schema = metadata.schema
        assert schema is not None

        # Should fallback to string type
        assert "value" in schema["properties"]

    def test_schema_generation_with_complex_optional(self):
        """Test schema generation with Union types."""

        async def handler(value: str | None):
            pass

        metadata = ToolMetadata(name="test", handler=handler)
        schema = metadata.schema
        assert schema is not None

        # Should handle Union with None
        assert "value" in schema["properties"]

    def test_schema_with_provided_schema(self):
        """Test that provided schema is used instead of auto-generation."""

        async def handler(name: str):
            pass

        custom_schema = {"type": "object", "properties": {"custom": {"type": "string"}}}
        metadata = ToolMetadata(name="test", handler=handler, schema=custom_schema)

        # Should use provided schema, not auto-generated
        assert metadata.schema == custom_schema
        assert metadata.schema is not None
        assert "custom" in metadata.schema["properties"]

    def test_schema_generation_list_without_type_param(self):
        """Test schema generation for list without type parameters."""

        async def handler(items: list):
            pass

        metadata = ToolMetadata(name="test", handler=handler)
        schema = metadata.schema
        assert schema is not None

        # Should create array schema
        assert "items" in schema["properties"]

    def test_schema_generation_list_of_floats(self):
        """Test schema generation for list[float] types."""

        async def handler(prices: list[float]):
            pass

        metadata = ToolMetadata(name="test", handler=handler)
        schema = metadata.schema
        assert schema is not None

        assert schema["properties"]["prices"] == {"type": "array", "items": {"type": "number"}}
        assert "prices" in schema["required"]

    def test_schema_generation_list_of_bools(self):
        """Test schema generation for list[bool] types."""

        async def handler(flags: list[bool]):
            pass

        metadata = ToolMetadata(name="test", handler=handler)
        schema = metadata.schema
        assert schema is not None

        assert schema["properties"]["flags"] == {"type": "array", "items": {"type": "boolean"}}
        assert "flags" in schema["required"]

    def test_schema_generation_dict_with_type_params(self):
        """Test schema generation for dict with type parameters."""
        from typing import Any

        async def handler(config: dict[str, Any]):
            pass

        metadata = ToolMetadata(name="test", handler=handler)
        schema = metadata.schema
        assert schema is not None

        # Should create object schema
        assert schema["properties"]["config"] == {"type": "object"}
        assert "config" in schema["required"]

    def test_schema_generation_union_with_empty_args(self):
        """Test schema generation for Union type with empty args (edge case)."""

        async def handler(value: str | None):  # Use | syntax for types.UnionType
            pass

        # Create a side effect that returns empty to trigger the false branch
        def mock_get_args_side_effect(param_type):
            # Return empty tuple to trigger the "if args:" false branch (78->80)
            return ()

        # Mock get_args to return empty tuple to hit the false branch
        with patch("fcp.mcp.registry.get_args", side_effect=mock_get_args_side_effect):
            metadata = ToolMetadata(name="test", handler=handler)
            schema = metadata.schema
        assert schema is not None

        # Should still create a schema (fallback to string when Union has no args)
        assert "value" in schema["properties"]

    def test_unknown_type_logs_warning(self, caplog):
        """Unknown parameter types should log a warning when falling back to string."""
        import logging

        class CustomType:
            pass

        async def handler_with_custom_type(param: CustomType):
            pass

        with caplog.at_level(logging.WARNING, logger="fcp.mcp.registry"):
            meta = ToolMetadata(name="dev.fcp.test.custom", handler=handler_with_custom_type)

        assert meta.schema is not None
        assert meta.schema["properties"]["param"]["type"] == "string"
        assert "Falling back" in caplog.text


class TestToolRegistry:
    """Test ToolRegistry class."""

    def test_register_tool(self, registry):
        """Test registering a tool."""

        async def handler():
            pass

        metadata = ToolMetadata(name="dev.fcp.test.tool", handler=handler)
        registry.register(metadata)

        assert registry.get("dev.fcp.test.tool") == metadata

    def test_register_duplicate_raises_error(self, registry):
        """Test that registering duplicate tool name raises error."""

        async def handler():
            pass

        metadata1 = ToolMetadata(name="dev.fcp.test.tool", handler=handler)
        metadata2 = ToolMetadata(name="dev.fcp.test.tool", handler=handler)

        registry.register(metadata1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(metadata2)

    def test_get_nonexistent_tool(self, registry):
        """Test getting a tool that doesn't exist."""
        result = registry.get("dev.fcp.nonexistent")
        assert result is None

    def test_list_all_tools(self, registry):
        """Test listing all tools."""

        async def handler():
            pass

        tool1 = ToolMetadata(name="tool1", handler=handler, category="cat1")
        tool2 = ToolMetadata(name="tool2", handler=handler, category="cat2")
        tool3 = ToolMetadata(name="tool3", handler=handler, category="cat1")

        registry.register(tool1)
        registry.register(tool2)
        registry.register(tool3)

        all_tools = registry.list_tools()
        assert len(all_tools) == 3
        assert tool1 in all_tools
        assert tool2 in all_tools
        assert tool3 in all_tools

    def test_list_tools_by_category(self, registry):
        """Test filtering tools by category."""

        async def handler():
            pass

        tool1 = ToolMetadata(name="tool1", handler=handler, category="nutrition")
        tool2 = ToolMetadata(name="tool2", handler=handler, category="recipes")
        tool3 = ToolMetadata(name="tool3", handler=handler, category="nutrition")

        registry.register(tool1)
        registry.register(tool2)
        registry.register(tool3)

        nutrition_tools = registry.list_tools(category="nutrition")
        assert len(nutrition_tools) == 2
        assert tool1 in nutrition_tools
        assert tool3 in nutrition_tools

    def test_list_tools_by_write_permission(self, registry):
        """Test filtering tools by write permission."""

        async def handler():
            pass

        tool1 = ToolMetadata(name="tool1", handler=handler, requires_write=True)
        tool2 = ToolMetadata(name="tool2", handler=handler, requires_write=False)
        tool3 = ToolMetadata(name="tool3", handler=handler, requires_write=True)

        registry.register(tool1)
        registry.register(tool2)
        registry.register(tool3)

        write_tools = registry.list_tools(requires_write=True)
        assert len(write_tools) == 2
        assert tool1 in write_tools
        assert tool3 in write_tools

        read_tools = registry.list_tools(requires_write=False)
        assert len(read_tools) == 1
        assert tool2 in read_tools

    def test_list_tools_by_admin_permission(self, registry):
        """Test filtering tools by admin permission."""

        async def handler():
            pass

        tool1 = ToolMetadata(name="tool1", handler=handler, requires_admin=True)
        tool2 = ToolMetadata(name="tool2", handler=handler, requires_admin=False)

        registry.register(tool1)
        registry.register(tool2)

        admin_tools = registry.list_tools(requires_admin=True)
        assert len(admin_tools) == 1
        assert tool1 in admin_tools

    def test_get_mcp_tool_list(self, registry):
        """Test generating MCP-compatible tool list."""

        async def handler(name: str, age: int = 25):
            pass

        metadata = ToolMetadata(
            name="dev.fcp.test.tool",
            handler=handler,
            description="A test tool",
        )
        registry.register(metadata)

        mcp_tools = registry.get_mcp_tool_list()
        assert len(mcp_tools) == 1

        tool_def = mcp_tools[0]
        assert tool_def.name == "dev.fcp.test.tool"
        assert tool_def.description == "A test tool"
        assert tool_def.inputSchema is not None
        assert tool_def.inputSchema["type"] == "object"

    def test_get_mcp_tool_list_sorted(self, registry):
        """Test that MCP tool list is sorted by name."""

        async def handler():
            pass

        registry.register(ToolMetadata(name="zebra", handler=handler))
        registry.register(ToolMetadata(name="alpha", handler=handler))
        registry.register(ToolMetadata(name="beta", handler=handler))

        mcp_tools = registry.get_mcp_tool_list()
        names = [t.name for t in mcp_tools]

        assert names == ["alpha", "beta", "zebra"]

    def test_get_categories(self, registry):
        """Test getting unique categories."""

        async def handler():
            pass

        registry.register(ToolMetadata(name="tool1", handler=handler, category="nutrition"))
        registry.register(ToolMetadata(name="tool2", handler=handler, category="recipes"))
        registry.register(ToolMetadata(name="tool3", handler=handler, category="nutrition"))
        registry.register(ToolMetadata(name="tool4", handler=handler, category="safety"))

        categories = registry.get_categories()
        assert categories == ["nutrition", "recipes", "safety"]  # Sorted

    def test_get_all_names_returns_registered_names(self, registry):
        """get_all_names() returns all registered tool names."""

        async def handler():
            pass

        registry.register(ToolMetadata(name="dev.fcp.test.alpha", handler=handler))
        registry.register(ToolMetadata(name="dev.fcp.test.beta", handler=handler))
        assert registry.get_all_names() == {"dev.fcp.test.alpha", "dev.fcp.test.beta"}

    def test_get_by_short_name_finds_tool(self, registry):
        """get_by_short_name() finds tool by its last segment."""

        async def handler():
            pass

        registry.register(ToolMetadata(name="dev.fcp.test.alpha", handler=handler))
        meta = registry.get_by_short_name("alpha")
        assert meta is not None
        assert meta.name == "dev.fcp.test.alpha"

    def test_get_by_short_name_returns_none_for_unknown(self, registry):
        """get_by_short_name() returns None for unregistered short name."""
        assert registry.get_by_short_name("nonexistent") is None

    def test_clear_also_clears_short_names(self, registry):
        """clear() clears both _tools and _short_names."""

        async def handler():
            pass

        registry.register(ToolMetadata(name="dev.fcp.test.alpha", handler=handler))
        assert registry.get_by_short_name("alpha") is not None
        registry.clear()
        assert registry.get_by_short_name("alpha") is None
        assert registry.get_all_names() == set()

    def test_clear(self, registry):
        """Test clearing the registry."""

        async def handler():
            pass

        registry.register(ToolMetadata(name="tool1", handler=handler))
        registry.register(ToolMetadata(name="tool2", handler=handler))

        assert len(registry.list_tools()) == 2

        registry.clear()

        assert len(registry.list_tools()) == 0
        assert registry.get("tool1") is None


class TestToolDecorator:
    """Test @tool decorator."""

    def test_basic_decorator(self):
        """Test basic tool registration with decorator."""

        @tool(name="dev.fcp.test.basic", description="Basic test")
        async def basic_handler():
            return "success"

        metadata = tool_registry.get("dev.fcp.test.basic")
        assert metadata is not None
        assert metadata.name == "dev.fcp.test.basic"
        assert metadata.description == "Basic test"
        assert metadata.handler == basic_handler

    def test_decorator_with_permissions(self):
        """Test decorator with permission flags."""

        @tool(
            name="dev.fcp.test.admin",
            requires_write=True,
            requires_admin=True,
        )
        async def admin_handler():
            pass

        metadata = tool_registry.get("dev.fcp.test.admin")
        assert metadata.requires_write is True
        assert metadata.requires_admin is True

    def test_decorator_with_category(self):
        """Test decorator with category."""

        @tool(name="dev.fcp.test.categorized", category="nutrition")
        async def categorized_handler():
            pass

        metadata = tool_registry.get("dev.fcp.test.categorized")
        assert metadata.category == "nutrition"

    def test_decorator_with_dependencies(self):
        """Test decorator with explicit dependencies."""

        @tool(
            name="dev.fcp.test.deps",
            dependencies={"db", "ai"},
        )
        async def handler_with_deps(name: str, db=None, ai=None):
            pass

        metadata = tool_registry.get("dev.fcp.test.deps")
        assert metadata.dependencies == {"db", "ai"}

    @pytest.mark.asyncio
    async def test_decorator_preserves_function(self):
        """Test that decorator returns the original function."""

        @tool(name="dev.fcp.test.preserved")
        async def original():
            return "result"

        # Decorator should return the original function
        result = await original()
        assert result == "result"

    def test_multiple_tools_registration(self):
        """Test registering multiple tools."""

        @tool(name="tool1")
        async def handler1():
            pass

        @tool(name="tool2")
        async def handler2():
            pass

        @tool(name="tool3")
        async def handler3():
            pass

        assert tool_registry.get("tool1") is not None
        assert tool_registry.get("tool2") is not None
        assert tool_registry.get("tool3") is not None
        assert len(tool_registry.list_tools()) == 3

    def test_decorator_auto_generates_schema(self):
        """Test that decorator auto-generates schema from signature."""

        @tool(name="dev.fcp.test.schema")
        async def handler(name: str, age: int, active: bool = True):
            pass

        metadata = tool_registry.get("dev.fcp.test.schema")
        schema = metadata.schema
        assert schema is not None

        assert schema["properties"]["name"] == {"type": "string"}
        assert schema["properties"]["age"] == {"type": "integer"}
        assert schema["properties"]["active"] == {"type": "boolean"}
        assert "name" in schema["required"]
        assert "age" in schema["required"]
        assert "active" not in schema["required"]  # Has default


class TestToolExecution:
    """Test executing registered tools."""

    @pytest.mark.asyncio
    async def test_execute_simple_tool(self):
        """Test executing a simple registered tool."""

        @tool(name="dev.fcp.test.simple")
        async def simple():
            return {"status": "success"}

        metadata = tool_registry.get("dev.fcp.test.simple")
        result = await metadata.handler()

        assert result == {"status": "success"}

    @pytest.mark.asyncio
    async def test_execute_tool_with_parameters(self):
        """Test executing a tool with parameters."""

        @tool(name="dev.fcp.test.params")
        async def with_params(name: str, count: int):
            return {"name": name, "count": count}

        metadata = tool_registry.get("dev.fcp.test.params")
        result = await metadata.handler(name="test", count=42)

        assert result == {"name": "test", "count": 42}
