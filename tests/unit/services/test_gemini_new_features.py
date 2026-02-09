"""Tests for new Gemini client features: Deep Research, Veo Video, Live API."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGenerateDeepResearch:
    """Tests for generate_deep_research method."""

    @pytest.mark.asyncio
    async def test_not_configured_raises_error(self):
        """Test that generate_deep_research raises when API not configured."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        client.client = None  # Simulate not configured

        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await client.generate_deep_research("test query")

    @pytest.mark.asyncio
    async def test_completed_research(self):
        """Test successful research completion."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()

        # Mock the client
        mock_genai_client = MagicMock()

        # Mock interaction with completed status
        mock_interaction = MagicMock()
        mock_interaction.id = "int_123"
        mock_interaction.status = "completed"
        mock_output = MagicMock()
        mock_output.text = "Research report about the topic."
        mock_interaction.outputs = [mock_output]

        mock_genai_client.aio.interactions.create = AsyncMock(return_value=mock_interaction)
        mock_genai_client.aio.interactions.get = AsyncMock(return_value=mock_interaction)

        client.client = mock_genai_client

        with patch("asyncio.sleep", new_callable=AsyncMock):  # Don't actually sleep
            result = await client.generate_deep_research("test query", timeout_seconds=1)

        assert result["status"] == "completed"
        assert result["report"] == "Research report about the topic."
        assert result["interaction_id"] == "int_123"

    @pytest.mark.asyncio
    async def test_failed_research(self):
        """Test research that fails."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Mock interaction with failed status
        mock_interaction = MagicMock()
        mock_interaction.id = "int_456"
        mock_interaction.status = "failed"
        mock_interaction.error = "API error occurred"

        mock_genai_client.aio.interactions.create = AsyncMock(return_value=mock_interaction)
        mock_genai_client.aio.interactions.get = AsyncMock(return_value=mock_interaction)

        client.client = mock_genai_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.generate_deep_research("test query", timeout_seconds=1)

        assert result["status"] == "failed"
        assert result["message"] == "API error occurred"
        assert result["interaction_id"] == "int_456"

    @pytest.mark.asyncio
    async def test_research_timeout(self):
        """Test research that times out."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Mock interaction that stays in-progress
        mock_interaction = MagicMock()
        mock_interaction.id = "int_789"
        mock_interaction.status = "in_progress"

        mock_genai_client.aio.interactions.create = AsyncMock(return_value=mock_interaction)
        mock_genai_client.aio.interactions.get = AsyncMock(return_value=mock_interaction)

        client.client = mock_genai_client

        # Use very short timeout
        with patch("asyncio.sleep", new_callable=AsyncMock):  # Don't actually sleep
            with patch("fcp.services.gemini.time.monotonic") as mock_time:
                # Simulate time passing beyond timeout
                time_values = [0, 1, 2]  # Start, check, check again
                time_index = [0]

                def _mock_time():
                    idx = time_index[0]
                    time_index[0] += 1
                    return time_values[idx] if idx < len(time_values) else time_values[-1] + 1000

                mock_time.side_effect = _mock_time
                result = await client.generate_deep_research("test query", timeout_seconds=1)

        assert result["status"] == "timeout"
        assert result["interaction_id"] == "int_789"
        assert "Research still in progress" in result["message"]

    @pytest.mark.asyncio
    async def test_completed_research_empty_outputs(self):
        """Test completed research with no outputs."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_interaction = MagicMock()
        mock_interaction.id = "int_empty"
        mock_interaction.status = "completed"
        mock_interaction.outputs = []  # Empty outputs

        mock_genai_client.aio.interactions.create = AsyncMock(return_value=mock_interaction)
        mock_genai_client.aio.interactions.get = AsyncMock(return_value=mock_interaction)

        client.client = mock_genai_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.generate_deep_research("test query", timeout_seconds=1)

        assert result["status"] == "completed"
        assert result["report"] == ""  # Empty report when no outputs


