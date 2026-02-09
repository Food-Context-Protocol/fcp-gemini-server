"""Tests for safety and analytics tools.

Tests:
- Food safety tools (grounding)
- Analytics tools (code execution)
"""
# sourcery skip: no-loop-in-tests

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def sample_meals_with_nutrition():
    """Sample meals with nutrition data."""
    now = datetime.now()
    return [
        {
            "id": "1",
            "dish_name": "Breakfast",
            "created_at": now.isoformat(),
            "nutrition": {"calories": 400, "protein_g": 20, "carbs_g": 50, "fat_g": 15},
        },
        {
            "id": "2",
            "dish_name": "Lunch",
            "created_at": (now - timedelta(hours=5)).isoformat(),
            "nutrition": {"calories": 600, "protein_g": 35, "carbs_g": 60, "fat_g": 25},
        },
        {
            "id": "3",
            "dish_name": "Dinner",
            "created_at": (now - timedelta(hours=10)).isoformat(),
            "nutrition": {"calories": 700, "protein_g": 40, "carbs_g": 70, "fat_g": 30},
        },
    ]


class TestFoodSafetyTools:
    """Tests for food safety grounded tools."""

    @pytest.fixture
    def mock_grounded_response(self):
        """Mock grounded response for safety queries (text-based, for restaurant/seasonal/claims)."""
        return {
            "text": "No current recalls found for romaine lettuce.",
            "sources": [
                {"title": "FDA Recalls", "url": "https://fda.gov/recalls"},
            ],
        }

    @pytest.fixture
    def mock_json_grounded_response(self):
        """Mock JSON grounded response for structured safety queries (recalls, allergens, interactions)."""
        return {
            "data": {
                "recall_info": "No current recalls found.",
                "has_active_recall": False,
            },
            "sources": [
                {"title": "FDA Recalls", "url": "https://fda.gov/recalls"},
            ],
        }

    @pytest.mark.asyncio
    async def test_check_food_recalls_returns_sources(self, mock_json_grounded_response):
        """check_food_recalls should return grounded info with sources."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(return_value=mock_json_grounded_response)

            from fcp.tools.safety import check_food_recalls

            result = await check_food_recalls("romaine lettuce")

            # check_food_recalls returns: food_item, recall_info, has_active_recall, sources, checked_at
            assert "food_item" in result
            assert "recall_info" in result
            assert "has_active_recall" in result
            assert "sources" in result
            assert result["food_item"] == "romaine lettuce"
            assert result["has_active_recall"] is False

    @pytest.mark.asyncio
    async def test_check_allergen_alerts_handles_food_with_common_allergens(self):
        """check_allergen_alerts should find allergen info for food items."""
        mock_response = {
            "data": {
                "allergen_alerts": "No allergen alerts found.",
                "has_alert": False,
            },
            "sources": [],
        }
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(return_value=mock_response)

            from fcp.tools.safety import check_allergen_alerts

            # Function takes only food_name, searches for allergen alerts
            result = await check_allergen_alerts(food_name="pad thai")

            assert result is not None
            assert "food_item" in result
            assert "has_alert" in result

    @pytest.mark.asyncio
    async def test_check_allergen_alerts_with_specific_allergens(self):
        """check_allergen_alerts should search for specific allergens when provided."""
        mock_response = {
            "data": {
                "allergen_alerts": "No allergen alerts found for specified allergens.",
                "has_alert": False,
            },
            "sources": [],
        }
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(return_value=mock_response)

            from fcp.tools.safety import check_allergen_alerts

            result = await check_allergen_alerts(
                food_name="chocolate cake",
                allergens=["peanuts", "tree nuts", "milk"],
            )

            assert result is not None
            assert result["food_item"] == "chocolate cake"
            assert result["allergens_checked"] == ["peanuts", "tree nuts", "milk"]
            # Verify the prompt included the allergens
            call_args = mock_gemini.generate_json_with_grounding.call_args[0][0]
            assert "peanuts" in call_args
            assert "tree nuts" in call_args
            assert "milk" in call_args

    @pytest.mark.asyncio
    async def test_get_restaurant_safety_info_includes_location(self, mock_grounded_response):
        """get_restaurant_safety_info should use location context."""
        mock_grounded_response["text"] = "Restaurant has A health rating"

        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_with_grounding = AsyncMock(return_value=mock_grounded_response)

            from fcp.tools.safety import get_restaurant_safety_info

            result = await get_restaurant_safety_info(
                restaurant_name="Thai Palace",
                location="Seattle, WA",
            )

            assert result is not None
            assert "sources" in result

    @pytest.mark.asyncio
    async def test_check_drug_food_interactions(self):
        """check_drug_food_interactions should warn about interactions."""
        mock_response = {
            "data": {
                "interaction_info": "Grapefruit can interact with statins.",
                "has_interaction": True,
            },
            "sources": [{"title": "NIH", "url": "https://nih.gov"}],
        }

        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(return_value=mock_response)

            from fcp.tools.safety import check_drug_food_interactions

            # Function takes food_name and medication (singular)
            result = await check_drug_food_interactions(food_name="Grapefruit", medications=["Statins"])

            assert result is not None
            assert "food" in result
            assert "medications" in result
            assert result["has_interaction"] is True

    @pytest.mark.asyncio
    async def test_verify_nutrition_claim(self, mock_grounded_response):
        """verify_nutrition_claim should fact-check claims."""
        mock_grounded_response["text"] = "Claim is partially true. Avocados have moderate protein."

        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_with_grounding = AsyncMock(return_value=mock_grounded_response)

            from fcp.tools.safety import verify_nutrition_claim

            result = await verify_nutrition_claim(
                claim="Avocados are high in protein",
                food_name="avocado",
            )

            assert result is not None


class TestAnalyticsTools:
    """Tests for analytics tools with code execution."""

    @pytest.fixture
    def mock_code_execution_response(self):
        """Mock code execution response.

        Must match the structure returned by gemini.generate_with_code_execution():
        - text: The response text
        - code: The executed Python code
        - execution_result: The output from code execution
        """
        return {
            "text": "Analysis complete",
            "code": "total = sum(calories)",
            "execution_result": "1700",
        }

    @pytest.mark.asyncio
    async def test_calculate_nutrition_stats_returns_metrics(
        self, sample_meals_with_nutrition, mock_code_execution_response
    ):
        """calculate_nutrition_stats should return computed metrics."""
        with patch("fcp.tools.analytics.gemini") as mock_gemini:
            mock_gemini.generate_with_code_execution = AsyncMock(return_value=mock_code_execution_response)

            from fcp.tools.analytics import calculate_nutrition_stats

            result = await calculate_nutrition_stats(sample_meals_with_nutrition)

            assert result is not None

    @pytest.mark.asyncio
    async def test_analyze_eating_patterns(self, sample_meals_with_nutrition, mock_code_execution_response):
        """analyze_eating_patterns should identify patterns."""
        # No need to modify mock - structure is already correct

        with patch("fcp.tools.analytics.gemini") as mock_gemini:
            mock_gemini.generate_with_code_execution = AsyncMock(return_value=mock_code_execution_response)

            from fcp.tools.analytics import analyze_eating_patterns

            result = await analyze_eating_patterns(sample_meals_with_nutrition)

            assert result is not None

    @pytest.mark.asyncio
    async def test_calculate_trend_report(self, sample_meals_with_nutrition, mock_code_execution_response):
        """calculate_trend_report should show trends."""
        # No need to modify mock - structure is already correct

        with patch("fcp.tools.analytics.gemini") as mock_gemini:
            mock_gemini.generate_with_code_execution = AsyncMock(return_value=mock_code_execution_response)

            from fcp.tools.analytics import calculate_trend_report

            result = await calculate_trend_report(sample_meals_with_nutrition)

            assert result is not None

    @pytest.mark.asyncio
    async def test_compare_periods_compares_two_periods(self, mock_code_execution_response):
        """compare_periods should compare two sets of food logs."""
        with patch("fcp.tools.analytics.gemini") as mock_gemini:
            mock_gemini.generate_with_code_execution = AsyncMock(return_value=mock_code_execution_response)

            from fcp.tools.analytics import compare_periods

            # Function takes period1_logs, period2_logs, and optional names
            result = await compare_periods(
                period1_logs=[{"id": "1", "dish_name": "Salad"}],
                period2_logs=[{"id": "2", "dish_name": "Pizza"}],
                period1_name="Week 1",
                period2_name="Week 2",
            )

            assert result is not None
            assert "period1" in result
            assert "period2" in result

    @pytest.mark.asyncio
    async def test_generate_nutrition_report_comprehensive(
        self, sample_meals_with_nutrition, mock_code_execution_response
    ):
        """generate_nutrition_report should create comprehensive report."""
        # No need to modify mock - structure is already correct

        with patch("fcp.tools.analytics.gemini") as mock_gemini:
            mock_gemini.generate_with_code_execution = AsyncMock(return_value=mock_code_execution_response)

            from fcp.tools.analytics import generate_nutrition_report

            result = await generate_nutrition_report(sample_meals_with_nutrition)

            assert result is not None


class TestAnalyticsEdgeCases:
    """Edge case tests for analytics."""

    @pytest.mark.asyncio
    async def test_empty_meals_list_handled(self):
        """Analytics should handle empty meal lists gracefully."""
        with patch("fcp.tools.analytics.gemini") as mock_gemini:
            mock_gemini.generate_with_code_execution = AsyncMock(
                return_value={
                    "text": "No data available",
                    "code": "# No data to analyze",
                    "execution_result": None,
                }
            )

            from fcp.tools.analytics import calculate_nutrition_stats

            result = await calculate_nutrition_stats([])

            # Should not raise, return empty or default result
            assert result is not None
            assert "analysis" in result

    @pytest.mark.asyncio
    async def test_missing_nutrition_data_handled(self):
        """Analytics should handle meals without nutrition data."""
        meals_without_nutrition = [
            {"id": "1", "dish_name": "Mystery Meal"},
            {"id": "2", "dish_name": "Another Meal", "nutrition": None},
        ]

        with patch("fcp.tools.analytics.gemini") as mock_gemini:
            mock_gemini.generate_with_code_execution = AsyncMock(
                return_value={
                    "text": "Limited data - some meals missing nutrition",
                    "code": "# Handling incomplete data",
                    "execution_result": None,
                }
            )

            from fcp.tools.analytics import calculate_nutrition_stats

            result = await calculate_nutrition_stats(meals_without_nutrition)

            assert result is not None
            assert "analysis" in result


class TestDetectActiveRecall:
    """Tests for _detect_active_recall function."""

    def test_no_recall_phrases_return_false(self):
        """Should return False when text indicates no recall."""
        from fcp.tools.safety import _detect_active_recall

        no_recall_texts = [
            "No active recalls found for romaine lettuce.",
            "There are no current recalls for this product.",
            "No recalls found for eggs in the past 30 days.",
            "This product is not currently under recall.",
            "No ongoing recalls were identified.",
            "Couldn't find any recalls for ground beef.",
            "No known recalls affect this food item.",
        ]

        for text in no_recall_texts:
            assert _detect_active_recall(text) is False, f"Failed for: {text}"

    def test_active_recall_phrases_return_true(self):
        """Should return True when text indicates active recall."""
        from fcp.tools.safety import _detect_active_recall

        active_recall_texts = [
            "Product has been recalled due to salmonella contamination.",
            "A voluntary recall was issued on January 10, 2026.",
            "FDA announced a recall for this product.",
            "Mandatory recall in effect for affected lots.",
            "Current recall affects products with lot numbers X-Y-Z.",
            "Active recall: Do not consume if you have this product.",
        ]

        for text in active_recall_texts:
            assert _detect_active_recall(text) is True, f"Failed for: {text}"

    def test_no_recall_word_returns_false(self):
        """Should return False if 'recall' is not in text."""
        from fcp.tools.safety import _detect_active_recall

        texts_without_recall = [
            "Product appears safe for consumption.",
            "No safety issues identified.",
            "This food item is widely available in stores.",
        ]

        for text in texts_without_recall:
            assert _detect_active_recall(text) is False, f"Failed for: {text}"

    def test_ambiguous_recall_mention_returns_true(self):
        """Should be cautious and return True for ambiguous mentions."""
        from fcp.tools.safety import _detect_active_recall

        # If recall is mentioned but not explicitly "no recall", be cautious
        assert _detect_active_recall("Check the FDA recall page for updates.") is True
        assert _detect_active_recall("Recall information is pending.") is True

    def test_case_insensitive(self):
        """Should handle case variations."""
        from fcp.tools.safety import _detect_active_recall

        assert _detect_active_recall("NO ACTIVE RECALLS found.") is False
        assert _detect_active_recall("VOLUNTARY RECALL issued.") is True


class TestCheckFoodRecallsWithFlag:
    """Tests for check_food_recalls with has_active_recall field from structured JSON."""

    @pytest.mark.asyncio
    async def test_returns_has_active_recall_false_for_no_recalls(self):
        """Should include has_active_recall=False from structured JSON response."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "recall_info": "No current recalls found for apples.",
                        "has_active_recall": False,
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_food_recalls

            result = await check_food_recalls("apples")

            assert "has_active_recall" in result
            assert result["has_active_recall"] is False

    @pytest.mark.asyncio
    async def test_returns_has_active_recall_true_for_active_recalls(self):
        """Should include has_active_recall=True from structured JSON response."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "recall_info": "URGENT: Product has been recalled due to listeria.",
                        "has_active_recall": True,
                    },
                    "sources": [{"title": "FDA", "url": "https://fda.gov"}],
                }
            )

            from fcp.tools.safety import check_food_recalls

            result = await check_food_recalls("spinach")

            assert "has_active_recall" in result
            assert result["has_active_recall"] is True

    @pytest.mark.asyncio
    async def test_defaults_to_false_when_field_missing(self):
        """Should default to False when has_active_recall field missing from response."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "recall_info": "Some recall info without boolean field.",
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_food_recalls

            result = await check_food_recalls("eggs")

            assert "has_active_recall" in result
            assert result["has_active_recall"] is False

    @pytest.mark.asyncio
    async def test_defaults_text_field_to_empty_string(self):
        """Should default recall_info to empty string when missing from response."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "has_active_recall": False,
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_food_recalls

            result = await check_food_recalls("eggs")

            assert "recall_info" in result
            assert result["recall_info"] == ""

    @pytest.mark.asyncio
    async def test_logs_warning_when_boolean_field_missing(self, caplog):
        """Should log warning when has_active_recall field is missing."""
        import logging

        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {"recall_info": "Some info"},
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_food_recalls

            with caplog.at_level(logging.WARNING, logger="fcp.tools.safety"):
                await check_food_recalls("eggs")

            assert "missing 'has_active_recall' field" in caplog.text
            assert "defaulting to False" in caplog.text


class TestDetectInteraction:
    """Tests for _detect_interaction function."""

    def test_no_interaction_phrases_return_false(self):
        """Should return False when text indicates no interaction."""
        from fcp.tools.safety import _detect_interaction

        no_interaction_texts = [
            "No known interactions between grapefruit and acetaminophen.",
            "There are no significant interactions between these.",
            "This food is generally safe to consume with your medications.",
            "No documented interactions were found.",
            "No evidence of interaction between spinach and aspirin.",
            "Safe to consume with most medications.",
        ]

        for text in no_interaction_texts:
            assert _detect_interaction(text) is False, f"Failed for: {text}"

    def test_interaction_phrases_return_true(self):
        """Should return True when text indicates potential interaction."""
        from fcp.tools.safety import _detect_interaction

        interaction_texts = [
            "Grapefruit may interact with statins.",
            "You should avoid consuming alcohol with this medication.",
            "Spinach can interfere with warfarin absorption.",
            "This food may affect the efficacy of your medication.",
            "Exercise caution: potential interaction with blood thinners.",
            "Consult your doctor before consuming grapefruit with this medication.",
            "Grapefruit can increase the effect of certain medications.",
            "This food may inhibit the metabolism of your drug.",
        ]

        for text in interaction_texts:
            assert _detect_interaction(text) is True, f"Failed for: {text}"

    def test_case_insensitive(self):
        """Should handle case variations."""
        from fcp.tools.safety import _detect_interaction

        assert _detect_interaction("NO KNOWN INTERACTIONS found.") is False
        assert _detect_interaction("MAY INTERACT with blood thinners.") is True

    def test_neutral_text_returns_false(self):
        """Should return False for text that doesn't match any known phrases."""
        from fcp.tools.safety import _detect_interaction

        # Text that doesn't contain any interaction keywords
        neutral_texts = [
            "The food is delicious.",
            "This meal contains vitamins and minerals.",
            "Enjoy your healthy breakfast.",
            "A balanced diet is important.",
        ]

        for text in neutral_texts:
            assert _detect_interaction(text) is False, f"Failed for: {text}"

    def test_logs_when_default_path_taken(self, caplog):
        """Should log a debug message when no phrases match (default path)."""
        import logging

        from fcp.tools.safety import _detect_interaction

        with caplog.at_level(logging.DEBUG, logger="fcp.tools.safety"):
            result = _detect_interaction("This is just a regular food description.")

        assert result is False
        assert "Interaction detection defaulted to False" in caplog.text
        assert "no matching phrases" in caplog.text

    def test_no_interaction_phrases_take_precedence(self):
        """No-interaction phrases should take precedence when both types present.

        This ensures explicit negations like 'no evidence of interaction between X'
        return False even though 'interaction between' appears in the text.
        """
        from fcp.tools.safety import _detect_interaction

        # Text with both no-interaction and interaction phrases
        # The no-interaction phrase should take precedence
        mixed_texts = [
            # Contains "no known interaction" - should return False
            "There is no known interaction, but consult your doctor before consuming.",
            # Contains "generally safe" - should return False
            "Generally safe, but may interact with certain medications.",
            # Contains "no significant interaction" - should return False
            "This may interact with your medication. However, no significant interaction was found in studies.",
            # Contains "no documented interaction" - should return False
            "Use caution when combining. No documented interaction in most cases.",
            # Contains "no evidence of interaction" which includes "interaction between"
            "No evidence of interaction between spinach and aspirin.",
        ]

        for text in mixed_texts:
            assert _detect_interaction(text) is False, f"Failed for: {text}"

    def test_negated_interaction_phrases_return_false(self):
        """Should return False when interaction phrases are preceded by negation patterns.

        This handles cases like 'does not inhibit' where 'inhibit' is an interaction
        phrase but is negated by 'does not'.
        """
        from fcp.tools.safety import _detect_interaction

        negated_texts = [
            # "does not" negation
            "Spinach does not inhibit the absorption of this medication.",
            "This food does not interfere with the drug's effectiveness.",
            "Grapefruit does not affect the absorption of aspirin.",
            # "doesn't" contraction
            "The herb doesn't potentiate the effects of the medication.",
            "This supplement doesn't inhibit drug metabolism.",
            # "will not" / "won't"
            "The food will not affect the efficacy of the treatment.",
            "This won't interfere with your medication.",
            # "cannot" / "can't"
            "Spinach cannot inhibit warfarin at normal dietary amounts.",
            "This food can't affect the absorption significantly.",
            # "no evidence" pattern
            "No evidence it will increase the effect of this drug.",
            "No proof that it can inhibit the medication's action.",
            # "unlikely to"
            "Unlikely to inhibit the drug's metabolism.",
            "The compound is unlikely to interfere with absorption.",
            # "not expected to" / "not known to"
            "This food is not expected to potentiate the drug's effects.",
            "Carrots are not known to inhibit any medications.",
        ]

        for text in negated_texts:
            assert _detect_interaction(text) is False, f"Failed for: {text}"

    def test_non_negated_interaction_phrases_still_detected(self):
        """Should still detect interactions when phrases are NOT negated."""
        from fcp.tools.safety import _detect_interaction

        # These should still return True - no negation present
        non_negated_texts = [
            "This medication may inhibit the absorption of iron.",
            "Grapefruit can interfere with statins.",
            "The herb can potentiate blood thinners.",
            "It will affect the efficacy of the drug.",
        ]

        for text in non_negated_texts:
            assert _detect_interaction(text) is True, f"Failed for: {text}"


