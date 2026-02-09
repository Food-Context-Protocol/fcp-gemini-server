"""Deep Research API routes.

Provides endpoints for AI-powered deep research on food topics
using Gemini's Interactions API.
"""

import logging

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, Field

from fcp.auth import AuthenticatedUser, require_write_access
from fcp.routes.router import APIRouter
from fcp.security import limiter
from fcp.tools.research import generate_research_report

logger = logging.getLogger(__name__)

router = APIRouter()


class ResearchRequest(BaseModel):
    """Request body for research endpoint."""

    topic: str = Field(..., description="Research topic", min_length=3, max_length=500)
    context: str | None = Field(None, description="Optional user context (dietary restrictions, goals)")
    timeout_seconds: int = Field(300, description="Max wait time in seconds", ge=60, le=600)


class ResearchResponse(BaseModel):
    """Response from research endpoint."""

    status: str = Field(..., description="Status: completed, failed, or timeout")
    report: str | None = Field(None, description="The research report (if completed)")
    topic: str = Field(..., description="Original research topic")
    interaction_id: str | None = Field(None, description="ID for follow-up queries")
    message: str | None = Field(None, description="Error or status message")


@router.post(
    "/research",
    response_model=ResearchResponse,
    summary="Generate deep research report",
    description="""
Generate a comprehensive research report on a food-related topic.

Uses the Deep Research Agent which autonomously:
- Plans research approach
- Executes multiple search queries
- Synthesizes findings into a report

**Note**: This is a long-running operation (typically 3-5+ minutes).

**Examples**:
- "Mediterranean diet health benefits"
- "Best cooking methods for nutrient retention"
- "Food trends in plant-based proteins"
    """,
)
@limiter.limit("5/minute")
async def research(
    request: Request,
    body: ResearchRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> ResearchResponse:
    """Generate a deep research report on a food topic."""
    logger.info("Research request [user=%s]: %s", user.user_id, body.topic[:50])

    try:
        result = await generate_research_report(
            topic=body.topic,
            context=body.context,
            timeout_seconds=body.timeout_seconds,
        )

        return ResearchResponse(
            status=result.get("status", "failed"),
            report=result.get("report"),
            topic=result.get("topic", body.topic),
            interaction_id=result.get("interaction_id"),
            message=result.get("message"),
        )

    except RuntimeError as e:
        # GEMINI_API_KEY not configured
        logger.error("Research failed - API not configured: %s", e)
        raise HTTPException(status_code=503, detail="Research service unavailable") from e
    except Exception as e:
        logger.exception("Research failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Research failed: {e}") from e
