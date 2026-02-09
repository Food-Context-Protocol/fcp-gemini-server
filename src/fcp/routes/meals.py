"""Meals Routes.

CRUD endpoints for food log entries:
- List meals
- Get single meal
- Create meal
- Create meal with image upload
- Update meal
- Delete meal
"""

import logging
from typing import Any

from fastapi import Depends, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field, field_validator

from fcp.auth import AuthenticatedUser, get_current_user, require_write_access
from fcp.routes.router import APIRouter
from fcp.routes.schemas import ActionResponse, MealDetailResponse, MealListResponse
from fcp.security.input_sanitizer import sanitize_user_input
from fcp.security.rate_limit import RATE_LIMIT_CRUD, limiter
from fcp.services.storage import get_storage_client, is_storage_configured
from fcp.tools import add_meal, delete_meal, get_meal, get_meals, update_meal
from fcp.tools.analyze import analyze_meal, analyze_meal_from_bytes

# Constants for image upload validation
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB

# Magic byte signatures for image file validation
IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": "image/jpeg",  # JPEG
    b"\x89PNG\r\n\x1a\n": "image/png",  # PNG
    b"RIFF": "image/webp",  # WebP (followed by WEBP at offset 8)
    b"\x00\x00\x00\x18ftypheic": "image/heic",  # HEIC (ftyp heic)
    b"\x00\x00\x00\x1cftypheic": "image/heic",  # HEIC variant
    b"\x00\x00\x00\x18ftypheif": "image/heif",  # HEIF
    b"\x00\x00\x00\x1cftypheif": "image/heif",  # HEIF variant
}

logger = logging.getLogger(__name__)

router = APIRouter()


def _validate_image_magic_bytes(data: bytes) -> bool:
    """Validate image file by checking magic bytes (file signature).

    Args:
        data: The file bytes to validate

    Returns:
        True if the file appears to be a valid image based on magic bytes
    """
    if len(data) < 12:
        return False

    return next(
        (
            (data[8:12] == b"WEBP" if signature == b"RIFF" and len(data) >= 12 else True)
            for signature in IMAGE_SIGNATURES
            if data.startswith(signature)
        ),
        False,
    )


def _sanitize_optional_text(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    return sanitize_user_input(value, max_length=max_length)


async def _read_and_validate_image(image: UploadFile) -> tuple[bytes, str]:
    content_type = image.content_type or "application/octet-stream"
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image type: {content_type}. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )

    image_data = await image.read()
    if len(image_data) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large. Maximum size: {MAX_IMAGE_SIZE // (1024 * 1024)} MB",
        )

    if len(image_data) == 0:
        raise HTTPException(status_code=400, detail="Empty image file")

    if not _validate_image_magic_bytes(image_data):
        raise HTTPException(
            status_code=400,
            detail="Invalid image file. File content does not match expected image format.",
        )

    return image_data, content_type


async def _analyze_with_storage(
    *,
    user_id: str,
    image: UploadFile,
    image_data: bytes,
    content_type: str,
    dish_name: str | None,
    auto_analyze: bool,
) -> tuple[dict[str, Any] | None, str | None, str | None, str | None]:
    storage_client = get_storage_client()
    try:
        image_path = storage_client.upload_blob(
            data=image_data,
            content_type=content_type,
            user_id=user_id,
            filename=image.filename,
        )
    finally:
        del image_data

    image_url = storage_client.get_public_url(image_path)
    analysis = None
    if auto_analyze:
        try:
            analysis = await analyze_meal(image_url)
            if not dish_name and analysis.get("dish_name"):
                dish_name = analysis["dish_name"]
        except Exception as e:
            logger.warning("Failed to analyze meal image: %s", str(e))

    return analysis, dish_name, image_path, image_url


async def _analyze_without_storage(
    *,
    image_data: bytes,
    content_type: str,
    dish_name: str | None,
    auto_analyze: bool,
) -> tuple[dict[str, Any] | None, str | None]:
    analysis = None
    if auto_analyze:
        try:
            analysis = await analyze_meal_from_bytes(image_data, content_type)
            if not dish_name and analysis.get("dish_name"):
                dish_name = analysis["dish_name"]
        except Exception as e:
            logger.warning("Failed to analyze meal image from bytes: %s", str(e))
        finally:
            del image_data
    else:
        del image_data

    return analysis, dish_name


# --- Request Models ---


class AddMealRequest(BaseModel):
    dish_name: str = Field(..., min_length=1, max_length=200)
    venue: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)
    image_path: str | None = Field(default=None, max_length=500)

    @field_validator("dish_name", "venue", "notes")
    @classmethod
    def sanitize_text_fields(cls, v: str | None) -> str | None:
        return None if v is None else sanitize_user_input(v, max_length=2000)


