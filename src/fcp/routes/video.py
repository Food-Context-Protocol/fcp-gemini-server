"""Video Generation API routes.

Provides endpoints for AI-powered video generation using Veo 3.1
for food content, recipe videos, and cooking clips.
"""

import base64
import logging

from fastapi import Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from fcp.auth import AuthenticatedUser, require_write_access
from fcp.routes.router import APIRouter
from fcp.security import limiter
from fcp.tools.video import generate_cooking_clip, generate_recipe_video

logger = logging.getLogger(__name__)

router = APIRouter()


class RecipeVideoRequest(BaseModel):
    """Request body for recipe video generation."""

    dish_name: str = Field(..., description="Name of the dish", min_length=2, max_length=200)
    description: str | None = Field(None, description="Additional context or specific shots desired")
    style: str = Field(
        "cinematic",
        description="Video style: cinematic, tutorial, social, lifestyle",
    )
    duration_seconds: int = Field(8, description="Video length (4-8 seconds)", ge=4, le=8)
    aspect_ratio: str = Field("16:9", description="Aspect ratio: 16:9 (landscape) or 9:16 (portrait)")
    timeout_seconds: int = Field(300, description="Max wait time in seconds", ge=60, le=600)


class CookingClipRequest(BaseModel):
    """Request body for cooking clip generation."""

    action: str = Field(..., description="Cooking action (e.g., 'chopping vegetables')", min_length=3)
    ingredients: list[str] | None = Field(None, description="Optional list of ingredients being used")
    duration_seconds: int = Field(8, description="Video length (4-8 seconds)", ge=4, le=8)
    timeout_seconds: int = Field(300, description="Max wait time in seconds", ge=60, le=600)


class VideoResponse(BaseModel):
    """Response from video generation endpoint."""

    status: str = Field(..., description="Status: completed, timeout, or failed")
    video_base64: str | None = Field(None, description="Base64-encoded video data")
    duration: int | None = Field(None, description="Video duration in seconds")
    dish_name: str | None = Field(None, description="Dish name (for recipe videos)")
    action: str | None = Field(None, description="Cooking action (for clips)")
    style: str | None = Field(None, description="Video style used")
    operation_name: str | None = Field(None, description="Operation ID for status checks")
    message: str | None = Field(None, description="Error or status message")


@router.post(
    "/video/recipe",
    response_model=VideoResponse,
    summary="Generate recipe video",
    description="""
Generate a short AI video for a dish or recipe using Veo 3.1.

Creates appetizing video content for:
- Food presentations
- Recipe showcases
- Social media content

**Styles**:
- `cinematic`: Shallow depth of field, warm lighting
- `tutorial`: Overhead cooking view, step-by-step
- `social`: Trendy, quick cuts, vibrant colors
- `lifestyle`: Person enjoying meal, cozy atmosphere

**Note**: Video generation takes 2-5 minutes.
    """,
)
@limiter.limit("3/minute")
async def generate_recipe_video_endpoint(
    request: Request,
    body: RecipeVideoRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> VideoResponse:
    """Generate a recipe video using Veo 3.1."""
    logger.info("Recipe video request [user=%s]: %s", user.user_id, body.dish_name)

    try:
        result = await generate_recipe_video(
            dish_name=body.dish_name,
            description=body.description,
            style=body.style,
            duration_seconds=body.duration_seconds,
            aspect_ratio=body.aspect_ratio,
            timeout_seconds=body.timeout_seconds,
        )

        # Convert video bytes to base64 if present
        video_base64 = None
        if result.get("video_bytes"):
            video_base64 = base64.b64encode(result["video_bytes"]).decode("utf-8")

        return VideoResponse(
            status=result.get("status", "failed"),
            video_base64=video_base64,
            duration=result.get("duration"),
            dish_name=result.get("dish_name"),
            style=result.get("style"),
            operation_name=result.get("operation_name"),
            message=result.get("message"),
        )

    except RuntimeError as e:
        logger.error("Video generation failed - API not configured: %s", e)
        raise HTTPException(status_code=503, detail="Video service unavailable") from e
    except Exception as e:
        logger.exception("Video generation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Video generation failed: {e}") from e


@router.post(
    "/video/clip",
    response_model=VideoResponse,
    summary="Generate cooking clip",
    description="""
Generate a short B-roll style cooking action clip.

Creates clips of cooking actions like:
- Chopping vegetables
- Sautéing ingredients
- Flipping pancakes
- Plating dishes

**Note**: Video generation takes 2-5 minutes.
    """,
)
@limiter.limit("3/minute")
async def generate_cooking_clip_endpoint(
    request: Request,
    body: CookingClipRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> VideoResponse:
    """Generate a cooking action clip using Veo 3.1."""
    logger.info("Cooking clip request [user=%s]: %s", user.user_id, body.action)

    try:
        result = await generate_cooking_clip(
            action=body.action,
            ingredients=body.ingredients,
            duration_seconds=body.duration_seconds,
            timeout_seconds=body.timeout_seconds,
        )

        # Convert video bytes to base64 if present
        video_base64 = None
        if result.get("video_bytes"):
            video_base64 = base64.b64encode(result["video_bytes"]).decode("utf-8")

        return VideoResponse(
            status=result.get("status", "failed"),
            video_base64=video_base64,
            duration=result.get("duration"),
            action=result.get("action"),
            operation_name=result.get("operation_name"),
            message=result.get("message"),
        )

    except RuntimeError as e:
        logger.error("Clip generation failed - API not configured: %s", e)
        raise HTTPException(status_code=503, detail="Video service unavailable") from e
    except Exception as e:
        logger.exception("Clip generation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Clip generation failed: {e}") from e


@router.post(
    "/video/recipe/raw",
    summary="Generate recipe video (raw bytes)",
    description="Generate a recipe video and return raw MP4 bytes.",
    responses={
        200: {"content": {"video/mp4": {}}},
        503: {"description": "Service unavailable"},
    },
)
@limiter.limit("3/minute")
async def generate_recipe_video_raw(
    request: Request,
    body: RecipeVideoRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> Response:
    """Generate a recipe video and return raw MP4 bytes."""
    logger.info("Recipe video (raw) request [user=%s]: %s", user.user_id, body.dish_name)

    try:
        result = await generate_recipe_video(
            dish_name=body.dish_name,
            description=body.description,
            style=body.style,
            duration_seconds=body.duration_seconds,
            aspect_ratio=body.aspect_ratio,
            timeout_seconds=body.timeout_seconds,
        )

        if result.get("status") != "completed" or not result.get("video_bytes"):
            raise HTTPException(
                status_code=504,
                detail=result.get("message", "Video generation did not complete"),
            )

        return Response(
            content=result["video_bytes"],
            media_type="video/mp4",
            headers={"Content-Disposition": f'attachment; filename="{body.dish_name}.mp4"'},
        )

    except HTTPException:
        raise
    except RuntimeError as e:
        logger.error("Video generation failed - API not configured: %s", e)
        raise HTTPException(status_code=503, detail="Video service unavailable") from e
    except Exception as e:
        logger.exception("Video generation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Video generation failed: {e}") from e
