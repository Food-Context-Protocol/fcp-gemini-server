"""Unit tests for recipe CRUD tools."""

from unittest.mock import AsyncMock, patch

import pytest

from fcp.mcp.container import DependencyContainer
from fcp.mcp.protocols import AIService, Database, HTTPClient
from fcp.tools.recipe_crud import (
    archive_recipe,
    delete_recipe,
    favorite_recipe,
    get_recipe,
    list_recipes,
    save_recipe,
    update_recipe,
)


@pytest.fixture
def mock_container():
    """Create a container with mocked dependencies."""
    mock_db = AsyncMock(spec=Database)
    return DependencyContainer(
        database=mock_db,
        ai_service=AsyncMock(spec=AIService),
        http_client=AsyncMock(spec=HTTPClient),
    )


class TestGetRecipe:
    """Test get_recipe tool."""

    @pytest.mark.asyncio
    async def test_get_recipe_found(self, mock_container):
        """Test get_recipe returns a recipe successfully."""
        # Arrange
        mock_recipe = {
            "id": "recipe_123",
            "name": "Spaghetti Carbonara",
            "ingredients": ["pasta", "eggs", "bacon"],
            "servings": 4,
        }
        mock_container.database.get_recipe.return_value = mock_recipe

        # Act
        result = await get_recipe(
            user_id="user_456",
            recipe_id="recipe_123",
            db=mock_container.database,
        )

        # Assert
        assert result == mock_recipe
        mock_container.database.get_recipe.assert_called_once_with("user_456", "recipe_123")

    @pytest.mark.asyncio
    async def test_get_recipe_not_found(self, mock_container):
        """Test get_recipe returns None when recipe doesn't exist."""
        # Arrange
        mock_container.database.get_recipe.return_value = None

        # Act
        result = await get_recipe(
            user_id="user_456",
            recipe_id="recipe_999",
            db=mock_container.database,
        )

        # Assert
        assert result is None
        mock_container.database.get_recipe.assert_called_once_with("user_456", "recipe_999")

    @pytest.mark.asyncio
    async def test_get_recipe_with_full_data(self, mock_container):
        """Test get_recipe with comprehensive recipe data."""
        # Arrange
        mock_recipe = {
            "id": "recipe_456",
            "name": "Chicken Tikka Masala",
            "ingredients": ["chicken", "yogurt", "spices", "tomatoes"],
            "instructions": ["Marinate chicken", "Cook sauce", "Combine and simmer"],
            "servings": 6,
            "prep_time_minutes": 30,
            "cook_time_minutes": 45,
            "cuisine": "Indian",
            "tags": ["spicy", "main course"],
            "nutrition": {"calories": 450, "protein": 35},
        }
        mock_container.database.get_recipe.return_value = mock_recipe

        # Act
        result = await get_recipe(
            user_id="user_789",
            recipe_id="recipe_456",
            db=mock_container.database,
        )

        # Assert
        assert result == mock_recipe
        assert result["name"] == "Chicken Tikka Masala"
        assert len(result["ingredients"]) == 4
        assert result["cuisine"] == "Indian"
        assert result["nutrition"]["calories"] == 450


class TestListRecipes:
    """Test list_recipes function."""

    @pytest.mark.asyncio
    async def test_list_recipes_returns_default_results(self):
        """Test list_recipes with default parameters."""
        # Arrange
        mock_db = AsyncMock(spec=Database)
        mock_recipes = [
            {"id": "r1", "name": "Recipe 1", "is_archived": False},
            {"id": "r2", "name": "Recipe 2", "is_archived": False},
        ]
        mock_db.get_recipes.return_value = mock_recipes

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await list_recipes(user_id="user_123")

            # Assert
            assert result == mock_recipes
            mock_db.get_recipes.assert_called_once_with(
                "user_123",
                limit=50,
                include_archived=False,
                favorites_only=False,
            )

    @pytest.mark.asyncio
    async def test_list_recipes_with_custom_params(self):
        """Test list_recipes with custom limit and filters."""
        # Arrange
        mock_db = AsyncMock(spec=Database)
        mock_recipes = [
            {"id": "r1", "name": "Favorite Recipe", "is_favorite": True},
        ]
        mock_db.get_recipes.return_value = mock_recipes

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await list_recipes(
                user_id="user_456",
                limit=20,
                include_archived=True,
                favorites_only=True,
            )

            # Assert
            assert result == mock_recipes
            mock_db.get_recipes.assert_called_once_with(
                "user_456",
                limit=20,
                include_archived=True,
                favorites_only=True,
            )