class TestGenerateVideo:
    """Tests for generate_video method."""

    @pytest.mark.asyncio
    async def test_not_configured_raises_error(self):
        """Test that generate_video raises when API not configured."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        client.client = None

        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await client.generate_video("test prompt")

    @pytest.mark.asyncio
    async def test_completed_video(self):
        """Test successful video generation."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Mock operation with completed status
        mock_video = MagicMock()
        mock_video.video = MagicMock()
        mock_video.video.video_bytes = b"fake_video_bytes"

        mock_response = MagicMock()
        mock_response.generated_videos = [mock_video]

        mock_operation = MagicMock()
        mock_operation.done = True
        mock_operation.response = mock_response

        mock_genai_client.aio.models.generate_videos = AsyncMock(return_value=mock_operation)

        client.client = mock_genai_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.generate_video("test prompt", timeout_seconds=1)

        assert result["status"] == "completed"
        assert result["video_bytes"] == b"fake_video_bytes"
        assert result["duration"] == 8  # Default duration

    @pytest.mark.asyncio
    async def test_video_no_response(self):
        """Test video generation with no response."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Mock operation done but no response
        mock_operation = MagicMock()
        mock_operation.done = True
        mock_operation.response = None

        mock_genai_client.aio.models.generate_videos = AsyncMock(return_value=mock_operation)

        client.client = mock_genai_client

        with patch("asyncio.sleep"):
            result = await client.generate_video("test prompt", timeout_seconds=1)

        assert result["status"] == "failed"
        assert "no video returned" in result["message"]

    @pytest.mark.asyncio
    async def test_video_timeout(self):
        """Test video generation that times out."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Mock operation that never completes
        mock_operation = MagicMock()
        mock_operation.done = False
        mock_operation.name = "op_timeout"

        mock_genai_client.aio.models.generate_videos = AsyncMock(return_value=mock_operation)
        mock_genai_client.aio.operations.get = AsyncMock(return_value=mock_operation)

        client.client = mock_genai_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("fcp.services.gemini.time.monotonic") as mock_time:
                time_values = [0, 1, 2]
                time_index = [0]

                def _mock_time():
                    idx = time_index[0]
                    time_index[0] += 1
                    return time_values[idx] if idx < len(time_values) else time_values[-1] + 1000

                mock_time.side_effect = _mock_time
                result = await client.generate_video("test prompt", timeout_seconds=1)

        assert result["status"] == "timeout"
        assert result["operation_name"] == "op_timeout"
        assert "Video still generating" in result["message"]

    @pytest.mark.asyncio
    async def test_video_with_custom_params(self):
        """Test video generation with custom parameters."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_video = MagicMock()
        mock_video.video = MagicMock()
        mock_video.video.video_bytes = b"data"

        mock_response = MagicMock()
        mock_response.generated_videos = [mock_video]

        mock_operation = MagicMock()
        mock_operation.done = True
        mock_operation.response = mock_response

        mock_genai_client.aio.models.generate_videos = AsyncMock(return_value=mock_operation)

        client.client = mock_genai_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.generate_video(
                "test prompt",
                duration_seconds=4,
                aspect_ratio="9:16",
                timeout_seconds=600,
            )

        assert result["status"] == "completed"
        assert result["duration"] == 4

        # Verify params were passed to API
        call_args = mock_genai_client.aio.models.generate_videos.call_args
        assert call_args.kwargs["prompt"] == "test prompt"

    @pytest.mark.asyncio
    async def test_video_empty_videos_list(self):
        """Test video generation with empty videos list."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_response = MagicMock()
        mock_response.generated_videos = []

        mock_operation = MagicMock()
        mock_operation.done = True
        mock_operation.response = mock_response

        mock_genai_client.aio.models.generate_videos = AsyncMock(return_value=mock_operation)

        client.client = mock_genai_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.generate_video("test prompt", timeout_seconds=1)

        assert result["status"] == "failed"


