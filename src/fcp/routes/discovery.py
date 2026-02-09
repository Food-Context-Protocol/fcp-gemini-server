"""Discovery Routes.

Location-based food discovery endpoints:
- POST /discovery/nearby - Find nearby restaurants/cafes using Google Maps

Security: Input validation ensures coordinates and radius are within valid ranges.
"""

from typing import Any, Literal

from fastapi import Depends
from pydantic import BaseModel, Field, model_validator

from fcp.auth import AuthenticatedUser, require_write_access
from fcp.routes.router import APIRouter
from fcp.routes.schemas import NearbyFoodResponse
from fcp.services.maps import geocode_address
from fcp.tools import find_nearby_food

router = APIRouter()


# --- Request Models ---


class NearbyFoodRequest(BaseModel):
    """Request model for finding nearby food venues.

    Location can be specified via:
    - latitude + longitude (GPS coordinates)
    - location (city name or address string)

    If both are provided, coordinates take precedence.
    """

    latitude: float | None = Field(None, ge=-90, le=90, description="Latitude in degrees")
    longitude: float | None = Field(None, ge=-180, le=180, description="Longitude in degrees")
    location: str | None = Field(
        None,
        min_length=1,
        max_length=500,
        description="City name or address (e.g., 'San Francisco, CA')",
    )
    radius: float = Field(default=2000.0, ge=100, le=50000, description="Search radius in meters")
    food_type: Literal["restaurant", "cafe", "bar", "bakery", "meal_delivery"] = Field(
        default="restaurant", description="Type of food venue to search for"
    )

    @model_validator(mode="after")
    def validate_location_provided(self) -> "NearbyFoodRequest":
        """Ensure either coordinates or location string is provided."""
        has_coords = self.latitude is not None and self.longitude is not None
        has_location = self.location is not None

        if not has_coords and not has_location:
            raise ValueError("Either (latitude, longitude) or location must be provided")

        return self


# --- Routes ---


@router.post("/discovery/nearby", response_model=NearbyFoodResponse)
async def post_nearby_food(
    nearby_request: NearbyFoodRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> NearbyFoodResponse:
    """Find nearby restaurants or cafes using Google Maps."""
    lat = nearby_request.latitude
    lon = nearby_request.longitude
    resolved_location = None

    # If coordinates not provided, geocode the location string
    if lat is None or lon is None:
        # Validator ensures location is set when coords are missing
        location_str = nearby_request.location
        assert location_str is not None
        geocode_result = await geocode_address(location_str)
        if geocode_result is None:
            return NearbyFoodResponse(
                venues=[],
                error="location_not_found",
                message=f"Could not find location: {nearby_request.location}",
            )
        lat = geocode_result.latitude
        lon = geocode_result.longitude
        resolved_location = geocode_result.formatted_address

    venues = await find_nearby_food(
        lat,
        lon,
        nearby_request.radius,
        nearby_request.food_type,
    )

    response_data: dict[str, Any] = {"venues": venues}
    if resolved_location:
        response_data["resolved_location"] = resolved_location
        response_data["coordinates"] = {"latitude": lat, "longitude": lon}

    return NearbyFoodResponse(**response_data)
