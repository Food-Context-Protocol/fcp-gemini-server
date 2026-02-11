"""Unit tests for CRUD tools."""

from unittest.mock import AsyncMock

import pytest

from fcp.mcp.container import DependencyContainer
from fcp.mcp.protocols import AIService, Database, HTTPClient
from fcp.tools.crud import add_meal, add_to_pantry, delete_meal, get_meals


@pytest.fixture
def mock_container():
    """Create a container with mocked dependencies."""
    mock_db = AsyncMock(spec=Database)
    return DependencyContainer(
        database=mock_db,
        ai_service=AsyncMock(spec=AIService),
        http_client=AsyncMock(spec=HTTPClient),
    )


class TestAddMeal:
    """Test add_meal tool."""

    @pytest.mark.asyncio
    async def test_add_meal_success(self, mock_container):
        """Test add_meal creates a log successfully."""
        # Arrange
        mock_container.database.create_log.return_value = "log_123"

        # Act
        result = await add_meal(
            user_id="user_456",
            dish_name="Spaghetti Carbonara",
            venue="Test Restaurant",
            notes="Delicious",
            db=mock_container.database,
        )

        # Assert
        assert result == {"success": True, "log_id": "log_123"}
        mock_container.database.create_log.assert_called_once()
        call_args = mock_container.database.create_log.call_args
        assert call_args[0][0] == "user_456"  # user_id
        assert call_args[0][1]["dish_name"] == "Spaghetti Carbonara"
        assert call_args[0][1]["venue_name"] == "Test Restaurant"
        assert call_args[0][1]["notes"] == "Delicious"
        assert call_args[0][1]["processing_status"] == "pending"

    @pytest.mark.asyncio
    async def test_add_meal_minimal(self, mock_container):
        """Test add_meal with only required parameters."""
        # Arrange
        mock_container.database.create_log.return_value = "log_456"

        # Act
        result = await add_meal(
            user_id="user_789",
            dish_name="Pizza",
            db=mock_container.database,
        )

        # Assert
        assert result == {"success": True, "log_id": "log_456"}
        mock_container.database.create_log.assert_called_once()
        call_args = mock_container.database.create_log.call_args
        assert call_args[0][1]["dish_name"] == "Pizza"
        assert call_args[0][1]["venue_name"] is None
        assert call_args[0][1]["notes"] is None

    @pytest.mark.asyncio
    async def test_add_meal_with_image(self, mock_container):
        """Test add_meal with image_path."""
        # Arrange
        mock_container.database.create_log.return_value = "log_789"

        # Act
        result = await add_meal(
            user_id="user_123",
            dish_name="Burger",
            image_path="/path/to/image.jpg",
            db=mock_container.database,
        )

        # Assert
        assert result == {"success": True, "log_id": "log_789"}
        call_args = mock_container.database.create_log.call_args
        assert call_args[0][1]["image_path"] == "/path/to/image.jpg"


class TestDeleteMeal:
    """Test delete_meal tool."""

    @pytest.mark.asyncio
    async def test_delete_meal_success(self, mock_container):
        """Test delete_meal marks a meal as deleted."""
        # Arrange
        mock_container.database.get_log.return_value = {"id": "log_123", "dish_name": "Pizza"}
        mock_container.database.update_log.return_value = None

        # Act
        result = await delete_meal(
            user_id="user_456",
            log_id="log_123",
            db=mock_container.database,
        )

        # Assert
        assert result == {"success": True}
        mock_container.database.get_log.assert_called_once_with("user_456", "log_123")
        mock_container.database.update_log.assert_called_once_with("user_456", "log_123", {"deleted": True})

    @pytest.mark.asyncio
    async def test_delete_meal_not_found(self, mock_container):
        """Test delete_meal when log doesn't exist."""
        # Arrange
        mock_container.database.get_log.return_value = None

        # Act
        result = await delete_meal(
            user_id="user_456",
            log_id="log_999",
            db=mock_container.database,
        )

        # Assert
        assert result == {"success": False, "error": "Log not found"}
        mock_container.database.get_log.assert_called_once_with("user_456", "log_999")
        mock_container.database.update_log.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_meal_update_fails(self, mock_container):
        """Test delete_meal when update fails."""
        # Arrange
        mock_container.database.get_log.return_value = {"id": "log_123"}
        mock_container.database.update_log.side_effect = Exception("Database error")

        # Act
        result = await delete_meal(
            user_id="user_456",
            log_id="log_123",
            db=mock_container.database,
        )

        # Assert
        assert result["success"] is False
        assert "deleting meal" in result["error"]
        mock_container.database.update_log.assert_called_once()


