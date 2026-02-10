"""Tests for centralized configuration."""
# sourcery skip: no-loop-in-tests, no-conditionals-in-tests

from unittest.mock import patch

from fcp.config import Config


class TestConfig:
    """Tests for Config class."""

    def test_gemini_model_name(self):
        """Config has correct Gemini model name."""
        assert Config.GEMINI_MODEL_NAME == "gemini-3-flash-preview"

    def test_veo_model_name(self):
        """Config has correct Veo model name."""
        assert Config.VEO_MODEL_NAME == "veo-3.1-generate-preview"

    def test_http_timeout(self):
        """Config has correct HTTP timeout."""
        assert Config.HTTP_TIMEOUT_SECONDS == 30.0

    def test_max_image_size(self):
        """Config has correct max image size."""
        assert Config.MAX_IMAGE_SIZE_BYTES == 10 * 1024 * 1024  # 10MB

    def test_connection_pooling_limits(self):
        """Config has correct connection pooling limits."""
        assert Config.HTTP_MAX_CONNECTIONS == 100
        assert Config.HTTP_MAX_KEEPALIVE_CONNECTIONS == 20

    def test_retry_configuration(self):
        """Config has correct retry configuration."""
        assert Config.RETRY_MAX_ATTEMPTS == 3
        assert Config.RETRY_MIN_WAIT_SECONDS == 1.0
        assert Config.RETRY_MAX_WAIT_SECONDS == 10.0

    def test_circuit_breaker_configuration(self):
        """Config has correct circuit breaker configuration."""
        assert Config.CIRCUIT_BREAKER_FAILURE_THRESHOLD == 5
        assert Config.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS == 30.0
        assert Config.CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS == 3

    def test_rate_limits(self):
        """Config has correct rate limits."""
        assert Config.RATE_LIMIT_DEFAULT == "100/minute"
        assert Config.RATE_LIMIT_ANALYZE == "30/minute"
        assert Config.RATE_LIMIT_EXPENSIVE == "10/minute"

    def test_gemini_pricing(self):
        """Config has correct Gemini pricing."""
        assert Config.GEMINI_COST_PER_INPUT_TOKEN == 0.50 / 1_000_000
        assert Config.GEMINI_COST_PER_OUTPUT_TOKEN == 3.00 / 1_000_000

    def test_thinking_budgets(self):
        """Config has correct thinking budgets."""
        assert Config.THINKING_BUDGET_MINIMAL == 1024
        assert Config.THINKING_BUDGET_LOW == 4096
        assert Config.THINKING_BUDGET_MEDIUM == 16384
        assert Config.THINKING_BUDGET_HIGH == 32768

    def test_cors_origins(self):
        """Config has correct CORS origins."""
        assert "https://fcp.dev" in list(Config.PRODUCTION_CORS_ORIGINS)
        assert "http://localhost:8080" in Config.DEVELOPMENT_CORS_ORIGINS

    def test_service_info(self):
        """Config has correct service info."""
        assert Config.SERVICE_NAME == "fcp-gemini-server"
        assert Config.API_VERSION == "1.1.0"


class TestConfigEnvironmentVariables:
    """Tests for environment variable properties via pydantic-settings.

    NOTE: With pydantic-settings, settings are loaded once at import time.
    These tests verify the module-level constants exported from config.py.
    """

    def test_gemini_api_key_from_env(self):
        """GEMINI_API_KEY is exported as module constant from settings."""
        from fcp.config import GEMINI_API_KEY

        # Should be set by test environment (conftest.py)
        assert GEMINI_API_KEY is not None

    def test_google_maps_api_key_optional(self):
        """GOOGLE_MAPS_API_KEY is optional."""
        from fcp.config import GOOGLE_MAPS_API_KEY

        # Optional - can be None
        assert GOOGLE_MAPS_API_KEY is None or isinstance(GOOGLE_MAPS_API_KEY, str)

    def test_usda_api_key_optional(self):
        """USDA_API_KEY is optional."""
        from fcp.config import USDA_API_KEY

        # Optional - can be None
        assert USDA_API_KEY is None or isinstance(USDA_API_KEY, str)


class TestConfigFeatureFlags:
    """Tests for feature flag properties via pydantic-settings.

    NOTE: Settings are loaded once at import. These tests verify Config
    correctly delegates to settings singleton (set by conftest.py).
    """

    def test_enable_metrics_delegates_to_settings(self):
        """ENABLE_METRICS delegates to settings."""
        # In test env, conftest sets ENABLE_METRICS=false
        assert isinstance(Config.ENABLE_METRICS, bool)

    def test_enable_audit_logging_delegates_to_settings(self):
        """ENABLE_AUDIT_LOGGING delegates to settings."""
        assert isinstance(Config.ENABLE_AUDIT_LOGGING, bool)

    def test_enable_telemetry_delegates_to_settings(self):
        """ENABLE_TELEMETRY delegates to settings."""
        assert isinstance(Config.ENABLE_TELEMETRY, bool)

    def test_is_production_in_test_environment(self):
        """IS_PRODUCTION returns False in test environment."""
        # conftest sets ENVIRONMENT=test
        assert Config.IS_PRODUCTION is False

    def test_is_cloud_run_false_locally(self):
        """IS_CLOUD_RUN returns False when K_SERVICE not set."""
        # K_SERVICE not set in test environment
        assert Config.IS_CLOUD_RUN is False

    def test_is_production_false_in_dev(self):
        """IS_PRODUCTION returns False in development."""
        # Settings already loaded with test environment
        assert Config.IS_PRODUCTION is False


class TestConfigCredentialValidation:
    """Tests for credential validation via pydantic-settings.

    NOTE: Validation now happens at Settings init time.
    These tests verify the module exports work correctly.
    """

    def test_gemini_api_key_validation_in_settings(self):
        """Gemini API key validation happens in Settings class."""
        from fcp.config import GEMINI_API_KEY

        # Should be valid test key from conftest
        assert GEMINI_API_KEY is not None
        assert GEMINI_API_KEY.startswith("AIza")

    def test_optional_api_keys_can_be_none(self):
        """Optional API keys can be None."""
        from fcp.config import FDA_API_KEY, GOOGLE_MAPS_API_KEY, USDA_API_KEY

        # These are optional
        assert FDA_API_KEY is None or isinstance(FDA_API_KEY, str)
        assert GOOGLE_MAPS_API_KEY is None or isinstance(GOOGLE_MAPS_API_KEY, str)
        assert USDA_API_KEY is None or isinstance(USDA_API_KEY, str)

    def test_data_dir_from_settings(self):
        """DATA_DIR is exported from settings."""
        from fcp.config import DATA_DIR

        assert isinstance(DATA_DIR, str)

    def test_fcp_server_url_from_settings(self):
        """FCP_SERVER_URL is exported from settings."""
        from fcp.config import FCP_SERVER_URL

        assert isinstance(FCP_SERVER_URL, str)

    def test_user_id_from_settings(self):
        """USER_ID is exported from settings."""
        from fcp.config import USER_ID

        assert isinstance(USER_ID, str)


class TestSettingsValidation:
    """Tests for Settings field validators."""

    def test_placeholder_api_key_accepted(self):
        """settings.py line 30: AIza_PLACEHOLDER passes validation."""
        from fcp.settings import Settings

        with patch.dict("os.environ", {"GEMINI_API_KEY": "AIza_PLACEHOLDER"}, clear=False):
            s = Settings(gemini_api_key="AIza_PLACEHOLDER")
            assert s.gemini_api_key == "AIza_PLACEHOLDER"
