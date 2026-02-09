"""Server-specific Gemini constants that bridge vendored core constants and server config.

This module imports shared constants from fcp.vendor.fcp_gemini_core and adds
server-specific configuration from fcp.config.
"""

import httpx

from fcp.config import GEMINI_API_KEY as _GEMINI_API_KEY
from fcp.config import Config
from fcp.vendor.fcp_gemini_core.constants import (
    # Costs
    DEFAULT_COST_PER_INPUT_TOKEN as _DEFAULT_COST_PER_INPUT_TOKEN,
)
from fcp.vendor.fcp_gemini_core.constants import (
    DEFAULT_COST_PER_OUTPUT_TOKEN as _DEFAULT_COST_PER_OUTPUT_TOKEN,
)
from fcp.vendor.fcp_gemini_core.constants import (
    DEFAULT_MODEL as _DEFAULT_MODEL,
)
from fcp.vendor.fcp_gemini_core.constants import (
    # Limits
    MAX_IMAGE_SIZE_BYTES as _MAX_IMAGE_SIZE_BYTES,
)

# Re-export shared constants from core
from fcp.vendor.fcp_gemini_core.constants import (
    THINKING_BUDGET_HIGH,
    THINKING_BUDGET_LOW,
    THINKING_BUDGET_MEDIUM,
    THINKING_BUDGET_MINIMAL,
)

# Server-specific configuration from Config
# These override the defaults if configured
GEMINI_API_KEY = _GEMINI_API_KEY
MODEL_NAME = Config.GEMINI_MODEL_NAME or _DEFAULT_MODEL
MAX_IMAGE_SIZE = Config.MAX_IMAGE_SIZE_BYTES or _MAX_IMAGE_SIZE_BYTES
COST_PER_INPUT_TOKEN = Config.GEMINI_COST_PER_INPUT_TOKEN or _DEFAULT_COST_PER_INPUT_TOKEN
COST_PER_OUTPUT_TOKEN = Config.GEMINI_COST_PER_OUTPUT_TOKEN or _DEFAULT_COST_PER_OUTPUT_TOKEN

# Thinking budgets from Config (use core defaults if not configured)
THINKING_BUDGETS = {
    "minimal": Config.THINKING_BUDGET_MINIMAL or THINKING_BUDGET_MINIMAL,
    "low": Config.THINKING_BUDGET_LOW or THINKING_BUDGET_LOW,
    "medium": Config.THINKING_BUDGET_MEDIUM or THINKING_BUDGET_MEDIUM,
    "high": Config.THINKING_BUDGET_HIGH or THINKING_BUDGET_HIGH,
}

# Exceptions that warrant retry (transient failures)
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.HTTPStatusError,  # Includes 429 rate limit, 503 service unavailable
)
