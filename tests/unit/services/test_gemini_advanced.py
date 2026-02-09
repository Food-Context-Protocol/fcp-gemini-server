"""Advanced tests for Gemini client: Deep Research, Video Generation, Live Audio.

This module provides comprehensive edge case coverage for:
- generate_deep_research() - Deep research with polling
- generate_video() - Video content analysis
- process_live_audio() - Real-time audio processing

Tests focus on edge cases, error handling, and branch coverage.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGenerateDeepResearchAdvanced:
    """Advanced tests for generate_deep_research edge cases."""

    @pytest.mark.asyncio
    async def test_polling_with_sleep_iterations(self):
        """Test that polling iterates through sleep cycles before completion."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Create initial interaction that is in_progress
        mock_in_progress = MagicMock()
        mock_in_progress.id = "int_poll"
        mock_in_progress.status = "in_progress"

        # After polling, it completes
        mock_completed = MagicMock()
        mock_completed.id = "int_poll"
        mock_completed.status = "completed"
        mock_output = MagicMock()
        mock_output.text = "Final research report."
        mock_completed.outputs = [mock_output]

        mock_genai_client.aio.interactions.create = AsyncMock(return_value=mock_in_progress)
        # First get returns in_progress, second returns completed
        mock_genai_client.aio.interactions.get = AsyncMock(side_effect=[mock_in_progress, mock_completed])

        client.client = mock_genai_client

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with patch("fcp.services.gemini.time.monotonic") as mock_time:
                # Start=0, first check=5 (still in timeout), second check=15 (still in timeout)
                time_values = [0, 5, 15]
                time_index = [0]

                def _mock_time():
                    idx = time_index[0]
                    time_index[0] += 1
                    return time_values[idx] if idx < len(time_values) else time_values[-1]

                mock_time.side_effect = _mock_time
                result = await client.generate_deep_research("test query", timeout_seconds=300)

        assert result["status"] == "completed"
        assert result["report"] == "Final research report."
        mock_sleep.assert_awaited_with(10)

    @pytest.mark.asyncio
    async def test_failed_research_without_error_attribute(self):
        """Test failed research when error attribute is missing."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Mock interaction without error attribute
        mock_interaction = MagicMock()
        mock_interaction.id = "int_no_error"
        mock_interaction.status = "failed"
        # Don't set error attribute - getattr should return "Unknown error"
        del mock_interaction.error

        mock_genai_client.aio.interactions.create = AsyncMock(return_value=mock_interaction)
        mock_genai_client.aio.interactions.get = AsyncMock(return_value=mock_interaction)

        client.client = mock_genai_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.generate_deep_research("test query", timeout_seconds=1)

        assert result["status"] == "failed"
        assert result["message"] == "Unknown error"
        assert result["interaction_id"] == "int_no_error"

    @pytest.mark.asyncio
    async def test_completed_research_with_none_outputs(self):
        """Test completed research when outputs is None rather than empty list."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_interaction = MagicMock()
        mock_interaction.id = "int_none"
        mock_interaction.status = "completed"
        mock_interaction.outputs = None  # None rather than []

        mock_genai_client.aio.interactions.create = AsyncMock(return_value=mock_interaction)
        mock_genai_client.aio.interactions.get = AsyncMock(return_value=mock_interaction)

        client.client = mock_genai_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.generate_deep_research("test query", timeout_seconds=1)

        assert result["status"] == "completed"
        assert result["report"] == ""

    @pytest.mark.asyncio
    async def test_completed_research_with_multiple_outputs(self):
        """Test completed research returns the last output."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_output1 = MagicMock()
        mock_output1.text = "First draft"
        mock_output2 = MagicMock()
        mock_output2.text = "Final report with corrections"

        mock_interaction = MagicMock()
        mock_interaction.id = "int_multi"
        mock_interaction.status = "completed"
        mock_interaction.outputs = [mock_output1, mock_output2]

        mock_genai_client.aio.interactions.create = AsyncMock(return_value=mock_interaction)
        mock_genai_client.aio.interactions.get = AsyncMock(return_value=mock_interaction)

        client.client = mock_genai_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.generate_deep_research("test query", timeout_seconds=1)

        assert result["status"] == "completed"
        assert result["report"] == "Final report with corrections"

    @pytest.mark.asyncio
    async def test_polling_multiple_iterations_before_timeout(self):
        """Test that polling iterates multiple times before timing out."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_interaction = MagicMock()
        mock_interaction.id = "int_multi_poll"
        mock_interaction.status = "in_progress"

        mock_genai_client.aio.interactions.create = AsyncMock(return_value=mock_interaction)
        mock_genai_client.aio.interactions.get = AsyncMock(return_value=mock_interaction)

        client.client = mock_genai_client

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with patch("fcp.services.gemini.time.monotonic") as mock_time:
                # Multiple iterations: 0, 10, 20, 40 (timeout at 30)
                time_values = [0, 10, 20, 40]
                time_index = [0]

                def _mock_time():
                    idx = time_index[0]
                    time_index[0] += 1
                    return time_values[idx] if idx < len(time_values) else time_values[-1] + 1000

                mock_time.side_effect = _mock_time
                result = await client.generate_deep_research("test query", timeout_seconds=30)

        assert result["status"] == "timeout"
        # Should have called sleep multiple times (each poll cycle)
        assert mock_sleep.call_count >= 2


