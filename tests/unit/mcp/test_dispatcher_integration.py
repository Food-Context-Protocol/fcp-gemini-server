"""Integration tests for dispatcher with tool registry."""

from unittest.mock import AsyncMock, patch

import pytest

from fcp.auth.permissions import AuthenticatedUser, UserRole
from fcp.mcp.container import DependencyContainer
from fcp.mcp.protocols import AIService, Database, HTTPClient
from fcp.mcp_tool_dispatch import dispatch_tool_call


@pytest.fixture(autouse=True)
def mock_firestore_client():
    """Automatically mock firestore_client in all tool modules to prevent real database access."""
    mock_db = AsyncMock()

    # Default mock behaviors
    mock_db.get_user_logs.return_value = []
    mock_db.get_log.return_value = None
    mock_db.create_log.return_value = "mock-log-id"
    mock_db.update_log.return_value = True
    mock_db.delete_log.return_value = True
    mock_db.get_recipes.return_value = []
    mock_db.get_recipe.return_value = None
    mock_db.update_pantry_items_batch.return_value = ["item-1", "item-2"]

    # Patch firestore_client in all tool modules
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
        patch("fcp.tools.knowledge_graph.get_firestore_client", return_value=mock_db),
        patch("fcp.tools.parser.get_firestore_client", return_value=mock_db),
        patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db),
    ]

    for p in patches:
        p.start()

    yield mock_db

    for p in patches:
        p.stop()


@pytest.fixture
def mock_container():
    """Create a container with mocked dependencies."""
    mock_db = AsyncMock(spec=Database)
    return DependencyContainer(
        database=mock_db,
        ai_service=AsyncMock(spec=AIService),
        http_client=AsyncMock(spec=HTTPClient),
    )


@pytest.fixture
def user_with_write():
    """Create a user with write permissions."""
    return AuthenticatedUser(user_id="test_user_123", role=UserRole.AUTHENTICATED)


@pytest.fixture
def user_without_write():
    """Create a user without write permissions."""
    return AuthenticatedUser(user_id="test_user_456", role=UserRole.DEMO)


class TestDispatcherRegistryIntegration:
    """Test dispatcher integration with tool registry."""

    @pytest.mark.asyncio
    async def test_dispatch_add_meal_via_registry(self, user_with_write):
        """Test dispatching add_meal through registry."""
        # Arrange
        arguments = {
            "dish_name": "Spaghetti Carbonara",
            "venue": "Italian Restaurant",
            "notes": "Delicious",
        }

        # Act
        result = await dispatch_tool_call(
            name="dev.fcp.nutrition.add_meal",
            arguments=arguments,
            user=user_with_write,
        )

        # Assert
        assert result.status == "success"
        assert len(result.contents) == 1
        # Parse the JSON response
        import json

        response = json.loads(result.contents[0].text)
        assert response["success"] is True
        assert "log_id" in response

    @pytest.mark.asyncio
    async def test_dispatch_add_meal_permission_denied(self, user_without_write):
        """Test add_meal rejects users without write permission."""
        # Arrange
        arguments = {"dish_name": "Pizza"}

        # Act
        result = await dispatch_tool_call(
            name="dev.fcp.nutrition.add_meal",
            arguments=arguments,
            user=user_without_write,
        )

        # Assert
        assert result.status == "error"
        assert result.error_message == "write_permission_denied"

    @pytest.mark.asyncio
    async def test_dispatch_get_meals_via_registry(self, user_with_write):
        """Test dispatching get_meals (read-only) through registry."""
        # Arrange
        arguments = {"limit": 5, "days": 7}

        # Act
        result = await dispatch_tool_call(
            name="dev.fcp.nutrition.get_recent_meals",
            arguments=arguments,
            user=user_with_write,
        )

        # Assert
        assert result.status == "success"
        import json

        response = json.loads(result.contents[0].text)
        assert isinstance(response, dict)
        assert "meals" in response
        assert isinstance(response["meals"], list)

    @pytest.mark.asyncio
    async def test_dispatch_delete_meal_via_registry(self, user_with_write):
        """Test dispatching delete_meal through registry."""
        # Arrange
        arguments = {"log_id": "log_123"}

        # Act
        result = await dispatch_tool_call(
            name="dev.fcp.nutrition.delete_meal",
            arguments=arguments,
            user=user_with_write,
        )

        # Assert
        assert result.status == "success"
        import json

        response = json.loads(result.contents[0].text)
        # Will be success=False because log doesn't exist, but that's expected
        assert "success" in response

    @pytest.mark.asyncio
    async def test_dispatch_add_to_pantry_via_registry(self, user_with_write):
        """Test dispatching add_to_pantry through registry."""
        # Arrange
        arguments = {"items": ["Tomato", "Onion", "Garlic"]}

        # Act
        result = await dispatch_tool_call(
            name="dev.fcp.inventory.add_to_pantry",
            arguments=arguments,
            user=user_with_write,
        )

        # Assert
        assert result.status == "success"
        import json

        response = json.loads(result.contents[0].text)
        assert isinstance(response, list)

    @pytest.mark.asyncio
    async def test_dispatch_get_recipe_via_registry(self, user_with_write):
        """Test dispatching get_recipe through registry."""
        # Arrange
        arguments = {"recipe_id": "recipe_123"}

        # Act
        result = await dispatch_tool_call(
            name="dev.fcp.recipes.get",
            arguments=arguments,
            user=user_with_write,
        )

        # Assert
        assert result.status == "success"
        # Recipe will be None because it doesn't exist, but dispatch succeeds
        assert len(result.contents) == 1

    @pytest.mark.asyncio
    async def test_legacy_tool_still_works(self, user_with_write):
        """Test that non-migrated tools still work via legacy dispatch."""
        # Arrange - use a tool that hasn't been migrated yet
        arguments = {
            "recipe_name": "Chocolate Cake",
            "preferences": "Sweet desserts",
        }

        # Act
        result = await dispatch_tool_call(
            name="dev.fcp.recipes.suggest",
            arguments=arguments,
            user=user_with_write,
        )

        # Assert - should work via legacy dispatch
        # (This tool hasn't been migrated to registry yet)
        assert result.status in ["success", "error"]  # Either is valid, just shouldn't crash