class TestIsPhraseNegated:
    """Tests for _is_phrase_negated helper function."""

    def test_detects_does_not_negation(self):
        """Should detect 'does not' preceding a phrase."""
        from fcp.tools.safety import _is_phrase_negated

        text = "spinach does not inhibit the medication"
        assert _is_phrase_negated(text, "inhibit", text.find("inhibit")) is True

    def test_detects_doesnt_negation(self):
        """Should detect contraction 'doesn't' preceding a phrase."""
        from fcp.tools.safety import _is_phrase_negated

        text = "this food doesn't interfere with drugs"
        assert _is_phrase_negated(text, "interfere with", text.find("interfere with")) is True

    def test_detects_no_evidence_negation(self):
        """Should detect 'no evidence' preceding a phrase."""
        from fcp.tools.safety import _is_phrase_negated

        text = "there is no evidence it will increase the effect"
        assert _is_phrase_negated(text, "increase the effect", text.find("increase the effect")) is True

    def test_detects_unlikely_to_negation(self):
        """Should detect 'unlikely to' preceding a phrase."""
        from fcp.tools.safety import _is_phrase_negated

        text = "the compound is unlikely to inhibit metabolism"
        assert _is_phrase_negated(text, "inhibit", text.find("inhibit")) is True

    def test_returns_false_when_no_negation(self):
        """Should return False when phrase is not preceded by negation."""
        from fcp.tools.safety import _is_phrase_negated

        text = "this medication can inhibit iron absorption"
        assert _is_phrase_negated(text, "inhibit", text.find("inhibit")) is False

    def test_handles_phrase_at_start(self):
        """Should handle phrase appearing at start of text."""
        from fcp.tools.safety import _is_phrase_negated

        text = "inhibit the medication's effect"
        assert _is_phrase_negated(text, "inhibit", 0) is False

    def test_only_checks_within_lookback_window(self):
        """Should only check within the 40-char lookback window."""
        from fcp.tools.safety import _is_phrase_negated

        # "does not" appears more than 40 chars before "inhibit"
        # so it should not be detected as a negation
        text = "this drug does not cause any side effects at all and it can inhibit enzymes"
        # The text before "inhibit" is "...effects at all and it can " which doesn't contain negation
        assert _is_phrase_negated(text, "inhibit", text.find("inhibit")) is False

    def test_detects_negation_within_lookback_window(self):
        """Should detect negation within the 40-char lookback window."""
        from fcp.tools.safety import _is_phrase_negated

        # "does not" appears within 40 chars before "inhibit"
        text = "this food does not significantly inhibit the medication"
        assert _is_phrase_negated(text, "inhibit", text.find("inhibit")) is True


