"""Tests for voice processing tool and routes."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fcp.tools.voice import process_voice_meal_log, voice_food_query


class TestProcessVoiceMealLog:
    """Tests for process_voice_meal_log function."""

    @pytest.mark.asyncio
    async def test_processes_audio_bytes(self):
        """Test processing raw audio bytes."""
        mock_result = {
            "response_text": "I logged your ramen.",
            "function_calls": [{"name": "log_meal", "args": {"dish_name": "Ramen"}}],
        }

        with patch("fcp.tools.voice.gemini") as mock_gemini:
            mock_gemini.process_live_audio = AsyncMock(return_value=mock_result)

            result = await process_voice_meal_log(
                audio_data=b"raw_audio_bytes",
                mime_type="audio/pcm",
                sample_rate=16000,
            )

            assert result["status"] == "logged"
            assert result["meal_data"] == {"dish_name": "Ramen"}
            assert result["response_text"] == "I logged your ramen."

    @pytest.mark.asyncio
    async def test_processes_base64_audio(self):
        """Test processing base64-encoded audio."""
        audio_bytes = b"test_audio_data"
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        mock_result = {
            "response_text": "Got it!",
            "function_calls": [{"name": "log_meal", "args": {"dish_name": "Pizza"}}],
        }

        with patch("fcp.tools.voice.gemini") as mock_gemini:
            mock_gemini.process_live_audio = AsyncMock(return_value=mock_result)

            result = await process_voice_meal_log(audio_data=audio_base64)

            assert result["status"] == "logged"
            # Verify the decoded bytes were passed
            call_args = mock_gemini.process_live_audio.call_args
            assert call_args.kwargs["audio_data"] == audio_bytes

    @pytest.mark.asyncio
    async def test_returns_clarification_needed_when_no_log_meal(self):
        """Test that clarification_needed is returned when log_meal not called."""
        mock_result = {
            "response_text": "What did you eat?",
            "function_calls": [],
        }

        with patch("fcp.tools.voice.gemini") as mock_gemini:
            mock_gemini.process_live_audio = AsyncMock(return_value=mock_result)

            result = await process_voice_meal_log(audio_data=b"audio")

            assert result["status"] == "clarification_needed"
            assert result["meal_data"] is None
            assert result["response_text"] == "What did you eat?"

    @pytest.mark.asyncio
    async def test_returns_clarification_when_other_function_called(self):
        """Test clarification_needed when function_calls has non-log_meal functions."""
        mock_result = {
            "response_text": "I understand you want something.",
            "function_calls": [
                {"name": "other_function", "args": {"foo": "bar"}},
                {"name": "another_function", "args": {"baz": 123}},
            ],
        }

        with patch("fcp.tools.voice.gemini") as mock_gemini:
            mock_gemini.process_live_audio = AsyncMock(return_value=mock_result)

            result = await process_voice_meal_log(audio_data=b"audio")

            assert result["status"] == "clarification_needed"
            assert result["meal_data"] is None

    @pytest.mark.asyncio
    async def test_includes_audio_response_when_available(self):
        """Test that audio response is included when generated."""
        mock_result = {
            "response_text": "Logged!",
            "response_audio": b"audio_response_bytes",
            "function_calls": [{"name": "log_meal", "args": {"dish_name": "Salad"}}],
        }

        with patch("fcp.tools.voice.gemini") as mock_gemini:
            mock_gemini.process_live_audio = AsyncMock(return_value=mock_result)

            result = await process_voice_meal_log(audio_data=b"audio")

            assert result["status"] == "logged"
            expected_b64 = base64.b64encode(b"audio_response_bytes").decode("utf-8")
            assert result["response_audio_base64"] == expected_b64

    @pytest.mark.asyncio
    async def test_handles_invalid_base64(self):
        """Test handling of invalid base64 input."""
        result = await process_voice_meal_log(audio_data="not_valid_base64!!!")

        assert result["status"] == "error"
        assert result["error"] == "Invalid base64 audio data"
        assert result["meal_data"] is None

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        """Test handling of exceptions during processing."""
        with patch("fcp.tools.voice.gemini") as mock_gemini:
            mock_gemini.process_live_audio = AsyncMock(side_effect=Exception("API error"))

            result = await process_voice_meal_log(audio_data=b"audio")

            assert result["status"] == "error"
            assert "API error" in result["error"]
            assert result["meal_data"] is None

    @pytest.mark.asyncio
    async def test_passes_mime_type_and_sample_rate(self):
        """Test that mime_type and sample_rate are passed."""
        mock_result = {"response_text": "Ok", "function_calls": []}

        with patch("fcp.tools.voice.gemini") as mock_gemini:
            mock_gemini.process_live_audio = AsyncMock(return_value=mock_result)

            await process_voice_meal_log(
                audio_data=b"audio",
                mime_type="audio/webm",
                sample_rate=44100,
            )

            call_args = mock_gemini.process_live_audio.call_args
            assert call_args.kwargs["mime_type"] == "audio/webm"
            assert call_args.kwargs["sample_rate"] == 44100


class TestVoiceFoodQuery:
    """Tests for voice_food_query function."""

    @pytest.mark.asyncio
    async def test_processes_query_with_search_request(self):
        """Test processing a voice query that triggers search."""
        mock_result = {
            "response_text": "Searching for pasta dishes.",
            "function_calls": [{"name": "search_food_history", "args": {"query": "pasta"}}],
        }

        with patch("fcp.tools.voice.gemini") as mock_gemini:
            mock_gemini.process_live_audio = AsyncMock(return_value=mock_result)

            result = await voice_food_query(
                audio_data=b"audio",
                user_id="user123",
            )

            assert result["status"] == "search_requested"
            assert result["query"] == "pasta"
            assert result["user_id"] == "user123"
            assert result["response_text"] == "Searching for pasta dishes."

    @pytest.mark.asyncio
    async def test_returns_response_when_no_search(self):
        """Test response status when no search is requested."""
        mock_result = {
            "response_text": "I can help you find meals.",
            "function_calls": [],
        }

        with patch("fcp.tools.voice.gemini") as mock_gemini:
            mock_gemini.process_live_audio = AsyncMock(return_value=mock_result)

            result = await voice_food_query(
                audio_data=b"audio",
                user_id="user456",
            )

            assert result["status"] == "response"
            assert result["query"] is None
            assert result["user_id"] == "user456"

    @pytest.mark.asyncio
    async def test_returns_response_when_other_function_called(self):
        """Test response status when function_calls has non-search functions."""
        mock_result = {
            "response_text": "Here's some information.",
            "function_calls": [
                {"name": "get_info", "args": {"topic": "nutrition"}},
                {"name": "another_function", "args": {}},
            ],
        }

        with patch("fcp.tools.voice.gemini") as mock_gemini:
            mock_gemini.process_live_audio = AsyncMock(return_value=mock_result)

            result = await voice_food_query(
                audio_data=b"audio",
                user_id="user789",
            )

            assert result["status"] == "response"
            assert result["query"] is None

    @pytest.mark.asyncio
    async def test_processes_base64_audio(self):
        """Test processing base64-encoded audio for query."""
        audio_bytes = b"query_audio"
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        mock_result = {"response_text": "Ok", "function_calls": []}

        with patch("fcp.tools.voice.gemini") as mock_gemini:
            mock_gemini.process_live_audio = AsyncMock(return_value=mock_result)

            await voice_food_query(
                audio_data=audio_base64,
                user_id="user789",
            )

            call_args = mock_gemini.process_live_audio.call_args
            assert call_args.kwargs["audio_data"] == audio_bytes

    @pytest.mark.asyncio
    async def test_includes_audio_response(self):
        """Test that audio response is included."""
        mock_result = {
            "response_text": "Here are your results.",
            "response_audio": b"audio_reply",
            "function_calls": [{"name": "search_food_history", "args": {"query": "lunch"}}],
        }

        with patch("fcp.tools.voice.gemini") as mock_gemini:
            mock_gemini.process_live_audio = AsyncMock(return_value=mock_result)

            result = await voice_food_query(audio_data=b"audio", user_id="user")

            expected_b64 = base64.b64encode(b"audio_reply").decode("utf-8")
            assert result["response_audio_base64"] == expected_b64

    @pytest.mark.asyncio
    async def test_handles_invalid_base64(self):
        """Test handling of invalid base64 input."""
        result = await voice_food_query(
            audio_data="invalid_base64!!!",
            user_id="user",
        )

        assert result["status"] == "error"
        assert result["error"] == "Invalid base64 audio data"
        assert result["query"] is None

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        """Test handling of exceptions during processing."""
        with patch("fcp.tools.voice.gemini") as mock_gemini:
            mock_gemini.process_live_audio = AsyncMock(side_effect=Exception("Connection failed"))

            result = await voice_food_query(audio_data=b"audio", user_id="user")

            assert result["status"] == "error"
            assert "Connection failed" in result["error"]

    @pytest.mark.asyncio
    async def test_passes_mime_type_and_sample_rate(self):
        """Test that parameters are passed correctly."""
        mock_result = {"response_text": "Ok", "function_calls": []}

        with patch("fcp.tools.voice.gemini") as mock_gemini:
            mock_gemini.process_live_audio = AsyncMock(return_value=mock_result)

            await voice_food_query(
                audio_data=b"audio",
                user_id="user",
                mime_type="audio/wav",
                sample_rate=22050,
            )

            call_args = mock_gemini.process_live_audio.call_args
            assert call_args.kwargs["mime_type"] == "audio/wav"
            assert call_args.kwargs["sample_rate"] == 22050


class TestLiveApiGeminiMethods:
    """Tests for Gemini client Live API methods."""

    def test_create_live_session_no_client(self):
        """Test error when client not configured."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        client.client = None

        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            client.create_live_session()

    def test_create_live_session_basic(self):
        """Test creating a basic live session."""
        from fcp.services.gemini import GeminiClient

        mock_session = MagicMock()
        mock_live = MagicMock()
        mock_live.connect.return_value = mock_session

        mock_client = MagicMock()
        mock_client.aio.live = mock_live

        client = GeminiClient()
        client.client = mock_client

        session = client.create_live_session()

        assert session == mock_session
        mock_live.connect.assert_called_once()

    def test_create_live_session_with_instruction(self):
        """Test creating live session with system instruction."""
        from fcp.services.gemini import GeminiClient

        mock_session = MagicMock()
        mock_live = MagicMock()
        mock_live.connect.return_value = mock_session

        mock_client = MagicMock()
        mock_client.aio.live = mock_live

        client = GeminiClient()
        client.client = mock_client

        client.create_live_session(
            system_instruction="Be helpful",
            enable_food_tools=False,
        )

        call_kwargs = mock_live.connect.call_args.kwargs
        assert "config" in call_kwargs

    @pytest.mark.asyncio
    async def test_process_live_audio_no_client(self):
        """Test error when client not configured."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        client.client = None

        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await client.process_live_audio(audio_data=b"audio")

    @pytest.mark.asyncio
    async def test_process_live_audio_success(self):
        """Test processing audio through Live API."""
        from fcp.services.gemini import GeminiClient

        # Create mock response with text
        mock_part = MagicMock()
        mock_part.text = "I understood your meal"
        mock_part.inline_data = None

        mock_model_turn = MagicMock()
        mock_model_turn.parts = [mock_part]

        mock_content = MagicMock()
        mock_content.model_turn = mock_model_turn

        mock_response = MagicMock()
        mock_response.server_content = mock_content
        mock_response.tool_call = None

        # Create async iterator for receive
        async def mock_receive():
            yield mock_response

        # Create mock session as async context manager
        mock_session = MagicMock()
        mock_session.send = AsyncMock()
        mock_session.receive.return_value = mock_receive()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_live = MagicMock()
        mock_live.connect.return_value = mock_session

        mock_client = MagicMock()
        mock_client.aio.live = mock_live

        client = GeminiClient()
        client.client = mock_client

        result = await client.process_live_audio(audio_data=b"test_audio")

        assert result["response_text"] == "I understood your meal"
        assert result["function_calls"] == []

    @pytest.mark.asyncio
    async def test_process_live_audio_with_function_call(self):
        """Test processing audio with function call response."""
        from fcp.services.gemini import GeminiClient

        # Create mock function call
        mock_fc = MagicMock()
        mock_fc.name = "log_meal"
        mock_fc.args = {"dish_name": "Pizza", "meal_type": "dinner"}

        mock_tool_call = MagicMock()
        mock_tool_call.function_calls = [mock_fc]

        mock_response = MagicMock()
        mock_response.server_content = None
        mock_response.tool_call = mock_tool_call

        # Create async iterator for receive
        async def mock_receive():
            yield mock_response

        # Create mock session as async context manager
        mock_session = MagicMock()
        mock_session.send = AsyncMock()
        mock_session.receive.return_value = mock_receive()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_live = MagicMock()
        mock_live.connect.return_value = mock_session

        mock_client = MagicMock()
        mock_client.aio.live = mock_live

        client = GeminiClient()
        client.client = mock_client

        result = await client.process_live_audio(audio_data=b"test_audio")

        assert len(result["function_calls"]) == 1
        assert result["function_calls"][0]["name"] == "log_meal"
        assert result["function_calls"][0]["args"]["dish_name"] == "Pizza"

    @pytest.mark.asyncio
    async def test_process_live_audio_with_audio_response(self):
        """Test processing audio returns audio response when available."""
        from fcp.services.gemini import GeminiClient

        # Create mock response with audio inline_data
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

        # Create async iterator for receive
        async def mock_receive():
            yield mock_response

        # Create mock session as async context manager
        mock_session = MagicMock()
        mock_session.send = AsyncMock()
        mock_session.receive.return_value = mock_receive()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_live = MagicMock()
        mock_live.connect.return_value = mock_session

        mock_client = MagicMock()
        mock_client.aio.live = mock_live

        client = GeminiClient()
        client.client = mock_client

        result = await client.process_live_audio(audio_data=b"test_audio")

        assert result["response_audio"] == b"audio_response_bytes"


class TestVoiceRouteValidation:
    """Tests for voice route request validation."""

    def test_voice_meal_log_request_valid(self):
        """Test valid voice meal log request."""
        from fcp.routes.voice import VoiceMealLogRequest

        audio_b64 = base64.b64encode(b"x" * 100).decode()
        request = VoiceMealLogRequest(audio_base64=audio_b64)
        assert request.mime_type == "audio/pcm"
        assert request.sample_rate == 16000

    def test_voice_meal_log_request_custom_params(self):
        """Test voice meal log request with custom params."""
        from fcp.routes.voice import VoiceMealLogRequest

        audio_b64 = base64.b64encode(b"x" * 100).decode()
        request = VoiceMealLogRequest(
            audio_base64=audio_b64,
            mime_type="audio/webm",
            sample_rate=44100,
        )
        assert request.mime_type == "audio/webm"
        assert request.sample_rate == 44100

    def test_voice_meal_log_request_sample_rate_bounds(self):
        """Test voice meal log request sample rate bounds."""
        from pydantic import ValidationError

        from fcp.routes.voice import VoiceMealLogRequest

        audio_b64 = base64.b64encode(b"x" * 100).decode()

        # Too low
        with pytest.raises(ValidationError):
            VoiceMealLogRequest(audio_base64=audio_b64, sample_rate=4000)

        # Too high
        with pytest.raises(ValidationError):
            VoiceMealLogRequest(audio_base64=audio_b64, sample_rate=96000)

    def test_voice_food_query_request_valid(self):
        """Test valid voice food query request."""
        from fcp.routes.voice import VoiceFoodQueryRequest

        audio_b64 = base64.b64encode(b"x" * 100).decode()
        request = VoiceFoodQueryRequest(audio_base64=audio_b64)
        assert request.mime_type == "audio/pcm"


class TestVoiceRouterConfig:
    """Tests for voice router configuration."""

    def test_voice_router_exists(self):
        """Test voice router is properly configured."""
        from fcp.routes.voice import router

        assert router is not None

    def test_voice_routes_registered(self):
        """Test voice routes are registered."""
        from fcp.routes.voice import router

        routes = [r.path for r in router.routes]
        assert "/voice/meal" in routes
        assert "/voice/query" in routes
