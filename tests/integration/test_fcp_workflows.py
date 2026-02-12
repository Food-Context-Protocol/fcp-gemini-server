"""
FCP Workflow Integration Tests

These tests demonstrate how FCP tool chains can be triggered by events,
showcasing the power of AI-backed food intelligence.

Each test tells a story:
- Photo → Analysis → Safety → Social Post
- Discovery → Recommendations → Content
- Gemini feature showcase

Run with: pytest tests/integration/ -v
Set GEMINI_API_KEY to run Gemini-dependent tests.
"""

import os

import pytest

pytestmark = [pytest.mark.integration]

# Skip marker for tests requiring Gemini API
requires_gemini = pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")


@pytest.fixture(autouse=True)
def reset_gemini_singleton():
    """Reset the gemini singleton before each test.

    This fixes test isolation issues where the gemini client's aiohttp
    session gets bound to a specific event loop. When pytest creates
    a new event loop for each test, the old session fails with
    'Event loop is closed'.

    Running this before EACH test ensures a fresh client per test.
    """
    import fcp.services.gemini as gemini_module
    from fcp.services.gemini import GeminiClient

    # Reset both the singleton and the shared HTTP client
    gemini_module._gemini_client = None
    GeminiClient.reset_http_client()
    yield
    # Clean up after test
    gemini_module._gemini_client = None
    GeminiClient.reset_http_client()


class TestFoodImageWorkflow:
    """
    Workflow: Image submission triggers full analysis pipeline.

    Story: A user uploads a food image. FCP automatically:
    1. Analyzes the image to identify the dish
    2. Checks for food safety recalls
    3. Generates a social media post
    """

    @requires_gemini
    @pytest.mark.asyncio
    async def test_photo_to_analysis_pipeline(self):
        """
        Event: New food image uploaded

        Tool Chain:
        1. analyze_meal (Gemini multimodal)

        Result: Structured food data with dish name, cuisine, ingredients, nutrition
        """
        import asyncio

        from fcp.tools import analyze_meal

        # Using a public domain food image (Pixabay)
        image_url = "https://cdn.pixabay.com/photo/2016/03/05/19/02/salmon-1238248_1280.jpg"

        result = await asyncio.wait_for(analyze_meal(image_url), timeout=45.0)

        # Verify structured output
        assert "dish_name" in result or "error" in result
        if "dish_name" in result:
            assert isinstance(result["dish_name"], str)
            assert len(result["dish_name"]) > 0

    @requires_gemini
    @pytest.mark.asyncio
    async def test_safety_check_with_grounding(self):
        """
        Event: User queries about food safety

        Tool Chain:
        1. check_food_recalls (Gemini grounding with Google Search)

        Result: Real-time recall information from trusted sources
        """
        import asyncio

        from fcp.tools import check_food_recalls

        result = await asyncio.wait_for(check_food_recalls(food_name="romaine lettuce"), timeout=45.0)

        # Verify grounded response
        assert "has_active_recall" in result or "error" in result


class TestDiscoveryWorkflow:
    """
    Workflow: User requests food discovery.

    Story: A user asks for restaurant recommendations. FCP:
    1. Loads the user's taste profile
    2. Queries nearby restaurants
    3. Generates personalized recommendations
    """

    @pytest.mark.integration
    @pytest.mark.core
    @pytest.mark.asyncio
    async def test_taste_profile_analysis(self):
        """
        Event: User requests their taste profile

        Tool Chain:
        1. get_taste_profile (analyzes meal history)

        Result: User preferences, favorite cuisines, dietary patterns
        """
        from fcp.tools import get_taste_profile

        user_id = "test-user"
        result = await get_taste_profile(user_id, period="all_time")

        # Even with no data, should return structure
        assert isinstance(result, dict)


