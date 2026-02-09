"""Additional coverage tests for pantry inventory tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools import inventory


class DummyDB:
    def __init__(self, pantry):
        self._pantry = pantry
        self.updated = []
        self.deleted = []

    async def get_pantry(self, user_id):
        return self._pantry

    async def update_pantry_item(self, user_id, item):
        self.updated.append(item)
        return item["id"]

    async def delete_pantry_item(self, user_id, item_id):
        self.deleted.append(item_id)
        return True


@pytest.mark.asyncio
async def test_check_pantry_expiry_empty():
    db = DummyDB([])
    with patch("fcp.tools.inventory.firestore_client", db):
        result = await inventory.check_pantry_expiry("u1")
        assert result["message"] == "Pantry is empty."


@pytest.mark.asyncio
async def test_deduct_from_pantry_not_found_and_low_stock():
    pantry = [{"id": "1", "name": "Milk", "quantity": 3}]
    db = DummyDB(pantry)

    matches = {"matches": [{"ingredient": "milk", "pantry_item": "Milk", "estimated_quantity": 1}]}
    with (
        patch("fcp.tools.inventory.firestore_client", db),
        patch("fcp.tools.inventory.gemini.generate_json", new=AsyncMock(return_value=matches)),
    ):
        result = await inventory.deduct_from_pantry("u1", ["milk"], servings=1)
        assert result["low_stock"] == ["Milk"]

    matches_not_low = {"matches": [{"ingredient": "milk", "pantry_item": "Milk", "estimated_quantity": 0.5}]}
    with (
        patch("fcp.tools.inventory.firestore_client", db),
        patch("fcp.tools.inventory.gemini.generate_json", new=AsyncMock(return_value=matches_not_low)),
    ):
        result = await inventory.deduct_from_pantry("u1", ["milk"], servings=1)
        assert result["low_stock"] == []

    missing_match = {"matches": [{"ingredient": "eggs", "pantry_item": "Eggs", "estimated_quantity": 1}]}
    with (
        patch("fcp.tools.inventory.firestore_client", db),
        patch("fcp.tools.inventory.gemini.generate_json", new=AsyncMock(return_value=missing_match)),
    ):
        result = await inventory.deduct_from_pantry("u1", ["eggs"], servings=1)
        assert "eggs" in result["not_found"]


@pytest.mark.asyncio
async def test_check_expiring_items_paths():
    db = DummyDB(
        [
            {"id": "1", "name": "Old", "expiration_date": "2020-01-01"},
            {"id": "2", "name": "Soon", "expiration_date": "2099-01-02"},
            {"id": "3", "name": "Bad", "expiration_date": "not-a-date"},
            {"id": "4", "name": "Far", "expiration_date": "2300-01-01"},
        ]
    )
    with patch("fcp.tools.inventory.firestore_client", db):
        result = await inventory.check_expiring_items("u1", days_threshold=365 * 200)
        assert any(item["id"] == "1" for item in result["expired"])
        assert any(item["id"] == "2" for item in result["expiring_soon"])


@pytest.mark.asyncio
async def test_suggest_meals_from_pantry_with_expiring_and_list_response():
    pantry = [{"id": "1", "name": "Rice"}]
    db = DummyDB(pantry)
    with (
        patch("fcp.tools.inventory.firestore_client", db),
        patch(
            "fcp.tools.inventory.check_expiring_items",
            new=AsyncMock(return_value={"expiring_soon": [{"name": "Rice"}]}),
        ),
        patch("fcp.tools.inventory.gemini.generate_json", new=AsyncMock(return_value=[{"suggestions": []}])),
    ):
        result = await inventory.suggest_meals_from_pantry("u1", prioritize_expiring=True)
        assert result["suggestions"] == []


@pytest.mark.asyncio
async def test_suggest_meals_from_pantry_dict_response():
    pantry = [{"id": "1", "name": "Rice"}]
    db = DummyDB(pantry)
    with (
        patch("fcp.tools.inventory.firestore_client", db),
        patch(
            "fcp.tools.inventory.check_expiring_items",
            new=AsyncMock(return_value={"expiring_soon": []}),
        ),
        patch(
            "fcp.tools.inventory.gemini.generate_json", new=AsyncMock(return_value={"suggestions": [{"meal": "Rice"}]})
        ),
    ):
        result = await inventory.suggest_meals_from_pantry("u1", prioritize_expiring=False)
        assert result["suggestions"][0]["meal"] == "Rice"
