"""Additional coverage tests for tool modules."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools import agents, civic, flavor, scaling, standardize


@pytest.mark.asyncio
async def test_delegate_to_food_agent_error():
    with patch("fcp.tools.agents.gemini.generate_json", new=AsyncMock(side_effect=Exception("boom"))):
        result = await agents.delegate_to_food_agent("visual_agent", "make a poster")
        assert result["status"] == "failed"
        assert "boom" in result["error"]


@pytest.mark.asyncio
async def test_civic_tools_list_responses():
    with patch(
        "fcp.tools.civic.gemini.generate_json",
        new=AsyncMock(return_value=[{"festival_name": "Taste Fest"}]),
    ):
        result = await civic.plan_food_festival("Austin", "BBQ")
        assert result["festival_name"] == "Taste Fest"

    with patch(
        "fcp.tools.civic.gemini.generate_json",
        new=AsyncMock(return_value=[{"gap": "no vegan"}]),
    ):
        result = await civic.detect_economic_gaps("Downtown", ["BBQ"])
        assert result["gap"] == "no vegan"


@pytest.mark.asyncio
async def test_scale_recipe_dict_response():
    with patch(
        "fcp.tools.scaling.gemini.generate_json",
        new=AsyncMock(return_value={"recipeYield": "4 servings"}),
    ):
        result = await scaling.scale_recipe({"recipeYield": "2 servings"}, 4)
        assert result["recipeYield"] == "4 servings"


@pytest.mark.asyncio
async def test_standardize_recipe_adds_context_and_type():
    with patch(
        "fcp.tools.standardize.gemini.generate_json",
        new=AsyncMock(return_value={"name": "Test Recipe"}),
    ):
        result = await standardize.standardize_recipe("2 eggs and salt")
        assert result["@context"] == "https://schema.org"
        assert result["@type"] == "Recipe"


@pytest.mark.asyncio
async def test_standardize_recipe_preserves_existing_context():
    with patch(
        "fcp.tools.standardize.gemini.generate_json",
        new=AsyncMock(return_value={"@context": "https://schema.org", "@type": "Recipe"}),
    ):
        result = await standardize.standardize_recipe("2 eggs and salt")
        assert result["@context"] == "https://schema.org"
        assert result["@type"] == "Recipe"


@pytest.mark.asyncio
async def test_flavor_pairings_dict_response():
    with patch(
        "fcp.tools.flavor.gemini.generate_json",
        new=AsyncMock(return_value={"subject": "Apple", "pairings": []}),
    ):
        result = await flavor.get_flavor_pairings("Apple")
        assert result["subject"] == "Apple"


@pytest.mark.asyncio
async def test_calculate_macro_targets():
    with patch(
        "fcp.tools.analytics.gemini.generate_with_code_execution",
        new=AsyncMock(return_value={"text": "ok", "code": "x=1", "execution_result": "out"}),
    ):
        from fcp.tools.analytics import calculate_macro_targets

        result = await calculate_macro_targets([{"dish_name": "Salad"}], goal="maintain", body_weight_kg=70)
        assert result["goal"] == "maintain"
        assert result["body_weight_kg"] == 70

        result = await calculate_macro_targets([{"dish_name": "Salad"}], goal="maintain")
        assert result["body_weight_kg"] is None
