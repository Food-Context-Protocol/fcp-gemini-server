"""Tests for routes/recipes.py endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from fcp.api import app
from fcp.auth.permissions import AuthenticatedUser, UserRole
from tests.constants import TEST_AUTH_HEADER, TEST_USER_ID

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _close_client():
    """Ensure the shared TestClient is properly closed."""
    yield
    client.close()


@pytest.fixture
def mock_auth():
    """Mock authentication to return test user."""
    from fcp.auth.local import get_current_user
    from fcp.auth.permissions import require_write_access

    user = AuthenticatedUser(user_id=TEST_USER_ID, role=UserRole.AUTHENTICATED)

    async def override_get_current_user(authorization=None):
        return user

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_write_access] = override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_write_access, None)


class TestStandardizeRecipeEndpoint:
    """Tests for POST /standardize-recipe endpoint."""

    def test_standardize_recipe_success(self, mock_auth):
        """Test standardizing recipe text."""
        mock_result = {
            "@context": "https://schema.org",
            "@type": "Recipe",
            "name": "Chocolate Chip Cookies",
            "recipeIngredient": ["flour", "sugar", "chocolate chips"],
            "recipeInstructions": [{"@type": "HowToStep", "text": "Mix dry ingredients"}],
        }

        with patch("fcp.routes.recipes.standardize_recipe", new_callable=AsyncMock) as mock_std:
            mock_std.return_value = mock_result

            response = client.post(
                "/standardize-recipe",
                json={"raw_text": "Mix 2 cups flour with 1 cup sugar and 1 cup chocolate chips..."},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["@type"] == "Recipe"
            assert data["name"] == "Chocolate Chip Cookies"


class TestScaleRecipeEndpoint:
    """Tests for POST /scaling/scale-recipe endpoint."""

    def test_scale_recipe_success(self, mock_auth):
        """Test scaling recipe ingredients."""
        original_recipe = {
            "name": "Pancakes",
            "recipeYield": "4 servings",
            "recipeIngredient": ["2 cups flour", "2 eggs", "1 cup milk"],
        }
        scaled_recipe = {
            "name": "Pancakes",
            "recipeYield": "8 servings",
            "recipeIngredient": ["4 cups flour", "4 eggs", "2 cups milk"],
        }

        with patch("fcp.routes.recipes.scale_recipe", new_callable=AsyncMock) as mock_scale:
            mock_scale.return_value = scaled_recipe

            response = client.post(
                "/scaling/scale-recipe",
                json={"recipe_json": original_recipe, "target_servings": 8},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["recipeYield"] == "8 servings"
            mock_scale.assert_called_once_with(original_recipe, 8)


class TestExtractRecipeEndpoint:
    """Tests for POST /recipes/extract endpoint."""

    def test_extract_recipe_from_image(self, mock_auth):
        """Test extracting recipe from image."""
        mock_result = {
            "name": "Grilled Salmon",
            "ingredients": ["salmon fillet", "lemon", "dill"],
            "instructions": ["Season salmon", "Grill for 4 minutes per side"],
        }

        with patch("fcp.routes.recipes.extract_recipe_from_media", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = mock_result

            response = client.post(
                "/recipes/extract",
                json={
                    "image_url": "https://firebasestorage.googleapis.com/recipe.jpg",
                    "additional_notes": "This is grilled salmon with herbs",
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_extract.assert_called_once_with(
                "https://firebasestorage.googleapis.com/recipe.jpg",
                None,  # media_url
                "This is grilled salmon with herbs",
            )

    def test_extract_recipe_from_video(self, mock_auth):
        """Test extracting recipe from video."""
        with patch("fcp.routes.recipes.extract_recipe_from_media", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {"name": "Video Recipe", "instructions": []}

            response = client.post(
                "/recipes/extract",
                json={
                    "media_url": "https://storage.googleapis.com/video.mp4",
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_extract.assert_called_once_with(
                None,  # image_url
                "https://storage.googleapis.com/video.mp4",
                None,  # additional_notes
            )


class TestListRecipesEndpoint:
    """Tests for GET /recipes endpoint."""

    def test_list_recipes_success(self, mock_auth):
        """Test listing user's recipes."""
        mock_recipes = [
            {"id": "r1", "name": "Pasta", "ingredients": ["pasta", "sauce"]},
            {"id": "r2", "name": "Salad", "ingredients": ["lettuce", "tomato"]},
        ]

        with patch("fcp.routes.recipes.list_recipes", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = mock_recipes

            response = client.get(
                "/recipes",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert "recipes" in data
            assert len(data["recipes"]) == 2


class TestGetRecipeEndpoint:
    """Tests for GET /recipes/{recipe_id} endpoint."""

    def test_get_recipe_success(self, mock_auth):
        """Test getting a single recipe."""
        mock_recipe = {"id": "r1", "name": "Pasta", "ingredients": ["pasta", "sauce"]}

        with patch("fcp.routes.recipes.get_recipe", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_recipe

            response = client.get(
                "/recipes/r1",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["recipe"]["name"] == "Pasta"

    def test_get_recipe_not_found(self, mock_auth):
        """Test getting non-existent recipe returns error."""
        with patch("fcp.routes.recipes.get_recipe", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            response = client.get(
                "/recipes/nonexistent",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert "error" in data


class TestSaveRecipeEndpoint:
    """Tests for POST /recipes endpoint."""

    def test_save_recipe_success(self, mock_auth):
        """Test saving a new recipe."""
        with patch("fcp.routes.recipes.save_recipe", new_callable=AsyncMock) as mock_save:
            mock_save.return_value = {"success": True, "recipe_id": "new-recipe-id"}

            response = client.post(
                "/recipes",
                json={"name": "Pasta", "ingredients": ["pasta", "sauce"]},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestUpdateRecipeEndpoint:
    """Tests for PATCH /recipes/{recipe_id} endpoint."""

    def test_update_recipe_success(self, mock_auth):
        """Test updating a recipe."""
        with patch("fcp.routes.recipes.update_recipe", new_callable=AsyncMock) as mock_update:
            mock_update.return_value = {"success": True}

            response = client.patch(
                "/recipes/r1",
                json={"servings": 6},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_update_recipe_no_updates(self, mock_auth):
        """Test updating with empty request."""
        response = client.patch(
            "/recipes/r1",
            json={},
            headers=TEST_AUTH_HEADER,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "No update fields" in data["error"]


class TestFavoriteRecipeEndpoint:
    """Tests for POST /recipes/{recipe_id}/favorite endpoint."""

    def test_favorite_recipe_success(self, mock_auth):
        """Test favoriting a recipe."""
        with patch("fcp.routes.recipes.favorite_recipe", new_callable=AsyncMock) as mock_fav:
            mock_fav.return_value = {"success": True, "is_favorite": True}

            response = client.post(
                "/recipes/r1/favorite",
                json={"is_favorite": True},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestArchiveRecipeEndpoint:
    """Tests for POST /recipes/{recipe_id}/archive endpoint."""

    def test_archive_recipe_success(self, mock_auth):
        """Test archiving a recipe."""
        with patch("fcp.routes.recipes.archive_recipe", new_callable=AsyncMock) as mock_archive:
            mock_archive.return_value = {"success": True}

            response = client.post(
                "/recipes/r1/archive",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestDeleteRecipeEndpoint:
    """Tests for DELETE /recipes/{recipe_id} endpoint."""

    def test_delete_recipe_success(self, mock_auth):
        """Test deleting a recipe."""
        with patch("fcp.routes.recipes.delete_recipe", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = {"success": True}

            response = client.delete(
                "/recipes/r1",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestGenerateRecipeEndpoint:
    """Tests for POST /recipes/generate endpoint."""

    def test_generate_recipe_minimal(self, mock_auth):
        """Test generating recipe with minimal input."""
        mock_result = {
            "name": "Vegetable Stir Fry",
            "ingredients": ["broccoli", "carrots", "soy sauce"],
            "instructions": ["Chop vegetables", "Heat oil", "Stir fry"],
        }

        with patch("fcp.routes.recipes.generate_recipe", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_result

            response = client.post(
                "/recipes/generate",
                json={"ingredients": ["broccoli", "carrots", "soy sauce"]},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_gen.assert_called_once_with(
                ingredients=["broccoli", "carrots", "soy sauce"],
                dish_name=None,
                cuisine=None,
                dietary_restrictions=None,
            )

    def test_generate_recipe_full_options(self, mock_auth):
        """Test generating recipe with all options."""
        with patch("fcp.routes.recipes.generate_recipe", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {"name": "Pad Thai", "instructions": []}

            response = client.post(
                "/recipes/generate",
                json={
                    "ingredients": ["rice noodles", "tofu", "peanuts"],
                    "dish_name": "Pad Thai",
                    "cuisine": "Thai",
                    "dietary_restrictions": "vegan",
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_gen.assert_called_once_with(
                ingredients=["rice noodles", "tofu", "peanuts"],
                dish_name="Pad Thai",
                cuisine="Thai",
                dietary_restrictions="vegan",
            )
