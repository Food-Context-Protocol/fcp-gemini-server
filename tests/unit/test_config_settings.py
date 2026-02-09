"""Tests for fcp.config module with pydantic-settings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from fcp.config import DATA_DIR, Config
from fcp.settings import Settings


class TestDataDir:
    """Tests for DATA_DIR constant from settings."""

    def test_data_dir_exported(self):
        """DATA_DIR is exported as a module constant from settings."""
        assert isinstance(DATA_DIR, str)
        # In test env, defaults to "data"
        assert DATA_DIR == "data"

    def test_config_has_static_constants(self):
        """Config class contains static constants."""
        # Verify static constants are accessible
        assert hasattr(Config, "GEMINI_MODEL_NAME")
        assert isinstance(Config.GEMINI_MODEL_NAME, str)


class TestGeminiKeyValidation:
    """Tests for Gemini API key validation rules."""

    def test_gemini_key_rejects_placeholder_values(self):
        """Gemini key validator rejects 'your-' placeholder."""
        with pytest.raises(ValidationError, match="GEMINI_API_KEY must be set to a valid API key"):
            Settings(gemini_api_key="your-api-key-here")

    def test_gemini_key_rejects_xxx_placeholder(self):
        """Gemini key validator rejects 'xxx' placeholder."""
        with pytest.raises(ValidationError, match="GEMINI_API_KEY must be set to a valid API key"):
            Settings(gemini_api_key="XXX_API_KEY")

    def test_gemini_key_rejects_changeme(self):
        """Gemini key validator rejects 'changeme' placeholder."""
        with pytest.raises(ValidationError, match="GEMINI_API_KEY must be set to a valid API key"):
            Settings(gemini_api_key="changeme")

    def test_gemini_key_must_start_with_aiza(self):
        """Gemini key validator requires 'AIza' prefix."""
        with pytest.raises(ValidationError, match="GEMINI_API_KEY must start with 'AIza'"):
            Settings(gemini_api_key="NotAValidKey123")

    def test_gemini_key_accepts_valid_format(self):
        """Gemini key validator accepts properly formatted keys."""
        # Should not raise
        settings = Settings(gemini_api_key="AIzaSyDummyKeyForTesting123456789")
        assert settings.gemini_api_key.startswith("AIza")


class TestEnvironmentProperties:
    """Tests for environment detection properties."""

    def test_is_test_detects_pytest(self, monkeypatch):
        """is_test property detects pytest in environment."""
        monkeypatch.setenv("_", "/path/to/pytest")
        settings = Settings(gemini_api_key="AIzaSyTestKey123", environment="development")
        assert settings.is_test is True

    def test_is_test_with_test_environment(self):
        """is_test property returns True when environment is 'test'."""
        settings = Settings(gemini_api_key="AIzaSyTestKey123", environment="test")
        assert settings.is_test is True

    def test_is_test_false_in_production(self, monkeypatch):
        """is_test property returns False in production without pytest."""
        monkeypatch.delenv("_", raising=False)
        settings = Settings(gemini_api_key="AIzaSyTestKey123", environment="production")
        assert settings.is_test is False


class TestHelperFunctions:
    """Tests for backward-compatible helper functions."""

    def test_get_fcp_server_url(self):
        from fcp.config import get_fcp_server_url

        assert isinstance(get_fcp_server_url(), str)

    def test_get_user_id(self):
        from fcp.config import get_user_id

        assert isinstance(get_user_id(), str)
