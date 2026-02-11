"""Security tests for Gemini _fetch_media method.

This module provides comprehensive security tests for the _fetch_media method
in the Gemini client, covering:
- SSRF protection (internal IPs, localhost variants)
- Content-type validation
- File size limits
- HTTP error handling
- Timeout handling
- Invalid URL formats
- Redirect-based SSRF attacks
- Empty response handling
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from fcp.security.url_validator import ImageURLError
from fcp.services.gemini import MAX_IMAGE_SIZE, GeminiClient


class TestFetchMediaSSRFProtection:
    """Tests for SSRF protection in _fetch_media."""

    @pytest.fixture
    def gemini_client(self):
        """Create a GeminiClient instance for testing."""
        with patch("fcp.services.gemini.GEMINI_API_KEY", "test-key"):
            with patch("fcp.services.gemini.genai"):
                return GeminiClient()

    @pytest.mark.asyncio
    async def test_blocks_loopback_127_0_0_1(self, gemini_client):
        """Test that 127.0.0.1 loopback address is blocked."""
        with pytest.raises(ValueError, match="Invalid media URL"):
            await gemini_client._fetch_media("http://127.0.0.1/image.jpg")

    @pytest.mark.asyncio
    async def test_blocks_loopback_range(self, gemini_client):
        """Test that entire 127.x.x.x loopback range is blocked."""
        with pytest.raises(ValueError, match="Invalid media URL"):
            await gemini_client._fetch_media("http://127.0.0.100/image.jpg")

    @pytest.mark.asyncio
    async def test_blocks_private_class_a_10_network(self, gemini_client):
        """Test that 10.x.x.x private network is blocked."""
        test_ips = ["10.0.0.1", "10.255.255.255", "10.10.10.10"]
        for ip in test_ips:
            with pytest.raises(ValueError, match="Invalid media URL"):
                await gemini_client._fetch_media(f"http://{ip}/image.jpg")

    @pytest.mark.asyncio
    async def test_blocks_private_class_b_172_network(self, gemini_client):
        """Test that 172.16.x.x - 172.31.x.x private network is blocked."""
        test_ips = ["172.16.0.1", "172.20.5.5", "172.31.255.255"]
        for ip in test_ips:
            with pytest.raises(ValueError, match="Invalid media URL"):
                await gemini_client._fetch_media(f"http://{ip}/image.jpg")

    @pytest.mark.asyncio
    async def test_blocks_private_class_c_192_168_network(self, gemini_client):
        """Test that 192.168.x.x private network is blocked."""
        test_ips = ["192.168.0.1", "192.168.1.1", "192.168.255.255"]
        for ip in test_ips:
            with pytest.raises(ValueError, match="Invalid media URL"):
                await gemini_client._fetch_media(f"http://{ip}/image.jpg")

    @pytest.mark.asyncio
    async def test_blocks_link_local_169_254(self, gemini_client):
        """Test that link-local / cloud metadata addresses are blocked."""
        test_ips = ["169.254.0.1", "169.254.169.254"]
        for ip in test_ips:
            with pytest.raises(ValueError, match="Invalid media URL"):
                await gemini_client._fetch_media(f"http://{ip}/image.jpg")

    @pytest.mark.asyncio
    async def test_blocks_metadata_google_internal(self, gemini_client):
        """Test that metadata.google.internal is blocked."""
        with pytest.raises(ValueError, match="Invalid media URL"):
            await gemini_client._fetch_media("http://metadata.google.internal/computeMetadata/v1/project/project-id")

    @pytest.mark.asyncio
    async def test_blocks_localhost_hostname(self, gemini_client):
        """Test that localhost hostname is blocked when not in allowed list."""
        # localhost is in ALLOWED_DOMAINS but is blocked for image URLs
        # when accessed via private IP resolution
        with patch(
            "fcp.security.url_validator.ALLOWED_DOMAINS",
            {"firebasestorage.googleapis.com"},
        ):
            with pytest.raises(ValueError, match="Invalid media URL"):
                await gemini_client._fetch_media("http://localhost/image.jpg")


class TestFetchMediaContentTypeValidation:
    """Tests for content-type validation in _fetch_media."""

    @pytest.fixture
    def gemini_client(self):
        """Create a GeminiClient instance for testing."""
        with patch("fcp.services.gemini.GEMINI_API_KEY", "test-key"):
            with patch("fcp.services.gemini.genai"):
                return GeminiClient()

    @pytest.mark.asyncio
    async def test_rejects_text_html_content_type(self, gemini_client):
        """Test that text/html content type is rejected for images."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"<html>fake</html>"

        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/image.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(ValueError, match="Invalid content type.*text/html"):
                    await gemini_client._fetch_media(
                        "https://firebasestorage.googleapis.com/image.jpg",
                        expected_type="image",
                    )

    @pytest.mark.asyncio
    async def test_rejects_application_json_content_type(self, gemini_client):
        """Test that application/json content type is rejected for images."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b'{"error": "fake"}'

        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/image.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(ValueError, match="Invalid content type.*application/json"):
                    await gemini_client._fetch_media(
                        "https://firebasestorage.googleapis.com/image.jpg",
                        expected_type="image",
                    )

    @pytest.mark.asyncio
    async def test_rejects_application_octet_stream_content_type(self, gemini_client):
        """Test that application/octet-stream is rejected for images."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "application/octet-stream"}
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"binary data"

        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/image.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(ValueError, match="Invalid content type.*application/octet-stream"):
                    await gemini_client._fetch_media(
                        "https://firebasestorage.googleapis.com/image.jpg",
                        expected_type="image",
                    )

    @pytest.mark.asyncio
    async def test_accepts_image_jpeg_content_type(self, gemini_client):
        """Test that image/jpeg content type is accepted."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"fake jpeg data"

        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/image.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                data, mime_type = await gemini_client._fetch_media(
                    "https://firebasestorage.googleapis.com/image.jpg",
                    expected_type="image",
                )

                assert data == b"fake jpeg data"
                assert mime_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_accepts_image_png_content_type(self, gemini_client):
        """Test that image/png content type is accepted."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "image/png; charset=utf-8"}
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"fake png data"

        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/image.png",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                data, mime_type = await gemini_client._fetch_media(
                    "https://firebasestorage.googleapis.com/image.png",
                    expected_type="image",
                )

                assert data == b"fake png data"
                # Mime type is stripped of charset
                assert mime_type == "image/png"

    @pytest.mark.asyncio
    async def test_skips_content_type_validation_for_media(self, gemini_client):
        """Test that content-type validation is skipped for media (non-image) type."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "video/mp4"}
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"fake video data"

        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/video.mp4",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                # expected_type="media" skips content-type validation
                data, mime_type = await gemini_client._fetch_media(
                    "https://firebasestorage.googleapis.com/video.mp4",
                    expected_type="media",
                )

                assert data == b"fake video data"
                assert mime_type == "video/mp4"


class TestFetchMediaSizeValidation:
    """Tests for file size validation in _fetch_media."""

    @pytest.fixture
    def gemini_client(self):
        """Create a GeminiClient instance for testing."""
        with patch("fcp.services.gemini.GEMINI_API_KEY", "test-key"):
            with patch("fcp.services.gemini.genai"):
                return GeminiClient()

    @pytest.mark.asyncio
    async def test_rejects_oversized_file_via_content_length(self, gemini_client):
        """Test that files exceeding MAX_IMAGE_SIZE are rejected."""
        mock_response = MagicMock()
        mock_response.headers = {
            "content-type": "image/jpeg",
            "content-length": str(MAX_IMAGE_SIZE + 1),  # 10MB + 1 byte
        }
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"x" * 100  # Actual content doesn't matter

        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/large.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(ValueError, match="Media too large"):
                    await gemini_client._fetch_media("https://firebasestorage.googleapis.com/large.jpg")

    @pytest.mark.asyncio
    async def test_accepts_file_at_max_size(self, gemini_client):
        """Test that files exactly at MAX_IMAGE_SIZE are accepted."""
        mock_response = MagicMock()
        mock_response.headers = {
            "content-type": "image/jpeg",
            "content-length": str(MAX_IMAGE_SIZE),  # Exactly 10MB
        }
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"valid image"

        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/image.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                data, mime_type = await gemini_client._fetch_media("https://firebasestorage.googleapis.com/image.jpg")

                assert data == b"valid image"
                assert mime_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_accepts_file_without_content_length_header(self, gemini_client):
        """Test that files without Content-Length header are accepted."""
        mock_response = MagicMock()
        mock_response.headers = {
            "content-type": "image/jpeg",
            # No content-length header
        }
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"valid image"

        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/image.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                data, mime_type = await gemini_client._fetch_media("https://firebasestorage.googleapis.com/image.jpg")

                assert data == b"valid image"
                assert mime_type == "image/jpeg"


class TestFetchMediaHTTPErrors:
    """Tests for HTTP error handling in _fetch_media."""

    @pytest.fixture
    def gemini_client(self):
        """Create a GeminiClient instance for testing."""
        with patch("fcp.services.gemini.GEMINI_API_KEY", "test-key"):
            with patch("fcp.services.gemini.genai"):
                return GeminiClient()

    @pytest.mark.asyncio
    async def test_handles_http_404_not_found(self, gemini_client):
        """Test that HTTP 404 errors are properly raised."""
        mock_request = MagicMock()
        mock_request.url = "https://firebasestorage.googleapis.com/missing.jpg"

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("Not Found", request=mock_request, response=mock_response)
        )

        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/missing.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(httpx.HTTPStatusError) as exc_info:
                    await gemini_client._fetch_media("https://firebasestorage.googleapis.com/missing.jpg")

                assert exc_info.value.response.status_code == 404

    @pytest.mark.asyncio
    async def test_handles_http_500_server_error(self, gemini_client):
        """Test that HTTP 500 errors are properly raised."""
        mock_request = MagicMock()
        mock_request.url = "https://firebasestorage.googleapis.com/image.jpg"

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("Internal Server Error", request=mock_request, response=mock_response)
        )

        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/image.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(httpx.HTTPStatusError) as exc_info:
                    await gemini_client._fetch_media("https://firebasestorage.googleapis.com/image.jpg")

                assert exc_info.value.response.status_code == 500

    @pytest.mark.asyncio
    async def test_handles_http_403_forbidden(self, gemini_client):
        """Test that HTTP 403 errors are properly raised."""
        mock_request = MagicMock()
        mock_request.url = "https://firebasestorage.googleapis.com/private.jpg"

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("Forbidden", request=mock_request, response=mock_response)
        )

        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/private.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(httpx.HTTPStatusError) as exc_info:
                    await gemini_client._fetch_media("https://firebasestorage.googleapis.com/private.jpg")

                assert exc_info.value.response.status_code == 403


class TestFetchMediaTimeoutHandling:
    """Tests for timeout handling in _fetch_media."""

    @pytest.fixture
    def gemini_client(self):
        """Create a GeminiClient instance for testing."""
        with patch("fcp.services.gemini.GEMINI_API_KEY", "test-key"):
            with patch("fcp.services.gemini.genai"):
                return GeminiClient()

    @pytest.mark.asyncio
    async def test_handles_connect_timeout(self, gemini_client):
        """Test that connection timeouts are properly raised."""
        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/image.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(side_effect=httpx.ConnectTimeout("Connection timed out"))
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(httpx.ConnectTimeout):
                    await gemini_client._fetch_media("https://firebasestorage.googleapis.com/image.jpg")

    @pytest.mark.asyncio
    async def test_handles_read_timeout(self, gemini_client):
        """Test that read timeouts are properly raised."""
        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/image.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(side_effect=httpx.ReadTimeout("Read timed out"))
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(httpx.ReadTimeout):
                    await gemini_client._fetch_media("https://firebasestorage.googleapis.com/image.jpg")

    @pytest.mark.asyncio
    async def test_handles_pool_timeout(self, gemini_client):
        """Test that pool timeouts are properly raised."""
        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/image.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(side_effect=httpx.PoolTimeout("Pool timed out"))
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(httpx.PoolTimeout):
                    await gemini_client._fetch_media("https://firebasestorage.googleapis.com/image.jpg")


class TestFetchMediaInvalidURLFormats:
    """Tests for invalid URL format handling in _fetch_media."""

    @pytest.fixture
    def gemini_client(self):
        """Create a GeminiClient instance for testing."""
        with patch("fcp.services.gemini.GEMINI_API_KEY", "test-key"):
            with patch("fcp.services.gemini.genai"):
                return GeminiClient()

    @pytest.mark.asyncio
    async def test_rejects_empty_url(self, gemini_client):
        """Test that empty URL is rejected."""
        with pytest.raises(ValueError, match="Invalid media URL"):
            await gemini_client._fetch_media("")

    @pytest.mark.asyncio
    async def test_rejects_none_url(self, gemini_client):
        """Test that None URL is rejected."""
        with pytest.raises(ValueError, match="Invalid media URL"):
            await gemini_client._fetch_media(None)

    @pytest.mark.asyncio
    async def test_rejects_file_protocol(self, gemini_client):
        """Test that file:// protocol is rejected."""
        with pytest.raises(ValueError, match="Invalid media URL"):
            await gemini_client._fetch_media("file:///etc/passwd")

    @pytest.mark.asyncio
    async def test_rejects_data_protocol(self, gemini_client):
        """Test that data: protocol is rejected."""
        with pytest.raises(ValueError, match="Invalid media URL"):
            await gemini_client._fetch_media("data:image/png;base64,abc123")

    @pytest.mark.asyncio
    async def test_rejects_ftp_protocol(self, gemini_client):
        """Test that ftp:// protocol is rejected."""
        with pytest.raises(ValueError, match="Invalid media URL"):
            await gemini_client._fetch_media("ftp://example.com/image.jpg")

    @pytest.mark.asyncio
    async def test_rejects_javascript_protocol(self, gemini_client):
        """Test that javascript: protocol is rejected."""
        with pytest.raises(ValueError, match="Invalid media URL"):
            await gemini_client._fetch_media("javascript:alert(1)")

    @pytest.mark.asyncio
    async def test_rejects_url_without_scheme(self, gemini_client):
        """Test that URL without scheme is rejected."""
        with pytest.raises(ValueError, match="Invalid media URL"):
            await gemini_client._fetch_media("//example.com/image.jpg")

    @pytest.mark.asyncio
    async def test_rejects_url_with_credentials(self, gemini_client):
        """Test that URL with credentials is rejected."""
        with pytest.raises(ValueError, match="Invalid media URL"):
            await gemini_client._fetch_media("https://user:password@firebasestorage.googleapis.com/image.jpg")


