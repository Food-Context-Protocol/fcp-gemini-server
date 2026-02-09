"""Tests for crud.py coverage gap: get_meals with format='schema_org' (lines 61-62)."""

from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools.crud import get_meals


@pytest.mark.asyncio
async def test_get_meals_schema_org_format():
    """Test get_meals with format='schema_org' transforms meals via to_schema_org_recipe.

    Covers lines 61-62 in crud.py where the schema_org branch calls
    ``to_schema_org_recipe`` on each meal.
    """
    mock_db = AsyncMock()
    mock_db.get_user_logs = AsyncMock(
        return_value=[
            {"dish_name": "Tacos", "id": "log1"},
            {"dish_name": "Ramen", "id": "log2"},
        ]
    )

    with patch("fcp.tools.crud.to_schema_org_recipe") as mock_schema:
        mock_schema.side_effect = lambda meal: {
            "@context": "https://schema.org",
            "@type": "Recipe",
            "name": meal["dish_name"],
        }

        result = await get_meals("user1", output_format="schema_org", db=mock_db)

    assert len(result) == 2
    assert result[0]["@type"] == "Recipe"
    assert result[0]["name"] == "Tacos"
    assert result[1]["@type"] == "Recipe"
    assert result[1]["name"] == "Ramen"

    # Verify to_schema_org_recipe was called once per meal
    assert mock_schema.call_count == 2


@pytest.mark.asyncio
async def test_get_meals_schema_org_format_empty_list():
    """Test get_meals with format='schema_org' returns empty list when no meals."""
    mock_db = AsyncMock()
    mock_db.get_user_logs = AsyncMock(return_value=[])

    with patch("fcp.tools.crud.to_schema_org_recipe") as mock_schema:
        result = await get_meals("user1", output_format="schema_org", db=mock_db)

    assert result == []
    mock_schema.assert_not_called()