class TestCreateLiveSession:
    """Tests for create_live_session method."""

    def test_not_configured_raises_error(self):
        """Test that create_live_session raises when API not configured."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        client.client = None

        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            client.create_live_session()

    def test_create_session_with_defaults(self):
        """Test creating live session with default options."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()
        mock_session = MagicMock()
        mock_genai_client.aio.live.connect.return_value = mock_session

        client.client = mock_genai_client

        result = client.create_live_session()

        assert result is mock_session
        mock_genai_client.aio.live.connect.assert_called_once()

    def test_create_session_with_system_instruction(self):
        """Test creating live session with system instruction."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()
        mock_session = MagicMock()
        mock_genai_client.aio.live.connect.return_value = mock_session

        client.client = mock_genai_client

        result = client.create_live_session(
            system_instruction="You are a helpful assistant.",
            enable_food_tools=True,
        )

        assert result is mock_session
        call_args = mock_genai_client.aio.live.connect.call_args
        assert call_args.kwargs["model"] == "gemini-2.0-flash-live-preview-04-09"

    def test_create_session_without_food_tools(self):
        """Test creating live session without food tools."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()
        mock_session = MagicMock()
        mock_genai_client.aio.live.connect.return_value = mock_session

        client.client = mock_genai_client

        result = client.create_live_session(enable_food_tools=False)

        assert result is mock_session


