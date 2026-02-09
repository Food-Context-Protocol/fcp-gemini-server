"""Tests for knowledge graph enrichment tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fcp.tools import knowledge_graph


class TestEnrichWithKnowledgeGraph:
    """Tests for enrich_with_knowledge_graph function."""

    @pytest.mark.asyncio
    async def test_returns_error_for_missing_log(self):
        """Should return error when log not found."""
        with patch("fcp.tools.knowledge_graph.get_firestore_client") as mock_db:
            mock_db.return_value.get_log = AsyncMock(return_value=None)

            result = await knowledge_graph.enrich_with_knowledge_graph("user-123", "nonexistent-log")

            assert result["success"] is False
            assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_error_for_empty_dish_name(self):
        """Should return error when log has no dish name."""
        with patch("fcp.tools.knowledge_graph.get_firestore_client") as mock_db:
            mock_db.return_value.get_log = AsyncMock(return_value={"id": "log-1"})

            result = await knowledge_graph.enrich_with_knowledge_graph("user-123", "log-1")

            assert result["success"] is False
            assert "no dish name" in result["error"]

    @pytest.mark.asyncio
    async def test_enriches_with_usda_data(self):
        """Should include USDA data when available."""
        mock_log = {"id": "log-1", "dish_name": "Apple"}

        with (
            patch("fcp.tools.knowledge_graph.get_firestore_client") as mock_db,
            patch("fcp.tools.knowledge_graph._get_usda_data") as mock_usda,
            patch("fcp.tools.knowledge_graph._get_off_data") as mock_off,
            patch("fcp.tools.knowledge_graph._get_related_foods") as mock_related,
            patch("fcp.tools.knowledge_graph._cache_knowledge"),
        ):
            mock_db.return_value.get_log = AsyncMock(return_value=mock_log)
            mock_db.return_value.update_log = AsyncMock()
            mock_usda.return_value = {
                "fdc_id": 123,
                "micronutrients": {"protein_g": 0.3},
            }
            mock_off.return_value = None
            mock_related.return_value = ["Pear", "Orange"]

            result = await knowledge_graph.enrich_with_knowledge_graph("user-123", "log-1")

            assert result["success"] is True
            assert "usda_data" in result["knowledge_graph"]
            assert result["knowledge_graph"]["usda_data"]["fdc_id"] == 123

    @pytest.mark.asyncio
    async def test_enriches_with_off_data(self):
        """Should include OFF data when available."""
        mock_log = {"id": "log-1", "dish_name": "Pasta"}

        with (
            patch("fcp.tools.knowledge_graph.get_firestore_client") as mock_db,
            patch("fcp.tools.knowledge_graph._get_usda_data") as mock_usda,
            patch("fcp.tools.knowledge_graph._get_off_data") as mock_off,
            patch("fcp.tools.knowledge_graph._get_related_foods") as mock_related,
            patch("fcp.tools.knowledge_graph._cache_knowledge"),
        ):
            mock_db.return_value.get_log = AsyncMock(return_value=mock_log)
            mock_db.return_value.update_log = AsyncMock()
            mock_usda.return_value = None
            mock_off.return_value = {
                "ecoscore": {"grade": "a"},
                "nova_group": 1,
            }
            mock_related.return_value = []

            result = await knowledge_graph.enrich_with_knowledge_graph("user-123", "log-1")

            assert result["success"] is True
            assert "off_data" in result["knowledge_graph"]
            assert result["knowledge_graph"]["off_data"]["ecoscore"]["grade"] == "a"

    @pytest.mark.asyncio
    async def test_skips_usda_when_disabled(self):
        """Should skip USDA data when include_micronutrients=False."""
        mock_log = {"id": "log-1", "dish_name": "Apple"}

        with (
            patch("fcp.tools.knowledge_graph.get_firestore_client") as mock_db,
            patch("fcp.tools.knowledge_graph._get_usda_data") as mock_usda,
            patch("fcp.tools.knowledge_graph._get_off_data") as mock_off,
            patch("fcp.tools.knowledge_graph._get_related_foods") as mock_related,
            patch("fcp.tools.knowledge_graph._cache_knowledge"),
        ):
            mock_db.return_value.get_log = AsyncMock(return_value=mock_log)
            mock_db.return_value.update_log = AsyncMock()
            mock_off.return_value = None
            mock_related.return_value = []

            result = await knowledge_graph.enrich_with_knowledge_graph(
                "user-123", "log-1", include_micronutrients=False
            )

            mock_usda.assert_not_called()
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_skips_off_when_disabled(self):
        """Should skip OFF data when include_sustainability=False."""
        mock_log = {"id": "log-1", "dish_name": "Apple"}

        with (
            patch("fcp.tools.knowledge_graph.get_firestore_client") as mock_db,
            patch("fcp.tools.knowledge_graph._get_usda_data") as mock_usda,
            patch("fcp.tools.knowledge_graph._get_off_data") as mock_off,
            patch("fcp.tools.knowledge_graph._get_related_foods") as mock_related,
            patch("fcp.tools.knowledge_graph._cache_knowledge"),
        ):
            mock_db.return_value.get_log = AsyncMock(return_value=mock_log)
            mock_db.return_value.update_log = AsyncMock()
            mock_usda.return_value = None
            mock_related.return_value = []

            result = await knowledge_graph.enrich_with_knowledge_graph(
                "user-123", "log-1", include_sustainability=False
            )

            mock_off.assert_not_called()
            assert result["success"] is True


class TestSearchKnowledge:
    """Tests for search_knowledge function."""

    @pytest.mark.asyncio
    async def test_searches_both_databases(self):
        """Should search both USDA and OFF databases."""
        with (
            patch("fcp.tools.knowledge_graph.usda.search_foods") as mock_usda,
            patch("fcp.tools.knowledge_graph.off.search_by_name") as mock_off,
        ):
            mock_usda.return_value = [{"fdcId": 123, "description": "Apple", "dataType": "Foundation"}]
            mock_off.return_value = [
                {
                    "product_name": "Apple Juice",
                    "brand": "Brand",
                    "ecoscore_grade": "b",
                    "nutriscore_grade": "c",
                }
            ]

            result = await knowledge_graph.search_knowledge("apple")

            assert len(result["usda"]) == 1
            assert len(result["off"]) == 1
            assert result["combined_count"] == 2

    @pytest.mark.asyncio
    async def test_handles_empty_results(self):
        """Should handle empty results from both databases."""
        with (
            patch("fcp.tools.knowledge_graph.usda.search_foods") as mock_usda,
            patch("fcp.tools.knowledge_graph.off.search_by_name") as mock_off,
        ):
            mock_usda.return_value = []
            mock_off.return_value = []

            result = await knowledge_graph.search_knowledge("nonexistent")

            assert result["usda"] == []
            assert result["off"] == []
            assert result["combined_count"] == 0


class TestCompareFoods:
    """Tests for compare_foods function."""

    @pytest.mark.asyncio
    async def test_returns_error_when_api_key_missing(self):
        """Should return SERVICE_UNAVAILABLE error when USDA API key not configured."""
        with patch("fcp.tools.knowledge_graph.usda._get_api_key") as mock_key:
            mock_key.return_value = None

            result = await knowledge_graph.compare_foods("apple", "banana")

            assert result["success"] is False
            assert result["error_code"] == "SERVICE_UNAVAILABLE"
            assert "API key" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_error_for_first_food_not_found(self):
        """Should return error when first food not found."""
        with (
            patch("fcp.tools.knowledge_graph.usda._get_api_key") as mock_key,
            patch("fcp.tools.knowledge_graph.usda.get_food_by_name") as mock_get,
        ):
            mock_key.return_value = "test-key"
            mock_get.return_value = None

            result = await knowledge_graph.compare_foods("nonexistent", "apple")

            assert result["success"] is False
            assert "nonexistent" in result["error"]

    @pytest.mark.asyncio
    async def test_returns_error_for_second_food_not_found(self):
        """Should return error when second food not found."""
        with (
            patch("fcp.tools.knowledge_graph.usda._get_api_key") as mock_key,
            patch("fcp.tools.knowledge_graph.usda.get_food_by_name") as mock_get,
        ):
            mock_key.return_value = "test-key"
            # First call returns data, second returns None
            mock_get.side_effect = [{"foodNutrients": []}, None]

            result = await knowledge_graph.compare_foods("apple", "nonexistent")

            assert result["success"] is False
            assert "nonexistent" in result["error"]

    @pytest.mark.asyncio
    async def test_compares_nutrients(self):
        """Should compare nutrients between two foods."""
        with (
            patch("fcp.tools.knowledge_graph.usda._get_api_key") as mock_key,
            patch("fcp.tools.knowledge_graph.usda.get_food_by_name") as mock_get,
            patch("fcp.tools.knowledge_graph.usda.extract_micronutrients") as mock_extract,
        ):
            mock_key.return_value = "test-key"
            mock_get.side_effect = [
                {"description": "Apple"},
                {"description": "Banana"},
            ]
            mock_extract.side_effect = [
                {"protein_g": 0.3, "fiber_g": 2.4},
                {"protein_g": 1.1, "fiber_g": 2.6},
            ]

            result = await knowledge_graph.compare_foods("apple", "banana")

            assert result["success"] is True
            assert result["food1"] == "apple"
            assert result["food2"] == "banana"
            assert "protein_g" in result["comparison"]
            assert result["comparison"]["protein_g"]["difference"] == -0.8

    @pytest.mark.asyncio
    async def test_compares_nutrients_with_missing_values(self):
        """Should use None for missing nutrients instead of zero."""
        with (
            patch("fcp.tools.knowledge_graph.usda._get_api_key") as mock_key,
            patch("fcp.tools.knowledge_graph.usda.get_food_by_name") as mock_get,
            patch("fcp.tools.knowledge_graph.usda.extract_micronutrients") as mock_extract,
        ):
            mock_key.return_value = "test-key"
            mock_get.side_effect = [
                {"description": "Apple"},
                {"description": "Banana"},
            ]
            # Apple has fiber, banana doesn't
            mock_extract.side_effect = [
                {"protein_g": 0.3, "fiber_g": 2.4},
                {"protein_g": 1.1},
            ]

            result = await knowledge_graph.compare_foods("apple", "banana")

            assert result["success"] is True
            # fiber_g: Apple has it, Banana doesn't
            assert result["comparison"]["fiber_g"]["food1"] == 2.4
            assert result["comparison"]["fiber_g"]["food2"] is None
            assert result["comparison"]["fiber_g"]["difference"] is None


class TestGetCachedKnowledge:
    """Tests for get_cached_knowledge function."""

    @pytest.mark.asyncio
    async def test_returns_cached_data(self):
        """Should return cached knowledge when available."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "food_name": "Apple",
            "usda_data": {"fdc_id": 123},
        }

        with patch("fcp.tools.knowledge_graph.get_firestore_client") as mock_db:
            mock_db.return_value.db.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_doc

            result = await knowledge_graph.get_cached_knowledge("user-123", "Apple")

            assert result is not None
            assert result["food_name"] == "Apple"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_cached(self):
        """Should return None when not cached."""
        mock_doc = MagicMock()
        mock_doc.exists = False

        with patch("fcp.tools.knowledge_graph.get_firestore_client") as mock_db:
            mock_db.return_value.db.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_doc

            result = await knowledge_graph.get_cached_knowledge("user-123", "Unknown")

            assert result is None


