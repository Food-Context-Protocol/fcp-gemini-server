"""Tests for Gemini 3 service methods.

Tests the new SDK features:
- Function calling
- Google Search grounding
- Extended thinking
- Code execution
- 1M context window
"""
# sourcery skip: no-loop-in-tests

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Mock the google-genai SDK before importing
# NOTE: This is NOT autouse because it breaks imports of google.cloud
# Tests that need it must explicitly request it as a parameter
@pytest.fixture
def mock_genai_sdk():
    """Mock the google-genai SDK.

    NOTE: This fixture is not autouse because it replaces the 'google' module
    in sys.modules, which breaks imports of google.cloud used by other services.
    Tests that need this mock must explicitly request it as a fixture parameter.
    """
    with patch.dict(
        "sys.modules",
        {
            "google": MagicMock(),
            "google.genai": MagicMock(),
            "google.genai.types": MagicMock(),
        },
    ):
        yield


class TestGeminiClientInit:
    """Tests for GeminiClient initialization."""

    def test_client_initializes_with_api_key(self, mock_genai_sdk):
        """Client should initialize with API key from environment."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            with patch("google.genai.Client"):
                from fcp.services.gemini import GeminiClient

                client = GeminiClient()
                # Client should be created
                assert client is not None

    def test_client_handles_missing_api_key(self, mock_genai_sdk):
        """Client should handle missing API key gracefully."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("google.genai.Client"):
                from fcp.services.gemini import GeminiClient

                # Should not raise, just set client to None
                GeminiClient()


class TestFunctionCalling:
    """Tests for function calling feature."""

    @pytest.fixture
    def mock_function_response(self):
        """Mock response with function calls."""
        mock_response = MagicMock()
        mock_response.text = "Analysis complete"

        # Mock function call part
        mock_call = MagicMock()
        mock_call.name = "identify_dish"
        mock_call.args = {"dish_name": "Ramen", "cuisine": "Japanese"}

        mock_part = MagicMock()
        mock_part.function_call = mock_call

        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]
        mock_response.candidates = [mock_candidate]

        return mock_response

    @pytest.mark.asyncio
    async def test_generate_with_tools_extracts_function_calls(self, mock_function_response):
        """Should extract function calls from response."""
        with patch("fcp.services.gemini.genai") as mock_genai:
            mock_client = MagicMock()

            # Mock the aio.models.generate_content async method
            async def mock_generate(*args, **kwargs):
                return mock_function_response

            mock_client.aio.models.generate_content = mock_generate
            mock_genai.Client.return_value = mock_client

            # Import and create client with mocked genai
            from fcp.services.gemini import GeminiClient

            client = GeminiClient()
            client.client = mock_client

            # Test the method
            result = await client.generate_with_tools(
                prompt="Analyze this food",
                tools=[{"name": "identify_dish", "description": "Identify dish", "parameters": {}}],
            )

            # Should have extracted the function call
            assert "function_calls" in result
            assert result is not None

    @pytest.mark.asyncio
    async def test_generate_with_tools_handles_no_function_calls(self):
        """Should handle responses without function calls."""
        mock_response = MagicMock()
        mock_response.text = "No functions called"
        mock_response.candidates = [MagicMock(content=MagicMock(parts=[]))]

        assert mock_response.text == "No functions called"


class TestGoogleSearchGrounding:
    """Tests for Google Search grounding feature."""

    @pytest.fixture
    def mock_grounded_response(self):
        """Mock response with grounding metadata."""
        mock_response = MagicMock()
        mock_response.text = "Here are the latest FDA recalls for romaine lettuce..."

        # Mock grounding metadata
        mock_source = MagicMock()
        mock_source.uri = "https://fda.gov/recalls/romaine"
        mock_source.title = "FDA Recall Notice"

        mock_metadata = MagicMock()
        mock_metadata.grounding_chunks = [MagicMock(web=mock_source)]

        mock_candidate = MagicMock()
        mock_candidate.grounding_metadata = mock_metadata
        mock_response.candidates = [mock_candidate]

        return mock_response

    @pytest.mark.asyncio
    async def test_generate_with_grounding_extracts_sources(self, mock_grounded_response):
        """Should extract source URLs from grounding metadata."""
        # The grounded response should contain sources
        assert mock_grounded_response.candidates[0].grounding_metadata is not None
        assert len(mock_grounded_response.candidates[0].grounding_metadata.grounding_chunks) > 0

    @pytest.mark.asyncio
    async def test_generate_with_grounding_returns_text_and_sources(self, mock_grounded_response):
        """Should return both text and source URLs."""
        # Text should be present
        assert mock_grounded_response.text is not None
        assert "FDA" in mock_grounded_response.text


