"""Audio processing tools for FCP."""

import logging
from typing import Any

from fcp.mcp.registry import tool
from fcp.services.firestore import firestore_client
from fcp.services.gemini import gemini

logger = logging.getLogger(__name__)


@tool(
    name="dev.fcp.nutrition.log_meal_from_audio",
    description="Process an audio recording of a meal description and log it",
    category="nutrition",
    requires_write=True,
)
async def log_meal_from_audio(user_id: str, audio_url: str, notes: str | None = None) -> dict[str, Any]:
    """
    Process an audio recording of a meal description and log it.

    Args:
        user_id: The user ID.
        audio_url: URL to the audio file (mp3, wav, etc.).
        notes: Optional text notes to accompany the audio.

    Returns:
        Structured log data of the processed meal.
    """
    # 1. Transcribe and extract dish information from audio
    prompt = """
    You are listening to a voice note of someone describing what they just ate.
    Transcribe the description and identify the dish name, venue (if mentioned),
    and any details about ingredients or feelings.

    Return your analysis as a JSON object:
    {
        "transcription": "...",
        "dish_name": "...",
        "venue": "...",
        "notes": "..."
    }
    """

    try:
        # Use Gemini's multimodal capabilities to "listen" to the audio
        analysis = await gemini.generate_json(prompt, media_url=audio_url)

        # 2. Use text-based analysis for nutrition/ingredients
        # (analyze_meal expects an image URL, so we use analyze_voice_transcript instead)
        dish_description = (
            f"{analysis.get('dish_name')} at {analysis.get('venue')}. {analysis.get('notes')} {notes or ''}"
        )
        meal_data = await analyze_voice_transcript(dish_description)

        # Check if extraction failed - don't create invalid logs
        if meal_data.get("error") or not meal_data.get("dish_name"):
            logger.warning(
                "Audio extraction failed for user %s: %s",
                user_id,
                meal_data.get("error", "No dish name extracted"),
            )
            return {
                "error": meal_data.get("error", "Could not extract meal from audio"),
                "status": "failed",
                "transcription": analysis.get("transcription"),
            }

        # 3. Create the log in Firestore only on successful extraction
        log_data = {
            **meal_data,
            "voice_note_url": audio_url,
            "transcription": analysis.get("transcription"),
            "source": "voice_note",
            "processing_status": "enriched",
        }

        log_id = await firestore_client.create_log(user_id, log_data)
        log_data["id"] = log_id

        return log_data

    except Exception as e:
        logger.error("Error processing audio log: %s", e, exc_info=True)
        return {"error": "Error processing audio log", "status": "failed"}


def _normalize_confidence(value: Any) -> float:
    """Normalize confidence to a float in [0.0, 1.0]."""
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _create_voice_analysis_error(error_message: str) -> dict[str, Any]:
    """Create a standardized error response for voice transcript analysis."""
    return {
        "dish_name": None,
        "description": None,
        "venue": None,
        "ingredients": [],
        "meal_type": None,
        "nutrition_estimate": None,
        "confidence": 0.0,
        "error": error_message,
    }


async def analyze_voice_transcript(transcript: str) -> dict[str, Any]:
    """
    Analyze a voice transcript to extract meal information for creating a food log.

    Args:
        transcript: Text transcription from voice input describing a meal.

    Returns:
        dict with extracted meal data ready for log creation:
        - dish_name: Identified dish name
        - description: Meal description
        - venue: Restaurant/location if mentioned
        - ingredients: List of identified ingredients
        - nutrition_estimate: Basic nutrition estimate if determinable
        - confidence: Float in [0.0, 1.0]
        - error: Error message if analysis failed, None otherwise
    """
    prompt = f"""
Analyze this voice transcript describing a meal and extract structured information.

Voice Transcript: "{transcript}"

Return a JSON object with:
{{
    "dish_name": "name of the dish",
    "description": "brief description of the meal",
    "venue": "restaurant or location name if mentioned, null otherwise",
    "ingredients": ["list", "of", "ingredients"],
    "meal_type": "breakfast" or "lunch" or "dinner" or "snack",
    "nutrition_estimate": {{
        "calories": estimated calories or null,
        "protein_g": estimated protein in grams or null,
        "carbs_g": estimated carbs in grams or null,
        "fat_g": estimated fat in grams or null
    }},
    "confidence": 0.0 to 1.0 based on clarity of the transcript
}}

If the transcript is unclear or doesn't describe food, return:
{{"dish_name": null, "description": null, "confidence": 0, "error": "Could not identify a meal"}}
"""

    try:
        result = await gemini.generate_json(prompt)

        # Normalize and validate response
        dish_name = result.get("dish_name")
        if not dish_name:
            error_msg = result.get("error", "Could not identify a meal from transcript")
            return _create_voice_analysis_error(error_msg)

        return {
            "dish_name": dish_name,
            "description": result.get("description"),
            "venue": result.get("venue"),
            "ingredients": result.get("ingredients", []),
            "meal_type": result.get("meal_type"),
            "nutrition_estimate": result.get("nutrition_estimate"),
            "confidence": _normalize_confidence(result.get("confidence", 0.5)),
            "error": None,
        }
    except Exception as e:
        logger.error("Error analyzing voice transcript: %s", e, exc_info=True)
        return _create_voice_analysis_error("Error analyzing voice transcript")


async def extract_voice_correction(voice_input: str) -> dict[str, Any]:
    """
    Extract the user's intent to correct a food log entry from voice input.

    Args:
        voice_input: Text from voice transcription describing a correction.

    Returns:
        dict with field to correct, new value, confidence score, and error.
        - field: The field to correct (dish_name, description, ingredients) or None
        - new_value: The corrected value or None
        - confidence: Float in [0.0, 1.0], normalized and clamped
        - error: Error message if an error occurred, None otherwise
    """
    prompt = f"""
Extract the user's intent to correct a food log entry from their voice input.

Voice Input: "{voice_input}"

Return a JSON object with:
{{
    "field": "dish_name" or "description" or "ingredients",
    "new_value": "the corrected value",
    "confidence": 0.9
}}

If the input is unclear or not a correction, return:
{{"field": null, "new_value": null, "confidence": 0}}
"""

    try:
        result = await gemini.generate_json(prompt)
        return {
            "field": result.get("field"),
            "new_value": result.get("new_value"),
            "confidence": _normalize_confidence(result.get("confidence", 0)),
            "error": None,
        }
    except Exception as e:
        logger.error("Error extracting voice correction: %s", e, exc_info=True)
        return {
            "field": None,
            "new_value": None,
            "confidence": 0.0,
            "error": "Error extracting voice correction",
        }
