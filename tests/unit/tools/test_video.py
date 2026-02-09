"""Tests for video generation tool and routes."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fcp.tools.video import (
    STYLE_PROMPTS,
    generate_cooking_clip,
    generate_recipe_video,
)


class TestStylePrompts:
    """Tests for style prompt constants."""

    def test_has_cinematic_style(self):
        """Test cinematic style exists."""
        assert "cinematic" in STYLE_PROMPTS
        assert "shallow depth of field" in STYLE_PROMPTS["cinematic"]

    def test_has_tutorial_style(self):
        """Test tutorial style exists."""
        assert "tutorial" in STYLE_PROMPTS
        assert "step-by-step" in STYLE_PROMPTS["tutorial"]

    def test_has_social_style(self):
        """Test social style exists."""
        assert "social" in STYLE_PROMPTS
        assert "vibrant colors" in STYLE_PROMPTS["social"]

    def test_has_lifestyle_style(self):
        """Test lifestyle style exists."""
        assert "lifestyle" in STYLE_PROMPTS
        assert "cozy atmosphere" in STYLE_PROMPTS["lifestyle"]


class TestGenerateRecipeVideo:
    """Tests for generate_recipe_video function."""

    @pytest.mark.asyncio
    async def test_generates_video_with_defaults(self):
        """Test video generation with default parameters."""
        mock_result = {
            "status": "completed",
            "video_bytes": b"fake_video_data",
            "duration": 8,
        }

        with patch("fcp.tools.video.gemini") as mock_gemini:
            mock_gemini.generate_video = AsyncMock(return_value=mock_result)

            result = await generate_recipe_video(dish_name="Spaghetti Carbonara")

            assert result["status"] == "completed"
            assert result["dish_name"] == "Spaghetti Carbonara"
            assert result["style"] == "cinematic"
            assert result["video_bytes"] == b"fake_video_data"

            # Verify prompt includes dish name and style
            call_args = mock_gemini.generate_video.call_args
            assert "Spaghetti Carbonara" in call_args.kwargs["prompt"]

    @pytest.mark.asyncio
    async def test_generates_video_with_description(self):
        """Test video generation with custom description."""
        mock_result = {"status": "completed", "video_bytes": b"data", "duration": 8}

        with patch("fcp.tools.video.gemini") as mock_gemini:
            mock_gemini.generate_video = AsyncMock(return_value=mock_result)

            await generate_recipe_video(
                dish_name="Pizza",
                description="Close-up of melting cheese",
            )

            call_args = mock_gemini.generate_video.call_args
            prompt = call_args.kwargs["prompt"]
            assert "Pizza" in prompt
            assert "Close-up of melting cheese" in prompt

    @pytest.mark.asyncio
    async def test_generates_video_with_custom_style(self):
        """Test video generation with custom style."""
        mock_result = {"status": "completed", "video_bytes": b"data", "duration": 8}

        with patch("fcp.tools.video.gemini") as mock_gemini:
            mock_gemini.generate_video = AsyncMock(return_value=mock_result)

            result = await generate_recipe_video(
                dish_name="Tacos",
                style="social",
            )

            assert result["style"] == "social"
            call_args = mock_gemini.generate_video.call_args
            prompt = call_args.kwargs["prompt"]
            assert "vibrant colors" in prompt

    @pytest.mark.asyncio
    async def test_generates_video_with_unknown_style_uses_cinematic(self):
        """Test that unknown style falls back to cinematic."""
        mock_result = {"status": "completed", "video_bytes": b"data", "duration": 8}

        with patch("fcp.tools.video.gemini") as mock_gemini:
            mock_gemini.generate_video = AsyncMock(return_value=mock_result)

            result = await generate_recipe_video(
                dish_name="Soup",
                style="unknown_style",
            )

            assert result["style"] == "unknown_style"
            call_args = mock_gemini.generate_video.call_args
            prompt = call_args.kwargs["prompt"]
            # Should use cinematic as fallback
            assert "shallow depth of field" in prompt

    @pytest.mark.asyncio
    async def test_passes_duration_and_aspect_ratio(self):
        """Test that duration and aspect ratio are passed."""
        mock_result = {"status": "completed", "video_bytes": b"data", "duration": 4}

        with patch("fcp.tools.video.gemini") as mock_gemini:
            mock_gemini.generate_video = AsyncMock(return_value=mock_result)

            await generate_recipe_video(
                dish_name="Ramen",
                duration_seconds=4,
                aspect_ratio="9:16",
            )

            call_args = mock_gemini.generate_video.call_args
            assert call_args.kwargs["duration_seconds"] == 4
            assert call_args.kwargs["aspect_ratio"] == "9:16"

    @pytest.mark.asyncio
    async def test_passes_timeout(self):
        """Test that timeout is passed."""
        mock_result = {"status": "completed", "video_bytes": b"data", "duration": 8}

        with patch("fcp.tools.video.gemini") as mock_gemini:
            mock_gemini.generate_video = AsyncMock(return_value=mock_result)

            await generate_recipe_video(
                dish_name="Burger",
                timeout_seconds=600,
            )

            call_args = mock_gemini.generate_video.call_args
            assert call_args.kwargs["timeout_seconds"] == 600

    @pytest.mark.asyncio
    async def test_handles_timeout_status(self):
        """Test handling of timeout status."""
        mock_result = {
            "status": "timeout",
            "operation_name": "op_123",
            "message": "Still generating",
        }

        with patch("fcp.tools.video.gemini") as mock_gemini:
            mock_gemini.generate_video = AsyncMock(return_value=mock_result)

            result = await generate_recipe_video(dish_name="Steak")

            assert result["status"] == "timeout"
            assert result["dish_name"] == "Steak"

    @pytest.mark.asyncio
    async def test_handles_failed_status(self):
        """Test handling of failed status."""
        mock_result = {
            "status": "failed",
            "message": "Generation failed",
        }

        with patch("fcp.tools.video.gemini") as mock_gemini:
            mock_gemini.generate_video = AsyncMock(return_value=mock_result)

            result = await generate_recipe_video(dish_name="Salad")

            assert result["status"] == "failed"
            assert result["dish_name"] == "Salad"


class TestGenerateCookingClip:
    """Tests for generate_cooking_clip function."""

    @pytest.mark.asyncio
    async def test_generates_clip_with_action_only(self):
        """Test clip generation with just an action."""
        mock_result = {
            "status": "completed",
            "video_bytes": b"clip_data",
            "duration": 8,
        }

        with patch("fcp.tools.video.gemini") as mock_gemini:
            mock_gemini.generate_video = AsyncMock(return_value=mock_result)

            result = await generate_cooking_clip(action="chopping vegetables")

            assert result["status"] == "completed"
            assert result["action"] == "chopping vegetables"
            assert result["ingredients"] is None

            call_args = mock_gemini.generate_video.call_args
            prompt = call_args.kwargs["prompt"]
            assert "Close-up of chopping vegetables" in prompt
            assert "Professional kitchen setting" in prompt

    @pytest.mark.asyncio
    async def test_generates_clip_with_ingredients(self):
        """Test clip generation with ingredients."""
        mock_result = {"status": "completed", "video_bytes": b"data", "duration": 8}

        with patch("fcp.tools.video.gemini") as mock_gemini:
            mock_gemini.generate_video = AsyncMock(return_value=mock_result)

            result = await generate_cooking_clip(
                action="sautéing",
                ingredients=["onions", "garlic", "peppers"],
            )

            assert result["action"] == "sautéing"
            assert result["ingredients"] == ["onions", "garlic", "peppers"]

            call_args = mock_gemini.generate_video.call_args
            prompt = call_args.kwargs["prompt"]
            assert "onions" in prompt
            assert "garlic" in prompt
            assert "peppers" in prompt

    @pytest.mark.asyncio
    async def test_limits_ingredients_to_three(self):
        """Test that only first 3 ingredients are used."""
        mock_result = {"status": "completed", "video_bytes": b"data", "duration": 8}

        with patch("fcp.tools.video.gemini") as mock_gemini:
            mock_gemini.generate_video = AsyncMock(return_value=mock_result)

            await generate_cooking_clip(
                action="mixing",
                ingredients=["flour", "sugar", "eggs", "butter", "milk"],
            )

            call_args = mock_gemini.generate_video.call_args
            prompt = call_args.kwargs["prompt"]
            assert "flour" in prompt
            assert "sugar" in prompt
            assert "eggs" in prompt
            assert "butter" not in prompt
            assert "milk" not in prompt

    @pytest.mark.asyncio
    async def test_passes_duration_and_timeout(self):
        """Test that duration and timeout are passed."""
        mock_result = {"status": "completed", "video_bytes": b"data", "duration": 4}

        with patch("fcp.tools.video.gemini") as mock_gemini:
            mock_gemini.generate_video = AsyncMock(return_value=mock_result)

            await generate_cooking_clip(
                action="flipping",
                duration_seconds=4,
                timeout_seconds=180,
            )

            call_args = mock_gemini.generate_video.call_args
            assert call_args.kwargs["duration_seconds"] == 4
            assert call_args.kwargs["timeout_seconds"] == 180
            # Always uses 16:9 for clips
            assert call_args.kwargs["aspect_ratio"] == "16:9"


class TestGenerateVideoGeminiMethod:
    """Tests for the Gemini client generate_video method."""

    @pytest.mark.asyncio
    async def test_generate_video_completed(self):
        """Test successful video generation in Gemini client."""
        from fcp.services.gemini import GeminiClient

        # Create mock video response
        mock_video = MagicMock()
        mock_video.video.video_bytes = b"video_content"

        mock_response = MagicMock()
        mock_response.generated_videos = [mock_video]

        mock_operation = MagicMock()
        mock_operation.done = True
        mock_operation.response = mock_response

        mock_client = MagicMock()
        mock_client.aio.models.generate_videos = AsyncMock(return_value=mock_operation)
        mock_client.aio.models.generate_videos = AsyncMock(return_value=mock_operation)

        client = GeminiClient()
        client.client = mock_client

        result = await client.generate_video(
            prompt="Test video",
            duration_seconds=8,
        )

        assert result["status"] == "completed"
        assert result["video_bytes"] == b"video_content"
        assert result["duration"] == 8

    @pytest.mark.asyncio
    async def test_generate_video_no_response(self):
        """Test video generation with no response."""
        from fcp.services.gemini import GeminiClient

        mock_operation = MagicMock()
        mock_operation.done = True
        mock_operation.response = None

        mock_client = MagicMock()
        mock_client.aio.models.generate_videos = AsyncMock(return_value=mock_operation)
        mock_client.aio.models.generate_videos = AsyncMock(return_value=mock_operation)

        client = GeminiClient()
        client.client = mock_client

        result = await client.generate_video(prompt="Test")

        assert result["status"] == "failed"
        assert "no video returned" in result["message"]

    @pytest.mark.asyncio
    async def test_generate_video_no_client(self):
        """Test error when client not configured."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        client.client = None

        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await client.generate_video(prompt="Test")

    @pytest.mark.asyncio
    async def test_generate_video_timeout(self):
        """Test video generation timeout."""
        from fcp.services.gemini import GeminiClient

        mock_operation = MagicMock()
        mock_operation.done = False
        mock_operation.name = "op-test-123"

        mock_client = MagicMock()
        mock_client.aio.models.generate_videos = AsyncMock(return_value=mock_operation)
        mock_client.aio.operations.get = AsyncMock(return_value=mock_operation)

        client = GeminiClient()
        client.client = mock_client

        # Patch time to simulate timeout
        time_values = [0, 5, 15]
        time_index = [0]

        def mock_time():
            idx = time_index[0]
            time_index[0] += 1
            return time_values[idx] if idx < len(time_values) else 1000

        with patch("fcp.services.gemini.time.monotonic", side_effect=mock_time):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client.generate_video(
                    prompt="Test",
                    timeout_seconds=10,
                )

        assert result["status"] == "timeout"
        assert result["operation_name"] == "op-test-123"

    @pytest.mark.asyncio
    async def test_generate_video_empty_videos_list(self):
        """Test video generation with empty videos list."""
        from fcp.services.gemini import GeminiClient

        mock_response = MagicMock()
        mock_response.generated_videos = []

        mock_operation = MagicMock()
        mock_operation.done = True
        mock_operation.response = mock_response

        mock_client = MagicMock()
        mock_client.aio.models.generate_videos = AsyncMock(return_value=mock_operation)
        mock_client.aio.models.generate_videos = AsyncMock(return_value=mock_operation)

        client = GeminiClient()
        client.client = mock_client

        result = await client.generate_video(prompt="Test")

        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_generate_video_no_video_bytes(self):
        """Test video generation when video object has no bytes."""
        from fcp.services.gemini import GeminiClient

        mock_video = MagicMock()
        mock_video.video = None  # No video attribute

        mock_response = MagicMock()
        mock_response.generated_videos = [mock_video]

        mock_operation = MagicMock()
        mock_operation.done = True
        mock_operation.response = mock_response

        mock_client = MagicMock()
        mock_client.aio.models.generate_videos = AsyncMock(return_value=mock_operation)

        client = GeminiClient()
        client.client = mock_client

        result = await client.generate_video(prompt="Test")

        assert result["status"] == "completed"
        assert result["video_bytes"] is None


