"""USDA FoodData Central API client.

Provides access to USDA's comprehensive food and nutrition database.
API docs: https://fdc.nal.usda.gov/api-guide.html

The USDA_API_KEY environment variable is optional. When not set,
all functions gracefully return empty results.
"""

import logging
import os
from typing import Any

import httpx

USDA_API_BASE = "https://api.nal.usda.gov/fdc/v1"
DEFAULT_TIMEOUT = 10.0
logger = logging.getLogger(__name__)


def _get_api_key() -> str | None:
    """Get USDA API key from environment."""
    return os.environ.get("USDA_API_KEY")


async def search_foods(query: str, page_size: int = 5) -> list[dict[str, Any]]:
    """Search USDA FoodData Central for foods matching query.

    Args:
        query: Search term (food name, ingredient, etc.)
        page_size: Maximum results to return (default 5)

    Returns:
        List of food items with fdcId, description, dataType, etc.
        Empty list if API key not configured or on error.
    """
    api_key = _get_api_key()
    if not api_key:
        return []

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(
                f"{USDA_API_BASE}/foods/search",
                params={
                    "query": query,
                    "pageSize": page_size,
                    "api_key": api_key,
                },
            )
            if response.status_code == 200:
                try:
                    data = response.json()
                except ValueError:
                    logger.warning("USDA search returned non-JSON response for query=%r", query)
                    return []
                return data.get("foods", [])
    except httpx.TimeoutException:
        # Graceful degradation: return empty results on timeout
        pass
    except httpx.RequestError:
        # Graceful degradation: return empty results on network error
        pass

    return []


async def get_food_details(fdc_id: int) -> dict[str, Any]:
    """Get detailed nutrition data for a specific FDC ID.

    Args:
        fdc_id: USDA FoodData Central ID

    Returns:
        Complete food data including nutrients, portions, etc.
        Empty dict if API key not configured or on error.
    """
    api_key = _get_api_key()
    if not api_key:
        return {}

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(
                f"{USDA_API_BASE}/food/{fdc_id}",
                params={"api_key": api_key},
            )
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError:
                    logger.warning("USDA food details returned non-JSON response for fdc_id=%r", fdc_id)
                    return {}
    except httpx.TimeoutException:
        # Graceful degradation: return empty dict on timeout
        pass
    except httpx.RequestError:
        # Graceful degradation: return empty dict on network error
        pass

    return {}


def extract_micronutrients(food_data: dict[str, Any]) -> dict[str, float]:
    """Extract micronutrients from USDA food response.

    Args:
        food_data: Response from get_food_details()

    Returns:
        Dict mapping nutrient names to amounts, e.g.:
        {"protein_g": 25.0, "iron_mg": 2.5, ...}
    """
    nutrients: dict[str, float] = {}

    for nutrient in food_data.get("foodNutrients", []):
        nutrient_info = nutrient.get("nutrient", {})
        name = nutrient_info.get("name", "")
        amount = nutrient.get("amount")
        unit = nutrient_info.get("unitName", "")

        if name and amount is not None:
            # Create a normalized key: "protein_g", "iron_mg", etc.
            key = _normalize_nutrient_key(name, unit)
            nutrients[key] = float(amount)

    return nutrients


def _normalize_nutrient_key(name: str, unit: str) -> str:
    """Normalize nutrient name to a consistent key format.

    Args:
        name: Nutrient name from USDA (e.g., "Protein", "Iron, Fe", "Vitamin B-12")
        unit: Unit from USDA (e.g., "g", "mg", "µg")

    Returns:
        Normalized key like "protein_g" or "iron_mg"
    """
    import re

    clean_name = name.lower()

    # Remove ", total" suffix
    clean_name = re.sub(r",\s*total\b", "", clean_name)

    # Remove element symbols after comma (e.g., ", Fe", ", Zn", ", K", ", Na")
    # Matches: comma, optional space, 1-2 letter element symbol at word boundary
    clean_name = re.sub(r",\s*[a-z]{1,2}\b", "", clean_name)

    # Remove parenthetical content (e.g., "(DFE)", "(RAE)")
    clean_name = re.sub(r"\s*\([^)]*\)", "", clean_name)

    # Normalize vitamin names: "Vitamin B-12" -> "vitamin_b12"
    clean_name = clean_name.replace("-", "")

    # Replace spaces and remaining special chars with underscores
    clean_name = re.sub(r"[^a-z0-9]+", "_", clean_name)

    # Collapse multiple underscores and strip leading/trailing
    clean_name = re.sub(r"_+", "_", clean_name).strip("_")

    # Normalize unit (µg -> ug)
    unit_lower = unit.lower().replace("µ", "u")

    return f"{clean_name}_{unit_lower}" if clean_name else f"unknown_{unit_lower}"


async def get_food_by_name(food_name: str) -> dict[str, Any] | None:
    """Search for a food and return its detailed data.

    Convenience function that combines search and detail lookup.

    Args:
        food_name: Name of food to search for

    Returns:
        Detailed food data for best match, or None if not found.
    """
    results = await search_foods(food_name, page_size=1)
    if not results:
        return None

    fdc_id = results[0].get("fdcId")
    return await get_food_details(fdc_id) if fdc_id else None
