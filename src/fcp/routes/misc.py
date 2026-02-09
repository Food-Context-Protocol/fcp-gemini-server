"""Miscellaneous Routes.

Various specialized endpoints:
- POST /enrich - Enrich food log with AI analysis
- POST /suggest - Get AI meal suggestions
- POST /visual/image-prompt - Generate image prompts
- POST /audio/log-meal - Log meal from audio
- POST /audio/voice-correction - Extract voice correction intent
- POST /analyze/voice - Analyze voice transcript for meal creation
- POST /cottage/label - Generate food labels
- GET /clinical/report - Generate clinical report
- POST /civic/plan-festival - Plan food festival
- POST /civic/economic-gaps - Detect economic gaps
- POST /parser/menu - Parse menu image
- POST /parser/receipt - Parse receipt image
- POST /taste-buddy/check - Dietary compatibility check
- GET /flavor/pairings - Get flavor pairings
- GET /trends/identify - Identify food trends
"""

from typing import Any

from fastapi import Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

from fcp.auth import AuthenticatedUser, get_current_user, require_write_access
from fcp.routes.router import APIRouter
from fcp.routes.schemas import ImageURLRequest
from fcp.security import sanitize_user_input
from fcp.security.rate_limit import RATE_LIMIT_ANALYZE, RATE_LIMIT_SUGGEST, limiter
from fcp.tools import (
    analyze_voice_transcript,
    check_dietary_compatibility,
    detect_economic_gaps,
    donate_meal,
    enrich_entry,
    extract_voice_correction,
    generate_cottage_label,
    generate_dietitian_report,
    generate_image_prompt,
    get_flavor_pairings,
    identify_emerging_trends,
    log_meal_from_audio,
    plan_food_festival,
    suggest_meal,
)

router = APIRouter()


# --- Request Models ---


class EnrichRequest(BaseModel):
    log_id: str = Field(..., min_length=1, max_length=100)


class SuggestRequest(BaseModel):
    """Request model for meal suggestions. Null values are converted to defaults."""

    context: str = Field(default="", max_length=500)
    exclude_recent_days: int = Field(default=3, ge=0, le=30)

    @field_validator("context", mode="before")
    @classmethod
    def handle_null_context(cls, v: str | None) -> str:
        """Convert null to empty string and sanitize input."""
        # Always sanitize - handles None, strips whitespace, removes injection patterns
        return sanitize_user_input(v, max_length=500)

    @field_validator("exclude_recent_days", mode="before")
    @classmethod
    def handle_null_days(cls, v: int | None) -> int:
        """Convert null to default value of 3."""
        return 3 if v is None else v


class ImagePromptRequest(BaseModel):
    """Request model for image prompt generation. Null values are converted to defaults."""

    subject: str = Field(..., min_length=1)
    style: str = Field(default="photorealistic")
    context: str = Field(default="menu")

    @field_validator("style", mode="before")
    @classmethod
    def handle_null_style(cls, v: str | None) -> str:
        """Convert null to default 'photorealistic'."""
        return v if v is not None else "photorealistic"

    @field_validator("context", mode="before")
    @classmethod
    def handle_null_context(cls, v: str | None) -> str:
        """Convert null to default 'menu'."""
        return v if v is not None else "menu"


class AudioLogRequest(BaseModel):
    audio_url: str = Field(...)
    notes: str | None = Field(default=None)


class CottageLabelRequest(BaseModel):
    """Request model for cottage food labels. Null is_refrigerated is converted to False."""

    product_name: str
    ingredients: list[str]
    net_weight: str | None = None
    business_name: str | None = None
    business_address: str | None = None
    is_refrigerated: bool = False

    @field_validator("is_refrigerated", mode="before")
    @classmethod
    def handle_null_refrigerated(cls, v: bool | None) -> bool:
        """Convert null to default False."""
        return v if v is not None else False


class FoodFestivalRequest(BaseModel):
    """Request model for food festival planning. Null target_vendor_count is converted to 10."""

    city_name: str
    theme: str
    target_vendor_count: int = 10
    location_description: str | None = None

    @field_validator("target_vendor_count", mode="before")
    @classmethod
    def handle_null_vendor_count(cls, v: int | None) -> int:
        """Convert null to default value of 10."""
        return v if v is not None else 10


class EconomicGapRequest(BaseModel):
    neighborhood: str
    existing_cuisines: list[str]


class DietaryCheckRequest(BaseModel):
    dish_name: str
    ingredients: list[str]
    user_allergies: list[str]
    user_diet: list[str]


class DonateMealRequest(BaseModel):
    log_id: str = Field(..., min_length=1, max_length=100)
    organization: str = Field(default="Local Food Bank", max_length=200)


_VOICE_INPUT_MAX_LENGTH = 1000


class VoiceCorrectionRequest(BaseModel):
    voice_input: str = Field(..., min_length=1, max_length=_VOICE_INPUT_MAX_LENGTH)

    @field_validator("voice_input")
    @classmethod
    def sanitize_voice_input(cls, v: str) -> str:
        return sanitize_user_input(v, max_length=_VOICE_INPUT_MAX_LENGTH)


