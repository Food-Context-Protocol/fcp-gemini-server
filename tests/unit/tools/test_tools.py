"""Tests for FCP tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAnalyzeMeal:
    """Tests for analyze_meal tool."""

    @pytest.mark.asyncio
    async def test_analyze_meal_success(self, mock_gemini_response):
        """Test successful meal analysis."""
        with patch("fcp.tools.analyze.gemini") as mock_gemini:
            mock_gemini.generate_json = AsyncMock(return_value=mock_gemini_response)

            from fcp.tools.analyze import analyze_meal

            result = await analyze_meal("https://example.com/food.jpg")

            assert result["dish_name"] == "Tonkotsu Ramen"
            assert result["cuisine"] == "Japanese"
            assert "pork broth" in result["ingredients"]
            assert result["nutrition"]["calories"] == 800
            assert result["spice_level"] == 2
            mock_gemini.generate_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_meal_with_defaults(self):
        """Test that missing fields get defaults."""
        with patch("fcp.tools.analyze.gemini") as mock_gemini:
            mock_gemini.generate_json = AsyncMock(return_value={})

            from fcp.tools.analyze import analyze_meal

            result = await analyze_meal("https://example.com/food.jpg")

            assert result["dish_name"] == "Unknown Dish"
            assert result["ingredients"] == []
            assert result["nutrition"] == {}
            assert result["dietary_tags"] == []
            assert result["allergens"] == []
            assert result["spice_level"] == 0

    @pytest.mark.asyncio
    async def test_analyze_meal_list_response(self):
        """Test that analyze_meal handles list response from Gemini."""
        with patch("fcp.tools.analyze.gemini") as mock_gemini:
            mock_gemini.generate_json = AsyncMock(return_value=[{"dish_name": "First Dish", "cuisine": "Italian"}])

            from fcp.tools.analyze import analyze_meal

            result = await analyze_meal("https://example.com/food.jpg")

            assert result["dish_name"] == "First Dish"
            assert result["cuisine"] == "Italian"

    @pytest.mark.asyncio
    async def test_analyze_meal_empty_list_response(self):
        """Test that analyze_meal handles empty list response."""
        with patch("fcp.tools.analyze.gemini") as mock_gemini:
            mock_gemini.generate_json = AsyncMock(return_value=[])

            from fcp.tools.analyze import analyze_meal

            result = await analyze_meal("https://example.com/food.jpg")

            assert result["dish_name"] == "Unknown Dish"
            assert result["ingredients"] == []

    @pytest.mark.asyncio
    async def test_analyze_meal_v2_success(self):
        """Test successful meal analysis with function calling (v2)."""
        mock_function_calls = {
            "function_calls": [
                {
                    "name": "identify_dish",
                    "args": {
                        "dish_name": "Sushi",
                        "cuisine": "Japanese",
                        "cooking_method": "Raw/Rice",
                        "confidence": 0.95,
                    },
                },
                {"name": "extract_nutrition", "args": {"calories": 400, "protein_g": 15}},
                {"name": "rate_spice_level", "args": {"spice_level": 1}},
            ]
        }

        with patch("fcp.tools.analyze.gemini") as mock_gemini:
            mock_gemini.generate_with_tools = AsyncMock(return_value=mock_function_calls)

            from fcp.tools.analyze import analyze_meal_v2

            result = await analyze_meal_v2("https://example.com/sushi.jpg")

            assert result["dish_name"] == "Sushi"
            assert result["cuisine"] == "Japanese"
            assert result["nutrition"]["calories"] == 400
            assert result["spice_level"] == 1
            mock_gemini.generate_with_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_meal_v2_all_function_types(self):
        """Test analyze_meal_v2 with all supported function types."""
        mock_function_calls = {
            "function_calls": [
                {
                    "name": "identify_dish",
                    "args": {
                        "dish_name": "Curry",
                        "cuisine": "Indian",
                        "cooking_method": "Simmered",
                        "confidence": 0.9,
                    },
                },
                {
                    "name": "identify_ingredients",
                    "args": {"ingredients": ["chicken", "rice", "curry spices"]},
                },
                {
                    "name": "extract_nutrition",
                    "args": {
                        "calories": 600,
                        "protein_g": 30,
                        "carbs_g": 45,
                        "fat_g": 20,
                        "fiber_g": 5,
                        "sodium_mg": 800,
                        "sugar_g": 8,
                        "serving_size": "1 bowl",
                    },
                },
                {
                    "name": "identify_allergens",
                    "args": {"allergens": ["dairy"], "warnings": ["Contains dairy products"]},
                },
                {
                    "name": "classify_dietary_tags",
                    "args": {
                        "tags": ["gluten-free"],
                        "vegetarian": False,
                        "vegan": False,
                        "gluten_free": True,
                        "dairy_free": False,
                        "keto_friendly": False,
                    },
                },
                {
                    "name": "rate_spice_level",
                    "args": {"spice_level": 4, "spice_notes": "Contains cayenne and chili"},
                },
            ]
        }

        with patch("fcp.tools.analyze.gemini") as mock_gemini:
            mock_gemini.generate_with_tools = AsyncMock(return_value=mock_function_calls)

            from fcp.tools.analyze import analyze_meal_v2

            result = await analyze_meal_v2("https://example.com/curry.jpg")

            assert result["dish_name"] == "Curry"
            assert result["ingredients"] == ["chicken", "rice", "curry spices"]
            assert result["nutrition"]["calories"] == 600
            assert result["allergens"] == ["dairy"]
            assert result["allergen_warnings"] == ["Contains dairy products"]
            assert result["dietary_tags"] == ["gluten-free"]
            assert result["dietary_flags"]["gluten_free"] is True
            assert result["spice_level"] == 4
            assert result["spice_notes"] == "Contains cayenne and chili"

    @pytest.mark.asyncio
    async def test_analyze_meal_v2_unknown_function_names(self):
        """Test analyze_meal_v2 ignores unknown function names."""
        mock_function_calls = {
            "function_calls": [
                {"name": "unknown_function", "args": {"foo": "bar"}},
                {"name": "another_unknown", "args": {"baz": 123}},
            ]
        }

        with patch("fcp.tools.analyze.gemini") as mock_gemini:
            mock_gemini.generate_with_tools = AsyncMock(return_value=mock_function_calls)

            from fcp.tools.analyze import analyze_meal_v2

            result = await analyze_meal_v2("https://example.com/test.jpg")

            # Should return defaults since no recognized functions were called
            assert result["dish_name"] == "Unknown Dish"
            assert result["ingredients"] == []
            assert result["nutrition"] == {}

    @pytest.mark.asyncio
    async def test_analyze_meal_with_thinking_success(self):
        """Test successful meal analysis with thinking."""
        mock_response = {
            "analysis": {
                "dish_name": "Complex Curry",
                "cuisine": "Indian Fusion",
                "ingredients": [{"name": "Chicken", "is_visible": True}],
                "nutrition": {"calories": 600},
                "analysis_notes": "Rich flavor profile",
            },
            "thinking": "This appears to be a complex Indian fusion dish with...",
        }

        with patch("fcp.tools.analyze.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value=mock_response)

            from fcp.tools.analyze import analyze_meal_with_thinking

            result = await analyze_meal_with_thinking("https://example.com/curry.jpg")

            assert result["dish_name"] == "Complex Curry"
            assert result["cuisine"] == "Indian Fusion"
            assert result["analysis_notes"] == "Rich flavor profile"
            assert result["thinking"] == "This appears to be a complex Indian fusion dish with..."
            mock_gemini.generate_json_with_thinking.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_meal_with_thinking_no_thinking_output(self):
        """Test meal analysis with thinking when thinking is not available."""
        mock_response = {
            "analysis": {
                "dish_name": "Simple Salad",
                "cuisine": "Mediterranean",
                "nutrition": {"calories": 200},
            },
            "thinking": None,
        }

        with patch("fcp.tools.analyze.gemini") as mock_gemini:
            mock_gemini.generate_json_with_thinking = AsyncMock(return_value=mock_response)

            from fcp.tools.analyze import analyze_meal_with_thinking

            result = await analyze_meal_with_thinking("https://example.com/salad.jpg")

            assert result["dish_name"] == "Simple Salad"
            assert result["thinking"] is None
            mock_gemini.generate_json_with_thinking.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_meal_with_agentic_vision_success(self):
        """Test Agentic Vision analysis returns expected structure."""
        mock_response = {
            "analysis": {
                "dish_name": "Sushi Platter",
                "cuisine": "Japanese",
                "ingredients": ["rice", "salmon", "tuna", "nori"],
                "nutrition": {"calories": 450, "protein_g": 28},
                "dietary_tags": ["pescatarian"],
                "allergens": ["fish", "shellfish"],
                "spice_level": 1,
                "cooking_method": "raw",
                "portion_analysis": {"item_count": 8, "estimated_weight_g": 320},
                "confidence_notes": "Counted 8 pieces clearly visible",
            },
            "code": "# Counted 8 pieces by detecting circular shapes\ncount = 8",
            "execution_result": "Detected 8 sushi pieces",
        }

        with patch("fcp.tools.analyze.gemini") as mock_gemini:
            mock_gemini.generate_json_with_agentic_vision = AsyncMock(return_value=mock_response)

            from fcp.tools.analyze import analyze_meal_with_agentic_vision

            result = await analyze_meal_with_agentic_vision("https://example.com/sushi.jpg")

            assert result["dish_name"] == "Sushi Platter"
            assert result["cuisine"] == "Japanese"
            assert result["portion_analysis"]["item_count"] == 8
            assert result["_agentic_vision"]["code_executed"] is not None
            assert "8" in result["_agentic_vision"]["execution_result"]
            mock_gemini.generate_json_with_agentic_vision.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_meal_with_agentic_vision_no_code(self):
        """Test Agentic Vision when model doesn't use code execution."""
        mock_response = {
            "analysis": {
                "dish_name": "Caesar Salad",
                "cuisine": "American",
                "ingredients": ["romaine", "parmesan", "croutons"],
            },
            "code": None,
            "execution_result": None,
        }

        with patch("fcp.tools.analyze.gemini") as mock_gemini:
            mock_gemini.generate_json_with_agentic_vision = AsyncMock(return_value=mock_response)

            from fcp.tools.analyze import analyze_meal_with_agentic_vision

            result = await analyze_meal_with_agentic_vision("https://example.com/salad.jpg")

            assert result["dish_name"] == "Caesar Salad"
            assert result["_agentic_vision"]["code_executed"] is None
            assert result["_agentic_vision"]["execution_result"] is None

    @pytest.mark.asyncio
    async def test_analyze_meal_with_agentic_vision_defaults(self):
        """Test that missing fields get proper defaults."""
        mock_response = {
            "analysis": {"dish_name": "Mystery Dish"},
            "code": None,
            "execution_result": None,
        }

        with patch("fcp.tools.analyze.gemini") as mock_gemini:
            mock_gemini.generate_json_with_agentic_vision = AsyncMock(return_value=mock_response)

            from fcp.tools.analyze import analyze_meal_with_agentic_vision

            result = await analyze_meal_with_agentic_vision("https://example.com/mystery.jpg")

            assert result["dish_name"] == "Mystery Dish"
            assert result["cuisine"] is None
            assert result["ingredients"] == []
            assert result["nutrition"] == {}
            assert result["dietary_tags"] == []
            assert result["allergens"] == []
            assert result["spice_level"] == 0
            assert result["portion_analysis"] is None
            assert "_agentic_vision" in result

    @pytest.mark.asyncio
    async def test_analyze_meal_with_agentic_vision_list_response(self):
        """Test Agentic Vision handles list response from Gemini."""
        mock_response = {
            "analysis": [{"dish_name": "First Dish", "cuisine": "Test"}],
            "code": None,
            "execution_result": None,
        }

        with patch("fcp.tools.analyze.gemini") as mock_gemini:
            mock_gemini.generate_json_with_agentic_vision = AsyncMock(return_value=mock_response)

            from fcp.tools.analyze import analyze_meal_with_agentic_vision

            result = await analyze_meal_with_agentic_vision("https://example.com/dish.jpg")

            assert result["dish_name"] == "First Dish"
            assert result["cuisine"] == "Test"

    @pytest.mark.asyncio
    async def test_analyze_meal_with_agentic_vision_empty_list_response(self):
        """Test Agentic Vision handles empty list response."""
        mock_response = {
            "analysis": [],
            "code": None,
            "execution_result": None,
        }

        with patch("fcp.tools.analyze.gemini") as mock_gemini:
            mock_gemini.generate_json_with_agentic_vision = AsyncMock(return_value=mock_response)

            from fcp.tools.analyze import analyze_meal_with_agentic_vision

            result = await analyze_meal_with_agentic_vision("https://example.com/empty.jpg")

            assert result["dish_name"] == "Unknown Dish"
            assert result["ingredients"] == []

    @pytest.mark.asyncio
    async def test_analyze_meal_with_agentic_vision_list_with_non_dict(self):
        """Test Agentic Vision handles list with non-dict first element."""
        mock_response = {
            "analysis": ["string instead of dict", {"dish_name": "Second"}],
            "code": None,
            "execution_result": None,
        }

        with patch("fcp.tools.analyze.gemini") as mock_gemini:
            mock_gemini.generate_json_with_agentic_vision = AsyncMock(return_value=mock_response)

            from fcp.tools.analyze import analyze_meal_with_agentic_vision

            result = await analyze_meal_with_agentic_vision("https://example.com/malformed.jpg")

            # Should fall back to empty dict, not crash
            assert result["dish_name"] == "Unknown Dish"
            assert result["ingredients"] == []


