"""Rate limiting for FCP API endpoints.

CRITICAL: This module prevents abuse and DoS attacks by limiting
the rate of requests to expensive endpoints.

Protections:
- Prevent API abuse
- Limit AI API costs from runaway requests
- Protect against credential stuffing
"""

import os

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from fcp.utils.metrics import record_rate_limit_exceeded


def _get_user_id_or_ip(request: Request) -> str:
    """
    Get rate limit key from user ID (if authenticated) or IP address.

    This allows per-user rate limiting for authenticated requests,
    falling back to IP-based limiting for unauthenticated requests.
    """
    if user_id := getattr(request.state, "user_id", None):
        return f"user:{user_id}"

    # Fall back to IP address
    return get_remote_address(request)


# Create limiter instance
limiter = Limiter(key_func=_get_user_id_or_ip)


# Rate limit configurations (can be overridden via environment)
RATE_LIMIT_ANALYZE = os.environ.get("RATE_LIMIT_ANALYZE", "10/minute")
RATE_LIMIT_SEARCH = os.environ.get("RATE_LIMIT_SEARCH", "30/minute")
RATE_LIMIT_SUGGEST = os.environ.get("RATE_LIMIT_SUGGEST", "20/minute")
RATE_LIMIT_PROFILE = os.environ.get("RATE_LIMIT_PROFILE", "10/minute")
RATE_LIMIT_CRUD = os.environ.get("RATE_LIMIT_CRUD", "60/minute")
RATE_LIMIT_DEFAULT = os.environ.get("RATE_LIMIT_DEFAULT", "100/minute")


def rate_limit_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.

    Returns a user-friendly JSON error response with retry information.
    """
    # Record the rate limit exceeded event for monitoring
    endpoint = request.url.path
    record_rate_limit_exceeded(endpoint)

    # Extract retry-after from the exception if available
    retry_after = getattr(exc, "retry_after", 60)

    # Use default detail if available
    detail = getattr(exc, "detail", "Rate limit exceeded")

    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": f"Rate limit exceeded. Try again in {retry_after} seconds.",
                "retry_after": retry_after,
            }
        },
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Limit": str(detail),
        },
    )


# Decorator shortcuts for common rate limits
def limit_analyze(func):
    """Apply analyze endpoint rate limit (AI-heavy, expensive)."""
    return limiter.limit(RATE_LIMIT_ANALYZE)(func)


def limit_search(func):
    """Apply search endpoint rate limit."""
    return limiter.limit(RATE_LIMIT_SEARCH)(func)


def limit_suggest(func):
    """Apply suggest endpoint rate limit."""
    return limiter.limit(RATE_LIMIT_SUGGEST)(func)


def limit_profile(func):
    """Apply profile endpoint rate limit."""
    return limiter.limit(RATE_LIMIT_PROFILE)(func)


def limit_crud(func):
    """Apply CRUD endpoint rate limit."""
    return limiter.limit(RATE_LIMIT_CRUD)(func)
