"""Thinking level optimization strategy for Gemini 3.

This module provides intelligent selection of thinking levels
based on task complexity to optimize cost and latency.
"""

from enum import Enum
from typing import Literal

ThinkingLevel = Literal["minimal", "low", "medium", "high"]


class TaskComplexity(Enum):
    """Classification of task complexity for thinking level selection."""

    TRIVIAL = "trivial"  # Simple lookups, yes/no
    SIMPLE = "simple"  # Basic analysis, classification
    MODERATE = "moderate"  # Multi-step reasoning
    COMPLEX = "complex"  # Deep analysis, planning


# Mapping of FoodLog operations to optimal thinking levels
THINKING_LEVEL_MAP: dict[str, ThinkingLevel] = {
    # Trivial tasks - use minimal/low
    "food_detection": "minimal",  # Is this a food photo?
    "cuisine_classification": "low",  # What cuisine is this?
    "dietary_tag_check": "low",  # Is this vegetarian?
    "spice_level_estimate": "low",  # How spicy is this?
    # Simple tasks - use low
    "dish_name_extraction": "low",
    "basic_nutrition_estimate": "low",
    "ingredient_list": "low",
    "portion_size_guess": "low",
    # Moderate tasks - use medium
    "detailed_nutrition": "medium",
    "recipe_from_image": "medium",
    "taste_profile_update": "medium",
    "meal_suggestions": "medium",
    # Complex tasks - use high
    "lifetime_analysis": "high",
    "meal_planning": "high",
    "dietary_coaching": "high",
    "recipe_creation": "high",
    "deep_research": "high",
    "multi_image_analysis": "high",
}


def get_thinking_level(operation: str) -> ThinkingLevel:
    """Get the optimal thinking level for an operation.

    Args:
        operation: The operation identifier

    Returns:
        The optimal thinking level for the operation
    """
    return THINKING_LEVEL_MAP.get(operation, "high")


def estimate_cost_savings(operation: str) -> float:
    """Estimate cost savings vs. always using 'high'.

    Args:
        operation: The operation identifier

    Returns:
        Estimated savings as a decimal (0.7 = 70% cheaper)
    """
    level = get_thinking_level(operation)
    savings_map = {
        "minimal": 0.7,  # 70% cheaper
        "low": 0.5,  # 50% cheaper
        "medium": 0.25,  # 25% cheaper
        "high": 0.0,  # baseline
    }
    return savings_map.get(level, 0.0)