class TestSaveRecipe:
    """Test save_recipe function."""

    @pytest.mark.asyncio
    async def test_save_recipe_requires_name(self):
        """Test save_recipe fails when name is missing."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.create_recipe = AsyncMock()

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await save_recipe(
                user_id="user_123",
                name="",  # Empty name
                ingredients=["flour", "water"],
            )

            # Assert
            assert result["success"] is False
            assert "name is required" in result["error"].lower()
            mock_db.create_recipe.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_recipe_requires_ingredients(self):
        """Test save_recipe fails when ingredients are missing."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.create_recipe = AsyncMock()

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await save_recipe(
                user_id="user_123",
                name="Test Recipe",
                ingredients=[],  # Empty list
            )

            # Assert
            assert result["success"] is False
            assert "ingredients are required" in result["error"].lower()
            mock_db.create_recipe.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_recipe_minimal_success(self):
        """Test save_recipe succeeds with minimal required fields."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.create_recipe = AsyncMock(return_value="recipe_abc123")

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await save_recipe(
                user_id="user_456",
                name="Simple Recipe",
                ingredients=["ingredient1", "ingredient2"],
            )

            # Assert
            assert result["success"] is True
            assert result["recipe_id"] == "recipe_abc123"
            mock_db.create_recipe.assert_called_once()
            call_args = mock_db.create_recipe.call_args
            assert call_args[0][0] == "user_456"  # user_id
            recipe_data = call_args[0][1]
            assert recipe_data["name"] == "Simple Recipe"
            assert recipe_data["ingredients"] == ["ingredient1", "ingredient2"]
            assert recipe_data["servings"] == 4  # default

    @pytest.mark.asyncio
    async def test_save_recipe_with_all_fields(self):
        """Test save_recipe with complete data including optional fields."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.create_recipe = AsyncMock(return_value="recipe_xyz789")

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await save_recipe(
                user_id="user_789",
                name="Complex Recipe",
                ingredients=["a", "b", "c"],
                instructions=["step1", "step2"],
                servings=6,
                description="A delicious dish",
                prep_time_minutes=15,
                cook_time_minutes=30,
                cuisine="Italian",
                tags=["vegetarian", "quick"],
                source="https://example.com/recipe",
                source_meal_id="meal_123",
                image_url="https://example.com/image.jpg",
                nutrition={"calories": 350, "protein": 20},
            )

            # Assert
            assert result["success"] is True
            assert result["recipe_id"] == "recipe_xyz789"
            call_args = mock_db.create_recipe.call_args
            recipe_data = call_args[0][1]
            assert recipe_data["description"] == "A delicious dish"
            assert recipe_data["cuisine"] == "Italian"
            assert recipe_data["nutrition"]["calories"] == 350

    @pytest.mark.asyncio
    async def test_save_recipe_handles_db_error(self):
        """Test save_recipe handles database errors gracefully."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.create_recipe = AsyncMock(side_effect=Exception("Database connection failed"))

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await save_recipe(
                user_id="user_999",
                name="Test Recipe",
                ingredients=["flour"],
            )

            # Assert
            assert result["success"] is False
            assert "saving recipe" in result["error"]


class TestUpdateRecipe:
    """Test update_recipe function."""

    @pytest.mark.asyncio
    async def test_update_recipe_requires_updates(self):
        """Test update_recipe fails when updates dict is empty."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.get_recipe = AsyncMock()
        mock_db.update_recipe = AsyncMock()

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await update_recipe(
                user_id="user_123",
                recipe_id="recipe_456",
                updates={},  # Empty updates
            )

            # Assert
            assert result["success"] is False
            assert "no update fields" in result["error"].lower()
            mock_db.get_recipe.assert_not_called()
            mock_db.update_recipe.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_recipe_not_found(self):
        """Test update_recipe fails when recipe doesn't exist."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.get_recipe = AsyncMock(return_value=None)  # Recipe not found
        mock_db.update_recipe = AsyncMock()

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await update_recipe(
                user_id="user_123",
                recipe_id="recipe_999",
                updates={"name": "New Name"},
            )

            # Assert
            assert result["success"] is False
            assert "not found" in result["error"].lower()
            assert "recipe_999" in result["error"]
            mock_db.get_recipe.assert_called_once_with("user_123", "recipe_999")
            mock_db.update_recipe.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_recipe_success(self):
        """Test update_recipe succeeds with valid data."""
        # Arrange
        mock_db = AsyncMock()
        existing_recipe = {"id": "recipe_abc", "name": "Old Name", "servings": 4}
        mock_db.get_recipe = AsyncMock(return_value=existing_recipe)
        mock_db.update_recipe = AsyncMock(return_value=True)

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await update_recipe(
                user_id="user_456",
                recipe_id="recipe_abc",
                updates={"name": "Updated Name", "servings": 6},
            )

            # Assert
            assert result["success"] is True
            mock_db.get_recipe.assert_called_once_with("user_456", "recipe_abc")
            mock_db.update_recipe.assert_called_once_with(
                "user_456",
                "recipe_abc",
                {"name": "Updated Name", "servings": 6},
            )

    @pytest.mark.asyncio
    async def test_update_recipe_db_failure(self):
        """Test update_recipe when database update returns False."""
        # Arrange
        mock_db = AsyncMock()
        existing_recipe = {"id": "recipe_xyz", "name": "Existing"}
        mock_db.get_recipe = AsyncMock(return_value=existing_recipe)
        mock_db.update_recipe = AsyncMock(return_value=False)  # Update failed

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await update_recipe(
                user_id="user_789",
                recipe_id="recipe_xyz",
                updates={"name": "New Name"},
            )

            # Assert
            assert result["success"] is False
            assert "update failed" in result["error"].lower()
            mock_db.get_recipe.assert_called_once_with("user_789", "recipe_xyz")
            mock_db.update_recipe.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_recipe_handles_exception(self):
        """Test update_recipe handles database exceptions gracefully."""
        # Arrange
        mock_db = AsyncMock()
        existing_recipe = {"id": "recipe_def", "name": "Test"}
        mock_db.get_recipe = AsyncMock(return_value=existing_recipe)
        mock_db.update_recipe = AsyncMock(side_effect=Exception("Connection timeout"))

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await update_recipe(
                user_id="user_321",
                recipe_id="recipe_def",
                updates={"servings": 8},
            )

            # Assert
            assert result["success"] is False
            assert "updating recipe" in result["error"]
            mock_db.get_recipe.assert_called_once_with("user_321", "recipe_def")
            mock_db.update_recipe.assert_called_once()


class TestFavoriteRecipe:
    """Test favorite_recipe function."""

    @pytest.mark.asyncio
    async def test_favorite_recipe_not_found(self):
        """Test favorite_recipe fails when recipe doesn't exist."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.get_recipe = AsyncMock(return_value=None)  # Recipe not found
        mock_db.update_recipe = AsyncMock()

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await favorite_recipe(
                user_id="user_123",
                recipe_id="recipe_999",
                is_favorite=True,
            )

            # Assert
            assert result["success"] is False
            assert "not found" in result["error"].lower()
            assert "recipe_999" in result["error"]
            mock_db.get_recipe.assert_called_once_with("user_123", "recipe_999")
            mock_db.update_recipe.assert_not_called()

    @pytest.mark.asyncio
    async def test_favorite_recipe_mark_favorite(self):
        """Test favorite_recipe successfully marks recipe as favorite."""
        # Arrange
        mock_db = AsyncMock()
        existing_recipe = {"id": "recipe_abc", "name": "Test Recipe", "is_favorite": False}
        mock_db.get_recipe = AsyncMock(return_value=existing_recipe)
        mock_db.update_recipe = AsyncMock(return_value=True)

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await favorite_recipe(
                user_id="user_456",
                recipe_id="recipe_abc",
                is_favorite=True,
            )

            # Assert
            assert result["success"] is True
            assert result["is_favorite"] is True
            mock_db.get_recipe.assert_called_once_with("user_456", "recipe_abc")
            mock_db.update_recipe.assert_called_once_with(
                "user_456",
                "recipe_abc",
                {"is_favorite": True},
            )

    @pytest.mark.asyncio
    async def test_favorite_recipe_unmark_favorite(self):
        """Test favorite_recipe successfully unmarks recipe as favorite."""
        # Arrange
        mock_db = AsyncMock()
        existing_recipe = {"id": "recipe_xyz", "name": "Test Recipe", "is_favorite": True}
        mock_db.get_recipe = AsyncMock(return_value=existing_recipe)
        mock_db.update_recipe = AsyncMock(return_value=True)

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await favorite_recipe(
                user_id="user_789",
                recipe_id="recipe_xyz",
                is_favorite=False,
            )

            # Assert
            assert result["success"] is True
            assert result["is_favorite"] is False
            mock_db.get_recipe.assert_called_once_with("user_789", "recipe_xyz")
            mock_db.update_recipe.assert_called_once_with(
                "user_789",
                "recipe_xyz",
                {"is_favorite": False},
            )

    @pytest.mark.asyncio
    async def test_favorite_recipe_update_fails(self):
        """Test favorite_recipe when database update returns False."""
        # Arrange
        mock_db = AsyncMock()
        existing_recipe = {"id": "recipe_def", "name": "Test Recipe"}
        mock_db.get_recipe = AsyncMock(return_value=existing_recipe)
        mock_db.update_recipe = AsyncMock(return_value=False)  # Update failed

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await favorite_recipe(
                user_id="user_321",
                recipe_id="recipe_def",
                is_favorite=True,
            )

            # Assert
            assert result["success"] is False
            assert "update failed" in result["error"].lower()
            mock_db.get_recipe.assert_called_once_with("user_321", "recipe_def")
            mock_db.update_recipe.assert_called_once_with(
                "user_321",
                "recipe_def",
                {"is_favorite": True},
            )

    @pytest.mark.asyncio
    async def test_favorite_recipe_handles_exception(self):
        """Test favorite_recipe handles database exceptions gracefully."""
        # Arrange
        mock_db = AsyncMock()
        existing_recipe = {"id": "recipe_ghi", "name": "Test Recipe"}
        mock_db.get_recipe = AsyncMock(return_value=existing_recipe)
        mock_db.update_recipe = AsyncMock(side_effect=Exception("Database error"))

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await favorite_recipe(
                user_id="user_654",
                recipe_id="recipe_ghi",
                is_favorite=True,
            )

            # Assert
            assert result["success"] is False
            assert "favoriting recipe" in result["error"]
            mock_db.get_recipe.assert_called_once_with("user_654", "recipe_ghi")
            mock_db.update_recipe.assert_called_once_with(
                "user_654",
                "recipe_ghi",
                {"is_favorite": True},
            )


