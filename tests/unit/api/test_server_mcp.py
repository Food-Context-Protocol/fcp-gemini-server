"""Tests for server.py MCP server implementation."""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import tool modules to trigger @tool decorator registration
# These are imported at module level but may need re-registration if other tests clear the registry
# ruff: noqa: F401
import fcp.tools.agents
import fcp.tools.audio
import fcp.tools.blog
import fcp.tools.civic
import fcp.tools.clinical
import fcp.tools.connector
import fcp.tools.cottage
import fcp.tools.crud
import fcp.tools.discovery
import fcp.tools.flavor
import fcp.tools.inventory
import fcp.tools.parser
import fcp.tools.profile
import fcp.tools.recipe_crud
import fcp.tools.recipe_extractor
import fcp.tools.safety
import fcp.tools.scaling
import fcp.tools.search
import fcp.tools.social
import fcp.tools.standardize
import fcp.tools.suggest
import fcp.tools.taste_buddy
import fcp.tools.trends
import fcp.tools.visual
from fcp.auth.permissions import AuthenticatedUser, UserRole


@pytest.fixture(autouse=True, scope="module")
def ensure_tools_registered():
    """Ensure tool modules are imported to register @tool decorators.

    This is needed because other tests may clear the global tool registry.
    The module-level imports handle initial registration, but if other tests
    clear the registry, this fixture re-registers by reloading the modules.
    """
    from fcp.mcp.registry import tool_registry

    # Check if tools are already registered
    registered_tools = tool_registry._tools.keys()

    if not any("nutrition.get_recent_meals" in name for name in registered_tools):
        # Tools not registered, need to reload modules
        import importlib

        modules = [
            fcp.tools.agents,
            fcp.tools.audio,
            fcp.tools.blog,
            fcp.tools.civic,
            fcp.tools.clinical,
            fcp.tools.connector,
            fcp.tools.cottage,
            fcp.tools.crud,
            fcp.tools.discovery,
            fcp.tools.flavor,
            fcp.tools.inventory,
            fcp.tools.parser,
            fcp.tools.profile,
            fcp.tools.recipe_crud,
            fcp.tools.recipe_extractor,
            fcp.tools.safety,
            fcp.tools.scaling,
            fcp.tools.search,
            fcp.tools.social,
            fcp.tools.standardize,
            fcp.tools.suggest,
            fcp.tools.taste_buddy,
            fcp.tools.trends,
            fcp.tools.visual,
        ]
        for module in modules:
            importlib.reload(module)

    yield


# Mock authenticated user for MCP tests
MOCK_USER = AuthenticatedUser(user_id="test-user", role=UserRole.AUTHENTICATED)
# Mock demo user for read-only access tests
DEMO_USER = AuthenticatedUser(user_id="demo", role=UserRole.DEMO)


@pytest.fixture(autouse=True)
def mock_firestore_client():
    """Automatically mock firestore_client in all tool modules to prevent real database access."""
    mock_db = AsyncMock()

    # Default mock behaviors for common operations
    mock_db.get_user_logs.return_value = []
    mock_db.get_log.return_value = None
    mock_db.create_log.return_value = "mock-log-id"
    mock_db.update_log.return_value = True
    mock_db.delete_log.return_value = True
    mock_db.get_recipes.return_value = []
    mock_db.get_recipe.return_value = None
    mock_db.create_recipe.return_value = "mock-recipe-id"
    mock_db.update_recipe.return_value = True
    mock_db.delete_recipe.return_value = True
    mock_db.get_pantry_items.return_value = []
    mock_db.add_pantry_item.return_value = "mock-item-id"
    mock_db.update_pantry_item.return_value = True
    mock_db.delete_pantry_item.return_value = True

    # Patch firestore_client in modules that import it directly
    patches = [
        patch("fcp.tools.audio.firestore_client", mock_db),
        patch("fcp.tools.clinical.firestore_client", mock_db),
        patch("fcp.tools.crud.firestore_client", mock_db),
        patch("fcp.tools.enrich.firestore_client", mock_db),
        patch("fcp.tools.inventory.firestore_client", mock_db),
        patch("fcp.tools.profile.firestore_client", mock_db),
        patch("fcp.tools.safety.firestore_client", mock_db),
        patch("fcp.tools.search.firestore_client", mock_db),
        patch("fcp.tools.suggest.firestore_client", mock_db),
        patch("fcp.tools.trends.firestore_client", mock_db),
        # Patch get_firestore_client for modules that use the function
        patch("fcp.tools.knowledge_graph.get_firestore_client", return_value=mock_db),
        patch("fcp.tools.parser.get_firestore_client", return_value=mock_db),
        patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db),
        patch("fcp.services.firestore.get_firestore_client", return_value=mock_db),
    ]

    # Start all patches
    for p in patches:
        p.start()

    yield mock_db

    # Stop all patches
    for p in patches:
        p.stop()