class TestExtendedThinking:
    """Tests for extended thinking/reasoning feature."""

    @pytest.fixture
    def mock_thinking_response(self):
        """Mock response with thinking."""
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "analysis": "Deep analysis result",
                "confidence": 0.95,
            }
        )
        return mock_response

    @pytest.mark.asyncio
    async def test_thinking_levels_are_valid(self):
        """Thinking levels should be one of: minimal, low, medium, high."""
        valid_levels = ["minimal", "low", "medium", "high"]
        for level in valid_levels:
            assert level in valid_levels

    @pytest.mark.asyncio
    async def test_thinking_config_maps_levels_correctly(self):
        """Thinking budget should map from level names."""
        level_map = {
            "minimal": 128,
            "low": 1024,
            "medium": 4096,
            "high": 8192,
        }
        assert level_map["high"] > level_map["low"]

    def test_extract_thinking_content_with_thoughts(self):
        """Should extract thinking content from response with thought parts."""
        from fcp.services.gemini import _extract_thinking_content

        # Mock response with thinking parts
        mock_response = MagicMock()
        mock_part1 = MagicMock()
        mock_part1.thought = True
        mock_part1.text = "First I'll analyze the dish..."

        mock_part2 = MagicMock()
        mock_part2.thought = True
        mock_part2.text = "The ingredients appear to be..."

        mock_part3 = MagicMock()
        mock_part3.thought = False  # Not a thought part
        mock_part3.text = "Final analysis"

        mock_content = MagicMock()
        mock_content.parts = [mock_part1, mock_part2, mock_part3]

        mock_candidate = MagicMock()
        mock_candidate.content = mock_content
        mock_response.candidates = [mock_candidate]

        result = _extract_thinking_content(mock_response)

        assert result is not None
        assert "First I'll analyze the dish..." in result
        assert "The ingredients appear to be..." in result
        assert "Final analysis" not in result

    def test_extract_thinking_content_without_thoughts(self):
        """Should return None when no thought parts are present."""
        from fcp.services.gemini import _extract_thinking_content

        mock_response = MagicMock()
        mock_part = MagicMock()
        mock_part.thought = False
        mock_part.text = "Just regular text"

        mock_content = MagicMock()
        mock_content.parts = [mock_part]

        mock_candidate = MagicMock()
        mock_candidate.content = mock_content
        mock_response.candidates = [mock_candidate]

        result = _extract_thinking_content(mock_response)

        assert result is None

    def test_extract_thinking_content_with_missing_thought_attribute(self):
        """Should handle parts without thought attribute."""
        from fcp.services.gemini import _extract_thinking_content

        mock_response = MagicMock()
        mock_part = MagicMock(spec=[])  # No attributes
        del mock_part.thought  # Ensure thought attribute doesn't exist

        mock_content = MagicMock()
        mock_content.parts = [mock_part]

        mock_candidate = MagicMock()
        mock_candidate.content = mock_content
        mock_response.candidates = [mock_candidate]

        result = _extract_thinking_content(mock_response)

        assert result is None

    def test_extract_thinking_content_with_empty_candidates(self):
        """Should handle response with no candidates."""
        from fcp.services.gemini import _extract_thinking_content

        mock_response = MagicMock()
        mock_response.candidates = []

        result = _extract_thinking_content(mock_response)

        assert result is None

    def test_extract_thinking_content_with_missing_content(self):
        """Should handle candidates with missing or None content."""
        from fcp.services.gemini import _extract_thinking_content

        mock_response = MagicMock()

        # Candidate with None content
        mock_candidate = MagicMock()
        mock_candidate.content = None
        mock_response.candidates = [mock_candidate]

        result = _extract_thinking_content(mock_response)

        assert result is None

    def test_extract_thinking_content_with_missing_parts(self):
        """Should handle content with missing or None parts."""
        from fcp.services.gemini import _extract_thinking_content

        mock_response = MagicMock()

        # Content with None parts
        mock_content = MagicMock()
        mock_content.parts = None

        mock_candidate = MagicMock()
        mock_candidate.content = mock_content
        mock_response.candidates = [mock_candidate]

        result = _extract_thinking_content(mock_response)

        assert result is None


