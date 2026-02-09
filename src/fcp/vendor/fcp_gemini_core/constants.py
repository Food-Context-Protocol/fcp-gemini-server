"""Shared constants for Gemini API.

These are pure, dependency-free constants that can be used across
fcp-gemini-server, gemini-connector, and other FCP components.
"""

# =============================================================================
# Model Identifiers
# =============================================================================

# Gemini 3 Flash Preview - Latest experimental features
GEMINI_3_FLASH_PREVIEW = "gemini-3-flash-preview"

# Gemini 3 Flash - Stable release
GEMINI_3_FLASH = "gemini-3-flash"

# Gemini 3 Live Preview - For real-time streaming
GEMINI_3_LIVE_PREVIEW = "gemini-3-live-preview"

# Default model for general use
DEFAULT_MODEL = GEMINI_3_FLASH_PREVIEW


# =============================================================================
# API Configuration
# =============================================================================

# HTTP timeout for API requests (seconds)
DEFAULT_TIMEOUT_SECONDS = 30.0

# Maximum retry attempts for transient failures
MAX_RETRIES = 3

# Exponential backoff configuration
RETRY_INITIAL_DELAY = 1.0  # seconds
RETRY_MAX_DELAY = 10.0  # seconds


# =============================================================================
# Safety Settings
# =============================================================================

# Default safety threshold for content filtering
DEFAULT_SAFETY_THRESHOLD = "BLOCK_MEDIUM_AND_ABOVE"

# Safety categories
SAFETY_CATEGORIES = [
    "HARM_CATEGORY_HARASSMENT",
    "HARM_CATEGORY_HATE_SPEECH",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "HARM_CATEGORY_DANGEROUS_CONTENT",
]


# =============================================================================
# Generation Parameters
# =============================================================================

# Temperature controls randomness (0.0 = deterministic, 1.0 = creative)
DEFAULT_TEMPERATURE = 0.7

# Top-p (nucleus sampling) - cumulative probability threshold
DEFAULT_TOP_P = 0.95

# Top-k - number of top tokens to consider
DEFAULT_TOP_K = 40

# Maximum output tokens
DEFAULT_MAX_OUTPUT_TOKENS = 8192


# =============================================================================
# Media Resolution Presets
# =============================================================================

# Media resolution levels (in pixels, longest dimension)
MEDIA_RESOLUTION_LOW = 400  # Fast, low cost
MEDIA_RESOLUTION_MEDIUM = 800  # Balanced
MEDIA_RESOLUTION_HIGH = 1600  # High quality, slower


# =============================================================================
# Token Costs (per 1M tokens)
# =============================================================================

# Gemini 3 Flash pricing as of 2026-02
# See: https://ai.google.dev/pricing
DEFAULT_COST_PER_INPUT_TOKEN = 0.0001  # $0.10 per 1M input tokens
DEFAULT_COST_PER_OUTPUT_TOKEN = 0.0003  # $0.30 per 1M output tokens


# =============================================================================
# Limits
# =============================================================================

# Maximum image size (bytes) - 10MB
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024

# Maximum video size (bytes) - 100MB
MAX_VIDEO_SIZE_BYTES = 100 * 1024 * 1024

# Maximum audio size (bytes) - 20MB
MAX_AUDIO_SIZE_BYTES = 20 * 1024 * 1024


# =============================================================================
# Thinking Budget Presets (in tokens)
# =============================================================================

THINKING_BUDGET_MINIMAL = 512
THINKING_BUDGET_LOW = 1024
THINKING_BUDGET_MEDIUM = 2048
THINKING_BUDGET_HIGH = 4096

THINKING_BUDGETS = {
    "minimal": THINKING_BUDGET_MINIMAL,
    "low": THINKING_BUDGET_LOW,
    "medium": THINKING_BUDGET_MEDIUM,
    "high": THINKING_BUDGET_HIGH,
}
