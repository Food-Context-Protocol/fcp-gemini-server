"""Additional coverage tests for safety tools."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools import safety


@pytest.mark.asyncio
async def test_check_food_recalls_list_response():
    with patch(
        "fcp.tools.safety.gemini.generate_json_with_grounding",
        new=AsyncMock(return_value={"data": [{"has_active_recall": False}], "sources": []}),
    ):
        result = await safety.check_food_recalls("eggs")
        assert result["has_active_recall"] is False


@pytest.mark.asyncio
async def test_run_recall_radar_alert_triggered():
    mock_firestore = SimpleNamespace(
        get_user_logs=AsyncMock(return_value=[{"id": "1", "dish_name": "Eggs"}]),
    )
    with (
        patch("fcp.tools.safety.firestore_client", mock_firestore),
        patch(
            "fcp.tools.safety.check_food_recalls",
            new=AsyncMock(return_value={"has_active_recall": True, "recall_info": "Recall"}),
        ),
    ):
        results = await safety.run_recall_radar("u1")
        assert results[0]["log_id"] == "1"


@pytest.mark.asyncio
async def test_run_recall_radar_no_alerts():
    mock_firestore = SimpleNamespace(
        get_user_logs=AsyncMock(return_value=[{"id": "1", "dish_name": "Eggs"}]),
    )
    with (
        patch("fcp.tools.safety.firestore_client", mock_firestore),
        patch(
            "fcp.tools.safety.check_food_recalls",
            new=AsyncMock(return_value={"has_active_recall": False, "recall_info": ""}),
        ),
    ):
        results = await safety.run_recall_radar("u1")
        assert results == []


@pytest.mark.asyncio
async def test_run_recall_radar_skips_missing_dish():
    mock_firestore = SimpleNamespace(get_user_logs=AsyncMock(return_value=[{"id": "1"}]))
    with patch("fcp.tools.safety.firestore_client", mock_firestore):
        results = await safety.run_recall_radar("u1")
        assert results == []


@pytest.mark.asyncio
async def test_check_allergen_alerts_list_response():
    with patch(
        "fcp.tools.safety.gemini.generate_json_with_grounding",
        new=AsyncMock(return_value={"data": [{"has_alert": False}], "sources": []}),
    ):
        result = await safety.check_allergen_alerts("bread", allergens=["gluten"])
        assert result["has_alert"] is False


@pytest.mark.asyncio
async def test_check_drug_food_interactions_list_response():
    with patch(
        "fcp.tools.safety.gemini.generate_json_with_grounding",
        new=AsyncMock(return_value={"data": [{"has_interaction": False}], "sources": []}),
    ):
        result = await safety.check_drug_food_interactions("grapefruit", ["statins"])
        assert result["has_interaction"] is False


@pytest.mark.asyncio
async def test_get_seasonal_food_safety():
    with patch(
        "fcp.tools.safety.gemini.generate_with_grounding",
        new=AsyncMock(return_value={"text": "ok", "sources": []}),
    ):
        result = await safety.get_seasonal_food_safety("NYC")
        assert result["safety_tips"] == "ok"
