"""Live API Voice routes.

Provides endpoints for real-time voice processing using Gemini Live API
for meal logging and food queries.
"""

import logging

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, Field

from fcp.auth import AuthenticatedUser, require_write_access
from fcp.routes.router import APIRouter
from fcp.security import limiter
from fcp.tools.voice import process_voice_meal_log, voice_food_query

logger = logging.getLogger(__name__)

router = APIRouter()


class VoiceMealLogRequest(BaseModel):
    """Request body for voice meal logging."""

    audio_base64: str = Field(..., description="Base64-encoded audio data")
    mime_type: str = Field("audio/pcm", description="Audio MIME type (audio/pcm, audio/webm, audio/wav)")
    sample_rate: int = Field(16000, description="Sample rate in Hz", ge=8000, le=48000)


class VoiceMealLogResponse(BaseModel):
    """Response from voice meal logging."""

    status: str = Field(..., description="Status: logged, clarification_needed, or error")
    meal_data: dict | None = Field(None, description="Extracted meal information (if logged)")
    response_text: str | None = Field(None, description="AI's text response")
    response_audio_base64: str | None = Field(None, description="AI's audio response (base64)")
    error: str | None = Field(None, description="Error message if status is error")


class VoiceFoodQueryRequest(BaseModel):
    """Request body for voice food query."""

    audio_base64: str = Field(..., description="Base64-encoded audio data")
    mime_type: str = Field("audio/pcm", description="Audio MIME type (audio/pcm, audio/webm, audio/wav)")
    sample_rate: int = Field(16000, description="Sample rate in Hz", ge=8000, le=48000)


class VoiceFoodQueryResponse(BaseModel):
    """Response from voice food query."""

    status: str = Field(..., description="Status: search_requested, response, or error")
    query: str | None = Field(None, description="Extracted search query (if search requested)")
    user_id: str = Field(..., description="User ID for context")
    response_text: str | None = Field(None, description="AI's text response")
    response_audio_base64: str | None = Field(None, description="AI's audio response (base64)")
    error: str | None = Field(None, description="Error message if status is error")


@router.post(
    "/voice/meal",
    response_model=VoiceMealLogResponse,
    summary="Log meal via voice",
    description="""
Process voice input to log a meal using the Gemini Live API.

The AI assistant will:
- Understand the spoken meal description
- Ask clarifying questions if needed
- Extract structured meal data when ready

**Audio formats supported**:
- `audio/pcm`: Raw PCM audio
- `audio/webm`: WebM audio
- `audio/wav`: WAV audio

**Sample rates**: 8000-48000 Hz (16000 recommended)

**Returns**:
- `logged`: Meal was successfully extracted
- `clarification_needed`: AI needs more information
- `error`: Processing failed
    """,
)
@limiter.limit("10/minute")
async def voice_meal_log_endpoint(
    request: Request,
    body: VoiceMealLogRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> VoiceMealLogResponse:
    """Process voice input to log a meal."""
    logger.info("Voice meal log request [user=%s]", user.user_id)

    try:
        result = await process_voice_meal_log(
            audio_data=body.audio_base64,
            mime_type=body.mime_type,
            sample_rate=body.sample_rate,
        )

        return VoiceMealLogResponse(
            status=result.get("status", "error"),
            meal_data=result.get("meal_data"),
            response_text=result.get("response_text"),
            response_audio_base64=result.get("response_audio_base64"),
            error=result.get("error"),
        )

    except RuntimeError as e:
        logger.error("Voice processing failed - API not configured: %s", e)
        raise HTTPException(status_code=503, detail="Voice service unavailable") from e
    except Exception as e:
        logger.exception("Voice processing failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {e}") from e


@router.post(
    "/voice/query",
    response_model=VoiceFoodQueryResponse,
    summary="Query food history via voice",
    description="""
Process a voice query about food history using the Gemini Live API.

The AI assistant will:
- Understand natural language food queries
- Extract search parameters
- Provide conversational responses

**Example queries**:
- "What did I eat last week?"
- "Show me my lunch from Tuesday"
- "Find all the pasta dishes I've had"

**Returns**:
- `search_requested`: A search query was extracted
- `response`: General response (no search needed)
- `error`: Processing failed
    """,
)
@limiter.limit("10/minute")
async def voice_food_query_endpoint(
    request: Request,
    body: VoiceFoodQueryRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> VoiceFoodQueryResponse:
    """Process a voice query about food history."""
    logger.info("Voice food query request [user=%s]", user.user_id)

    try:
        result = await voice_food_query(
            audio_data=body.audio_base64,
            user_id=user.user_id,
            mime_type=body.mime_type,
            sample_rate=body.sample_rate,
        )

        return VoiceFoodQueryResponse(
            status=result.get("status", "error"),
            query=result.get("query"),
            user_id=result.get("user_id", user.user_id),
            response_text=result.get("response_text"),
            response_audio_base64=result.get("response_audio_base64"),
            error=result.get("error"),
        )

    except RuntimeError as e:
        logger.error("Voice query failed - API not configured: %s", e)
        raise HTTPException(status_code=503, detail="Voice service unavailable") from e
    except Exception as e:
        logger.exception("Voice query failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Voice query failed: {e}") from e
