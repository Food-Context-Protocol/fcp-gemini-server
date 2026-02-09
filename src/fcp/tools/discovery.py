"""Discovery tools for finding food in the real world."""

from typing import Any

from fcp.mcp.registry import tool
from fcp.services.maps import geocode_address, search_nearby_restaurants


@tool(
    name="dev.fcp.discovery.find_nearby_food",
    description="Find nearby food venues using Google Maps",
    category="discovery",
)
async def find_nearby_food_tool(
    latitude: float | None = None,
    longitude: float | None = None,
    radius: float = 2000.0,
    food_type: str = "restaurant",
    location: str | None = None,
) -> dict[str, Any]:
    """MCP tool wrapper for find_nearby_food."""
    venues = await find_nearby_food(latitude, longitude, radius, food_type, location)
    return {"venues": venues}


async def find_nearby_food(
    latitude: float | None = None,
    longitude: float | None = None,
    radius: float = 2000.0,
    food_type: str = "restaurant",
    location: str | None = None,
) -> list[dict[str, Any]]:
    """
    Find nearby food venues using Google Maps.

    Args:
        latitude: User's latitude (optional if location provided)
        longitude: User's longitude (optional if location provided)
        radius: Search radius in meters
        food_type: Type of food venue (restaurant, cafe, bar, etc.)
        location: City name or address (alternative to lat/lon)

    Returns:
        List of matching venues.
    """
    lat = latitude
    lon = longitude

    # Geocode if location string provided and no coordinates
    if (lat is None or lon is None) and location:
        geocode_result = await geocode_address(location)
        if geocode_result is None:
            return []
        lat = geocode_result.latitude
        lon = geocode_result.longitude

    if lat is None or lon is None:
        raise ValueError("Either (latitude, longitude) or location must be provided")

    # Map food_type to Google Places types if necessary
    place_types = [food_type] if food_type != "any" else ["restaurant", "cafe"]

    return await search_nearby_restaurants(latitude=lat, longitude=lon, radius=radius, included_types=place_types)
