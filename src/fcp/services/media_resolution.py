"""Media resolution control for cost optimization.

This module provides intelligent selection of media resolution
based on task requirements to optimize cost and performance.
"""

from enum import Enum
from typing import Literal

MediaResolution = Literal["low", "medium", "high", "ultra_high"]


class MediaTask(Enum):
    """Classification of media processing tasks."""

    FOOD_DETECTION = "food_detection"  # Is this food?
    CUISINE_CLASSIFICATION = "cuisine"  # What cuisine?
    BASIC_ANALYSIS = "basic_analysis"  # Quick dish ID
    DETAILED_ANALYSIS = "detailed_analysis"  # Full nutrition
    INGREDIENT_EXTRACTION = "ingredients"  # Identify all ingredients
    RECEIPT_OCR = "receipt_ocr"  # Read receipt text
    PORTION_ANALYSIS = "portion_analysis"  # Precise measurements


# Token consumption per resolution level (approximate)
RESOLUTION_TOKENS = {
    "low": 70,
    "medium": 560,
    "high": 1120,
    "ultra_high": 2500,
}

# Optimal resolution mapping based on task requirements
RESOLUTION_MAP: dict[MediaTask, MediaResolution] = {
    MediaTask.FOOD_DETECTION: "low",  # Just classification
    MediaTask.CUISINE_CLASSIFICATION: "low",  # Overall appearance
    MediaTask.BASIC_ANALYSIS: "medium",  # Standard detail
    MediaTask.DETAILED_ANALYSIS: "high",  # Ingredient visibility
    MediaTask.INGREDIENT_EXTRACTION: "high",  # Need to see everything
    MediaTask.RECEIPT_OCR: "ultra_high",  # Text must be readable
    MediaTask.PORTION_ANALYSIS: "ultra_high",  # Precise measurements
}


def get_optimal_resolution(task: MediaTask) -> MediaResolution:
    """Get the optimal resolution for a media processing task.

    Args:
        task: The MediaTask to get resolution for

    Returns:
        The optimal media resolution
    """
    return RESOLUTION_MAP.get(task, "medium")


def estimate_token_savings(task: MediaTask) -> tuple[int, float]:
    """Estimate token delta vs. always using 'high' resolution.

    This returns the difference in tokens between 'high' and the optimal
    resolution for the given task. Positive values indicate savings (when
    optimal is lower than high), negative values indicate extra cost (when
    optimal is higher than high, e.g., ultra_high).

    Args:
        task: The MediaTask to estimate for

    Returns:
        Tuple of (token delta, percentage delta). Positive = savings, negative = extra cost.
    """
    optimal = get_optimal_resolution(task)
    optimal_tokens = RESOLUTION_TOKENS[optimal]
    high_tokens = RESOLUTION_TOKENS["high"]

    tokens_saved = high_tokens - optimal_tokens
    percentage = tokens_saved / high_tokens if high_tokens > 0 else 0.0

    return tokens_saved, percentage


def get_resolution_for_operation(operation: str) -> MediaResolution:
    """Get resolution for a named operation string.

    This provides a string-based interface for compatibility with
    existing code that uses operation strings.

    Args:
        operation: Operation name string

    Returns:
        Optimal media resolution
    """
    operation_map = {
        "is_food": MediaTask.FOOD_DETECTION,
        "food_detection": MediaTask.FOOD_DETECTION,
        "cuisine": MediaTask.CUISINE_CLASSIFICATION,
        "cuisine_classification": MediaTask.CUISINE_CLASSIFICATION,
        "quick_analysis": MediaTask.BASIC_ANALYSIS,
        "basic_analysis": MediaTask.BASIC_ANALYSIS,
        "analyze": MediaTask.DETAILED_ANALYSIS,
        "detailed_analysis": MediaTask.DETAILED_ANALYSIS,
        "ingredients": MediaTask.INGREDIENT_EXTRACTION,
        "ingredient_extraction": MediaTask.INGREDIENT_EXTRACTION,
        "receipt": MediaTask.RECEIPT_OCR,
        "receipt_ocr": MediaTask.RECEIPT_OCR,
        "portions": MediaTask.PORTION_ANALYSIS,
        "portion_analysis": MediaTask.PORTION_ANALYSIS,
    }

    if task := operation_map.get(operation.lower()):
        return get_optimal_resolution(task)

    # Default to medium for unknown operations
    return "medium"