class TestSearchMeals:
    """Tests for search_meals tool."""

    @pytest.mark.asyncio
    async def test_search_meals_semantic(self, sample_food_logs):
        """Test semantic search returns relevant results."""
        with patch("fcp.tools.search.firestore_client") as mock_fs:
            mock_fs.get_user_logs = AsyncMock(return_value=sample_food_logs)

            with patch("fcp.tools.search.gemini") as mock_gemini:
                mock_gemini.generate_json = AsyncMock(
                    return_value={
                        "matches": [
                            {"id": "log1", "relevance": 0.95, "reason": "ramen match"},
                            {"id": "log3", "relevance": 0.7, "reason": "spicy match"},
                        ]
                    }
                )

                from fcp.tools.search import search_meals

                results = await search_meals("test_user", "spicy ramen")

                assert len(results) == 2
                assert results[0]["dish_name"] == "Tonkotsu Ramen"
                assert results[0]["relevance_score"] == 0.95

    @pytest.mark.asyncio
    async def test_search_meals_fallback_keyword(self, sample_food_logs):
        """Test fallback to keyword search when Gemini fails."""
        with patch("fcp.tools.search.firestore_client") as mock_fs:
            mock_fs.get_user_logs = AsyncMock(return_value=sample_food_logs)

            with patch("fcp.tools.search.gemini") as mock_gemini:
                mock_gemini.generate_json = AsyncMock(side_effect=Exception("API Error"))

                from fcp.tools.search import search_meals

                results = await search_meals("test_user", "ramen")

                assert len(results) >= 1
                assert any("Ramen" in r["dish_name"] for r in results)

    @pytest.mark.asyncio
    async def test_search_meals_empty_logs(self):
        """Test search with no food logs."""
        with patch("fcp.tools.search.firestore_client") as mock_fs:
            mock_fs.get_user_logs = AsyncMock(return_value=[])

            from fcp.tools.search import search_meals

            results = await search_meals("test_user", "anything")

            assert results == []

    @pytest.mark.asyncio
    async def test_search_meals_match_id_not_in_logs(self, sample_food_logs):
        """Test semantic search when Gemini returns IDs not in the logs."""
        with patch("fcp.tools.search.firestore_client") as mock_fs:
            mock_fs.get_user_logs = AsyncMock(return_value=sample_food_logs)

            with patch("fcp.tools.search.gemini") as mock_gemini:
                # Return matches with IDs that don't exist in sample_food_logs
                mock_gemini.generate_json = AsyncMock(
                    return_value={
                        "matches": [
                            {"id": "nonexistent_id_1", "relevance": 0.9, "reason": "phantom match"},
                            {"id": "log1", "relevance": 0.8, "reason": "real match"},
                            {"id": "nonexistent_id_2", "relevance": 0.7, "reason": "another phantom"},
                            {"id": None, "relevance": 0.6, "reason": "null id match"},
                        ]
                    }
                )

                from fcp.tools.search import search_meals

                results = await search_meals("test_user", "food")

                # Only the valid match (log1) should be returned
                assert len(results) == 1
                assert results[0]["id"] == "log1"
                assert results[0]["relevance_score"] == 0.8