class TestArchiveRecipe:
    """Test archive_recipe function."""

    @pytest.mark.asyncio
    async def test_archive_recipe_not_found(self):
        """Test archive_recipe fails when recipe doesn't exist."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.get_recipe = AsyncMock(return_value=None)  # Recipe not found
        mock_db.update_recipe = AsyncMock()

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await archive_recipe(
                user_id="user_123",
                recipe_id="recipe_999",
            )

            # Assert
            assert result["success"] is False
            assert "not found" in result["error"].lower()
            assert "recipe_999" in result["error"]
            mock_db.get_recipe.assert_called_once_with("user_123", "recipe_999")
            mock_db.update_recipe.assert_not_called()

    @pytest.mark.asyncio
    async def test_archive_recipe_success(self):
        """Test archive_recipe successfully archives a recipe."""
        # Arrange
        mock_db = AsyncMock()
        existing_recipe = {"id": "recipe_abc", "name": "Test Recipe", "is_archived": False}
        mock_db.get_recipe = AsyncMock(return_value=existing_recipe)
        mock_db.update_recipe = AsyncMock(return_value=True)

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await archive_recipe(
                user_id="user_456",
                recipe_id="recipe_abc",
            )

            # Assert
            assert result["success"] is True
            mock_db.get_recipe.assert_called_once_with("user_456", "recipe_abc")
            mock_db.update_recipe.assert_called_once_with(
                "user_456",
                "recipe_abc",
                {"is_archived": True},
            )

    @pytest.mark.asyncio
    async def test_archive_recipe_update_fails(self):
        """Test archive_recipe when database update returns False."""
        # Arrange
        mock_db = AsyncMock()
        existing_recipe = {"id": "recipe_xyz", "name": "Test Recipe"}
        mock_db.get_recipe = AsyncMock(return_value=existing_recipe)
        mock_db.update_recipe = AsyncMock(return_value=False)  # Update failed

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await archive_recipe(
                user_id="user_789",
                recipe_id="recipe_xyz",
            )

            # Assert
            assert result["success"] is False
            assert "archive failed" in result["error"].lower()
            mock_db.get_recipe.assert_called_once_with("user_789", "recipe_xyz")
            mock_db.update_recipe.assert_called_once_with(
                "user_789",
                "recipe_xyz",
                {"is_archived": True},
            )

    @pytest.mark.asyncio
    async def test_archive_recipe_handles_exception(self):
        """Test archive_recipe handles database exceptions gracefully."""
        # Arrange
        mock_db = AsyncMock()
        existing_recipe = {"id": "recipe_def", "name": "Test Recipe"}
        mock_db.get_recipe = AsyncMock(return_value=existing_recipe)
        mock_db.update_recipe = AsyncMock(side_effect=Exception("Connection lost"))

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await archive_recipe(
                user_id="user_321",
                recipe_id="recipe_def",
            )

            # Assert
            assert result["success"] is False
            assert "archiving recipe" in result["error"]
            mock_db.get_recipe.assert_called_once_with("user_321", "recipe_def")
            mock_db.update_recipe.assert_called_once_with(
                "user_321",
                "recipe_def",
                {"is_archived": True},
            )


class TestDeleteRecipe:
    """Test delete_recipe function."""

    @pytest.mark.asyncio
    async def test_delete_recipe_success(self):
        """Test delete_recipe successfully deletes a recipe."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.delete_recipe = AsyncMock(return_value=True)

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await delete_recipe(
                user_id="user_123",
                recipe_id="recipe_abc",
            )

            # Assert
            assert result["success"] is True
            mock_db.delete_recipe.assert_called_once_with("user_123", "recipe_abc")

    @pytest.mark.asyncio
    async def test_delete_recipe_not_found(self):
        """Test delete_recipe fails when recipe doesn't exist."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.delete_recipe = AsyncMock(return_value=False)  # Not found

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await delete_recipe(
                user_id="user_456",
                recipe_id="recipe_999",
            )

            # Assert
            assert result["success"] is False
            assert "not found" in result["error"].lower()
            assert "recipe_999" in result["error"]
            mock_db.delete_recipe.assert_called_once_with("user_456", "recipe_999")

    @pytest.mark.asyncio
    async def test_delete_recipe_handles_exception(self):
        """Test delete_recipe handles database exceptions gracefully."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.delete_recipe = AsyncMock(side_effect=Exception("Database unavailable"))

        with patch("fcp.tools.recipe_crud.get_firestore_client", return_value=mock_db):
            # Act
            result = await delete_recipe(
                user_id="user_789",
                recipe_id="recipe_xyz",
            )

            # Assert
            assert result["success"] is False
            assert "deleting recipe" in result["error"]
            mock_db.delete_recipe.assert_called_once_with("user_789", "recipe_xyz")
