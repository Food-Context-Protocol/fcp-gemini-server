"""Tests for Pydantic AI-based Media Processing Agent."""

from unittest.mock import AsyncMock, patch

import pytest

from fcp.agents.pydantic_agents.media_processor import (
    CourseInfo,
    CreateEntriesRequest,
    FilteredImage,
    FilterImagesRequest,
    FilterImagesResult,
    FoodLogEntry,
    Ingredient,
    MealSequenceRequest,
    MealSequenceResult,
    NutritionInfo,
    PhotoAnalysis,
    PhotoBatchRequest,
    PhotoBatchResult,
    PydanticMediaProcessingAgent,
    SinglePhotoRequest,
    VenueInfo,
)


class TestInputModels:
    """Tests for input Pydantic models."""

    def test_photo_batch_request(self):
        """Should create photo batch request."""
        request = PhotoBatchRequest(
            image_urls=["https://example.com/food.jpg"],
            auto_log=True,
        )
        assert request.auto_log is True
        assert len(request.image_urls) == 1

    def test_single_photo_request(self):
        """Should create single photo request."""
        request = SinglePhotoRequest(image_url="https://example.com/food.jpg")
        assert request.image_url == "https://example.com/food.jpg"

    def test_filter_photos_request(self):
        """Should create filter photos request with defaults."""
        request = FilterImagesRequest(image_urls=["https://example.com/food.jpg"])
        assert request.confidence_threshold == 0.7

    def test_filter_photos_request_custom_threshold(self):
        """Should accept custom threshold."""
        request = FilterImagesRequest(
            image_urls=["https://example.com/food.jpg"],
            confidence_threshold=0.9,
        )
        assert request.confidence_threshold == 0.9

    def test_create_entries_request(self):
        """Should create entries request."""
        request = CreateEntriesRequest(
            image_urls=["https://example.com/food.jpg"],
            default_venue="My Restaurant",
        )
        assert request.default_venue == "My Restaurant"

    def test_meal_sequence_request(self):
        """Should create meal sequence request."""
        request = MealSequenceRequest(image_urls=["https://example.com/food1.jpg", "https://example.com/food2.jpg"])
        assert len(request.image_urls) == 2


class TestOutputModels:
    """Tests for output Pydantic models."""

    def test_nutrition_info_defaults(self):
        """Should have None defaults."""
        nutrition = NutritionInfo()
        assert nutrition.calories is None
        assert nutrition.protein_g is None

    def test_nutrition_info_with_values(self):
        """Should accept values."""
        nutrition = NutritionInfo(
            calories=500,
            protein_g=25.0,
            carbs_g=60.0,
            fat_g=15.0,
        )
        assert nutrition.calories == 500
        assert nutrition.protein_g == 25.0

    def test_venue_info_defaults(self):
        """Should have None defaults."""
        venue = VenueInfo()
        assert venue.name is None
        assert venue.type is None

    def test_ingredient_defaults(self):
        """Should have empty defaults."""
        ingredient = Ingredient()
        assert ingredient.name == ""
        assert ingredient.quantity is None

    def test_photo_analysis_defaults(self):
        """Should have sensible defaults."""
        analysis = PhotoAnalysis(image_url="https://example.com/test.jpg")
        assert analysis.is_food is False
        assert analysis.confidence == 0.0
        assert analysis.ingredients == []

    def test_photo_batch_result(self):
        """Should create batch result."""
        result = PhotoBatchResult(
            total_processed=5,
            food_detected=3,
            non_food=2,
            results=[],
            auto_logged=False,
        )
        assert result.total_processed == 5
        assert result.food_detected == 3

    def test_filtered_image(self):
        """Should create filtered image."""
        img = FilteredImage(url="https://example.com/food.jpg", confidence=0.95)
        assert img.confidence == 0.95

    def test_filter_photos_result(self):
        """Should create filter result."""
        result = FilterImagesResult(
            food_images=[],
            non_food_images=[],
            food_count=0,
            threshold_used=0.7,
        )
        assert result.threshold_used == 0.7

    def test_food_log_entry(self):
        """Should create food log entry."""
        entry = FoodLogEntry(
            dish_name="Ramen",
            image_url="https://example.com/ramen.jpg",
            cuisine="Japanese",
            status="draft",
        )
        assert entry.dish_name == "Ramen"
        assert entry.status == "draft"

    def test_course_info(self):
        """Should create course info."""
        course = CourseInfo(dish_name="Appetizer")
        assert course.dish_name == "Appetizer"

    def test_meal_sequence_result_not_meal(self):
        """Should create non-meal result."""
        result = MealSequenceResult(
            is_meal=False,
            message="No food detected",
        )
        assert result.is_meal is False
        assert result.course_count == 0

    def test_meal_sequence_result_is_meal(self):
        """Should create meal result."""
        result = MealSequenceResult(
            is_meal=True,
            course_count=3,
            courses=[CourseInfo(dish_name="Main")],
            cuisines=["Japanese"],
        )
        assert result.is_meal is True
        assert len(result.courses) == 1


