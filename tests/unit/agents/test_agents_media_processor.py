"""Tests for MediaProcessingAgent."""

from unittest.mock import AsyncMock, patch

import pytest


class TestMediaProcessingAgentProcessPhotoBatch:
    """Tests for process_photo_batch method."""

    @pytest.mark.asyncio
    async def test_process_photo_batch_success(self):
        """Test successful batch processing."""
        from fcp.agents.media_processor import MediaProcessingAgent

        agent = MediaProcessingAgent()

        mock_photo_result = {
            "image_url": "http://example.com/img.jpg",
            "is_food": True,
            "confidence": 0.95,
            "dish_name": "Pizza",
        }

        with patch.object(agent, "process_single_photo", new_callable=AsyncMock) as mock_process:
            mock_process.return_value = mock_photo_result

            result = await agent.process_photo_batch(
                image_urls=["http://example.com/img1.jpg", "http://example.com/img2.jpg"],
                auto_log=True,
            )

            assert result["total_processed"] == 2
            assert result["food_detected"] == 2
            assert result["non_food"] == 0
            assert result["auto_logged"] is True
            assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_process_photo_batch_mixed_results(self):
        """Test batch processing with mixed food/non-food results."""
        from fcp.agents.media_processor import MediaProcessingAgent

        agent = MediaProcessingAgent()

        with patch.object(agent, "process_single_photo", new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = [
                {"is_food": True, "confidence": 0.9},
                {"is_food": False, "confidence": 0.1},
                {"is_food": True, "confidence": 0.85},
            ]

            result = await agent.process_photo_batch(
                image_urls=["url1", "url2", "url3"],
                auto_log=False,
            )

            assert result["total_processed"] == 3
            assert result["food_detected"] == 2
            assert result["non_food"] == 1


class TestMediaProcessingAgentProcessSinglePhoto:
    """Tests for process_single_photo method."""

    @pytest.mark.asyncio
    async def test_process_single_photo_food_detected(self):
        """Test processing photo with food detected."""
        from fcp.agents.media_processor import MediaProcessingAgent

        agent = MediaProcessingAgent()

        mock_tool_result = {
            "function_calls": [
                {
                    "name": "detect_food_in_image",
                    "args": {"is_food": True, "confidence": 0.95, "food_type": "main_dish"},
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
                    "args": {"calories": 500, "protein_g": 25, "carbs_g": 60, "fat_g": 15},
                },
                {
                    "name": "extract_venue_info",
                    "args": {"venue_name": "Ichiran", "venue_type": "restaurant", "location_hint": "NYC"},
                },
            ]
        }

        with patch("fcp.agents.media_processor.gemini") as mock_gemini:
            mock_gemini.generate_with_tools = AsyncMock(return_value=mock_tool_result)

            result = await agent.process_single_photo("http://example.com/ramen.jpg")

            assert result["is_food"] is True
            assert result["confidence"] == 0.95
            assert result["dish_name"] == "Ramen"
            assert result["cuisine"] == "Japanese"
            assert result["ingredients"] == [{"name": "noodles"}, {"name": "pork"}]
            assert result["nutrition"]["calories"] == 500
            assert result["venue"]["name"] == "Ichiran"

    @pytest.mark.asyncio
    async def test_process_single_photo_not_food(self):
        """Test processing photo with no food detected."""
        from fcp.agents.media_processor import MediaProcessingAgent

        agent = MediaProcessingAgent()

        mock_tool_result = {
            "function_calls": [
                {
                    "name": "detect_food_in_image",
                    "args": {"is_food": False, "confidence": 0.1},
                },
            ]
        }

        with patch("fcp.agents.media_processor.gemini") as mock_gemini:
            mock_gemini.generate_with_tools = AsyncMock(return_value=mock_tool_result)

            result = await agent.process_single_photo("http://example.com/cat.jpg")

            assert result["is_food"] is False
            assert result["confidence"] == 0.1

    @pytest.mark.asyncio
    async def test_process_single_photo_no_venue(self):
        """Test processing photo without venue information."""
        from fcp.agents.media_processor import MediaProcessingAgent

        agent = MediaProcessingAgent()

        mock_tool_result = {
            "function_calls": [
                {
                    "name": "detect_food_in_image",
                    "args": {"is_food": True, "confidence": 0.9},
                },
                {
                    "name": "extract_venue_info",
                    "args": {},  # No venue_name
                },
            ]
        }

        with patch("fcp.agents.media_processor.gemini") as mock_gemini:
            mock_gemini.generate_with_tools = AsyncMock(return_value=mock_tool_result)

            result = await agent.process_single_photo("http://example.com/homemade.jpg")

            assert result["is_food"] is True
            assert "venue" not in result

    @pytest.mark.asyncio
    async def test_process_single_photo_empty_venue_name(self):
        """Test extract_venue_info with empty venue_name."""
        from fcp.agents.media_processor import MediaProcessingAgent

        agent = MediaProcessingAgent()

        mock_tool_result = {
            "function_calls": [
                {
                    "name": "detect_food_in_image",
                    "args": {"is_food": True, "confidence": 0.9},
                },
                {
                    "name": "extract_venue_info",
                    "args": {"venue_name": ""},
                },
            ]
        }

        with patch("fcp.agents.media_processor.gemini") as mock_gemini:
            mock_gemini.generate_with_tools = AsyncMock(return_value=mock_tool_result)

            result = await agent.process_single_photo("http://example.com/homemade.jpg")

            assert result["is_food"] is True
            assert "venue" not in result

    @pytest.mark.asyncio
    async def test_process_single_photo_unknown_tool_ignored(self):
        """Unknown tool calls should be ignored."""
        from fcp.agents.media_processor import MediaProcessingAgent

        agent = MediaProcessingAgent()

        mock_tool_result = {
            "function_calls": [
                {
                    "name": "detect_food_in_image",
                    "args": {"is_food": True, "confidence": 0.9},
                },
                {
                    "name": "unknown_tool",
                    "args": {"foo": "bar"},
                },
            ]
        }

        with patch("fcp.agents.media_processor.gemini") as mock_gemini:
            mock_gemini.generate_with_tools = AsyncMock(return_value=mock_tool_result)

            result = await agent.process_single_photo("http://example.com/homemade.jpg")

            assert result["is_food"] is True


class TestMediaProcessingAgentFilterFoodImages:
    """Tests for filter_food_images method."""

    @pytest.mark.asyncio
    async def test_filter_food_images_success(self):
        """Test filtering images for food content."""
        from fcp.agents.media_processor import MediaProcessingAgent

        agent = MediaProcessingAgent()

        mock_results = [
            {"function_calls": [{"name": "detect_food_in_image", "args": {"is_food": True, "confidence": 0.9}}]},
            {"function_calls": [{"name": "detect_food_in_image", "args": {"is_food": False, "confidence": 0.2}}]},
            {"function_calls": [{"name": "detect_food_in_image", "args": {"is_food": True, "confidence": 0.5}}]},
        ]

        with patch("fcp.agents.media_processor.gemini") as mock_gemini:
            mock_gemini.generate_with_tools = AsyncMock(side_effect=mock_results)

            result = await agent.filter_food_images(
                image_urls=["url1", "url2", "url3"],
                confidence_threshold=0.7,
            )

            assert len(result["food_images"]) == 1  # Only url1 passes 0.7 threshold
            assert len(result["non_food_images"]) == 2
            assert result["food_count"] == 1
            assert result["threshold_used"] == 0.7

    @pytest.mark.asyncio
    async def test_filter_food_images_all_food(self):
        """Test filtering when all images are food."""
        from fcp.agents.media_processor import MediaProcessingAgent

        agent = MediaProcessingAgent()

        with patch("fcp.agents.media_processor.gemini") as mock_gemini:
            mock_gemini.generate_with_tools = AsyncMock(
                return_value={
                    "function_calls": [{"name": "detect_food_in_image", "args": {"is_food": True, "confidence": 0.95}}]
                }
            )

            result = await agent.filter_food_images(
                image_urls=["url1", "url2"],
                confidence_threshold=0.5,
            )

            assert result["food_count"] == 2
            assert len(result["non_food_images"]) == 0

    @pytest.mark.asyncio
    async def test_filter_food_images_handles_empty_function_calls(self):
        """Test filtering when no function calls are returned."""
        from fcp.agents.media_processor import MediaProcessingAgent

        agent = MediaProcessingAgent()

        with patch("fcp.agents.media_processor.gemini") as mock_gemini:
            mock_gemini.generate_with_tools = AsyncMock(return_value={"function_calls": []})

            result = await agent.filter_food_images(
                image_urls=["url1"],
                confidence_threshold=0.7,
            )

            assert result["food_count"] == 0
            assert result["non_food_images"][0]["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_filter_food_images_ignores_non_detect_calls(self):
        """Test filtering when function calls do not include detect_food_in_image."""
        from fcp.agents.media_processor import MediaProcessingAgent

        agent = MediaProcessingAgent()

        with patch("fcp.agents.media_processor.gemini") as mock_gemini:
            mock_gemini.generate_with_tools = AsyncMock(
                return_value={"function_calls": [{"name": "other_call", "args": {}}]}
            )

            result = await agent.filter_food_images(
                image_urls=["url1"],
                confidence_threshold=0.7,
            )

            assert result["food_count"] == 0

    @pytest.mark.asyncio
    async def test_filter_food_photos_alias(self):
        """Test filter_food_photos delegates to filter_food_images."""
        from fcp.agents.media_processor import MediaProcessingAgent

        agent = MediaProcessingAgent()

        with patch.object(agent, "filter_food_images", new=AsyncMock(return_value={"food_images": []})) as mock_filter:
            result = await agent.filter_food_photos(image_urls=["url1"], confidence_threshold=0.5)
            assert result == {"food_images": []}
            mock_filter.assert_called_once_with(image_urls=["url1"], confidence_threshold=0.5)


class TestMediaProcessingAgentCreateFoodLogEntries:
    """Tests for create_food_log_entries method."""

    @pytest.mark.asyncio
    async def test_create_food_log_entries_success(self):
        """Test creating food log entries from images."""
        from fcp.agents.media_processor import MediaProcessingAgent

        agent = MediaProcessingAgent()

        mock_analysis = {
            "is_food": True,
            "confidence": 0.9,
            "dish_name": "Tacos",
            "cuisine": "Mexican",
            "ingredients": [{"name": "beef"}, {"name": "tortilla"}],
            "nutrition": {"calories": 350},
            "venue": {"name": "Taqueria"},
        }

        with patch.object(agent, "process_single_photo", new_callable=AsyncMock) as mock_process:
            mock_process.return_value = mock_analysis

            result = await agent.create_food_log_entries(
                image_urls=["url1"],
                default_venue="My Kitchen",
            )

            assert len(result) == 1
            entry = result[0]
            assert entry["dish_name"] == "Tacos"
            assert entry["venue"] == "Taqueria"  # Uses detected venue over default
            assert entry["status"] == "draft"

    @pytest.mark.asyncio
    async def test_create_food_log_entries_uses_default_venue(self):
        """Test using default venue when none detected."""
        from fcp.agents.media_processor import MediaProcessingAgent

        agent = MediaProcessingAgent()

        mock_analysis = {
            "is_food": True,
            "confidence": 0.9,
            "dish_name": "Pasta",
            "venue": {},  # No venue detected
        }

        with patch.object(agent, "process_single_photo", new_callable=AsyncMock) as mock_process:
            mock_process.return_value = mock_analysis

            result = await agent.create_food_log_entries(
                image_urls=["url1"],
                default_venue="Home",
            )

            assert len(result) == 1
            assert result[0]["venue"] == "Home"

    @pytest.mark.asyncio
    async def test_create_food_log_entries_skips_non_food(self):
        """Test that non-food images don't create entries."""
        from fcp.agents.media_processor import MediaProcessingAgent

        agent = MediaProcessingAgent()

        with patch.object(agent, "process_single_photo", new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {"is_food": False}

            result = await agent.create_food_log_entries(image_urls=["url1", "url2"])

            assert len(result) == 0


class TestMediaProcessingAgentAnalyzeMealSequence:
    """Tests for analyze_meal_sequence method."""

    @pytest.mark.asyncio
    async def test_analyze_meal_sequence_success(self):
        """Test analyzing a sequence of meal photos."""
        from fcp.agents.media_processor import MediaProcessingAgent

        agent = MediaProcessingAgent()

        mock_courses = [
            {
                "is_food": True,
                "image_url": "url1",
                "dish_name": "Appetizer",
                "cuisine": "Italian",
                "nutrition": {"calories": 200, "protein_g": 10, "carbs_g": 20, "fat_g": 8},
                "venue": {"name": "Restaurant"},
            },
            {
                "is_food": True,
                "image_url": "url2",
                "dish_name": "Main Course",
                "cuisine": "Italian",
                "nutrition": {"calories": 500, "protein_g": 30, "carbs_g": 50, "fat_g": 20},
            },
        ]

        with patch.object(agent, "process_single_photo", new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = mock_courses

            result = await agent.analyze_meal_sequence(image_urls=["url1", "url2"])

            assert result["is_meal"] is True
            assert result["course_count"] == 2
            assert result["total_nutrition"]["calories"] == 700
            assert result["total_nutrition"]["protein_g"] == 40
            assert "Italian" in result["cuisines"]
            assert result["venue"]["name"] == "Restaurant"

    @pytest.mark.asyncio
    async def test_analyze_meal_sequence_no_food(self):
        """Test analyzing sequence with no food detected."""
        from fcp.agents.media_processor import MediaProcessingAgent

        agent = MediaProcessingAgent()

        with patch.object(agent, "process_single_photo", new_callable=AsyncMock) as mock_process:
            mock_process.return_value = {"is_food": False}

            result = await agent.analyze_meal_sequence(image_urls=["url1"])

            assert result["is_meal"] is False
            assert "No food detected" in result["message"]

    @pytest.mark.asyncio
    async def test_analyze_meal_sequence_handles_missing_nutrition(self):
        """Test handling courses with missing nutrition data."""
        from fcp.agents.media_processor import MediaProcessingAgent

        agent = MediaProcessingAgent()

        mock_courses = [
            {"is_food": True, "dish_name": "Food", "nutrition": {}},
            {"is_food": True, "dish_name": "Food2"},  # No nutrition key at all
        ]

        with patch.object(agent, "process_single_photo", new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = mock_courses

            result = await agent.analyze_meal_sequence(image_urls=["url1", "url2"])

            assert result["is_meal"] is True
            # Should have zeros for missing values
            assert result["total_nutrition"]["calories"] == 0