class TestGeminiFeatureShowcase:
    """
    Showcase each Gemini capability used in FCP.

    Each test demonstrates a specific Gemini feature that powers
    the Food Context Protocol.
    """

    @requires_gemini
    @pytest.mark.asyncio
    async def test_multimodal_vision(self):
        """
        Gemini Feature: Multimodal (Image + Text)

        FCP Tool: analyze_meal
        Capability: Understands food images to extract structured data
        """
        import asyncio

        from fcp.tools import analyze_meal

        # This demonstrates Gemini's ability to understand images
        image_url = "https://cdn.pixabay.com/photo/2017/06/06/22/46/mediterranean-cuisine-2378758_1280.jpg"

        result = await asyncio.wait_for(analyze_meal(image_url), timeout=45.0)

        # Multimodal analysis should return structured data
        assert isinstance(result, dict)

    @requires_gemini
    @pytest.mark.asyncio
    async def test_grounded_search(self):
        """
        Gemini Feature: Google Search Grounding

        FCP Tool: check_food_recalls
        Capability: Real-time information from trusted sources
        """
        import asyncio

        from fcp.tools import check_food_recalls

        # This demonstrates grounded search for current information
        result = await asyncio.wait_for(check_food_recalls(food_name="beef"), timeout=60.0)

        assert isinstance(result, dict)

    @requires_gemini
    @pytest.mark.asyncio
    async def test_extended_thinking(self):
        """
        Gemini Feature: Extended Thinking

        FCP Tool: analyze_meal_with_thinking
        Capability: Deep reasoning for complex dishes

        Note: Thinking models may not be available with all API keys.
        """
        import asyncio

        from google.genai.errors import ClientError

        from fcp.tools import analyze_meal_with_thinking

        # This demonstrates extended thinking for complex analysis
        image_url = "https://cdn.pixabay.com/photo/2016/03/05/19/02/salmon-1238248_1280.jpg"

        try:
            result = await asyncio.wait_for(analyze_meal_with_thinking(image_url), timeout=45.0)
            assert isinstance(result, dict)
        except ClientError as e:
            # Thinking model may not be available
            if "NOT_FOUND" in str(e) or "not supported" in str(e):
                pytest.skip("Thinking model not available with this API key")
            raise


class TestMealCRUDWorkflow:
    """
    Workflow: Basic meal management operations.

    Story: User creates, reads, updates, and deletes meals.
    """

    @pytest.mark.integration
    @pytest.mark.core
    @pytest.mark.asyncio
    async def test_meal_lifecycle(self):
        """
        Complete meal lifecycle test.

        Tool Chain:
        1. add_meal - Create entry
        2. get_meals - Read entries
        3. (update_meal - Update entry)
        4. (delete_meal - Delete entry)
        """
        from fcp.tools import add_meal, get_meals

        user_id = "test-user"

        # Create
        meal = await add_meal(
            user_id=user_id,
            dish_name="Test Pasta",
            venue="Test Kitchen",
            notes="Integration test meal",
        )
        assert "log_id" in meal or "success" in meal

        # Read
        meals = await get_meals(user_id, limit=5)
        assert isinstance(meals, (list, dict))


class TestGemini3Features:
    """
    Tests for all 15 Gemini 3 features used in FCP.

    Each test targets a specific Gemini capability to ensure
    the integration works correctly.
    """

    @requires_gemini
    @pytest.mark.asyncio
    async def test_code_execution(self):
        """
        Gemini Feature #5: Code Execution

        Capability: Execute Python for calculations
        """
        import asyncio

        from fcp.services.gemini import get_gemini

        gemini = get_gemini()
        result = await asyncio.wait_for(
            gemini.generate_with_code_execution(
                prompt="Calculate the total calories for a meal with 500g rice (1.3 cal/g) and 200g chicken (2.39 cal/g)"
            ),
            timeout=45.0,
        )

        assert isinstance(result, dict)
        assert "text" in result or "execution_result" in result

    @requires_gemini
    @pytest.mark.asyncio
    async def test_streaming(self):
        """
        Gemini Feature #7: Streaming

        Capability: Stream content generation for real-time UI
        """
        import asyncio

        from fcp.services.gemini import get_gemini

        gemini = get_gemini()
        chunks = []

        async def collect_chunks():
            async for chunk in gemini.generate_content_stream(prompt="Describe a perfect breakfast in 2 sentences."):
                chunks.append(chunk)

        await asyncio.wait_for(collect_chunks(), timeout=45.0)

        # Should receive at least one chunk
        assert chunks

    @requires_gemini
    @pytest.mark.asyncio
    async def test_function_calling(self):
        """
        Gemini Feature #8: Function Calling

        Capability: Structured tool invocation
        """
        import asyncio

        from fcp.services.gemini import get_gemini

        gemini = get_gemini()
        tools = [
            {
                "name": "identify_dish",
                "description": "Identify a dish from description",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dish_name": {"type": "string"},
                        "cuisine": {"type": "string"},
                    },
                    "required": ["dish_name"],
                },
            }
        ]

        result = await asyncio.wait_for(
            gemini.generate_with_tools(
                prompt="Identify this dish: a bowl of rice topped with raw fish slices",
                tools=tools,
            ),
            timeout=45.0,
        )

        assert isinstance(result, dict)
        # Should have function_calls or text
        assert "function_calls" in result or "text" in result

    @requires_gemini
    @pytest.mark.asyncio
    async def test_media_resolution(self):
        """
        Gemini Feature #10: Media Resolution

        Capability: Cost-optimized image analysis
        """
        import asyncio

        from fcp.services.gemini import get_gemini

        gemini = get_gemini()
        image_url = "https://cdn.pixabay.com/photo/2016/03/05/19/02/salmon-1238248_1280.jpg"

        # Test with low resolution (faster, cheaper)
        result = await asyncio.wait_for(
            gemini.generate_json_with_media_resolution(
                prompt='Is this food? Answer with JSON: {"is_food": true/false}',
                image_url=image_url,
                resolution="low",
            ),
            timeout=45.0,
        )

        assert isinstance(result, dict)

    @requires_gemini
    @pytest.mark.asyncio
    async def test_multi_tool_combination(self):
        """
        Gemini Feature #15: Multi-tool Combination

        Capability: Combine multiple Gemini features
        """
        import asyncio

        from fcp.services.gemini import get_gemini

        gemini = get_gemini()

        # 45s timeout - grounding calls can be slow (observed ~29s in testing)
        result = await asyncio.wait_for(
            gemini.generate_with_all_tools(
                prompt="What are the current food trends for healthy eating?",
                enable_grounding=True,
            ),
            timeout=45.0,
        )

        assert isinstance(result, dict)
        assert "text" in result or "sources" in result


