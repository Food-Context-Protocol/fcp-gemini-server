"""Tests for openFDA API client."""

import os
from unittest.mock import patch

import httpx
import pytest
import respx

from fcp.services.fda import (
    FDA_BASE_URL,
    search_drug_food_interactions,
    search_food_recalls,
)


class TestSearchFoodRecalls:
    """Tests for search_food_recalls."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_recall_search(self):
        """Should return recall results."""
        respx.get(f"{FDA_BASE_URL}/food/enforcement.json").mock(
            return_value=httpx.Response(
                200,
                json={
                    "meta": {"results": {"total": 1}},
                    "results": [
                        {
                            "recall_number": "F-123-2026",
                            "reason_for_recall": "Undeclared allergen",
                            "status": "Ongoing",
                            "product_description": "Test Product",
                        }
                    ],
                },
            )
        )
        result = await search_food_recalls("peanut butter")
        assert len(result["results"]) == 1
        assert result["results"][0]["recall_number"] == "F-123-2026"

    @respx.mock
    @pytest.mark.asyncio
    async def test_no_results_404(self):
        """Should return empty results on 404."""
        respx.get(f"{FDA_BASE_URL}/food/enforcement.json").mock(return_value=httpx.Response(404))
        result = await search_food_recalls("unicorn fruit")
        assert result["results"] == []
        assert result["meta"]["total"] == 0

    @respx.mock
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Should handle timeout gracefully."""
        respx.get(f"{FDA_BASE_URL}/food/enforcement.json").mock(
            side_effect=httpx.TimeoutException("Connection timed out")
        )
        result = await search_food_recalls("anything")
        assert result["results"] == []
        assert result.get("error") == "timeout"

    @respx.mock
    @pytest.mark.asyncio
    async def test_server_error_handling(self):
        """Should handle 5xx errors gracefully."""
        respx.get(f"{FDA_BASE_URL}/food/enforcement.json").mock(return_value=httpx.Response(500))
        result = await search_food_recalls("anything")
        assert result["results"] == []
        assert "error" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_api_key_included_when_set(self):
        """Should include API key in params when configured."""
        with patch.dict(os.environ, {"FDA_API_KEY": "test-key-123"}):
            from importlib import reload

            import fcp.services.fda as fda_mod

            reload(fda_mod)

            route = respx.get(f"{FDA_BASE_URL}/food/enforcement.json").mock(
                return_value=httpx.Response(200, json={"results": [], "meta": {"results": {"total": 0}}})
            )
            await fda_mod.search_food_recalls("test")
            assert "api_key" in str(route.calls[0].request.url)

            # Restore
            reload(fda_mod)

    @respx.mock
    @pytest.mark.asyncio
    async def test_unexpected_exception(self):
        """Should handle unexpected exceptions gracefully."""
        respx.get(f"{FDA_BASE_URL}/food/enforcement.json").mock(side_effect=Exception("Network error"))
        result = await search_food_recalls("test")
        assert result["results"] == []
        assert "error" in result


class TestSearchDrugFoodInteractions:
    """Tests for search_drug_food_interactions."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_interaction_search(self):
        """Should return drug-food interaction data."""
        respx.get(f"{FDA_BASE_URL}/drug/label.json").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "openfda": {"generic_name": ["warfarin"]},
                            "food_interaction": [
                                "Avoid grapefruit juice",
                                "Vitamin K-rich foods may reduce effectiveness",
                            ],
                        }
                    ],
                },
            )
        )
        result = await search_drug_food_interactions("warfarin")
        assert len(result["interactions"]) == 2
        assert "grapefruit" in result["interactions"][0].lower()
        assert result["drug_name"] == "warfarin"

    @respx.mock
    @pytest.mark.asyncio
    async def test_no_results_404(self):
        """Should return empty interactions on 404."""
        respx.get(f"{FDA_BASE_URL}/drug/label.json").mock(return_value=httpx.Response(404))
        result = await search_drug_food_interactions("madeupdrugxyz")
        assert result["interactions"] == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_no_food_interactions_in_label(self):
        """Should return empty when label has no food_interaction field."""
        respx.get(f"{FDA_BASE_URL}/drug/label.json").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "openfda": {"generic_name": ["aspirin"]},
                        }
                    ],
                },
            )
        )
        result = await search_drug_food_interactions("aspirin")
        assert result["interactions"] == []
        assert result["label_count"] == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Should handle timeout gracefully."""
        respx.get(f"{FDA_BASE_URL}/drug/label.json").mock(side_effect=httpx.TimeoutException("timeout"))
        result = await search_drug_food_interactions("test")
        assert result["interactions"] == []
        assert result.get("error") == "timeout"

    @respx.mock
    @pytest.mark.asyncio
    async def test_server_error(self):
        """Should handle server errors gracefully."""
        respx.get(f"{FDA_BASE_URL}/drug/label.json").mock(return_value=httpx.Response(503))
        result = await search_drug_food_interactions("test")
        assert result["interactions"] == []
        assert "error" in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_unexpected_exception(self):
        """Should handle unexpected exceptions gracefully."""
        respx.get(f"{FDA_BASE_URL}/drug/label.json").mock(side_effect=Exception("Unexpected"))
        result = await search_drug_food_interactions("test")
        assert result["interactions"] == []
        assert "error" in result