class TestGetTasteProfile:
    """Tests for get_taste_profile tool."""

    @pytest.mark.asyncio
    async def test_taste_profile_with_data(self, sample_food_logs):
        """Test taste profile generation."""
        with patch("fcp.tools.profile.firestore_client") as mock_fs:
            mock_fs.get_user_logs = AsyncMock(return_value=sample_food_logs)

            with patch("fcp.tools.profile.gemini") as mock_gemini:
                mock_gemini.generate_json = AsyncMock(
                    return_value={
                        "top_cuisines": [
                            {"name": "Italian", "percentage": 40},
                            {"name": "Japanese", "percentage": 20},
                        ],
                        "spice_preference": "medium",
                        "favorite_venues": [{"name": "Pizzeria Mozza", "visits": 2}],
                    }
                )

                from fcp.tools.profile import get_taste_profile

                result = await get_taste_profile("test_user", "month")

                assert result["total_meals"] == 5
                assert result["period"] == "month"
                assert "top_cuisines" in result

    @pytest.mark.asyncio
    async def test_taste_profile_empty(self):
        """Test taste profile with no data."""
        with patch("fcp.tools.profile.firestore_client") as mock_fs:
            mock_fs.get_user_logs = AsyncMock(return_value=[])

            from fcp.tools.profile import get_taste_profile

            result = await get_taste_profile("test_user")

            assert result["total_meals"] == 0
            assert "message" in result

    @pytest.mark.asyncio
    async def test_taste_profile_fallback(self, sample_food_logs):
        """Test fallback aggregation when Gemini fails."""
        with patch("fcp.tools.profile.firestore_client") as mock_fs:
            mock_fs.get_user_logs = AsyncMock(return_value=sample_food_logs)

            with patch("fcp.tools.profile.gemini") as mock_gemini:
                mock_gemini.generate_json = AsyncMock(side_effect=Exception("API Error"))

                from fcp.tools.profile import get_taste_profile

                result = await get_taste_profile("test_user")

                assert result["total_meals"] == 5
                assert len(result["top_cuisines"]) > 0
                # Italian appears twice
                italian = next((c for c in result["top_cuisines"] if c["name"] == "Italian"), None)
                assert italian is not None
                assert italian["count"] == 2

    @pytest.mark.asyncio
    async def test_taste_profile_fallback_logs_missing_fields(self):
        """Test fallback aggregation with logs missing cuisine, venue, and spice_level."""
        # Logs missing optional fields to test branch coverage in _simple_profile
        sparse_logs = [
            {"id": "log1", "dish_name": "Plain Rice"},  # No cuisine, venue, spice_level
            {"id": "log2", "dish_name": "Water", "venue_name": "Home"},  # No cuisine, no spice
            {"id": "log3", "dish_name": "Toast", "cuisine": "American"},  # No venue, no spice
            {"id": "log4", "dish_name": "Soup", "spice_level": 0},  # No cuisine, no venue
        ]

        with patch("fcp.tools.profile.firestore_client") as mock_fs:
            mock_fs.get_user_logs = AsyncMock(return_value=sparse_logs)

            with patch("fcp.tools.profile.gemini") as mock_gemini:
                mock_gemini.generate_json = AsyncMock(side_effect=Exception("API Error"))

                from fcp.tools.profile import get_taste_profile

                result = await get_taste_profile("test_user")

                assert result["total_meals"] == 4
                # Should have one cuisine entry for American
                assert len(result["top_cuisines"]) == 1
                assert result["top_cuisines"][0]["name"] == "American"
                # Should have one venue entry for Home
                assert len(result["favorite_venues"]) == 1
                assert result["favorite_venues"][0]["name"] == "Home"
                # Spice preference should be calculated from single entry with spice_level=0
                assert result["spice_preference"] == "mild"