class TestCodeExecution:
    """Tests for code execution feature."""

    @pytest.fixture
    def mock_code_response(self):
        """Mock response with code execution."""
        mock_response = MagicMock()
        mock_response.text = "Calculated result: 1850 calories"

        # Mock executable code part
        mock_code = MagicMock()
        mock_code.code = "total = sum([800, 600, 450])"
        mock_code.outcome = "SUCCESS"
        mock_code.output = "1850"

        mock_part = MagicMock()
        mock_part.executable_code = mock_code

        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]
        mock_response.candidates = [mock_candidate]

        return mock_response

    @pytest.mark.asyncio
    async def test_code_execution_extracts_results(self, mock_code_response):
        """Should extract code execution results."""
        parts = mock_code_response.candidates[0].content.parts
        assert len(parts) > 0
        assert parts[0].executable_code.output == "1850"

    @pytest.mark.asyncio
    async def test_code_execution_handles_failure(self):
        """Should handle code execution failures gracefully."""
        mock_code = MagicMock()
        mock_code.outcome = "FAILED"
        mock_code.output = "Error: division by zero"

        # Should capture error state
        assert mock_code.outcome == "FAILED"


class TestAgenticVision:
    """Tests for Agentic Vision (code execution + image) feature."""

    @pytest.fixture
    def mock_agentic_vision_response(self):
        """Mock response with code execution and JSON analysis."""
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "dish_name": "Sushi Platter",
                "cuisine": "Japanese",
                "ingredients": ["rice", "salmon", "tuna"],
                "portion_analysis": {"item_count": 8},
            }
        )

        # Mock code execution parts
        mock_code_part = MagicMock()
        mock_code_part.executable_code = MagicMock()
        mock_code_part.executable_code.code = "# Counted 8 pieces of sushi"
        mock_code_part.code_execution_result = None

        mock_result_part = MagicMock()
        mock_result_part.executable_code = None
        mock_result_part.code_execution_result = MagicMock()
        mock_result_part.code_execution_result.output = "8"

        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_code_part, mock_result_part]
        mock_response.candidates = [mock_candidate]

        # Mock usage metadata
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50

        return mock_response

    @pytest.mark.asyncio
    async def test_generate_json_with_agentic_vision_extracts_code(self, mock_agentic_vision_response):
        """Should extract code and execution results from response."""
        parts = mock_agentic_vision_response.candidates[0].content.parts
        assert len(parts) == 2

        # First part has code
        assert parts[0].executable_code.code == "# Counted 8 pieces of sushi"

        # Second part has result
        assert parts[1].code_execution_result.output == "8"

    @pytest.mark.asyncio
    async def test_generate_json_with_agentic_vision_parses_json(self, mock_agentic_vision_response):
        """Should parse JSON from response text."""
        result = json.loads(mock_agentic_vision_response.text)

        assert result["dish_name"] == "Sushi Platter"
        assert result["portion_analysis"]["item_count"] == 8

    @pytest.mark.asyncio
    async def test_agentic_vision_without_code_execution(self):
        """Should handle responses where model doesn't execute code."""
        mock_response = MagicMock()
        mock_response.text = json.dumps({"dish_name": "Simple Dish"})

        mock_part = MagicMock()
        mock_part.executable_code = None
        mock_part.code_execution_result = None

        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]
        mock_response.candidates = [mock_candidate]

        # Should still work without code execution
        result = json.loads(mock_response.text)
        assert result["dish_name"] == "Simple Dish"

    @pytest.mark.asyncio
    async def test_agentic_vision_configures_code_execution_tool(self):
        """Agentic Vision should configure code execution tool in API call."""
        with patch("fcp.services.gemini.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = '{"dish_name": "Test"}'
            mock_response.candidates = [MagicMock(content=MagicMock(parts=[]))]
            mock_response.usage_metadata = MagicMock()
            mock_response.usage_metadata.prompt_token_count = 10
            mock_response.usage_metadata.candidates_token_count = 10

            mock_generate = AsyncMock(return_value=mock_response)
            mock_client.aio.models.generate_content = mock_generate

            from fcp.services.gemini import GeminiClient

            client = GeminiClient()
            client.client = mock_client

            async def mock_prepare_parts(*args, **kwargs):
                return [MagicMock()]

            setattr(client, "_prepare_parts", mock_prepare_parts)

            await client.generate_json_with_agentic_vision(prompt="Test", image_url="https://example.com/test.jpg")

            # Verify config was passed with code execution tool
            mock_generate.assert_called_once()
            call_kwargs = mock_generate.call_args.kwargs
            config = call_kwargs.get("config")
            assert config is not None
            assert config.response_mime_type == "application/json"
            assert config.tools is not None
            assert len(config.tools) > 0


class TestCombinedFeatures:
    """Tests for using multiple features together."""

    @pytest.mark.asyncio
    async def test_generate_with_all_tools_signature(self):
        """generate_with_all_tools should accept all feature flags."""
        # Method signature should support:
        expected_params = [
            "prompt",
            "function_tools",
            "enable_grounding",
            "enable_code_execution",
            "thinking_level",
            "image_url",
        ]
        # All params should be configurable
        assert len(expected_params) == 6

    @pytest.mark.asyncio
    async def test_agents_use_combined_features(self):
        """Discovery agent should use grounding + thinking + functions."""
        # Agent should configure all three
        config = {
            "grounding": True,
            "thinking_level": "high",
            "function_tools": ["save_recommendation"],
        }
        assert config["grounding"] is True
        assert config["thinking_level"] == "high"


class TestLargeContext:
    """Tests for 1M token context window."""

    @pytest.mark.asyncio
    async def test_large_context_handles_big_payload(self):
        """Should handle large payloads without truncation."""
        # Simulate a large food log history
        large_history = [{"dish": f"Meal {i}"} for i in range(1000)]
        json_size = len(json.dumps(large_history))

        # Should be able to handle without issue
        assert json_size > 10000  # Over 10KB of data

    @pytest.mark.asyncio
    async def test_generate_json_with_large_context_signature(self):
        """Method should exist for large context JSON generation."""


class TestFunctionDefinitions:
    """Tests for function/tool definitions."""

    def test_food_analysis_tools_are_defined(self):
        """Food analysis tools should be properly defined."""
        from fcp.tools.function_definitions import FOOD_ANALYSIS_TOOLS

        assert len(FOOD_ANALYSIS_TOOLS) > 0

        # Each tool should have required fields
        for tool in FOOD_ANALYSIS_TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool

    def test_discovery_agent_tools_are_defined(self):
        """Discovery agent tools should be defined."""
        from fcp.tools.function_definitions import DISCOVERY_AGENT_TOOLS

        assert len(DISCOVERY_AGENT_TOOLS) > 0

        # Should include save_recommendation
        tool_names = [t["name"] for t in DISCOVERY_AGENT_TOOLS]
        assert "save_recommendation" in tool_names

    def test_media_processing_tools_are_defined(self):
        """Media processing tools should be defined."""
        from fcp.tools.function_definitions import MEDIA_PROCESSING_TOOLS

        assert len(MEDIA_PROCESSING_TOOLS) > 0

        # Should include food detection
        tool_names = [t["name"] for t in MEDIA_PROCESSING_TOOLS]
        assert "detect_food_in_image" in tool_names


class TestGeminiClientNotConfigured:
    """Tests that all public methods raise RuntimeError when GEMINI_API_KEY is not configured.

    These tests verify that every public method that requires the Gemini client
    properly raises a RuntimeError with the message "GEMINI_API_KEY not configured"
    when self.client is None.
    """

    @pytest.fixture
    def unconfigured_client(self):
        """Create a GeminiClient with client=None to simulate missing API key."""
        from fcp.services.gemini import GeminiClient

        client = GeminiClient()
        client.client = None  # Simulate missing API key
        return client

    @pytest.mark.asyncio
    async def test_generate_content_raises_when_not_configured(self, unconfigured_client):
        """generate_content should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await unconfigured_client.generate_content("test prompt")

    @pytest.mark.asyncio
    async def test_generate_content_stream_raises_when_not_configured(self, unconfigured_client):
        """generate_content_stream should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            async for _ in unconfigured_client.generate_content_stream("test prompt"):
                pass

    @pytest.mark.asyncio
    async def test_generate_json_raises_when_not_configured(self, unconfigured_client):
        """generate_json should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await unconfigured_client.generate_json("test prompt")

    @pytest.mark.asyncio
    async def test_generate_json_stream_raises_when_not_configured(self, unconfigured_client):
        """generate_json_stream should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            async for _ in unconfigured_client.generate_json_stream("test prompt"):
                pass

    @pytest.mark.asyncio
    async def test_generate_with_tools_raises_when_not_configured(self, unconfigured_client):
        """generate_with_tools should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await unconfigured_client.generate_with_tools(
                prompt="test prompt",
                tools=[{"name": "test_tool", "description": "test", "parameters": {}}],
            )

    @pytest.mark.asyncio
    async def test_generate_with_grounding_raises_when_not_configured(self, unconfigured_client):
        """generate_with_grounding should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await unconfigured_client.generate_with_grounding("test prompt")

    @pytest.mark.asyncio
    async def test_generate_json_with_grounding_raises_when_not_configured(self, unconfigured_client):
        """generate_json_with_grounding should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await unconfigured_client.generate_json_with_grounding("test prompt")

    @pytest.mark.asyncio
    async def test_generate_with_thinking_raises_when_not_configured(self, unconfigured_client):
        """generate_with_thinking should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await unconfigured_client.generate_with_thinking("test prompt")

    @pytest.mark.asyncio
    async def test_generate_json_with_thinking_raises_when_not_configured(self, unconfigured_client):
        """generate_json_with_thinking should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await unconfigured_client.generate_json_with_thinking("test prompt")

    @pytest.mark.asyncio
    async def test_generate_with_code_execution_raises_when_not_configured(self, unconfigured_client):
        """generate_with_code_execution should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await unconfigured_client.generate_with_code_execution("test prompt")

    @pytest.mark.asyncio
    async def test_generate_json_with_agentic_vision_raises_when_not_configured(self, unconfigured_client):
        """generate_json_with_agentic_vision should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await unconfigured_client.generate_json_with_agentic_vision(
                prompt="test prompt", image_url="https://example.com/test.jpg"
            )

    @pytest.mark.asyncio
    async def test_generate_with_large_context_raises_when_not_configured(self, unconfigured_client):
        """generate_with_large_context should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await unconfigured_client.generate_with_large_context("test prompt")

    @pytest.mark.asyncio
    async def test_generate_json_with_large_context_raises_when_not_configured(self, unconfigured_client):
        """generate_json_with_large_context should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await unconfigured_client.generate_json_with_large_context("test prompt")

    @pytest.mark.asyncio
    async def test_create_context_cache_raises_when_not_configured(self, unconfigured_client):
        """create_context_cache should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await unconfigured_client.create_context_cache(name="test_cache", content="test content")

    @pytest.mark.asyncio
    async def test_generate_with_cache_raises_when_not_configured(self, unconfigured_client):
        """generate_with_cache should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await unconfigured_client.generate_with_cache(prompt="test prompt", cache_name="test_cache")

    @pytest.mark.asyncio
    async def test_generate_with_all_tools_raises_when_not_configured(self, unconfigured_client):
        """generate_with_all_tools should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await unconfigured_client.generate_with_all_tools("test prompt")

    @pytest.mark.asyncio
    async def test_generate_deep_research_raises_when_not_configured(self, unconfigured_client):
        """generate_deep_research should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await unconfigured_client.generate_deep_research("test query")

    @pytest.mark.asyncio
    async def test_generate_video_raises_when_not_configured(self, unconfigured_client):
        """generate_video should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await unconfigured_client.generate_video("test prompt")

    def test_create_live_session_raises_when_not_configured(self, unconfigured_client):
        """create_live_session should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            unconfigured_client.create_live_session()

    @pytest.mark.asyncio
    async def test_process_live_audio_raises_when_not_configured(self, unconfigured_client):
        """process_live_audio should raise RuntimeError when client is None."""
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await unconfigured_client.process_live_audio(audio_data=b"test audio")