class TestDetectAllergenAlert:
    """Tests for _detect_allergen_alert function."""

    def test_no_alert_phrases_return_false(self):
        """Should return False when text indicates no allergen alert."""
        from fcp.tools.safety import _detect_allergen_alert

        no_alert_texts = [
            "No allergen alerts found for this product.",
            "Product is properly labeled with all allergens.",
            "No undeclared allergens were identified.",
            "This product is safe for those with peanut allergies.",
            "No mislabeling issues found.",
            "No cross-contamination concerns identified.",
        ]

        for text in no_alert_texts:
            assert _detect_allergen_alert(text) is False, f"Failed for: {text}"

    def test_alert_phrases_return_true(self):
        """Should return True when text indicates allergen alert."""
        from fcp.tools.safety import _detect_allergen_alert

        alert_texts = [
            "WARNING: Undeclared peanuts in chocolate bar.",
            "Product was mislabeled and contains tree nuts.",
            "Cross-contamination risk with milk products.",
            "Allergen alert: product may contain traces of soy.",
            "Product has been recalled due to undeclared eggs.",
            "Do not consume if you have a wheat allergy.",
            "Sesame not declared on label despite being present.",
        ]

        for text in alert_texts:
            assert _detect_allergen_alert(text) is True, f"Failed for: {text}"

    def test_case_insensitive(self):
        """Should handle case variations."""
        from fcp.tools.safety import _detect_allergen_alert

        assert _detect_allergen_alert("NO ALLERGEN ALERTS found.") is False
        assert _detect_allergen_alert("UNDECLARED PEANUTS in product.") is True

    def test_neutral_text_returns_false(self):
        """Should return False for text that doesn't match any known phrases."""
        from fcp.tools.safety import _detect_allergen_alert

        # Text that doesn't contain any allergen keywords
        neutral_texts = [
            "This is a tasty meal.",
            "The product is fresh and nutritious.",
            "Enjoy your healthy snack.",
            "A wonderful recipe for the whole family.",
        ]

        for text in neutral_texts:
            assert _detect_allergen_alert(text) is False, f"Failed for: {text}"

    def test_logs_when_default_path_taken(self, caplog):
        """Should log a debug message when no phrases match (default path)."""
        import logging

        from fcp.tools.safety import _detect_allergen_alert

        with caplog.at_level(logging.DEBUG, logger="fcp.tools.safety"):
            result = _detect_allergen_alert("This is just a regular food description.")

        assert result is False
        assert "Allergen detection defaulted to False" in caplog.text
        assert "no matching phrases" in caplog.text

    def test_no_alert_phrases_take_precedence(self):
        """No-alert phrases should take precedence when both types present.

        This ensures explicit negations like 'no allergen alert' return False
        even though 'alert' appears in the text.
        """
        from fcp.tools.safety import _detect_allergen_alert

        # Text with both no-alert and alert phrases
        # The no-alert phrase should take precedence
        mixed_texts = [
            # Contains "no allergen alert" - should return False
            "No allergen alerts found, but may contain traces of nuts.",
            # Contains "properly labeled" - should return False
            "Product is properly labeled. Cross-contamination risk exists.",
            # Contains "no issues found" - should return False
            "Undeclared allergen found. No issues found in other batches.",
            # Contains "no known allergen" - should return False
            "Allergen warning issued. No known allergen in this specific lot.",
        ]

        for text in mixed_texts:
            assert _detect_allergen_alert(text) is False, f"Failed for: {text}"


