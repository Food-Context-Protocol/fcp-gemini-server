"""Publishing Routes.

Content generation and publishing endpoints:
- POST /publish/generate - Generate content from food logs
- GET /publish/drafts - List all drafts
- GET /publish/drafts/{draft_id} - Get specific draft
- PATCH /publish/drafts/{draft_id} - Update draft
- DELETE /publish/drafts/{draft_id} - Delete draft
- POST /publish/drafts/{draft_id}/publish - Publish a draft
- GET /publish/published - List published content
- GET /publish/analytics/{content_id} - Get analytics for published content
"""

from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, Field

from fcp.agents import ContentGeneratorAgent
from fcp.auth import AuthenticatedUser, get_current_user, require_write_access
from fcp.routes.router import APIRouter
from fcp.routes.schemas import (
    ActionResponse,
    AnalyticsResponse,
    DraftCreationResponse,
    DraftDetailResponse,
    DraftListResponse,
    PublishActionResponse,
    PublishedListResponse,
)
from fcp.security.rate_limit import RATE_LIMIT_PROFILE, limiter
from fcp.services.firestore import get_firestore_client
from fcp.tools import get_astro_bridge, get_meals, get_meals_by_ids

router = APIRouter()


# --- Request Models ---


class GenerateContentRequest(BaseModel):
    """Request model for content generation."""

    content_type: Literal["blog_post", "social_twitter", "social_instagram", "weekly_digest"]
    log_ids: list[str] | None = Field(default=None, description="Specific log IDs to use for generation")
    theme: str = Field(
        default="culinary_journey",
        pattern=r"^(culinary_journey|nutrition_focus|cultural_exploration)$",
    )
    style: str = Field(default="conversational", pattern=r"^(conversational|professional|casual)$")


class UpdateDraftRequest(BaseModel):
    """Request model for updating a draft."""

    content: dict[str, Any] | None = None
    status: Literal["draft", "archived", "partial"] | None = None


class PublishRequest(BaseModel):
    """Request model for publishing a draft."""

    platforms: list[Literal["blog"]] = Field(default=["blog"])
    publish_immediately: bool = Field(default=True)


# --- Routes ---