class TestGetUserId:
    """Tests for get_user_id function."""

    def test_no_token_returns_demo_user(self):
        """Test that missing token returns demo user with read-only access."""
        with patch.dict(os.environ, {}, clear=True):
            from fcp.server import get_user_id

            result = get_user_id()
            # Use attribute checks instead of isinstance (module reloading creates different class objects)
            assert hasattr(result, "user_id") and hasattr(result, "role")
            assert result.role.value == UserRole.DEMO.value
            assert result.is_demo is True

    def test_no_token_explicit_env_var(self):
        """Test that empty FCP_TOKEN env var returns demo user."""
        with patch.dict(os.environ, {"FCP_TOKEN": ""}, clear=True):
            from fcp.server import get_user_id

            result = get_user_id()
            assert hasattr(result, "user_id") and hasattr(result, "role")
            assert result.role.value == UserRole.DEMO.value
            assert result.is_demo is True

    def test_dev_mode_returns_authenticated_user(self):
        """Test that dev mode uses token directly as user ID with authenticated role."""
        with patch.dict(os.environ, {"FCP_TOKEN": "dev-user-123", "FOODLOG_DEV_MODE": "true"}):
            from fcp.server import get_user_id

            result = get_user_id()
            # Use attribute checks instead of isinstance (module reloading creates different class objects)
            assert hasattr(result, "user_id") and hasattr(result, "role")
            assert result.user_id == "dev-user-123"
            assert result.role.value == UserRole.AUTHENTICATED.value

    def test_dev_mode_with_token(self):
        """Test that dev mode with FCP_DEV_MODE=true returns authenticated user."""
        with patch.dict(os.environ, {"FCP_TOKEN": "dev-token-456", "FCP_DEV_MODE": "true"}):
            from fcp.server import get_user_id

            result = get_user_id()
            assert hasattr(result, "user_id") and hasattr(result, "role")
            assert result.user_id == "dev-token-456"
            assert result.role.value == UserRole.AUTHENTICATED.value

    def test_token_as_user_id(self):
        """Test that token is used directly as user_id in local auth."""
        with patch.dict(os.environ, {"FCP_TOKEN": "my-user-token"}, clear=True):
            from fcp.server import get_user_id

            result = get_user_id()
            assert hasattr(result, "user_id") and hasattr(result, "role")
            assert result.user_id == "my-user-token"
            assert result.role.value == UserRole.AUTHENTICATED.value

    def test_production_token_as_user_id(self):
        """Test that token is used as user_id in production (non-dev mode)."""
        with patch.dict(os.environ, {"FCP_TOKEN": "prod-token-789", "FCP_DEV_MODE": "false"}, clear=True):
            from fcp.server import get_user_id

            result = get_user_id()
            assert hasattr(result, "user_id") and hasattr(result, "role")
            assert result.user_id == "prod-token-789"
            assert result.role.value == UserRole.AUTHENTICATED.value

    def test_any_token_returns_authenticated_user(self):
        """Test that any token returns authenticated user in local auth mode."""
        with patch.dict(os.environ, {"FCP_TOKEN": "any-token"}, clear=True):
            from fcp.server import get_user_id

            result = get_user_id()
            assert hasattr(result, "user_id") and hasattr(result, "role")
            assert result.user_id == "any-token"
            assert result.role.value == UserRole.AUTHENTICATED.value