class TestCheckAllergenAlertsWithFlag:
    """Tests for check_allergen_alerts with has_alert field from structured JSON."""

    @pytest.mark.asyncio
    async def test_returns_has_alert_false_for_no_alerts(self):
        """Should include has_alert=False from structured JSON response."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "allergen_alerts": "No allergen alerts found for chocolate chip cookies.",
                        "has_alert": False,
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_allergen_alerts

            result = await check_allergen_alerts("chocolate chip cookies", ["peanuts"])

            assert "has_alert" in result
            assert result["has_alert"] is False

    @pytest.mark.asyncio
    async def test_returns_has_alert_true_for_active_alerts(self):
        """Should include has_alert=True from structured JSON response."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "allergen_alerts": "WARNING: Undeclared peanuts found in this product.",
                        "has_alert": True,
                    },
                    "sources": [{"title": "FDA", "url": "https://fda.gov"}],
                }
            )

            from fcp.tools.safety import check_allergen_alerts

            result = await check_allergen_alerts("energy bar", ["peanuts"])

            assert "has_alert" in result
            assert result["has_alert"] is True

    @pytest.mark.asyncio
    async def test_defaults_to_false_when_field_missing(self):
        """Should default to False when has_alert field missing from response."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "allergen_alerts": "Some allergen info without boolean field.",
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_allergen_alerts

            result = await check_allergen_alerts("cookies", ["nuts"])

            assert "has_alert" in result
            assert result["has_alert"] is False

    @pytest.mark.asyncio
    async def test_defaults_text_field_to_empty_string(self):
        """Should default allergen_alerts to empty string when missing from response."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "has_alert": False,
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_allergen_alerts

            result = await check_allergen_alerts("cookies", ["nuts"])

            assert "allergen_alerts" in result
            assert result["allergen_alerts"] == ""

    @pytest.mark.asyncio
    async def test_logs_warning_when_boolean_field_missing(self, caplog):
        """Should log warning when has_alert field is missing."""
        import logging

        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {"allergen_alerts": "Some info"},
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_allergen_alerts

            with caplog.at_level(logging.WARNING, logger="fcp.tools.safety"):
                await check_allergen_alerts("cookies", ["nuts"])

            assert "missing 'has_alert' field" in caplog.text
            assert "defaulting to False" in caplog.text


