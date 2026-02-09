"""Tests for Cottage Industry tools."""

from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools.cottage import generate_cottage_label


@pytest.mark.asyncio
async def test_generate_cottage_label_success():
    """Test successful cottage label generation."""
    mock_response = {
        "label_text": "Grandma's Cookies",
        "ingredients_formatted": "Flour, Sugar, Butter",
        "allergens_identified": ["Wheat", "Dairy"],
        "legal_warnings": ["Made in a Home Kitchen"],
        "storage_instructions": "Keep cool",
    }

    with patch("fcp.tools.cottage.gemini.generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_response

        result = await generate_cottage_label("Cookies", ["Flour"], "8 oz", "My Bakery", "123 Home St")

        assert result["label_text"] == "Grandma's Cookies"
        assert "Wheat" in result["allergens_identified"]

        # Verify prompt content
        args, _ = mock_gen.call_args
        assert "regulatory compliance" in args[0]
        assert "My Bakery" in args[0]