class TestPrivateFunctions:
    """Tests for private helper functions."""

    @pytest.mark.asyncio
    async def test_get_usda_data_returns_none_for_no_results(self):
        """Should return None when USDA search finds nothing."""
        with patch("fcp.tools.knowledge_graph.usda.search_foods") as mock_search:
            mock_search.return_value = []

            result = await knowledge_graph._get_usda_data("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_usda_data_returns_data(self):
        """Should return USDA data when found."""
        with (
            patch("fcp.tools.knowledge_graph.usda.search_foods") as mock_search,
            patch("fcp.tools.knowledge_graph.usda.get_food_details") as mock_details,
            patch("fcp.tools.knowledge_graph.usda.extract_micronutrients") as mock_extract,
        ):
            mock_search.return_value = [{"fdcId": 123, "description": "Apple", "dataType": "Foundation"}]
            mock_details.return_value = {"foodNutrients": []}
            mock_extract.return_value = {"protein_g": 0.3}

            result = await knowledge_graph._get_usda_data("apple")

            assert result is not None
            assert result["fdc_id"] == 123

    @pytest.mark.asyncio
    async def test_get_usda_data_returns_none_for_missing_fdc_id(self):
        """Should return None when search result has no fdcId."""
        with patch("fcp.tools.knowledge_graph.usda.search_foods") as mock_search:
            mock_search.return_value = [{"description": "Apple"}]  # No fdcId

            result = await knowledge_graph._get_usda_data("apple")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_usda_data_returns_none_for_empty_details(self):
        """Should return None when details fetch returns empty."""
        with (
            patch("fcp.tools.knowledge_graph.usda.search_foods") as mock_search,
            patch("fcp.tools.knowledge_graph.usda.get_food_details") as mock_details,
        ):
            mock_search.return_value = [{"fdcId": 123, "description": "Apple"}]
            mock_details.return_value = {}  # Empty details

            result = await knowledge_graph._get_usda_data("apple")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_off_data_returns_none_for_no_results(self):
        """Should return None when OFF search finds nothing."""
        with patch("fcp.tools.knowledge_graph.off.search_by_name") as mock_search:
            mock_search.return_value = []

            result = await knowledge_graph._get_off_data("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_off_data_returns_data(self):
        """Should return OFF data when found."""
        with patch("fcp.tools.knowledge_graph.off.search_by_name") as mock_search:
            mock_search.return_value = [
                {
                    "ecoscore_grade": "a",
                    "nova_group": 1,
                    "nutriscore_grade": "a",
                    "additives_tags": [],
                }
            ]

            result = await knowledge_graph._get_off_data("apple")

            assert result is not None
            assert result["ecoscore"]["grade"] == "a"

    @pytest.mark.asyncio
    async def test_get_related_foods_returns_list(self):
        """Should return list of related foods."""
        with patch("fcp.tools.knowledge_graph.gemini") as mock_gemini:
            mock_gemini.generate_json = AsyncMock(return_value={"related_foods": ["Pear", "Orange"]})

            result = await knowledge_graph._get_related_foods("Apple")

            assert result == ["Pear", "Orange"]

    @pytest.mark.asyncio
    async def test_get_related_foods_handles_error(self):
        """Should return empty list on error."""
        with patch("fcp.tools.knowledge_graph.gemini") as mock_gemini:
            mock_gemini.generate_json = AsyncMock(side_effect=Exception("API error"))

            result = await knowledge_graph._get_related_foods("Apple")

            assert result == []

    @pytest.mark.asyncio
    async def test_cache_knowledge_stores_data(self):
        """Should cache knowledge graph data in Firestore."""
        mock_set = MagicMock()
        mock_doc = MagicMock()
        mock_doc.set = mock_set
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc

        with patch("fcp.tools.knowledge_graph.get_firestore_client") as mock_db:
            mock_db.return_value.db.collection.return_value.document.return_value.collection.return_value = (
                mock_collection
            )

            await knowledge_graph._cache_knowledge(
                "user-123",
                "Apple Pie",
                {"usda_data": {"fdc_id": 123}},
            )

            mock_collection.document.assert_called_once_with("apple_pie")
            mock_set.assert_called_once()
            call_args = mock_set.call_args[0][0]
            assert call_args["food_name"] == "Apple Pie"
            assert call_args["usda_data"]["fdc_id"] == 123


class TestMakeSafeDocId:
    """Tests for _make_safe_doc_id edge cases."""

    def test_removes_slashes(self):
        """Should remove forward slashes which are invalid in Firestore doc IDs."""
        result = knowledge_graph._make_safe_doc_id("chicken/rice")
        assert "/" not in result
        assert result == "chicken_rice"

    def test_handles_special_characters(self):
        """Should replace all special characters with underscores."""
        result = knowledge_graph._make_safe_doc_id("café & crème brûlée!")
        assert result == "caf_cr_me_br_l_e"

    def test_handles_unicode(self):
        """Should handle unicode characters."""
        result = knowledge_graph._make_safe_doc_id("寿司 sushi")
        assert result == "sushi"

    def test_collapses_multiple_underscores(self):
        """Should collapse multiple consecutive underscores."""
        result = knowledge_graph._make_safe_doc_id("apple   pie")
        assert "__" not in result
        assert result == "apple_pie"

    def test_strips_leading_trailing_underscores(self):
        """Should strip leading and trailing underscores."""
        result = knowledge_graph._make_safe_doc_id("  apple pie  ")
        assert not result.startswith("_")
        assert not result.endswith("_")
        assert result == "apple_pie"

    def test_truncates_to_50_chars(self):
        """Should truncate long names to 50 characters."""
        long_name = "a" * 100
        result = knowledge_graph._make_safe_doc_id(long_name)
        assert len(result) <= 50

    def test_returns_unknown_for_empty_string(self):
        """Should return 'unknown' for empty string after sanitization."""
        result = knowledge_graph._make_safe_doc_id("")
        assert result == "unknown"

    def test_returns_unknown_for_only_special_chars(self):
        """Should return 'unknown' when name contains only special chars."""
        result = knowledge_graph._make_safe_doc_id("!@#$%^&*()")
        assert result == "unknown"

    def test_lowercases_input(self):
        """Should lowercase the input."""
        result = knowledge_graph._make_safe_doc_id("APPLE PIE")
        assert result == "apple_pie"


class TestEnrichmentEdgeCases:
    """Tests for enrichment edge cases."""

    @pytest.mark.asyncio
    async def test_enrichment_when_all_sources_return_no_data(self):
        """Should handle case when both USDA and OFF return no data."""
        with (
            patch("fcp.tools.knowledge_graph.get_firestore_client") as mock_db,
            patch("fcp.tools.knowledge_graph._get_usda_data") as mock_usda,
            patch("fcp.tools.knowledge_graph._get_off_data") as mock_off,
            patch("fcp.tools.knowledge_graph._get_related_foods") as mock_related,
            patch("fcp.tools.knowledge_graph._cache_knowledge") as mock_cache,
        ):
            mock_db.return_value.get_log = AsyncMock(return_value={"id": "log-1", "dish_name": "Mystery Food"})
            mock_db.return_value.update_log = AsyncMock()
            # Both external sources return no data
            mock_usda.return_value = None
            mock_off.return_value = None
            mock_related.return_value = []

            result = await knowledge_graph.enrich_with_knowledge_graph("user-123", "log-1")

            # Should still succeed but with minimal data (only enriched_at)
            assert result["success"] is True
            kg = result["knowledge_graph"]
            assert "usda_data" not in kg  # Not added when None
            assert "off_data" not in kg  # Not added when None
            assert "related_foods" not in kg  # Not added when empty
            assert "enriched_at" in kg  # Always present
            # Should still cache the result
            mock_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_enrichment_with_only_usda_data(self):
        """Should succeed when only USDA returns data."""
        with (
            patch("fcp.tools.knowledge_graph.get_firestore_client") as mock_db,
            patch("fcp.tools.knowledge_graph._get_usda_data") as mock_usda,
            patch("fcp.tools.knowledge_graph._get_off_data") as mock_off,
            patch("fcp.tools.knowledge_graph._get_related_foods") as mock_related,
            patch("fcp.tools.knowledge_graph._cache_knowledge"),
        ):
            mock_db.return_value.get_log = AsyncMock(return_value={"id": "log-1", "dish_name": "Apple"})
            mock_db.return_value.update_log = AsyncMock()
            mock_usda.return_value = {"fdc_id": 123, "nutrients": {"protein_g": 0.3}}
            mock_off.return_value = None
            mock_related.return_value = ["Pear"]

            result = await knowledge_graph.enrich_with_knowledge_graph("user-123", "log-1")

            assert result["success"] is True
            kg = result["knowledge_graph"]
            assert "usda_data" in kg
            assert kg["usda_data"]["fdc_id"] == 123
            assert "off_data" not in kg  # Not added when None

    @pytest.mark.asyncio
    async def test_enrichment_with_only_off_data(self):
        """Should succeed when only OFF returns data."""
        with (
            patch("fcp.tools.knowledge_graph.get_firestore_client") as mock_db,
            patch("fcp.tools.knowledge_graph._get_usda_data") as mock_usda,
            patch("fcp.tools.knowledge_graph._get_off_data") as mock_off,
            patch("fcp.tools.knowledge_graph._get_related_foods") as mock_related,
            patch("fcp.tools.knowledge_graph._cache_knowledge"),
        ):
            mock_db.return_value.get_log = AsyncMock(return_value={"id": "log-1", "dish_name": "Imported Snack"})
            mock_db.return_value.update_log = AsyncMock()
            mock_usda.return_value = None
            mock_off.return_value = {"ecoscore": {"grade": "b"}, "nova_group": 3}
            mock_related.return_value = []

            result = await knowledge_graph.enrich_with_knowledge_graph("user-123", "log-1")

            assert result["success"] is True
            kg = result["knowledge_graph"]
            assert "usda_data" not in kg  # Not added when None
            assert "off_data" in kg
            assert kg["off_data"]["ecoscore"]["grade"] == "b"