class TestProcessLiveAudio:
    """Tests for process_live_audio method."""

    @pytest.mark.asyncio
    async def test_not_configured_raises_error(self):
        """Test that process_live_audio raises when API not configured."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        client.client = None

        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await client.process_live_audio(b"audio_data")

    @pytest.mark.asyncio
    async def test_process_audio_with_text_response(self):
        """Test processing audio that returns text response."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Create mock session context manager
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.send = AsyncMock()

        # Mock response with text
        mock_part = MagicMock()
        mock_part.text = "I logged your meal."
        mock_part.inline_data = None

        mock_model_turn = MagicMock()
        mock_model_turn.parts = [mock_part]

        mock_content = MagicMock()
        mock_content.model_turn = mock_model_turn

        mock_response = MagicMock()
        mock_response.server_content = mock_content
        mock_response.tool_call = None

        async def mock_receive():
            yield mock_response

        mock_session.receive = mock_receive

        # Mock create_live_session
        with patch.object(client, "create_live_session", return_value=mock_session):
            client.client = mock_genai_client

            result = await client.process_live_audio(
                b"audio_data",
                mime_type="audio/pcm",
                sample_rate=16000,
            )

            assert result["response_text"] == "I logged your meal."
            assert result["function_calls"] == []

    @pytest.mark.asyncio
    async def test_process_audio_with_function_call(self):
        """Test processing audio that triggers function call."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Create mock session context manager
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.send = AsyncMock()

        # Mock function call
        mock_fc = MagicMock()
        mock_fc.name = "log_meal"
        mock_fc.args = {"dish_name": "Ramen", "venue": "Restaurant"}

        mock_tool_call = MagicMock()
        mock_tool_call.function_calls = [mock_fc]

        mock_response = MagicMock()
        mock_response.server_content = None
        mock_response.tool_call = mock_tool_call

        async def mock_receive():
            yield mock_response

        mock_session.receive = mock_receive

        with patch.object(client, "create_live_session", return_value=mock_session):
            client.client = mock_genai_client

            result = await client.process_live_audio(b"audio_data")

            assert len(result["function_calls"]) == 1
            assert result["function_calls"][0]["name"] == "log_meal"
            assert result["function_calls"][0]["args"]["dish_name"] == "Ramen"

    @pytest.mark.asyncio
    async def test_process_audio_with_audio_response(self):
        """Test processing audio that returns audio response."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Create mock session context manager
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.send = AsyncMock()

        # Mock response with audio
        mock_inline_data = MagicMock()
        mock_inline_data.data = b"audio_response_bytes"

        mock_part = MagicMock()
        mock_part.text = None
        mock_part.inline_data = mock_inline_data

        mock_model_turn = MagicMock()
        mock_model_turn.parts = [mock_part]

        mock_content = MagicMock()
        mock_content.model_turn = mock_model_turn

        mock_response = MagicMock()
        mock_response.server_content = mock_content
        mock_response.tool_call = None

        async def mock_receive():
            yield mock_response

        mock_session.receive = mock_receive

        with patch.object(client, "create_live_session", return_value=mock_session):
            client.client = mock_genai_client

            result = await client.process_live_audio(b"audio_data")

            assert result["response_audio"] == b"audio_response_bytes"

    @pytest.mark.asyncio
    async def test_process_audio_empty_response(self):
        """Test processing audio with no response parts."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Create mock session context manager
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.send = AsyncMock()

        # Mock empty response
        mock_response = MagicMock()
        mock_response.server_content = None
        mock_response.tool_call = None

        async def mock_receive():
            yield mock_response

        mock_session.receive = mock_receive

        with patch.object(client, "create_live_session", return_value=mock_session):
            client.client = mock_genai_client

            result = await client.process_live_audio(b"audio_data")

            assert result["response_text"] is None
            assert result["function_calls"] == []

    @pytest.mark.asyncio
    async def test_process_audio_with_custom_params(self):
        """Test processing audio with custom MIME type and sample rate."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.send = AsyncMock()

        async def mock_receive():
            # Async generator that yields nothing (empty iteration)
            if False:  # Never executes, but makes this an async generator
                yield

        mock_session.receive = mock_receive

        with patch.object(client, "create_live_session", return_value=mock_session):
            client.client = mock_genai_client

            await client.process_live_audio(
                b"audio_data",
                mime_type="audio/webm",
                sample_rate=44100,
            )

            # Verify send was called with audio data
            mock_session.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_audio_function_call_no_args(self):
        """Test processing audio with function call that has no args."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.send = AsyncMock()

        # Mock function call with no args
        mock_fc = MagicMock()
        mock_fc.name = "search_food_history"
        mock_fc.args = None

        mock_tool_call = MagicMock()
        mock_tool_call.function_calls = [mock_fc]

        mock_response = MagicMock()
        mock_response.server_content = None
        mock_response.tool_call = mock_tool_call

        async def mock_receive():
            yield mock_response

        mock_session.receive = mock_receive

        with patch.object(client, "create_live_session", return_value=mock_session):
            client.client = mock_genai_client

            result = await client.process_live_audio(b"audio_data")

            assert len(result["function_calls"]) == 1
            assert result["function_calls"][0]["args"] == {}


# =============================================================================
# Media Resolution Tests
# =============================================================================


class TestGenerateJsonWithMediaResolution:
    """Tests for generate_json_with_media_resolution method."""

    @pytest.mark.asyncio
    async def test_not_configured_raises_error(self):
        """Test raises RuntimeError when API not configured."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        client.client = None

        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await client.generate_json_with_media_resolution("Analyze this food", "https://example.com/food.jpg")

    @pytest.mark.asyncio
    async def test_low_resolution_analysis(self):
        """Test image analysis with low resolution (64 tokens)."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_response = MagicMock()
        mock_response.text = '{"food": "pizza", "category": "fast_food"}'
        mock_response.usage_metadata = None

        mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        client.client = mock_genai_client

        with patch.object(client, "_prepare_parts", new_callable=AsyncMock) as mock_prep:
            mock_prep.return_value = [MagicMock()]

            result = await client.generate_json_with_media_resolution(
                "Categorize this food", "https://example.com/food.jpg", resolution="low"
            )

            assert result["food"] == "pizza"
            assert result["category"] == "fast_food"

            # Verify config was passed with correct resolution
            call_args = mock_genai_client.aio.models.generate_content.call_args
            config = call_args.kwargs["config"]
            assert config.media_resolution == "MEDIA_RESOLUTION_LOW"

    @pytest.mark.asyncio
    async def test_medium_resolution_analysis(self):
        """Test image analysis with medium resolution."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_response = MagicMock()
        mock_response.text = '{"ingredients": ["flour", "cheese", "tomatoes"], "calories": 450}'
        mock_response.usage_metadata = None

        mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        client.client = mock_genai_client

        with patch.object(client, "_prepare_parts", new_callable=AsyncMock) as mock_prep:
            mock_prep.return_value = [MagicMock()]

            result = await client.generate_json_with_media_resolution(
                "Extract all ingredients", "https://example.com/food.jpg", resolution="medium"
            )

            assert "ingredients" in result
            assert result["calories"] == 450

            call_args = mock_genai_client.aio.models.generate_content.call_args
            config = call_args.kwargs["config"]
            assert config.media_resolution == "MEDIA_RESOLUTION_MEDIUM"

    @pytest.mark.asyncio
    async def test_default_resolution_is_high(self):
        """Test that default resolution is 'high' (1024 tokens)."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_response = MagicMock()
        mock_response.text = '{"detected": true}'
        mock_response.usage_metadata = None

        mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        client.client = mock_genai_client

        with patch.object(client, "_prepare_parts", new_callable=AsyncMock) as mock_prep:
            mock_prep.return_value = [MagicMock()]

            await client.generate_json_with_media_resolution("Analyze", "https://example.com/food.jpg")

            call_args = mock_genai_client.aio.models.generate_content.call_args
            config = call_args.kwargs["config"]
            assert config.media_resolution == "MEDIA_RESOLUTION_HIGH"

    @pytest.mark.asyncio
    async def test_invalid_resolution_defaults_to_high(self):
        """Test that invalid resolution falls back to high."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_response = MagicMock()
        mock_response.text = '{"result": "ok"}'
        mock_response.usage_metadata = None

        mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        client.client = mock_genai_client

        with patch.object(client, "_prepare_parts", new_callable=AsyncMock) as mock_prep:
            mock_prep.return_value = [MagicMock()]

            await client.generate_json_with_media_resolution(
                "Analyze", "https://example.com/food.jpg", resolution="invalid"
            )

            call_args = mock_genai_client.aio.models.generate_content.call_args
            config = call_args.kwargs["config"]
            assert config.media_resolution == "MEDIA_RESOLUTION_HIGH"


