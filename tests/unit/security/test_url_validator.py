"""Tests for security/url_validator.py."""
# sourcery skip: no-loop-in-tests

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fcp.security.url_validator import (
    ALLOWED_CONTENT_TYPES,
    ALLOWED_DOMAINS,
    BLOCKED_HOSTNAMES,
    ImageURLError,
    _is_ip_blocked,
    _is_production,
    validate_browser_url,
    validate_content_type,
    validate_image_url,
)


class TestIsProduction:
    """Tests for _is_production function."""

    def test_returns_true_for_production_env(self):
        """Test that production environment is detected."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            assert _is_production() is True

    def test_returns_true_for_prod_env(self):
        """Test that 'prod' environment is detected."""
        with patch.dict(os.environ, {"ENVIRONMENT": "prod"}):
            assert _is_production() is True

    def test_returns_true_for_cloud_run(self):
        """Test that Cloud Run is detected via K_SERVICE."""
        with patch.dict(os.environ, {"K_SERVICE": "my-service"}, clear=True):
            assert _is_production() is True

    def test_returns_false_for_development(self):
        """Test that development environment returns False."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            assert _is_production() is False

    def test_returns_false_for_empty_env(self):
        """Test that empty environment returns False."""
        with patch.dict(os.environ, {}, clear=True):
            assert _is_production() is False


class TestIsIpBlocked:
    """Tests for _is_ip_blocked function."""

    def test_blocks_private_class_a(self):
        """Test that 10.x.x.x addresses are blocked."""
        assert _is_ip_blocked("10.0.0.1") is True
        assert _is_ip_blocked("10.255.255.255") is True

    def test_blocks_private_class_b(self):
        """Test that 172.16.x.x addresses are blocked."""
        assert _is_ip_blocked("172.16.0.1") is True
        assert _is_ip_blocked("172.31.255.255") is True

    def test_blocks_private_class_c(self):
        """Test that 192.168.x.x addresses are blocked."""
        assert _is_ip_blocked("192.168.0.1") is True
        assert _is_ip_blocked("192.168.255.255") is True

    def test_blocks_loopback(self):
        """Test that loopback addresses are blocked."""
        assert _is_ip_blocked("127.0.0.1") is True
        assert _is_ip_blocked("127.0.0.100") is True

    def test_blocks_link_local(self):
        """Test that link-local addresses are blocked."""
        assert _is_ip_blocked("169.254.0.1") is True
        assert _is_ip_blocked("169.254.169.254") is True

    def test_allows_public_ips(self):
        """Test that public IP addresses are allowed."""
        assert _is_ip_blocked("8.8.8.8") is False
        assert _is_ip_blocked("1.1.1.1") is False
        assert _is_ip_blocked("142.250.185.238") is False

    def test_non_ip_returns_false(self):
        """Test that hostnames return False."""
        assert _is_ip_blocked("google.com") is False
        assert _is_ip_blocked("example.org") is False