class TestVideoRouteValidation:
    """Tests for video route request validation."""

    def test_recipe_video_request_valid(self):
        """Test valid recipe video request."""
        from fcp.routes.video import RecipeVideoRequest

        request = RecipeVideoRequest(dish_name="Pasta")
        assert request.dish_name == "Pasta"
        assert request.style == "cinematic"
        assert request.duration_seconds == 8
        assert request.aspect_ratio == "16:9"

    def test_recipe_video_request_all_fields(self):
        """Test recipe video request with all fields."""
        from fcp.routes.video import RecipeVideoRequest

        request = RecipeVideoRequest(
            dish_name="Sushi",
            description="Rolling technique close-up",
            style="tutorial",
            duration_seconds=4,
            aspect_ratio="9:16",
            timeout_seconds=120,
        )
        assert request.dish_name == "Sushi"
        assert request.description == "Rolling technique close-up"
        assert request.style == "tutorial"
        assert request.duration_seconds == 4
        assert request.aspect_ratio == "9:16"
        assert request.timeout_seconds == 120

    def test_recipe_video_request_duration_bounds(self):
        """Test recipe video request duration bounds."""
        from pydantic import ValidationError

        from fcp.routes.video import RecipeVideoRequest

        # Too short
        with pytest.raises(ValidationError):
            RecipeVideoRequest(dish_name="Dish", duration_seconds=2)

        # Too long
        with pytest.raises(ValidationError):
            RecipeVideoRequest(dish_name="Dish", duration_seconds=10)

    def test_cooking_clip_request_valid(self):
        """Test valid cooking clip request."""
        from fcp.routes.video import CookingClipRequest

        request = CookingClipRequest(action="chopping onions")
        assert request.action == "chopping onions"
        assert request.ingredients is None

    def test_cooking_clip_request_with_ingredients(self):
        """Test cooking clip request with ingredients."""
        from fcp.routes.video import CookingClipRequest

        request = CookingClipRequest(
            action="sautéing",
            ingredients=["garlic", "onion"],
        )
        assert request.action == "sautéing"
        assert request.ingredients == ["garlic", "onion"]


class TestVideoRouterConfig:
    """Tests for video router configuration."""

    def test_video_router_exists(self):
        """Test video router is properly configured."""
        from fcp.routes.video import router

        assert router is not None

    def test_video_routes_registered(self):
        """Test video routes are registered."""
        from fcp.routes.video import router

        routes = [r.path for r in router.routes]
        assert "/video/recipe" in routes
        assert "/video/clip" in routes
        assert "/video/recipe/raw" in routes
