"""Tests for recipe generator tool."""

from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools.recipe_generator import generate_recipe


@pytest.mark.asyncio
async def test_generate_recipe_success() -> None:
    """Test successful recipe generation."""
    mock_response = {
        "recipe_name": "Grilled Lemon Chicken",
        "description": "A delicious grilled chicken with lemon",
        "prep_time": "15 minutes",
        "cook_time": "25 minutes",
        "servings": 4,
        "difficulty": "Easy",
        "ingredients_list": [
            {"item": "chicken breast", "amount": "4", "notes": "boneless"},
            {"item": "lemon", "amount": "2", "notes": "juiced"},
            {"item": "garlic", "amount": "3 cloves", "notes": "minced"},
        ],
        "instructions": [
            "Step 1: Marinate chicken in lemon juice and garlic",
            "Step 2: Grill for 6-7 minutes per side",
        ],
        "tips": ["Let chicken rest before slicing"],
        "nutrition_per_serving": {
            "calories": 280,
            "protein": "35g",
            "carbs": "5g",
            "fat": "12g",
        },
        "variations": ["Add rosemary for extra flavor"],
    }

    with patch("fcp.tools.recipe_generator.gemini") as mock_gemini:
        mock_gemini.generate_json = AsyncMock(return_value=mock_response)

        result = await generate_recipe(
            ingredients=["chicken", "lemon", "garlic"],
            dish_name="Lemon Chicken",
            cuisine="Mediterranean",
        )

        assert result["recipe_name"] == "Grilled Lemon Chicken"
        assert result["servings"] == 4
        assert len(result["ingredients_list"]) == 3
        assert len(result["instructions"]) == 2


@pytest.mark.asyncio
async def test_generate_recipe_minimal_input() -> None:
    """Test recipe generation with minimal input."""
    mock_response = {
        "recipe_name": "Simple Pasta",
        "description": "Quick pasta dish",
        "servings": 2,
        "ingredients_list": [{"item": "pasta", "amount": "200g", "notes": None}],
        "instructions": ["Cook pasta according to package"],
    }

    with patch("fcp.tools.recipe_generator.gemini") as mock_gemini:
        mock_gemini.generate_json = AsyncMock(return_value=mock_response)

        result = await generate_recipe(ingredients=["pasta"])

        assert result["recipe_name"] == "Simple Pasta"
        mock_gemini.generate_json.assert_called_once()


@pytest.mark.asyncio
async def test_generate_recipe_with_dietary_restrictions() -> None:
    """Test recipe generation with dietary restrictions."""
    mock_response = {
        "recipe_name": "Vegan Stir Fry",
        "description": "Plant-based stir fry",
        "servings": 4,
        "ingredients_list": [],
        "instructions": [],
    }

    with patch("fcp.tools.recipe_generator.gemini") as mock_gemini:
        mock_gemini.generate_json = AsyncMock(return_value=mock_response)

        result = await generate_recipe(
            ingredients=["tofu", "broccoli", "soy sauce"],
            dietary_restrictions="vegan, gluten-free",
        )

        assert result["recipe_name"] == "Vegan Stir Fry"
        # Verify the prompt includes dietary restrictions
        call_args = mock_gemini.generate_json.call_args[0][0]
        assert "dietary restrictions: vegan, gluten-free" in call_args


@pytest.mark.asyncio
async def test_generate_recipe_gemini_error() -> None:
    """Test handling of Gemini API errors."""
    with patch("fcp.tools.recipe_generator.gemini") as mock_gemini:
        mock_gemini.generate_json = AsyncMock(side_effect=Exception("API error"))

        with pytest.raises(Exception, match="API error"):
            await generate_recipe(ingredients=["chicken"])


@pytest.mark.asyncio
async def test_generate_recipe_json_parse_error() -> None:
    """Test handling of JSON parse errors from Gemini (normalized to ValueError)."""
    with patch("fcp.tools.recipe_generator.gemini") as mock_gemini:
        # Gemini service normalizes json.JSONDecodeError to ValueError
        mock_gemini.generate_json = AsyncMock(side_effect=ValueError("Failed to parse JSON from Gemini response"))

        with pytest.raises(ValueError, match="Failed to generate recipe"):
            await generate_recipe(ingredients=["chicken"])