class TestGenerateVideoAdvanced:
    """Advanced tests for generate_video edge cases."""

    @pytest.mark.asyncio
    async def test_video_without_video_bytes_attribute(self):
        """Test video completion when video object lacks video_bytes."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Mock video without video_bytes attribute
        mock_video = MagicMock(spec=["video"])
        mock_video.video = MagicMock(spec=[])  # No video_bytes

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
        assert result["video_bytes"] is None
        assert result["duration"] == 8

    @pytest.mark.asyncio
    async def test_video_without_video_attribute(self):
        """Test video completion when video object lacks video attribute."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Mock video without video attribute
        mock_video = MagicMock(spec=[])  # No video attribute

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
        assert result["video_bytes"] is None

    @pytest.mark.asyncio
    async def test_video_polling_with_operations_get(self):
        """Test that video polls via operations.get when not immediately done."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Initial operation not done
        mock_operation_pending = MagicMock()
        mock_operation_pending.done = False
        mock_operation_pending.name = "op_pending"

        # After polling, operation is done
        mock_video = MagicMock()
        mock_video.video = MagicMock()
        mock_video.video.video_bytes = b"final_video"

        mock_response = MagicMock()
        mock_response.generated_videos = [mock_video]

        mock_operation_done = MagicMock()
        mock_operation_done.done = True
        mock_operation_done.response = mock_response

        mock_genai_client.aio.models.generate_videos = AsyncMock(return_value=mock_operation_pending)
        mock_genai_client.aio.operations.get = AsyncMock(return_value=mock_operation_done)

        client.client = mock_genai_client

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with patch("fcp.services.gemini.time.monotonic") as mock_time:
                # Start=0, first check=5, second check=15
                time_values = [0, 5, 15]
                time_index = [0]

                def _mock_time():
                    idx = time_index[0]
                    time_index[0] += 1
                    return time_values[idx] if idx < len(time_values) else time_values[-1]

                mock_time.side_effect = _mock_time
                result = await client.generate_video("test prompt", timeout_seconds=300)

        assert result["status"] == "completed"
        assert result["video_bytes"] == b"final_video"
        mock_sleep.assert_awaited_once_with(10)
        mock_genai_client.aio.operations.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_video_timeout_without_name_attribute(self):
        """Test video timeout when operation lacks name attribute."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Mock operation without name attribute
        mock_operation = MagicMock(spec=["done"])
        mock_operation.done = False

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
        assert result["operation_name"] is None
        assert "Video still generating" in result["message"]

    @pytest.mark.asyncio
    async def test_video_with_portrait_aspect_ratio(self):
        """Test video generation with portrait aspect ratio."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_video = MagicMock()
        mock_video.video = MagicMock()
        mock_video.video.video_bytes = b"portrait_video"

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
                aspect_ratio="9:16",  # Portrait
                timeout_seconds=60,
            )

        assert result["status"] == "completed"
        assert result["duration"] == 4

    @pytest.mark.asyncio
    async def test_video_multiple_polling_iterations(self):
        """Test video generation with multiple polling iterations before done."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        # Create pending and done operations
        mock_operation_pending = MagicMock()
        mock_operation_pending.done = False
        mock_operation_pending.name = "op_long"

        mock_video = MagicMock()
        mock_video.video = MagicMock()
        mock_video.video.video_bytes = b"video_data"

        mock_response = MagicMock()
        mock_response.generated_videos = [mock_video]

        mock_operation_done = MagicMock()
        mock_operation_done.done = True
        mock_operation_done.response = mock_response

        mock_genai_client.aio.models.generate_videos = AsyncMock(return_value=mock_operation_pending)
        # Return pending twice, then done
        mock_genai_client.aio.operations.get = AsyncMock(
            side_effect=[
                mock_operation_pending,
                mock_operation_pending,
                mock_operation_done,
            ]
        )

        client.client = mock_genai_client

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with patch("fcp.services.gemini.time.monotonic") as mock_time:
                # Multiple poll iterations
                time_values = [0, 10, 20, 30, 40]
                time_index = [0]

                def _mock_time():
                    idx = time_index[0]
                    time_index[0] += 1
                    return time_values[idx] if idx < len(time_values) else time_values[-1]

                mock_time.side_effect = _mock_time
                result = await client.generate_video("test prompt", timeout_seconds=300)

        assert result["status"] == "completed"
        assert mock_sleep.await_count == 3  # Three sleep calls before completion