class TestValidateImageUrl:
    """Tests for validate_image_url function."""

    def test_valid_firebase_storage_url(self):
        """Test valid Firebase Storage URL."""
        url = "https://firebasestorage.googleapis.com/v0/b/bucket/o/image.jpg"
        result = validate_image_url(url)
        assert result == url

    def test_valid_gcs_url(self):
        """Test valid Google Cloud Storage URL."""
        url = "https://storage.googleapis.com/bucket/image.jpg"
        result = validate_image_url(url)
        assert result == url

    def test_valid_cloudinary_url(self):
        """Test valid Cloudinary URL."""
        url = "https://res.cloudinary.com/demo/image/upload/sample.jpg"
        result = validate_image_url(url)
        assert result == url

    def test_strips_whitespace(self):
        """Test that whitespace is stripped from URL."""
        url = "  https://firebasestorage.googleapis.com/image.jpg  "
        result = validate_image_url(url)
        assert result == url.strip()

    def test_rejects_empty_url(self):
        """Test that empty URL is rejected."""
        with pytest.raises(ImageURLError, match="URL is required"):
            validate_image_url("")

    def test_rejects_none_url(self):
        """Test that None URL is rejected."""
        with pytest.raises(ImageURLError, match="URL is required"):
            validate_image_url(None)

    def test_rejects_non_string(self):
        """Test that non-string URL is rejected."""
        with pytest.raises(ImageURLError, match="URL is required"):
            validate_image_url(12345)

    def test_rejects_file_protocol(self):
        """Test that file:// protocol is rejected."""
        with pytest.raises(ImageURLError, match="file://"):
            validate_image_url("file:///etc/passwd")

    def test_rejects_data_protocol(self):
        """Test that data: protocol is rejected."""
        with pytest.raises(ImageURLError, match="data:"):
            validate_image_url("data:image/png;base64,abc123")

    def test_rejects_ftp_protocol(self):
        """Test that ftp:// protocol is rejected."""
        with pytest.raises(ImageURLError, match="ftp://"):
            validate_image_url("ftp://example.com/image.jpg")

    def test_rejects_invalid_url_format(self):
        """Test that invalid URL format is rejected."""
        with pytest.raises(ImageURLError, match="(Invalid URL|URL scheme)"):
            validate_image_url("not a url at all : : : ://")

    def test_rejects_private_ip(self):
        """Test that private IP addresses are rejected."""
        with pytest.raises(ImageURLError, match="private"):
            validate_image_url("https://192.168.1.1/image.jpg")

    def test_rejects_metadata_hostname(self):
        """Test that cloud metadata hostnames are rejected."""
        with pytest.raises(ImageURLError, match="not allowed"):
            validate_image_url("http://metadata.google.internal/")

    def test_rejects_url_without_hostname(self):
        """Test that URL without hostname is rejected."""
        with pytest.raises(ImageURLError, match="hostname"):
            validate_image_url("https:///image.jpg")

    def test_rejects_blocked_hostnames(self):
        """Test that blocked hostnames are rejected."""
        for hostname in BLOCKED_HOSTNAMES:
            with pytest.raises(ImageURLError, match="not allowed"):
                validate_image_url(f"http://{hostname}/")

    def test_rejects_url_with_credentials(self):
        """Test that URLs with credentials are rejected."""
        with pytest.raises(ImageURLError, match="credentials"):
            validate_image_url("https://user:pass@firebasestorage.googleapis.com/image.jpg")

    def test_rejects_disallowed_domain(self):
        """Test that disallowed domains are rejected."""
        with pytest.raises(ImageURLError, match="not in the allowed list"):
            validate_image_url("https://evil-site.com/malware.jpg")

    def test_allows_additional_domains(self):
        """Test that additional domains can be allowed."""
        url = "https://custom-cdn.example.com/image.jpg"
        result = validate_image_url(url, additional_domains={"custom-cdn.example.com"})
        assert result == url

    def test_allows_any_domain_flag(self):
        """Test that allow_any_domain bypasses domain check."""
        url = "https://any-domain.com/image.jpg"
        result = validate_image_url(url, allow_any_domain=True)
        assert result == url

    def test_allows_subdomain_matching(self):
        """Test that subdomains of allowed domains work."""
        url = "https://subdomain.firebasestorage.googleapis.com/image.jpg"
        result = validate_image_url(url)
        assert result == url

    def test_rejects_non_standard_port_in_production(self):
        """Test that non-standard ports are rejected in production."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            with pytest.raises(ImageURLError, match="port"):
                validate_image_url("https://firebasestorage.googleapis.com:9999/image.jpg")

    def test_rejects_http_in_production(self):
        """Test that HTTP URLs are rejected in production."""
        with (
            patch.dict(os.environ, {"ENVIRONMENT": "production"}),
            patch("fcp.security.url_validator.ALLOWED_SCHEMES", {"https"}),
        ):
            with pytest.raises(ImageURLError, match="HTTP URLs are not allowed"):
                validate_image_url("http://firebasestorage.googleapis.com/image.jpg")

    def test_allows_dev_ports_in_development(self):
        """Test that common dev ports are allowed in development."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            url = "http://localhost:8080/image.jpg"
            result = validate_image_url(url)
            assert result == url


class TestValidateContentType:
    """Tests for validate_content_type function."""

    def test_valid_jpeg(self):
        """Test that image/jpeg is valid."""
        assert validate_content_type("image/jpeg") is True

    def test_valid_png(self):
        """Test that image/png is valid."""
        assert validate_content_type("image/png") is True

    def test_valid_webp(self):
        """Test that image/webp is valid."""
        assert validate_content_type("image/webp") is True

    def test_valid_gif(self):
        """Test that image/gif is valid."""
        assert validate_content_type("image/gif") is True

    def test_valid_heic(self):
        """Test that image/heic is valid."""
        assert validate_content_type("image/heic") is True

    def test_valid_with_charset(self):
        """Test that content type with charset is handled."""
        assert validate_content_type("image/jpeg; charset=utf-8") is True

    def test_rejects_text_html(self):
        """Test that text/html is rejected."""
        assert validate_content_type("text/html") is False

    def test_rejects_application_json(self):
        """Test that application/json is rejected."""
        assert validate_content_type("application/json") is False

    def test_rejects_none(self):
        """Test that None is rejected."""
        assert validate_content_type(None) is False

    def test_rejects_empty_string(self):
        """Test that empty string is rejected."""
        assert validate_content_type("") is False

    def test_case_insensitive(self):
        """Test that content type check is case insensitive."""
        assert validate_content_type("IMAGE/JPEG") is True
        assert validate_content_type("Image/Png") is True


