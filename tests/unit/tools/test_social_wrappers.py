"""Tests for social.py coverage gaps: tool wrapper (line 23) and no-content branch (47->49)."""

from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools.social import generate_social_post, generate_social_post_tool


@pytest.mark.asyncio
async def test_generate_social_post_tool_delegates_to_generate():
    """Test generate_social_post_tool wrapper calls get_meal then generate_social_post.

    Covers line 23: the ``return await generate_social_post(...)`` path inside the
    decorated wrapper function.
    """
    with patch("fcp.tools.crud.get_meal", new_callable=AsyncMock) as mock_meal:
        mock_meal.return_value = {"dish_name": "Tacos", "venue_name": "Taqueria"}

        with patch("fcp.tools.social.generate_social_post", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {
                "content": "Great tacos!",
                "text": "Great tacos!",
                "hashtags": ["#food"],
            }

            result = await generate_social_post_tool("user1", "log1")

    # Verify get_meal was called with the right args
    mock_meal.assert_awaited_once_with("user1", "log1")

    # Verify generate_social_post was called with the meal data and defaults
    mock_gen.assert_awaited_once_with(
        log_data={"dish_name": "Tacos", "venue_name": "Taqueria"},
        platform="twitter",
        style="casual",
    )

    assert result["content"] == "Great tacos!"
    assert result["hashtags"] == ["#food"]


@pytest.mark.asyncio
async def test_generate_social_post_tool_custom_platform_and_tone():
    """Test generate_social_post_tool passes custom platform/tone through."""
    with patch("fcp.tools.crud.get_meal", new_callable=AsyncMock) as mock_meal:
        mock_meal.return_value = {"dish_name": "Sushi", "venue_name": "Nobu"}

        with patch("fcp.tools.social.generate_social_post", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {"content": "Sushi night!"}

            result = await generate_social_post_tool("user1", "log1", platform="instagram", tone="professional")

    mock_gen.assert_awaited_once_with(
        log_data={"dish_name": "Sushi", "venue_name": "Nobu"},
        platform="instagram",
        style="professional",
    )
    assert result["content"] == "Sushi night!"


@pytest.mark.asyncio
async def test_generate_social_post_tool_meal_not_found():
    """Test generate_social_post_tool returns error when meal is not found."""
    with patch("fcp.tools.crud.get_meal", new_callable=AsyncMock) as mock_meal:
        mock_meal.return_value = None

        result = await generate_social_post_tool("user1", "missing_log")

    assert result == {"error": "Log missing_log not found"}


@pytest.mark.asyncio
async def test_generate_social_post_no_content_key_in_result():
    """Test generate_social_post when Gemini returns dict WITHOUT 'content' key.

    Covers branch 47->49: the condition
        ``result and isinstance(result, dict) and "content" in result``
    is False, so ``result["text"] = result["content"]`` is skipped.
    """
    with patch("fcp.tools.social.gemini") as mock_gemini:
        mock_gemini.generate_json = AsyncMock(return_value={"summary": "Great food!", "hashtags": ["#yum"]})

        result = await generate_social_post(
            log_data={"dish_name": "Pasta", "venue_name": "Italian Place"},
            platform="twitter",
            style="casual",
        )

    assert result == {"summary": "Great food!", "hashtags": ["#yum"]}
    # "text" key should NOT be present because "content" was missing
    assert "text" not in result
    assert "content" not in result