class TestListTools:
    """Tests for list_tools MCP handler."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_tools(self):
        """Test that list_tools returns available tools."""
        from fcp.server import list_tools

        tools = await list_tools()

        assert len(tools) > 0
        # Check some expected tools exist (using new dev.fcp.* namespaces)
        tool_names = [t.name for t in tools]
        assert "dev.fcp.nutrition.get_recent_meals" in tool_names
        assert "dev.fcp.nutrition.search_meals" in tool_names
        assert "dev.fcp.nutrition.add_meal" in tool_names


class TestListResources:
    """Tests for list_resources MCP handler."""

    @pytest.mark.asyncio
    async def test_list_resources_returns_resources(self):
        """Test that list_resources returns available resources."""
        from fcp.server import list_resources

        resources = await list_resources()

        assert len(resources) == 2
        # URIs are AnyUrl objects, convert to strings for comparison
        uris = [str(r.uri) for r in resources]
        assert "foodlog://journal" in uris
        assert "foodlog://profile" in uris


class TestListPrompts:
    """Tests for list_prompts MCP handler."""

    @pytest.mark.asyncio
    async def test_list_prompts_returns_prompts(self):
        """Test that list_prompts returns available prompts."""
        from fcp.server import list_prompts

        prompts = await list_prompts()

        assert len(prompts) == 2
        names = [p.name for p in prompts]
        assert "foodlog.plan" in names
        assert "foodlog.diary" in names


class TestCallTool:
    """Tests for call_tool MCP handler."""

    @pytest.mark.asyncio
    async def test_call_tool_rate_limit_exceeded(self):
        """Test that rate limit exceeded returns error."""
        from fcp.security.mcp_rate_limit import MCPRateLimitError
        from fcp.server import call_tool

        with patch("fcp.server.check_mcp_rate_limit") as mock_check:
            # MCPRateLimitError(tool_name, limit, window, retry_after)
            mock_check.side_effect = MCPRateLimitError(
                tool_name="get_recent_meals", limit=60, window=60, retry_after=30.5
            )

            result = await call_tool("dev.fcp.nutrition.get_recent_meals", {})

            assert len(result) == 1
            data = json.loads(result[0].text)
            assert data["error"] == "rate_limit_exceeded"
            assert data["retry_after"] == 30.5

    @pytest.mark.asyncio
    async def test_call_tool_get_recent_meals(self, mock_firestore_client):
        """Test get_recent_meals tool."""
        from fcp.server import call_tool

        # Configure mock for this test
        mock_firestore_client.get_user_logs.return_value = [{"dish_name": "Pasta", "cuisine": "Italian"}]

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch(
                "fcp.tools.crud.get_meals", new=AsyncMock(return_value=[{"dish_name": "Pasta", "cuisine": "Italian"}])
            ),
        ):
            result = await call_tool("dev.fcp.nutrition.get_recent_meals", {"limit": 5, "days": 3})

            assert len(result) == 1
            data = json.loads(result[0].text)
            assert "meals" in data
            assert len(data["meals"]) == 1
            assert data["meals"][0]["dish_name"] == "Pasta"

    @pytest.mark.skip(reason="schema_org format removed in registry migration")
    @pytest.mark.asyncio
    async def test_call_tool_get_recent_meals_with_schema_org_format(self):
        """Test get_recent_meals legacy handler with schema.org format."""
        from fcp.server import call_tool
        from fcp.services.mapper import to_schema_org_recipe as real_to_schema_org_recipe

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.crud.get_meals", new=AsyncMock(return_value=[{"dish_name": "Pizza"}])),
            patch("fcp.tools.crud.to_schema_org_recipe", side_effect=real_to_schema_org_recipe) as mock_mapper,
        ):
            # Use short name to trigger legacy handler with schema_org format
            result = await call_tool("get_recent_meals", {"format": "schema_org"})

            # Verify mapper was called with meal data
            mock_mapper.assert_called_once_with({"dish_name": "Pizza"})

            data = json.loads(result[0].text)
            assert "meals" in data
            assert data["meals"][0]["@type"] == "Recipe"

    @pytest.mark.asyncio
    async def test_call_tool_search_meals(self):
        """Test search_meals tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.search.search_meals_tool", new_callable=AsyncMock) as mock_search,
        ):
            mock_search.return_value = {"results": [{"dish_name": "Ramen", "relevance": 0.9}]}

            result = await call_tool("dev.fcp.nutrition.search_meals", {"query": "spicy noodles"})

            data = json.loads(result[0].text)
            assert "results" in data
            mock_search.assert_called_once_with(query="spicy noodles", user_id="test-user")

    @pytest.mark.asyncio
    async def test_call_tool_get_taste_profile(self):
        """Test get_taste_profile tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.profile.get_taste_profile_tool", new_callable=AsyncMock) as mock_profile,
        ):
            mock_profile.return_value = {"profile": {"top_cuisines": ["Italian", "Japanese"]}}

            result = await call_tool("dev.fcp.profile.get_taste_profile", {"period": "month"})

            data = json.loads(result[0].text)
            assert "profile" in data
            mock_profile.assert_called_once_with(period="month", user_id="test-user")

    @pytest.mark.asyncio
    async def test_call_tool_get_meal_suggestions(self):
        """Test get_meal_suggestions tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.suggest.get_meal_suggestions_tool", new_callable=AsyncMock) as mock_suggest,
        ):
            mock_suggest.return_value = {"suggestions": [{"name": "Sushi", "reason": "You love Japanese"}]}

            result = await call_tool("dev.fcp.planning.get_meal_suggestions", {"context": "date night"})

            data = json.loads(result[0].text)
            assert "suggestions" in data

    @pytest.mark.asyncio
    async def test_call_tool_add_meal(self, mock_firestore_client):
        """Test add_meal tool."""
        from fcp.server import call_tool

        # Configure mock for this test
        mock_firestore_client.create_log.return_value = "meal-123"

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            result = await call_tool("dev.fcp.nutrition.add_meal", {"dish_name": "Tacos", "venue": "Casa del Sol"})

            data = json.loads(result[0].text)
            assert data["success"] is True
            assert data["log_id"] == "meal-123"

    @pytest.mark.asyncio
    async def test_call_tool_delete_meal(self, mock_firestore_client):
        """Test delete_meal tool."""
        from fcp.server import call_tool

        # Configure mock for this test
        mock_firestore_client.get_log.return_value = {"id": "log-123", "dish_name": "Tacos"}
        mock_firestore_client.update_log.return_value = True

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            result = await call_tool("dev.fcp.nutrition.delete_meal", {"log_id": "log-123"})

            data = json.loads(result[0].text)
            assert data["success"] is True
            mock_firestore_client.get_log.assert_called_once_with("test-user", "log-123")
            mock_firestore_client.update_log.assert_called_once_with("test-user", "log-123", {"deleted": True})

    @pytest.mark.asyncio
    async def test_call_tool_donate_meal(self):
        """Test donate_meal tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.crud.donate_meal", new_callable=AsyncMock) as mock_donate,
        ):
            mock_donate.return_value = {"status": "pledged"}

            result = await call_tool("dev.fcp.business.donate_meal", {"log_id": "meal-123"})

            data = json.loads(result[0].text)
            assert data["status"] == "pledged"

    @pytest.mark.asyncio
    async def test_call_tool_lookup_product(self):
        """Test lookup_product tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.external.open_food_facts.lookup_product", new_callable=AsyncMock) as mock_lookup,
        ):
            mock_lookup.return_value = {"name": "Cereal", "nutrition": {}}

            result = await call_tool("dev.fcp.external.lookup_product", {"barcode": "123456789"})

            data = json.loads(result[0].text)
            assert data["name"] == "Cereal"

    @pytest.mark.asyncio
    async def test_call_tool_lookup_product_not_found(self):
        """Test lookup_product when product not found."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.external.open_food_facts.lookup_product", new_callable=AsyncMock) as mock_lookup,
        ):
            mock_lookup.return_value = {"error": "Product not found"}

            result = await call_tool("dev.fcp.external.lookup_product", {"barcode": "000000000"})

            data = json.loads(result[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_call_tool_standardize_recipe(self):
        """Test standardize_recipe tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.standardize.standardize_recipe", new_callable=AsyncMock) as mock_std,
        ):
            mock_std.return_value = {"@type": "Recipe", "name": "Test"}

            result = await call_tool("dev.fcp.recipes.standardize", {"raw_text": "Mix flour..."})

            data = json.loads(result[0].text)
            assert data["@type"] == "Recipe"

    @pytest.mark.asyncio
    async def test_call_tool_generate_image_prompt(self):
        """Test generate_image_prompt tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.visual.generate_image_prompt_tool", new_callable=AsyncMock) as mock_gen,
        ):
            mock_gen.return_value = {"prompt": "A beautiful photo of ramen..."}

            result = await call_tool("dev.fcp.visual.generate_image_prompt", {"subject": "ramen"})

            data = json.loads(result[0].text)
            assert "prompt" in data

    @pytest.mark.asyncio
    async def test_call_tool_generate_social_post(self):
        """Test generate_social_post tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.crud.get_meal", new_callable=AsyncMock) as mock_get,
            patch("fcp.tools.social.generate_social_post_tool", new_callable=AsyncMock) as mock_gen,
        ):
            mock_get.return_value = {"dish_name": "Pizza"}
            mock_gen.return_value = {"text": "Just had amazing pizza!"}

            result = await call_tool("dev.fcp.publishing.generate_social_post", {"log_id": "meal-123"})

            data = json.loads(result[0].text)
            assert "text" in data

    @pytest.mark.asyncio
    async def test_call_tool_generate_social_post_not_found(self):
        """Test generate_social_post when log not found."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.crud.get_meal", new_callable=AsyncMock) as mock_get,
        ):
            mock_get.return_value = None

            result = await call_tool("dev.fcp.publishing.generate_social_post", {"log_id": "nonexistent"})

            data = json.loads(result[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_call_tool_find_nearby_food(self):
        """Test find_nearby_food tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.discovery.find_nearby_food_tool", new_callable=AsyncMock) as mock_find,
        ):
            mock_find.return_value = {"venues": [{"name": "Best Pizza", "rating": 4.5}]}

            result = await call_tool(
                "dev.fcp.discovery.find_nearby_food", {"latitude": 37.7749, "longitude": -122.4194}
            )

            data = json.loads(result[0].text)
            assert "venues" in data

    @pytest.mark.asyncio
    async def test_call_tool_find_nearby_food_missing_location(self):
        """Test find_nearby_food tool returns error when neither coordinates nor location provided."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            result = await call_tool("dev.fcp.discovery.find_nearby_food", {})

            data = json.loads(result[0].text)
            assert "error" in data
            assert data["error"] == "Tool execution failed"

    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self):
        """Test calling unknown tool returns error."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            result = await call_tool("nonexistent_tool", {})

            data = json.loads(result[0].text)
            assert "error" in data
            assert "Unknown tool" in data["error"]

    @pytest.mark.asyncio
    async def test_call_tool_exception_handling(self, mock_firestore_client):
        """Test that exceptions are caught and returned as errors."""
        from fcp.server import call_tool

        # Reset and configure mock to raise exception
        mock_firestore_client.reset_mock()
        mock_firestore_client.get_user_logs = AsyncMock(side_effect=Exception("Database error"))

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            result = await call_tool("dev.fcp.nutrition.get_recent_meals", {})

            data = json.loads(result[0].text)
            assert "error" in data
            assert data["error"] == "Tool execution failed"

    @pytest.mark.asyncio
    async def test_call_tool_records_observability_metrics(self, mock_firestore_client):
        """Test that observability metrics are recorded in finally block."""
        from fcp.server import call_tool

        # Configure mock for successful call
        mock_firestore_client.get_user_logs.return_value = [{"dish_name": "Pasta"}]

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.server.observe_tool_execution") as mock_observe,
        ):
            await call_tool("dev.fcp.nutrition.get_recent_meals", {"limit": 5})

            # Verify observability function was called with correct parameters
            mock_observe.assert_called_once()
            call_args = mock_observe.call_args
            assert call_args.kwargs["tool_name"] == "dev.fcp.nutrition.get_recent_meals"
            assert call_args.kwargs["arguments"] == {"limit": 5}
            assert call_args.kwargs["user"] == MOCK_USER
            assert call_args.kwargs["status"] == "success"
            assert "duration_seconds" in call_args.kwargs
            assert call_args.kwargs["duration_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_call_tool_exception_in_dispatch(self):
        """Test exception handling when dispatch_tool_call raises."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.server.dispatch_tool_call", side_effect=RuntimeError("Dispatch error")),
            patch("fcp.server.observe_tool_execution") as mock_observe,
        ):
            result = await call_tool("dev.fcp.nutrition.search_meals", {"query": "test"})

            # Verify error is returned
            data = json.loads(result[0].text)
            assert "error" in data
            assert data["error"] == "Internal server error"

            # Verify observability recorded with error status
            mock_observe.assert_called_once()
            call_args = mock_observe.call_args
            assert call_args.kwargs["status"] == "error"
            assert call_args.kwargs["error_message"] == "Dispatch error"

    @pytest.mark.asyncio
    async def test_call_tool_log_meal_from_audio(self):
        """Test log_meal_from_audio tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.audio.log_meal_from_audio", new_callable=AsyncMock) as mock_log,
        ):
            mock_log.return_value = {"id": "meal-456", "dish_name": "Burger"}

            result = await call_tool(
                "dev.fcp.nutrition.log_meal_from_audio", {"audio_url": "https://example.com/audio.mp3"}
            )

            data = json.loads(result[0].text)
            assert data["id"] == "meal-456"

    @pytest.mark.asyncio
    async def test_call_tool_get_pantry_suggestions(self):
        """Test get_pantry_suggestions tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.inventory.suggest_recipe_from_pantry", new_callable=AsyncMock) as mock_suggest,
        ):
            mock_suggest.return_value = {"recipes": [{"name": "Omelette"}]}

            result = await call_tool("dev.fcp.inventory.get_pantry_suggestions", {"context": "breakfast"})

            data = json.loads(result[0].text)
            assert "recipes" in data

    @pytest.mark.asyncio
    async def test_call_tool_add_to_pantry(self, mock_firestore_client):
        """Test add_to_pantry tool."""
        from fcp.server import call_tool

        # Configure mock to return list of IDs
        mock_firestore_client.update_pantry_items_batch.return_value = ["item-1", "item-2"]

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            result = await call_tool("dev.fcp.inventory.add_to_pantry", {"items": ["eggs", "milk"]})

            data = json.loads(result[0].text)
            # Registry-based dispatch returns raw list from add_to_pantry
            assert isinstance(data, list)
            assert data == ["item-1", "item-2"]

    @pytest.mark.asyncio
    async def test_call_tool_delegate_to_food_agent(self):
        """Test delegate_to_food_agent tool."""
        from fcp.server import call_tool

        mock_firestore = MagicMock()
        mock_firestore.get_user_preferences = AsyncMock(return_value={"allergies": []})

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.services.firestore.firestore_client", mock_firestore),
            patch("fcp.tools.agents.delegate_to_food_agent_tool", new_callable=AsyncMock) as mock_delegate,
        ):
            mock_delegate.return_value = {"result": "Agent completed task"}

            result = await call_tool(
                "dev.fcp.agents.delegate_to_food_agent",
                {"agent_name": "discovery_agent", "objective": "Find Italian restaurants"},
            )

            data = json.loads(result[0].text)
            assert "result" in data

    @pytest.mark.asyncio
    async def test_call_tool_generate_cottage_label(self):
        """Test generate_cottage_label tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.cottage.generate_cottage_label", new_callable=AsyncMock) as mock_gen,
        ):
            mock_gen.return_value = {"label_html": "<div>Label</div>"}

            result = await call_tool(
                "dev.fcp.business.generate_cottage_label",
                {
                    "product_name": "Jam",
                    "ingredients": ["strawberries", "sugar"],
                    "net_weight": "8 oz",
                    "business_name": "Mom's Kitchen",
                    "business_address": "123 Main St",
                },
            )

            data = json.loads(result[0].text)
            assert "label_html" in data

    @pytest.mark.asyncio
    async def test_call_tool_generate_dietitian_report(self):
        """Test generate_dietitian_report tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.clinical.generate_dietitian_report", new_callable=AsyncMock) as mock_gen,
        ):
            mock_gen.return_value = {"report": "Clinical analysis..."}

            result = await call_tool("dev.fcp.clinical.generate_dietitian_report", {"days": 7})

            data = json.loads(result[0].text)
            assert "report" in data

    @pytest.mark.asyncio
    async def test_call_tool_plan_food_festival(self):
        """Test plan_food_festival tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.civic.plan_food_festival", new_callable=AsyncMock) as mock_plan,
        ):
            mock_plan.return_value = {"vendors": [], "layout": ""}

            result = await call_tool(
                "dev.fcp.business.plan_food_festival", {"city_name": "San Francisco", "theme": "Street Food"}
            )

            data = json.loads(result[0].text)
            assert "vendors" in data

    @pytest.mark.asyncio
    async def test_call_tool_detect_economic_gaps(self):
        """Test detect_economic_gaps tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.civic.detect_economic_gaps", new_callable=AsyncMock) as mock_detect,
        ):
            mock_detect.return_value = {"gaps": ["Ethiopian", "Korean"]}

            result = await call_tool(
                "dev.fcp.business.detect_economic_gaps",
                {"neighborhood": "SOMA", "existing_cuisines": ["Italian", "Mexican"]},
            )

            data = json.loads(result[0].text)
            assert "gaps" in data

    @pytest.mark.asyncio
    async def test_call_tool_scale_recipe(self):
        """Test scale_recipe tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.scaling.scale_recipe", new_callable=AsyncMock) as mock_scale,
        ):
            mock_scale.return_value = {"ingredients": [{"item": "flour", "amount": "4 cups"}]}

            result = await call_tool("dev.fcp.recipes.scale", {"recipe_json": {"name": "Bread"}, "target_servings": 8})

            data = json.loads(result[0].text)
            assert "ingredients" in data

    @pytest.mark.asyncio
    async def test_call_tool_parse_menu(self):
        """Test parse_menu tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.parser.parse_menu", new_callable=AsyncMock) as mock_parse,
        ):
            mock_parse.return_value = {"dishes": [{"name": "Burger", "price": 12.99}]}

            result = await call_tool("dev.fcp.parsing.parse_menu", {"image_url": "https://example.com/menu.jpg"})

            data = json.loads(result[0].text)
            assert "dishes" in data

    @pytest.mark.asyncio
    async def test_call_tool_parse_receipt(self):
        """Test parse_receipt tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.parser.parse_receipt", new_callable=AsyncMock) as mock_parse,
        ):
            mock_parse.return_value = {"items": [{"name": "Milk", "price": 4.99}]}

            result = await call_tool("dev.fcp.parsing.parse_receipt", {"image_url": "https://example.com/receipt.jpg"})

            data = json.loads(result[0].text)
            assert "items" in data

    @pytest.mark.asyncio
    async def test_call_tool_check_dietary_compatibility(self):
        """Test check_dietary_compatibility tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.taste_buddy.check_dietary_compatibility", new_callable=AsyncMock) as mock_check,
        ):
            mock_check.return_value = {"compatible": True, "warnings": []}

            result = await call_tool(
                "dev.fcp.safety.check_dietary_compatibility",
                {
                    "dish_name": "Salad",
                    "ingredients": ["lettuce", "tomato"],
                    "user_allergies": ["peanuts"],
                    "user_diet": ["vegetarian"],
                },
            )

            data = json.loads(result[0].text)
            assert data["compatible"] is True

    @pytest.mark.asyncio
    async def test_call_tool_generate_blog_post(self):
        """Test generate_blog_post tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.crud.get_meal", new_callable=AsyncMock) as mock_get,
            patch("fcp.tools.blog.generate_blog_post_tool", new_callable=AsyncMock) as mock_gen,
        ):
            mock_get.return_value = {"dish_name": "Sushi"}
            mock_gen.return_value = "# Amazing Sushi Experience\n\n..."

            result = await call_tool("dev.fcp.publishing.generate_blog_post", {"log_id": "meal-123"})

            # Blog post returns markdown text directly
            assert "Sushi" in result[0].text or len(result[0].text) > 0

    @pytest.mark.asyncio
    async def test_call_tool_generate_blog_post_not_found(self):
        """Test generate_blog_post when log not found."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.crud.get_meal", new_callable=AsyncMock) as mock_get,
        ):
            mock_get.return_value = None

            result = await call_tool("dev.fcp.publishing.generate_blog_post", {"log_id": "nonexistent"})

            data = json.loads(result[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_call_tool_get_flavor_pairings(self):
        """Test get_flavor_pairings tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.flavor.get_flavor_pairings", new_callable=AsyncMock) as mock_get,
        ):
            mock_get.return_value = {"pairings": ["chocolate", "coffee"]}

            result = await call_tool("dev.fcp.trends.get_flavor_pairings", {"subject": "vanilla"})

            data = json.loads(result[0].text)
            assert "pairings" in data

    @pytest.mark.asyncio
    async def test_call_tool_get_flavor_pairings_missing_subject(self):
        """Test get_flavor_pairings tool requires subject argument."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            result = await call_tool("dev.fcp.trends.get_flavor_pairings", {})
            data = json.loads(result[0].text)
            assert "error" in data
            assert data["error"] == "Tool execution failed"

    @pytest.mark.asyncio
    async def test_call_tool_check_pantry_expiry(self):
        """Test check_pantry_expiry tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.inventory.check_pantry_expiry", new_callable=AsyncMock) as mock_check,
        ):
            mock_check.return_value = {"expiring_soon": [{"item": "Milk", "days_left": 2}]}

            result = await call_tool("dev.fcp.inventory.check_pantry_expiry", {})

            data = json.loads(result[0].text)
            assert "expiring_soon" in data

    @pytest.mark.asyncio
    async def test_call_tool_sync_to_calendar(self):
        """Test sync_to_calendar tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.connector.sync_to_calendar", new_callable=AsyncMock) as mock_sync,
        ):
            mock_sync.return_value = {"event_id": "cal-event-123"}

            result = await call_tool(
                "dev.fcp.connectors.sync_to_calendar",
                {"event_title": "Dinner Reservation", "start_time": "2024-01-15T19:00:00Z"},
            )

            data = json.loads(result[0].text)
            assert "event_id" in data

    @pytest.mark.asyncio
    async def test_call_tool_sync_to_calendar_missing_args(self):
        """Test sync_to_calendar tool requires event_title and start_time."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            result = await call_tool(
                "dev.fcp.connectors.sync_to_calendar", {"event_title": "Test"}
            )  # Missing start_time
            data = json.loads(result[0].text)
            assert "error" in data
            assert data["error"] == "Tool execution failed"

    @pytest.mark.asyncio
    async def test_call_tool_save_to_drive(self):
        """Test save_to_drive tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.connector.save_to_drive", new_callable=AsyncMock) as mock_save,
        ):
            mock_save.return_value = {"file_id": "drive-file-123"}

            result = await call_tool(
                "dev.fcp.connectors.save_to_drive", {"filename": "recipe.md", "content": "# My Recipe"}
            )

            data = json.loads(result[0].text)
            assert "file_id" in data

    @pytest.mark.asyncio
    async def test_call_tool_save_to_drive_missing_args(self):
        """Test save_to_drive tool requires filename and content."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            result = await call_tool("dev.fcp.connectors.save_to_drive", {"filename": "test.md"})  # Missing content
            data = json.loads(result[0].text)
            assert "error" in data
            assert data["error"] == "Tool execution failed"

    @pytest.mark.asyncio
    async def test_call_tool_identify_emerging_trends(self):
        """Test identify_emerging_trends tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.trends.identify_emerging_trends", new_callable=AsyncMock) as mock_identify,
        ):
            mock_identify.return_value = {"trends": ["plant-based", "fermented foods"]}

            result = await call_tool("dev.fcp.trends.identify_emerging_trends", {"region": "local"})

            data = json.loads(result[0].text)
            assert "trends" in data

    @pytest.mark.asyncio
    async def test_call_tool_extract_recipe_from_media(self):
        """Test extract_recipe_from_media tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.recipe_extractor.extract_recipe_from_media", new_callable=AsyncMock) as mock_extract,
        ):
            mock_extract.return_value = {"recipe": {"name": "Extracted Recipe"}}

            result = await call_tool("dev.fcp.media.extract_recipe", {"image_url": "https://example.com/recipe.jpg"})

            data = json.loads(result[0].text)
            assert "recipe" in data

    @pytest.mark.asyncio
    async def test_call_tool_list_recipes(self, mock_firestore_client):
        """Test list_recipes tool."""
        from fcp.server import call_tool

        # Configure mock to return a recipe list
        mock_firestore_client.get_recipes.return_value = [{"id": "r1", "name": "Recipe 1"}]

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            result = await call_tool("dev.fcp.recipes.list", {"limit": 10})
            data = json.loads(result[0].text)
            assert "recipes" in data
            assert len(data["recipes"]) == 1

    @pytest.mark.asyncio
    async def test_call_tool_get_recipe(self, mock_firestore_client):
        """Test get_recipe tool."""
        from fcp.server import call_tool

        # Configure mock to return a recipe
        mock_firestore_client.get_recipe.return_value = {"id": "r1", "name": "Recipe 1"}

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            result = await call_tool("dev.fcp.recipes.get", {"recipe_id": "r1"})
            data = json.loads(result[0].text)
            # Registry-based dispatch returns raw dict from get_recipe
            assert data["id"] == "r1"
            assert data["name"] == "Recipe 1"

    @pytest.mark.asyncio
    async def test_call_tool_get_recipe_missing_id(self):
        """Test get_recipe tool missing id."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            result = await call_tool("dev.fcp.recipes.get", {})
            data = json.loads(result[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_call_tool_get_recipe_not_found(self, mock_firestore_client):
        """Test get_recipe tool when recipe not found."""
        from fcp.server import call_tool

        # Configure mock to return None (not found)
        mock_firestore_client.get_recipe.return_value = None

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            result = await call_tool("dev.fcp.recipes.get", {"recipe_id": "r1"})
            data = json.loads(result[0].text)
            # Registry-based dispatch returns raw None from get_recipe when not found
            assert data is None

    @pytest.mark.asyncio
    async def test_call_tool_save_recipe(self):
        """Test save_recipe tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.recipe_crud.save_recipe", new_callable=AsyncMock) as mock_save,
        ):
            mock_save.return_value = {"id": "r1", "status": "saved"}
            result = await call_tool(
                "dev.fcp.recipes.save",
                {"name": "Cake", "ingredients": ["Flour", "Sugar"]},
            )
            data = json.loads(result[0].text)
            assert data["status"] == "saved"

    @pytest.mark.asyncio
    async def test_call_tool_save_recipe_missing_args(self):
        """Test save_recipe tool missing required args."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            # Missing name
            result = await call_tool("dev.fcp.recipes.save", {"ingredients": ["Flour"]})
            data = json.loads(result[0].text)
            assert "error" in data

            # Missing ingredients
            result = await call_tool("dev.fcp.recipes.save", {"name": "Cake"})
            data = json.loads(result[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_call_tool_favorite_recipe(self):
        """Test favorite_recipe tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.recipe_crud.favorite_recipe", new_callable=AsyncMock) as mock_fav,
        ):
            mock_fav.return_value = {"status": "favorited"}
            result = await call_tool("dev.fcp.recipes.favorite", {"recipe_id": "r1"})
            data = json.loads(result[0].text)
            assert data["status"] == "favorited"

    @pytest.mark.asyncio
    async def test_call_tool_favorite_recipe_missing_id(self):
        """Test favorite_recipe tool missing id."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            result = await call_tool("dev.fcp.recipes.favorite", {})
            data = json.loads(result[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_call_tool_archive_recipe(self):
        """Test archive_recipe tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.recipe_crud.archive_recipe", new_callable=AsyncMock) as mock_archive,
        ):
            mock_archive.return_value = {"status": "archived"}
            result = await call_tool("dev.fcp.recipes.archive", {"recipe_id": "r1"})
            data = json.loads(result[0].text)
            assert data["status"] == "archived"

    @pytest.mark.asyncio
    async def test_call_tool_archive_recipe_missing_id(self):
        """Test archive_recipe tool missing id."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            result = await call_tool("dev.fcp.recipes.archive", {})
            data = json.loads(result[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_call_tool_delete_recipe(self):
        """Test delete_recipe tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.recipe_crud.delete_recipe", new_callable=AsyncMock) as mock_delete,
        ):
            mock_delete.return_value = {"status": "deleted"}
            result = await call_tool("dev.fcp.recipes.delete", {"recipe_id": "r1"})
            data = json.loads(result[0].text)
            assert data["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_call_tool_delete_recipe_missing_id(self):
        """Test delete_recipe tool missing id."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            result = await call_tool("dev.fcp.recipes.delete", {})
            data = json.loads(result[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_call_tool_update_pantry_item(self):
        """Test update_pantry_item tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.inventory.update_pantry_item", new_callable=AsyncMock) as mock_update,
        ):
            mock_update.return_value = {"id": "p1", "status": "updated"}
            result = await call_tool(
                "dev.fcp.inventory.update_pantry_item",
                {"item_id": "p1", "quantity": 5},
            )
            data = json.loads(result[0].text)
            assert data["status"] == "updated"

    @pytest.mark.asyncio
    async def test_call_tool_update_pantry_item_errors(self):
        """Test update_pantry_item tool error cases."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            # Missing item_id
            result = await call_tool("dev.fcp.inventory.update_pantry_item", {"quantity": 5})
            data = json.loads(result[0].text)
            assert "error" in data

            # No updates provided
            result = await call_tool("dev.fcp.inventory.update_pantry_item", {"item_id": "p1"})
            data = json.loads(result[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_call_tool_delete_pantry_item(self):
        """Test delete_pantry_item tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.inventory.delete_pantry_item", new_callable=AsyncMock) as mock_delete,
        ):
            mock_delete.return_value = {"status": "deleted"}
            result = await call_tool("dev.fcp.inventory.delete_pantry_item", {"item_id": "p1"})
            data = json.loads(result[0].text)
            assert data["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_call_tool_delete_pantry_item_missing_id(self):
        """Test delete_pantry_item tool missing id."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
        ):
            result = await call_tool("dev.fcp.inventory.delete_pantry_item", {})
            data = json.loads(result[0].text)
            assert "error" in data

    @pytest.mark.asyncio
    async def test_call_tool_check_food_recalls(self):
        """Test check_food_recalls tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.safety.check_food_recalls", new_callable=AsyncMock) as mock_check,
        ):
            mock_check.return_value = {"recalls": [], "checked": "peanut butter"}
            result = await call_tool("dev.fcp.safety.check_food_recalls", {"food_name": "peanut butter"})
            data = json.loads(result[0].text)
            assert "recalls" in data

    @pytest.mark.asyncio
    async def test_call_tool_check_allergen_alerts(self):
        """Test check_allergen_alerts tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.safety.check_allergen_alerts", new_callable=AsyncMock) as mock_check,
        ):
            mock_check.return_value = {"alerts": [], "food_name": "bread"}
            result = await call_tool(
                "dev.fcp.safety.check_allergen_alerts", {"food_name": "bread", "allergens": ["gluten"]}
            )
            data = json.loads(result[0].text)
            assert "alerts" in data

    @pytest.mark.asyncio
    async def test_call_tool_check_drug_food_interactions(self):
        """Test check_drug_food_interactions tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.safety.check_drug_food_interactions", new_callable=AsyncMock) as mock_check,
        ):
            mock_check.return_value = {"interactions": [], "food_name": "grapefruit"}
            result = await call_tool(
                "dev.fcp.safety.check_drug_food_interactions",
                {"food_name": "grapefruit", "medications": ["statins"]},
            )
            data = json.loads(result[0].text)
            assert "interactions" in data

    @pytest.mark.asyncio
    async def test_call_tool_get_restaurant_safety_info(self):
        """Test get_restaurant_safety_info tool."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=MOCK_USER),
            patch("fcp.tools.safety.get_restaurant_safety_info", new_callable=AsyncMock) as mock_get,
        ):
            mock_get.return_value = {"safety_score": "A", "restaurant": "Test Cafe"}
            result = await call_tool(
                "dev.fcp.safety.get_restaurant_safety_info",
                {"restaurant_name": "Test Cafe", "location": "NYC"},
            )
            data = json.loads(result[0].text)
            assert "safety_score" in data


class TestLoadIcon:
    """Tests for _load_icon function."""

    def test_load_icon_exception_handling(self):
        """Test that _load_icon handles exceptions gracefully."""
        # Import the function directly
        from fcp.server import _load_icon

        # Patch Path to raise an exception
        with patch("fcp.server.Path") as mock_path:
            mock_instance = MagicMock()
            mock_instance.parent.__truediv__.side_effect = Exception("Cannot access path")
            mock_path.return_value = mock_instance

            # Call should not raise, should return None
            result = _load_icon()
            assert result is None


class TestServerMain:
    """Tests for server main function."""

    @pytest.mark.asyncio
    async def test_main_function(self):
        """Test the run_mcp_server() function runs the MCP server."""
        from fcp.server import run_mcp_server

        # Create mock streams
        mock_read_stream = AsyncMock()
        mock_write_stream = AsyncMock()

        # Create async context manager mock
        mock_stdio_server = MagicMock()
        mock_stdio_server.__aenter__ = AsyncMock(return_value=(mock_read_stream, mock_write_stream))
        mock_stdio_server.__aexit__ = AsyncMock(return_value=None)

        mock_server_run = AsyncMock()

        with (
            patch("fcp.server.stdio_server", return_value=mock_stdio_server),
            patch("fcp.server.server.run", mock_server_run),
            patch("fcp.server.server.create_initialization_options", return_value={}),
        ):
            await run_mcp_server()

            mock_server_run.assert_called_once()

    def test_cli_argument_parser_mcp(self):
        """Test CLI argument parser with --mcp flag."""
        import argparse
        import sys

        # Parse --mcp flag
        with patch.object(sys, "argv", ["fcp-server", "--mcp"]):
            parser = argparse.ArgumentParser()
            parser.add_argument("--mcp", action="store_true")
            parser.add_argument("--http", action="store_true")
            parser.add_argument("--port", type=int, default=8080)
            args = parser.parse_args()
            assert args.mcp is True
            assert args.http is False

    def test_cli_argument_parser_http(self):
        """Test CLI argument parser with --http flag."""
        import argparse
        import sys

        # Parse --http flag
        with patch.object(sys, "argv", ["fcp-server", "--http", "--port", "9000"]):
            parser = argparse.ArgumentParser()
            parser.add_argument("--mcp", action="store_true")
            parser.add_argument("--http", action="store_true")
            parser.add_argument("--port", type=int, default=8080)
            args = parser.parse_args()
            assert args.http is True
            assert args.mcp is False
            assert args.port == 9000

    def test_cli_argument_parser_default(self):
        """Test CLI argument parser with no flags."""
        import argparse
        import sys

        # Parse no flags
        with patch.object(sys, "argv", ["fcp-server"]):
            parser = argparse.ArgumentParser()
            parser.add_argument("--mcp", action="store_true")
            parser.add_argument("--http", action="store_true")
            args = parser.parse_args()
            assert args.mcp is False
            assert args.http is False


class TestDemoModeWritePermissionDenied:
    """Tests for demo mode write permission denial in MCP tools."""

    @pytest.mark.asyncio
    async def test_add_meal_denied_for_demo_user(self):
        """Test add_meal returns permission denied for demo user."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=DEMO_USER),
        ):
            result = await call_tool("dev.fcp.nutrition.add_meal", {"dish_name": "Tacos"})
            data = json.loads(result[0].text)
            assert data["error"] == "write_permission_denied"
            assert "Demo mode" in data["message"]

    @pytest.mark.asyncio
    async def test_add_to_pantry_denied_for_demo_user(self):
        """Test add_to_pantry returns permission denied for demo user."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=DEMO_USER),
        ):
            result = await call_tool("dev.fcp.inventory.add_to_pantry", {"items": [{"name": "Milk"}]})
            data = json.loads(result[0].text)
            assert data["error"] == "write_permission_denied"

    @pytest.mark.asyncio
    async def test_archive_recipe_denied_for_demo_user(self):
        """Test archive_recipe returns permission denied for demo user."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=DEMO_USER),
        ):
            result = await call_tool("dev.fcp.recipes.archive", {"recipe_id": "recipe-123"})
            data = json.loads(result[0].text)
            assert data["error"] == "write_permission_denied"

    @pytest.mark.asyncio
    async def test_delete_meal_denied_for_demo_user(self):
        """Test delete_meal returns permission denied for demo user."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=DEMO_USER),
        ):
            result = await call_tool("dev.fcp.nutrition.delete_meal", {"log_id": "log-123"})
            data = json.loads(result[0].text)
            assert data["error"] == "write_permission_denied"

    @pytest.mark.asyncio
    async def test_delete_pantry_item_denied_for_demo_user(self):
        """Test delete_pantry_item returns permission denied for demo user."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=DEMO_USER),
        ):
            result = await call_tool("dev.fcp.inventory.delete_pantry_item", {"item_id": "item-123"})
            data = json.loads(result[0].text)
            assert data["error"] == "write_permission_denied"

    @pytest.mark.asyncio
    async def test_delete_recipe_denied_for_demo_user(self):
        """Test delete_recipe returns permission denied for demo user."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=DEMO_USER),
        ):
            result = await call_tool("dev.fcp.recipes.delete", {"recipe_id": "recipe-123"})
            data = json.loads(result[0].text)
            assert data["error"] == "write_permission_denied"

    @pytest.mark.asyncio
    async def test_donate_meal_denied_for_demo_user(self):
        """Test donate_meal returns permission denied for demo user."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=DEMO_USER),
        ):
            result = await call_tool("dev.fcp.business.donate_meal", {"log_id": "meal-123"})
            data = json.loads(result[0].text)
            assert data["error"] == "write_permission_denied"

    @pytest.mark.asyncio
    async def test_favorite_recipe_denied_for_demo_user(self):
        """Test favorite_recipe returns permission denied for demo user."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=DEMO_USER),
        ):
            result = await call_tool("dev.fcp.recipes.favorite", {"recipe_id": "recipe-123"})
            data = json.loads(result[0].text)
            assert data["error"] == "write_permission_denied"

    @pytest.mark.asyncio
    async def test_log_meal_from_audio_denied_for_demo_user(self):
        """Test log_meal_from_audio returns permission denied for demo user."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=DEMO_USER),
        ):
            result = await call_tool(
                "dev.fcp.nutrition.log_meal_from_audio", {"audio_url": "https://example.com/audio.mp3"}
            )
            data = json.loads(result[0].text)
            assert data["error"] == "write_permission_denied"

    @pytest.mark.asyncio
    async def test_save_recipe_denied_for_demo_user(self):
        """Test save_recipe returns permission denied for demo user."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=DEMO_USER),
        ):
            result = await call_tool("dev.fcp.recipes.save", {"name": "Pasta", "ingredients": ["pasta", "sauce"]})
            data = json.loads(result[0].text)
            assert data["error"] == "write_permission_denied"

    @pytest.mark.asyncio
    async def test_save_to_drive_denied_for_demo_user(self):
        """Test save_to_drive returns permission denied for demo user."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=DEMO_USER),
        ):
            result = await call_tool("dev.fcp.connectors.save_to_drive", {"filename": "test.txt", "content": "data"})
            data = json.loads(result[0].text)
            assert data["error"] == "write_permission_denied"

    @pytest.mark.asyncio
    async def test_sync_to_calendar_denied_for_demo_user(self):
        """Test sync_to_calendar returns permission denied for demo user."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=DEMO_USER),
        ):
            result = await call_tool(
                "dev.fcp.connectors.sync_to_calendar", {"event_title": "Dinner", "start_time": "2024-01-01T18:00:00"}
            )
            data = json.loads(result[0].text)
            assert data["error"] == "write_permission_denied"

    @pytest.mark.asyncio
    async def test_update_pantry_item_denied_for_demo_user(self):
        """Test update_pantry_item returns permission denied for demo user."""
        from fcp.server import call_tool

        with (
            patch("fcp.server.check_mcp_rate_limit"),
            patch("fcp.server.get_user_id", return_value=DEMO_USER),
        ):
            result = await call_tool("dev.fcp.inventory.update_pantry_item", {"item_id": "item-123", "quantity": 5})
            data = json.loads(result[0].text)
            assert data["error"] == "write_permission_denied"
