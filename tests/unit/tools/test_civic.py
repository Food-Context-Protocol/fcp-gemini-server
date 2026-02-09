"""Tests for Civic and Community tools."""

from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools.civic import detect_economic_gaps, plan_food_festival


@pytest.mark.asyncio
async def test_plan_food_festival_success():
    """Test successful festival planning."""
    mock_plan = {
        "festival_name": "Spicy Summer Fest",
        "vendor_lineup": [{"cuisine": "Thai", "reason": "Trending"}],
        "layout_notes": "Place Thai near the entrance",
        "marketing_hook": "Feel the heat!",
        "community_impact_score": 0.9,
    }

    with patch("fcp.tools.civic.gemini.generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_plan

        result = await plan_food_festival("San Francisco", "Spicy Food")

        assert result["festival_name"] == "Spicy Summer Fest"
        assert result["community_impact_score"] == 0.9

        # Verify instructions
        args, _ = mock_gen.call_args
        assert "City Event Weaver" in args[0]


@pytest.mark.asyncio
async def test_detect_economic_gaps_success():
    """Test gap detection."""
    mock_gaps = {"identified_gaps": ["Ethiopian", "Korean BBQ"], "viability_score": 0.85}

    with patch("fcp.tools.civic.gemini.generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_gaps

        result = await detect_economic_gaps("Mission District", ["Mexican", "Italian"])

        assert "Ethiopian" in result["identified_gaps"]
        assert result["viability_score"] == 0.85


@pytest.mark.asyncio
async def test_plan_food_festival_error():
    with patch("fcp.tools.civic.gemini.generate_json", side_effect=Exception("API Error")):
        result = await plan_food_festival("City", "Theme")
        assert "error" in result
        assert result["status"] == "failed"


@pytest.mark.asyncio
async def test_detect_economic_gaps_error():
    with patch("fcp.tools.civic.gemini.generate_json", side_effect=Exception("API Error")):
        result = await detect_economic_gaps("Hood", [])
        assert "error" in result