class TestFetchMediaRedirectSSRF:
    """Tests for SSRF protection via redirect attacks."""

    @pytest.fixture
    def gemini_client(self):
        """Create a GeminiClient instance for testing."""
        with patch("fcp.services.gemini.GEMINI_API_KEY", "test-key"):
            with patch("fcp.services.gemini.genai"):
                return GeminiClient()

    @pytest.mark.asyncio
    async def test_initial_url_validation_blocks_internal_ip(self, gemini_client):
        """Test that initial URL validation blocks internal IPs before redirect."""
        # The URL validator should reject internal IPs before any HTTP request
        with pytest.raises(ValueError, match="Invalid media URL"):
            await gemini_client._fetch_media("http://192.168.1.1/image.jpg")

    @pytest.mark.asyncio
    async def test_redirect_to_internal_ip_detection(self, gemini_client):
        """Test detection of redirect to internal IP.

        Note: httpx with follow_redirects=True will follow redirects automatically.
        The primary defense is the URL validation on the initial request.
        This test verifies the initial URL is validated properly.
        """
        # Testing that even if a malicious external URL could redirect to internal,
        # the initial URL itself must pass validation first
        with patch(
            "fcp.security.url_validator.validate_image_url",
            side_effect=ImageURLError("Access to private/internal IP addresses is not allowed"),
        ):
            with pytest.raises(ValueError, match="Invalid media URL"):
                await gemini_client._fetch_media("http://evil.com/redirect-to-internal")

    @pytest.mark.asyncio
    async def test_domain_not_in_allowlist(self, gemini_client):
        """Test that domains not in allowlist are rejected."""
        with pytest.raises(ValueError, match="Invalid media URL"):
            await gemini_client._fetch_media("https://evil-domain.com/malware.jpg")