class TestSuggestMeal:
    """Tests for suggest_meal tool."""

    @pytest.mark.asyncio
    async def test_suggest_meal_success(self, sample_food_logs):
        """Test meal suggestions."""
        with patch("fcp.tools.suggest.firestore_client") as mock_fs:
            mock_fs.get_user_logs = AsyncMock(return_value=sample_food_logs)

            with patch("fcp.tools.suggest.get_taste_profile") as mock_profile:
                mock_profile.return_value = {"top_cuisines": [{"name": "Italian"}]}

                with patch("fcp.tools.suggest.gemini") as mock_gemini:
                    mock_gemini.generate_json = AsyncMock(
                        return_value={
                            "suggestions": [
                                {
                                    "dish_name": "Carbonara",
                                    "venue": "Osteria Mozza",
                                    "type": "favorite",
                                    "reason": "You loved it last time",
                                }
                            ]
                        }
                    )

                    from fcp.tools.suggest import suggest_meal

                    results = await suggest_meal("test_user", context="dinner")

                    assert len(results) >= 1
                    assert results[0]["dish_name"] == "Carbonara"

    @pytest.mark.asyncio
    async def test_suggest_meal_excludes_recent(self, sample_food_logs):
        """Test that recent meals are excluded."""
        with patch("fcp.tools.suggest.firestore_client") as mock_fs:
            # Return only one recent log
            mock_fs.get_user_logs = AsyncMock(return_value=sample_food_logs[:1])

            with patch("fcp.tools.suggest.get_taste_profile") as mock_profile:
                mock_profile.return_value = {}

                with patch("fcp.tools.suggest.gemini") as mock_gemini:
                    mock_gemini.generate_json = AsyncMock(side_effect=Exception("API Error"))

                    from fcp.tools.suggest import suggest_meal

                    # With fallback, should exclude recent
                    results = await suggest_meal("test_user", exclude_recent_days=1)

                    # Recent dish should not be in suggestions
                    assert all(r["dish_name"] != "Tonkotsu Ramen" for r in results)


