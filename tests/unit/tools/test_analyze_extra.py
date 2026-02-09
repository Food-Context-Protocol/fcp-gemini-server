"""Additional coverage tests for analyze tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_analyze_meal_from_bytes_uses_image_bytes():
    with patch("fcp.tools.analyze.gemini.generate_json", new=AsyncMock(return_value={"dish_name": "Salad"})) as mock:
        from fcp.tools.analyze import analyze_meal_from_bytes

        image_bytes = b"fake"
        result = await analyze_meal_from_bytes(image_bytes, mime_type="image/png")

    assert result["dish_name"] == "Salad"
    mock.assert_called_once()
    _, kwargs = mock.call_args
    assert kwargs["image_bytes"] == image_bytes
    assert kwargs["image_mime_type"] == "image/png"


@pytest.mark.asyncio
async def test_analyze_meal_v2_allergen_warnings():
    mock_function_calls = {
        "function_calls": [
            {"name": "identify_allergens", "args": {"allergens": ["nuts"], "warnings": ["peanuts"]}},
        ]
    }
    with patch("fcp.tools.analyze.gemini.generate_with_tools", new=AsyncMock(return_value=mock_function_calls)):
        from fcp.tools.analyze import analyze_meal_v2

        result = await analyze_meal_v2("https://example.com/test.jpg")

    assert result["allergens"] == ["nuts"]
    assert result["allergen_warnings"] == ["peanuts"]


@pytest.mark.asyncio
async def test_analyze_meal_v2_allergen_no_warnings():
    mock_function_calls = {
        "function_calls": [
            {"name": "identify_allergens", "args": {"allergens": ["soy"]}},
        ]
    }
    with patch("fcp.tools.analyze.gemini.generate_with_tools", new=AsyncMock(return_value=mock_function_calls)):
        from fcp.tools.analyze import analyze_meal_v2

        result = await analyze_meal_v2("https://example.com/test.jpg")

    assert result["allergens"] == ["soy"]
    assert "allergen_warnings" not in result
