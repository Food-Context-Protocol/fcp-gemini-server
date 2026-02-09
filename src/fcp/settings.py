"""Type-safe application settings using pydantic-settings."""

import os
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with automatic validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown env vars
    )

    # ==========================================================================
    # Required API Keys
    # ==========================================================================
    gemini_api_key: str = Field("AIza_PLACEHOLDER", description="Gemini API key from ai.google.dev")

    @field_validator("gemini_api_key")
    @classmethod
    def validate_gemini_key(cls, v: str) -> str:
        """Validate Gemini API key format."""
        if v == "AIza_PLACEHOLDER":
            return v
        if not v or any(p in v.lower() for p in ["your-", "xxx", "placeholder", "changeme"]):
            raise ValueError("GEMINI_API_KEY must be set to a valid API key")
        if not v.startswith("AIza"):
            raise ValueError("GEMINI_API_KEY must start with 'AIza'")
        return v

    # ==========================================================================
    # Optional API Keys
    # ==========================================================================
    google_maps_api_key: str | None = Field(None, description="Google Maps API key")
    usda_api_key: str | None = Field(None, description="USDA FoodData Central API key")
    fda_api_key: str | None = Field(None, description="openFDA API key")

    # ==========================================================================
    # Authentication
    # ==========================================================================
    fcp_token: str | None = Field(None, description="Auth token for write access")
    fcp_user_id: str = Field("cli-user", description="Default user ID")

    # ==========================================================================
    # Database Configuration
    # ==========================================================================
    database_backend: Literal["sqlite", "firestore"] = Field(
        "sqlite",
        description="Database backend (sqlite for local, firestore for Cloud Run)",
    )
    fcp_data_dir: str = Field("data", description="Data directory path")
    database_url: str | None = Field(None, description="SQLite database URL")

    # Cloud Firestore (only needed if database_backend=firestore)
    google_cloud_project: str | None = Field(None, description="GCP project ID")
    google_application_credentials: str | None = Field(None, description="Path to service account JSON")

    # ==========================================================================
    # Server Configuration
    # ==========================================================================
    port: int = Field(8080, description="HTTP server port")
    environment: str = Field("development", description="Environment (development/production/test)")
    fcp_server_url: str = Field("http://localhost:8080", description="Server base URL")

    # ==========================================================================
    # Feature Flags
    # ==========================================================================
    enable_metrics: bool = Field(True, description="Enable Prometheus metrics")
    enable_audit_logging: bool = Field(True, description="Enable audit logging")
    enable_telemetry: bool = Field(True, description="Enable Logfire telemetry")

    # ==========================================================================
    # Rate Limiting
    # ==========================================================================
    rate_limit_per_minute: int = Field(60, description="API rate limit per minute")

    # ==========================================================================
    # Logfire Observability (optional)
    # ==========================================================================
    logfire_token: str | None = Field(None, description="Logfire API token")
    logfire_project_name: str = Field("fcp-gemini-server", description="Logfire project name")
    logfire_send_to_logfire: bool = Field(True, description="Send traces to Logfire cloud")
    fcp_logfire_console: bool = Field(True, description="Enable rich console output")
    fcp_logfire_capture_bodies: bool = Field(False, description="Capture HTTP request/response bodies")

    # ==========================================================================
    # Computed Properties
    # ==========================================================================
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        env_lower = self.environment.lower()
        return env_lower in {"production", "prod"} or self.is_cloud_run

    @property
    def is_cloud_run(self) -> bool:
        """Check if running on Google Cloud Run."""
        return os.getenv("K_SERVICE") is not None

    @property
    def is_test(self) -> bool:
        """Check if running in test environment."""
        return self.environment.lower() == "test" or "pytest" in os.getenv("_", "")


# Global settings instance - loaded once at import time
settings = Settings()
