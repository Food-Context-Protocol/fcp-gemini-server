"""Application configuration constants.

Environment-based config moved to settings.py (pydantic-settings).
This module now contains only static constants.
"""

from dataclasses import dataclass

from fcp.settings import settings

# ==========================================================================
# Re-export settings for convenience
# ==========================================================================
GEMINI_API_KEY = settings.gemini_api_key
GOOGLE_MAPS_API_KEY = settings.google_maps_api_key
USDA_API_KEY = settings.usda_api_key
FDA_API_KEY = settings.fda_api_key
DATA_DIR = settings.fcp_data_dir
FCP_SERVER_URL = settings.fcp_server_url
USER_ID = settings.fcp_user_id


@dataclass(frozen=True)
class _Config:
    """Static configuration constants (not loaded from environment)."""

    # ==========================================================================
    # Model Configuration
    # ==========================================================================
    GEMINI_MODEL_NAME: str = "gemini-3-flash-preview"
    GEMINI_LIVE_MODEL_NAME: str = "gemini-2.0-flash-live-preview-04-09"
    VEO_MODEL_NAME: str = "veo-3.1-generate-preview"
    DEEP_RESEARCH_AGENT: str = "deep-research-pro-preview-12-2025"

    # ==========================================================================
    # Timeouts (seconds)
    # ==========================================================================
    HTTP_TIMEOUT_SECONDS: float = 30.0
    GEMINI_TIMEOUT_SECONDS: float = 60.0
    VIDEO_GENERATION_TIMEOUT_SECONDS: int = 300
    DEEP_RESEARCH_TIMEOUT_SECONDS: int = 300

    # ==========================================================================
    # Size Limits (bytes)
    # ==========================================================================
    MAX_IMAGE_SIZE_BYTES: int = 10 * 1024 * 1024
    MAX_REQUEST_SIZE_BYTES: int = 50 * 1024 * 1024
    MAX_USER_INPUT_LENGTH: int = 10000

    # ==========================================================================
    # Connection Pooling
    # ==========================================================================
    HTTP_MAX_CONNECTIONS: int = 100
    HTTP_MAX_KEEPALIVE_CONNECTIONS: int = 20

    # ==========================================================================
    # Retry Configuration
    # ==========================================================================
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_MIN_WAIT_SECONDS: float = 1.0
    RETRY_MAX_WAIT_SECONDS: float = 10.0

    # ==========================================================================
    # Circuit Breaker
    # ==========================================================================
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS: float = 30.0
    CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS: int = 3

    # ==========================================================================
    # Rate Limiting
    # ==========================================================================
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_ANALYZE: str = "30/minute"
    RATE_LIMIT_EXPENSIVE: str = "10/minute"

    # ==========================================================================
    # Gemini Pricing (per 1M tokens)
    # ==========================================================================
    GEMINI_COST_PER_INPUT_TOKEN: float = 0.50 / 1_000_000
    GEMINI_COST_PER_OUTPUT_TOKEN: float = 3.00 / 1_000_000

    # ==========================================================================
    # Thinking Budget (tokens)
    # ==========================================================================
    THINKING_BUDGET_MINIMAL: int = 1024
    THINKING_BUDGET_LOW: int = 4096
    THINKING_BUDGET_MEDIUM: int = 16384
    THINKING_BUDGET_HIGH: int = 32768

    # ==========================================================================
    # Feature Flags (delegated to settings)
    # ==========================================================================
    @property
    def ENABLE_METRICS(self) -> bool:  # noqa: N802
        return settings.enable_metrics

    @property
    def ENABLE_AUDIT_LOGGING(self) -> bool:  # noqa: N802
        return settings.enable_audit_logging

    @property
    def ENABLE_TELEMETRY(self) -> bool:  # noqa: N802
        return settings.enable_telemetry

    @property
    def IS_PRODUCTION(self) -> bool:  # noqa: N802
        return settings.is_production

    @property
    def IS_CLOUD_RUN(self) -> bool:  # noqa: N802
        return settings.is_cloud_run

    # ==========================================================================
    # CORS Configuration
    # ==========================================================================
    PRODUCTION_CORS_ORIGINS: tuple[str, ...] = (
        "https://fcp.dev",
        "https://app.fcp.dev",
        "https://www.fcp.dev",
        "https://api.fcp.dev",
    )

    DEVELOPMENT_CORS_ORIGINS: tuple[str, ...] = (
        "http://localhost:8080",
        "http://localhost:3000",
        "http://localhost:5000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:3000",
    )

    # ==========================================================================
    # Service Info
    # ==========================================================================
    SERVICE_NAME: str = "fcp-gemini-server"
    API_VERSION: str = "1.1.0"


Config = _Config()


# Backward compatibility for code that uses these functions
def get_fcp_server_url() -> str:
    """Get FCP server URL."""
    return settings.fcp_server_url


def get_user_id() -> str:
    """Get user ID."""
    return settings.fcp_user_id
