"""Tests for Social Syndication tools."""

from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools.social import generate_social_post


@pytest.mark.asyncio
async def test_generate_social_post_success():
    """Test successful social post generation."""
    log_data = {
        "dish_name": "Spicy Ramen",
        "venue_name": "Ramen Nagi",
        "rating": 5,
        "notes": "Best ramen ever! So spicy.",
        "cuisine": "Japanese",
    }

    expected_response = {
        "content": "Just had the best Spicy Ramen at Ramen Nagi! 🍜🔥 5/5 stars. #Ramen #Spicy #Foodie",
        "hashtags": ["#Ramen", "#Spicy", "#Foodie"],
        "image_concept": "Close up of ramen bowl",
    }

    with patch("fcp.tools.social.gemini.generate_json", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = expected_response

        result = await generate_social_post(log_data, platform="twitter")

        assert result == expected_response
        args, _ = mock_generate.call_args
        assert "Spicy Ramen" in args[0]
        assert "Ramen Nagi" in args[0]
        assert "twitter" in args[0]


@pytest.mark.asyncio
async def test_generate_social_post_error_fallback():
    """Test fallback when API fails."""
    log_data = {"dish_name": "Burger", "venue_name": "Shake Shack"}

    with patch("fcp.tools.social.gemini.generate_json", side_effect=Exception("API Error")):
        result = await generate_social_post(log_data)

        assert "content" in result
        assert "Burger" in result["content"]
        assert "error" in result
