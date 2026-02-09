"""Prometheus metrics for FCP API.

Provides:
- Automatic HTTP metrics (latency, request count, errors)
- Custom metrics for Gemini API usage
- /metrics endpoint for Cloud Monitoring

Usage:
    from fcp.utils.metrics import setup_metrics
    setup_metrics(app)
"""

import logging

from fastapi import FastAPI
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# Custom metrics for Gemini API
GEMINI_REQUESTS = Counter(
    "gemini_api_requests_total",
    "Total Gemini API requests",
    ["method", "status"],
)

GEMINI_TOKENS = Counter(
    "gemini_api_tokens_total",
    "Total Gemini API tokens used",
    ["type"],  # input, output
)

GEMINI_LATENCY = Histogram(
    "gemini_api_latency_seconds",
    "Gemini API request latency",
    ["method"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

GEMINI_COST = Counter(
    "gemini_api_cost_usd_total",
    "Total Gemini API cost in USD",
)

# =============================================================================
# Business Metrics - Food Logging
# =============================================================================

MEALS_LOGGED = Counter(
    "fcp_meals_logged_total",
    "Total meals logged",
    ["meal_type", "cuisine"],  # breakfast/lunch/dinner/snack, cuisine type
)

MEALS_ANALYZED = Counter(
    "fcp_meals_analyzed_total",
    "Total meals analyzed with AI",
    ["analysis_type"],  # image, text, voice
)

ANALYSIS_DURATION = Histogram(
    "fcp_analysis_seconds",
    "Meal analysis latency",
    ["analysis_type"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

PANTRY_OPERATIONS = Counter(
    "fcp_pantry_operations_total",
    "Total pantry operations",
    ["operation"],  # add, remove, update, expire
)

RECIPES_GENERATED = Counter(
    "fcp_recipes_generated_total",
    "Total recipes generated or extracted",
    ["source"],  # pantry_suggestion, url_extraction, ai_generated
)

SAFETY_CHECKS = Counter(
    "fcp_safety_checks_total",
    "Total food safety checks performed",
    ["check_type", "result"],  # allergen/recall/interaction, safe/warning/danger
)

DISCOVERY_REQUESTS = Counter(
    "fcp_discovery_requests_total",
    "Total food discovery requests",
    ["discovery_type"],  # nearby, search, recommendation
)

USER_ACTIVE_SESSIONS = Counter(
    "fcp_user_sessions_total",
    "Total user sessions",
    ["auth_method"],  # firebase, anonymous
)


# =============================================================================
# MCP Tool Execution Metrics
# =============================================================================

TOOL_CALLS = Counter(
    "fcp_tool_calls_total",
    "Total MCP tool calls",
    ["tool_name", "status", "user_role"],
)

TOOL_LATENCY = Histogram(
    "fcp_tool_latency_seconds",
    "Tool execution latency in seconds",
    ["tool_name"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

# =============================================================================
# Security Event Metrics
# =============================================================================

SECURITY_EVENTS = Counter(
    "fcp_security_events_total",
    "Security events by type and outcome",
    ["event_type", "outcome"],
)


# =============================================================================
# Business Metric Recording Functions
# =============================================================================


def record_meal_logged(meal_type: str = "unknown", cuisine: str = "unknown") -> None:
    """Record a meal being logged.

    Args:
        meal_type: Type of meal (breakfast, lunch, dinner, snack)
        cuisine: Cuisine type (Japanese, Italian, etc.)
    """
    MEALS_LOGGED.labels(meal_type=meal_type, cuisine=cuisine).inc()


def record_meal_analyzed(analysis_type: str, duration_seconds: float) -> None:
    """Record a meal analysis.

    Args:
        analysis_type: Type of analysis (image, text, voice)
        duration_seconds: How long the analysis took
    """
    MEALS_ANALYZED.labels(analysis_type=analysis_type).inc()
    ANALYSIS_DURATION.labels(analysis_type=analysis_type).observe(duration_seconds)


def record_pantry_operation(operation: str) -> None:
    """Record a pantry operation.

    Args:
        operation: Type of operation (add, remove, update, expire)
    """
    PANTRY_OPERATIONS.labels(operation=operation).inc()


def record_recipe_generated(source: str) -> None:
    """Record a recipe generation.

    Args:
        source: Source of recipe (pantry_suggestion, url_extraction, ai_generated)
    """
    RECIPES_GENERATED.labels(source=source).inc()


def record_safety_check(check_type: str, result: str) -> None:
    """Record a food safety check.

    Args:
        check_type: Type of check (allergen, recall, interaction)
        result: Result of check (safe, warning, danger)
    """
    SAFETY_CHECKS.labels(check_type=check_type, result=result).inc()


def record_discovery_request(discovery_type: str) -> None:
    """Record a food discovery request.

    Args:
        discovery_type: Type of discovery (nearby, search, recommendation)
    """
    DISCOVERY_REQUESTS.labels(discovery_type=discovery_type).inc()


def record_user_session(auth_method: str) -> None:
    """Record a user session.

    Args:
        auth_method: Authentication method (firebase, anonymous)
    """
    USER_ACTIVE_SESSIONS.labels(auth_method=auth_method).inc()


# =============================================================================
# Security Event Recording Functions
# =============================================================================


def record_auth_failure(reason: str) -> None:
    """Record an authentication failure.

    Args:
        reason: Reason for failure (invalid_token, expired_token, revoked_token, etc.)
    """
    SECURITY_EVENTS.labels(event_type="auth_failure", outcome=reason).inc()


def record_permission_denied(resource: str) -> None:
    """Record a permission denial.

    Args:
        resource: The resource that was denied access (write_operation, etc.)
    """
    SECURITY_EVENTS.labels(event_type="permission_denied", outcome=resource).inc()


def record_rate_limit_exceeded(endpoint: str) -> None:
    """Record a rate limit exceeded event.

    Args:
        endpoint: The endpoint that hit the rate limit
    """
    SECURITY_EVENTS.labels(event_type="rate_limit", outcome=endpoint).inc()


# =============================================================================
# MCP Tool Execution Recording Functions
# =============================================================================


def record_tool_call(
    tool_name: str,
    status: str,
    user_role: str,
    duration_seconds: float,
) -> None:
    """Record an MCP tool call with status and timing.

    Args:
        tool_name: Name of the MCP tool (e.g., "get_recent_meals")
        status: "success" or "error"
        user_role: "demo" or "authenticated"
        duration_seconds: How long the tool execution took
    """
    TOOL_CALLS.labels(
        tool_name=tool_name,
        status=status,
        user_role=user_role,
    ).inc()
    TOOL_LATENCY.labels(tool_name=tool_name).observe(duration_seconds)


def record_gemini_usage(
    method: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    latency_seconds: float,
    success: bool = True,
) -> None:
    """Record Gemini API usage metrics.

    Call this from services/gemini.py after each API call.

    Args:
        method: Gemini method name (e.g., "generate_json")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cost_usd: Cost in USD
        latency_seconds: Request latency
        success: Whether the request succeeded
    """
    status = "success" if success else "error"
    GEMINI_REQUESTS.labels(method=method, status=status).inc()
    GEMINI_TOKENS.labels(type="input").inc(input_tokens)
    GEMINI_TOKENS.labels(type="output").inc(output_tokens)
    GEMINI_LATENCY.labels(method=method).observe(latency_seconds)
    GEMINI_COST.inc(cost_usd)


def setup_metrics(app: FastAPI) -> None:
    """Metrics setup (no-op - Prometheus instrumentator removed)."""
    pass