class TestCheckDrugInteractionsWithFlag:
    """Tests for check_drug_food_interactions with has_interaction field from structured JSON."""

    @pytest.mark.asyncio
    async def test_returns_has_interaction_false_for_no_interactions(self):
        """Should include has_interaction=False from structured JSON response."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "interaction_info": "No known interactions between carrots and ibuprofen.",
                        "has_interaction": False,
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_drug_food_interactions

            result = await check_drug_food_interactions("carrots", ["ibuprofen"])

            assert "has_interaction" in result
            assert result["has_interaction"] is False

    @pytest.mark.asyncio
    async def test_returns_has_interaction_true_for_interactions(self):
        """Should include has_interaction=True from structured JSON response."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "interaction_info": "Grapefruit may interact with statins.",
                        "has_interaction": True,
                    },
                    "sources": [{"title": "NIH", "url": "https://nih.gov"}],
                }
            )

            from fcp.tools.safety import check_drug_food_interactions

            result = await check_drug_food_interactions("grapefruit", ["atorvastatin"])

            assert "has_interaction" in result
            assert result["has_interaction"] is True

    @pytest.mark.asyncio
    async def test_defaults_to_false_when_field_missing(self):
        """Should default to False when has_interaction field missing from response."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "interaction_info": "Some interaction info without boolean field.",
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_drug_food_interactions

            result = await check_drug_food_interactions("apple", ["aspirin"])

            assert "has_interaction" in result
            assert result["has_interaction"] is False

    @pytest.mark.asyncio
    async def test_defaults_text_field_to_empty_string(self):
        """Should default interaction_info to empty string when missing from response."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "has_interaction": False,
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_drug_food_interactions

            result = await check_drug_food_interactions("apple", ["aspirin"])

            assert "interaction_info" in result
            assert result["interaction_info"] == ""

    @pytest.mark.asyncio
    async def test_logs_warning_when_boolean_field_missing(self, caplog):
        """Should log warning when has_interaction field is missing."""
        import logging

        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {"interaction_info": "Some info"},
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_drug_food_interactions

            with caplog.at_level(logging.WARNING, logger="fcp.tools.safety"):
                await check_drug_food_interactions("apple", ["aspirin"])

            assert "missing 'has_interaction' field" in caplog.text
            assert "defaulting to False" in caplog.text


