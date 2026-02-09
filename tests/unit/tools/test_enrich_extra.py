"""Additional coverage tests for enrich tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_usda_nutrition_success():
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "foods": [
                    {
                        "fdcId": 123,
                        "foodNutrients": [
                            {"nutrientName": "Magnesium, Mg", "value": 1},
                            {"nutrientName": "Iron, Fe", "value": 2},
                            {"nutrientName": "Vitamin D (D2 + D3)", "value": 3},
                            {"nutrientName": "Calcium, Ca", "value": 4},
                        ],
                    }
                ]
            }

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, *_args, **_kwargs):
            return FakeResponse()

    with patch("fcp.tools.enrich.httpx.AsyncClient", return_value=FakeClient()):
        from fcp.tools.enrich import get_usda_nutrition

        result = await get_usda_nutrition("salad")

    assert result["fdc_id"] == 123
    assert result["magnesium"] == 1
    assert result["iron"] == 2
    assert result["vitamin_d"] == 3
    assert result["calcium"] == 4


@pytest.mark.asyncio
async def test_get_usda_nutrition_non_200():
    class FakeResponse:
        status_code = 500

        def json(self):
            return {}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, *_args, **_kwargs):
            return FakeResponse()

    with patch("fcp.tools.enrich.httpx.AsyncClient", return_value=FakeClient()):
        from fcp.tools.enrich import get_usda_nutrition

        result = await get_usda_nutrition("salad")

    assert result == {}


@pytest.mark.asyncio
async def test_enrich_entry_storage_not_configured():
    firestore_stub = type("FirestoreStub", (), {"get_log": AsyncMock(return_value={"image_path": "path"})})()
    with (
        patch("fcp.tools.enrich.firestore_client", firestore_stub),
        patch("fcp.tools.enrich.is_storage_configured", return_value=False),
    ):
        from fcp.tools.enrich import enrich_entry

        result = await enrich_entry("user-1", "log-1")

    assert result["success"] is False
    assert "Storage not configured" in result["error"]


@pytest.mark.asyncio
async def test_enrich_entry_sets_foodon_and_inferred_context():
    firestore_stub = type(
        "FirestoreStub",
        (),
        {
            "get_log": AsyncMock(return_value={"image_path": "path", "dish_name": "Pasta"}),
            "update_log": AsyncMock(),
        },
    )()
    enrich_payload = {
        "dish_name": "Pasta",
        "ingredients": [],
        "nutrition": {},
        "dietary_tags": [],
        "allergens": [],
        "cuisine": "italian",
        "foodon": {"foodon_id": "FOODON:123"},
        "inferred_context": {"occasion": "dinner", "notes_summary": "home cooked"},
    }
    with (
        patch("fcp.tools.enrich.firestore_client", firestore_stub),
        patch("fcp.tools.enrich.is_storage_configured", return_value=True),
        patch("fcp.tools.enrich.storage_client.get_public_url", return_value="https://example.com/image.jpg"),
        patch("fcp.tools.enrich.gemini.generate_json", new=AsyncMock(return_value=enrich_payload)),
        patch("fcp.tools.enrich.get_usda_nutrition", new=AsyncMock(return_value={})),
    ):
        from fcp.tools.enrich import enrich_entry

        result = await enrich_entry("user-1", "log-1")

    assert result["success"] is True
    update_data = firestore_stub.update_log.call_args.args[2]
    assert update_data["foodon"] == {"foodon_id": "FOODON:123"}
    assert update_data["occasion"] == "dinner"
    assert update_data["ai_notes"] == "home cooked"
