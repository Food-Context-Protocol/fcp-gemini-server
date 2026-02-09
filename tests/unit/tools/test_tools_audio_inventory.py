"""Coverage tests for audio and inventory tools."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools import audio, inventory


class DummyFirestore:
    def __init__(self):
        self.created = []
        self.updated = []
        self.deleted = []
        self.pantry = []
        self.preferences = {"top_cuisines": ["Italian"], "dietary_patterns": ["vegetarian"]}

    async def create_log(self, user_id, log_data):
        self.created.append((user_id, log_data))
        return "log_1"

    async def get_pantry(self, user_id):
        return self.pantry

    async def get_user_preferences(self, user_id):
        return self.preferences

    async def update_pantry_items_batch(self, user_id, items_data):
        return [item["name"] for item in items_data]

    async def update_pantry_item(self, user_id, item_data):
        self.updated.append((user_id, item_data))
        return item_data["id"]

    async def delete_pantry_item(self, user_id, item_id):
        self.deleted.append((user_id, item_id))
        return True


@pytest.mark.asyncio
async def test_log_meal_from_audio_success_and_failures():
    db = DummyFirestore()
    with patch("fcp.tools.audio.firestore_client", db):
        with patch(
            "fcp.tools.audio.gemini.generate_json",
            new=AsyncMock(return_value={"transcription": "hi", "dish_name": "Soup", "venue": "Home", "notes": ""}),
        ):
            with patch(
                "fcp.tools.audio.analyze_voice_transcript",
                new=AsyncMock(return_value={"dish_name": "Soup"}),
            ):
                result = await audio.log_meal_from_audio("u1", "http://audio", notes="tasty")
                assert result["id"] == "log_1"

        # Extraction failed (no dish_name)
        with patch(
            "fcp.tools.audio.gemini.generate_json",
            new=AsyncMock(return_value={"transcription": "hi", "dish_name": "", "venue": "Home", "notes": ""}),
        ):
            with patch(
                "fcp.tools.audio.analyze_voice_transcript",
                new=AsyncMock(return_value={"dish_name": None, "error": "no dish"}),
            ):
                result = await audio.log_meal_from_audio("u1", "http://audio")
                assert result["status"] == "failed"

        # Gemini error
        with patch(
            "fcp.tools.audio.gemini.generate_json",
            new=AsyncMock(side_effect=Exception("boom")),
        ):
            result = await audio.log_meal_from_audio("u1", "http://audio")
            assert result["status"] == "failed"


@pytest.mark.asyncio
async def test_analyze_voice_transcript_and_correction():
    with patch(
        "fcp.tools.audio.gemini.generate_json",
        new=AsyncMock(return_value={"dish_name": "Pasta", "confidence": 2.5}),
    ):
        result = await audio.analyze_voice_transcript("ate pasta")
        assert result["dish_name"] == "Pasta"
        assert result["confidence"] == 1.0

    with patch(
        "fcp.tools.audio.gemini.generate_json",
        new=AsyncMock(return_value={"dish_name": None, "error": "nope"}),
    ):
        result = await audio.analyze_voice_transcript("???")
        assert result["error"] == "nope"

    with patch(
        "fcp.tools.audio.gemini.generate_json",
        new=AsyncMock(side_effect=Exception("boom")),
    ):
        result = await audio.analyze_voice_transcript("oops")
        assert result["error"] == "Error analyzing voice transcript"

    with patch(
        "fcp.tools.audio.gemini.generate_json",
        new=AsyncMock(return_value={"field": "dish_name", "new_value": "Soup", "confidence": -1}),
    ):
        result = await audio.extract_voice_correction("fix it")
        assert result["confidence"] == 0.0

    with patch(
        "fcp.tools.audio.gemini.generate_json",
        new=AsyncMock(side_effect=Exception("boom")),
    ):
        result = await audio.extract_voice_correction("fix it")
        assert result["error"] == "Error extracting voice correction"


@pytest.mark.asyncio
async def test_inventory_suggestions_and_expiry():
    db = DummyFirestore()
    with patch("fcp.tools.inventory.firestore_client", db):
        # Empty pantry
        db.pantry = []
        result = await inventory.suggest_recipe_from_pantry("u1")
        assert result["suggestions"] == []

        # Pantry with items success
        db.pantry = [{"name": "eggs"}]
        with patch(
            "fcp.tools.inventory.gemini.generate_json",
            new=AsyncMock(return_value={"suggestions": [{"name": "Omelet"}]}),
        ):
            result = await inventory.suggest_recipe_from_pantry("u1", context="breakfast")
            assert result["pantry_count"] == 1

        # Gemini error
        with patch(
            "fcp.tools.inventory.gemini.generate_json",
            new=AsyncMock(side_effect=Exception("boom")),
        ):
            result = await inventory.suggest_recipe_from_pantry("u1")
            assert result["status"] == "failed"

        # check_pantry_expiry
        today = datetime.now()
        db.pantry = [
            {"name": "milk", "purchase_date": today},
        ]
        with patch(
            "fcp.tools.inventory.gemini.generate_json",
            new=AsyncMock(return_value={"alerts": []}),
        ):
            result = await inventory.check_pantry_expiry("u1")
            assert "alerts" in result

        with patch(
            "fcp.tools.inventory.gemini.generate_json",
            new=AsyncMock(side_effect=Exception("boom")),
        ):
            result = await inventory.check_pantry_expiry("u1")
            assert "error" in result


@pytest.mark.asyncio
async def test_inventory_add_update_delete_and_expiring():
    db = DummyFirestore()
    with patch("fcp.tools.inventory.firestore_client", db):
        result = await inventory.add_to_pantry("u1", ["eggs"])
        assert result == ["eggs"]

        # check_expiring_items
        today = datetime.now().date()
        db.pantry = [
            {"id": "1", "name": "old", "expiration_date": (today - timedelta(days=1)).isoformat()},
            {"id": "2", "name": "soon", "expiration_date": (today + timedelta(days=2)).isoformat()},
            {"id": "3", "name": "bad", "expiration_date": "invalid"},
            {"id": "4", "name": "none"},
        ]
        exp = await inventory.check_expiring_items("u1", days_threshold=3)
        assert len(exp["expired"]) == 1
        assert len(exp["expiring_soon"]) == 1

        # update_pantry_item not found
        result = await inventory.update_pantry_item("u1", "missing", name="x")
        assert result["success"] is False

        # update_pantry_item success
        result = await inventory.update_pantry_item("u1", "2", name="new")
        assert result["success"] is True

        # update_pantry_item exception
        with patch.object(db, "update_pantry_item", new=AsyncMock(side_effect=Exception("boom"))):
            result = await inventory.update_pantry_item("u1", "2", name="new")
            assert result["success"] is False

        # delete_pantry_item paths
        result = await inventory.delete_pantry_item("u1", "2")
        assert result["success"] is True
        with patch.object(db, "delete_pantry_item", new=AsyncMock(return_value=False)):
            result = await inventory.delete_pantry_item("u1", "missing")
            assert result["success"] is False
        with patch.object(db, "delete_pantry_item", new=AsyncMock(side_effect=Exception("boom"))):
            result = await inventory.delete_pantry_item("u1", "missing")
            assert result["success"] is False


@pytest.mark.asyncio
async def test_inventory_deduct_and_suggest_meals():
    db = DummyFirestore()
    with patch("fcp.tools.inventory.firestore_client", db):
        # Empty pantry
        db.pantry = []
        result = await inventory.deduct_from_pantry("u1", ["salt"])
        assert result["not_found"] == ["salt"]

        # Pantry with one item
        db.pantry = [{"id": "1", "name": "Salt", "quantity": 1}]
        with patch(
            "fcp.tools.inventory.gemini.generate_json",
            new=AsyncMock(
                return_value=[{"matches": [{"ingredient": "salt", "pantry_item": "Salt", "estimated_quantity": "x"}]}]
            ),
        ):
            result = await inventory.deduct_from_pantry("u1", ["salt"])
            assert result["deducted"][0]["removed"] is True

        # Update path and low stock
        db.pantry = [{"id": "2", "name": "Pepper", "quantity": 3}]
        with patch(
            "fcp.tools.inventory.gemini.generate_json",
            new=AsyncMock(
                return_value={"matches": [{"ingredient": "pepper", "pantry_item": "Pepper", "estimated_quantity": 1}]}
            ),
        ):
            result = await inventory.deduct_from_pantry("u1", ["pepper"], servings=1)
            assert "remaining" in result["deducted"][0]
            assert "Pepper" in result["low_stock"]

        # not found match
        db.pantry = [{"id": "3", "name": "Sugar", "quantity": 5}]
        with patch(
            "fcp.tools.inventory.gemini.generate_json",
            new=AsyncMock(return_value={"matches": [{"ingredient": "salt", "pantry_item": None}]}),
        ):
            result = await inventory.deduct_from_pantry("u1", ["salt"])
            assert "salt" in result["not_found"]

        # suggest meals from pantry
        db.pantry = [{"name": "eggs"}]
        with patch(
            "fcp.tools.inventory.gemini.generate_json",
            new=AsyncMock(return_value=[{"suggestions": []}]),
        ):
            result = await inventory.suggest_meals_from_pantry("u1", prioritize_expiring=False)
            assert "suggestions" in result

        # prioritize expiring with empty pantry
        db.pantry = []
        result = await inventory.suggest_meals_from_pantry("u1", prioritize_expiring=True)
        assert "message" in result
