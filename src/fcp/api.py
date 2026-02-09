"""Food Context Protocol HTTP API.

FastAPI application for Flutter app and CLI access to FCP functionality.
This provides the same tools as the MCP server, but over HTTP.

Architecture:
- All routes are organized in modular files under routes/
- This file handles app configuration, middleware, and lifecycle management
- See routes/__init__.py for the full list of available routers

Features:
- Streaming endpoints for real-time AI feedback
- JSON mode for guaranteed structured output
- Multimodal image analysis

Security:
- Firebase ID token authentication
- Rate limiting on all endpoints
- CORS configuration
- Input validation and sanitization
"""

import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi.errors import RateLimitExceeded

from fcp.mcp.initialize import initialize_tools
from fcp.mcp.registry import tool_registry
from fcp.routes import (
    agents_router,
    analytics_router,
    analyze_router,
    connectors_router,
    discovery_router,
    external_router,
    health_router,
    inventory_router,
    knowledge_router,
    meals_router,
    misc_router,
    parser_router,
    profile_router,
    publishing_router,
    recipes_router,
    research_router,
    safety_router,
    scheduler_router,
    search_router,
    social_router,
    video_router,
    voice_router,
)
from fcp.security import (
    limiter,
    rate_limit_exceeded_handler,
)
from fcp.services.logfire_service import init_logfire, shutdown_logfire
from fcp.utils.audit import setup_audit_logging
from fcp.utils.background_tasks import cancel_all_tasks
from fcp.utils.errors import register_exception_handlers
from fcp.utils.logging import request_id_ctx, setup_logging

# Initialize tools (must run after imports to register all @tool decorators)
initialize_tools()


def _load_openapi_description() -> str:
    """Load OpenAPI description from external markdown file."""
    docs_path = Path(__file__).parent / "docs" / "openapi_description.md"
    try:
        return docs_path.read_text()
    except FileNotFoundError:
        return "Food Context Protocol HTTP API."


# Configure logging to show INFO level messages with request ID support
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)
setup_logging()  # Add request ID filter to root logger
logger = logging.getLogger(__name__)

# --- App Configuration ---


def _is_scheduler_available() -> bool:
    """Check if the scheduler module is installed."""
    try:
        import fcp.scheduler  # noqa: F401

        return True
    except ImportError:
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle app startup and shutdown events.
    """
    # Startup
    init_logfire()  # Initialize Logfire for enhanced observability
    setup_audit_logging()  # Initialize audit logging (logs to stderr by default)

    if _is_scheduler_available():
        from fcp.scheduler.jobs import initialize_all_schedules

        initialize_all_schedules()

    yield

    # Shutdown
    if _is_scheduler_available():
        from fcp.scheduler import stop_scheduler

        stop_scheduler()

    # Cancel any running background tasks
    await cancel_all_tasks()

    # Close shared HTTP client (connection pooling cleanup)
    try:
        from fcp.services.gemini import GeminiClient

        await GeminiClient.close_http_client()
    except Exception as e:
        logger.warning("Failed to close Gemini HTTP client during shutdown: %s", e)

    shutdown_logfire()  # Flush any pending Logfire data


app = FastAPI(
    title="Food Context Protocol API",
    description=_load_openapi_description(),
    version="1.1.0",
    openapi_tags=[
        {
            "name": "meals",
            "description": "Food log CRUD operations",
        },
        {
            "name": "analyze",
            "description": "AI-powered meal image analysis",
        },
        {
            "name": "search",
            "description": "Semantic search across food history",
        },
        {
            "name": "profile",
            "description": "User taste profile and preferences",
        },
        {
            "name": "safety",
            "description": "Food safety, allergens, and recalls",
        },
        {
            "name": "inventory",
            "description": "Pantry and ingredient management",
        },
        {
            "name": "recipes",
            "description": "Recipe extraction and management",
        },
        {
            "name": "discovery",
            "description": "Location-based food discovery",
        },
        {
            "name": "agents",
            "description": "Autonomous AI agents",
        },
        {
            "name": "health",
            "description": "Health check endpoints for monitoring",
        },
        {
            "name": "analytics",
            "description": "Usage analytics and insights",
        },
        {
            "name": "publishing",
            "description": "Recipe and content publishing",
        },
        {
            "name": "knowledge",
            "description": "Food knowledge graph queries",
        },
        {
            "name": "social",
            "description": "Social features and sharing",
        },
        {
            "name": "connectors",
            "description": "Third-party service integrations",
        },
        {
            "name": "external",
            "description": "External data source queries",
        },
        {
            "name": "scheduler",
            "description": "Scheduled task management",
        },
        {
            "name": "parser",
            "description": "Content parsing utilities",
        },
        {
            "name": "misc",
            "description": "Miscellaneous utility endpoints",
        },
        {
            "name": "research",
            "description": "Deep research reports using AI",
        },
        {
            "name": "video",
            "description": "AI video generation with Veo 3.1",
        },
        {
            "name": "voice",
            "description": "Real-time voice processing with Live API",
        },
    ],
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# --- Security Headers Middleware ---
def _is_production() -> bool:
    """Check if running in production environment."""
    env = os.environ.get("ENVIRONMENT", "").lower()
    return env in {"production", "prod"} or os.environ.get("K_SERVICE") is not None


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses.

    Headers added:
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking
    - Referrer-Policy: Controls referrer information
    - Strict-Transport-Security: Forces HTTPS (production only)
    - Content-Security-Policy: Restricts resource loading (API responses)

    Note: X-XSS-Protection is intentionally NOT included as it is deprecated
    and can introduce vulnerabilities in modern browsers. CSP provides better protection.
    """
    response = await call_next(request)

    # Always add these headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # CSP: Permissive for docs UI, restrictive for API
    docs_paths = {"/docs", "/redoc", "/openapi.json"}
    if request.url.path in docs_paths:
        # Allow Swagger/ReDoc UI resources
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "frame-ancestors 'none'"
        )
    else:
        # API-specific CSP (restrictive since we only return JSON)
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

    # HSTS only in production (requires HTTPS)
    if _is_production():
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


