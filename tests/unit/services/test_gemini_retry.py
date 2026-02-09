"""Tests for Gemini retry logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from fcp.services.gemini import (
    RETRYABLE_EXCEPTIONS,
    GeminiClient,
    _create_retry_decorator,
    gemini_retry,
)


class TestRetryDecorator:
    """Tests for the retry decorator factory."""

    def test_create_retry_decorator_returns_decorator(self):
        """Should return a retry decorator."""
        decorator = _create_retry_decorator()
        assert callable(decorator)

    def test_retryable_exceptions_defined(self):
        """Should define retryable exceptions."""
        assert httpx.ConnectError in RETRYABLE_EXCEPTIONS
        assert httpx.TimeoutException in RETRYABLE_EXCEPTIONS
        assert httpx.HTTPStatusError in RETRYABLE_EXCEPTIONS

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self):
        """Should retry on connection errors."""
        call_count = 0

        @gemini_retry
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("Connection failed")
            return "success"

        result = await failing_function()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_on_timeout_error(self):
        """Should retry on timeout errors."""
        call_count = 0

        @gemini_retry
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("Request timed out")
            return "success"

        result = await failing_function()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Should raise after max retries exceeded."""

        @gemini_retry
        async def always_failing():
            raise httpx.ConnectError("Connection failed")

        with pytest.raises(httpx.ConnectError):
            await always_failing()

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_exception(self):
        """Should not retry on non-retryable exceptions."""
        call_count = 0

        @gemini_retry
        async def failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            await failing_function()

        assert call_count == 1  # No retry


class TestGeminiClientRetry:
    """Tests for retry behavior in GeminiClient methods."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Gemini client."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            client = GeminiClient()
            # Create mock for the internal client
            mock_genai = MagicMock()
            mock_genai.aio.models.generate_content = AsyncMock()
            client.client = mock_genai
            return client

    @pytest.mark.asyncio
    async def test_generate_content_has_retry_decorator(self, mock_client):
        """generate_content should have retry decorator."""
        # Verify the method has the retry decorator by checking __wrapped__
        assert hasattr(GeminiClient.generate_content, "__wrapped__")

    @pytest.mark.asyncio
    async def test_generate_json_has_retry_decorator(self, mock_client):
        """generate_json should have retry decorator."""
        assert hasattr(GeminiClient.generate_json, "__wrapped__")

    @pytest.mark.asyncio
    async def test_generate_with_tools_has_retry_decorator(self, mock_client):
        """generate_with_tools should have retry decorator."""
        assert hasattr(GeminiClient.generate_with_tools, "__wrapped__")

    @pytest.mark.asyncio
    async def test_generate_with_grounding_has_retry_decorator(self, mock_client):
        """generate_with_grounding should have retry decorator."""
        assert hasattr(GeminiClient.generate_with_grounding, "__wrapped__")

    @pytest.mark.asyncio
    async def test_generate_with_thinking_has_retry_decorator(self, mock_client):
        """generate_with_thinking should have retry decorator."""
        assert hasattr(GeminiClient.generate_with_thinking, "__wrapped__")

    @pytest.mark.asyncio
    async def test_generate_with_code_execution_has_retry_decorator(self, mock_client):
        """generate_with_code_execution should have retry decorator."""
        assert hasattr(GeminiClient.generate_with_code_execution, "__wrapped__")

    @pytest.mark.asyncio
    async def test_generate_with_large_context_has_retry_decorator(self, mock_client):
        """generate_with_large_context should have retry decorator."""
        assert hasattr(GeminiClient.generate_with_large_context, "__wrapped__")

    @pytest.mark.asyncio
    async def test_generate_with_all_tools_has_retry_decorator(self, mock_client):
        """generate_with_all_tools should have retry decorator."""
        assert hasattr(GeminiClient.generate_with_all_tools, "__wrapped__")