# =============================================================================
# URL Context Tests
# =============================================================================


class TestGenerateJsonWithUrlContext:
    """Tests for generate_json_with_url_context method."""

    @pytest.mark.asyncio
    async def test_not_configured_raises_error(self):
        """Test raises RuntimeError when API not configured."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        client.client = None

        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await client.generate_json_with_url_context("Extract recipe", ["https://example.com/recipe"])

    @pytest.mark.asyncio
    async def test_recipe_import_from_url(self):
        """Test importing recipe data from a URL."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_response = MagicMock()
        mock_response.text = '{"title": "Pasta Carbonara", "ingredients": ["pasta", "eggs", "bacon"]}'
        mock_response.usage_metadata = None

        mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        client.client = mock_genai_client

        result = await client.generate_json_with_url_context(
            "Extract recipe information",
            ["https://example.com/carbonara-recipe"],
        )

        assert result["data"]["title"] == "Pasta Carbonara"
        assert "pasta" in result["data"]["ingredients"]
        assert result["sources"] == ["https://example.com/carbonara-recipe"]

    @pytest.mark.asyncio
    async def test_multiple_urls(self):
        """Test processing multiple URLs for context."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_response = MagicMock()
        mock_response.text = '{"comparison": "Recipe A is healthier"}'
        mock_response.usage_metadata = None

        mock_genai_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        client.client = mock_genai_client

        urls = [
            "https://example.com/recipe-a",
            "https://example.com/recipe-b",
        ]

        result = await client.generate_json_with_url_context(
            "Compare these recipes for healthiness",
            urls,
        )

        assert result["data"]["comparison"] == "Recipe A is healthier"
        assert len(result["sources"]) == 2


# =============================================================================
# Imagen 3 Tests
# =============================================================================


class TestGenerateImage:
    """Tests for generate_image method using Imagen 3."""

    @pytest.mark.asyncio
    async def test_not_configured_raises_error(self):
        """Test raises RuntimeError when API not configured."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        client.client = None

        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await client.generate_image("A healthy salad bowl")

    @pytest.mark.asyncio
    async def test_generate_food_image(self):
        """Test generating a food image."""
        import base64

        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Mock generated image
        mock_image = MagicMock()
        mock_image.image = MagicMock()
        mock_image.image.image_bytes = b"fake_png_data"

        mock_response = MagicMock()
        mock_response.generated_images = [mock_image]

        mock_genai_client.aio.models.generate_images = AsyncMock(return_value=mock_response)
        client.client = mock_genai_client

        result = await client.generate_image("A Mediterranean salad bowl")

        assert result["count"] == 1
        assert result["mime_type"] == "image/png"
        assert len(result["images"]) == 1
        # Verify base64 encoding
        decoded = base64.b64decode(result["images"][0])
        assert decoded == b"fake_png_data"

    @pytest.mark.asyncio
    async def test_generate_multiple_images(self):
        """Test generating multiple images."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Mock multiple generated images
        mock_images = []
        for i in range(3):
            mock_image = MagicMock()
            mock_image.image = MagicMock()
            mock_image.image.image_bytes = f"image_{i}".encode()
            mock_images.append(mock_image)

        mock_response = MagicMock()
        mock_response.generated_images = mock_images

        mock_genai_client.aio.models.generate_images = AsyncMock(return_value=mock_response)
        client.client = mock_genai_client

        result = await client.generate_image("A healthy breakfast", number_of_images=3)

        assert result["count"] == 3
        assert len(result["images"]) == 3

    @pytest.mark.asyncio
    async def test_custom_aspect_ratio(self):
        """Test generating image with custom aspect ratio."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_image = MagicMock()
        mock_image.image = MagicMock()
        mock_image.image.image_bytes = b"wide_image"

        mock_response = MagicMock()
        mock_response.generated_images = [mock_image]

        mock_genai_client.aio.models.generate_images = AsyncMock(return_value=mock_response)
        client.client = mock_genai_client

        await client.generate_image("Food photo", aspect_ratio="16:9")

        call_args = mock_genai_client.aio.models.generate_images.call_args
        assert call_args.kwargs["config"].aspect_ratio == "16:9"

    @pytest.mark.asyncio
    async def test_no_generated_images_returns_empty(self):
        """Test handling when no images are generated."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_response = MagicMock()
        mock_response.generated_images = []

        mock_genai_client.aio.models.generate_images = AsyncMock(return_value=mock_response)
        client.client = mock_genai_client

        result = await client.generate_image("A meal")

        assert result["count"] == 0
        assert result["images"] == []

    @pytest.mark.asyncio
    async def test_missing_image_bytes_skipped(self):
        """Test that images without bytes are skipped."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Image without image_bytes
        mock_image_bad = MagicMock()
        mock_image_bad.image = MagicMock()
        del mock_image_bad.image.image_bytes  # Simulate missing attribute

        # Image with bytes
        mock_image_good = MagicMock()
        mock_image_good.image = MagicMock()
        mock_image_good.image.image_bytes = b"good_data"

        mock_response = MagicMock()
        mock_response.generated_images = [mock_image_bad, mock_image_good]

        mock_genai_client.aio.models.generate_images = AsyncMock(return_value=mock_response)
        client.client = mock_genai_client

        result = await client.generate_image("A meal")

        # Only the good image should be in the result
        assert result["count"] == 1
