"""Live restaurant data service using grounded structured outputs.

This service combines Google Search grounding with structured JSON output
to fetch real-time restaurant information.
"""

import json
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class RestaurantLiveData(BaseModel):
    """Live data about a restaurant from Google Search."""

    name: str
    current_rating: float = Field(ge=0, le=5)
    review_count: int = Field(ge=0)
    is_currently_open: bool
    current_wait_time: str | None = None
    recent_reviews: list[str] = Field(default_factory=list)
    popular_dishes: list[str] = Field(default_factory=list)
    price_range: str
    last_updated: str


class FoodRecallAlert(BaseModel):
    """Food recall alert information."""

    product_name: str
    brand: str
    recall_reason: str
    affected_regions: list[str]
    recall_date: str
    severity: str  # "Class I", "Class II", "Class III"
    source_url: str


class IngredientPrice(BaseModel):
    """Current price for an ingredient."""

    ingredient_name: str
    average_price: float
    unit: str
    price_range: tuple[float, float]
    trending: str  # "up", "down", "stable"


async def get_live_restaurant_data(
    restaurant_name: str,
    location: str,
) -> RestaurantLiveData:
    """Get live restaurant data using grounded structured output.

    Args:
        restaurant_name: Name of the restaurant
        location: City/area location

    Returns:
        Live restaurant data with ratings, reviews, etc.
    """
    client = genai.Client()

    response = await client.aio.models.generate_content(
        model="gemini-3-flash-preview",
        contents=f"Get current information about {restaurant_name} in {location}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RestaurantLiveData.model_json_schema(),
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )

    data = json.loads(response.text)
    return RestaurantLiveData(**data)


async def check_food_recalls(
    food_item: str,
    brand: str | None = None,
) -> list[FoodRecallAlert]:
    """Check for active food recalls using grounded search.

    Args:
        food_item: The food item to check
        brand: Optional brand name to filter by

    Returns:
        List of active recall alerts
    """
    client = genai.Client()

    query = f"food recall alerts for {food_item}"
    if brand:
        query += f" {brand}"

    response = await client.aio.models.generate_content(
        model="gemini-3-flash-preview",
        contents=f"Check for active food recalls: {query}. Return as JSON array.",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )

    try:
        data = json.loads(response.text)
        if isinstance(data, list):
            return [FoodRecallAlert(**item) for item in data]
        return []
    except (json.JSONDecodeError, TypeError):
        return []


async def get_ingredient_prices(
    ingredients: list[str],
    location: str,
) -> dict[str, IngredientPrice]:
    """Get current prices for ingredients using grounded search.

    Args:
        ingredients: List of ingredient names
        location: Location for pricing

    Returns:
        Dictionary mapping ingredient names to price data
    """
    client = genai.Client()

    response = await client.aio.models.generate_content(
        model="gemini-3-flash-preview",
        contents=f"Get current grocery prices in {location} for: {', '.join(ingredients)}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )

    try:
        data = json.loads(response.text)
        return {
            item["ingredient_name"]: IngredientPrice(**item)
            for item in (data if isinstance(data, list) else [data])
            if "ingredient_name" in item
        }
    except (json.JSONDecodeError, TypeError):
        return {}


async def get_restaurant_recommendations(
    cuisine: str,
    location: str,
    occasion: str | None = None,
    price_range: str | None = None,
) -> list[dict[str, Any]]:
    """Get restaurant recommendations with live data.

    Args:
        cuisine: Type of cuisine desired
        location: Location to search
        occasion: Optional occasion (date night, family, etc.)
        price_range: Optional price range filter

    Returns:
        List of restaurant recommendations with live data
    """
    client = genai.Client()

    query = f"Best {cuisine} restaurants in {location}"
    if occasion:
        query += f" for {occasion}"
    if price_range:
        query += f", {price_range} price range"

    response = await client.aio.models.generate_content(
        model="gemini-3-flash-preview",
        contents=query,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )

    try:
        data = json.loads(response.text)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        return []