class TestAllowedDomainsConfig:
    """Tests for ALLOWED_DOMAINS configuration."""

    def test_firebase_storage_allowed(self):
        """Test that Firebase Storage is allowed."""
        assert "firebasestorage.googleapis.com" in ALLOWED_DOMAINS

    def test_gcs_allowed(self):
        """Test that GCS is allowed."""
        assert "storage.googleapis.com" in ALLOWED_DOMAINS

    def test_cloudinary_allowed(self):
        """Test that Cloudinary is allowed."""
        assert "res.cloudinary.com" in ALLOWED_DOMAINS

    def test_localhost_allowed_for_dev(self):
        """Test that localhost is allowed for development."""
        assert "localhost" in ALLOWED_DOMAINS


class TestAllowedContentTypesConfig:
    """Tests for ALLOWED_CONTENT_TYPES configuration."""

    def test_common_image_types_allowed(self):
        """Test that common image types are in the allowed list."""
        assert "image/jpeg" in ALLOWED_CONTENT_TYPES
        assert "image/png" in ALLOWED_CONTENT_TYPES
        assert "image/gif" in ALLOWED_CONTENT_TYPES
        assert "image/webp" in ALLOWED_CONTENT_TYPES


class TestVerifyUrlReachability:
    """Tests for verify_url_reachability function."""

    @pytest.mark.asyncio
    async def test_reachable_valid_image(self):
        """Test URL is reachable and returns valid image type."""
        from fcp.security.url_validator import verify_url_reachability

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/jpeg"}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.head.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await verify_url_reachability("https://example.com/image.jpg")
            assert result is True

    @pytest.mark.asyncio
    async def test_reachable_invalid_content_type(self):
        """Test URL is reachable but returns invalid content type."""
        from fcp.security.url_validator import verify_url_reachability

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.head.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await verify_url_reachability("https://example.com/image.jpg")
            assert result is False

    @pytest.mark.asyncio
    async def test_unreachable_404(self):
        """Test URL returns 404."""
        from fcp.security.url_validator import verify_url_reachability

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.head.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            # Fallback stream returns 404 when attempted
            mock_stream_ctx = MagicMock()
            mock_stream_ctx.__aenter__ = AsyncMock(return_value=MagicMock(status_code=404))
            mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream = MagicMock(return_value=mock_stream_ctx)

            result = await verify_url_reachability("https://example.com/image.jpg")
            assert result is False

    @pytest.mark.asyncio
    async def test_fallback_to_get_on_403(self):
        """Test fallback to GET when HEAD returns 403."""
        from fcp.security.url_validator import verify_url_reachability

        mock_head_response = MagicMock()
        mock_head_response.status_code = 403

        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.headers = {"Content-Type": "image/png"}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()  # Use MagicMock as base, not AsyncMock

            # head is an async method -> AsyncMock
            mock_client.head = AsyncMock(return_value=mock_head_response)

            # stream is a sync method returning async CM -> MagicMock
            mock_stream_ctx = MagicMock()
            mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_get_response)
            mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream = MagicMock(return_value=mock_stream_ctx)

            # Context manager for AsyncClient itself
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client_cls.return_value = mock_client

            result = await verify_url_reachability("https://example.com/image.png")
            assert result is True
            mock_client.head.assert_called_once()
            mock_client.stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_static_validation_failure(self):
        """Test static validation fails before network request."""
        from fcp.security.url_validator import verify_url_reachability

        with patch("httpx.AsyncClient") as mock_client_cls:
            # Should fail because scheme is not http/https
            result = await verify_url_reachability("ftp://example.com/image.jpg")
            assert result is False
            mock_client_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test network exception handling."""
        from fcp.security.url_validator import verify_url_reachability

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.head.side_effect = Exception("Connection error")
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await verify_url_reachability("https://example.com/image.jpg")
            assert result is False

    @pytest.mark.asyncio
    async def test_fallback_get_non_200_status(self):
        """Test fallback GET returns non-200 status."""
        from fcp.security.url_validator import verify_url_reachability

        mock_head_response = MagicMock()
        mock_head_response.status_code = 405  # Method not allowed

        mock_get_response = MagicMock()
        mock_get_response.status_code = 404  # Not found

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.head = AsyncMock(return_value=mock_head_response)

            mock_stream_ctx = MagicMock()
            mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_get_response)
            mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_client.stream = MagicMock(return_value=mock_stream_ctx)

            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client_cls.return_value = mock_client

            result = await verify_url_reachability("https://example.com/image.png")
            assert result is False

    @pytest.mark.asyncio
    async def test_fallback_get_exception(self):
        """Test fallback GET raises exception."""
        from fcp.security.url_validator import verify_url_reachability

        mock_head_response = MagicMock()
        mock_head_response.status_code = 403  # Forbidden

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.head = AsyncMock(return_value=mock_head_response)

            # Make stream raise an exception
            mock_stream_ctx = MagicMock()
            mock_stream_ctx.__aenter__ = AsyncMock(side_effect=Exception("Stream failed"))
            mock_client.stream = MagicMock(return_value=mock_stream_ctx)

            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client_cls.return_value = mock_client

            result = await verify_url_reachability("https://example.com/image.png")
            assert result is False

    @pytest.mark.asyncio
    async def test_non_retryable_error_code(self):
        """Test HEAD returns non-retryable error (not in 403, 404, 405)."""
        from fcp.security.url_validator import verify_url_reachability

        mock_head_response = MagicMock()
        mock_head_response.status_code = 500  # Server error - not retryable

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.head = AsyncMock(return_value=mock_head_response)

            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)

            mock_client_cls.return_value = mock_client

            result = await verify_url_reachability("https://example.com/image.png")
            assert result is False
            # Verify stream was never called (no fallback for 500)
            mock_client.stream.assert_not_called()


class TestValidateBrowserUrl:
    """Tests for validate_browser_url (SSRF protection for browser automation)."""

    def test_allows_valid_https_url(self):
        assert validate_browser_url("https://example.com/recipe") == "https://example.com/recipe"

    def test_allows_valid_http_url(self):
        assert validate_browser_url("http://example.com/recipe") == "http://example.com/recipe"

    def test_allows_arbitrary_domains(self):
        """Unlike validate_image_url, browser URLs allow any domain."""
        assert validate_browser_url("https://www.seriouseats.com/recipe") == "https://www.seriouseats.com/recipe"

    def test_rejects_empty_url(self):
        with pytest.raises(ImageURLError, match="URL is required"):
            validate_browser_url("")

    def test_rejects_none_url(self):
        with pytest.raises(ImageURLError, match="URL is required"):
            validate_browser_url(None)

    def test_rejects_file_scheme(self):
        with pytest.raises(ImageURLError, match="file://"):
            validate_browser_url("file:///etc/passwd")

    def test_rejects_data_scheme(self):
        with pytest.raises(ImageURLError, match="data:"):
            validate_browser_url("data:text/html,<h1>hi</h1>")

    def test_rejects_ftp_scheme(self):
        with pytest.raises(ImageURLError, match="ftp://"):
            validate_browser_url("ftp://evil.com/file")

    def test_rejects_javascript_scheme(self):
        with pytest.raises(ImageURLError, match="javascript:"):
            validate_browser_url("javascript:alert(1)")

    def test_rejects_metadata_google_internal(self):
        with pytest.raises(ImageURLError, match="not allowed"):
            validate_browser_url("http://metadata.google.internal/computeMetadata/v1/")

    def test_rejects_aws_metadata_ip(self):
        with pytest.raises(ImageURLError, match="not allowed"):
            validate_browser_url("http://169.254.169.254/latest/meta-data/")

    def test_rejects_private_ip_10(self):
        with pytest.raises(ImageURLError, match="private/internal"):
            validate_browser_url("http://10.0.0.1/admin")

    def test_rejects_private_ip_192(self):
        with pytest.raises(ImageURLError, match="private/internal"):
            validate_browser_url("http://192.168.1.1/admin")

    def test_rejects_loopback_ip(self):
        with pytest.raises(ImageURLError, match="private/internal"):
            validate_browser_url("http://127.0.0.1/admin")

    def test_rejects_credentials_in_url(self):
        with pytest.raises(ImageURLError, match="credentials"):
            validate_browser_url("https://user@example.com/recipe")

    def test_rejects_no_hostname(self):
        with pytest.raises(ImageURLError, match="hostname"):
            validate_browser_url("https://")

    def test_rejects_invalid_scheme(self):
        with pytest.raises(ImageURLError, match="scheme must be"):
            validate_browser_url("gopher://example.com/recipe")

    def test_strips_whitespace(self):
        assert validate_browser_url("  https://example.com/recipe  ") == "https://example.com/recipe"

    def test_urlparse_exception(self):
        with patch("fcp.security.url_validator.urlparse", side_effect=Exception("Parse failed")):
            with pytest.raises(ImageURLError, match="Invalid URL format"):
                validate_browser_url("https://example.com/recipe")


class TestUrlParseException:
    """Tests for urlparse exception handling."""

    def test_urlparse_exception_raises_invalid_url_error(self):
        """Test that urlparse exception triggers ImageURLError."""
        with patch("fcp.security.url_validator.urlparse", side_effect=Exception("Parse failed")):
            with pytest.raises(ImageURLError, match="Invalid URL format"):
                validate_image_url("https://example.com/image.jpg")