class TestPydanticMediaProcessingAgent:
    """Tests for PydanticMediaProcessingAgent."""

    @pytest.fixture
    def agent(self):
        """Create agent instance."""
        return PydanticMediaProcessingAgent()

    @pytest.fixture
    def mock_food_response(self):
        """Create mock response for food detected."""
        return {
            "function_calls": [
                {
                    "name": "detect_food_in_image",
                    "args": {"is_food": True, "confidence": 0.95, "food_type": "dish"},
                },
                {
                    "name": "identify_dish",
                    "args": {"dish_name": "Ramen", "cuisine": "Japanese", "cooking_method": "boiled"},
                },
                {
                    "name": "identify_ingredients",
                    "args": {"ingredients": [{"name": "noodles"}, {"name": "pork"}]},
                },
                {
                    "name": "extract_nutrition",
                    "args": {"calories": 500, "protein_g": 25.0, "carbs_g": 60.0, "fat_g": 15.0},
                },
                {
                    "name": "extract_venue_info",
                    "args": {"venue_name": "Ramen Shop", "venue_type": "restaurant", "location_hint": "Tokyo"},
                },
            ]
        }

    @pytest.fixture
    def mock_non_food_response(self):
        """Create mock response for non-food."""
        return {
            "function_calls": [
                {
                    "name": "detect_food_in_image",
                    "args": {"is_food": False, "confidence": 0.1},
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_process_single_photo_typed_food(self, agent, mock_food_response):
        """Should process single photo detecting food."""
        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=mock_food_response,
        ):
            request = SinglePhotoRequest(image_url="https://example.com/ramen.jpg")
            result = await agent.process_single_photo_typed(request)

            assert isinstance(result, PhotoAnalysis)
            assert result.is_food is True
            assert result.confidence == 0.95
            assert result.dish_name == "Ramen"
            assert result.cuisine == "Japanese"
            assert len(result.ingredients) == 2
            assert result.nutrition.calories == 500
            assert result.venue is not None
            assert result.venue.name == "Ramen Shop"

    @pytest.mark.asyncio
    async def test_process_single_photo_typed_non_food(self, agent, mock_non_food_response):
        """Should process single photo detecting non-food."""
        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=mock_non_food_response,
        ):
            request = SinglePhotoRequest(image_url="https://example.com/cat.jpg")
            result = await agent.process_single_photo_typed(request)

            assert result.is_food is False
            assert result.confidence == 0.1
            assert result.dish_name is None

    @pytest.mark.asyncio
    async def test_process_photo_batch_typed(self, agent, mock_food_response, mock_non_food_response):
        """Should process batch of photos."""
        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            side_effect=[mock_food_response, mock_non_food_response],
        ):
            request = PhotoBatchRequest(
                image_urls=["https://example.com/food.jpg", "https://example.com/cat.jpg"],
                auto_log=True,
            )
            result = await agent.process_photo_batch_typed(request)

            assert isinstance(result, PhotoBatchResult)
            assert result.total_processed == 2
            assert result.food_detected == 1
            assert result.non_food == 1
            assert result.auto_logged is True

    @pytest.mark.asyncio
    async def test_filter_food_images_typed(self, agent):
        """Should filter food images."""
        food_response = {
            "function_calls": [{"name": "detect_food_in_image", "args": {"is_food": True, "confidence": 0.9}}]
        }
        non_food_response = {
            "function_calls": [{"name": "detect_food_in_image", "args": {"is_food": False, "confidence": 0.1}}]
        }

        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            side_effect=[food_response, non_food_response],
        ):
            request = FilterImagesRequest(
                image_urls=["https://example.com/food.jpg", "https://example.com/cat.jpg"],
                confidence_threshold=0.7,
            )
            result = await agent.filter_food_images_typed(request)

            assert isinstance(result, FilterImagesResult)
            assert result.food_count == 1
            assert len(result.food_images) == 1
            assert len(result.non_food_images) == 1
            assert result.threshold_used == 0.7

    @pytest.mark.asyncio
    async def test_filter_food_photos_typed_alias(self, agent):
        """Should delegate filter_food_photos_typed to filter_food_images_typed."""
        request = FilterImagesRequest(
            image_urls=["https://example.com/food.jpg"],
            confidence_threshold=0.6,
        )
        expected = FilterImagesResult(
            food_images=[FilteredImage(url="https://example.com/food.jpg", confidence=0.9)],
            non_food_images=[],
            food_count=1,
            threshold_used=0.6,
        )

        with patch.object(agent, "filter_food_images_typed", new=AsyncMock(return_value=expected)) as mock_filter:
            result = await agent.filter_food_photos_typed(request)

            assert result == expected
            mock_filter.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_filter_food_images_low_confidence(self, agent):
        """Should filter out low confidence food."""
        low_confidence_response = {
            "function_calls": [{"name": "detect_food_in_image", "args": {"is_food": True, "confidence": 0.5}}]
        }

        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=low_confidence_response,
        ):
            request = FilterImagesRequest(
                image_urls=["https://example.com/maybe_food.jpg"],
                confidence_threshold=0.7,
            )
            result = await agent.filter_food_images_typed(request)

            assert result.food_count == 0
            assert len(result.non_food_images) == 1

    @pytest.mark.asyncio
    async def test_create_food_log_entries_typed(self, agent, mock_food_response):
        """Should create food log entries."""
        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=mock_food_response,
        ):
            request = CreateEntriesRequest(
                image_urls=["https://example.com/ramen.jpg"],
                default_venue="Default Restaurant",
            )
            result = await agent.create_food_log_entries_typed(request)

            assert len(result) == 1
            assert result[0].dish_name == "Ramen"
            assert result[0].status == "draft"
            assert result[0].venue == "Ramen Shop"  # Uses detected venue

    @pytest.mark.asyncio
    async def test_create_food_log_entries_default_venue(self, agent):
        """Should use default venue when none detected."""
        response_no_venue = {
            "function_calls": [
                {"name": "detect_food_in_image", "args": {"is_food": True, "confidence": 0.9}},
                {"name": "identify_dish", "args": {"dish_name": "Pasta", "cuisine": "Italian"}},
            ]
        }

        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=response_no_venue,
        ):
            request = CreateEntriesRequest(
                image_urls=["https://example.com/pasta.jpg"],
                default_venue="My Kitchen",
            )
            result = await agent.create_food_log_entries_typed(request)

            assert result[0].venue == "My Kitchen"

    @pytest.mark.asyncio
    async def test_create_food_log_entries_non_food(self, agent, mock_non_food_response):
        """Should skip non-food images."""
        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=mock_non_food_response,
        ):
            request = CreateEntriesRequest(image_urls=["https://example.com/cat.jpg"])
            result = await agent.create_food_log_entries_typed(request)

            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_analyze_meal_sequence_typed(self, agent, mock_food_response):
        """Should analyze meal sequence."""
        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=mock_food_response,
        ):
            request = MealSequenceRequest(
                image_urls=["https://example.com/appetizer.jpg", "https://example.com/main.jpg"]
            )
            result = await agent.analyze_meal_sequence_typed(request)

            assert isinstance(result, MealSequenceResult)
            assert result.is_meal is True
            assert result.course_count == 2
            assert len(result.courses) == 2
            assert result.total_nutrition.calories == 1000  # 500 * 2

    @pytest.mark.asyncio
    async def test_analyze_meal_sequence_no_food(self, agent, mock_non_food_response):
        """Should handle no food in sequence."""
        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=mock_non_food_response,
        ):
            request = MealSequenceRequest(image_urls=["https://example.com/landscape.jpg"])
            result = await agent.analyze_meal_sequence_typed(request)

            assert result.is_meal is False
            assert result.message == "No food detected in images"

    # Backward compatibility tests
    @pytest.mark.asyncio
    async def test_backward_compat_process_single_photo(self, agent, mock_food_response):
        """Should work with dict interface."""
        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=mock_food_response,
        ):
            result = await agent.process_single_photo("https://example.com/ramen.jpg")

            assert isinstance(result, dict)
            assert result["is_food"] is True
            assert result["dish_name"] == "Ramen"

    @pytest.mark.asyncio
    async def test_backward_compat_process_photo_batch(self, agent, mock_food_response):
        """Should work with dict interface."""
        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=mock_food_response,
        ):
            result = await agent.process_photo_batch(
                image_urls=["https://example.com/food.jpg"],
                auto_log=True,
            )

            assert isinstance(result, dict)
            assert result["total_processed"] == 1
            assert result["auto_logged"] is True

    @pytest.mark.asyncio
    async def test_backward_compat_filter_food_photos(self, agent):
        """Should work with dict interface."""
        food_response = {
            "function_calls": [{"name": "detect_food_in_image", "args": {"is_food": True, "confidence": 0.9}}]
        }

        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=food_response,
        ):
            result = await agent.filter_food_photos(
                image_urls=["https://example.com/food.jpg"],
                confidence_threshold=0.8,
            )

            assert isinstance(result, dict)
            assert result["food_count"] == 1
            assert result["threshold_used"] == 0.8

    @pytest.mark.asyncio
    async def test_backward_compat_create_food_log_entries(self, agent, mock_food_response):
        """Should work with dict interface."""
        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=mock_food_response,
        ):
            result = await agent.create_food_log_entries(
                image_urls=["https://example.com/ramen.jpg"],
                default_venue="Restaurant",
            )

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["dish_name"] == "Ramen"

    @pytest.mark.asyncio
    async def test_backward_compat_analyze_meal_sequence_food(self, agent, mock_food_response):
        """Should work with dict interface for meal."""
        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=mock_food_response,
        ):
            result = await agent.analyze_meal_sequence(image_urls=["https://example.com/food.jpg"])

            assert isinstance(result, dict)
            assert result["is_meal"] is True

    @pytest.mark.asyncio
    async def test_backward_compat_analyze_meal_sequence_no_food(self, agent, mock_non_food_response):
        """Should work with dict interface for non-meal."""
        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=mock_non_food_response,
        ):
            result = await agent.analyze_meal_sequence(image_urls=["https://example.com/cat.jpg"])

            assert isinstance(result, dict)
            assert result["is_meal"] is False
            assert result["message"] == "No food detected in images"


