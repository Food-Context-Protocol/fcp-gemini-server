"""Tests for Gemini context cache TTL handling."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from google.genai import errors as genai_errors


class TestGenerateWithCacheTTLHandling:
    """Tests for generate_with_cache cache expiration handling."""

    @pytest.fixture
    def mock_response(self):
        """Create a mock Gemini response."""
        response = MagicMock()
        response.text = "Generated content"
        response.usage_metadata = MagicMock(
            prompt_token_count=100,
            candidates_token_count=50,
            total_token_count=150,
        )
        return response

    @pytest.fixture
    def mock_client(self, mock_response):
        """Create a mock Gemini client."""
        client = MagicMock()
        client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        return client

    @pytest.mark.asyncio
    async def test_generate_with_cache_success(self, mock_client, mock_response):
        """Test successful cached generation."""
        from fcp.services.gemini import GeminiClient

        gemini = GeminiClient()
        gemini.client = mock_client

        result = await gemini.generate_with_cache(
            prompt="What is this?",
            cache_name="caches/test-cache-123",
        )

        assert result == "Generated content"
        mock_client.aio.models.generate_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_cache_expired_fallback(self, mock_client, mock_response):
        """Test fallback when cache is expired (410 Gone)."""
        from fcp.services.gemini import GeminiClient

        gemini = GeminiClient()
        gemini.client = mock_client

        # First call raises 410 (cache expired), second call succeeds
        expired_error = genai_errors.ClientError(
            code=410,
            response_json={"error": {"message": "Cache has expired", "status": "GONE"}},
        )
        mock_client.aio.models.generate_content = AsyncMock(side_effect=[expired_error, mock_response])

        result = await gemini.generate_with_cache(
            prompt="What is this?",
            cache_name="caches/expired-cache-123",
        )

        assert result == "Generated content"
        # Should have been called twice: first with cache, then fallback
        assert mock_client.aio.models.generate_content.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_with_cache_not_found_fallback(self, mock_client, mock_response):
        """Test fallback when cache is not found (404)."""
        from fcp.services.gemini import GeminiClient

        gemini = GeminiClient()
        gemini.client = mock_client

        not_found_error = genai_errors.ClientError(
            code=404,
            response_json={"error": {"message": "Cache not found", "status": "NOT_FOUND"}},
        )
        mock_client.aio.models.generate_content = AsyncMock(side_effect=[not_found_error, mock_response])

        result = await gemini.generate_with_cache(
            prompt="What is this?",
            cache_name="caches/nonexistent-cache-123",
        )

        assert result == "Generated content"
        assert mock_client.aio.models.generate_content.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_with_cache_invalid_fallback(self, mock_client, mock_response):
        """Test fallback when cache is invalid (400)."""
        from fcp.services.gemini import GeminiClient

        gemini = GeminiClient()
        gemini.client = mock_client

        invalid_error = genai_errors.ClientError(
            code=400,
            response_json={"error": {"message": "Invalid cache name", "status": "INVALID_ARGUMENT"}},
        )
        mock_client.aio.models.generate_content = AsyncMock(side_effect=[invalid_error, mock_response])

        result = await gemini.generate_with_cache(
            prompt="What is this?",
            cache_name="invalid-cache-name",
        )

        assert result == "Generated content"
        assert mock_client.aio.models.generate_content.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_with_cache_fallback_disabled(self, mock_client):
        """Test that fallback can be disabled."""
        from fcp.services.gemini import GeminiClient

        gemini = GeminiClient()
        gemini.client = mock_client

        not_found_error = genai_errors.ClientError(
            code=404,
            response_json={"error": {"message": "Cache not found", "status": "NOT_FOUND"}},
        )
        mock_client.aio.models.generate_content = AsyncMock(side_effect=not_found_error)

        with pytest.raises(genai_errors.ClientError) as exc_info:
            await gemini.generate_with_cache(
                prompt="What is this?",
                cache_name="caches/nonexistent-cache-123",
                fallback_to_uncached=False,
            )

        assert exc_info.value.code == 404
        # Should only have been called once (no fallback)
        mock_client.aio.models.generate_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_cache_non_cache_error_propagates(self, mock_client):
        """Test that non-cache errors are propagated."""
        from fcp.services.gemini import GeminiClient

        gemini = GeminiClient()
        gemini.client = mock_client

        # 401 Unauthorized is not a cache error
        auth_error = genai_errors.ClientError(
            code=401,
            response_json={"error": {"message": "Unauthorized", "status": "UNAUTHENTICATED"}},
        )
        mock_client.aio.models.generate_content = AsyncMock(side_effect=auth_error)

        with pytest.raises(genai_errors.ClientError) as exc_info:
            await gemini.generate_with_cache(
                prompt="What is this?",
                cache_name="caches/test-cache-123",
            )

        assert exc_info.value.code == 401
        # Should only have been called once (no fallback for auth errors)
        mock_client.aio.models.generate_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_cache_server_error_propagates(self, mock_client):
        """Test that server errors are propagated (not fallback)."""
        from fcp.services.gemini import GeminiClient

        gemini = GeminiClient()
        gemini.client = mock_client

        server_error = genai_errors.ServerError(
            code=500,
            response_json={"error": {"message": "Internal error", "status": "INTERNAL"}},
        )
        mock_client.aio.models.generate_content = AsyncMock(side_effect=server_error)

        with pytest.raises(genai_errors.ServerError) as exc_info:
            await gemini.generate_with_cache(
                prompt="What is this?",
                cache_name="caches/test-cache-123",
            )

        assert exc_info.value.code == 500
        mock_client.aio.models.generate_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_cache_not_configured(self):
        """Test RuntimeError when client is not configured."""
        from fcp.services.gemini import GeminiClient

        gemini = GeminiClient()
        gemini.client = None

        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await gemini.generate_with_cache(
                prompt="What is this?",
                cache_name="caches/test-cache-123",
            )

    @pytest.mark.asyncio
    async def test_generate_with_cache_empty_response(self, mock_client):
        """Test handling of empty response text."""
        from fcp.services.gemini import GeminiClient

        gemini = GeminiClient()
        gemini.client = mock_client

        empty_response = MagicMock()
        empty_response.text = None
        empty_response.usage_metadata = MagicMock(
            prompt_token_count=100,
            candidates_token_count=0,
            total_token_count=100,
        )
        mock_client.aio.models.generate_content = AsyncMock(return_value=empty_response)

        result = await gemini.generate_with_cache(
            prompt="What is this?",
            cache_name="caches/test-cache-123",
        )

        assert result == ""

    @pytest.mark.asyncio
    async def test_generate_with_cache_logs_warning_on_fallback(self, mock_client, mock_response, caplog):
        """Test that a warning is logged when falling back."""
        import logging

        from fcp.services.gemini import GeminiClient

        gemini = GeminiClient()
        gemini.client = mock_client

        expired_error = genai_errors.ClientError(
            code=410,
            response_json={"error": {"message": "Cache expired", "status": "GONE"}},
        )
        mock_client.aio.models.generate_content = AsyncMock(side_effect=[expired_error, mock_response])

        with caplog.at_level(logging.WARNING):
            await gemini.generate_with_cache(
                prompt="What is this?",
                cache_name="caches/expired-cache",
            )

        assert "Cache error" in caplog.text
        assert "Falling back to uncached generation" in caplog.text


class TestCreateContextCache:
    """Tests for create_context_cache method."""

    @pytest.fixture
    def mock_cache_response(self):
        """Create a mock cache response."""
        cache = MagicMock()
        cache.name = "caches/test-cache-123"
        return cache

    @pytest.fixture
    def mock_client(self, mock_cache_response):
        """Create a mock Gemini client for cache creation."""
        client = MagicMock()
        client.aio.caches.create = AsyncMock(return_value=mock_cache_response)
        return client

    @pytest.mark.asyncio
    async def test_create_context_cache_success(self, mock_client, mock_cache_response):
        """Test successful cache creation."""
        from fcp.services.gemini import GeminiClient

        gemini = GeminiClient()
        gemini.client = mock_client

        result = await gemini.create_context_cache(
            name="my-test-cache",
            content="Large context content here...",
            ttl_minutes=60,
        )

        assert result == "caches/test-cache-123"
        mock_client.aio.caches.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_context_cache_custom_ttl(self, mock_client, mock_cache_response):
        """Test cache creation with custom TTL."""
        from fcp.services.gemini import GeminiClient

        gemini = GeminiClient()
        gemini.client = mock_client

        await gemini.create_context_cache(
            name="my-test-cache",
            content="Large context content here...",
            ttl_minutes=120,  # 2 hours
        )

        call_args = mock_client.aio.caches.create.call_args
        config = call_args.kwargs.get("config") or call_args[1].get("config")
        assert config.ttl == "7200s"  # 120 * 60 = 7200 seconds

    @pytest.mark.asyncio
    async def test_create_context_cache_not_configured(self):
        """Test RuntimeError when client is not configured."""
        from fcp.services.gemini import GeminiClient

        gemini = GeminiClient()
        gemini.client = None

        with pytest.raises(RuntimeError, match="GEMINI_API_KEY not configured"):
            await gemini.create_context_cache(
                name="my-test-cache",
                content="Large context content here...",
            )

    @pytest.mark.asyncio
    async def test_create_context_cache_empty_name(self, mock_client):
        """Test cache creation when response has no name."""
        from fcp.services.gemini import GeminiClient

        gemini = GeminiClient()
        gemini.client = mock_client

        empty_cache = MagicMock()
        empty_cache.name = None
        mock_client.aio.caches.create = AsyncMock(return_value=empty_cache)

        result = await gemini.create_context_cache(
            name="my-test-cache",
            content="Large context content here...",
        )

        assert result == ""