@router.post("/publish/generate", response_model=DraftCreationResponse)
@limiter.limit(RATE_LIMIT_PROFILE)
async def generate_content(
    request: Request,
    generate_request: GenerateContentRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> DraftCreationResponse:
    """
    Generate content from food logs.

    Supports:
    - blog_post: SEO-optimized blog post
    - social_twitter: Twitter-optimized post
    - social_instagram: Instagram-optimized post
    - weekly_digest: Weekly food journey summary
    """
    db = get_firestore_client()
    agent = ContentGeneratorAgent(user.user_id)

    # Get logs - either specific IDs or default to last 7 days
    if generate_request.log_ids:
        # Batch fetch logs for efficiency (avoids N+1 queries)
        logs = await get_meals_by_ids(user.user_id, generate_request.log_ids)
        if not logs:
            raise HTTPException(status_code=404, detail="No logs found with provided IDs")
    else:
        logs = await get_meals(user.user_id, days=7)
        if not logs:
            raise HTTPException(status_code=404, detail="No food logs found in the last 7 days")

    # Generate content based on type
    if generate_request.content_type == "blog_post":
        result = await agent.generate_blog_post(
            food_logs=logs,
            theme=generate_request.theme,
            style=generate_request.style,
        )
    elif generate_request.content_type == "weekly_digest":
        result = await agent.generate_weekly_digest(food_logs=logs)
    else:  # social_twitter, social_instagram (exhaustive via Literal type)
        platform = generate_request.content_type.replace("social_", "")
        result = await agent.generate_social_post(
            food_log=logs[0],
            platform=platform,
        )

    # Save as draft
    draft_id = await db.save_draft(
        user.user_id,
        {
            "content_type": generate_request.content_type,
            "content": result,
            "status": "draft",
            "source_log_ids": generate_request.log_ids or [log.get("id") for log in logs],
        },
    )

    payload = {
        "draft_id": draft_id,
        "content_type": generate_request.content_type,
        **result,
    }
    return DraftCreationResponse(**payload)


@router.get("/publish/drafts", response_model=DraftListResponse)
async def list_drafts(
    user: AuthenticatedUser = Depends(get_current_user),
) -> DraftListResponse:
    """List all content drafts."""
    db = get_firestore_client()
    drafts = await db.get_drafts(user.user_id)
    return DraftListResponse(drafts=drafts, count=len(drafts))


@router.get("/publish/drafts/{draft_id}", response_model=DraftDetailResponse)
async def get_draft(
    draft_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> DraftDetailResponse:
    """Get a specific draft."""
    db = get_firestore_client()
    draft = await db.get_draft(user.user_id, draft_id)

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    response_data = {"draft_id": draft_id, **draft}
    return DraftDetailResponse(**response_data)


@router.patch("/publish/drafts/{draft_id}", response_model=ActionResponse)
async def update_draft(
    draft_id: str,
    update_request: UpdateDraftRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> ActionResponse:
    """Update a draft's content or status."""
    db = get_firestore_client()

    # Verify draft exists
    existing = await db.get_draft(user.user_id, draft_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Draft not found")

    # Build updates
    updates: dict[str, Any] = {}
    if update_request.content is not None:
        updates["content"] = update_request.content
    if update_request.status is not None:
        updates["status"] = update_request.status

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    await db.update_draft(user.user_id, draft_id, updates)
    return ActionResponse(success=True, draft_id=draft_id)


@router.delete("/publish/drafts/{draft_id}", response_model=ActionResponse)
async def delete_draft(
    draft_id: str,
    user: AuthenticatedUser = Depends(require_write_access),
) -> ActionResponse:
    """Delete a draft."""
    db = get_firestore_client()
    deleted = await db.delete_draft(user.user_id, draft_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Draft not found")

    return ActionResponse(success=True, draft_id=draft_id)


@router.post("/publish/drafts/{draft_id}/publish", response_model=PublishActionResponse)
@limiter.limit(RATE_LIMIT_PROFILE)
async def publish_draft(
    request: Request,
    draft_id: str,
    publish_request: PublishRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> PublishActionResponse:
    """
    Publish a draft to configured platforms.

    Currently supports:
    - blog: Publish to Astro CMS (requires ASTRO_API_KEY and ASTRO_ENDPOINT)
    """
    db = get_firestore_client()
    draft = await db.get_draft(user.user_id, draft_id)

    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.get("status") == "published":
        raise HTTPException(status_code=400, detail="Draft is already published")

    results: dict[str, Any] = {}
    external_urls: dict[str, str] = {}
    external_ids: dict[str, str] = {}

    # Publish to each requested platform
    if "blog" in publish_request.platforms:
        astro = get_astro_bridge()
        result = await astro.publish_post(
            draft.get("content", {}),
            user.user_id,
            publish_immediately=publish_request.publish_immediately,
        )
        results["blog"] = result
        if result.get("success"):
            if result.get("url"):
                external_urls["blog"] = result["url"]
            if result.get("post_id"):
                external_ids["astro_post_id"] = result["post_id"]

    # Check if at least one platform succeeded
    any_success = any(r.get("success") for r in results.values())

    if not any_success:
        # All platforms failed - return failure without marking as published
        return PublishActionResponse(
            success=False,
            draft_id=draft_id,
            error="All publishing platforms failed",
            results=results,
        )

    # Determine status based on results
    all_success = all(r.get("success") for r in results.values())
    status = "published" if all_success else "partial"

    # Update draft status
    await db.update_draft(
        user.user_id,
        draft_id,
        {
            "status": status,
            "published_at": datetime.now(UTC).isoformat(),
            "publish_results": results,
        },
    )

    # Save to published content collection
    published_id = await db.save_published_content(
        user.user_id,
        {
            "draft_id": draft_id,
            "content_type": draft.get("content_type"),
            "content": draft.get("content"),
            "platforms": publish_request.platforms,
            "external_urls": external_urls,
            "external_ids": external_ids,
            "publish_results": results,
        },
    )

    return PublishActionResponse(
        success=True,
        draft_id=draft_id,
        published_id=published_id,
        results=results,
        external_urls=external_urls,
    )


@router.get("/publish/published", response_model=PublishedListResponse)
async def list_published(
    user: AuthenticatedUser = Depends(get_current_user),
) -> PublishedListResponse:
    """List all published content."""
    db = get_firestore_client()
    published = await db.get_published_content(user.user_id)
    return PublishedListResponse(published=published, count=len(published))


@router.get("/publish/analytics/{content_id}", response_model=AnalyticsResponse)
async def get_analytics(
    content_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> AnalyticsResponse:
    """
    Get analytics for published content.

    Fetches analytics from Astro CMS if configured.
    """
    db = get_firestore_client()

    # Verify content exists and belongs to user
    content = await db.get_published_content_item(user.user_id, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Published content not found")

    # Get the Astro post ID from stored external_ids
    external_ids = content.get("external_ids", {})
    astro_post_id = external_ids.get("astro_post_id")

    if not astro_post_id:
        return AnalyticsResponse(success=False, error="No Astro post ID found for this content", analytics=None)

    # Get analytics from Astro using the correct post ID
    astro = get_astro_bridge()
    result = await astro.get_analytics(astro_post_id)

    if result.get("success"):
        # Update stored analytics
        await db.update_published_content(user.user_id, content_id, {"analytics": result.get("analytics")})

    return AnalyticsResponse(**result)
