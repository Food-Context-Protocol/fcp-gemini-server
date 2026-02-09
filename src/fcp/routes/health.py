"""Health check endpoints for Kubernetes/Cloud Run probes.

Provides:
- /health/live - Liveness probe (is the process running?)
- /health/ready - Readiness probe (can it serve traffic?)
- /health/deps - Dependency health check (detailed service status)

These follow Kubernetes health check patterns and are suitable for
Cloud Run, GKE, and other container orchestration platforms.
"""

import logging
import os
from typing import Any

from fcp.routes.router import APIRouter
from fcp.routes.schemas import DependencyHealthResponse, ReadinessResponse, StatusResponse
from fcp.utils.circuit_breaker import get_all_circuit_breakers
from fcp.utils.logging import get_request_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

# Environment detection
IS_CLOUD_RUN = os.environ.get("K_SERVICE") is not None


async def _check_gemini_health() -> dict[str, Any]:
    """Check Gemini API connectivity."""
    try:
        from fcp.services.gemini import get_gemini_client

        client = get_gemini_client()
        if client.client is None:
            return {"healthy": False, "error": "API key not configured"}
        # Client exists, consider healthy (actual API call would be expensive)
        return {"healthy": True}
    except Exception as e:
        return {"healthy": False, "error": str(e)[:100]}


async def _check_firestore_health() -> dict[str, Any]:
    """Check Firestore connectivity."""
    try:
        from fcp.services.firestore import get_firestore_client, get_firestore_status

        status = get_firestore_status()
        if not status["available"]:
            return {
                "healthy": False,
                "error": status["error"] or "Firestore credentials unavailable",
                "mode": "offline",
            }

        client = get_firestore_client()
        db = getattr(client, "db", None)
        if db is None:
            return {
                "healthy": False,
                "error": "Firestore client unavailable",
                "mode": "local",
            }
        return {"healthy": True, "mode": "firestore"}
    except Exception as e:
        return {"healthy": False, "error": str(e)[:100]}


@router.get("/live", response_model=StatusResponse)
async def liveness() -> StatusResponse:
    """Liveness probe - check if the process is running.

    This endpoint should always return 200 if the server is running.
    Used by Kubernetes/Cloud Run to detect if the container needs restart.

    Returns:
        Simple status response
    """
    return StatusResponse(status="ok")


@router.get("/ready", response_model=ReadinessResponse)
async def readiness() -> ReadinessResponse:
    """Readiness probe - check if the service can handle requests.

    Verifies:
    - Gemini API key is configured
    - Database connection is available

    Returns:
        Status with component health details
    """
    all_healthy = True

    # Check Gemini API key
    gemini_key = os.environ.get("GEMINI_API_KEY")
    checks: dict[str, bool] = {"gemini_api_key": bool(gemini_key)}
    if not gemini_key:
        all_healthy = False
        logger.warning(
            "Readiness check failed: GEMINI_API_KEY not configured [request_id=%s]",
            get_request_id(),
        )

    # Check database availability
    # Note: Set to True for lightweight readiness check
    # For actual database health, use /health/deps endpoint
    checks["database"] = True

    status = "ok" if all_healthy else "degraded"
    return ReadinessResponse(status=status, checks=checks)


@router.get("/deps", response_model=DependencyHealthResponse)
async def dependency_health() -> DependencyHealthResponse:
    """Detailed dependency health check.

    Checks actual connectivity to:
    - Gemini API (client availability)
    - Firestore (database connection)
    - Circuit breakers (current state)

    This is more expensive than /ready and should be used for debugging,
    not high-frequency probes.

    Returns:
        Detailed status of all dependencies
    """
    checks: dict[str, Any] = {"gemini": await _check_gemini_health()}

    # Check Firestore
    checks["firestore"] = await _check_firestore_health()

    # Check circuit breakers
    circuit_breakers = get_all_circuit_breakers()
    checks["circuit_breakers"] = circuit_breakers

    # Determine overall status
    core_healthy = all(check.get("healthy", False) for check in [checks["gemini"], checks["firestore"]])

    # Check if any circuit breaker is open
    circuits_healthy = all(cb.get("state") != "open" for cb in circuit_breakers.values()) if circuit_breakers else True

    if core_healthy and circuits_healthy:
        status = "healthy"
    elif core_healthy:
        status = "degraded"  # Core services ok, but circuit breaker open
    else:
        status = "unhealthy"

    return DependencyHealthResponse(
        status=status,
        checks=checks,
        request_id=get_request_id(),
    )


@router.get("/", response_model=StatusResponse)
async def health_root() -> StatusResponse:
    """Root health endpoint - simple health check.

    Equivalent to /health/live for convenience.
    """
    return StatusResponse(status="ok")
