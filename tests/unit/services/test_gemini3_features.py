"""Tests for Gemini 3 new features integration.

This module tests the new Gemini 3 capabilities:
- Nano Banana Pro image generation
- Thought signatures for agentic workflows
- Thinking level control
- Computer Use for recipe import
- Enhanced Live API cooking assistant
- Code execution with vision for portion analysis
- Media resolution control
- Grounding + structured outputs
"""
# sourcery skip: no-loop-in-tests

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# Feature 1: Nano Banana Pro Image Generation Tests
# =============================================================================


class TestImageGenerationService:
    """Tests for Nano Banana Pro image generation."""

    def test_build_food_prompt_generates_valid_prompt(self):
        """Test that food prompt generation works correctly."""
        from fcp.services.image_generation import ImageGenerationService

        service = ImageGenerationService()
        prompt = service._build_food_prompt(
            dish_name="Tonkotsu Ramen",
            cuisine="Japanese",
            style="professional food photography",
        )

        assert "Tonkotsu Ramen" in prompt
        assert "Japanese" in prompt
        assert "professional" in prompt

    def test_generated_image_model(self):
        """Test GeneratedImage model creation."""
        from fcp.services.image_generation import (
            AspectRatio,
            GeneratedImage,
            Resolution,
        )

        image = GeneratedImage(
            image_bytes=b"fake-image-data",
            mime_type="image/png",
            aspect_ratio=AspectRatio.STANDARD,
            resolution=Resolution.HIGH,
            thought_signature="sig123",
        )

        assert image.image_bytes == b"fake-image-data"
        assert image.mime_type == "image/png"
        assert image.aspect_ratio == AspectRatio.STANDARD
        assert image.resolution == Resolution.HIGH
        assert image.thought_signature == "sig123"

    def test_generated_image_without_signature(self):
        """Test GeneratedImage model without thought signature."""
        from fcp.services.image_generation import (
            AspectRatio,
            GeneratedImage,
            Resolution,
        )

        image = GeneratedImage(
            image_bytes=b"data",
            mime_type="image/jpeg",
            aspect_ratio=AspectRatio.WIDE,
            resolution=Resolution.ULTRA,
        )

        assert image.thought_signature is None

    def test_build_food_prompt_with_cuisine(self):
        """Test prompt building includes cuisine hint."""
        from fcp.services.image_generation import ImageGenerationService

        service = ImageGenerationService()
        prompt = service._build_food_prompt(
            dish_name="Ramen",
            cuisine="Japanese",
            style="professional",
        )

        assert "Japanese" in prompt
        assert "Ramen" in prompt
        assert "professional" in prompt

    def test_build_food_prompt_without_cuisine(self):
        """Test prompt building without cuisine."""
        from fcp.services.image_generation import ImageGenerationService

        service = ImageGenerationService()
        prompt = service._build_food_prompt(
            dish_name="Salad",
            cuisine=None,
            style="casual",
        )

        assert "Salad" in prompt
        assert "casual" in prompt

    @pytest.mark.asyncio
    async def test_generate_food_image_success(self):
        """Test successful food image generation."""
        from fcp.services.image_generation import (
            AspectRatio,
            ImageGenerationService,
            Resolution,
        )

        service = ImageGenerationService()

        # Mock response with image data - use spec to prevent auto-created attributes
        mock_part = MagicMock()
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = b"fake-image-bytes"
        mock_part.inline_data.mime_type = "image/png"
        # Explicitly set thought_signature to None so Pydantic doesn't get a MagicMock
        mock_part.thought_signature = None

        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        service.client = MagicMock()
        service.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        # Patch types module to avoid ImageGenerationConfig issues
        with patch("fcp.services.image_generation.types") as mock_types:
            mock_types.GenerateContentConfig.return_value = MagicMock()

            result = await service.generate_food_image(
                dish_name="Spaghetti Carbonara",
                cuisine="Italian",
                style="professional food photography",
                aspect_ratio=AspectRatio.STANDARD,
                resolution=Resolution.HIGH,
            )

            assert result.image_bytes == b"fake-image-bytes"
            assert result.mime_type == "image/png"
            assert result.aspect_ratio == AspectRatio.STANDARD
            assert result.resolution == Resolution.HIGH

    @pytest.mark.asyncio
    async def test_generate_food_image_with_thought_signature(self):
        """Test food image generation preserves thought signature."""
        from fcp.services.image_generation import ImageGenerationService

        service = ImageGenerationService()

        mock_part = MagicMock()
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = b"image-data"
        mock_part.inline_data.mime_type = "image/jpeg"
        mock_part.thought_signature = "thought_sig_abc"

        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        service.client = MagicMock()
        service.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("fcp.services.image_generation.types") as mock_types:
            mock_types.GenerateContentConfig.return_value = MagicMock()

            result = await service.generate_food_image("Test Dish")

            assert result.image_bytes == b"image-data"
            assert result.thought_signature == "thought_sig_abc"

    @pytest.mark.asyncio
    async def test_generate_food_image_no_image_raises(self):
        """Test that ValueError is raised when no image in response."""
        from fcp.services.image_generation import ImageGenerationService

        service = ImageGenerationService()

        # Mock response without image data
        mock_part = MagicMock()
        mock_part.inline_data = None

        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        service.client = MagicMock()
        service.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("fcp.services.image_generation.types") as mock_types:
            mock_types.GenerateContentConfig.return_value = MagicMock()

            with pytest.raises(ValueError, match="No image generated"):
                await service.generate_food_image("Test Dish")

    @pytest.mark.asyncio
    async def test_generate_recipe_card_success(self):
        """Test successful recipe card generation."""
        from fcp.services.image_generation import (
            AspectRatio,
            ImageGenerationService,
            Resolution,
        )

        service = ImageGenerationService()

        mock_part = MagicMock()
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = b"recipe-card-bytes"
        mock_part.inline_data.mime_type = "image/png"

        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        service.client = MagicMock()
        service.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("fcp.services.image_generation.types") as mock_types:
            mock_types.GenerateContentConfig.return_value = MagicMock()

            result = await service.generate_recipe_card(
                recipe_name="Chocolate Cake",
                ingredients=["flour", "sugar", "cocoa", "eggs"],
                prep_time="20 min",
                cook_time="45 min",
                servings=8,
            )

            assert result.image_bytes == b"recipe-card-bytes"
            assert result.aspect_ratio == AspectRatio.INSTAGRAM  # 4:5 for Instagram-friendly cards
            assert result.resolution == Resolution.HIGH

    @pytest.mark.asyncio
    async def test_generate_recipe_card_no_image_raises(self):
        """Test recipe card raises when no image."""
        from fcp.services.image_generation import ImageGenerationService

        service = ImageGenerationService()

        mock_part = MagicMock()
        mock_part.inline_data = None

        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        service.client = MagicMock()
        service.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("fcp.services.image_generation.types") as mock_types:
            mock_types.GenerateContentConfig.return_value = MagicMock()

            with pytest.raises(ValueError, match="No recipe card generated"):
                await service.generate_recipe_card(
                    recipe_name="Test",
                    ingredients=["a", "b"],
                    prep_time="5 min",
                    cook_time="10 min",
                    servings=2,
                )

    @pytest.mark.asyncio
    async def test_generate_meal_variation_success(self):
        """Test successful meal variation generation."""
        from fcp.services.image_generation import (
            AspectRatio,
            ImageGenerationService,
            Resolution,
        )

        service = ImageGenerationService()

        mock_part = MagicMock()
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.data = b"variation-bytes"
        mock_part.inline_data.mime_type = "image/png"

        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        service.client = MagicMock()
        service.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("fcp.services.image_generation.types") as mock_types:
            mock_types.GenerateContentConfig.return_value = MagicMock()
            mock_types.Part.from_uri.return_value = MagicMock()
            mock_types.Part.return_value = MagicMock()

            result = await service.generate_meal_variation(
                original_image_url="gs://bucket/image.jpg",
                variation="Make it vegetarian",
            )

            assert result.image_bytes == b"variation-bytes"
            assert result.aspect_ratio == AspectRatio.STANDARD
            assert result.resolution == Resolution.HIGH

    @pytest.mark.asyncio
    async def test_generate_meal_variation_no_image_raises(self):
        """Test meal variation raises when no image."""
        from fcp.services.image_generation import ImageGenerationService

        service = ImageGenerationService()

        mock_part = MagicMock()
        mock_part.inline_data = None

        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        service.client = MagicMock()
        service.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch("fcp.services.image_generation.types") as mock_types:
            mock_types.GenerateContentConfig.return_value = MagicMock()
            mock_types.Part.from_uri.return_value = MagicMock()
            mock_types.Part.return_value = MagicMock()

            with pytest.raises(ValueError, match="No variation generated"):
                await service.generate_meal_variation(
                    original_image_url="gs://bucket/image.jpg",
                    variation="Test variation",
                )


class TestAspectRatioEnum:
    """Tests for AspectRatio enumeration."""

    def test_aspect_ratio_values(self):
        """Test all aspect ratio values are valid."""
        from fcp.services.image_generation import AspectRatio

        assert AspectRatio.SQUARE.value == "1:1"
        assert AspectRatio.PORTRAIT.value == "2:3"
        assert AspectRatio.LANDSCAPE.value == "3:2"
        assert AspectRatio.STANDARD.value == "4:3"
        assert AspectRatio.WIDE.value == "16:9"
        assert AspectRatio.ULTRA_WIDE.value == "21:9"
        assert AspectRatio.STORY.value == "9:16"


class TestResolutionEnum:
    """Tests for Resolution enumeration."""

    def test_resolution_values(self):
        """Test all resolution values are valid."""
        from fcp.services.image_generation import Resolution

        assert Resolution.STANDARD.value == "1K"
        assert Resolution.HIGH.value == "2K"
        assert Resolution.ULTRA.value == "4K"


# =============================================================================
# Feature 2: Thought Signatures Tests
# =============================================================================


class TestConversationState:
    """Tests for conversation state management with thought signatures."""

    def test_add_user_message(self):
        """Test adding a user message to conversation."""
        from fcp.services.conversation_state import ConversationState

        with patch("fcp.services.conversation_state.types") as mock_types:
            mock_types.Part.return_value = MagicMock()

            state = ConversationState()
            state.add_user_message("Hello, plan my meals")

            assert len(state.turns) == 1
            assert state.turns[0].role == "user"

    def test_add_model_response_with_signature(self):
        """Test adding model response preserves thought signature."""
        from fcp.services.conversation_state import ConversationState

        state = ConversationState()

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.thought_signature = "encrypted_sig_123"
        mock_part.function_call = MagicMock()
        mock_part.function_call.name = "get_pantry"
        mock_part.function_call.args = {"user_id": "123"}
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        state.add_model_response(mock_response)

        assert len(state.turns) == 1
        assert state.turns[0].role == "model"
        assert state.turns[0].thought_signature == "encrypted_sig_123"
        assert len(state.turns[0].function_calls) == 1

    def test_add_model_response_without_signature(self):
        """Test model response without thought signature."""
        from fcp.services.conversation_state import ConversationState

        state = ConversationState()

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.thought_signature = None
        mock_part.function_call = None
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        state.add_model_response(mock_response)

        assert len(state.turns) == 1
        assert state.turns[0].thought_signature is None

    def test_add_model_response_without_function_call(self):
        """Test model response without function calls."""
        from fcp.services.conversation_state import ConversationState

        state = ConversationState()

        # Part without function_call attribute
        mock_part = MagicMock(spec=["thought_signature"])
        mock_part.thought_signature = None

        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        state.add_model_response(mock_response)

        assert len(state.turns) == 1
        assert len(state.turns[0].function_calls) == 0

    def test_add_function_responses(self):
        """Test adding function execution results."""
        from fcp.services.conversation_state import ConversationState

        with patch("fcp.services.conversation_state.types") as mock_types:
            mock_types.Part.return_value = MagicMock()
            mock_types.FunctionResponse.return_value = MagicMock()

            state = ConversationState()
            state.add_function_responses(
                [
                    {"name": "get_pantry", "result": {"items": ["eggs", "milk"]}},
                ]
            )

            assert len(state.turns) == 1
            assert state.turns[0].role == "user"
            assert len(state.turns[0].function_responses) == 1

    def test_get_last_thought_signature(self):
        """Test retrieving the most recent thought signature."""
        from fcp.services.conversation_state import ConversationState

        state = ConversationState()

        # Add turns without signatures
        state.turns.append(MagicMock(role="user", thought_signature=None))

        # Add turn with signature
        mock_turn = MagicMock()
        mock_turn.thought_signature = "sig_abc"
        state.turns.append(mock_turn)

        assert state.get_last_thought_signature() == "sig_abc"

    def test_get_last_thought_signature_none(self):
        """Test returns None when no signatures exist."""
        from fcp.services.conversation_state import ConversationState

        state = ConversationState()
        state.turns.append(MagicMock(role="user", thought_signature=None))

        assert state.get_last_thought_signature() is None

    def test_to_contents_empty(self):
        """Test converting empty state to contents."""
        from fcp.services.conversation_state import ConversationState

        state = ConversationState()
        contents = state.to_contents()

        assert contents == []

    def test_to_contents_with_turns(self):
        """Test converting state with turns to contents."""
        from fcp.services.conversation_state import ConversationState, ConversationTurn

        with patch("fcp.services.conversation_state.types") as mock_types:
            mock_content = MagicMock()
            mock_types.Content.return_value = mock_content

            state = ConversationState()
            state.turns.append(ConversationTurn(role="user", parts=[MagicMock()]))
            state.turns.append(ConversationTurn(role="model", parts=[MagicMock()]))

            contents = state.to_contents()

            assert len(contents) == 2
            assert mock_types.Content.call_count == 2


