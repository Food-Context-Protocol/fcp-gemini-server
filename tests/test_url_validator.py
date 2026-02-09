"""
Tests for URL validation and SSRF prevention.

These tests verify that the URL validator properly:
- Blocks private/internal IP addresses
- Blocks dangerous URL schemes
- Enforces domain allowlist
- Handles production vs development modes
"""

import os
from unittest.mock import patch

import pytest

from fcp.security.url_validator import (
    ImageURLError,
    validate_content_type,
    validate_image_url,
)


class TestValidateImageUrl:
    """Tests for validate_image_url function."""

    def test_valid_https_url(self):
        """Test valid HTTPS URL from allowed domain."""
        url = "https://firebasestorage.googleapis.com/image.jpg"
        result = validate_image_url(url)
        assert result == url

    def test_valid_wikimedia_url(self):
        """Test valid Wikimedia URL."""
        url = "https://upload.wikimedia.org/wikipedia/commons/image.jpg"
        result = validate_image_url(url)
        assert result == url

    def test_blocks_file_scheme(self):
        """Test that file:// URLs are blocked."""
        with pytest.raises(ImageURLError, match="file:// URLs are not allowed"):
            validate_image_url("file:///etc/passwd")

    def test_blocks_data_scheme(self):
        """Test that data: URLs are blocked."""
        with pytest.raises(ImageURLError, match="data: URLs are not allowed"):
            validate_image_url("data:image/png;base64,abc123")

    def test_blocks_ftp_scheme(self):
        """Test that ftp:// URLs are blocked."""
        with pytest.raises(ImageURLError, match="ftp:// URLs are not allowed"):
            validate_image_url("ftp://example.com/file.jpg")

    def test_blocks_metadata_endpoint(self):
        """Test that cloud metadata endpoints are blocked."""
        with pytest.raises(ImageURLError, match="not allowed"):
            validate_image_url("http://169.254.169.254/latest/meta-data/")

    def test_blocks_internal_metadata_hostname(self):
        """Test that internal metadata hostnames are blocked."""
        with pytest.raises(ImageURLError, match="not allowed"):
            validate_image_url("http://metadata.google.internal/")

    def test_blocks_private_ip_10(self):
        """Test that 10.x.x.x private IPs are blocked."""
        with pytest.raises(ImageURLError, match="private/internal IP"):
            validate_image_url("http://10.0.0.1/image.jpg")

    def test_blocks_private_ip_172(self):
        """Test that 172.16.x.x private IPs are blocked."""
        with pytest.raises(ImageURLError, match="private/internal IP"):
            validate_image_url("http://172.16.0.1/image.jpg")

    def test_blocks_private_ip_192(self):
        """Test that 192.168.x.x private IPs are blocked."""
        with pytest.raises(ImageURLError, match="private/internal IP"):
            validate_image_url("http://192.168.1.1/image.jpg")

    def test_blocks_url_with_credentials(self):
        """Test that URLs with embedded credentials are blocked."""
        with pytest.raises(ImageURLError, match="credentials"):
            # Use an allowed domain to reach the credentials check
            validate_image_url("https://user:pass@firebasestorage.googleapis.com/image.jpg")

    def test_blocks_disallowed_domain(self):
        """Test that domains not in allowlist are blocked."""
        with pytest.raises(ImageURLError, match="not in the allowed list"):
            validate_image_url("https://evil-site.com/image.jpg")

    def test_allows_any_domain_flag(self):
        """Test allow_any_domain bypasses domain check."""
        url = "https://any-domain.com/image.jpg"
        result = validate_image_url(url, allow_any_domain=True)
        assert result == url

    def test_additional_domains(self):
        """Test additional_domains parameter."""
        url = "https://custom-cdn.example.com/image.jpg"
        result = validate_image_url(url, additional_domains={"custom-cdn.example.com"})
        assert result == url

    def test_empty_url_raises(self):
        """Test that empty URL raises error."""
        with pytest.raises(ImageURLError, match="URL is required"):
            validate_image_url("")

    def test_none_url_raises(self):
        """Test that None URL raises error."""
        with pytest.raises(ImageURLError, match="URL is required"):
            validate_image_url(None)  # type: ignore

    def test_url_without_hostname(self):
        """Test URL without hostname raises error."""
        with pytest.raises(ImageURLError, match="must have a hostname"):
            validate_image_url("https:///path/image.jpg")


class TestProductionMode:
    """Tests for production mode behavior."""

    def test_localhost_blocked_in_production(self):
        """Test that localhost is NOT in ALLOWED_DOMAINS in production."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            import fcp.security.url_validator as validator

            # Simulate production allowlist (no localhost entries).
            with patch.object(validator, "ALLOWED_DOMAINS", validator._BASE_ALLOWED_DOMAINS.copy()):
                assert "localhost" not in validator.ALLOWED_DOMAINS
                assert "127.0.0.1" not in validator.ALLOWED_DOMAINS

    def test_http_blocked_in_production(self):
        """Test that HTTP URLs are blocked in production."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            import fcp.security.url_validator as validator

            with patch.object(validator, "ALLOWED_SCHEMES", {"https"}):
                with pytest.raises(validator.ImageURLError, match="HTTPS"):
                    validator.validate_image_url("http://firebasestorage.googleapis.com/image.jpg")


class TestValidateContentType:
    """Tests for validate_content_type function."""

    def test_valid_jpeg(self):
        """Test valid JPEG content type."""
        assert validate_content_type("image/jpeg") is True

    def test_valid_png(self):
        """Test valid PNG content type."""
        assert validate_content_type("image/png") is True

    def test_valid_webp(self):
        """Test valid WebP content type."""
        assert validate_content_type("image/webp") is True

    def test_valid_with_charset(self):
        """Test content type with charset parameter."""
        assert validate_content_type("image/jpeg; charset=utf-8") is True

    def test_invalid_text(self):
        """Test invalid text content type."""
        assert validate_content_type("text/html") is False

    def test_invalid_application(self):
        """Test invalid application content type."""
        assert validate_content_type("application/json") is False

    def test_none_content_type(self):
        """Test None content type."""
        assert validate_content_type(None) is False

    def test_empty_content_type(self):
        """Test empty content type."""
        assert validate_content_type("") is False