class TestGetMeals:
    """Test get_meals tool."""

    @pytest.mark.asyncio
    async def test_get_meals_default_params(self, mock_container):
        """Test get_meals with default parameters."""
        # Arrange
        mock_logs = [
            {"id": "log_1", "dish_name": "Pizza"},
            {"id": "log_2", "dish_name": "Pasta", "nutrition": {"calories": 500}},
        ]
        mock_container.database.get_user_logs.return_value = mock_logs

        # Act
        result = await get_meals(
            user_id="user_456",
            db=mock_container.database,
        )

        # Assert
        assert len(result) == 2
        assert result[0]["dish_name"] == "Pizza"
        assert result[1]["dish_name"] == "Pasta"
        # Nutrition should be removed by default
        assert "nutrition" not in result[1]
        mock_container.database.get_user_logs.assert_called_once_with(
            "user_456",
            limit=10,
            days=None,
            start_date=None,
            end_date=None,
        )

    @pytest.mark.asyncio
    async def test_get_meals_include_nutrition(self, mock_container):
        """Test get_meals with include_nutrition=True."""
        # Arrange
        mock_logs = [
            {"id": "log_1", "dish_name": "Pizza", "nutrition": {"calories": 600}},
        ]
        mock_container.database.get_user_logs.return_value = mock_logs

        # Act
        result = await get_meals(
            user_id="user_456",
            include_nutrition=True,
            db=mock_container.database,
        )

        # Assert
        assert len(result) == 1
        assert "nutrition" in result[0]
        assert result[0]["nutrition"]["calories"] == 600

    @pytest.mark.asyncio
    async def test_get_meals_with_limit(self, mock_container):
        """Test get_meals with custom limit."""
        # Arrange
        mock_container.database.get_user_logs.return_value = []

        # Act
        result = await get_meals(
            user_id="user_456",
            limit=5,
            db=mock_container.database,
        )

        # Assert
        assert result == []
        mock_container.database.get_user_logs.assert_called_once_with(
            "user_456",
            limit=5,
            days=None,
            start_date=None,
            end_date=None,
        )

    @pytest.mark.asyncio
    async def test_get_meals_with_days(self, mock_container):
        """Test get_meals with days filter."""
        # Arrange
        mock_container.database.get_user_logs.return_value = []

        # Act
        result = await get_meals(
            user_id="user_456",
            days=7,
            db=mock_container.database,
        )

        # Assert
        assert result == []
        mock_container.database.get_user_logs.assert_called_once_with(
            "user_456",
            limit=10,
            days=7,
            start_date=None,
            end_date=None,
        )

    @pytest.mark.asyncio
    async def test_get_meals_with_date_range(self, mock_container):
        """Test get_meals with start and end dates."""
        from datetime import datetime

        # Arrange
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 31)
        mock_container.database.get_user_logs.return_value = []

        # Act
        result = await get_meals(
            user_id="user_456",
            start_date=start,
            end_date=end,
            db=mock_container.database,
        )

        # Assert
        assert result == []
        mock_container.database.get_user_logs.assert_called_once_with(
            "user_456",
            limit=10,
            days=None,
            start_date=start,
            end_date=end,
        )


class TestAddToPantry:
    """Test add_to_pantry tool."""

    @pytest.mark.asyncio
    async def test_add_to_pantry_success(self, mock_container):
        """Test add_to_pantry adds items successfully."""
        # Arrange
        mock_container.database.update_pantry_items_batch.return_value = ["item_1", "item_2"]

        # Act
        result = await add_to_pantry(
            user_id="user_456",
            items=["Tomato", "Onion"],
            db=mock_container.database,
        )

        # Assert
        assert result == ["item_1", "item_2"]
        mock_container.database.update_pantry_items_batch.assert_called_once()
        call_args = mock_container.database.update_pantry_items_batch.call_args
        assert call_args[0][0] == "user_456"
        items_data = call_args[0][1]
        assert len(items_data) == 2
        assert items_data[0]["name"] == "Tomato"
        assert items_data[0]["quantity"] == 1
        assert items_data[0]["status"] == "in_stock"
        assert items_data[1]["name"] == "Onion"

    @pytest.mark.asyncio
    async def test_add_to_pantry_single_item(self, mock_container):
        """Test add_to_pantry with a single item."""
        # Arrange
        mock_container.database.update_pantry_items_batch.return_value = ["item_1"]

        # Act
        result = await add_to_pantry(
            user_id="user_789",
            items=["Garlic"],
            db=mock_container.database,
        )

        # Assert
        assert result == ["item_1"]
        call_args = mock_container.database.update_pantry_items_batch.call_args
        items_data = call_args[0][1]
        assert len(items_data) == 1
        assert items_data[0]["name"] == "Garlic"

    @pytest.mark.asyncio
    async def test_add_to_pantry_empty_list(self, mock_container):
        """Test add_to_pantry with empty items list."""
        # Arrange
        mock_container.database.update_pantry_items_batch.return_value = []

        # Act
        result = await add_to_pantry(
            user_id="user_456",
            items=[],
            db=mock_container.database,
        )

        # Assert
        assert result == []
        call_args = mock_container.database.update_pantry_items_batch.call_args
        items_data = call_args[0][1]
        assert len(items_data) == 0
