"""Tests for Automated Trend Spotter tools."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools.trends import identify_emerging_trends


def _mock_firestore(stats=None, prefs=None):
    mock_stats = AsyncMock(return_value=stats)
    mock_prefs = AsyncMock(return_value=prefs)
    return SimpleNamespace(get_user_stats=mock_stats, get_user_preferences=mock_prefs), mock_stats, mock_prefs


@pytest.mark.asyncio
async def test_identify_emerging_trends_success():
    """Test successful trend identification."""
    user_id = "test_user"
    mock_stats = {"total_logs": 100}
    mock_prefs = {"top_cuisines": ["Mexican"]}

    mock_gemini_result = {
        "text": '{"trending_dish": "Birria Ramen", "why_its_trending": "Fusion boom", "user_alignment_score": 0.9, "recommendation": "Try it!", "sources": []}',
        "sources": [{"title": "Food Trends", "url": "https://example.com"}],
    }

    mock_firestore, mock_stats_get, mock_prefs_get = _mock_firestore(mock_stats, mock_prefs)
    with (
        patch("fcp.tools.trends.firestore_client", mock_firestore),
        patch("fcp.tools.trends.gemini.generate_with_all_tools", new_callable=AsyncMock) as mock_gen,
    ):
        mock_gen.return_value = mock_gemini_result

        result = await identify_emerging_trends(user_id)

        assert result["trending_dish"] == "Birria Ramen"
        assert result["user_alignment_score"] == 0.9
        assert len(result["grounding_sources"]) == 1

        # Verify instructions
        args, kwargs = mock_gen.call_args
        assert "Culinary Futurist" in kwargs["prompt"]
        assert kwargs["enable_grounding"] is True


@pytest.mark.asyncio
async def test_identify_emerging_trends_markdown_json():
    """Test trend identification with JSON wrapped in markdown code blocks."""
    user_id = "test_user"
    mock_stats = {"total_logs": 50}
    mock_prefs = {"top_cuisines": ["Italian"]}

    # Gemini often wraps JSON in markdown code blocks
    mock_gemini_result = {
        "text": """Here are the emerging trends I found:

```json
{
    "trending_dish": "Smash Burger",
    "why_its_trending": "TikTok viral sensation",
    "user_alignment_score": 0.75,
    "recommendation": "Try the smash technique at home",
    "sources": ["TikTok", "Food Network"]
}
```

This trend aligns well with your preferences!""",
        "sources": [{"title": "Viral Foods", "url": "https://example.com"}],
    }

    mock_firestore, mock_stats_get, mock_prefs_get = _mock_firestore(mock_stats, mock_prefs)
    with (
        patch("fcp.tools.trends.firestore_client", mock_firestore),
        patch("fcp.tools.trends.gemini.generate_with_all_tools", new_callable=AsyncMock) as mock_gen,
    ):
        mock_gen.return_value = mock_gemini_result

        result = await identify_emerging_trends(user_id)

        assert result["trending_dish"] == "Smash Burger"
        assert result["user_alignment_score"] == 0.75
        assert "grounding_sources" in result


@pytest.mark.asyncio
async def test_identify_emerging_trends_parse_failure():
    """Test trend identification when JSON parsing fails."""
    user_id = "test_user"
    mock_stats = {"total_logs": 10}
    mock_prefs = {"top_cuisines": []}

    # Invalid/unparseable response
    mock_gemini_result = {
        "text": "I couldn't find any trends right now. Please try again later.",
        "sources": [],
    }

    mock_firestore, mock_stats_get, mock_prefs_get = _mock_firestore(mock_stats, mock_prefs)
    with (
        patch("fcp.tools.trends.firestore_client", mock_firestore),
        patch("fcp.tools.trends.gemini.generate_with_all_tools", new_callable=AsyncMock) as mock_gen,
    ):
        mock_gen.return_value = mock_gemini_result

        result = await identify_emerging_trends(user_id)

        assert "error" in result
        assert result["error"] == "Failed to parse trend analysis"
        assert "raw_text" in result


@pytest.mark.asyncio
async def test_identify_emerging_trends_exception():
    """Test trend identification when an exception occurs during Gemini call."""
    user_id = "test_user"
    mock_stats = {"total_logs": 10}
    mock_prefs = {"top_cuisines": []}

    mock_firestore, mock_stats_get, mock_prefs_get = _mock_firestore(mock_stats, mock_prefs)
    with (
        patch("fcp.tools.trends.firestore_client", mock_firestore),
        patch("fcp.tools.trends.gemini.generate_with_all_tools", new_callable=AsyncMock) as mock_gen,
    ):
        mock_gen.side_effect = Exception("Gemini API error")

        result = await identify_emerging_trends(user_id)

        assert "error" in result
        assert "Gemini API error" in result["error"]


@pytest.mark.asyncio
async def test_identify_emerging_trends_with_cuisine_focus():
    """Test trend identification with a specific cuisine focus."""
    user_id = "test_user"
    mock_stats = {"total_logs": 100}
    mock_prefs = {"top_cuisines": ["Japanese"]}

    mock_gemini_result = {
        "text": '{"trending_dish": "Katsu Sando", "why_its_trending": "Japanese comfort food", "user_alignment_score": 0.95, "recommendation": "Try making at home", "sources": []}',
        "sources": [],
    }

    mock_firestore, mock_stats_get, mock_prefs_get = _mock_firestore(mock_stats, mock_prefs)
    with (
        patch("fcp.tools.trends.firestore_client", mock_firestore),
        patch("fcp.tools.trends.gemini.generate_with_all_tools", new_callable=AsyncMock) as mock_gen,
    ):
        mock_gen.return_value = mock_gemini_result

        result = await identify_emerging_trends(user_id, region="tokyo", cuisine_focus="Japanese")

        assert result["trending_dish"] == "Katsu Sando"

        # Verify cuisine focus is in prompt
        args, kwargs = mock_gen.call_args
        assert "Japanese" in kwargs["prompt"]
        assert "tokyo" in kwargs["prompt"]