# --- Request ID Middleware ---
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Add unique request ID for tracing and security auditing.

    - Accepts X-Request-ID from client (for distributed tracing)
    - Generates UUID if not provided
    - Sets in context var for logging
    - Returns in response header
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    # Set context var for logging
    token = request_id_ctx.set(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_ctx.reset(token)


# --- User ID Middleware for Rate Limiting ---
@app.middleware("http")
async def user_id_middleware(request: Request, call_next):
    """Extract user ID from Authorization header for rate limiting.

    This middleware sets request.state.user_id so that rate limiting
    can be per-user instead of per-IP for authenticated requests.
    """
    request.state.user_id = None  # Default to None (will use IP-based limiting)

    if auth_header := request.headers.get("Authorization"):
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            request.state.user_id = parts[1]
    return await call_next(request)


# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Register standardized error handlers
register_exception_handlers(app)

# CORS configuration
# Note: allow_credentials=True requires explicit origins (not "*")
# See: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS/Errors/CORSNotSupportingCredentials
#
# SECURITY: Production origins are restricted to known domains only.
# Localhost origins are ONLY added in development mode.
_PRODUCTION_CORS_ORIGINS = [
    "https://fcp.dev",
    "https://app.fcp.dev",
    "https://www.fcp.dev",
    "https://api.fcp.dev",
]

_DEVELOPMENT_CORS_ORIGINS = [
    "http://localhost:8080",
    "http://localhost:3000",
    "http://localhost:5000",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:3000",
]

# Start with production origins, add dev origins only in development
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "").split(",") if os.environ.get("CORS_ORIGINS") else []
CORS_ORIGINS.extend(_PRODUCTION_CORS_ORIGINS)

if not _is_production():
    # Development mode: add localhost origins
    CORS_ORIGINS.extend(_DEVELOPMENT_CORS_ORIGINS)
    if dev_origins := os.environ.get("DEV_CORS_ORIGINS", ""):
        CORS_ORIGINS.extend(dev_origins.split(","))

# Remove empty strings and duplicates
CORS_ORIGINS = list(filter(None, set(CORS_ORIGINS)))

# Never allow wildcard with credentials
if "*" in CORS_ORIGINS:
    CORS_ORIGINS.remove("*")
    logger.warning("Removed wildcard '*' from CORS origins (incompatible with credentials)")

app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=86400,  # Cache preflight for 24 hours
)

# Response compression for large payloads (> 1KB)
app.add_middleware(GZipMiddleware, minimum_size=1000)  # type: ignore[arg-type]

# Include route modules
# Routes are extracted to routes/ for better organization
app.include_router(meals_router, prefix="", tags=["meals"])
app.include_router(search_router, prefix="", tags=["search"])
app.include_router(safety_router, prefix="/safety", tags=["safety"])
app.include_router(profile_router, prefix="", tags=["profile"])
app.include_router(publishing_router, prefix="", tags=["publishing"])
app.include_router(analyze_router, prefix="", tags=["analyze"])
app.include_router(analytics_router, prefix="", tags=["analytics"])
app.include_router(agents_router, prefix="", tags=["agents"])
app.include_router(inventory_router, prefix="", tags=["inventory"])
app.include_router(knowledge_router, prefix="", tags=["knowledge"])
app.include_router(discovery_router, prefix="", tags=["discovery"])
app.include_router(recipes_router, prefix="", tags=["recipes"])
app.include_router(social_router, prefix="", tags=["social"])
app.include_router(connectors_router, prefix="", tags=["connectors"])
app.include_router(external_router, prefix="", tags=["external"])
app.include_router(scheduler_router, prefix="", tags=["scheduler"])
app.include_router(parser_router, prefix="", tags=["parser"])
app.include_router(misc_router, prefix="", tags=["misc"])
app.include_router(research_router, prefix="", tags=["research"])
app.include_router(video_router, prefix="", tags=["video"])
app.include_router(voice_router, prefix="", tags=["voice"])
app.include_router(health_router)  # No prefix - routes already have /health prefix


# --- Routes ---


@app.get("/mcp/v1/tools/list")
async def list_mcp_tools():
    """List all available MCP tools."""
    return {"tools": tool_registry.get_mcp_tool_list()}


@app.get("/")
async def root():
    """Health check."""
    return {"status": "ok", "service": "FoodLog FCP API", "version": "1.1.0"}


# All other routes have been extracted to modular route files in routes/
# See routes/__init__.py for the full list of available routers.
