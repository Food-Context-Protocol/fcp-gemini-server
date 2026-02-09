"""Coverage tests for external API clients."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from fcp.tools.external import open_food_facts, usda


class DummyResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}

    def json(self):
        return self._json


class DummyClient:
    def __init__(self, response, *args, **kwargs):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, *args, **kwargs):
        return self._response


@pytest.mark.asyncio
async def test_open_food_facts_lookup_product_paths():
    # Non-200 returns error dict
    response = DummyResponse(status_code=404, json_data={})
    with patch("fcp.tools.external.open_food_facts.httpx.AsyncClient", new=lambda *a, **k: DummyClient(response)):
        result = await open_food_facts.lookup_product("123")
        assert result == {"error": "Product not found or API error"}

    # Status 0 returns error dict
    response = DummyResponse(status_code=200, json_data={"status": 0})
    with patch("fcp.tools.external.open_food_facts.httpx.AsyncClient", new=lambda *a, **k: DummyClient(response)):
        result = await open_food_facts.lookup_product("123")
        assert result == {"error": "Product not found or API error"}

    # Success returns product data
    response = DummyResponse(
        status_code=200,
        json_data={
            "status": 1,
            "product": {
                "product_name": "Bar",
                "brands": "Brand",
                "ingredients_text": "x",
                "nutriments": {"calories": 100},
                "nova_group": 4,
                "ecoscore_grade": "b",
                "image_url": "http://img",
            },
        },
    )
    with patch("fcp.tools.external.open_food_facts.httpx.AsyncClient", new=lambda *a, **k: DummyClient(response)):
        result = await open_food_facts.lookup_product("123")
        assert result is not None
        assert result["dish_name"] == "Bar"
        assert result["source"] == "open_food_facts"


@pytest.mark.asyncio
async def test_open_food_facts_lookup_exception():
    class ErrorClient(DummyClient):
        async def get(self, *args, **kwargs):
            raise RuntimeError("boom")

    with patch("fcp.tools.external.open_food_facts.httpx.AsyncClient", new=lambda *a, **k: ErrorClient(None)):
        result = await open_food_facts.lookup_product("123")
        assert result == {"error": "boom"}


@pytest.mark.asyncio
async def test_open_food_facts_search_paths():
    response = DummyResponse(
        status_code=200,
        json_data={
            "products": [
                {"product_name": "Chips", "brands": "A", "code": "1"},
                {"code": "2"},
            ]
        },
    )
    with patch("fcp.tools.external.open_food_facts.httpx.AsyncClient", new=lambda *a, **k: DummyClient(response)):
        result = await open_food_facts.search_by_name("chips")
        assert result[0]["product_name"] == "Chips"

    response = DummyResponse(status_code=500, json_data={})
    with patch("fcp.tools.external.open_food_facts.httpx.AsyncClient", new=lambda *a, **k: DummyClient(response)):
        assert await open_food_facts.search_by_name("chips") == []

    class ErrorClient(DummyClient):
        async def get(self, *args, **kwargs):
            raise RuntimeError("boom")

    with patch("fcp.tools.external.open_food_facts.httpx.AsyncClient", new=lambda *a, **k: ErrorClient(None)):
        assert await open_food_facts.search_by_name("chips") == []


def test_open_food_facts_helper_functions():
    assert open_food_facts.get_nova_group({"nova_group": "bad"}) is None
    assert open_food_facts.get_nova_group({"nova_group": "2"}) == 2
    assert open_food_facts.get_nova_group({}) is None
    additives = open_food_facts.get_additives(
        {"additives_tags": ["en:e300", "fr:e621-monosodium-glutamate", "e500", 123]}
    )
    codes = [a["code"] for a in additives]
    assert "E300" in codes
    assert "E621" in codes
    assert "E500" in codes


@pytest.mark.asyncio
async def test_usda_search_and_details_paths():
    with patch.dict("os.environ", {}, clear=True):
        assert await usda.search_foods("apple") == []
        assert await usda.get_food_details(1) == {}

    response = DummyResponse(status_code=200, json_data={"foods": [{"fdcId": 1}]})
    with (
        patch.dict("os.environ", {"USDA_API_KEY": "key"}),
        patch("fcp.tools.external.usda.httpx.AsyncClient", new=lambda *a, **k: DummyClient(response)),
    ):
        results = await usda.search_foods("apple")
        assert results[0]["fdcId"] == 1

    response = DummyResponse(status_code=200, json_data={"name": "Food"})
    with (
        patch.dict("os.environ", {"USDA_API_KEY": "key"}),
        patch("fcp.tools.external.usda.httpx.AsyncClient", new=lambda *a, **k: DummyClient(response)),
    ):
        data = await usda.get_food_details(10)
        assert data["name"] == "Food"

    response = DummyResponse(status_code=404, json_data={})
    with (
        patch.dict("os.environ", {"USDA_API_KEY": "key"}),
        patch("fcp.tools.external.usda.httpx.AsyncClient", new=lambda *a, **k: DummyClient(response)),
    ):
        assert await usda.search_foods("apple") == []
        assert await usda.get_food_details(10) == {}


@pytest.mark.asyncio
async def test_usda_timeout_and_request_error():
    class TimeoutClient(DummyClient):
        async def get(self, *args, **kwargs):
            raise httpx.TimeoutException("timeout")

    class ErrorClient(DummyClient):
        async def get(self, *args, **kwargs):
            raise httpx.RequestError("boom", request=None)

    with (
        patch.dict("os.environ", {"USDA_API_KEY": "key"}),
        patch("fcp.tools.external.usda.httpx.AsyncClient", new=lambda *a, **k: TimeoutClient(None)),
    ):
        assert await usda.search_foods("apple") == []

    with (
        patch.dict("os.environ", {"USDA_API_KEY": "key"}),
        patch("fcp.tools.external.usda.httpx.AsyncClient", new=lambda *a, **k: ErrorClient(None)),
    ):
        assert await usda.get_food_details(1) == {}

    with (
        patch.dict("os.environ", {"USDA_API_KEY": "key"}),
        patch("fcp.tools.external.usda.httpx.AsyncClient", new=lambda *a, **k: ErrorClient(None)),
    ):
        assert await usda.search_foods("apple") == []

    with (
        patch.dict("os.environ", {"USDA_API_KEY": "key"}),
        patch("fcp.tools.external.usda.httpx.AsyncClient", new=lambda *a, **k: TimeoutClient(None)),
    ):
        assert await usda.get_food_details(1) == {}


def test_usda_extract_micronutrients_and_normalize():
    data = {
        "foodNutrients": [
            {"nutrient": {"name": "Iron, Fe", "unitName": "mg"}, "amount": 2.5},
            {"nutrient": {"name": "Vitamin B-12", "unitName": "µg"}, "amount": 1.2},
        ]
    }
    result = usda.extract_micronutrients(data)
    assert result["iron_mg"] == 2.5
    assert result["vitamin_b12_ug"] == 1.2


def test_usda_extract_micronutrients_skips_missing_fields():
    data = {
        "foodNutrients": [
            {"nutrient": {"name": "", "unitName": "mg"}, "amount": 1.0},
            {"nutrient": {"name": "Protein", "unitName": "g"}, "amount": None},
        ]
    }
    result = usda.extract_micronutrients(data)
    assert result == {}


@pytest.mark.asyncio
async def test_usda_get_food_by_name():
    with patch("fcp.tools.external.usda.search_foods", new=AsyncMock(return_value=[{"fdcId": 5}])):
        with patch("fcp.tools.external.usda.get_food_details", new=AsyncMock(return_value={"id": 5})):
            result = await usda.get_food_by_name("banana")
            assert result is not None
            assert result["id"] == 5


@pytest.mark.asyncio
async def test_usda_get_food_by_name_no_results():
    with patch("fcp.tools.external.usda.search_foods", new=AsyncMock(return_value=[])):
        assert await usda.get_food_by_name("unknown") is None

    with patch("fcp.tools.external.usda.search_foods", new=AsyncMock(return_value=[{"fdcId": None}])):
        assert await usda.get_food_by_name("unknown") is None