class TestFetchMediaEmptyResponse:
    """Tests for empty response handling in _fetch_media."""

    @pytest.fixture
    def gemini_client(self):
        """Create a GeminiClient instance for testing."""
        with patch("fcp.services.gemini.GEMINI_API_KEY", "test-key"):
            with patch("fcp.services.gemini.genai"):
                return GeminiClient()

    @pytest.mark.asyncio
    async def test_returns_empty_content(self, gemini_client):
        """Test that empty response body is returned as-is.

        The _fetch_media method doesn't validate response body size,
        it only checks Content-Length header. Empty responses are valid.
        """
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "image/jpeg"}
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b""  # Empty body

        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/empty.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                data, mime_type = await gemini_client._fetch_media("https://firebasestorage.googleapis.com/empty.jpg")

                # Empty content is returned - validation happens at Gemini API level
                assert data == b""
                assert mime_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_handles_empty_content_type_header(self, gemini_client):
        """Test handling of empty content-type header for images."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": ""}
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"some data"

        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/image.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                # Empty content-type is rejected because validate_content_type returns False
                with pytest.raises(ValueError, match="Invalid content type"):
                    await gemini_client._fetch_media(
                        "https://firebasestorage.googleapis.com/image.jpg",
                        expected_type="image",
                    )

    @pytest.mark.asyncio
    async def test_handles_missing_content_type_header(self, gemini_client):
        """Test handling of missing content-type header for images."""
        mock_response = MagicMock()
        mock_response.headers = {}  # No content-type header
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"some data"

        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/image.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                # Missing content-type defaults to empty string, which is invalid
                with pytest.raises(ValueError, match="Invalid content type"):
                    await gemini_client._fetch_media(
                        "https://firebasestorage.googleapis.com/image.jpg",
                        expected_type="image",
                    )


class TestFetchMediaConnectionErrors:
    """Tests for network connection error handling in _fetch_media."""

    @pytest.fixture
    def gemini_client(self):
        """Create a GeminiClient instance for testing."""
        with patch("fcp.services.gemini.GEMINI_API_KEY", "test-key"):
            with patch("fcp.services.gemini.genai"):
                return GeminiClient()

    @pytest.mark.asyncio
    async def test_handles_connection_refused(self, gemini_client):
        """Test that connection refused errors are properly raised."""
        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/image.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(httpx.ConnectError):
                    await gemini_client._fetch_media("https://firebasestorage.googleapis.com/image.jpg")

    @pytest.mark.asyncio
    async def test_handles_dns_resolution_failure(self, gemini_client):
        """Test that DNS resolution failures are properly raised."""
        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/image.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(side_effect=httpx.ConnectError("DNS resolution failed"))
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                with pytest.raises(httpx.ConnectError):
                    await gemini_client._fetch_media("https://firebasestorage.googleapis.com/image.jpg")


class TestFetchMediaImageURLErrorConversion:
    """Tests for ImageURLError to ValueError conversion in _fetch_media."""

    @pytest.fixture
    def gemini_client(self):
        """Create a GeminiClient instance for testing."""
        with patch("fcp.services.gemini.GEMINI_API_KEY", "test-key"):
            with patch("fcp.services.gemini.genai"):
                return GeminiClient()

    @pytest.mark.asyncio
    async def test_converts_image_url_error_to_value_error(self, gemini_client):
        """Test that ImageURLError is converted to ValueError with message."""
        with patch(
            "fcp.services.gemini.validate_image_url",
            side_effect=ImageURLError("Custom error message"),
        ):
            with pytest.raises(ValueError) as exc_info:
                await gemini_client._fetch_media("https://example.com/image.jpg")

            assert "Invalid media URL" in str(exc_info.value)
            assert "Custom error message" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_preserves_ssrf_error_message(self, gemini_client):
        """Test that SSRF-specific error messages are preserved."""
        with patch(
            "fcp.security.url_validator.validate_image_url",
            side_effect=ImageURLError("Access to private/internal IP addresses is not allowed"),
        ):
            with pytest.raises(ValueError) as exc_info:
                await gemini_client._fetch_media("http://10.0.0.1/image.jpg")

            assert "private/internal IP" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_preserves_domain_error_message(self, gemini_client):
        """Test that domain-not-allowed error messages are preserved."""
        with patch(
            "fcp.security.url_validator.validate_image_url",
            side_effect=ImageURLError("Domain evil.com is not in the allowed list"),
        ):
            with pytest.raises(ValueError) as exc_info:
                await gemini_client._fetch_media("https://evil.com/image.jpg")

            assert "evil.com" in str(exc_info.value)
            assert "allowed list" in str(exc_info.value)


class TestFetchMediaMimeTypeParsing:
    """Tests for MIME type parsing in _fetch_media."""

    @pytest.fixture
    def gemini_client(self):
        """Create a GeminiClient instance for testing."""
        with patch("fcp.services.gemini.GEMINI_API_KEY", "test-key"):
            with patch("fcp.services.gemini.genai"):
                return GeminiClient()

    @pytest.mark.asyncio
    async def test_strips_charset_from_content_type(self, gemini_client):
        """Test that charset parameter is stripped from content-type."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "image/jpeg; charset=utf-8"}
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"image data"

        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/image.jpg",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                data, mime_type = await gemini_client._fetch_media("https://firebasestorage.googleapis.com/image.jpg")

                assert mime_type == "image/jpeg"

    @pytest.mark.asyncio
    async def test_strips_boundary_from_content_type(self, gemini_client):
        """Test that boundary parameter is stripped from content-type."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "image/png; boundary=something"}
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"image data"

        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/image.png",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                data, mime_type = await gemini_client._fetch_media("https://firebasestorage.googleapis.com/image.png")

                assert mime_type == "image/png"

    @pytest.mark.asyncio
    async def test_strips_whitespace_from_mime_type(self, gemini_client):
        """Test that whitespace is stripped from mime type."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "  image/webp  ; charset=utf-8"}
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"image data"

        with patch(
            "fcp.security.url_validator.validate_image_url",
            return_value="https://firebasestorage.googleapis.com/image.webp",
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                data, mime_type = await gemini_client._fetch_media("https://firebasestorage.googleapis.com/image.webp")

                assert mime_type == "image/webp"


class TestGeminiHTTPClientManagement:
    """Tests for HTTP client lifecycle management."""

    @pytest.fixture
    def gemini_client(self):
        """Create a GeminiClient instance for testing."""
        with patch("fcp.services.gemini.GEMINI_API_KEY", "test-key"):
            with patch("fcp.services.gemini.genai"):
                client = GeminiClient()
                # Ensure we start with no client
                GeminiClient._http_client = None
                return client

    def test_get_http_client_creates_client_when_none(self, gemini_client):
        """_get_http_client creates a new client when none exists."""
        GeminiClient._http_client = None
        client = gemini_client._get_http_client()
        assert client is not None
        assert isinstance(client, httpx.AsyncClient)
        # Clean up
        GeminiClient._http_client = None

    def test_get_http_client_returns_existing_client(self, gemini_client):
        """_get_http_client returns existing client when one exists."""
        mock_client = MagicMock(spec=httpx.AsyncClient)
        GeminiClient._http_client = mock_client

        result = gemini_client._get_http_client()

        assert result is mock_client
        # Clean up
        GeminiClient._http_client = None

    @pytest.mark.asyncio
    async def test_close_http_client_when_client_exists(self, gemini_client):
        """close_http_client closes existing client."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        GeminiClient._http_client = mock_client

        await GeminiClient.close_http_client()

        mock_client.aclose.assert_called_once()
        assert GeminiClient._http_client is None

    @pytest.mark.asyncio
    async def test_close_http_client_when_no_client(self, gemini_client):
        """close_http_client does nothing when no client exists."""
        GeminiClient._http_client = None

        # Should not raise
        await GeminiClient.close_http_client()

        assert GeminiClient._http_client is None

    def test_reset_http_client(self, gemini_client):
        """reset_http_client sets client to None."""
        mock_client = MagicMock(spec=httpx.AsyncClient)
        GeminiClient._http_client = mock_client

        GeminiClient.reset_http_client()

        assert GeminiClient._http_client is None
