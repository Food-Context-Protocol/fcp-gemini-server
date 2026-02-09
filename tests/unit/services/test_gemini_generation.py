"""Tests for gemini_generation.py mixin classes."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import types

from fcp.services.gemini_generation import (
    GeminiCodeExecutionMixin,
    GeminiCombinedToolsMixin,
    GeminiGenerationMixin,
    GeminiGroundingMixin,
    GeminiImageMixin,
    GeminiMediaMixin,
    GeminiThinkingMixin,
    GeminiToolingMixin,
)


# Test base class with mocked dependencies
class MockGeminiService(
    GeminiGenerationMixin,
    GeminiToolingMixin,
    GeminiGroundingMixin,
    GeminiThinkingMixin,
    GeminiCodeExecutionMixin,
    GeminiMediaMixin,
    GeminiImageMixin,
    GeminiCombinedToolsMixin,
):
    """Mock service combining all mixins for testing."""

    def __init__(self, mock_client):
        self.mock_client = mock_client

    def _require_client(self):
        """Return the mock client."""
        return self.mock_client

    async def _prepare_parts(
        self,
        prompt: str,
        image_url: str | None = None,
        media_url: str | None = None,
        image_bytes: bytes | None = None,
        image_mime_type: str | None = None,
    ):
        """Return parts for testing."""
        parts = [types.Part(text=prompt)]
        if image_url:
            parts.append(types.Part(file_data=types.FileData(file_uri=image_url)))
        if media_url:
            parts.append(types.Part(file_data=types.FileData(file_uri=media_url)))
        if image_bytes:
            parts.append(
                types.Part(
                    inline_data=types.Blob(
                        mime_type=image_mime_type or "image/jpeg",
                        data=image_bytes,
                    )
                )
            )
        return parts


@pytest.fixture
def mock_client():
    """Create a mock Gemini client."""
    mock = MagicMock()
    mock.aio = MagicMock()
    mock.aio.models = MagicMock()
    return mock


@pytest.fixture
def service(mock_client):
    """Create a mock service with all mixins."""
    return MockGeminiService(mock_client)


class TestGeminiGenerationMixin:
    """Tests for GeminiGenerationMixin."""

    @pytest.mark.asyncio
    async def test_generate_content_basic(self, service, mock_client):
        """Test basic content generation."""
        # Mock response
        mock_response = MagicMock()
        mock_response.text = "Generated content"
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_content("Test prompt")

        assert result == "Generated content"
        mock_client.aio.models.generate_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_content_with_image(self, service, mock_client):
        """Test content generation with image URL."""
        mock_response = MagicMock()
        mock_response.text = "Image analysis"
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_content("Analyze this", image_url="https://example.com/image.jpg")

        assert result == "Image analysis"

    @pytest.mark.asyncio
    async def test_generate_content_empty_response(self, service, mock_client):
        """Test handling of empty response text."""
        mock_response = MagicMock()
        mock_response.text = None
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=0)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_content("Test")

        assert result == ""

    @pytest.mark.asyncio
    async def test_generate_content_stream(self, service, mock_client):
        """Test streaming content generation."""
        # Mock streaming response
        mock_chunk1 = MagicMock(text="Hello ")
        mock_chunk2 = MagicMock(text="world")
        mock_chunk3 = MagicMock(text=None)  # Empty chunk should be skipped

        async def mock_stream():
            for chunk in [mock_chunk1, mock_chunk2, mock_chunk3]:
                yield chunk

        mock_client.aio.models.generate_content_stream = AsyncMock(return_value=mock_stream())

        chunks = []
        async for chunk in service.generate_content_stream("Test prompt"):
            chunks.append(chunk)

        assert chunks == ["Hello ", "world"]

    @pytest.mark.asyncio
    async def test_generate_json_dict(self, service, mock_client):
        """Test JSON generation returning a dict."""
        mock_response = MagicMock()
        mock_response.text = '{"key": "value", "count": 42}'
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_json("Test prompt")

        assert result == {"key": "value", "count": 42}

    @pytest.mark.asyncio
    async def test_generate_json_list_wrapped(self, service, mock_client):
        """Test JSON generation returning a list (should be wrapped)."""
        mock_response = MagicMock()
        mock_response.text = "[1, 2, 3]"
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_json("Test prompt")

        assert result == {"items": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_generate_json_with_image_bytes(self, service, mock_client):
        """Test JSON generation with image bytes."""
        mock_response = MagicMock()
        mock_response.text = '{"analysis": "complete"}'
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_json(
            "Analyze",
            image_bytes=b"fake_image_data",
            image_mime_type="image/png",
        )

        assert result == {"analysis": "complete"}

    @pytest.mark.asyncio
    async def test_generate_json_stream(self, service, mock_client):
        """Test streaming JSON generation."""
        mock_chunk1 = MagicMock(text='{"key"')
        mock_chunk2 = MagicMock(text=': "value"')
        mock_chunk3 = MagicMock(text="}")

        async def mock_stream():
            for chunk in [mock_chunk1, mock_chunk2, mock_chunk3]:
                yield chunk

        # The method itself returns the stream, not wrapped in a coroutine
        mock_client.aio.models.generate_content_stream = MagicMock(return_value=mock_stream())

        chunks = []
        async for chunk in service.generate_json_stream("Test"):
            chunks.append(chunk)

        assert chunks == ['{"key"', ': "value"', "}"]


class TestGeminiToolingMixin:
    """Tests for GeminiToolingMixin."""

    @pytest.mark.asyncio
    async def test_generate_with_tools_basic(self, service, mock_client):
        """Test tool calling with basic response."""
        # Mock function call in response
        mock_function_call = MagicMock()
        mock_function_call.name = "get_weather"
        mock_function_call.args = {"location": "San Francisco"}

        mock_part = MagicMock()
        mock_part.function_call = mock_function_call

        mock_content = MagicMock()
        mock_content.parts = [mock_part]

        mock_candidate = MagicMock()
        mock_candidate.content = mock_content

        mock_response = MagicMock()
        mock_response.text = "I'll check the weather for you."
        mock_response.candidates = [mock_candidate]
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        tools = [
            {
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {"type": "object", "properties": {}},
            }
        ]

        result = await service.generate_with_tools("What's the weather?", tools)

        assert result["text"] == "I'll check the weather for you."
        assert len(result["function_calls"]) == 1
        assert result["function_calls"][0]["name"] == "get_weather"
        assert result["function_calls"][0]["args"] == {"location": "San Francisco"}

    @pytest.mark.asyncio
    async def test_generate_with_tools_no_calls(self, service, mock_client):
        """Test tool calling when no functions are called."""
        mock_response = MagicMock()
        mock_response.text = "Just a regular response"
        mock_response.candidates = []
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        tools = [{"name": "test_tool", "parameters": {}}]
        result = await service.generate_with_tools("Test", tools)

        assert result["function_calls"] == []

    @pytest.mark.asyncio
    async def test_generate_with_tools_multiple_calls(self, service, mock_client):
        """Test multiple function calls in response."""
        # First function call
        mock_call1 = MagicMock(name="func1", args={"arg1": "value1"})
        mock_part1 = MagicMock(function_call=mock_call1)

        # Second function call
        mock_call2 = MagicMock(name="func2", args={"arg2": "value2"})
        mock_part2 = MagicMock(function_call=mock_call2)

        mock_content = MagicMock(parts=[mock_part1, mock_part2])
        mock_candidate = MagicMock(content=mock_content)

        mock_response = MagicMock(
            text="Response",
            candidates=[mock_candidate],
            usage_metadata=MagicMock(prompt_token_count=10, candidates_token_count=5),
        )

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_with_tools("Test", [])

        assert len(result["function_calls"]) == 2


class TestGeminiGroundingMixin:
    """Tests for GeminiGroundingMixin."""

    @pytest.mark.asyncio
    @patch("fcp.services.gemini_generation._extract_grounding_sources")
    async def test_generate_with_grounding(self, mock_extract_sources, service, mock_client):
        """Test grounding with Google Search."""
        mock_response = MagicMock()
        mock_response.text = "Search result text"
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)

        mock_extract_sources.return_value = [{"uri": "https://example.com", "title": "Example"}]

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_with_grounding("What is FCP?")

        assert result["text"] == "Search result text"
        assert len(result["sources"]) == 1
        assert result["sources"][0]["uri"] == "https://example.com"

    @pytest.mark.asyncio
    @patch("fcp.services.gemini_generation._extract_grounding_sources")
    async def test_generate_json_with_grounding(self, mock_extract_sources, service, mock_client):
        """Test JSON generation with grounding."""
        mock_response = MagicMock()
        mock_response.text = '{"answer": "test"}'
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)

        mock_extract_sources.return_value = []

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_json_with_grounding("Test query")

        assert result["data"] == {"answer": "test"}
        assert result["sources"] == []

    @pytest.mark.asyncio
    async def test_generate_json_with_grounding_empty_response(self, service, mock_client):
        """Test grounding with None response text raises error."""
        mock_response = MagicMock()
        mock_response.text = None
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=0)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with pytest.raises(ValueError, match="Gemini returned empty response"):
            await service.generate_json_with_grounding("Test")


class TestGeminiThinkingMixin:
    """Tests for GeminiThinkingMixin."""

    @pytest.mark.asyncio
    @patch("fcp.services.gemini_generation._get_thinking_budget")
    async def test_generate_with_thinking(self, mock_get_budget, service, mock_client):
        """Test generation with thinking."""
        mock_get_budget.return_value = 32768

        mock_response = MagicMock()
        mock_response.text = "Thoughtful response"
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_with_thinking("Complex question", "high")

        assert result == "Thoughtful response"
        mock_get_budget.assert_called_once_with("high")

    @pytest.mark.asyncio
    @patch("fcp.services.gemini_generation._get_thinking_budget")
    async def test_generate_json_with_thinking_no_output(self, mock_get_budget, service, mock_client):
        """Test JSON thinking without thinking output."""
        mock_get_budget.return_value = 16384

        mock_response = MagicMock()
        mock_response.text = '{"result": "analyzed"}'
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_json_with_thinking("Analyze", "medium", include_thinking_output=False)

        assert result == {"result": "analyzed"}

    @pytest.mark.asyncio
    @patch("fcp.services.gemini_generation._extract_thinking_content")
    @patch("fcp.services.gemini_generation._get_thinking_budget")
    async def test_generate_json_with_thinking_with_output(
        self, mock_get_budget, mock_extract_thinking, service, mock_client
    ):
        """Test JSON thinking with thinking output."""
        mock_get_budget.return_value = 16384
        mock_extract_thinking.return_value = "My reasoning was..."

        mock_response = MagicMock()
        mock_response.text = '{"result": "analyzed"}'
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_json_with_thinking("Analyze", "medium", include_thinking_output=True)

        assert result["analysis"] == {"result": "analyzed"}
        assert result["thinking"] == "My reasoning was..."

    @pytest.mark.asyncio
    @patch("fcp.services.gemini_generation._get_thinking_budget")
    async def test_generate_with_large_context(self, mock_get_budget, service, mock_client):
        """Test large context generation."""
        mock_get_budget.return_value = 32768

        mock_response = MagicMock()
        mock_response.text = "Large context response"
        mock_response.usage_metadata = MagicMock(prompt_token_count=100000, candidates_token_count=1000)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_with_large_context("Long document...", "high")

        assert result == "Large context response"

    @pytest.mark.asyncio
    @patch("fcp.services.gemini_generation._get_thinking_budget")
    async def test_generate_json_with_large_context_dict(self, mock_get_budget, service, mock_client):
        """Test large context JSON returning dict."""
        mock_get_budget.return_value = 32768

        mock_response = MagicMock()
        mock_response.text = '{"summary": "analyzed"}'
        mock_response.usage_metadata = MagicMock(prompt_token_count=100000, candidates_token_count=100)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_json_with_large_context("Long doc", "high")

        assert result == {"summary": "analyzed"}

    @pytest.mark.asyncio
    @patch("fcp.services.gemini_generation._get_thinking_budget")
    async def test_generate_json_with_large_context_list(self, mock_get_budget, service, mock_client):
        """Test large context JSON returning list (wrapped)."""
        mock_get_budget.return_value = 32768

        mock_response = MagicMock()
        mock_response.text = '[{"item": 1}, {"item": 2}]'
        mock_response.usage_metadata = MagicMock(prompt_token_count=100000, candidates_token_count=50)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_json_with_large_context("Long doc", "high")

        assert result == {"items": [{"item": 1}, {"item": 2}]}

    @pytest.mark.asyncio
    async def test_generate_json_with_large_context_empty(self, service, mock_client):
        """Test large context with None response raises error."""
        mock_response = MagicMock()
        mock_response.text = None
        mock_response.usage_metadata = MagicMock(prompt_token_count=100000, candidates_token_count=0)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with pytest.raises(ValueError, match="Gemini returned empty response"):
            await service.generate_json_with_large_context("Test")


class TestGeminiCodeExecutionMixin:
    """Tests for GeminiCodeExecutionMixin."""

    @pytest.mark.asyncio
    async def test_generate_with_code_execution_basic(self, service, mock_client):
        """Test code execution with basic response."""
        mock_executable = MagicMock(code="print('hello')")
        mock_result = MagicMock(output="hello\n")

        mock_part1 = MagicMock(executable_code=mock_executable, code_execution_result=None)
        mock_part2 = MagicMock(executable_code=None, code_execution_result=mock_result)

        mock_content = MagicMock(parts=[mock_part1, mock_part2])
        mock_candidate = MagicMock(content=mock_content)

        mock_response = MagicMock(
            text="Executed code",
            candidates=[mock_candidate],
            usage_metadata=MagicMock(prompt_token_count=10, candidates_token_count=5),
        )

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_with_code_execution("Calculate 2+2")

        assert result["text"] == "Executed code"
        assert result["code"] == "print('hello')"
        assert result["execution_result"] == "hello\n"

    @pytest.mark.asyncio
    async def test_generate_with_code_execution_no_code(self, service, mock_client):
        """Test code execution when no code is generated."""
        mock_response = MagicMock(
            text="No code needed",
            candidates=[],
            usage_metadata=MagicMock(prompt_token_count=10, candidates_token_count=5),
        )

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_with_code_execution("Simple question")

        assert result["code"] is None
        assert result["execution_result"] is None

    @pytest.mark.asyncio
    async def test_generate_json_with_agentic_vision(self, service, mock_client):
        """Test agentic vision with code execution."""
        mock_executable = MagicMock(code="analyze_image()")
        mock_result = MagicMock(output="{'detected': ['apple']}")

        mock_part1 = MagicMock(executable_code=mock_executable, code_execution_result=None)
        mock_part2 = MagicMock(executable_code=None, code_execution_result=mock_result)

        mock_content = MagicMock(parts=[mock_part1, mock_part2])
        mock_candidate = MagicMock(content=mock_content)

        mock_response = MagicMock(
            text='{"objects": ["apple"]}',
            candidates=[mock_candidate],
            usage_metadata=MagicMock(prompt_token_count=10, candidates_token_count=5),
        )

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_json_with_agentic_vision(
            "What's in the image?", "https://example.com/image.jpg"
        )

        assert result["analysis"] == {"objects": ["apple"]}
        assert result["code"] == "analyze_image()"
        assert result["execution_result"] == "{'detected': ['apple']}"

    @pytest.mark.asyncio
    async def test_generate_json_with_agentic_vision_empty(self, service, mock_client):
        """Test agentic vision with None response raises error."""
        mock_response = MagicMock(
            text=None,
            candidates=[],
            usage_metadata=MagicMock(prompt_token_count=10, candidates_token_count=0),
        )

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with pytest.raises(ValueError, match="Gemini returned empty response"):
            await service.generate_json_with_agentic_vision("Test", "http://img.jpg")


class TestGeminiMediaMixin:
    """Tests for GeminiMediaMixin."""

    @pytest.mark.asyncio
    async def test_generate_json_with_media_resolution_high(self, service, mock_client):
        """Test media resolution with high quality."""
        mock_response = MagicMock()
        mock_response.text = '{"analysis": "high quality"}'
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_json_with_media_resolution(
            "Analyze", "https://example.com/image.jpg", resolution="high"
        )

        assert result == {"analysis": "high quality"}

    @pytest.mark.asyncio
    async def test_generate_json_with_media_resolution_medium(self, service, mock_client):
        """Test media resolution with medium quality."""
        mock_response = MagicMock()
        mock_response.text = '{"analysis": "medium"}'
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_json_with_media_resolution(
            "Analyze", "https://example.com/image.jpg", resolution="medium"
        )

        assert result == {"analysis": "medium"}

    @pytest.mark.asyncio
    async def test_generate_json_with_media_resolution_list(self, service, mock_client):
        """Test media resolution returning list (wrapped)."""
        mock_response = MagicMock()
        mock_response.text = '[{"item": 1}]'
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await service.generate_json_with_media_resolution("Analyze", "https://example.com/image.jpg")

        assert result == {"items": [{"item": 1}]}

    @pytest.mark.asyncio
    async def test_generate_json_with_url_context(self, service, mock_client):
        """Test URL context analysis."""
        mock_response = MagicMock()
        mock_response.text = '{"summary": "analyzed"}'
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        urls = ["https://example.com/doc1", "https://example.com/doc2"]
        result = await service.generate_json_with_url_context("Summarize", urls)

        assert result["data"] == {"summary": "analyzed"}
        assert result["sources"] == urls


class TestGeminiImageMixin:
    """Tests for GeminiImageMixin."""

    @pytest.mark.asyncio
    async def test_generate_image_single(self, service, mock_client):
        """Test single image generation."""
        # Mock image response
        image_bytes = b"fake_png_data"
        mock_image = MagicMock()
        mock_image.image = MagicMock(image_bytes=image_bytes)

        mock_response = MagicMock()
        mock_response.generated_images = [mock_image]

        mock_client.aio.models.generate_images = AsyncMock(return_value=mock_response)

        result = await service.generate_image("A beautiful sunset")

        assert result["count"] == 1
        assert result["mime_type"] == "image/png"
        assert len(result["images"]) == 1
        # Verify base64 encoding
        assert result["images"][0] == base64.b64encode(image_bytes).decode("utf-8")

    @pytest.mark.asyncio
    async def test_generate_image_multiple(self, service, mock_client):
        """Test multiple image generation."""
        image1 = MagicMock(image=MagicMock(image_bytes=b"image1"))
        image2 = MagicMock(image=MagicMock(image_bytes=b"image2"))

        mock_response = MagicMock(generated_images=[image1, image2])

        mock_client.aio.models.generate_images = AsyncMock(return_value=mock_response)

        result = await service.generate_image("Multiple views", aspect_ratio="16:9", number_of_images=2)

        assert result["count"] == 2
        assert len(result["images"]) == 2

    @pytest.mark.asyncio
    async def test_generate_image_no_images(self, service, mock_client):
        """Test image generation with no results."""
        mock_response = MagicMock(generated_images=[])

        mock_client.aio.models.generate_images = AsyncMock(return_value=mock_response)

        result = await service.generate_image("Test")

        assert result["count"] == 0
        assert result["images"] == []

    @pytest.mark.asyncio
    async def test_generate_image_missing_attributes(self, service, mock_client):
        """Test image generation with malformed response."""
        # Mock image without image_bytes attribute
        mock_image = MagicMock(spec=[])

        mock_response = MagicMock(generated_images=[mock_image])

        mock_client.aio.models.generate_images = AsyncMock(return_value=mock_response)

        result = await service.generate_image("Test")

        assert result["count"] == 0
        assert result["images"] == []


class TestGeminiCombinedToolsMixin:
    """Tests for GeminiCombinedToolsMixin."""

    def test_build_combined_tools_all_enabled(self, service):
        """Test building tools with all features enabled."""
        function_tools = [{"name": "test_func", "parameters": {}}]

        tools = service._build_combined_tools(
            function_tools,
            enable_grounding=True,
            enable_code_execution=True,
        )

        assert len(tools) == 3
        # Check types (order may vary but all should be present)
        assert any("google_search" in str(t) for t in tools)
        assert any("function_declarations" in str(t) for t in tools)
        assert any("code_execution" in str(t) for t in tools)

    def test_build_combined_tools_none_enabled(self, service):
        """Test building tools with no features enabled."""
        tools = service._build_combined_tools(
            None,
            enable_grounding=False,
            enable_code_execution=False,
        )

        assert len(tools) == 0

    def test_extract_combined_tool_response_complete(self, service):
        """Test extracting all tool response types."""
        # Mock function call
        mock_func_call = MagicMock()
        mock_func_call.name = "test_func"
        mock_func_call.args = {"arg": "value"}
        mock_func_part = MagicMock(
            function_call=mock_func_call,
            executable_code=None,
            code_execution_result=None,
        )

        # Mock grounding
        mock_web = MagicMock(uri="https://example.com", title="Example")
        mock_chunk = MagicMock(web=mock_web)
        mock_grounding = MagicMock(grounding_chunks=[mock_chunk])

        # Mock code execution
        mock_code = MagicMock(code="print('test')")
        mock_code_part = MagicMock(
            executable_code=mock_code,
            function_call=None,
            code_execution_result=None,
        )

        mock_result = MagicMock(output="test\n")
        mock_result_part = MagicMock(
            code_execution_result=mock_result,
            executable_code=None,
            function_call=None,
        )

        mock_content = MagicMock(parts=[mock_func_part, mock_code_part, mock_result_part])
        mock_candidate = MagicMock(
            content=mock_content,
            grounding_metadata=mock_grounding,
        )

        mock_response = MagicMock(candidates=[mock_candidate])

        (
            function_calls,
            sources,
            code,
            execution_result,
        ) = service._extract_combined_tool_response(mock_response)

        assert len(function_calls) == 1
        assert function_calls[0]["name"] == "test_func"
        assert len(sources) == 1
        assert sources[0]["uri"] == "https://example.com"
        assert code == "print('test')"
        assert execution_result == "test\n"

    def test_extract_combined_tool_response_empty(self, service):
        """Test extracting from response with no tools."""
        mock_response = MagicMock(candidates=[])

        (
            function_calls,
            sources,
            code,
            execution_result,
        ) = service._extract_combined_tool_response(mock_response)

        assert function_calls == []
        assert sources == []
        assert code is None
        assert execution_result is None

    @pytest.mark.asyncio
    @patch("fcp.services.gemini_generation._get_thinking_budget")
    async def test_generate_with_all_tools(self, mock_get_budget, service, mock_client):
        """Test generation with all tools combined."""
        mock_get_budget.return_value = 32768

        mock_response = MagicMock(
            text="Combined response",
            candidates=[],
            usage_metadata=MagicMock(prompt_token_count=10, candidates_token_count=5),
        )

        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        function_tools = [{"name": "test", "parameters": {}}]
        result = await service.generate_with_all_tools(
            "Complex query",
            function_tools=function_tools,
            enable_grounding=True,
            enable_code_execution=True,
            thinking_level="high",
        )

        assert result["text"] == "Combined response"
        assert "function_calls" in result
        assert "sources" in result
        assert "code" in result
        assert "execution_result" in result
