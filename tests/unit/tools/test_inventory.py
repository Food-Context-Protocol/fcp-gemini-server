"""Tests for Inventory and Pantry tools."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools.inventory import add_to_pantry, suggest_recipe_from_pantry


@pytest.mark.asyncio
async def test_suggest_recipe_from_pantry_success():
    """Test successful recipe suggestion from pantry."""
    user_id = "test_user"
    mock_pantry = [{"name": "chicken"}, {"name": "spinach"}]
    mock_prefs = {"top_cuisines": ["Italian"]}

    mock_suggestions = {"suggestions": [{"name": "Chicken Florentine", "reason": "Uses chicken and spinach"}]}

    mock_get_pantry = AsyncMock(return_value=mock_pantry)
    mock_get_prefs = AsyncMock(return_value=mock_prefs)
    mock_firestore = SimpleNamespace(
        get_pantry=mock_get_pantry,
        get_user_preferences=mock_get_prefs,
    )

    with (
        patch("fcp.tools.inventory.firestore_client", mock_firestore),
        patch("fcp.tools.inventory.gemini.generate_json", new_callable=AsyncMock) as mock_gen_json,
    ):
        mock_gen_json.return_value = mock_suggestions

        result = await suggest_recipe_from_pantry(user_id)

        assert result["pantry_count"] == 2
        assert result["suggestions"][0]["name"] == "Chicken Florentine"


@pytest.mark.asyncio
async def test_add_to_pantry():
    """Test adding items to pantry."""
    user_id = "test_user"
    items = ["eggs", "milk"]

    mock_update = AsyncMock(return_value=["eggs", "milk"])
    mock_firestore = SimpleNamespace(update_pantry_items_batch=mock_update)

    with patch("fcp.tools.inventory.firestore_client", mock_firestore):
        result = await add_to_pantry(user_id, items)

        assert result == ["eggs", "milk"]
        assert mock_update.call_count == 1