class TestConversationTurnDataclass:
    """Tests for ConversationTurn dataclass."""

    def test_conversation_turn_defaults(self):
        """Test ConversationTurn default values."""
        from fcp.services.conversation_state import ConversationTurn

        turn = ConversationTurn(role="user", parts=[])

        assert turn.role == "user"
        assert turn.parts == []
        assert turn.thought_signature is None
        assert turn.function_calls == []
        assert turn.function_responses == []


class TestMealPlannerAgent:
    """Tests for multi-turn meal planning agent."""

    def test_build_initial_prompt(self):
        """Test initial prompt building."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")
        prompt = agent._build_initial_prompt(
            days=7,
            dietary_preferences=["vegetarian", "low-carb"],
            budget="$100/week",
            taste_profile={"cuisines": ["Japanese", "Italian"]},
        )

        assert "7-day" in prompt
        assert "vegetarian" in prompt
        assert "low-carb" in prompt
        assert "$100/week" in prompt

    def test_build_initial_prompt_minimal(self):
        """Test initial prompt with minimal options."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")
        prompt = agent._build_initial_prompt(
            days=3,
            dietary_preferences=None,
            budget=None,
            taste_profile=None,
        )

        assert "3-day" in prompt
        assert "balanced" in prompt

    def test_has_function_calls_true(self):
        """Test detecting function calls in response."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.function_call = MagicMock(name="get_pantry")
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        assert agent._has_function_calls(mock_response) is True

    def test_has_function_calls_false(self):
        """Test no function calls detected."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.function_call = None
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        assert agent._has_function_calls(mock_response) is False

    def test_has_function_calls_no_attr(self):
        """Test no function calls when attribute missing."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        mock_response = MagicMock()
        mock_part = MagicMock(spec=[])  # No function_call attr
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        assert agent._has_function_calls(mock_response) is False

    def test_extract_meal_plan_from_json(self):
        """Test extracting meal plan from JSON response."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.text = '{"days": [{"date": "Monday", "breakfast": "Oatmeal", "lunch": "Salad", "dinner": "Pasta"}], "shopping_list": ["eggs", "milk"]}'
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        result = agent._extract_meal_plan(mock_response)

        assert len(result.days) == 1
        assert result.days[0].breakfast == "Oatmeal"
        assert len(result.shopping_list) == 2

    def test_extract_meal_plan_with_text_wrapper(self):
        """Test extracting meal plan with text wrapper around JSON."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.text = 'Here is your meal plan:\n{"days": [{"date": "Monday", "breakfast": "Toast"}]}\n\nEnjoy!'
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        result = agent._extract_meal_plan(mock_response)

        assert len(result.days) == 1
        assert result.days[0].breakfast == "Toast"

    def test_extract_meal_plan_invalid_json(self):
        """Test extracting meal plan with invalid JSON returns empty."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.text = "This is not JSON at all {invalid"
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        result = agent._extract_meal_plan(mock_response)

        assert len(result.days) == 0

    def test_extract_meal_plan_no_days_key(self):
        """Test extracting meal plan without days key returns empty."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.text = '{"other_key": "value"}'
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        result = agent._extract_meal_plan(mock_response)

        assert len(result.days) == 0

    def test_extract_meal_plan_no_text(self):
        """Test extracting meal plan with no text part returns empty."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        mock_response = MagicMock()
        mock_part = MagicMock(spec=[])  # No text attribute
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        result = agent._extract_meal_plan(mock_response)

        assert len(result.days) == 0

    def test_extract_shopping_list(self):
        """Test extracting shopping list from response."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.text = '["eggs", "milk", "bread", "butter"]'
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        result = agent._extract_shopping_list(mock_response)

        assert len(result) == 4
        assert "eggs" in result

    def test_extract_shopping_list_with_bullets(self):
        """Test extracting shopping list from bullet point format.

        The fallback to bullet parsing only happens when JSON parsing fails,
        so we use text that starts with '[' but is invalid JSON.
        """
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        mock_response = MagicMock()
        mock_part = MagicMock()
        # Text must start with '[' to trigger JSON parsing, and be invalid to trigger fallback
        mock_part.text = "[invalid]\n- eggs\n- milk\n* bread\n* butter"
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        result = agent._extract_shopping_list(mock_response)

        assert "eggs" in result
        assert "milk" in result
        assert "bread" in result
        assert "butter" in result

    def test_extract_shopping_list_no_text(self):
        """Test extracting shopping list with no text part."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        mock_response = MagicMock()
        mock_part = MagicMock(spec=[])  # No text attribute
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        result = agent._extract_shopping_list(mock_response)

        assert result == []

    @pytest.mark.asyncio
    async def test_call_function_get_pantry_items(self):
        """Test calling get_pantry_items function."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")
        result = await agent._call_function("get_pantry_items", {})

        assert "items" in result
        assert "message" in result

    @pytest.mark.asyncio
    async def test_call_function_get_food_history(self):
        """Test calling get_food_history function."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")
        result = await agent._call_function("get_food_history", {"days": 14})

        assert "logs" in result
        assert result["days_checked"] == 14

    @pytest.mark.asyncio
    async def test_call_function_get_food_history_default_days(self):
        """Test calling get_food_history with default days."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")
        result = await agent._call_function("get_food_history", {})

        assert result["days_checked"] == 7

    @pytest.mark.asyncio
    async def test_call_function_check_recipe_exists(self):
        """Test calling check_recipe_exists function."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")
        result = await agent._call_function("check_recipe_exists", {"dish_name": "Pasta"})

        assert result["exists"] is False
        assert result["dish_name"] == "Pasta"

    @pytest.mark.asyncio
    async def test_call_function_check_recipe_exists_default(self):
        """Test calling check_recipe_exists without dish_name."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")
        result = await agent._call_function("check_recipe_exists", {})

        assert result["dish_name"] == ""

    @pytest.mark.asyncio
    async def test_call_function_unknown(self):
        """Test calling unknown function."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")
        result = await agent._call_function("unknown_func", {})

        assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_function_calls(self):
        """Test executing function calls from response."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.function_call = MagicMock()
        mock_part.function_call.name = "get_pantry_items"
        mock_part.function_call.args = {}
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        results = await agent._execute_function_calls(mock_response)

        assert len(results) == 1
        assert results[0]["name"] == "get_pantry_items"
        assert "items" in results[0]["result"]

    @pytest.mark.asyncio
    async def test_execute_function_calls_no_args(self):
        """Test executing function calls with None args."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.function_call = MagicMock()
        mock_part.function_call.name = "get_pantry_items"
        mock_part.function_call.args = None
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        results = await agent._execute_function_calls(mock_response)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_start_planning(self):
        """Test starting a meal planning session."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        # Mock response without function calls
        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.text = '{"days": [{"date": "Monday", "breakfast": "Toast"}], "shopping_list": []}'
        mock_part.function_call = None
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        with patch.object(agent, "_generate_with_tools", AsyncMock(return_value=mock_response)):
            result = await agent.start_planning(days=7)

            assert len(result.days) == 1

    @pytest.mark.asyncio
    async def test_start_planning_function_call_path(self):
        """Test start_planning with function calls to cover lines 123-126."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        class TestMealPlannerAgent(MealPlannerAgent):
            def __init__(self, user_id: str):
                super().__init__(user_id)
                self.call_count = 0

            async def _generate_with_tools(self):
                self.call_count += 1
                mock_response = MagicMock()
                if self.call_count == 1:
                    # First call: return function call response
                    mock_part = MagicMock()
                    mock_part.function_call = MagicMock()
                    mock_part.function_call.name = "get_pantry_items"
                    mock_part.function_call.args = {}
                else:
                    # Subsequent calls: return meal plan
                    mock_part = MagicMock(spec=["text"])
                    mock_part.text = '{"days": []}'
                mock_response.candidates = [MagicMock()]
                mock_response.candidates[0].content.parts = [mock_part]
                return mock_response

        with patch("fcp.services.conversation_state.types") as mt:
            mt.Part.return_value = MagicMock()
            mt.FunctionResponse.return_value = MagicMock()

            agent = TestMealPlannerAgent("user123")
            await agent.start_planning()

            # _generate_with_tools should be called twice (initial + after function call)
            assert agent.call_count == 2

    @pytest.mark.asyncio
    async def test_refine_plan(self):
        """Test refining an existing meal plan."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.text = '{"days": [{"date": "Tuesday", "breakfast": "Pancakes"}]}'
        mock_part.function_call = None
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        with patch.object(agent, "_generate_with_tools", AsyncMock(return_value=mock_response)):
            result = await agent.refine_plan("Make Tuesday breakfast pancakes")

            assert result.days[0].breakfast == "Pancakes"

    @pytest.mark.asyncio
    async def test_refine_plan_with_function_calls(self):
        """Test refining meal plan when response contains function calls (covers lines 123-126)."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        # First response with function call
        mock_fc_part = MagicMock()
        mock_fc_part.function_call = MagicMock()
        mock_fc_part.function_call.name = "get_food_history"
        mock_fc_part.function_call.args = {"days": 7}
        mock_fc_part.text = None
        mock_fc_response = MagicMock()
        mock_fc_response.candidates = [MagicMock()]
        mock_fc_response.candidates[0].content.parts = [mock_fc_part]

        # Second response with final meal plan
        mock_plan_part = MagicMock()
        mock_plan_part.function_call = None
        mock_plan_part.text = '{"days": [{"date": "Tuesday", "breakfast": "Oatmeal"}]}'
        mock_plan_response = MagicMock()
        mock_plan_response.candidates = [MagicMock()]
        mock_plan_response.candidates[0].content.parts = [mock_plan_part]

        call_count = [0]

        async def mock_generate(*args, **kwargs):
            call_count[0] += 1
            return mock_fc_response if call_count[0] == 1 else mock_plan_response

        with patch("fcp.services.conversation_state.types") as mock_types:
            mock_types.Part.return_value = MagicMock()
            mock_types.FunctionResponse.return_value = MagicMock()

            agent = MealPlannerAgent("user123")

            with patch.object(agent, "_generate_with_tools", mock_generate):
                result = await agent.refine_plan("Add more protein to all lunches")

                # Verify _generate_with_tools was called twice (once for fc, once for result)
                assert call_count[0] == 2, f"Expected 2 calls, got {call_count[0]}"
                assert result.days[0].breakfast == "Oatmeal"

    @pytest.mark.asyncio
    async def test_generate_shopping_list(self):
        """Test generating shopping list."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.text = '["eggs", "milk"]'
        mock_part.function_call = None
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        with patch.object(agent, "_generate_with_tools", AsyncMock(return_value=mock_response)):
            result = await agent.generate_shopping_list()

            assert "eggs" in result
            assert "milk" in result

    @pytest.mark.asyncio
    async def test_generate_shopping_list_with_function_calls(self):
        """Test generating shopping list with function calls."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        # First response with function call (pantry check)
        mock_fc_part = MagicMock()
        mock_fc_part.function_call = MagicMock()
        mock_fc_part.function_call.name = "get_pantry_items"
        mock_fc_part.function_call.args = {"user_id": "user123"}  # Non-empty args
        mock_fc_part.text = None
        mock_fc_part.thought_signature = None
        mock_fc_response = MagicMock()
        mock_fc_response.candidates = [MagicMock()]
        mock_fc_response.candidates[0].content.parts = [mock_fc_part]

        # Second response with shopping list
        mock_list_part = MagicMock()
        mock_list_part.function_call = None
        mock_list_part.text = '["bread", "butter"]'
        mock_list_part.thought_signature = None
        mock_list_response = MagicMock()
        mock_list_response.candidates = [MagicMock()]
        mock_list_response.candidates[0].content.parts = [mock_list_part]

        call_count = [0]

        async def mock_generate(*args, **kwargs):
            call_count[0] += 1
            return mock_fc_response if call_count[0] == 1 else mock_list_response

        with patch("fcp.services.conversation_state.types") as mock_types:
            mock_types.Part.return_value = MagicMock()
            mock_types.FunctionResponse.return_value = MagicMock()

            agent = MealPlannerAgent("user123")
            mock_firestore = AsyncMock()
            mock_firestore.get_pantry_items = AsyncMock(return_value=["eggs"])
            agent.firestore_service = mock_firestore

            with patch.object(agent, "_generate_with_tools", mock_generate):
                result = await agent.generate_shopping_list()

                # Verify _generate_with_tools was called at least twice
                assert call_count[0] >= 2, f"Expected at least 2 calls, got {call_count[0]}"
                assert "bread" in result
                assert "butter" in result

    def test_extract_meal_plan_json_decode_error(self):
        """Test _extract_meal_plan handles JSONDecodeError gracefully."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        # Response with invalid JSON inside markdown block
        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.text = "```json\n{invalid json here}\n```"
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        result = agent._extract_meal_plan(mock_response)

        # Should return empty plan on parse error
        assert len(result.days) == 0

    def test_extract_shopping_list_invalid_json(self):
        """Test _extract_shopping_list falls back to line parsing on JSONDecodeError."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        # Response with invalid JSON that has brackets (triggers JSONDecodeError)
        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.text = "[invalid json here]\n- eggs\n- milk\n* bread"
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        result = agent._extract_shopping_list(mock_response)

        # Should fall back to line parsing due to JSONDecodeError
        assert "eggs" in result
        assert "milk" in result
        assert "bread" in result

    def test_extract_shopping_list_plain_lines(self):
        """Test _extract_shopping_list with plain lines (no bullets)."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        # Response with invalid JSON that triggers fallback, including plain lines and header
        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.text = "[invalid]\n# This is a header\neggs\nmilk\n\n"
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        result = agent._extract_shopping_list(mock_response)

        # Should include plain lines, skip headers and empty lines
        assert "eggs" in result
        assert "milk" in result
        # Header line should be skipped (starts with #)
        assert "# This is a header" not in result

    def test_extract_shopping_list_multiple_parts_loop_continuation(self):
        """Test _extract_shopping_list with multiple parts to cover branch 373->366.

        The first part has text but no valid JSON array pattern (no brackets),
        so the loop continues to the next part which has a valid JSON array.
        """
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        # First part: text without any brackets (start will be -1, failing the condition on line 373)
        mock_part1 = MagicMock()
        mock_part1.text = "Here is your shopping list:"  # No [ ] brackets

        # Second part: valid JSON array
        mock_part2 = MagicMock()
        mock_part2.text = '["eggs", "milk", "bread"]'

        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part1, mock_part2]

        result = agent._extract_shopping_list(mock_response)

        # Should get the valid JSON array from the second part
        assert "eggs" in result
        assert "milk" in result
        assert "bread" in result

    @pytest.mark.asyncio
    async def test_execute_function_calls_no_function_call_parts(self):
        """Test _execute_function_calls with parts that have no function_call."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        # Response with parts that don't have function_call
        mock_response = MagicMock()
        mock_part = MagicMock(spec=["text"])  # No function_call attribute
        mock_part.text = "Some text"
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        results = await agent._execute_function_calls(mock_response)

        # Should return empty list when no function calls found
        assert results == []

    @pytest.mark.asyncio
    async def test_generate_with_tools(self):
        """Test _generate_with_tools method."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlannerAgent

        agent = MealPlannerAgent("user123")

        mock_response = MagicMock()

        # genai is imported inside _generate_with_tools, so patch at google.genai level
        with patch("google.genai.Client") as mock_client_class:
            with patch("google.genai.types") as mock_types:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
                mock_types.Tool.return_value = MagicMock()
                mock_types.FunctionDeclaration.return_value = MagicMock()
                mock_types.Schema.return_value = MagicMock()
                mock_types.GenerateContentConfig.return_value = MagicMock()
                mock_types.ThinkingConfig.return_value = MagicMock()

                result = await agent._generate_with_tools()

                assert result == mock_response
                mock_client.aio.models.generate_content.assert_called_once()


class TestMealPlanModels:
    """Tests for meal plan Pydantic models."""

    def test_meal_plan_day_model(self):
        """Test MealPlanDay model."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlanDay

        day = MealPlanDay(
            date="Monday",
            breakfast="Oatmeal",
            lunch="Salad",
            dinner="Pasta",
            snacks=["Apple", "Nuts"],
            estimated_calories=1800,
            notes="Prep pasta sauce ahead",
        )

        assert day.date == "Monday"
        assert day.breakfast == "Oatmeal"
        assert len(day.snacks) == 2

    def test_meal_plan_day_defaults(self):
        """Test MealPlanDay with defaults."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlanDay

        day = MealPlanDay(date="Tuesday")

        assert day.breakfast is None
        assert day.snacks == []
        assert day.estimated_calories is None

    def test_meal_plan_model(self):
        """Test MealPlan model."""
        from fcp.agents.pydantic_agents.meal_planner import MealPlan, MealPlanDay

        plan = MealPlan(
            days=[MealPlanDay(date="Monday")],
            shopping_list=["eggs", "milk"],
            dietary_notes="High protein",
            total_estimated_cost=75.50,
        )

        assert len(plan.days) == 1
        assert len(plan.shopping_list) == 2
        assert plan.total_estimated_cost == 75.50


# =============================================================================
# Feature 3: Thinking Level Control Tests
# =============================================================================


class TestThinkingStrategy:
    """Tests for thinking level optimization."""

    def test_get_thinking_level_trivial_task(self):
        """Test minimal thinking for trivial tasks."""
        from fcp.services.thinking_strategy import get_thinking_level

        assert get_thinking_level("food_detection") == "minimal"

    def test_get_thinking_level_simple_task(self):
        """Test low thinking for simple tasks."""
        from fcp.services.thinking_strategy import get_thinking_level

        assert get_thinking_level("cuisine_classification") == "low"
        assert get_thinking_level("dish_name_extraction") == "low"

    def test_get_thinking_level_moderate_task(self):
        """Test medium thinking for moderate tasks."""
        from fcp.services.thinking_strategy import get_thinking_level

        assert get_thinking_level("detailed_nutrition") == "medium"
        assert get_thinking_level("meal_suggestions") == "medium"

    def test_get_thinking_level_complex_task(self):
        """Test high thinking for complex tasks."""
        from fcp.services.thinking_strategy import get_thinking_level

        assert get_thinking_level("lifetime_analysis") == "high"
        assert get_thinking_level("meal_planning") == "high"

    def test_get_thinking_level_unknown_defaults_high(self):
        """Test unknown operations default to high thinking."""
        from fcp.services.thinking_strategy import get_thinking_level

        assert get_thinking_level("unknown_operation") == "high"

    def test_estimate_cost_savings(self):
        """Test cost savings estimation."""
        from fcp.services.thinking_strategy import estimate_cost_savings

        assert estimate_cost_savings("food_detection") == 0.7  # 70% savings
        assert estimate_cost_savings("cuisine_classification") == 0.5  # 50% savings
        assert estimate_cost_savings("lifetime_analysis") == 0.0  # No savings


# =============================================================================
# Feature 4: Computer Use Tests
# =============================================================================


class TestBrowserAutomationService:
    """Tests for browser automation and recipe import."""

    def test_recipe_import_result_model(self):
        """Test RecipeImportResult model creation."""
        from fcp.services.browser_automation import RecipeImportResult

        result = RecipeImportResult(
            title="Classic Pasta",
            ingredients=["pasta", "tomatoes", "garlic"],
            instructions=["Boil water", "Cook pasta", "Add sauce"],
            prep_time="10 minutes",
            cook_time="20 minutes",
            servings=4,
            source_url="https://example.com/recipe",
        )

        assert result.title == "Classic Pasta"
        assert len(result.ingredients) == 3
        assert len(result.instructions) == 3
        assert result.servings == 4

    def test_recipe_import_result_optional_fields(self):
        """Test RecipeImportResult with optional fields."""
        from fcp.services.browser_automation import RecipeImportResult

        result = RecipeImportResult(
            title="Simple Salad",
            ingredients=["lettuce"],
            instructions=["Mix"],
            source_url="https://example.com",
        )

        assert result.prep_time is None
        assert result.cook_time is None
        assert result.servings is None
        assert result.image_url is None

    def test_browser_action_model(self):
        """Test BrowserAction model creation."""
        from fcp.services.browser_automation import BrowserAction

        action = BrowserAction(
            action="click_at",
            x=500,
            y=300,
        )

        assert action.action == "click_at"
        assert action.x == 500
        assert action.y == 300

    def test_browser_action_all_fields(self):
        """Test BrowserAction with all fields."""
        from fcp.services.browser_automation import BrowserAction

        action = BrowserAction(
            action="type_text_at",
            x=100,
            y=200,
            text="Hello",
            url="https://example.com",
            direction="down",
            keys="Enter",
        )

        assert action.text == "Hello"
        assert action.url == "https://example.com"
        assert action.direction == "down"
        assert action.keys == "Enter"

    @pytest.mark.asyncio
    async def test_take_screenshot_returns_base64(self):
        """Test screenshot capture returns base64 encoded data."""
        from fcp.services.browser_automation import BrowserAutomationService

        service = BrowserAutomationService()
        service.page = AsyncMock()
        service.page.screenshot = AsyncMock(return_value=b"fake-screenshot-data")

        result = await service._take_screenshot()

        expected = base64.b64encode(b"fake-screenshot-data").decode("utf-8")
        assert result == expected

    @pytest.mark.asyncio
    async def test_execute_action_click(self):
        """Test executing a click action."""
        from fcp.services.browser_automation import (
            BrowserAction,
            BrowserAutomationService,
        )

        service = BrowserAutomationService()
        service.page = AsyncMock()
        service.SCREEN_WIDTH = 1440
        service.SCREEN_HEIGHT = 900

        action = BrowserAction(action="click_at", x=500, y=500)
        await service._execute_action(action)

        service.page.mouse.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_action_click_no_coordinates(self):
        """Test click action without coordinates does nothing."""
        from fcp.services.browser_automation import (
            BrowserAction,
            BrowserAutomationService,
        )

        service = BrowserAutomationService()
        service.page = AsyncMock()

        action = BrowserAction(action="click_at")  # No x or y
        await service._execute_action(action)

        service.page.mouse.click.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_action_type_text(self):
        """Test executing a type text action."""
        from fcp.services.browser_automation import (
            BrowserAction,
            BrowserAutomationService,
        )

        service = BrowserAutomationService()
        service.page = AsyncMock()
        service.SCREEN_WIDTH = 1440
        service.SCREEN_HEIGHT = 900

        action = BrowserAction(action="type_text_at", x=100, y=100, text="Hello")
        await service._execute_action(action)

        service.page.mouse.click.assert_called_once()
        service.page.keyboard.type.assert_called_once_with("Hello")

    @pytest.mark.asyncio
    async def test_execute_action_type_text_no_text(self):
        """Test executing type text action without text."""
        from fcp.services.browser_automation import (
            BrowserAction,
            BrowserAutomationService,
        )

        service = BrowserAutomationService()
        service.page = AsyncMock()

        action = BrowserAction(action="type_text_at", x=100, y=100)
        await service._execute_action(action)

        service.page.keyboard.type.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_action_type_text_no_coordinates(self):
        """Test type_text_at without coordinates only types text."""
        from fcp.services.browser_automation import (
            BrowserAction,
            BrowserAutomationService,
        )

        service = BrowserAutomationService()
        service.page = AsyncMock()

        action = BrowserAction(action="type_text_at", text="Hello")  # No x or y
        await service._execute_action(action)

        # Should not click without coordinates
        service.page.mouse.click.assert_not_called()
        # But should still type the text
        service.page.keyboard.type.assert_called_once_with("Hello")

    @pytest.mark.asyncio
    async def test_execute_action_scroll_document(self):
        """Test executing a scroll document action."""
        from fcp.services.browser_automation import (
            BrowserAction,
            BrowserAutomationService,
        )

        service = BrowserAutomationService()
        service.page = AsyncMock()

        action = BrowserAction(action="scroll_document", direction="down")
        await service._execute_action(action)

        service.page.mouse.wheel.assert_called_once_with(0, 300)

    @pytest.mark.asyncio
    async def test_execute_action_scroll_document_up(self):
        """Test scrolling up."""
        from fcp.services.browser_automation import (
            BrowserAction,
            BrowserAutomationService,
        )

        service = BrowserAutomationService()
        service.page = AsyncMock()

        action = BrowserAction(action="scroll_document", direction="up")
        await service._execute_action(action)

        service.page.mouse.wheel.assert_called_once_with(0, -300)

    @pytest.mark.asyncio
    async def test_execute_action_scroll_at(self):
        """Test executing scroll at position."""
        from fcp.services.browser_automation import (
            BrowserAction,
            BrowserAutomationService,
        )

        service = BrowserAutomationService()
        service.page = AsyncMock()
        service.SCREEN_WIDTH = 1000
        service.SCREEN_HEIGHT = 1000

        action = BrowserAction(action="scroll_at", x=500, y=500, direction="down")
        await service._execute_action(action)

        service.page.mouse.move.assert_called_once()
        service.page.mouse.wheel.assert_called_once_with(0, 200)

    @pytest.mark.asyncio
    async def test_execute_action_scroll_at_up(self):
        """Test scroll at position upward."""
        from fcp.services.browser_automation import (
            BrowserAction,
            BrowserAutomationService,
        )

        service = BrowserAutomationService()
        service.page = AsyncMock()

        action = BrowserAction(action="scroll_at", x=500, y=500, direction="up")
        await service._execute_action(action)

        service.page.mouse.wheel.assert_called_once_with(0, -200)

    @pytest.mark.asyncio
    async def test_execute_action_scroll_at_no_coordinates(self):
        """Test scroll_at without coordinates does nothing."""
        from fcp.services.browser_automation import (
            BrowserAction,
            BrowserAutomationService,
        )

        service = BrowserAutomationService()
        service.page = AsyncMock()

        action = BrowserAction(action="scroll_at", direction="down")  # No x or y
        await service._execute_action(action)

        # Should not move or scroll without coordinates
        service.page.mouse.move.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_action_navigate(self):
        """Test executing a navigation action."""
        from fcp.services.browser_automation import (
            BrowserAction,
            BrowserAutomationService,
        )

        service = BrowserAutomationService()
        service.page = AsyncMock()

        action = BrowserAction(action="navigate", url="https://example.com")
        await service._execute_action(action)

        service.page.goto.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    async def test_execute_action_navigate_no_url(self):
        """Test navigation without URL."""
        from fcp.services.browser_automation import (
            BrowserAction,
            BrowserAutomationService,
        )

        service = BrowserAutomationService()
        service.page = AsyncMock()

        action = BrowserAction(action="navigate")
        await service._execute_action(action)

        service.page.goto.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_action_navigate_rejects_ssrf(self):
        """Test that navigation rejects SSRF URLs."""
        from fcp.security.url_validator import ImageURLError
        from fcp.services.browser_automation import (
            BrowserAction,
            BrowserAutomationService,
        )

        service = BrowserAutomationService()
        service.page = AsyncMock()

        action = BrowserAction(action="navigate", url="http://169.254.169.254/latest/meta-data/")
        with pytest.raises(ImageURLError, match="not allowed"):
            await service._execute_action(action)

        service.page.goto.assert_not_called()

    @pytest.mark.asyncio
    async def test_import_recipe_rejects_ssrf_url(self):
        """Test that import_recipe_from_url rejects SSRF URLs."""
        from fcp.security.url_validator import ImageURLError
        from fcp.services.browser_automation import BrowserAutomationService

        service = BrowserAutomationService()

        with pytest.raises(ImageURLError, match="private/internal"):
            await service.import_recipe_from_url("http://10.0.0.1/admin")

    @pytest.mark.asyncio
    async def test_execute_action_key_combination(self):
        """Test key combination action."""
        from fcp.services.browser_automation import (
            BrowserAction,
            BrowserAutomationService,
        )

        service = BrowserAutomationService()
        service.page = AsyncMock()

        action = BrowserAction(action="key_combination", keys="Control+Enter")
        await service._execute_action(action)

        service.page.keyboard.press.assert_called_once_with("Control+Enter")

    @pytest.mark.asyncio
    async def test_execute_action_key_combination_no_keys(self):
        """Test key combination without keys."""
        from fcp.services.browser_automation import (
            BrowserAction,
            BrowserAutomationService,
        )

        service = BrowserAutomationService()
        service.page = AsyncMock()

        action = BrowserAction(action="key_combination")
        await service._execute_action(action)

        service.page.keyboard.press.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_action_wait(self):
        """Test wait action."""
        from fcp.services.browser_automation import (
            BrowserAction,
            BrowserAutomationService,
        )

        service = BrowserAutomationService()
        service.page = AsyncMock()

        action = BrowserAction(action="wait_5_seconds")
        await service._execute_action(action)

        service.page.wait_for_timeout.assert_called_once_with(5000)

    @pytest.mark.asyncio
    async def test_execute_action_go_back(self):
        """Test go back action."""
        from fcp.services.browser_automation import (
            BrowserAction,
            BrowserAutomationService,
        )

        service = BrowserAutomationService()
        service.page = AsyncMock()

        action = BrowserAction(action="go_back")
        await service._execute_action(action)

        service.page.go_back.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_action_unknown(self):
        """Test unknown action does nothing."""
        from fcp.services.browser_automation import (
            BrowserAction,
            BrowserAutomationService,
        )

        service = BrowserAutomationService()
        service.page = AsyncMock()

        action = BrowserAction(action="unknown_action")
        await service._execute_action(action)

        # Should not raise, just do nothing

    def test_extract_actions_from_response(self):
        """Test extracting browser actions from model response."""
        from fcp.services.browser_automation import BrowserAutomationService

        service = BrowserAutomationService()

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.function_call = MagicMock()
        mock_part.function_call.name = "click_at"
        mock_part.function_call.args = {"x": 100, "y": 200}
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        actions = service._extract_actions(mock_response)

        assert len(actions) == 1
        assert actions[0].action == "click_at"
        assert actions[0].x == 100
        assert actions[0].y == 200

    def test_extract_actions_non_browser_function(self):
        """Test extract actions ignores non-browser functions."""
        from fcp.services.browser_automation import BrowserAutomationService

        service = BrowserAutomationService()

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.function_call = MagicMock()
        mock_part.function_call.name = "submit_recipe"  # Not a browser action
        mock_part.function_call.args = {}
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        actions = service._extract_actions(mock_response)

        assert len(actions) == 0

    def test_extract_actions_no_function_call(self):
        """Test extract actions with no function calls."""
        from fcp.services.browser_automation import BrowserAutomationService

        service = BrowserAutomationService()

        mock_response = MagicMock()
        mock_part = MagicMock(spec=[])  # No function_call attribute
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        actions = service._extract_actions(mock_response)

        assert len(actions) == 0

    def test_has_recipe_submission_true(self):
        """Test detecting recipe submission in response."""
        from fcp.services.browser_automation import BrowserAutomationService

        service = BrowserAutomationService()

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.function_call = MagicMock()
        mock_part.function_call.name = "submit_recipe"
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        assert service._has_recipe_submission(mock_response) is True

    def test_has_recipe_submission_false(self):
        """Test when no recipe submission in response."""
        from fcp.services.browser_automation import BrowserAutomationService

        service = BrowserAutomationService()

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.function_call = MagicMock()
        mock_part.function_call.name = "scroll_document"
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        assert service._has_recipe_submission(mock_response) is False

    def test_has_recipe_submission_no_function_call(self):
        """Test submission check with no function_call attribute."""
        from fcp.services.browser_automation import BrowserAutomationService

        service = BrowserAutomationService()

        mock_response = MagicMock()
        mock_part = MagicMock(spec=[])
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        assert service._has_recipe_submission(mock_response) is False

    def test_extract_recipe_data(self):
        """Test extracting recipe data from submission."""
        from fcp.services.browser_automation import BrowserAutomationService

        service = BrowserAutomationService()

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.function_call = MagicMock()
        mock_part.function_call.name = "submit_recipe"
        mock_part.function_call.args = {
            "title": "Test Recipe",
            "ingredients": ["a", "b"],
            "instructions": ["step 1"],
        }
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        data = service._extract_recipe_data(mock_response)

        assert data["title"] == "Test Recipe"
        assert len(data["ingredients"]) == 2

    def test_extract_recipe_data_not_found(self):
        """Test extracting recipe data raises when not found."""
        from fcp.services.browser_automation import BrowserAutomationService

        service = BrowserAutomationService()

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.function_call = MagicMock()
        mock_part.function_call.name = "other_function"
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        with pytest.raises(ValueError, match="No recipe submission found"):
            service._extract_recipe_data(mock_response)

    @pytest.mark.asyncio
    async def test_import_recipe_from_url(self):
        """Test importing recipe from URL."""
        import sys

        # Create mock playwright module
        mock_playwright_module = MagicMock()
        mock_async_playwright = AsyncMock()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()

        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()
        mock_page.goto = AsyncMock()

        mock_playwright_context = AsyncMock()
        mock_playwright_context.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_async_playwright.__aenter__ = AsyncMock(return_value=mock_playwright_context)
        mock_async_playwright.__aexit__ = AsyncMock(return_value=None)

        mock_playwright_module.async_playwright = MagicMock(return_value=mock_async_playwright)
        mock_playwright_module.async_api = MagicMock()
        mock_playwright_module.async_api.async_playwright = MagicMock(return_value=mock_async_playwright)

        # Patch sys.modules to provide mock playwright
        with patch.dict(
            sys.modules,
            {"playwright": mock_playwright_module, "playwright.async_api": mock_playwright_module.async_api},
        ):
            from fcp.services.browser_automation import BrowserAutomationService

            mock_recipe_data = {
                "title": "Chocolate Cake",
                "ingredients": ["flour", "sugar"],
                "instructions": ["mix", "bake"],
            }

            service = BrowserAutomationService()

            with patch.object(service, "_run_extraction_loop", AsyncMock(return_value=mock_recipe_data)):
                result = await service.import_recipe_from_url("https://example.com/recipe")

                assert result.title == "Chocolate Cake"
                assert result.source_url == "https://example.com/recipe"

    @pytest.mark.asyncio
    async def test_run_extraction_loop_immediate_submission(self):
        """Test extraction loop with immediate recipe submission."""
        from fcp.services.browser_automation import BrowserAutomationService

        service = BrowserAutomationService()
        service.page = AsyncMock()
        service.page.screenshot = AsyncMock(return_value=b"screenshot")

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.function_call = MagicMock()
        mock_part.function_call.name = "submit_recipe"
        mock_part.function_call.args = {
            "title": "Quick Recipe",
            "ingredients": ["a"],
            "instructions": ["do"],
        }
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        with patch.object(service, "_generate_with_computer_use", AsyncMock(return_value=mock_response)):
            result = await service._run_extraction_loop()

            assert result["title"] == "Quick Recipe"

    @pytest.mark.asyncio
    async def test_run_extraction_loop_with_actions(self):
        """Test extraction loop executing actions."""
        from fcp.services.browser_automation import BrowserAutomationService

        service = BrowserAutomationService()
        service.page = AsyncMock()
        service.page.screenshot = AsyncMock(return_value=b"screenshot")

        # First response with action
        mock_action_part = MagicMock()
        mock_action_part.function_call = MagicMock()
        mock_action_part.function_call.name = "scroll_document"
        mock_action_part.function_call.args = {"direction": "down"}
        mock_action_response = MagicMock()
        mock_action_response.candidates = [MagicMock()]
        mock_action_response.candidates[0].content.parts = [mock_action_part]

        # Second response with submission
        mock_submit_part = MagicMock()
        mock_submit_part.function_call = MagicMock()
        mock_submit_part.function_call.name = "submit_recipe"
        mock_submit_part.function_call.args = {
            "title": "Found Recipe",
            "ingredients": ["x"],
            "instructions": ["y"],
        }
        mock_submit_response = MagicMock()
        mock_submit_response.candidates = [MagicMock()]
        mock_submit_response.candidates[0].content.parts = [mock_submit_part]

        call_count = [0]

        async def mock_generate(history):
            call_count[0] += 1
            return mock_action_response if call_count[0] == 1 else mock_submit_response

        with patch.object(service, "_generate_with_computer_use", mock_generate):
            with patch.object(service, "_execute_action", AsyncMock()):
                result = await service._run_extraction_loop()

                assert result["title"] == "Found Recipe"

    @pytest.mark.asyncio
    async def test_run_extraction_loop_max_steps_exceeded(self):
        """Test extraction loop raises when max steps exceeded."""
        from fcp.services.browser_automation import BrowserAutomationService

        service = BrowserAutomationService()
        service.page = AsyncMock()
        service.page.screenshot = AsyncMock(return_value=b"screenshot")

        # Response with actions but no submission - loop should iterate through all steps
        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.function_call = MagicMock()
        mock_part.function_call.name = "scroll_document"  # This is a browser action, not submission
        mock_part.function_call.args = {"direction": "down"}
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        with patch.object(service, "_generate_with_computer_use", AsyncMock(return_value=mock_response)):
            with patch.object(service, "_execute_action", AsyncMock()):  # Don't actually execute actions
                with pytest.raises(ValueError, match="Failed to extract recipe"):
                    await service._run_extraction_loop(max_steps=2)

    @pytest.mark.asyncio
    async def test_run_extraction_loop_breaks_on_no_actions(self):
        """Test extraction loop breaks early when no actions returned."""
        from fcp.services.browser_automation import BrowserAutomationService

        service = BrowserAutomationService()
        service.page = AsyncMock()
        service.page.screenshot = AsyncMock(return_value=b"screenshot")

        # Response with no actions and no submission - use spec=[] to prevent function_call attribute
        mock_response = MagicMock()
        mock_part = MagicMock(spec=[])  # No function_call attribute
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        with patch.object(service, "_generate_with_computer_use", AsyncMock(return_value=mock_response)):
            with pytest.raises(ValueError, match="Failed to extract recipe"):
                await service._run_extraction_loop(max_steps=10)

    @pytest.mark.asyncio
    async def test_generate_with_computer_use(self):
        """Test generating with computer use tools."""
        from fcp.services.browser_automation import BrowserAutomationService

        mock_response = MagicMock()

        # Patch types at google.genai.types since it's imported inside the method
        with patch("google.genai.types") as mock_types:
            mock_types.Tool.return_value = MagicMock()
            mock_types.ComputerUse.return_value = MagicMock()
            mock_types.Environment.ENVIRONMENT_BROWSER = "browser"
            mock_types.FunctionDeclaration.return_value = MagicMock()
            mock_types.Schema.return_value = MagicMock()
            mock_types.GenerateContentConfig.return_value = MagicMock()
            mock_types.ThinkingConfig.return_value = MagicMock()

            service = BrowserAutomationService()
            service.client = MagicMock()
            service.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await service._generate_with_computer_use([{"role": "user", "parts": []}])

            assert result == mock_response


# =============================================================================
# Feature 5: Live API Cooking Assistant Tests
# =============================================================================


class TestCookingAssistantService:
    """Tests for real-time cooking assistant."""

    def test_cooking_step_model(self):
        """Test CookingStep model."""
        from fcp.services.cooking_assistant import CookingStep

        step = CookingStep(
            step_number=1,
            instruction="Boil water",
            duration_seconds=300,
            temperature="212°F",
            warning="Handle hot water carefully",
        )

        assert step.step_number == 1
        assert step.instruction == "Boil water"
        assert step.duration_seconds == 300

    def test_cooking_step_defaults(self):
        """Test CookingStep with defaults."""
        from fcp.services.cooking_assistant import CookingStep

        step = CookingStep(step_number=1, instruction="Mix")

        assert step.duration_seconds is None
        assert step.temperature is None
        assert step.warning is None

    def test_cooking_session_model(self):
        """Test CookingSession model."""
        from fcp.services.cooking_assistant import CookingSession

        session = CookingSession(
            recipe_name="Pasta",
            current_step=2,
            total_steps=5,
            active_timers=[{"id": "t1", "label": "boil"}],
            warnings=["Watch the heat"],
        )

        assert session.recipe_name == "Pasta"
        assert session.current_step == 2
        assert len(session.active_timers) == 1

    def test_build_system_instruction(self):
        """Test system instruction includes recipe details."""
        from fcp.services.cooking_assistant import CookingAssistantService

        service = CookingAssistantService("user123")

        recipe = {
            "name": "Spaghetti Carbonara",
            "ingredients": ["spaghetti", "eggs", "pecorino", "guanciale"],
            "instructions": ["Boil water", "Cook pasta", "Make sauce"],
        }

        instruction = service._build_system_instruction(recipe)

        assert "Spaghetti Carbonara" in instruction
        assert "spaghetti" in instruction
        assert "Boil water" in instruction
        assert "cooking assistant" in instruction.lower()

    def test_build_system_instruction_empty_recipe(self):
        """Test system instruction with empty recipe."""
        from fcp.services.cooking_assistant import CookingAssistantService

        service = CookingAssistantService("user123")

        recipe = {}

        instruction = service._build_system_instruction(recipe)

        assert "Unknown" in instruction

    def test_build_cooking_tools(self):
        """Test cooking tools include all required functions."""
        from fcp.services.cooking_assistant import CookingAssistantService

        service = CookingAssistantService("user123")
        tools = service._build_cooking_tools()

        assert len(tools) > 0

        # Extract function names
        function_names = []
        for tool in tools:
            function_names.extend(decl.name for decl in tool.function_declarations)
        assert "set_timer" in function_names
        assert "advance_step" in function_names
        assert "log_cooking_note" in function_names
        assert "emergency_alert" in function_names

    @pytest.mark.asyncio
    async def test_handle_tool_call_set_timer(self):
        """Test handling set_timer function call."""
        from fcp.services.cooking_assistant import (
            CookingAssistantService,
            CookingSession,
        )

        service = CookingAssistantService("user123")
        service.session = CookingSession(
            recipe_name="Test",
            current_step=1,
            total_steps=5,
            active_timers=[],
            warnings=[],
        )

        mock_tool_call = MagicMock()
        mock_tool_call.function_calls = [MagicMock()]
        mock_tool_call.function_calls[0].name = "set_timer"
        mock_tool_call.function_calls[0].args = {
            "duration_seconds": 300,
            "label": "pasta boiling",
        }

        with patch.object(service, "_create_timer", return_value="timer123"):
            result = await service._handle_tool_call(mock_tool_call)

            assert result.name == "set_timer"
            assert result.response["timer_id"] == "timer123"  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_handle_tool_call_advance_step(self):
        """Test handling advance_step function call."""
        from fcp.services.cooking_assistant import (
            CookingAssistantService,
            CookingSession,
        )

        service = CookingAssistantService("user123")
        service.session = CookingSession(
            recipe_name="Test",
            current_step=1,
            total_steps=5,
            active_timers=[],
            warnings=[],
        )

        mock_tool_call = MagicMock()
        mock_tool_call.function_calls = [MagicMock()]
        mock_tool_call.function_calls[0].name = "advance_step"
        mock_tool_call.function_calls[0].args = {"step_number": 3}

        result = await service._handle_tool_call(mock_tool_call)

        assert service.session.current_step == 3
        assert result.response["current_step"] == 3  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_handle_tool_call_advance_step_no_number(self):
        """Test advance_step without step number increments."""
        from fcp.services.cooking_assistant import (
            CookingAssistantService,
            CookingSession,
        )

        service = CookingAssistantService("user123")
        service.session = CookingSession(
            recipe_name="Test",
            current_step=2,
            total_steps=5,
            active_timers=[],
            warnings=[],
        )

        mock_tool_call = MagicMock()
        mock_tool_call.function_calls = [MagicMock()]
        mock_tool_call.function_calls[0].name = "advance_step"
        mock_tool_call.function_calls[0].args = {}

        await service._handle_tool_call(mock_tool_call)

        assert service.session.current_step == 3

    @pytest.mark.asyncio
    async def test_handle_tool_call_advance_step_no_session(self):
        """Test advance_step without session."""
        from fcp.services.cooking_assistant import CookingAssistantService

        service = CookingAssistantService("user123")
        service.session = None

        mock_tool_call = MagicMock()
        mock_tool_call.function_calls = [MagicMock()]
        mock_tool_call.function_calls[0].name = "advance_step"
        mock_tool_call.function_calls[0].args = {}

        result = await service._handle_tool_call(mock_tool_call)

        assert result.response["current_step"] == 1  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_handle_tool_call_log_cooking_note(self):
        """Test handling log_cooking_note function call."""
        from fcp.services.cooking_assistant import CookingAssistantService

        service = CookingAssistantService("user123")

        mock_tool_call = MagicMock()
        mock_tool_call.function_calls = [MagicMock()]
        mock_tool_call.function_calls[0].name = "log_cooking_note"
        mock_tool_call.function_calls[0].args = {
            "note": "Added extra garlic",
            "category": "modification",
        }

        with patch.object(service, "_save_cooking_note", AsyncMock()):
            result = await service._handle_tool_call(mock_tool_call)

            assert result.name == "log_cooking_note"
            assert result.response["status"] == "logged"  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_handle_tool_call_emergency_alert(self):
        """Test handling emergency_alert function call."""
        from fcp.services.cooking_assistant import CookingAssistantService

        service = CookingAssistantService("user123")

        mock_tool_call = MagicMock()
        mock_tool_call.function_calls = [MagicMock()]
        mock_tool_call.function_calls[0].name = "emergency_alert"
        mock_tool_call.function_calls[0].args = {
            "alert_type": "smoke",
            "message": "Smoke detected from pan",
        }

        with patch.object(service, "_trigger_emergency_alert", AsyncMock()):
            result = await service._handle_tool_call(mock_tool_call)

            assert result.name == "emergency_alert"
            assert result.response["status"] == "alert_sent"  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_handle_tool_call_unknown(self):
        """Test handling unknown function call."""
        from fcp.services.cooking_assistant import CookingAssistantService

        service = CookingAssistantService("user123")

        mock_tool_call = MagicMock()
        mock_tool_call.function_calls = [MagicMock()]
        mock_tool_call.function_calls[0].name = "unknown_function"
        mock_tool_call.function_calls[0].args = {}

        result = await service._handle_tool_call(mock_tool_call)

        assert result.response["error"] == "Unknown function"  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_create_timer(self):
        """Test creating a cooking timer."""
        from fcp.services.cooking_assistant import (
            CookingAssistantService,
            CookingSession,
        )

        service = CookingAssistantService("user123")
        service.session = CookingSession(
            recipe_name="Test",
            current_step=1,
            total_steps=5,
            active_timers=[],
            warnings=[],
        )

        timer_id = await service._create_timer(60, "egg timer")

        assert timer_id is not None
        assert len(service.session.active_timers) == 1
        assert service.session.active_timers[0]["label"] == "egg timer"

    @pytest.mark.asyncio
    async def test_create_timer_no_session(self):
        """Test creating timer without session."""
        from fcp.services.cooking_assistant import CookingAssistantService

        service = CookingAssistantService("user123")
        service.session = None

        timer_id = await service._create_timer(60, "timer")

        assert timer_id is not None

    @pytest.mark.asyncio
    async def test_timer_notification(self):
        """Test timer notification logs."""
        from fcp.services.cooking_assistant import CookingAssistantService

        service = CookingAssistantService("user123")

        # Use a very short duration
        with patch("fcp.services.cooking_assistant.logfire") as mock_logfire:
            with patch("asyncio.sleep", AsyncMock()):
                await service._timer_notification("t1", 0, "test")

                mock_logfire.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_cooking_note(self):
        """Test saving cooking note logs."""
        from fcp.services.cooking_assistant import CookingAssistantService

        service = CookingAssistantService("user123")

        with patch("fcp.services.cooking_assistant.logfire") as mock_logfire:
            await service._save_cooking_note("Test note", "tip")

            mock_logfire.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_emergency_alert(self):
        """Test triggering emergency alert logs."""
        from fcp.services.cooking_assistant import CookingAssistantService

        service = CookingAssistantService("user123")

        with patch("fcp.services.cooking_assistant.logfire") as mock_logfire:
            await service._trigger_emergency_alert("fire", "Flames visible!")

            mock_logfire.warn.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_audio_input(self):
        """Test sending audio input."""
        from fcp.services.cooking_assistant import CookingAssistantService

        service = CookingAssistantService("user123")

        mock_session = AsyncMock()

        with patch("fcp.services.cooking_assistant.types"):
            await service.send_audio_input(mock_session, b"audio-data")

            mock_session.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_video_frame(self):
        """Test sending video frame."""
        from fcp.services.cooking_assistant import CookingAssistantService

        service = CookingAssistantService("user123")

        mock_session = AsyncMock()

        with patch("fcp.services.cooking_assistant.types"):
            await service.send_video_frame(mock_session, b"frame-data")

            mock_session.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_cooking_session(self):
        """Test starting a cooking session with Live API."""
        from fcp.services.cooking_assistant import CookingAssistantService

        service = CookingAssistantService("user123")

        recipe = {
            "name": "Pasta Carbonara",
            "ingredients": ["spaghetti", "eggs", "pecorino"],
            "instructions": ["Boil water", "Cook pasta", "Mix sauce"],
        }

        # Create mock response with audio data
        mock_response = MagicMock()
        mock_response.server_content = MagicMock()
        mock_response.server_content.model_turn = MagicMock()
        mock_audio_part = MagicMock()
        mock_audio_part.inline_data = MagicMock()
        mock_audio_part.inline_data.data = b"audio-response-bytes"
        mock_response.server_content.model_turn.parts = [mock_audio_part]
        mock_response.tool_call = None

        # Create mock Live API session
        mock_live_session = AsyncMock()
        mock_live_session.send = AsyncMock()
        mock_live_session.receive = AsyncMock(return_value=[mock_response])

        # Make receive an async iterator
        async def mock_receive():
            yield mock_response

        mock_live_session.receive = mock_receive

        # Mock the client's live.connect
        mock_connect_context = AsyncMock()
        mock_connect_context.__aenter__ = AsyncMock(return_value=mock_live_session)
        mock_connect_context.__aexit__ = AsyncMock(return_value=None)

        with patch("fcp.services.cooking_assistant.logfire"):
            with patch.object(service.client.aio.live, "connect", return_value=mock_connect_context):
                # Collect audio responses
                audio_chunks = []
                async for chunk in service.start_cooking_session(recipe):
                    audio_chunks.append(chunk)

                # Verify session was created
                assert service.session is not None
                assert service.session.recipe_name == "Pasta Carbonara"
                assert service.session.current_step == 1
                assert service.session.total_steps == 3

                # Verify audio was yielded
                assert len(audio_chunks) == 1
                assert audio_chunks[0] == b"audio-response-bytes"

    @pytest.mark.asyncio
    async def test_start_cooking_session_with_tool_call(self):
        """Test cooking session handling tool calls."""
        from fcp.services.cooking_assistant import CookingAssistantService

        service = CookingAssistantService("user123")

        recipe = {
            "name": "Quick Soup",
            "ingredients": ["broth"],
            "instructions": ["Heat broth"],
        }

        # Create mock response with tool call
        mock_tool_response = MagicMock()
        mock_tool_response.server_content = None
        mock_tool_response.tool_call = MagicMock()
        mock_tool_response.tool_call.function_calls = [MagicMock()]
        mock_tool_response.tool_call.function_calls[0].name = "set_timer"
        mock_tool_response.tool_call.function_calls[0].args = {
            "duration_seconds": 60,
            "label": "heat broth",
        }

        # Create mock Live API session
        mock_live_session = AsyncMock()

        async def mock_receive():
            yield mock_tool_response

        mock_live_session.receive = mock_receive
        mock_live_session.send = AsyncMock()

        mock_connect_context = AsyncMock()
        mock_connect_context.__aenter__ = AsyncMock(return_value=mock_live_session)
        mock_connect_context.__aexit__ = AsyncMock(return_value=None)

        with patch("fcp.services.cooking_assistant.logfire"):
            with patch("fcp.services.cooking_assistant.types") as mock_types:
                # Set up mock types for tool response handling
                mock_types.LiveClientContent = MagicMock()
                mock_types.ToolResponse = MagicMock()
                mock_types.FunctionResponse = MagicMock()

                with patch.object(service.client.aio.live, "connect", return_value=mock_connect_context):
                    with patch.object(service, "_create_timer", AsyncMock(return_value="timer123")):
                        # Consume the generator
                        audio_chunks = []
                        async for chunk in service.start_cooking_session(recipe):
                            audio_chunks.append(chunk)

                        # Verify session was created
                        assert service.session is not None

                        # Verify send was called for tool response
                        assert mock_live_session.send.call_count >= 2  # Initial greeting + tool response

    @pytest.mark.asyncio
    async def test_start_cooking_session_no_inline_data(self):
        """Test cooking session with response parts lacking inline_data."""
        from fcp.services.cooking_assistant import CookingAssistantService

        service = CookingAssistantService("user123")

        recipe = {
            "name": "Toast",
            "ingredients": ["bread"],
            "instructions": ["Toast bread"],
        }

        # Create mock response without inline_data
        mock_response = MagicMock()
        mock_response.server_content = MagicMock()
        mock_response.server_content.model_turn = MagicMock()
        mock_text_part = MagicMock(spec=["text"])  # No inline_data attribute
        mock_text_part.text = "Let me guide you"
        mock_text_part.inline_data = None
        mock_response.server_content.model_turn.parts = [mock_text_part]
        mock_response.tool_call = None

        mock_live_session = AsyncMock()

        async def mock_receive():
            yield mock_response

        mock_live_session.receive = mock_receive
        mock_live_session.send = AsyncMock()

        mock_connect_context = AsyncMock()
        mock_connect_context.__aenter__ = AsyncMock(return_value=mock_live_session)
        mock_connect_context.__aexit__ = AsyncMock(return_value=None)

        with patch("fcp.services.cooking_assistant.logfire"):
            with patch.object(service.client.aio.live, "connect", return_value=mock_connect_context):
                audio_chunks = []
                async for chunk in service.start_cooking_session(recipe):
                    audio_chunks.append(chunk)

                # No audio should be yielded since no inline_data
                assert not audio_chunks


# =============================================================================
# Feature 6: Code Execution with Vision Tests
# =============================================================================


class TestPortionAnalyzerService:
    """Tests for portion analysis using code execution."""

    def test_portion_measurement_model(self):
        """Test PortionMeasurement model creation."""
        from fcp.services.portion_analyzer import PortionMeasurement

        measurement = PortionMeasurement(
            item_name="rice",
            estimated_volume_cups=1.0,
            estimated_weight_grams=200,
            bounding_box=(10, 10, 100, 100),
            confidence=0.9,
        )

        assert measurement.item_name == "rice"
        assert measurement.estimated_volume_cups == 1.0
        assert measurement.estimated_weight_grams == 200
        assert measurement.confidence == 0.9

    def test_portion_analysis_result_model(self):
        """Test PortionAnalysisResult model creation."""
        from fcp.services.portion_analyzer import (
            PortionAnalysisResult,
            PortionMeasurement,
        )

        result = PortionAnalysisResult(
            portions=[
                PortionMeasurement(
                    item_name="rice",
                    estimated_volume_cups=1.0,
                    estimated_weight_grams=200,
                    bounding_box=(10, 10, 100, 100),
                    confidence=0.9,
                )
            ],
            annotated_image_base64="base64data",
            total_estimated_calories=200,
            analysis_code="import cv2\n# code",
            reasoning="Analyzed based on visual inspection",
        )

        assert len(result.portions) == 1
        assert result.total_estimated_calories == 200
        assert "cv2" in result.analysis_code

    def test_build_analysis_prompt_with_reference(self):
        """Test prompt includes reference object."""
        from fcp.services.portion_analyzer import PortionAnalyzerService

        service = PortionAnalyzerService()
        prompt = service._build_analysis_prompt("standard fork")

        assert "standard fork" in prompt
        assert "size reference" in prompt

    def test_build_analysis_prompt_without_reference(self):
        """Test prompt without reference object."""
        from fcp.services.portion_analyzer import PortionAnalyzerService

        service = PortionAnalyzerService()
        prompt = service._build_analysis_prompt(None)

        # Should not contain the specific reference hint when none provided
        # The phrase "Use the X in the image as a size reference" should not be present
        assert "as a size reference" not in prompt

    @pytest.mark.asyncio
    async def test_analyze_portions_success(self):
        """Test successful portion analysis."""
        from fcp.services.portion_analyzer import PortionAnalyzerService

        # Mock response with code execution result
        # Use spec to control which attributes exist on each part
        mock_code_part = MagicMock(spec=["executable_code"])
        mock_code_part.executable_code = MagicMock()
        mock_code_part.executable_code.code = "import cv2\nprint('hello')"

        mock_result_part = MagicMock(spec=["code_execution_result"])
        mock_result_part.code_execution_result = MagicMock()
        mock_result_part.code_execution_result.output = json.dumps(
            {
                "portions": [
                    {
                        "item_name": "rice",
                        "estimated_volume_cups": 1.0,
                        "estimated_weight_grams": 200,
                        "bounding_box": [0, 0, 100, 100],
                        "confidence": 0.9,
                    }
                ],
                "total_estimated_calories": 200,
                "reasoning": "Analyzed",
            }
        )

        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_code_part, mock_result_part]

        with patch("fcp.services.portion_analyzer.types") as mock_types:
            mock_types.Part.from_uri.return_value = MagicMock()
            mock_types.Part.return_value = MagicMock()
            mock_types.GenerateContentConfig.return_value = MagicMock()
            mock_types.Tool.return_value = MagicMock()
            mock_types.ThinkingConfig.return_value = MagicMock()

            service = PortionAnalyzerService()
            service.client = MagicMock()
            service.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await service.analyze_portions("gs://bucket/image.jpg")

            assert len(result.portions) == 1
            assert result.portions[0].item_name == "rice"

    @pytest.mark.asyncio
    async def test_analyze_portions_with_text_reasoning(self):
        """Test portion analysis with text reasoning."""
        from fcp.services.portion_analyzer import PortionAnalyzerService

        mock_text_part = MagicMock()
        mock_text_part.text = "Additional reasoning here"
        mock_text_part.executable_code = None
        mock_text_part.code_execution_result = None

        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_text_part]

        with patch("fcp.services.portion_analyzer.types") as mock_types:
            mock_types.Part.from_uri.return_value = MagicMock()
            mock_types.Part.return_value = MagicMock()
            mock_types.GenerateContentConfig.return_value = MagicMock()
            mock_types.Tool.return_value = MagicMock()
            mock_types.ThinkingConfig.return_value = MagicMock()

            service = PortionAnalyzerService()
            service.client = MagicMock()
            service.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await service.analyze_portions("gs://bucket/image.jpg")

            assert "Additional reasoning" in result.reasoning

    @pytest.mark.asyncio
    async def test_analyze_portions_invalid_json(self):
        """Test portion analysis with invalid JSON."""
        from fcp.services.portion_analyzer import PortionAnalyzerService

        mock_result_part = MagicMock()
        mock_result_part.executable_code = None
        mock_result_part.code_execution_result = MagicMock()
        mock_result_part.code_execution_result.output = "Not valid JSON"
        mock_result_part.text = None

        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_result_part]

        with patch("fcp.services.portion_analyzer.types") as mock_types:
            mock_types.Part.from_uri.return_value = MagicMock()
            mock_types.Part.return_value = MagicMock()
            mock_types.GenerateContentConfig.return_value = MagicMock()
            mock_types.Tool.return_value = MagicMock()
            mock_types.ThinkingConfig.return_value = MagicMock()

            service = PortionAnalyzerService()
            service.client = MagicMock()
            service.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await service.analyze_portions("gs://bucket/image.jpg")

            # Should handle gracefully
            assert "Not valid JSON" in result.reasoning

    @pytest.mark.asyncio
    async def test_compare_portions_success(self):
        """Test successful portion comparison."""
        from fcp.services.portion_analyzer import PortionAnalyzerService

        mock_result_part = MagicMock()
        mock_result_part.code_execution_result = MagicMock()
        mock_result_part.code_execution_result.output = json.dumps(
            {
                "consumed_items": [{"name": "rice", "portion_eaten": 0.75}],
                "total_calories_consumed": 150,
                "leftovers": [],
            }
        )

        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_result_part]

        with patch("fcp.services.portion_analyzer.types") as mock_types:
            mock_types.Part.from_uri.return_value = MagicMock()
            mock_types.Part.return_value = MagicMock()
            mock_types.GenerateContentConfig.return_value = MagicMock()
            mock_types.Tool.return_value = MagicMock()
            mock_types.ThinkingConfig.return_value = MagicMock()

            service = PortionAnalyzerService()
            service.client = MagicMock()
            service.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await service.compare_portions("gs://before.jpg", "gs://after.jpg")

            assert result["total_calories_consumed"] == 150
            assert len(result["consumed_items"]) == 1

    @pytest.mark.asyncio
    async def test_compare_portions_invalid_json(self):
        """Test portion comparison with invalid JSON."""
        from fcp.services.portion_analyzer import PortionAnalyzerService

        mock_result_part = MagicMock()
        mock_result_part.code_execution_result = MagicMock()
        mock_result_part.code_execution_result.output = "Invalid JSON"

        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_result_part]

        with patch("fcp.services.portion_analyzer.types") as mock_types:
            mock_types.Part.from_uri.return_value = MagicMock()
            mock_types.Part.return_value = MagicMock()
            mock_types.GenerateContentConfig.return_value = MagicMock()
            mock_types.Tool.return_value = MagicMock()
            mock_types.ThinkingConfig.return_value = MagicMock()

            service = PortionAnalyzerService()
            service.client = MagicMock()
            service.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await service.compare_portions("gs://before.jpg", "gs://after.jpg")

            assert result["consumed_items"] == []
            assert result["total_calories_consumed"] == 0

    @pytest.mark.asyncio
    async def test_compare_portions_no_result(self):
        """Test portion comparison with no code result."""
        from fcp.services.portion_analyzer import PortionAnalyzerService

        mock_part = MagicMock()
        mock_part.code_execution_result = None

        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]

        with patch("fcp.services.portion_analyzer.types") as mock_types:
            mock_types.Part.from_uri.return_value = MagicMock()
            mock_types.Part.return_value = MagicMock()
            mock_types.GenerateContentConfig.return_value = MagicMock()
            mock_types.Tool.return_value = MagicMock()
            mock_types.ThinkingConfig.return_value = MagicMock()

            service = PortionAnalyzerService()
            service.client = MagicMock()
            service.client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await service.compare_portions("gs://before.jpg", "gs://after.jpg")

            assert result["consumed_items"] == []


# =============================================================================
# Feature 7: Media Resolution Control Tests
# =============================================================================


class TestMediaResolution:
    """Tests for media resolution optimization."""

    def test_get_optimal_resolution_food_detection(self):
        """Test low resolution for food detection."""
        from fcp.services.media_resolution import (
            MediaTask,
            get_optimal_resolution,
        )

        assert get_optimal_resolution(MediaTask.FOOD_DETECTION) == "low"

    def test_get_optimal_resolution_basic_analysis(self):
        """Test medium resolution for basic analysis."""
        from fcp.services.media_resolution import (
            MediaTask,
            get_optimal_resolution,
        )

        assert get_optimal_resolution(MediaTask.BASIC_ANALYSIS) == "medium"

    def test_get_optimal_resolution_detailed_analysis(self):
        """Test high resolution for detailed analysis."""
        from fcp.services.media_resolution import (
            MediaTask,
            get_optimal_resolution,
        )

        assert get_optimal_resolution(MediaTask.DETAILED_ANALYSIS) == "high"

    def test_get_optimal_resolution_receipt_ocr(self):
        """Test ultra high resolution for OCR."""
        from fcp.services.media_resolution import (
            MediaTask,
            get_optimal_resolution,
        )

        assert get_optimal_resolution(MediaTask.RECEIPT_OCR) == "ultra_high"

    def test_get_optimal_resolution_cuisine(self):
        """Test low resolution for cuisine classification."""
        from fcp.services.media_resolution import (
            MediaTask,
            get_optimal_resolution,
        )

        assert get_optimal_resolution(MediaTask.CUISINE_CLASSIFICATION) == "low"

    def test_get_optimal_resolution_ingredient_extraction(self):
        """Test high resolution for ingredient extraction."""
        from fcp.services.media_resolution import (
            MediaTask,
            get_optimal_resolution,
        )

        assert get_optimal_resolution(MediaTask.INGREDIENT_EXTRACTION) == "high"

    def test_get_optimal_resolution_portion_analysis(self):
        """Test ultra high resolution for portion analysis."""
        from fcp.services.media_resolution import (
            MediaTask,
            get_optimal_resolution,
        )

        assert get_optimal_resolution(MediaTask.PORTION_ANALYSIS) == "ultra_high"

    def test_estimate_token_savings_low_res(self):
        """Test token savings for low resolution tasks."""
        from fcp.services.media_resolution import (
            MediaTask,
            estimate_token_savings,
        )

        tokens_saved, percentage = estimate_token_savings(MediaTask.FOOD_DETECTION)

        assert tokens_saved > 0
        assert percentage > 0

    def test_estimate_token_savings_high_res(self):
        """Test token savings for high resolution tasks."""
        from fcp.services.media_resolution import (
            MediaTask,
            estimate_token_savings,
        )

        tokens_saved, percentage = estimate_token_savings(MediaTask.DETAILED_ANALYSIS)

        # High res matches baseline, so no savings
        assert tokens_saved == 0
        assert percentage == 0.0

    def test_estimate_token_savings_ultra_high(self):
        """Test token savings for ultra high resolution tasks."""
        from fcp.services.media_resolution import (
            MediaTask,
            estimate_token_savings,
        )

        tokens_saved, percentage = estimate_token_savings(MediaTask.RECEIPT_OCR)

        # Ultra high uses more than baseline, negative savings
        assert tokens_saved < 0

    def test_get_resolution_for_operation_food_detection(self):
        """Test resolution for food detection operation strings."""
        from fcp.services.media_resolution import get_resolution_for_operation

        assert get_resolution_for_operation("is_food") == "low"
        assert get_resolution_for_operation("food_detection") == "low"

    def test_get_resolution_for_operation_cuisine(self):
        """Test resolution for cuisine operation strings."""
        from fcp.services.media_resolution import get_resolution_for_operation

        assert get_resolution_for_operation("cuisine") == "low"
        assert get_resolution_for_operation("cuisine_classification") == "low"

    def test_get_resolution_for_operation_analysis(self):
        """Test resolution for analysis operation strings."""
        from fcp.services.media_resolution import get_resolution_for_operation

        assert get_resolution_for_operation("quick_analysis") == "medium"
        assert get_resolution_for_operation("basic_analysis") == "medium"
        assert get_resolution_for_operation("analyze") == "high"
        assert get_resolution_for_operation("detailed_analysis") == "high"

    def test_get_resolution_for_operation_ingredients(self):
        """Test resolution for ingredients operation strings."""
        from fcp.services.media_resolution import get_resolution_for_operation

        assert get_resolution_for_operation("ingredients") == "high"
        assert get_resolution_for_operation("ingredient_extraction") == "high"

    def test_get_resolution_for_operation_receipt(self):
        """Test resolution for receipt operation strings."""
        from fcp.services.media_resolution import get_resolution_for_operation

        assert get_resolution_for_operation("receipt") == "ultra_high"
        assert get_resolution_for_operation("receipt_ocr") == "ultra_high"

    def test_get_resolution_for_operation_portions(self):
        """Test resolution for portions operation strings."""
        from fcp.services.media_resolution import get_resolution_for_operation

        assert get_resolution_for_operation("portions") == "ultra_high"
        assert get_resolution_for_operation("portion_analysis") == "ultra_high"

    def test_get_resolution_for_operation_unknown(self):
        """Test resolution for unknown operation strings."""
        from fcp.services.media_resolution import get_resolution_for_operation

        assert get_resolution_for_operation("unknown_operation") == "medium"
        assert get_resolution_for_operation("UNKNOWN") == "medium"

    def test_get_resolution_for_operation_case_insensitive(self):
        """Test operation resolution is case insensitive."""
        from fcp.services.media_resolution import get_resolution_for_operation

        assert get_resolution_for_operation("FOOD_DETECTION") == "low"
        assert get_resolution_for_operation("Food_Detection") == "low"


class TestMediaTaskEnum:
    """Tests for MediaTask enumeration."""

    def test_all_media_task_values(self):
        """Test all MediaTask enum values."""
        from fcp.services.media_resolution import MediaTask

        assert MediaTask.FOOD_DETECTION.value == "food_detection"
        assert MediaTask.CUISINE_CLASSIFICATION.value == "cuisine"
        assert MediaTask.BASIC_ANALYSIS.value == "basic_analysis"
        assert MediaTask.DETAILED_ANALYSIS.value == "detailed_analysis"
        assert MediaTask.INGREDIENT_EXTRACTION.value == "ingredients"
        assert MediaTask.RECEIPT_OCR.value == "receipt_ocr"
        assert MediaTask.PORTION_ANALYSIS.value == "portion_analysis"


# =============================================================================
# Feature 8: Grounding + Structured Outputs Tests
# =============================================================================


class TestLiveRestaurantData:
    """Tests for grounded structured restaurant data."""

    @pytest.mark.asyncio
    async def test_get_live_restaurant_data(self):
        """Test fetching live restaurant data with grounding."""
        from fcp.services.live_restaurant_data import (
            get_live_restaurant_data,
        )

        mock_response = MagicMock()
        mock_response.text = """{
            "name": "Joe's Pizza",
            "current_rating": 4.5,
            "review_count": 1234,
            "is_currently_open": true,
            "current_wait_time": "15 minutes",
            "recent_reviews": ["Great pizza!", "Loved it"],
            "popular_dishes": ["Margherita", "Pepperoni"],
            "price_range": "$$",
            "last_updated": "2026-02-03T12:00:00Z"
        }"""

        with patch("fcp.services.live_restaurant_data.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await get_live_restaurant_data(
                restaurant_name="Joe's Pizza",
                location="New York, NY",
            )

            assert result.name == "Joe's Pizza"
            assert result.current_rating == 4.5
            assert result.is_currently_open is True
            assert len(result.recent_reviews) == 2

    @pytest.mark.asyncio
    async def test_check_food_recalls_success(self):
        """Test checking food recalls."""
        from fcp.services.live_restaurant_data import check_food_recalls

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            [
                {
                    "product_name": "Lettuce",
                    "brand": "Fresh Farms",
                    "recall_reason": "E. coli",
                    "affected_regions": ["CA", "AZ"],
                    "recall_date": "2026-02-01",
                    "severity": "Class I",
                    "source_url": "https://fda.gov/recall/123",
                }
            ]
        )

        with patch("fcp.services.live_restaurant_data.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await check_food_recalls("lettuce", "Fresh Farms")

            assert len(result) == 1
            assert result[0].product_name == "Lettuce"
            assert result[0].severity == "Class I"

    @pytest.mark.asyncio
    async def test_check_food_recalls_no_brand(self):
        """Test checking food recalls without brand."""
        from fcp.services.live_restaurant_data import check_food_recalls

        mock_response = MagicMock()
        mock_response.text = "[]"

        with patch("fcp.services.live_restaurant_data.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await check_food_recalls("chicken")

            assert result == []

    @pytest.mark.asyncio
    async def test_check_food_recalls_invalid_json(self):
        """Test checking food recalls with invalid JSON."""
        from fcp.services.live_restaurant_data import check_food_recalls

        mock_response = MagicMock()
        mock_response.text = "Not JSON"

        with patch("fcp.services.live_restaurant_data.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await check_food_recalls("beef")

            assert result == []

    @pytest.mark.asyncio
    async def test_check_food_recalls_non_list(self):
        """Test checking food recalls with non-list response."""
        from fcp.services.live_restaurant_data import check_food_recalls

        mock_response = MagicMock()
        mock_response.text = '{"message": "No recalls found"}'

        with patch("fcp.services.live_restaurant_data.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await check_food_recalls("pork")

            assert result == []

    @pytest.mark.asyncio
    async def test_get_ingredient_prices_success(self):
        """Test getting ingredient prices."""
        from fcp.services.live_restaurant_data import get_ingredient_prices

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            [
                {
                    "ingredient_name": "eggs",
                    "average_price": 4.99,
                    "unit": "dozen",
                    "price_range": [3.99, 5.99],
                    "trending": "up",
                }
            ]
        )

        with patch("fcp.services.live_restaurant_data.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await get_ingredient_prices(["eggs", "milk"], "San Francisco")

            assert "eggs" in result
            assert result["eggs"].average_price == 4.99

    @pytest.mark.asyncio
    async def test_get_ingredient_prices_dict_response(self):
        """Test getting ingredient prices with dict response."""
        from fcp.services.live_restaurant_data import get_ingredient_prices

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "ingredient_name": "milk",
                "average_price": 3.49,
                "unit": "gallon",
                "price_range": [2.99, 3.99],
                "trending": "stable",
            }
        )

        with patch("fcp.services.live_restaurant_data.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await get_ingredient_prices(["milk"], "Denver")

            assert "milk" in result

    @pytest.mark.asyncio
    async def test_get_ingredient_prices_invalid_json(self):
        """Test getting ingredient prices with invalid JSON."""
        from fcp.services.live_restaurant_data import get_ingredient_prices

        mock_response = MagicMock()
        mock_response.text = "Not JSON"

        with patch("fcp.services.live_restaurant_data.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await get_ingredient_prices(["bread"], "NYC")

            assert result == {}

    @pytest.mark.asyncio
    async def test_get_ingredient_prices_no_ingredient_name(self):
        """Test getting ingredient prices with missing ingredient_name."""
        from fcp.services.live_restaurant_data import get_ingredient_prices

        mock_response = MagicMock()
        mock_response.text = json.dumps([{"other_field": "value"}])

        with patch("fcp.services.live_restaurant_data.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await get_ingredient_prices(["butter"], "Boston")

            assert result == {}

    @pytest.mark.asyncio
    async def test_get_restaurant_recommendations_success(self):
        """Test getting restaurant recommendations."""
        from fcp.services.live_restaurant_data import get_restaurant_recommendations

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            [
                {"name": "Sushi Place", "rating": 4.8},
                {"name": "Ramen Shop", "rating": 4.5},
            ]
        )

        with patch("fcp.services.live_restaurant_data.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await get_restaurant_recommendations("Japanese", "Seattle")

            assert len(result) == 2
            assert result[0]["name"] == "Sushi Place"

    @pytest.mark.asyncio
    async def test_get_restaurant_recommendations_with_occasion(self):
        """Test getting restaurant recommendations with occasion."""
        from fcp.services.live_restaurant_data import get_restaurant_recommendations

        mock_response = MagicMock()
        mock_response.text = json.dumps([{"name": "Fancy Italian"}])

        with patch("fcp.services.live_restaurant_data.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await get_restaurant_recommendations(
                "Italian",
                "Portland",
                occasion="date night",
            )

            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_restaurant_recommendations_with_price_range(self):
        """Test getting restaurant recommendations with price range."""
        from fcp.services.live_restaurant_data import get_restaurant_recommendations

        mock_response = MagicMock()
        mock_response.text = json.dumps([{"name": "Budget Thai"}])

        with patch("fcp.services.live_restaurant_data.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await get_restaurant_recommendations(
                "Thai",
                "Austin",
                price_range="$",
            )

            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_restaurant_recommendations_single_result(self):
        """Test getting restaurant recommendations with single dict result."""
        from fcp.services.live_restaurant_data import get_restaurant_recommendations

        mock_response = MagicMock()
        mock_response.text = json.dumps({"name": "Solo Restaurant"})

        with patch("fcp.services.live_restaurant_data.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await get_restaurant_recommendations("French", "Miami")

            assert len(result) == 1
            assert result[0]["name"] == "Solo Restaurant"

    @pytest.mark.asyncio
    async def test_get_restaurant_recommendations_invalid_json(self):
        """Test getting restaurant recommendations with invalid JSON."""
        from fcp.services.live_restaurant_data import get_restaurant_recommendations

        mock_response = MagicMock()
        mock_response.text = "Not JSON"

        with patch("fcp.services.live_restaurant_data.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

            result = await get_restaurant_recommendations("Mexican", "Chicago")

            assert result == []


class TestLiveRestaurantDataModels:
    """Tests for live restaurant data Pydantic models."""

    def test_restaurant_live_data_model(self):
        """Test RestaurantLiveData model."""
        from fcp.services.live_restaurant_data import RestaurantLiveData

        data = RestaurantLiveData(
            name="Test Restaurant",
            current_rating=4.5,
            review_count=100,
            is_currently_open=True,
            current_wait_time="10 min",
            recent_reviews=["Great!"],
            popular_dishes=["Burger"],
            price_range="$$",
            last_updated="2026-02-03",
        )

        assert data.name == "Test Restaurant"
        assert data.current_rating == 4.5

    def test_food_recall_alert_model(self):
        """Test FoodRecallAlert model."""
        from fcp.services.live_restaurant_data import FoodRecallAlert

        alert = FoodRecallAlert(
            product_name="Spinach",
            brand="Green Farms",
            recall_reason="Listeria",
            affected_regions=["CA"],
            recall_date="2026-01-15",
            severity="Class I",
            source_url="https://example.com",
        )

        assert alert.product_name == "Spinach"
        assert alert.severity == "Class I"

    def test_ingredient_price_model(self):
        """Test IngredientPrice model."""
        from fcp.services.live_restaurant_data import IngredientPrice

        price = IngredientPrice(
            ingredient_name="Olive Oil",
            average_price=12.99,
            unit="liter",
            price_range=(10.99, 14.99),
            trending="up",
        )

        assert price.ingredient_name == "Olive Oil"
        assert price.average_price == 12.99


# =============================================================================
# Fake Client Extension Tests
# =============================================================================


class TestFakeGeminiClientWithSignatures:
    """Tests for extended fake client with thought signatures."""

    def test_generate_thought_signature(self):
        """Test fake signature generation."""
        from tests.fakes.fake_gemini import FakeGeminiClientWithSignatures  # sourcery skip: dont-import-test-modules

        client = FakeGeminiClientWithSignatures()

        sig1 = client._generate_thought_signature()
        sig2 = client._generate_thought_signature()

        assert sig1 != sig2
        assert "fake_thought_sig" in sig1

    @pytest.mark.asyncio
    async def test_generate_with_tools_and_signatures(self):
        """Test tool generation includes signatures."""
        from tests.fakes.fake_gemini import FakeGeminiClientWithSignatures  # sourcery skip: dont-import-test-modules

        client = FakeGeminiClientWithSignatures(function_calls=[{"name": "test_func", "args": {}}])

        result = await client.generate_with_tools_and_signatures(
            contents=[],
            tools=[],
        )

        assert "function_calls" in result
        assert len(result["function_calls"]) == 1
        assert "thought_signature" in result["function_calls"][0]


# =============================================================================
# Integration Tests
# =============================================================================


class TestGemini3FeatureIntegration:
    """Integration tests for Gemini 3 features working together."""

    @pytest.mark.asyncio
    async def test_meal_planning_with_image_generation(self):
        """Test meal planning that generates images for each meal."""
        # This would test the full flow:
        # 1. Start meal planning session
        # 2. Generate meal plan with thought signatures
        # 3. For each meal, generate a food image
        # 4. Return complete plan with images

        # Implementation would involve mocking multiple services
        pass

    @pytest.mark.asyncio
    async def test_recipe_import_with_portion_analysis(self):
        """Test importing a recipe and analyzing portion sizes."""
        # This would test:
        # 1. Use Computer Use to import recipe from URL
        # 2. Generate a sample food image
        # 3. Analyze portions using code execution
        pass

    @pytest.mark.asyncio
    async def test_cooking_assistant_with_live_data(self):
        """Test cooking assistant with real-time restaurant data."""
        # This would test:
        # 1. Start cooking session
        # 2. User asks about ingredient substitution
        # 3. System uses grounding to find alternatives
        # 4. Returns structured data
        pass
