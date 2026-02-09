"""Tests for Clinical and Dietitian tools."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools.clinical import generate_dietitian_report


@pytest.mark.asyncio
async def test_generate_dietitian_report_success():
    """Test successful dietitian report generation."""
    user_id = "test_user"
    mock_logs = [{"dish_name": "Salad", "nutrition": {"calories": 200}}]
    mock_prefs = {"dietary_patterns": ["low-carb"]}

    mock_report = {
        "report_title": "Weekly Nutrition Summary",
        "macro_analysis": {"avg_protein": 50, "avg_carbs": 30, "avg_fat": 20},
        "findings": ["Low carbohydrate intake observed"],
        "recommendations": ["Maintain current fiber levels"],
        "trigger_warnings": [],
    }

    mock_get_logs = AsyncMock(return_value=mock_logs)
    mock_get_prefs = AsyncMock(return_value=mock_prefs)
    mock_firestore = SimpleNamespace(
        get_user_logs=mock_get_logs,
        get_user_preferences=mock_get_prefs,
    )

    with (
        patch("fcp.tools.clinical.firestore_client", mock_firestore),
        patch("fcp.tools.clinical.gemini.generate_json", new_callable=AsyncMock) as mock_gen,
    ):
        mock_gen.return_value = mock_report

        result = await generate_dietitian_report(user_id)

        assert result["report_title"] == "Weekly Nutrition Summary"
        assert result["macro_analysis"]["avg_protein"] == 50

        # Verify instructions were included in prompt
        args, _ = mock_gen.call_args
        assert "registered dietitian" in args[0]
