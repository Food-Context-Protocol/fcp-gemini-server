"""Real-time voice processing using Gemini Live API.

Provides interactive voice conversations for meal logging and food queries.
"""

import base64
import logging
from typing import Any

from fcp.services.gemini import gemini
from fcp.utils.errors import tool_error

logger = logging.getLogger(__name__)


async def process_voice_meal_log(
    audio_data: bytes | str,
    mime_type: str = "audio/pcm",
    sample_rate: int = 16000,
) -> dict[str, Any]:
    """
    Process voice input to log a meal using the Live API.

    Uses real-time voice processing for natural meal logging conversations.
    The AI will understand the meal description and extract structured data.

    Args:
        audio_data: Audio bytes or base64-encoded string
        mime_type: Audio MIME type (audio/pcm, audio/webm, audio/wav)
        sample_rate: Sample rate in Hz (default 16000)

    Returns:
        Dict with:
        - meal_data: Extracted meal information (if log_meal was called)
        - response_text: AI's text response
        - response_audio_base64: AI's audio response (if generated)
        - status: "logged", "clarification_needed", or "error"
    """
    # Handle base64 input
    if isinstance(audio_data, str):
        try:
            audio_bytes = base64.b64decode(audio_data)
        except Exception as e:
            logger.error("Failed to decode base64 audio: %s", e)
            return {
                "meal_data": None,
                "response_text": None,
                "status": "error",
                "error": "Invalid base64 audio data",
            }
    else:
        audio_bytes = audio_data

    try:
        result = await gemini.process_live_audio(
            audio_data=audio_bytes,
            mime_type=mime_type,
            sample_rate=sample_rate,
        )

        # Check if log_meal was called
        meal_data = None
        status = "clarification_needed"

        for fc in result.get("function_calls", []):
            if fc["name"] == "log_meal":
                meal_data = fc["args"]
                status = "logged"
                break

        response: dict[str, Any] = {
            "meal_data": meal_data,
            "response_text": result.get("response_text"),
            "status": status,
        }

        # Include audio response if available
        if result.get("response_audio"):
            response["response_audio_base64"] = base64.b64encode(result["response_audio"]).decode("utf-8")

        return response

    except Exception as e:
        logger.exception("Error processing voice meal log: %s", e)
        return {
            "meal_data": None,
            "response_text": None,
            "status": "error",
            "error": "An error occurred during voice meal logging",
        }


async def voice_food_query(
    audio_data: bytes | str,
    user_id: str,
    mime_type: str = "audio/pcm",
    sample_rate: int = 16000,
) -> dict[str, Any]:
    """
    Process a voice query about food history.

    Uses the Live API to understand natural language food queries
    like "What did I eat last week?" or "Show me my lunch from Tuesday".

    Args:
        audio_data: Audio bytes or base64-encoded string
        user_id: User ID for food history lookup
        mime_type: Audio MIME type
        sample_rate: Sample rate in Hz

    Returns:
        Dict with:
        - query: Extracted search query (if search_food_history was called)
        - response_text: AI's text response
        - status: "search_requested", "response", or "error"
    """
    # Handle base64 input
    if isinstance(audio_data, str):
        try:
            audio_bytes = base64.b64decode(audio_data)
        except Exception as e:
            logger.error("Failed to decode base64 audio: %s", e)
            return {
                "query": None,
                "response_text": None,
                "status": "error",
                "error": "Invalid base64 audio data",
            }
    else:
        audio_bytes = audio_data

    try:
        result = await gemini.process_live_audio(
            audio_data=audio_bytes,
            mime_type=mime_type,
            sample_rate=sample_rate,
        )

        # Check if search was requested
        query = None
        status = "response"

        for fc in result.get("function_calls", []):
            if fc["name"] == "search_food_history":
                query = fc["args"].get("query")
                status = "search_requested"
                break

        response: dict[str, Any] = {
            "query": query,
            "user_id": user_id,
            "response_text": result.get("response_text"),
            "status": status,
        }

        # Include audio response if available
        if result.get("response_audio"):
            response["response_audio_base64"] = base64.b64encode(result["response_audio"]).decode("utf-8")

        return response

    except Exception as e:
        logger.exception("Error processing voice food query: %s", e)
        return {
            "query": None,
            "response_text": None,
            "status": "error",
            "error": "An error occurred during voice food query",
        }
