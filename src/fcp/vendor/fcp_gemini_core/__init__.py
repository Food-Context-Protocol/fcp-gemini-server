"""FCP Gemini Core - Shared Gemini service layer.

This package contains the shared, dependency-free Gemini service components
used across the FCP ecosystem (fcp-gemini-server, gemini-connector).
"""

__version__ = "1.0.0"

from .constants import (
    # Costs
    DEFAULT_COST_PER_INPUT_TOKEN,
    DEFAULT_COST_PER_OUTPUT_TOKEN,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MODEL,
    # Generation parameters
    DEFAULT_TEMPERATURE,
    # API Configuration
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_TOP_K,
    DEFAULT_TOP_P,
    GEMINI_3_FLASH,
    # Model identifiers
    GEMINI_3_FLASH_PREVIEW,
    GEMINI_3_LIVE_PREVIEW,
    MAX_AUDIO_SIZE_BYTES,
    # Limits
    MAX_IMAGE_SIZE_BYTES,
    MAX_RETRIES,
    MAX_VIDEO_SIZE_BYTES,
    MEDIA_RESOLUTION_HIGH,
    # Media resolution
    MEDIA_RESOLUTION_LOW,
    MEDIA_RESOLUTION_MEDIUM,
    RETRY_INITIAL_DELAY,
    RETRY_MAX_DELAY,
    THINKING_BUDGET_HIGH,
    THINKING_BUDGET_LOW,
    THINKING_BUDGET_MEDIUM,
    THINKING_BUDGET_MINIMAL,
    # Thinking budgets
    THINKING_BUDGETS,
)

__all__ = [
    # Model constants
    "GEMINI_3_FLASH_PREVIEW",
    "GEMINI_3_FLASH",
    "GEMINI_3_LIVE_PREVIEW",
    "DEFAULT_MODEL",
    # API config
    "DEFAULT_TIMEOUT_SECONDS",
    "MAX_RETRIES",
    "RETRY_INITIAL_DELAY",
    "RETRY_MAX_DELAY",
    # Generation
    "DEFAULT_TEMPERATURE",
    "DEFAULT_TOP_P",
    "DEFAULT_TOP_K",
    "DEFAULT_MAX_OUTPUT_TOKENS",
    # Media
    "MEDIA_RESOLUTION_LOW",
    "MEDIA_RESOLUTION_MEDIUM",
    "MEDIA_RESOLUTION_HIGH",
    # Thinking
    "THINKING_BUDGETS",
    "THINKING_BUDGET_MINIMAL",
    "THINKING_BUDGET_LOW",
    "THINKING_BUDGET_MEDIUM",
    "THINKING_BUDGET_HIGH",
    # Limits
    "MAX_IMAGE_SIZE_BYTES",
    "MAX_VIDEO_SIZE_BYTES",
    "MAX_AUDIO_SIZE_BYTES",
    # Costs
    "DEFAULT_COST_PER_INPUT_TOKEN",
    "DEFAULT_COST_PER_OUTPUT_TOKEN",
]
