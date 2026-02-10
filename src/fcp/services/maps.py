"""Google Maps Platform integration for FCP."""

import logging
import math
import os
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
PLACES_API_URL = "https://places.googleapis.com/v1/places:searchNearby"
GEOCODING_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"


@dataclass
class GeocodingResult:
    """Result from geocoding an address."""

    latitude: float
    longitude: float
    formatted_address: str


async def geocode_address(address: str) -> GeocodingResult | None:
    """Convert an address or city name to geographic coordinates.

    Args:
        address: City name, address, or location string (e.g., "San Francisco, CA")

    Returns:
        GeocodingResult with lat/lon or None if not found.

    Raises:
        ValueError: If address is empty or invalid.
    """
    if not address or not address.strip():
        raise ValueError("Address cannot be empty")

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_MAPS_API_KEY not configured for geocoding.")
        return None

    params = {
        "address": address.strip(),
        "key": api_key,
    }

    try:
        logger.info("Geocoding address: %s", address)
        async with httpx.AsyncClient() as client:
            response = await client.get(GEOCODING_API_URL, params=params, timeout=10.0)

        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK" or not data.get("results"):
            logger.info("No geocoding results for: %s (status: %s)", address, data.get("status"))
            return None

        result = data["results"][0]
        location = result["geometry"]["location"]

        geocoded = GeocodingResult(
            latitude=location["lat"],
            longitude=location["lng"],
            formatted_address=result.get("formatted_address", address),
        )
        logger.info("Geocoded '%s' successfully", address)
        return geocoded

    except Exception as e:
        logger.error("Error geocoding address '%s': %s", address, e)
        return None


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points using Haversine formula.

    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point

    Returns:
        Distance in meters
    """
    r = 6371000  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return r * c


async def find_nearby_places(
    latitude: float,
    longitude: float,
    radius: float = 1000.0,
    max_results: int = 5,
    included_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Find nearby places using Google Maps API.

    Returns places with:
    - name, address, rating, review_count, id
    - latitude, longitude (venue location)
    - distance (meters from user)
    - is_open (boolean, if available)
    - price_level (1-5 scale: 1=free, 2=inexpensive, 3=moderate, 4=expensive, 5=very expensive)
    """
    if included_types is None:
        included_types = ["restaurant"]
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_MAPS_API_KEY not configured. Returning empty results.")
        return []

    # Request all fields needed for the UI
    field_mask = ",".join(
        [
            "places.displayName",
            "places.formattedAddress",
            "places.rating",
            "places.userRatingCount",
            "places.types",
            "places.id",
            "places.location",
            "places.priceLevel",
            "places.regularOpeningHours",
        ]
    )

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": field_mask,
    }

    body = {
        "includedTypes": included_types,
        "maxResultCount": max_results,
        "locationRestriction": {"circle": {"center": {"latitude": latitude, "longitude": longitude}, "radius": radius}},
    }

    try:
        logger.info(
            "Searching places: radius=%dm, types=%s",
            int(radius),
            included_types,
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(PLACES_API_URL, headers=headers, json=body, timeout=10.0)

        response.raise_for_status()
        data = response.json()
        logger.info("Found %d places", len(data.get("places", [])))

        places = []
        for place in data.get("places", []):
            # Extract location
            location = place.get("location", {})
            place_lat = location.get("latitude")
            place_lon = location.get("longitude")

            # Calculate distance from user
            distance = None
            if place_lat is not None and place_lon is not None:
                distance = haversine_distance(latitude, longitude, place_lat, place_lon)

            # Extract opening hours
            opening_hours = place.get("regularOpeningHours", {})
            is_open = opening_hours.get("openNow")

            # Extract price level (Google returns PRICE_LEVEL_FREE, PRICE_LEVEL_INEXPENSIVE, etc.)
            # Normalize to 1-5 scale: 1=free, 2=inexpensive, 3=moderate, 4=expensive, 5=very expensive
            price_level_str = place.get("priceLevel")
            price_level = None
            if price_level_str:
                price_map = {
                    "PRICE_LEVEL_FREE": 1,
                    "PRICE_LEVEL_INEXPENSIVE": 2,
                    "PRICE_LEVEL_MODERATE": 3,
                    "PRICE_LEVEL_EXPENSIVE": 4,
                    "PRICE_LEVEL_VERY_EXPENSIVE": 5,
                }
                price_level = price_map.get(price_level_str)

            places.append(
                {
                    "name": place.get("displayName", {}).get("text", "Unknown"),
                    "address": place.get("formattedAddress"),
                    "rating": place.get("rating"),
                    "review_count": place.get("userRatingCount"),
                    "id": place.get("id"),
                    "source": "Google Maps",
                    "latitude": place_lat,
                    "longitude": place_lon,
                    "distance": round(distance) if distance is not None else None,
                    "is_open": is_open,
                    "price_level": price_level,
                }
            )

        # Sort by distance
        places.sort(key=lambda p: p.get("distance") or float("inf"))

        return places

    except Exception as e:
        logger.error("Error searching Google Places: %s", e)
        return []


async def search_nearby_restaurants(
    latitude: float,
    longitude: float,
    radius: float = 1000.0,
    max_results: int = 5,
    included_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Search for nearby restaurants using Google Maps API.
    Convenience wrapper around find_nearby_places with restaurant defaults.
    """
    if included_types is None:
        included_types = ["restaurant"]
    return await find_nearby_places(
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        max_results=max_results,
        included_types=included_types,
    )