class TestCrud:
    """Tests for CRUD operations."""

    @pytest.mark.asyncio
    async def test_get_meals(self, sample_food_logs):
        """Test getting meals."""
        with patch("fcp.tools.crud.firestore_client") as mock_fs:
            mock_fs.get_user_logs = AsyncMock(return_value=sample_food_logs)

            from fcp.tools.crud import get_meals

            result = await get_meals("test_user", limit=5)

            assert len(result) == 5
            assert result[0]["dish_name"] == "Tonkotsu Ramen"

    @pytest.mark.asyncio
    async def test_get_meals_without_nutrition(self, sample_food_logs):
        """Test that nutrition is stripped when not requested."""
        with patch("fcp.tools.crud.firestore_client") as mock_fs:
            mock_fs.get_user_logs = AsyncMock(return_value=sample_food_logs)

            from fcp.tools.crud import get_meals

            result = await get_meals("test_user", include_nutrition=False)

            assert "nutrition" not in result[0]

    @pytest.mark.asyncio
    async def test_get_meals_with_nutrition(self, sample_food_logs):
        """Test that nutrition is preserved when requested."""
        with patch("fcp.tools.crud.firestore_client") as mock_fs:
            mock_fs.get_user_logs = AsyncMock(return_value=sample_food_logs)

            from fcp.tools.crud import get_meals

            result = await get_meals("test_user", include_nutrition=True)

            # Nutrition should be present when include_nutrition=True
            assert "nutrition" in result[0]
            assert result[0]["nutrition"]["calories"] == 800

    @pytest.mark.asyncio
    async def test_get_single_meal(self, sample_food_logs):
        """Test getting a single meal."""
        with patch("fcp.tools.crud.firestore_client") as mock_fs:
            mock_fs.get_log = AsyncMock(return_value=sample_food_logs[0])

            from fcp.tools.crud import get_meal

            result = await get_meal("test_user", "log1")
            assert result is not None
            assert result["dish_name"] == "Tonkotsu Ramen"

    @pytest.mark.asyncio
    async def test_get_meal_not_found(self):
        """Test getting a meal that doesn't exist."""
        with patch("fcp.tools.crud.firestore_client") as mock_fs:
            mock_fs.get_log = AsyncMock(return_value=None)

            from fcp.tools.crud import get_meal

            result = await get_meal("test_user", "nonexistent")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_meals_by_ids(self, sample_food_logs):
        """Test getting multiple meals by IDs in a batch."""
        with patch("fcp.tools.crud.firestore_client") as mock_fs:
            mock_fs.get_logs_by_ids = AsyncMock(return_value=sample_food_logs[:2])

            from fcp.tools.crud import get_meals_by_ids

            result = await get_meals_by_ids("test_user", ["log1", "log2"])

            assert len(result) == 2
            mock_fs.get_logs_by_ids.assert_called_once_with("test_user", ["log1", "log2"])

    @pytest.mark.asyncio
    async def test_get_meals_by_ids_empty_list(self):
        """Test getting meals with empty ID list returns empty."""
        from fcp.tools.crud import get_meals_by_ids

        result = await get_meals_by_ids("test_user", [])

        assert result == []

    @pytest.mark.asyncio
    async def test_add_meal(self):
        """Test adding a new meal."""
        with patch("fcp.tools.crud.firestore_client") as mock_fs:
            mock_fs.create_log = AsyncMock(return_value="new_log_123")

            from fcp.tools.crud import add_meal

            result = await add_meal(
                "test_user",
                dish_name="Burger",
                venue="Shake Shack",
                notes="Great burger",
            )

            assert result["success"] is True
            assert result["log_id"] == "new_log_123"
            mock_fs.create_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_meal(self, sample_food_logs):
        """Test updating a meal."""
        with patch("fcp.tools.crud.firestore_client") as mock_fs:
            mock_fs.get_log = AsyncMock(return_value=sample_food_logs[0])
            mock_fs.update_log = AsyncMock()

            from fcp.tools.crud import update_meal

            result = await update_meal(
                "test_user",
                "log1",
                {"dish_name": "Updated Ramen", "rating": 5},
            )

            assert result["success"] is True
            assert result["success"] is True
            assert "rating" in result["updated_fields"]

    @pytest.mark.asyncio
    async def test_update_meal_not_found(self):
        """Test updating a meal that doesn't exist."""
        with patch("fcp.tools.crud.firestore_client") as mock_fs:
            mock_fs.get_log = AsyncMock(return_value=None)

            from fcp.tools.crud import update_meal

            result = await update_meal("test_user", "nonexistent", {"dish_name": "X"})

            assert result["success"] is False
            assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_update_meal_invalid_fields(self, sample_food_logs):
        """Test that invalid fields are filtered."""
        with patch("fcp.tools.crud.firestore_client") as mock_fs:
            mock_fs.get_log = AsyncMock(return_value=sample_food_logs[0])

            from fcp.tools.crud import update_meal

            result = await update_meal(
                "test_user",
                "log1",
                {"invalid_field": "value", "another_bad": 123},
            )

            assert result["success"] is False
            assert "No valid fields" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_meal(self, sample_food_logs):
        """Test deleting a meal (soft delete)."""
        with patch("fcp.tools.crud.firestore_client") as mock_fs:
            mock_fs.get_log = AsyncMock(return_value=sample_food_logs[0])
            mock_fs.update_log = AsyncMock()

            from fcp.tools.crud import delete_meal

            result = await delete_meal("test_user", "log1")

            assert result["success"] is True
            # Verify soft delete was called
            mock_fs.update_log.assert_called_once()
            call_args = mock_fs.update_log.call_args
            assert call_args[0][2]["deleted"] is True

    @pytest.mark.asyncio
    async def test_delete_meal_not_found(self):
        """Test deleting a meal that doesn't exist."""
        with patch("fcp.tools.crud.firestore_client") as mock_fs:
            mock_fs.get_log = AsyncMock(return_value=None)

            from fcp.tools.crud import delete_meal

            result = await delete_meal("test_user", "nonexistent")

            assert result["success"] is False


