"""Standardized error handling for the FCP API.

Provides:
- APIErrorCodes: Enumeration of all error codes
- APIError: Pydantic model for error responses
- Exception handlers for FastAPI

All API errors follow a consistent schema:
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable message",
        "details": {...},  # Optional additional context
        "request_id": "uuid"  # For tracing
    }
}
"""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class APIErrorCodes:
    """Centralized error codes for the API."""

    # Client errors (4xx)
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"

    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # Domain-specific errors
    GEMINI_ERROR = "GEMINI_ERROR"
    FIREBASE_ERROR = "FIREBASE_ERROR"
    IMAGE_ERROR = "IMAGE_ERROR"

    # Status code to error code mapping
    _STATUS_MAP = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }

    @classmethod
    def from_status(cls, status_code: int) -> str:
        """Map HTTP status code to error code."""
        return cls._STATUS_MAP.get(status_code, cls.INTERNAL_ERROR)


class APIErrorDetail(BaseModel):
    """Standardized error response detail."""

    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


class APIErrorResponse(BaseModel):
    """Standardized error response wrapper."""

    error: APIErrorDetail


def _get_request_id(request: Request) -> str | None:
    """Extract request ID from request state."""
    return getattr(request.state, "request_id", None)


def _format_field_path(loc: tuple[str | int, ...]) -> str:
    """Format validation error field path for human readability.

    Converts Pydantic's location tuple into a readable field path:
    - ("body", "items", 0, "name") -> "body.items[0].name"
    - ("query", "page") -> "query.page"

    Args:
        loc: Pydantic error location tuple

    Returns:
        Human-readable field path string
    """
    parts = []
    for item in loc:
        if isinstance(item, int):
            # Array index - use bracket notation
            parts.append(f"[{item}]")
        elif parts:
            # Not first item - add dot separator
            parts.append(f".{item}")
        else:
            # First item - no separator
            parts.append(str(item))
    return "".join(parts)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPException with standardized format."""
    request_id = _get_request_id(request)

    error_response = APIErrorResponse(
        error=APIErrorDetail(
            code=APIErrorCodes.from_status(exc.status_code),
            message=str(exc.detail),
            request_id=request_id,
        )
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors with standardized format."""
    request_id = _get_request_id(request)

    # Extract validation error details with improved field path formatting
    errors = exc.errors()
    details = {
        "validation_errors": [
            {
                "field": _format_field_path(err["loc"]),
                "message": err["msg"],
                "type": err["type"],
            }
            for err in errors
        ]
    }

    error_response = APIErrorResponse(
        error=APIErrorDetail(
            code=APIErrorCodes.VALIDATION_ERROR,
            message="Request validation failed",
            details=details,
            request_id=request_id,
        )
    )

    return JSONResponse(
        status_code=422,
        content=error_response.model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with standardized format.

    SECURITY: Never expose internal error details to clients.
    Log the full exception for debugging, return generic message.
    """
    request_id = _get_request_id(request)

    # Log the full exception with request ID for debugging
    logger.exception(
        "Unhandled exception [request_id=%s]: %s",
        request_id,
        str(exc),
    )

    error_response = APIErrorResponse(
        error=APIErrorDetail(
            code=APIErrorCodes.INTERNAL_ERROR,
            message="An unexpected error occurred",
            request_id=request_id,
        )
    )

    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(),
    )


def tool_error(e: Exception, context: str = "operation") -> dict[str, Any]:
    """Return a safe error dict for MCP tool responses.

    Logs the full exception server-side but returns only a generic
    message to the client, preventing internal details from leaking.
    """
    logger.exception("Tool error during %s", context)
    return {"error": f"An error occurred during {context}. Please try again."}


def register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers with FastAPI app.

    Call this in api.py after creating the app:
        from fcp.utils.errors import register_exception_handlers
        register_exception_handlers(app)

    Registers handlers for:
    - HTTPException: Standardized HTTP error responses
    - RequestValidationError: Pydantic validation errors with field paths
    - Exception: Catch-all for uncaught exceptions (prevents stack trace leaks)
    """
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)  # type: ignore[arg-type]