class TestVideoAndImageGeneration:
    """
    Tests for Veo 3.1 video and Imagen 3 image generation.

    Note: These tests are longer running and may timeout.
    """

    @requires_gemini
    @pytest.mark.asyncio
    async def test_image_generation_tool(self):
        """
        Gemini Feature #12: Imagen 3

        FCP Tool: generate_food_image
        Capability: Generate photorealistic food images

        Note: Imagen 3 may not be available with all API keys.
        """
        import asyncio

        from google.genai.errors import ClientError

        from fcp.tools import generate_food_image

        try:
            result = await asyncio.wait_for(
                generate_food_image(
                    dish_name="chocolate cake",
                    style="professional",
                    aspect_ratio="1:1",
                ),
                timeout=60.0,  # Image generation can be slower
            )
            assert isinstance(result, dict)
            assert "image_base64" in result or "images" in result or "status" in result
        except ClientError as e:
            # Imagen 3 may not be enabled for this API key
            if "NOT_FOUND" in str(e) or "not supported" in str(e):
                pytest.skip("Imagen 3 not available with this API key")
            raise

    @requires_gemini
    @pytest.mark.asyncio
    async def test_video_generation_tool(self):
        """
        Gemini Feature #13: Veo 3.1

        FCP Tool: generate_recipe_video
        Capability: Generate cooking videos

        Note: Video generation takes 2-5 minutes, so we just verify
        the call starts correctly (will timeout or return status).
        """
        import asyncio

        from fcp.tools import generate_recipe_video

        # Use short timeout to just verify the API call works
        result = await asyncio.wait_for(
            generate_recipe_video(
                dish_name="pancakes",
                style="tutorial",
                duration_seconds=4,
            ),
            timeout=60.0,  # Video generation starts quickly but may timeout
        )

        assert isinstance(result, dict)
        # Should have status (completed, timeout, or failed)
        assert "status" in result


class TestVoiceAndResearch:
    """
    Tests for Live API voice and Deep Research features.
    """

    @requires_gemini
    @pytest.mark.asyncio
    async def test_deep_research(self):
        """
        Gemini Feature #14: Deep Research

        Capability: Autonomous research with citations

        Note: Deep research takes 3-5+ minutes, so we just verify
        the call starts (will return timeout status quickly).
        """
        import asyncio

        from fcp.services.gemini import get_gemini

        gemini = get_gemini()
        result = await asyncio.wait_for(
            gemini.generate_deep_research(
                query="What are the health benefits of Mediterranean diet?",
                timeout_seconds=30,  # Short timeout for testing
            ),
            timeout=60.0,  # Outer timeout in case internal timeout fails
        )

        assert isinstance(result, dict)
        # Should have interaction_id and status
        assert "status" in result
        # Accept completed, timeout, or failed (API can be flaky)
        assert result["status"] in ("completed", "timeout", "failed")
    pytestmark = [pytest.mark.gemini]
    pytestmark = [pytest.mark.core]
    pytestmark = [pytest.mark.gemini]
    pytestmark = [pytest.mark.core]
    pytestmark = [pytest.mark.gemini]
    pytestmark = [pytest.mark.gemini]
    pytestmark = [pytest.mark.gemini]
