"""Tests for FCP services."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fcp.services.gemini import _parse_json_response


class TestParseJsonResponse:
    """Tests for _parse_json_response helper function."""

    def test_parses_pure_json_object(self):
        """Should parse valid JSON object directly."""
        result = _parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parses_pure_json_array(self):
        """Should parse valid JSON array directly."""
        result = _parse_json_response("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_parses_json_with_whitespace(self):
        """Should handle JSON with leading/trailing whitespace."""
        result = _parse_json_response('  {"key": "value"}  ')
        assert result == {"key": "value"}

    def test_parses_markdown_wrapped_json(self):
        """Should extract JSON from markdown code blocks."""
        text = """Here is the result:

```json
{"recommendations": [{"name": "Pizza"}]}
```

Enjoy!"""
        result = _parse_json_response(text)
        assert result == {"recommendations": [{"name": "Pizza"}]}

    def test_parses_generic_code_block(self):
        """Should extract JSON from generic code blocks."""
        text = """```
{"status": "ok"}
```"""
        result = _parse_json_response(text)
        assert result == {"status": "ok"}

    def test_parses_json_embedded_in_prose(self):
        """Should extract JSON embedded in explanatory text."""
        text = 'Based on analysis: {"result": true} End of response.'
        result = _parse_json_response(text)
        assert result == {"result": True}

    def test_raises_on_empty_response(self):
        """Should raise ValueError for empty response."""
        with pytest.raises(ValueError, match="Empty response"):
            _parse_json_response("")

    def test_raises_on_whitespace_only(self):
        """Should raise ValueError for whitespace-only response."""
        with pytest.raises(ValueError, match="Empty response"):
            _parse_json_response("   \n\t  ")

    def test_raises_on_invalid_json(self):
        """Should raise ValueError for unparseable text."""
        with pytest.raises(ValueError, match="Failed to parse JSON"):
            _parse_json_response("This is not JSON at all")

    def test_handles_nested_json(self):
        """Should handle deeply nested JSON structures."""
        text = '{"outer": {"inner": {"deep": [1, 2, 3]}}}'
        result = _parse_json_response(text)
        assert result == {"outer": {"inner": {"deep": [1, 2, 3]}}}

    def test_handles_unicode(self):
        """Should handle unicode characters in JSON."""
        text = '{"name": "寿司", "emoji": "🍣"}'
        result = _parse_json_response(text)
        assert result == {"name": "寿司", "emoji": "🍣"}

    def test_handles_bom_characters(self):
        """Should handle BOM (byte order mark) characters."""
        # UTF-8 BOM followed by valid JSON
        text = '\ufeff{"key": "value"}'
        result = _parse_json_response(text)
        assert result == {"key": "value"}

    def test_raises_on_none_input(self):
        """Should raise ValueError for None input."""
        with pytest.raises(ValueError, match="Empty response"):
            _parse_json_response(None)


class TestGeminiClient:
    """Tests for Gemini service."""

    @pytest.mark.asyncio
    async def test_generate_content(self):
        """Test basic content generation."""
        with patch("fcp.services.gemini.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = "Test response"

            # Mock the aio.models.generate_content async method
            async def mock_generate(*args, **kwargs):
                return mock_response

            mock_client.aio.models.generate_content = mock_generate

            from fcp.services.gemini import GeminiClient

            client = GeminiClient()
            client.client = mock_client

            result = await client.generate_content("Test prompt")
            assert result == "Test response"

    @pytest.mark.asyncio
    async def test_generate_json_with_json_mode(self):
        """Test JSON generation using Gemini's JSON mode."""
        with patch("fcp.services.gemini.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            # JSON mode returns pure JSON, no markdown wrapper
            mock_response.text = '{"key": "value"}'

            async def mock_generate(*args, **kwargs):
                return mock_response

            mock_client.aio.models.generate_content = mock_generate

            from fcp.services.gemini import GeminiClient

            client = GeminiClient()
            client.client = mock_client

            result = await client.generate_json("Test prompt")
            assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_generate_json_with_whitespace(self):
        """Test JSON generation handles whitespace in response."""
        with patch("fcp.services.gemini.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            # Response with extra whitespace (which .strip() handles)
            mock_response.text = '  {"key": "value"}  \n'

            async def mock_generate(*args, **kwargs):
                return mock_response

            mock_client.aio.models.generate_content = mock_generate

            from fcp.services.gemini import GeminiClient

            client = GeminiClient()
            client.client = mock_client

            result = await client.generate_json("Test prompt")
            assert result == {"key": "value"}

    def test_client_requires_api_key(self):
        """Test that client checks for API key."""
        with patch("fcp.services.gemini.GEMINI_API_KEY", None), patch("fcp.services.gemini.genai"):
            from fcp.services.gemini import GeminiClient

            client = GeminiClient()
            # Client should be None when no API key
            assert client.client is None

    @pytest.mark.asyncio
    async def test_generate_json_with_markdown_fallback(self):
        """Test JSON generation handles markdown-wrapped response via fallback."""
        with patch("fcp.services.gemini.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            # Sometimes JSON mode still returns markdown (edge case)
            mock_response.text = '```json\n{"key": "value"}\n```'

            async def mock_generate(*args, **kwargs):
                return mock_response

            mock_client.aio.models.generate_content = mock_generate

            from fcp.services.gemini import GeminiClient

            client = GeminiClient()
            client.client = mock_client

            result = await client.generate_json("Test prompt")
            assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_generate_json_raises_on_invalid_response(self):
        """Test JSON generation raises ValueError for unparseable response."""
        with patch("fcp.services.gemini.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = "This is not JSON at all"

            async def mock_generate(*args, **kwargs):
                return mock_response

            mock_client.aio.models.generate_content = mock_generate

            from fcp.services.gemini import GeminiClient

            client = GeminiClient()
            client.client = mock_client

            with pytest.raises(ValueError, match="Failed to parse JSON"):
                await client.generate_json("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_json_raises_on_empty_response(self):
        """Test JSON generation raises ValueError for empty response."""
        with patch("fcp.services.gemini.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = "   "  # Whitespace only

            async def mock_generate(*args, **kwargs):
                return mock_response

            mock_client.aio.models.generate_content = mock_generate

            from fcp.services.gemini import GeminiClient

            client = GeminiClient()
            client.client = mock_client

            with pytest.raises(ValueError, match="Empty response"):
                await client.generate_json("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_json_with_grounding_returns_data_and_sources(self):
        """Test JSON generation with grounding returns structured data and sources."""
        with patch("fcp.services.gemini.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = '{"recall_info": "No recalls found", "has_active_recall": false}'

            # Mock grounding metadata
            mock_chunk = MagicMock()
            mock_chunk.web = MagicMock()
            mock_chunk.web.uri = "https://fda.gov/recalls"
            mock_chunk.web.title = "FDA Recalls"

            mock_metadata = MagicMock()
            mock_metadata.grounding_chunks = [mock_chunk]

            mock_candidate = MagicMock()
            mock_candidate.grounding_metadata = mock_metadata

            mock_response.candidates = [mock_candidate]

            # Use AsyncMock to capture call args
            mock_generate = AsyncMock(return_value=mock_response)
            mock_client.aio.models.generate_content = mock_generate

            from fcp.services.gemini import GeminiClient

            client = GeminiClient()
            client.client = mock_client

            result = await client.generate_json_with_grounding("Test prompt")

            # Verify response parsing
            assert "data" in result
            assert "sources" in result
            assert result["data"]["recall_info"] == "No recalls found"
            assert result["data"]["has_active_recall"] is False
            assert len(result["sources"]) == 1
            assert result["sources"][0]["uri"] == "https://fda.gov/recalls"

            # Verify config passed to Gemini (JSON mode + Google Search grounding)
            mock_generate.assert_called_once()
            call_kwargs = mock_generate.call_args.kwargs
            config = call_kwargs.get("config")
            assert config is not None, "config argument was not passed to generate_content"
            assert config.response_mime_type == "application/json", "JSON mode not configured"
            assert config.tools is not None and len(config.tools) > 0, "No tools configured"
            assert any(hasattr(tool, "google_search") and tool.google_search is not None for tool in config.tools), (
                "Google Search grounding not configured"
            )

    @pytest.mark.asyncio
    async def test_generate_json_with_grounding_handles_no_sources(self):
        """Test JSON generation with grounding handles response without sources."""
        with patch("fcp.services.gemini.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = '{"has_alert": false}'

            mock_candidate = MagicMock()
            mock_candidate.grounding_metadata = None
            mock_response.candidates = [mock_candidate]

            async def mock_generate(*args, **kwargs):
                return mock_response

            mock_client.aio.models.generate_content = mock_generate

            from fcp.services.gemini import GeminiClient

            client = GeminiClient()
            client.client = mock_client

            result = await client.generate_json_with_grounding("Test prompt")

            assert "data" in result
            assert "sources" in result
            assert result["data"]["has_alert"] is False
            assert len(result["sources"]) == 0

    @pytest.mark.asyncio
    async def test_generate_json_with_grounding_raises_on_invalid_json(self):
        """Test JSON generation with grounding raises ValueError for invalid JSON."""
        with patch("fcp.services.gemini.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = "This is not JSON"
            mock_response.candidates = []

            async def mock_generate(*args, **kwargs):
                return mock_response

            mock_client.aio.models.generate_content = mock_generate

            from fcp.services.gemini import GeminiClient

            client = GeminiClient()
            client.client = mock_client

            with pytest.raises(ValueError, match="Failed to parse JSON"):
                await client.generate_json_with_grounding("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_json_with_grounding_requires_api_key(self):
        """Test JSON generation with grounding requires API key."""
        with patch("fcp.services.gemini.GEMINI_API_KEY", None), patch("fcp.services.gemini.genai"):
            from fcp.services.gemini import GeminiClient

            client = GeminiClient()

            with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
                await client.generate_json_with_grounding("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_json_with_grounding_empty_chunks(self):
        """Test JSON generation with grounding handles empty grounding_chunks."""
        with patch("fcp.services.gemini.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = '{"has_alert": false}'

            # Grounding metadata with empty chunks list
            mock_metadata = MagicMock()
            mock_metadata.grounding_chunks = []

            mock_candidate = MagicMock()
            mock_candidate.grounding_metadata = mock_metadata
            mock_response.candidates = [mock_candidate]

            async def mock_generate(*args, **kwargs):
                return mock_response

            mock_client.aio.models.generate_content = mock_generate

            from fcp.services.gemini import GeminiClient

            client = GeminiClient()
            client.client = mock_client

            result = await client.generate_json_with_grounding("Test prompt")

            assert result["sources"] == []

    @pytest.mark.asyncio
    async def test_generate_json_with_grounding_chunks_without_web(self):
        """Test JSON generation with grounding handles chunks without web attribute."""
        with patch("fcp.services.gemini.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = '{"has_alert": false}'

            # Chunk without web attribute (spec returns False for hasattr check)
            mock_chunk = MagicMock(spec=[])
            mock_metadata = MagicMock()
            mock_metadata.grounding_chunks = [mock_chunk]

            mock_candidate = MagicMock()
            mock_candidate.grounding_metadata = mock_metadata
            mock_response.candidates = [mock_candidate]

            async def mock_generate(*args, **kwargs):
                return mock_response

            mock_client.aio.models.generate_content = mock_generate

            from fcp.services.gemini import GeminiClient

            client = GeminiClient()
            client.client = mock_client

            result = await client.generate_json_with_grounding("Test prompt")

            assert result["sources"] == []


class TestExtractGroundingSources:
    """Tests for _extract_grounding_sources helper function."""

    def test_no_candidates_returns_empty(self):
        """Should return empty list when no candidates."""
        from fcp.services.gemini import _extract_grounding_sources

        mock_response = MagicMock()
        mock_response.candidates = []

        result = _extract_grounding_sources(mock_response)
        assert result == []

    def test_no_grounding_metadata_returns_empty(self):
        """Should return empty list when no grounding_metadata."""
        from fcp.services.gemini import _extract_grounding_sources

        mock_candidate = MagicMock()
        mock_candidate.grounding_metadata = None
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]

        result = _extract_grounding_sources(mock_response)
        assert result == []

    def test_empty_grounding_chunks_returns_empty(self):
        """Should return empty list when grounding_chunks is empty."""
        from fcp.services.gemini import _extract_grounding_sources

        mock_metadata = MagicMock()
        mock_metadata.grounding_chunks = []
        mock_candidate = MagicMock()
        mock_candidate.grounding_metadata = mock_metadata
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]

        result = _extract_grounding_sources(mock_response)
        assert result == []

    def test_chunks_without_web_attribute_returns_empty(self):
        """Should skip chunks without web attribute."""
        from fcp.services.gemini import _extract_grounding_sources

        mock_chunk = MagicMock(spec=[])  # spec=[] makes hasattr return False
        mock_metadata = MagicMock()
        mock_metadata.grounding_chunks = [mock_chunk]
        mock_candidate = MagicMock()
        mock_candidate.grounding_metadata = mock_metadata
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]

        result = _extract_grounding_sources(mock_response)
        assert result == []

    def test_extracts_web_sources_correctly(self):
        """Should extract uri and title from web chunks."""
        from fcp.services.gemini import _extract_grounding_sources

        mock_chunk = MagicMock()
        mock_chunk.web = MagicMock()
        mock_chunk.web.uri = "https://example.com"
        mock_chunk.web.title = "Example Site"

        mock_metadata = MagicMock()
        mock_metadata.grounding_chunks = [mock_chunk]
        mock_candidate = MagicMock()
        mock_candidate.grounding_metadata = mock_metadata
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]

        result = _extract_grounding_sources(mock_response)
        assert len(result) == 1
        assert result[0]["uri"] == "https://example.com"
        assert result[0]["title"] == "Example Site"


class TestAgenticVisionService:
    """Tests for generate_json_with_agentic_vision method."""

    @pytest.mark.asyncio
    async def test_generate_json_with_agentic_vision_success(self):
        """Test Agentic Vision returns analysis with code execution metadata."""
        with patch("fcp.services.gemini.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = '{"dish_name": "Sushi", "item_count": 8}'

            # Mock code execution parts
            mock_code_part = MagicMock()
            mock_code_part.executable_code = MagicMock()
            mock_code_part.executable_code.code = "# Count sushi pieces"
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

            mock_generate = AsyncMock(return_value=mock_response)
            mock_client.aio.models.generate_content = mock_generate

            from fcp.services.gemini import GeminiClient

            client = GeminiClient()
            client.client = mock_client

            # Mock _prepare_parts to avoid httpx calls
            async def mock_prepare_parts(*args, **kwargs):
                return [MagicMock()]

            setattr(client, "_prepare_parts", mock_prepare_parts)

            result = await client.generate_json_with_agentic_vision(
                prompt="Analyze this image",
                image_url="https://storage.googleapis.com/test.jpg",
            )

            assert "analysis" in result
            assert result["analysis"]["dish_name"] == "Sushi"
            assert result["code"] == "# Count sushi pieces"
            assert result["execution_result"] == "8"

    @pytest.mark.asyncio
    async def test_generate_json_with_agentic_vision_no_code_execution(self):
        """Test Agentic Vision when model doesn't execute code."""
        with patch("fcp.services.gemini.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = '{"dish_name": "Salad"}'

            # Parts without code execution
            mock_part = MagicMock()
            mock_part.executable_code = None
            mock_part.code_execution_result = None

            mock_candidate = MagicMock()
            mock_candidate.content.parts = [mock_part]
            mock_response.candidates = [mock_candidate]

            mock_response.usage_metadata = MagicMock()
            mock_response.usage_metadata.prompt_token_count = 50
            mock_response.usage_metadata.candidates_token_count = 25

            mock_generate = AsyncMock(return_value=mock_response)
            mock_client.aio.models.generate_content = mock_generate

            from fcp.services.gemini import GeminiClient

            client = GeminiClient()
            client.client = mock_client

            async def mock_prepare_parts(*args, **kwargs):
                return [MagicMock()]

            setattr(client, "_prepare_parts", mock_prepare_parts)

            result = await client.generate_json_with_agentic_vision(
                prompt="Analyze",
                image_url="https://storage.googleapis.com/test.jpg",
            )

            assert result["analysis"]["dish_name"] == "Salad"
            assert result["code"] is None
            assert result["execution_result"] is None

    @pytest.mark.asyncio
    async def test_generate_json_with_agentic_vision_raises_without_client(self):
        """Test Agentic Vision raises RuntimeError when client not configured."""
        with patch("fcp.services.gemini.GEMINI_API_KEY", None), patch("fcp.services.gemini.genai"):
            from fcp.services.gemini import GeminiClient

            client = GeminiClient()
            client.client = None

            with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
                await client.generate_json_with_agentic_vision(
                    prompt="Test",
                    image_url="https://example.com/test.jpg",
                )