class TestStructuredSafetyResponseFields:
    """Tests for new structured safety response fields (alert_type, alert_severity, etc)."""

    @pytest.mark.asyncio
    async def test_check_food_recalls_includes_structured_fields(self):
        """check_food_recalls should return alert_type, alert_severity, affected_products, recommended_action."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "recall_info": "URGENT: Product recalled due to salmonella contamination.",
                        "has_active_recall": True,
                        "alert_type": "recall",
                        "alert_severity": "critical",
                        "affected_products": ["Brand X Spinach 10oz", "Brand X Spinach 5oz"],
                        "recommended_action": "Discard product immediately and contact retailer for refund.",
                    },
                    "sources": [{"title": "FDA", "url": "https://fda.gov"}],
                }
            )

            from fcp.tools.safety import check_food_recalls

            result = await check_food_recalls("spinach")

            assert result["alert_type"] == "recall"
            assert result["alert_severity"] == "critical"
            assert result["affected_products"] == ["Brand X Spinach 10oz", "Brand X Spinach 5oz"]
            assert result["recommended_action"] == "Discard product immediately and contact retailer for refund."

    @pytest.mark.asyncio
    async def test_check_food_recalls_null_fields_when_no_recall(self):
        """check_food_recalls should return null/empty structured fields when no recall."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "recall_info": "No current recalls found.",
                        "has_active_recall": False,
                        "alert_type": None,
                        "alert_severity": None,
                        "affected_products": [],
                        "recommended_action": None,
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_food_recalls

            result = await check_food_recalls("apples")

            assert result["alert_type"] is None
            assert result["alert_severity"] is None
            assert result["affected_products"] == []
            assert result["recommended_action"] is None

    @pytest.mark.asyncio
    async def test_check_food_recalls_defaults_structured_fields(self):
        """check_food_recalls should default structured fields when missing from response."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "recall_info": "No recalls found.",
                        "has_active_recall": False,
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_food_recalls

            result = await check_food_recalls("carrots")

            assert result["alert_type"] is None
            assert result["alert_severity"] is None
            assert result["affected_products"] == []
            assert result["recommended_action"] is None

    @pytest.mark.asyncio
    async def test_check_allergen_alerts_includes_structured_fields(self):
        """check_allergen_alerts should return alert_type, alert_severity, affected_products, recommended_action."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "allergen_alerts": "Undeclared peanuts found in chocolate bar.",
                        "has_alert": True,
                        "alert_type": "allergen",
                        "alert_severity": "critical",
                        "affected_products": ["ChocoBrand Dark Chocolate 100g"],
                        "recommended_action": "Do not consume if allergic to peanuts. Return for refund.",
                    },
                    "sources": [{"title": "FDA", "url": "https://fda.gov"}],
                }
            )

            from fcp.tools.safety import check_allergen_alerts

            result = await check_allergen_alerts("chocolate bar", ["peanuts"])

            assert result["alert_type"] == "allergen"
            assert result["alert_severity"] == "critical"
            assert result["affected_products"] == ["ChocoBrand Dark Chocolate 100g"]
            assert result["recommended_action"] == "Do not consume if allergic to peanuts. Return for refund."

    @pytest.mark.asyncio
    async def test_check_allergen_alerts_defaults_structured_fields(self):
        """check_allergen_alerts should default structured fields when missing from response."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "allergen_alerts": "No alerts found.",
                        "has_alert": False,
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_allergen_alerts

            result = await check_allergen_alerts("bread", ["gluten"])

            assert result["alert_type"] is None
            assert result["alert_severity"] is None
            assert result["affected_products"] == []
            assert result["recommended_action"] is None

    @pytest.mark.asyncio
    async def test_check_drug_interactions_includes_structured_fields(self):
        """check_drug_food_interactions should return alert_severity, affected_medications, recommended_action."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "interaction_info": "Grapefruit significantly increases statin blood levels.",
                        "has_interaction": True,
                        "alert_severity": "critical",
                        "affected_medications": ["atorvastatin", "simvastatin"],
                        "recommended_action": "Avoid grapefruit completely while taking statins.",
                    },
                    "sources": [{"title": "NIH", "url": "https://nih.gov"}],
                }
            )

            from fcp.tools.safety import check_drug_food_interactions

            result = await check_drug_food_interactions("grapefruit", ["atorvastatin", "simvastatin"])

            assert result["alert_severity"] == "critical"
            assert result["affected_medications"] == ["atorvastatin", "simvastatin"]
            assert result["recommended_action"] == "Avoid grapefruit completely while taking statins."

    @pytest.mark.asyncio
    async def test_check_drug_interactions_defaults_structured_fields(self):
        """check_drug_food_interactions should default structured fields when missing from response."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "interaction_info": "No interactions found.",
                        "has_interaction": False,
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_drug_food_interactions

            result = await check_drug_food_interactions("apple", ["aspirin"])

            assert result["alert_severity"] is None
            assert result["affected_medications"] == []
            assert result["recommended_action"] is None

    @pytest.mark.asyncio
    async def test_check_food_recalls_nonlist_structured_fields(self):
        """check_food_recalls should coerce non-list structured fields to lists."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "recall_info": "Product recalled.",
                        "has_active_recall": True,
                        # Malformed structured fields: non-list values
                        "affected_products": "SingleProduct",  # string instead of list
                        "alert_type": 123,  # wrong type
                        "alert_severity": "CRITICAL",  # wrong case
                        "recommended_action": ["action1", "action2"],  # list instead of string
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_food_recalls

            result = await check_food_recalls("apples")

            # Non-list affected_products coerced to list with single item
            assert result["affected_products"] == ["SingleProduct"]
            # Invalid alert_type (int) coerced to None
            assert result["alert_type"] is None
            # alert_severity normalized to lowercase
            assert result["alert_severity"] == "critical"
            # List recommended_action joined to string
            assert result["recommended_action"] == "action1 action2"

    @pytest.mark.asyncio
    async def test_check_allergen_alerts_nonlist_structured_fields(self):
        """check_allergen_alerts should coerce non-list structured fields to lists."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "allergen_alerts": "Undeclared allergen.",
                        "has_alert": True,
                        "affected_products": "SingleAllergenProduct",
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_allergen_alerts

            result = await check_allergen_alerts("chocolate", ["peanuts"])

            # Non-list affected_products coerced to list with single item
            assert result["affected_products"] == ["SingleAllergenProduct"]

    @pytest.mark.asyncio
    async def test_check_drug_interactions_nonlist_structured_fields(self):
        """check_drug_food_interactions should coerce non-list structured fields to lists."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "interaction_info": "Interaction found.",
                        "has_interaction": True,
                        "affected_medications": "SingleMedication",
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_drug_food_interactions

            result = await check_drug_food_interactions("grapefruit", ["warfarin"])

            # Non-list affected_medications coerced to list with single item
            assert result["affected_medications"] == ["SingleMedication"]

    @pytest.mark.asyncio
    async def test_normalize_affected_list_returns_empty_for_invalid_type(self):
        """_normalize_affected_list should return [] when value is not string/list/tuple."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "recall_info": "Recall found.",
                        "has_active_recall": True,
                        # affected_products is an int, not string/list/tuple
                        "affected_products": 12345,
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_food_recalls

            result = await check_food_recalls("test")

            # Invalid type should result in empty list
            assert result["affected_products"] == []

    @pytest.mark.asyncio
    async def test_normalize_affected_list_converts_nonstring_items_to_string(self):
        """_normalize_affected_list should convert non-string items in list to strings."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "recall_info": "Recall found.",
                        "has_active_recall": True,
                        # List contains non-string items
                        "affected_products": [123, "Product B", 456.78],
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_food_recalls

            result = await check_food_recalls("test")

            # Non-string items converted to strings
            assert result["affected_products"] == ["123", "Product B", "456.78"]

    @pytest.mark.asyncio
    async def test_normalize_affected_list_skips_empty_items(self):
        """_normalize_affected_list should skip empty/whitespace-only items."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "recall_info": "Recall found.",
                        "has_active_recall": True,
                        # List contains empty and whitespace-only items
                        "affected_products": ["Product A", "", "   ", "Product B", "\t\n"],
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_food_recalls

            result = await check_food_recalls("test")

            # Empty items should be skipped
            assert result["affected_products"] == ["Product A", "Product B"]

    @pytest.mark.asyncio
    async def test_normalize_affected_list_truncates_at_50_items(self):
        """_normalize_affected_list should truncate list at 50 items."""
        with patch("fcp.tools.safety.gemini") as mock_gemini:
            # Create list with 60 products
            products = [f"Product {i}" for i in range(60)]
            mock_gemini.generate_json_with_grounding = AsyncMock(
                return_value={
                    "data": {
                        "recall_info": "Many recalls found.",
                        "has_active_recall": True,
                        "affected_products": products,
                    },
                    "sources": [],
                }
            )

            from fcp.tools.safety import check_food_recalls

            result = await check_food_recalls("test")

            # Should be truncated to 50 items
            assert len(result["affected_products"]) == 50
            assert result["affected_products"][0] == "Product 0"
            assert result["affected_products"][49] == "Product 49"