class TestEnrichEntry:
    """Tests for enrich_entry tool."""

    @pytest.mark.asyncio
    async def test_enrich_entry_success(self, sample_food_logs, mock_gemini_response):
        """Test successful enrichment."""
        with patch("fcp.tools.enrich.firestore_client") as mock_fs:
            mock_fs.get_log = AsyncMock(
                return_value={
                    **sample_food_logs[0],
                    "image_path": "users/test/images/food.jpg",
                }
            )
            mock_fs.update_log = AsyncMock()

            with patch("fcp.tools.enrich.storage_client") as mock_storage:
                mock_storage.get_public_url = MagicMock(return_value="https://storage.example.com/food.jpg")

                with patch("fcp.tools.enrich.gemini") as mock_gemini:
                    mock_gemini.generate_json = AsyncMock(return_value=mock_gemini_response)

                    from fcp.tools.enrich import enrich_entry

                    result = await enrich_entry("test_user", "log1")

                    assert result["success"] is True
                    assert "enrichment" in result
                    mock_fs.update_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_enrich_entry_not_found(self):
        """Test enrichment when log doesn't exist."""
        with patch("fcp.tools.enrich.firestore_client") as mock_fs:
            mock_fs.get_log = AsyncMock(return_value=None)

            from fcp.tools.enrich import enrich_entry

            result = await enrich_entry("test_user", "nonexistent")

            assert result["success"] is False
            assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_enrich_entry_no_image(self, sample_food_logs):
        """Test enrichment when log has no image."""
        log_without_image = {**sample_food_logs[0]}
        log_without_image.pop("image_path", None)

        with patch("fcp.tools.enrich.firestore_client") as mock_fs:
            mock_fs.get_log = AsyncMock(return_value=log_without_image)

            from fcp.tools.enrich import enrich_entry

            result = await enrich_entry("test_user", "log1")

            assert result["success"] is False
            assert "No image" in result["error"]

    @pytest.mark.asyncio
    async def test_enrich_entry_gemini_failure(self, sample_food_logs):
        """Test enrichment failure handling."""
        with patch("fcp.tools.enrich.firestore_client") as mock_fs:
            mock_fs.get_log = AsyncMock(
                return_value={
                    **sample_food_logs[0],
                    "image_path": "users/test/images/food.jpg",
                }
            )
            mock_fs.update_log = AsyncMock()

            with patch("fcp.tools.enrich.storage_client") as mock_storage:
                mock_storage.get_public_url = MagicMock(return_value="https://storage.example.com/food.jpg")

                with patch("fcp.tools.enrich.gemini") as mock_gemini:
                    mock_gemini.generate_json = AsyncMock(side_effect=Exception("Gemini API Error"))

                    from fcp.tools.enrich import enrich_entry

                    result = await enrich_entry("test_user", "log1")

                    assert result["success"] is False
                    # Should mark as failed in Firestore
                    update_call = mock_fs.update_log.call_args
                    assert update_call[0][2]["processing_status"] == "failed"

    @pytest.mark.asyncio
    async def test_enrich_entry_with_inferred_context_partial(self, sample_food_logs):
        """Test enrichment with partial inferred_context (no occasion or notes_summary)."""
        gemini_response = {
            "dish_name": "Pasta",
            "ingredients": ["pasta", "sauce"],
            "nutrition": {"calories": 500},
            "inferred_context": {},  # Empty - tests both branches (no occasion, no notes_summary)
        }

        with patch("fcp.tools.enrich.firestore_client") as mock_fs:
            mock_fs.get_log = AsyncMock(
                return_value={
                    **sample_food_logs[0],
                    "image_path": "users/test/images/food.jpg",
                }
            )
            mock_fs.update_log = AsyncMock()

            with patch("fcp.tools.enrich.storage_client") as mock_storage:
                mock_storage.get_public_url = MagicMock(return_value="https://storage.example.com/food.jpg")

                with patch("fcp.tools.enrich.gemini") as mock_gemini:
                    mock_gemini.generate_json = AsyncMock(return_value=gemini_response)

                    with patch("fcp.tools.enrich.get_usda_nutrition", new_callable=AsyncMock) as mock_usda:
                        mock_usda.return_value = {}

                        from fcp.tools.enrich import enrich_entry

                        result = await enrich_entry("test_user", "log1")

                        assert result["success"] is True
                        # No occasion or ai_notes should be set
                        update_data = mock_fs.update_log.call_args[0][2]
                        assert "occasion" not in update_data
                        assert "ai_notes" not in update_data

    @pytest.mark.asyncio
    async def test_enrich_entry_with_occasion_only(self, sample_food_logs):
        """Test enrichment with inferred_context having occasion but no notes_summary."""
        gemini_response = {
            "dish_name": "Birthday Cake",
            "ingredients": ["flour", "sugar"],
            "inferred_context": {"occasion": "birthday"},  # Has occasion, no notes_summary
        }

        with patch("fcp.tools.enrich.firestore_client") as mock_fs:
            mock_fs.get_log = AsyncMock(
                return_value={
                    **sample_food_logs[0],
                    "image_path": "users/test/images/food.jpg",
                }
            )
            mock_fs.update_log = AsyncMock()

            with patch("fcp.tools.enrich.storage_client") as mock_storage:
                mock_storage.get_public_url = MagicMock(return_value="https://storage.example.com/food.jpg")

                with patch("fcp.tools.enrich.gemini") as mock_gemini:
                    mock_gemini.generate_json = AsyncMock(return_value=gemini_response)

                    with patch("fcp.tools.enrich.get_usda_nutrition", new_callable=AsyncMock) as mock_usda:
                        mock_usda.return_value = {}

                        from fcp.tools.enrich import enrich_entry

                        result = await enrich_entry("test_user", "log1")

                        assert result["success"] is True
                        update_data = mock_fs.update_log.call_args[0][2]
                        assert update_data["occasion"] == "birthday"
                        assert "ai_notes" not in update_data

    @pytest.mark.asyncio
    async def test_enrich_entry_with_notes_summary_only(self, sample_food_logs):
        """Test enrichment with inferred_context having notes_summary but no occasion."""
        gemini_response = {
            "dish_name": "Quick Lunch",
            "ingredients": ["bread", "cheese"],
            "inferred_context": {"notes_summary": "Quick weekday lunch"},  # Has notes_summary, no occasion
        }

        with patch("fcp.tools.enrich.firestore_client") as mock_fs:
            mock_fs.get_log = AsyncMock(
                return_value={
                    **sample_food_logs[0],
                    "image_path": "users/test/images/food.jpg",
                }
            )
            mock_fs.update_log = AsyncMock()

            with patch("fcp.tools.enrich.storage_client") as mock_storage:
                mock_storage.get_public_url = MagicMock(return_value="https://storage.example.com/food.jpg")

                with patch("fcp.tools.enrich.gemini") as mock_gemini:
                    mock_gemini.generate_json = AsyncMock(return_value=gemini_response)

                    with patch("fcp.tools.enrich.get_usda_nutrition", new_callable=AsyncMock) as mock_usda:
                        mock_usda.return_value = {}

                        from fcp.tools.enrich import enrich_entry

                        result = await enrich_entry("test_user", "log1")

                        assert result["success"] is True
                        update_data = mock_fs.update_log.call_args[0][2]
                        assert "occasion" not in update_data
                        assert update_data["ai_notes"] == "Quick weekday lunch"


class TestGetUsdaNutrition:
    """Tests for get_usda_nutrition function."""

    @pytest.mark.asyncio
    async def test_usda_returns_empty_foods_list(self):
        """Test USDA API returning empty foods list."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"foods": []}  # Empty foods list

        with patch.object(httpx.AsyncClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            from fcp.tools.enrich import get_usda_nutrition

            with patch("fcp.tools.enrich.httpx.AsyncClient") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client_cls.return_value = mock_client

                result = await get_usda_nutrition("nonexistent food")

                assert result == {}