class UpdateMealRequest(BaseModel):
    """Request model for updating a meal. Only includes fields that are actually updatable."""

    dish_name: str | None = Field(default=None, max_length=200)
    venue_name: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)
    rating: int | None = Field(default=None, ge=1, le=5)
    tags: list[str] | None = Field(default=None, max_length=20)
    public: bool | None = None
    image_path: str | None = Field(default=None, max_length=500)


# --- Routes ---


@router.get("/meals", response_model=MealListResponse)
@limiter.limit(RATE_LIMIT_CRUD)
async def list_meals(
    request: Request,
    limit: int = Query(default=10, ge=1, le=100),
    days: int | None = Query(default=None, ge=1, le=365),
    include_nutrition: bool = Query(default=False),
    user: AuthenticatedUser = Depends(get_current_user),
) -> MealListResponse:
    """Get user's food logs."""
    meals = await get_meals(
        user.user_id,
        limit=limit,
        days=days,
        include_nutrition=include_nutrition,
    )
    return MealListResponse(meals=meals, count=len(meals))


@router.get("/meals/{log_id}", response_model=MealDetailResponse)
@limiter.limit(RATE_LIMIT_CRUD)
async def get_single_meal(
    request: Request,
    log_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> MealDetailResponse:
    """Get a single food log entry."""
    meal = await get_meal(user.user_id, log_id)
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    return MealDetailResponse(meal=meal)


@router.post("/meals", response_model=ActionResponse)
@limiter.limit(RATE_LIMIT_CRUD)
async def create_meal(
    request: Request,
    meal_request: AddMealRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> ActionResponse:
    """Add a new meal to the food log. Requires authentication."""
    result = await add_meal(
        user.user_id,
        dish_name=meal_request.dish_name,
        venue=meal_request.venue,
        notes=meal_request.notes,
        image_path=meal_request.image_path,
    )
    return ActionResponse(**result)


@router.patch("/meals/{log_id}", response_model=ActionResponse)
@limiter.limit(RATE_LIMIT_CRUD)
async def patch_meal(
    request: Request,
    log_id: str,
    meal_request: UpdateMealRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> ActionResponse:
    """Update a food log entry. Requires authentication."""
    updates = meal_request.model_dump(exclude_unset=True)
    result = await update_meal(user.user_id, log_id, updates)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return ActionResponse(**result)


@router.delete("/meals/{log_id}", response_model=ActionResponse)
@limiter.limit(RATE_LIMIT_CRUD)
async def remove_meal(
    request: Request,
    log_id: str,
    user: AuthenticatedUser = Depends(require_write_access),
) -> ActionResponse:
    """Delete a food log entry. Requires authentication."""
    result = await delete_meal(user.user_id, log_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return ActionResponse(**result)


@router.post("/meals/with-image", response_model=ActionResponse)
@limiter.limit(RATE_LIMIT_CRUD)
async def create_meal_with_image(
    request: Request,
    image: UploadFile = File(...),
    dish_name: str | None = Form(default=None),
    venue: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    auto_analyze: bool = Form(default=True),
    user: AuthenticatedUser = Depends(require_write_access),
) -> ActionResponse:
    """Create a meal with image upload.

    Uploads the image to Firebase Storage, optionally analyzes it with Gemini,
    and creates the meal record.

    Args:
        image: The food image file (JPEG, PNG, WebP, HEIC supported)
        dish_name: Optional dish name (will be inferred from image if not provided)
        venue: Optional venue/restaurant name
        notes: Optional notes about the meal
        auto_analyze: Whether to analyze the image with Gemini (default: True)

    Returns:
        Created meal with log_id and optional analysis results
    """
    image_data, content_type = await _read_and_validate_image(image)

    dish_name = _sanitize_optional_text(dish_name, max_length=200)
    venue = _sanitize_optional_text(venue, max_length=200)
    notes = _sanitize_optional_text(notes, max_length=2000)

    # Check if storage is configured
    image_path: str | None = None
    image_url: str | None = None
    analysis = None

    if is_storage_configured():
        analysis, dish_name, image_path, image_url = await _analyze_with_storage(
            user_id=user.user_id,
            image=image,
            image_data=image_data,
            content_type=content_type,
            dish_name=dish_name,
            auto_analyze=auto_analyze,
        )
    else:
        logger.info("Storage not configured, analyzing image from bytes")
        analysis, dish_name = await _analyze_without_storage(
            image_data=image_data,
            content_type=content_type,
            dish_name=dish_name,
            auto_analyze=auto_analyze,
        )

    # Ensure we have a dish name
    if not dish_name:
        dish_name = "Unknown Dish"

    # Create the meal (image_path may be None if storage not configured)
    result = await add_meal(
        user.user_id,
        dish_name=dish_name,
        venue=venue,
        notes=notes,
        image_path=image_path,
    )

    result.setdefault("success", True)
    result.setdefault("dish_name", dish_name)
    result["analysis"] = analysis

    # Include image_url if available (only when storage is configured)
    if image_url:
        result["image_url"] = image_url
    else:
        result["storage_note"] = "Image analyzed but not stored locally"

    return ActionResponse(**result)