class TestParseFunctionCalls:
    """Tests for _parse_function_calls helper."""

    @pytest.fixture
    def agent(self):
        return PydanticMediaProcessingAgent()

    def test_parse_empty_function_calls(self, agent):
        """Should handle empty function calls."""
        result = agent._parse_function_calls({"function_calls": []}, "https://example.com/test.jpg")
        assert result.is_food is False
        assert result.confidence == 0.0

    def test_parse_missing_function_calls(self, agent):
        """Should handle missing function calls."""
        result = agent._parse_function_calls({}, "https://example.com/test.jpg")
        assert result.is_food is False

    def test_parse_ingredients_string_format(self, agent):
        """Should handle ingredients as strings."""
        result = agent._parse_function_calls(
            {
                "function_calls": [
                    {"name": "detect_food_in_image", "args": {"is_food": True, "confidence": 0.9}},
                    {"name": "identify_ingredients", "args": {"ingredients": ["noodles", "pork"]}},
                ]
            },
            "https://example.com/test.jpg",
        )
        assert len(result.ingredients) == 2
        assert result.ingredients[0].name == "noodles"

    def test_parse_venue_without_name(self, agent):
        """Should skip venue without name."""
        result = agent._parse_function_calls(
            {
                "function_calls": [
                    {"name": "detect_food_in_image", "args": {"is_food": True}},
                    {"name": "extract_venue_info", "args": {"venue_type": "restaurant"}},
                ]
            },
            "https://example.com/test.jpg",
        )
        assert result.venue is None

    def test_parse_unrecognized_function_continues_loop(self, agent):
        """Unrecognized function names are silently skipped."""
        result = agent._parse_function_calls(
            {
                "function_calls": [
                    {"name": "unknown_function", "args": {"foo": "bar"}},
                    {"name": "detect_food_in_image", "args": {"is_food": True, "confidence": 0.8}},
                ]
            },
            "https://example.com/test.jpg",
        )
        assert result.is_food is True
        assert result.confidence == 0.8

    def test_parse_venue_then_nutrition(self, agent):
        """Should handle extract_venue_info followed by another function call in the loop."""
        result = agent._parse_function_calls(
            {
                "function_calls": [
                    {"name": "detect_food_in_image", "args": {"is_food": True, "confidence": 0.9}},
                    {"name": "extract_venue_info", "args": {"venue_name": "Cafe", "venue_type": "cafe"}},
                    {"name": "extract_nutrition", "args": {"calories": 200}},
                ]
            },
            "https://example.com/test.jpg",
        )
        assert result.venue is not None
        assert result.venue.name == "Cafe"
        assert result.nutrition.calories == 200


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.fixture
    def agent(self):
        return PydanticMediaProcessingAgent()

    @pytest.mark.asyncio
    async def test_process_single_photo_no_nutrition(self, agent):
        """Should handle response without nutrition."""
        response = {
            "function_calls": [
                {"name": "detect_food_in_image", "args": {"is_food": True, "confidence": 0.9}},
                {"name": "identify_dish", "args": {"dish_name": "Mystery Dish"}},
            ]
        }

        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await agent.process_single_photo("https://example.com/mystery.jpg")

            assert result["is_food"] is True
            assert "nutrition" not in result

    @pytest.mark.asyncio
    async def test_create_entries_unknown_dish(self, agent):
        """Should use 'Unknown Dish' when dish not identified."""
        response = {
            "function_calls": [
                {"name": "detect_food_in_image", "args": {"is_food": True, "confidence": 0.8}},
            ]
        }

        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=response,
        ):
            request = CreateEntriesRequest(image_urls=["https://example.com/food.jpg"])
            result = await agent.create_food_log_entries_typed(request)

            assert result[0].dish_name == "Unknown Dish"

    @pytest.mark.asyncio
    async def test_meal_sequence_multiple_cuisines(self, agent):
        """Should collect multiple cuisines."""
        japanese_response = {
            "function_calls": [
                {"name": "detect_food_in_image", "args": {"is_food": True, "confidence": 0.9}},
                {"name": "identify_dish", "args": {"dish_name": "Sushi", "cuisine": "Japanese"}},
                {"name": "extract_nutrition", "args": {"calories": 300}},
            ]
        }
        italian_response = {
            "function_calls": [
                {"name": "detect_food_in_image", "args": {"is_food": True, "confidence": 0.9}},
                {"name": "identify_dish", "args": {"dish_name": "Pasta", "cuisine": "Italian"}},
                {"name": "extract_nutrition", "args": {"calories": 400}},
            ]
        }

        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            side_effect=[japanese_response, italian_response],
        ):
            request = MealSequenceRequest(image_urls=["https://example.com/sushi.jpg", "https://example.com/pasta.jpg"])
            result = await agent.analyze_meal_sequence_typed(request)

            assert len(result.cuisines) == 2
            assert "Japanese" in result.cuisines
            assert "Italian" in result.cuisines
            assert result.total_nutrition.calories == 700

    @pytest.mark.asyncio
    async def test_filter_photos_no_detect_function(self, agent):
        """Should handle response without detect_food_in_image function."""
        response_no_detect = {"function_calls": [{"name": "other_function", "args": {}}]}

        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=response_no_detect,
        ):
            request = FilterImagesRequest(image_urls=["https://example.com/test.jpg"])
            result = await agent.filter_food_images_typed(request)

            assert result.food_count == 0
            assert len(result.non_food_images) == 1

    @pytest.mark.asyncio
    async def test_filter_photos_empty_function_calls(self, agent):
        """Should handle empty function_calls list."""
        response_empty = {"function_calls": []}

        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=response_empty,
        ):
            request = FilterImagesRequest(image_urls=["https://example.com/test.jpg"])
            result = await agent.filter_food_images_typed(request)

            assert result.food_count == 0

    @pytest.mark.asyncio
    async def test_backward_compat_process_single_photo_partial_response(self, agent):
        """Should handle partial response in backward compat mode."""
        response = {
            "function_calls": [
                {"name": "detect_food_in_image", "args": {"is_food": True, "confidence": 0.9, "food_type": "dish"}},
                {"name": "identify_dish", "args": {"cuisine": "Japanese"}},  # No dish_name
            ]
        }

        with patch(
            "fcp.agents.pydantic_agents.media_processor.gemini.generate_with_tools",
            new_callable=AsyncMock,
            return_value=response,
        ):
            result = await agent.process_single_photo("https://example.com/test.jpg")

            assert result["is_food"] is True
            assert result["food_type"] == "dish"
            assert result["cuisine"] == "Japanese"
            assert "dish_name" not in result  # Not set because it was None
