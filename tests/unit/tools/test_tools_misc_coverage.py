"""Coverage tests for assorted tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools import (
    analytics,
    clinical,
    connector,
    cottage,
    crud,
    flavor,
    parser,
    recipe_extractor,
    safety,
    suggest,
    taste_buddy,
)


class DummyFirestore:
    def __init__(self):
        self.logs = []
        self.recent_logs = None
        self.preferences = {"dietary_patterns": ["vegan"]}

    async def get_user_logs(self, user_id, limit=None, days=None):
        if days is not None and self.recent_logs is not None:
            return self.recent_logs
        return self.logs

    async def get_user_preferences(self, user_id):
        return self.preferences

    async def get_log(self, user_id, log_id):
        return next((log for log in self.logs if log.get("id") == log_id), None)

    async def update_log(self, user_id, log_id, updates):
        if log_id == "boom":
            raise ValueError("boom")
        return True

    async def create_log(self, user_id, data):
        return "log_1"


@pytest.mark.asyncio
async def test_analytics_helpers_and_functions():
    food_logs = [{"dish_name": "Pasta", "nutrition": {"calories": 100}}]
    with patch(
        "fcp.tools.analytics.gemini.generate_with_code_execution",
        new=AsyncMock(return_value={"text": "ok", "code": "x=1", "execution_result": "out"}),
    ):
        result = await analytics.calculate_nutrition_stats(food_logs, period="week")
        assert result["entry_count"] == 1

        result = await analytics.analyze_eating_patterns(food_logs)
        assert "pattern_analysis" in result

        result = await analytics.calculate_trend_report(food_logs, metric="calories")
        assert result["metric"] == "calories"

        result = await analytics.compare_periods(food_logs, food_logs, period1_name="A", period2_name="B")
        assert result["period1"]["name"] == "A"

        result = await analytics.generate_nutrition_report(food_logs, user_goals={"calories": 2000})
        assert "comparison" not in result

    with pytest.raises(ValueError):
        await analytics.calculate_trend_report(food_logs, metric="invalid")


@pytest.mark.asyncio
async def test_flavor_pairings_success_list_and_error():
    with patch("fcp.tools.flavor.gemini.generate_json", new=AsyncMock(return_value=[{"pairings": []}])):
        result = await flavor.get_flavor_pairings("steak")
        assert "pairings" in result

    with patch("fcp.tools.flavor.gemini.generate_json", new=AsyncMock(side_effect=Exception("boom"))):
        result = await flavor.get_flavor_pairings("steak")
        assert "error" in result


@pytest.mark.asyncio
async def test_suggest_meal_success_and_fallback():
    db = DummyFirestore()
    db.logs = [{"dish_name": "Soup", "venue_name": "Home"}]
    db.recent_logs = []
    with patch("fcp.tools.suggest.firestore_client", db):
        with patch("fcp.tools.suggest.get_taste_profile", new=AsyncMock(return_value={"likes": []})):
            with patch(
                "fcp.tools.suggest.gemini.generate_json",
                new=AsyncMock(return_value={"suggestions": [{"dish_name": "Pasta"}]}),
            ):
                result = await suggest.suggest_meal("u1", context="lunch")
                assert result[0]["dish_name"] == "Pasta"

            with patch(
                "fcp.tools.suggest.gemini.generate_json",
                new=AsyncMock(side_effect=Exception("boom")),
            ):
                result = await suggest.suggest_meal("u1", context="lunch")
                assert result


def test_simple_suggestions_counts_repeat():
    logs = [
        {"dish_name": "Soup", "venue_name": "Home"},
        {"dish_name": "Soup", "venue_name": "Home"},
    ]
    result = suggest._simple_suggestions(logs, recent_dishes=[])
    assert result[0]["dish_name"] == "Soup"


@pytest.mark.asyncio
async def test_cottage_label_success_list_and_error():
    with patch("fcp.tools.cottage.gemini.generate_json", new=AsyncMock(return_value=[{"label_text": "ok"}])):
        result = await cottage.generate_cottage_label("Jam", ["sugar"])
        assert result["label_text"] == "ok"

    with patch("fcp.tools.cottage.gemini.generate_json", new=AsyncMock(side_effect=Exception("boom"))):
        result = await cottage.generate_cottage_label("Jam", ["sugar"])
        assert result["status"] == "failed"


@pytest.mark.asyncio
async def test_crud_update_delete_and_donate():
    db = DummyFirestore()
    db.logs = [{"id": "1", "dish_name": "Soup"}, {"id": "boom", "dish_name": "Soup"}]
    with patch("fcp.tools.crud.firestore_client", db):
        result = await crud.update_meal("u1", "missing", {"dish_name": "x"})
        assert result["error"] == "Log not found"

        result = await crud.update_meal("u1", "1", {"invalid": "x"})
        assert result["error"] == "No valid fields to update"

        result = await crud.update_meal("u1", "boom", {"dish_name": "x"})
        assert result["success"] is False

        result = await crud.delete_meal("u1", "missing")
        assert result["error"] == "Log not found"

        result = await crud.delete_meal("u1", "boom")
        assert result["success"] is False

        result = await crud.donate_meal("u1", "missing")
        assert result["success"] is False

        result = await crud.donate_meal("u1", "1", organization="Org")
        assert result["organization"] == "Org"
        result = await crud.donate_meal("u1", "boom")
        assert result["success"] is False


@pytest.mark.asyncio
async def test_crud_add_to_pantry():
    db = DummyFirestore()
    db.update_pantry_items_batch = AsyncMock(return_value=["eggs"])
    with patch("fcp.tools.crud.firestore_client", db):
        result = await crud.add_to_pantry("u1", ["eggs"])
        assert result == ["eggs"]


@pytest.mark.asyncio
async def test_clinical_report_paths():
    db = DummyFirestore()
    db.logs = []
    with patch("fcp.tools.clinical.firestore_client", db):
        result = await clinical.generate_dietitian_report("u1")
        assert "error" in result

        db.logs = [{"dish_name": "Salad", "created_at": "2025-01-01"}]
        with patch(
            "fcp.tools.clinical.gemini.generate_json",
            new=AsyncMock(return_value=[{"report_title": "ok"}]),
        ):
            result = await clinical.generate_dietitian_report("u1", focus_area="protein")
            assert result["report_title"] == "ok"

        with patch(
            "fcp.tools.clinical.gemini.generate_json",
            new=AsyncMock(side_effect=Exception("boom")),
        ):
            result = await clinical.generate_dietitian_report("u1")
            assert result["status"] == "failed"


@pytest.mark.asyncio
async def test_connector_tools():
    result = await connector.sync_to_calendar("u1", "Dinner", "2025-01-01T00:00:00Z", description="desc")
    assert result["service"] == "Google Calendar"
    result = await connector.save_to_drive("u1", "file.md", "content")
    assert result["service"] == "Google Drive"


@pytest.mark.asyncio
async def test_parser_and_recipe_extractor():
    with patch(
        "fcp.tools.parser.gemini.generate_json",
        new=AsyncMock(return_value=[{"venue_name": "Cafe", "dishes": []}]),
    ):
        result = await parser.parse_menu("http://image")
        assert result["venue_name"] == "Cafe"

    with patch(
        "fcp.tools.parser.gemini.generate_json",
        new=AsyncMock(return_value={"venue_name": "Deli", "dishes": []}),
    ):
        result = await parser.parse_menu("http://image")
        assert result["venue_name"] == "Deli"

    with patch(
        "fcp.tools.parser.gemini.generate_json",
        new=AsyncMock(side_effect=Exception("boom")),
    ):
        result = await parser.parse_menu("http://image")
        assert "error" in result

    with patch(
        "fcp.tools.recipe_extractor.gemini.generate_json",
        new=AsyncMock(return_value=[{"title": "Pie", "servings": "4", "ingredients": "eggs"}]),
    ):
        result = await recipe_extractor.extract_recipe_from_media(image_url="http://img", additional_notes="x")
        assert result["title"] == "Pie"
        assert result["servings"] == 4
        assert result["ingredients"] == ["eggs"]

    with patch(
        "fcp.tools.recipe_extractor.gemini.generate_json",
        new=AsyncMock(return_value="not dict"),
    ):
        result = await recipe_extractor.extract_recipe_from_media(image_url="http://img")
        assert result["title"] == "Untitled Recipe"

    with patch(
        "fcp.tools.recipe_extractor.gemini.generate_json",
        new=AsyncMock(side_effect=Exception("boom")),
    ):
        result = await recipe_extractor.extract_recipe_from_media(image_url="http://img")
        assert "error" in result


@pytest.mark.asyncio
async def test_taste_buddy_paths():
    with patch(
        "fcp.tools.taste_buddy.gemini.generate_json",
        new=AsyncMock(return_value=[{"is_safe": True, "warnings": "ok"}]),
    ):
        result = await taste_buddy.check_dietary_compatibility("Dish", ["a"], ["b"], ["c"])
        assert result["is_safe"] is True
        assert result["warnings"] == ["ok"]

    with patch(
        "fcp.tools.taste_buddy.gemini.generate_json",
        new=AsyncMock(return_value="bad"),
    ):
        result = await taste_buddy.check_dietary_compatibility("Dish", [], [], [])
        assert result["is_safe"] is False

    with patch(
        "fcp.tools.taste_buddy.gemini.generate_json",
        new=AsyncMock(side_effect=Exception("boom")),
    ):
        result = await taste_buddy.check_dietary_compatibility("Dish", [], [], [])
        assert result["error"] == "boom"


@pytest.mark.asyncio
async def test_safety_alerts_missing_flags():
    with patch(
        "fcp.tools.safety.gemini.generate_json_with_grounding",
        new=AsyncMock(return_value={"data": {}, "sources": []}),
    ):
        result = await safety.check_food_recalls("eggs")
        assert result["has_active_recall"] is False

    with patch(
        "fcp.tools.safety.gemini.generate_json_with_grounding",
        new=AsyncMock(return_value={"data": {}, "sources": []}),
    ):
        result = await safety.check_allergen_alerts("milk", allergens=["dairy"])
        assert result["has_alert"] is False