class VoiceTranscriptRequest(BaseModel):
    transcript: str = Field(..., min_length=1, max_length=2000)

    @field_validator("transcript")
    @classmethod
    def sanitize_transcript(cls, v: str) -> str:
        return sanitize_user_input(v, max_length=2000)


# --- Routes ---


@router.post("/enrich")
@limiter.limit(RATE_LIMIT_ANALYZE)
async def enrich_log(
    request: Request,
    enrich_request: EnrichRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Enrich a food log entry with AI analysis. Requires authentication."""
    result = await enrich_entry(user.user_id, enrich_request.log_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/suggest")
@limiter.limit(RATE_LIMIT_SUGGEST)
async def meal_suggestions(
    request: Request,
    suggest_request: SuggestRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get AI-powered meal suggestions."""
    suggestions = await suggest_meal(
        user.user_id,
        context=suggest_request.context,
        exclude_recent_days=suggest_request.exclude_recent_days,
    )
    return {"suggestions": suggestions, "context": suggest_request.context}


@router.post("/visual/image-prompt")
async def post_image_prompt(
    prompt_request: ImagePromptRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Generate a detailed, style-optimized prompt for creating food images."""
    prompt = await generate_image_prompt(prompt_request.subject, prompt_request.style, prompt_request.context)
    return {"prompt": prompt}


@router.post("/audio/log-meal")
async def post_audio_log(
    audio_request: AudioLogRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Log a meal by providing a URL to an audio recording. Requires authentication."""
    return await log_meal_from_audio(user.user_id, audio_request.audio_url, audio_request.notes)


@router.post("/audio/voice-correction")
@limiter.limit(RATE_LIMIT_ANALYZE)
async def post_voice_correction(
    request: Request,
    correction_request: VoiceCorrectionRequest,
    _user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Extract user's intent to correct a food log entry from voice input."""
    return await extract_voice_correction(correction_request.voice_input)


@router.post("/analyze/voice")
@limiter.limit(RATE_LIMIT_ANALYZE)
async def post_analyze_voice(
    request: Request,
    voice_request: VoiceTranscriptRequest,
    _user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Analyze a voice transcript to extract meal information for log creation."""
    return await analyze_voice_transcript(voice_request.transcript)


@router.post("/cottage/label")
async def post_cottage_label(
    label_request: CottageLabelRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Generate a legally compliant food label for home-based businesses."""
    return await generate_cottage_label(
        label_request.product_name,
        label_request.ingredients,
        label_request.net_weight,
        label_request.business_name,
        label_request.business_address,
        label_request.is_refrigerated,
    )


@router.get("/clinical/report")
async def get_clinical_report(
    days: int = Query(default=7, ge=1, le=30),
    focus_area: str | None = Query(default=None),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Analyze recent food logs and generate a professional clinical report."""
    return await generate_dietitian_report(user.user_id, days, focus_area)


@router.post("/civic/plan-festival")
async def post_plan_festival(
    festival_request: FoodFestivalRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Plan a community food festival based on local engagement."""
    return await plan_food_festival(
        festival_request.city_name,
        festival_request.theme,
        festival_request.target_vendor_count,
        festival_request.location_description,
    )


@router.post("/civic/economic-gaps")
async def post_economic_gaps(
    gap_request: EconomicGapRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Identify culinary gaps in a neighborhood."""
    return await detect_economic_gaps(gap_request.neighborhood, gap_request.existing_cuisines)


@router.post("/parser/menu")
async def post_parse_menu(
    analyze_request: ImageURLRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Parse a restaurant menu image into structured dish data."""
    from fcp.tools import parse_menu

    return await parse_menu(analyze_request.image_url)


@router.post("/parser/receipt")
async def post_parse_receipt(
    analyze_request: ImageURLRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Parse a grocery receipt image into itemized pantry data."""
    from fcp.tools import parse_receipt

    return await parse_receipt(analyze_request.image_url)


@router.post("/taste-buddy/check")
async def post_dietary_check(
    check_request: DietaryCheckRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Check a dish against user allergies and dietary preferences."""
    return await check_dietary_compatibility(
        check_request.dish_name,
        check_request.ingredients,
        check_request.user_allergies,
        check_request.user_diet,
    )


@router.get("/flavor/pairings")
async def get_pairings(
    subject: str = Query(..., min_length=1),
    pairing_type: str = Query(default="ingredient", pattern=r"^(ingredient|beverage)$"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get perfect culinary pairings for an ingredient or dish."""
    return await get_flavor_pairings(subject, pairing_type)


@router.get("/trends/identify")
async def get_trends(
    region: str = Query(default="local"),
    cuisine_focus: str | None = Query(default=None),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Identify trending food movements based on global and local data."""
    return await identify_emerging_trends(user.user_id, region, cuisine_focus)


@router.post("/impact/donate")
async def post_donate_meal(
    donate_request: DonateMealRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """
    Pledge a meal for donation to a food program. Requires authentication.

    This marks the meal as donated and associates it with a food bank or
    community organization for social impact tracking.
    """
    result = await donate_meal(user.user_id, donate_request.log_id, donate_request.organization)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result