class TestProcessLiveAudioAdvanced:
    """Advanced tests for process_live_audio edge cases."""

    # (Existing code for TestProcessLiveAudioAdvanced remains unchanged, skipping for brevity in thought process but I will write it all back)
    # Actually I should include it to overwrite the file properly.

    @pytest.mark.asyncio
    async def test_process_audio_with_no_model_turn(self):
        """Test processing when server_content has no model_turn."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.send = AsyncMock()

        # Mock response with server_content but no model_turn
        mock_content = MagicMock()
        mock_content.model_turn = None

        mock_response = MagicMock()
        mock_response.server_content = mock_content
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
    async def test_process_audio_with_multiple_text_parts(self):
        """Test processing audio with multiple text parts concatenated."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.send = AsyncMock()

        # Create multiple parts with text
        mock_part1 = MagicMock()
        mock_part1.text = "Hello, "
        mock_part1.inline_data = None

        mock_part2 = MagicMock()
        mock_part2.text = "I logged your meal."
        mock_part2.inline_data = None

        mock_model_turn = MagicMock()
        mock_model_turn.parts = [mock_part1, mock_part2]

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

            assert result["response_text"] == "Hello, I logged your meal."

    @pytest.mark.asyncio
    async def test_process_audio_with_multiple_function_calls(self):
        """Test processing audio with multiple function calls."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.send = AsyncMock()

        # Create multiple function calls
        mock_fc1 = MagicMock()
        mock_fc1.name = "log_meal"
        mock_fc1.args = {"dish_name": "Salad"}

        mock_fc2 = MagicMock()
        mock_fc2.name = "search_food_history"
        mock_fc2.args = {"query": "healthy meals"}

        mock_tool_call = MagicMock()
        mock_tool_call.function_calls = [mock_fc1, mock_fc2]

        mock_response = MagicMock()
        mock_response.server_content = None
        mock_response.tool_call = mock_tool_call

        async def mock_receive():
            yield mock_response

        mock_session.receive = mock_receive

        with patch.object(client, "create_live_session", return_value=mock_session):
            client.client = mock_genai_client

            result = await client.process_live_audio(b"audio_data")

            assert len(result["function_calls"]) == 2
            assert result["function_calls"][0]["name"] == "log_meal"
            assert result["function_calls"][1]["name"] == "search_food_history"

    @pytest.mark.asyncio
    async def test_process_audio_with_mixed_responses(self):
        """Test processing audio that returns both text and audio."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.send = AsyncMock()

        # Part with text
        mock_part1 = MagicMock()
        mock_part1.text = "Understood."
        mock_part1.inline_data = None

        # Part with audio
        mock_inline_data = MagicMock()
        mock_inline_data.data = b"audio_bytes"

        mock_part2 = MagicMock()
        mock_part2.text = None
        mock_part2.inline_data = mock_inline_data

        mock_model_turn = MagicMock()
        mock_model_turn.parts = [mock_part1, mock_part2]

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

            assert result["response_text"] == "Understood."
            assert result["response_audio"] == b"audio_bytes"

    @pytest.mark.asyncio
    async def test_process_audio_with_multiple_responses(self):
        """Test processing multiple response messages from session."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.send = AsyncMock()

        # First response with text
        mock_part1 = MagicMock()
        mock_part1.text = "Part 1. "
        mock_part1.inline_data = None

        mock_model_turn1 = MagicMock()
        mock_model_turn1.parts = [mock_part1]

        mock_content1 = MagicMock()
        mock_content1.model_turn = mock_model_turn1

        mock_response1 = MagicMock()
        mock_response1.server_content = mock_content1
        mock_response1.tool_call = None

        # Second response with more text
        mock_part2 = MagicMock()
        mock_part2.text = "Part 2."
        mock_part2.inline_data = None

        mock_model_turn2 = MagicMock()
        mock_model_turn2.parts = [mock_part2]

        mock_content2 = MagicMock()
        mock_content2.model_turn = mock_model_turn2

        mock_response2 = MagicMock()
        mock_response2.server_content = mock_content2
        mock_response2.tool_call = None

        async def mock_receive():
            yield mock_response1
            yield mock_response2

        mock_session.receive = mock_receive

        with patch.object(client, "create_live_session", return_value=mock_session):
            client.client = mock_genai_client

            result = await client.process_live_audio(b"audio_data")

            assert result["response_text"] == "Part 1. Part 2."

    @pytest.mark.asyncio
    async def test_process_audio_response_without_text_attribute(self):
        """Test processing when part has no text attribute."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.send = AsyncMock()

        # Part without text attribute (spec removes it)
        mock_part = MagicMock(spec=["inline_data"])
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

        with patch.object(client, "create_live_session", return_value=mock_session):
            client.client = mock_genai_client

            result = await client.process_live_audio(b"audio_data")

            assert result["response_text"] is None

    @pytest.mark.asyncio
    async def test_process_audio_response_without_inline_data_attribute(self):
        """Test processing when part has no inline_data attribute."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.send = AsyncMock()

        # Part without inline_data attribute
        mock_part = MagicMock(spec=["text"])
        mock_part.text = "Hello"

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

            assert result["response_text"] == "Hello"
            assert result["response_audio"] is None

    @pytest.mark.asyncio
    async def test_process_audio_with_text_and_function_call(self):
        """Test processing with both text response and function call."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.send = AsyncMock()

        # Text response
        mock_part = MagicMock()
        mock_part.text = "Logging your meal now."
        mock_part.inline_data = None

        mock_model_turn = MagicMock()
        mock_model_turn.parts = [mock_part]

        mock_content = MagicMock()
        mock_content.model_turn = mock_model_turn

        mock_response1 = MagicMock()
        mock_response1.server_content = mock_content
        mock_response1.tool_call = None

        # Function call response
        mock_fc = MagicMock()
        mock_fc.name = "log_meal"
        mock_fc.args = {"dish_name": "Pasta", "meal_type": "dinner"}

        mock_tool_call = MagicMock()
        mock_tool_call.function_calls = [mock_fc]

        mock_response2 = MagicMock()
        mock_response2.server_content = None
        mock_response2.tool_call = mock_tool_call

        async def mock_receive():
            yield mock_response1
            yield mock_response2

        mock_session.receive = mock_receive

        with patch.object(client, "create_live_session", return_value=mock_session):
            client.client = mock_genai_client

            result = await client.process_live_audio(b"audio_data")

            assert result["response_text"] == "Logging your meal now."
            assert len(result["function_calls"]) == 1
            assert result["function_calls"][0]["name"] == "log_meal"
            assert result["function_calls"][0]["args"]["dish_name"] == "Pasta"

    @pytest.mark.asyncio
    async def test_process_audio_response_without_server_content_attribute(self):
        """Test processing when response has no server_content attribute."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.send = AsyncMock()

        # Response without server_content attribute
        mock_response = MagicMock(spec=["tool_call"])
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
    async def test_process_audio_response_without_tool_call_attribute(self):
        """Test processing when response has no tool_call attribute."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()

        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.send = AsyncMock()

        # Response without tool_call attribute
        mock_response = MagicMock(spec=["server_content"])
        mock_response.server_content = None

        async def mock_receive():
            yield mock_response

        mock_session.receive = mock_receive

        with patch.object(client, "create_live_session", return_value=mock_session):
            client.client = mock_genai_client

            result = await client.process_live_audio(b"audio_data")

            assert result["response_text"] is None
            assert result["function_calls"] == []


class TestCreateLiveSessionAdvanced:
    """Advanced tests for create_live_session edge cases."""

    def test_create_session_with_both_instruction_and_no_tools(self):
        """Test creating session with system instruction but no food tools."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()
        mock_session = MagicMock()
        mock_genai_client.aio.live.connect.return_value = mock_session

        client.client = mock_genai_client

        result = client.create_live_session(
            system_instruction="Custom instruction here.",
            enable_food_tools=False,
        )

        assert result is mock_session
        call_args = mock_genai_client.aio.live.connect.call_args
        config = call_args.kwargs["config"]
        # With enable_food_tools=False, tools should not be in config
        assert hasattr(config, "response_modalities")

    def test_create_session_with_empty_system_instruction(self):
        """Test creating session with empty string system instruction."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        mock_genai_client = MagicMock()
        mock_session = MagicMock()
        mock_genai_client.aio.live.connect.return_value = mock_session

        client.client = mock_genai_client

        # Empty string is falsy, so system_instruction should not be set
        result = client.create_live_session(
            system_instruction="",
            enable_food_tools=True,
        )

        assert result is mock_session
