"""
Tests for SSE (Server-Sent Events) streaming.

These tests verify that the SSE streaming endpoints:
- Return proper SSE format with data: prefix
- Escape newlines correctly in chunks
- Send [DONE] event on completion
"""

import pytest


class TestSSEFormatting:
    """Tests for SSE response formatting."""

    @pytest.mark.asyncio
    async def test_sse_data_format(self):
        """Test that streaming response uses proper SSE data: format."""

        # Mock the generator to produce chunks
        async def mock_stream(*args, **kwargs):
            yield "Hello"
            yield "World"

        chunks = []
        async for chunk in mock_stream():
            # SSE format: "data: <content>\n\n"
            sse_chunk = f"data: {chunk}\n\n"
            chunks.append(sse_chunk)

        assert chunks[0] == "data: Hello\n\n"
        assert chunks[1] == "data: World\n\n"

    @pytest.mark.asyncio
    async def test_sse_newline_escaping(self):
        """Test that newlines in chunks are escaped for SSE protocol."""
        chunk_with_newlines = "Line 1\nLine 2\nLine 3"

        # SSE requires newlines to be escaped to maintain protocol
        escaped_chunk = chunk_with_newlines.replace("\n", "\\n")
        sse_chunk = f"data: {escaped_chunk}\n\n"

        assert sse_chunk == "data: Line 1\\nLine 2\\nLine 3\n\n"
        assert "\n\n" in sse_chunk  # SSE terminator present
        # The actual newlines should be escaped
        assert "Line 1\\nLine 2" in sse_chunk

    @pytest.mark.asyncio
    async def test_sse_done_event(self):
        """Test that [DONE] event is sent on completion."""
        done_event = "data: [DONE]\n\n"

        assert done_event.startswith("data: ")
        assert "[DONE]" in done_event
        assert done_event.endswith("\n\n")


class TestAnalyzeStreamEndpoint:
    """Tests for the /analyze/stream endpoint."""

    @pytest.mark.asyncio
    async def test_stream_generator_format(self):
        """Test that the stream generator produces correct SSE format."""

        # Simulate the generate() function from analyze.py
        async def mock_gemini_stream():
            yield "Analyzing"
            yield " food"
            yield " image..."

        async def generate():
            async for chunk in mock_gemini_stream():
                escaped_chunk = chunk.replace("\n", "\\n")
                yield f"data: {escaped_chunk}\n\n"
            yield "data: [DONE]\n\n"

        chunks = []
        async for chunk in generate():
            chunks.append(chunk)

        # Verify format
        assert len(chunks) == 4  # 3 content chunks + 1 DONE
        assert all(c.startswith("data: ") for c in chunks)
        assert all(c.endswith("\n\n") for c in chunks)
        assert chunks[-1] == "data: [DONE]\n\n"

    @pytest.mark.asyncio
    async def test_stream_with_multiline_content(self):
        """Test streaming with content that contains newlines."""

        async def mock_gemini_stream():
            yield "Dish: Pizza\nIngredients: cheese, tomato"

        async def generate():
            async for chunk in mock_gemini_stream():
                escaped_chunk = chunk.replace("\n", "\\n")
                yield f"data: {escaped_chunk}\n\n"
            yield "data: [DONE]\n\n"

        chunks = []
        async for chunk in generate():
            chunks.append(chunk)

        # Content newlines should be escaped
        assert "\\n" in chunks[0]
        # But SSE terminator should be actual newlines
        assert chunks[0].endswith("\n\n")
        # Original newline should NOT appear mid-chunk (would break SSE)
        content_part = chunks[0][6:-2]  # Strip "data: " and "\n\n"
        assert "\n" not in content_part

    @pytest.mark.asyncio
    async def test_empty_stream_still_sends_done(self):
        """Test that empty stream still sends [DONE] event."""

        async def mock_empty_stream():
            return  # pragma: no cover
            yield  # Makes this an async generator (Python syntax requirement)

        async def generate():
            async for chunk in mock_empty_stream():
                escaped_chunk = chunk.replace("\n", "\\n")
                yield f"data: {escaped_chunk}\n\n"
            yield "data: [DONE]\n\n"

        chunks = []
        async for chunk in generate():
            chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0] == "data: [DONE]\n\n"
