"""Tests for Google Maps integration."""

import httpx
import pytest
import respx

from fcp.services.maps import (
    GEOCODING_API_URL,
    PLACES_API_URL,
    GeocodingResult,
    find_nearby_places,
    geocode_address,
    haversine_distance,
    search_nearby_restaurants,
)
from fcp.tools.discovery import find_nearby_food


class TestHaversineDistance:
    """Tests for the Haversine distance calculation."""

    def test_same_point_returns_zero(self):
        """Distance from a point to itself should be zero."""
        result = haversine_distance(37.7749, -122.4194, 37.7749, -122.4194)
        assert result == 0.0

    def test_known_distance_sf_to_oakland(self):
        """Test with known distance between SF and Oakland (~13km)."""
        # San Francisco
        sf_lat, sf_lon = 37.7749, -122.4194
        # Oakland
        oak_lat, oak_lon = 37.8044, -122.2712

        result = haversine_distance(sf_lat, sf_lon, oak_lat, oak_lon)

        # Distance should be approximately 13km (13000m)
        assert 12000 < result < 15000

    def test_known_distance_nyc_to_la(self):
        """Test with known distance between NYC and LA (~3940km)."""
        # New York City
        nyc_lat, nyc_lon = 40.7128, -74.0060
        # Los Angeles
        la_lat, la_lon = 34.0522, -118.2437

        result = haversine_distance(nyc_lat, nyc_lon, la_lat, la_lon)

        # Distance should be approximately 3940km
        assert 3900000 < result < 4000000

    def test_equator_distance(self):
        """Test distance along the equator (1 degree ~ 111km)."""
        result = haversine_distance(0, 0, 0, 1)

        # One degree of longitude at equator is ~111km
        assert 110000 < result < 112000

    def test_symmetry(self):
        """Distance from A to B should equal distance from B to A."""
        lat1, lon1 = 37.7749, -122.4194
        lat2, lon2 = 40.7128, -74.0060

        dist_ab = haversine_distance(lat1, lon1, lat2, lon2)
        dist_ba = haversine_distance(lat2, lon2, lat1, lon1)

        assert dist_ab == dist_ba


@pytest.mark.asyncio
@respx.mock
async def test_search_nearby_restaurants_success():
    """Test successful restaurant search."""
    # Mock coordinates
    lat, lng = 37.7749, -122.4194

    mock_response = {
        "places": [
            {
                "displayName": {"text": "Tasty Tacos"},
                "formattedAddress": "123 Main St, San Francisco, CA",
                "rating": 4.5,
                "userRatingCount": 100,
                "id": "place123",
            }
        ]
    }

    respx.post(PLACES_API_URL).mock(return_value=httpx.Response(200, json=mock_response))

    # We need to set a dummy API key for the test
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GOOGLE_MAPS_API_KEY", "test-key")
        result = await search_nearby_restaurants(lat, lng)

    assert len(result) == 1
    assert result[0]["name"] == "Tasty Tacos"
    assert result[0]["source"] == "Google Maps"


@pytest.mark.asyncio
@respx.mock
async def test_search_nearby_restaurants_with_location_data():
    """Test restaurant search returns location and distance data."""
    lat, lng = 37.7749, -122.4194

    mock_response = {
        "places": [
            {
                "displayName": {"text": "Nearby Cafe"},
                "formattedAddress": "456 Oak St, San Francisco, CA",
                "rating": 4.2,
                "userRatingCount": 50,
                "id": "place456",
                "location": {"latitude": 37.7760, "longitude": -122.4180},
                "priceLevel": "PRICE_LEVEL_MODERATE",
                "regularOpeningHours": {"openNow": True},
            }
        ]
    }

    respx.post(PLACES_API_URL).mock(return_value=httpx.Response(200, json=mock_response))

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GOOGLE_MAPS_API_KEY", "test-key")
        result = await search_nearby_restaurants(lat, lng)

    assert len(result) == 1
    place = result[0]
    assert place["name"] == "Nearby Cafe"
    assert place["latitude"] == 37.7760
    assert place["longitude"] == -122.4180
    assert place["is_open"] is True
    assert place["price_level"] == 3  # MODERATE = 3 (on 1-5 scale)
    assert place["distance"] is not None
    assert place["distance"] < 500  # Should be close


@pytest.mark.asyncio
@respx.mock
async def test_search_nearby_restaurants_price_level_mapping():
    """Test price level string to int mapping (1-5 scale)."""
    lat, lng = 37.7749, -122.4194

    mock_response = {
        "places": [
            {
                "displayName": {"text": "Free Spot"},
                "id": "p1",
                "priceLevel": "PRICE_LEVEL_FREE",
            },
            {
                "displayName": {"text": "Cheap Spot"},
                "id": "p2",
                "priceLevel": "PRICE_LEVEL_INEXPENSIVE",
            },
            {
                "displayName": {"text": "Medium Spot"},
                "id": "p3",
                "priceLevel": "PRICE_LEVEL_MODERATE",
            },
            {
                "displayName": {"text": "Fancy Spot"},
                "id": "p4",
                "priceLevel": "PRICE_LEVEL_EXPENSIVE",
            },
            {
                "displayName": {"text": "Ultra Fancy"},
                "id": "p5",
                "priceLevel": "PRICE_LEVEL_VERY_EXPENSIVE",
            },
            {
                "displayName": {"text": "Unknown Price"},
                "id": "p6",
                "priceLevel": "PRICE_LEVEL_UNKNOWN",
            },
            {
                "displayName": {"text": "No Price Info"},
                "id": "p7",
            },
        ]
    }

    respx.post(PLACES_API_URL).mock(return_value=httpx.Response(200, json=mock_response))

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GOOGLE_MAPS_API_KEY", "test-key")
        result = await search_nearby_restaurants(lat, lng, max_results=10)

    # Test 1-5 scale mapping
    assert result[0]["price_level"] == 1  # FREE
    assert result[1]["price_level"] == 2  # INEXPENSIVE
    assert result[2]["price_level"] == 3  # MODERATE
    assert result[3]["price_level"] == 4  # EXPENSIVE
    assert result[4]["price_level"] == 5  # VERY_EXPENSIVE
    # Unknown/missing values should be None
    assert result[5]["price_level"] is None  # UNKNOWN
    assert result[6]["price_level"] is None  # Missing


@pytest.mark.asyncio
@respx.mock
async def test_search_nearby_restaurants_missing_location():
    """Test handling of places without location data."""
    lat, lng = 37.7749, -122.4194

    mock_response = {
        "places": [
            {
                "displayName": {"text": "No Location Place"},
                "id": "p1",
            }
        ]
    }

    respx.post(PLACES_API_URL).mock(return_value=httpx.Response(200, json=mock_response))

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GOOGLE_MAPS_API_KEY", "test-key")
        result = await search_nearby_restaurants(lat, lng)

    assert len(result) == 1
    assert result[0]["latitude"] is None
    assert result[0]["longitude"] is None
    assert result[0]["distance"] is None


@pytest.mark.asyncio
@respx.mock
async def test_search_nearby_restaurants_sorted_by_distance():
    """Test results are sorted by distance."""
    lat, lng = 37.7749, -122.4194

    mock_response = {
        "places": [
            {
                "displayName": {"text": "Far Away"},
                "id": "p1",
                "location": {"latitude": 37.8000, "longitude": -122.4000},
            },
            {
                "displayName": {"text": "Very Close"},
                "id": "p2",
                "location": {"latitude": 37.7750, "longitude": -122.4190},
            },
            {
                "displayName": {"text": "Medium Distance"},
                "id": "p3",
                "location": {"latitude": 37.7800, "longitude": -122.4100},
            },
        ]
    }

    respx.post(PLACES_API_URL).mock(return_value=httpx.Response(200, json=mock_response))

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GOOGLE_MAPS_API_KEY", "test-key")
        result = await search_nearby_restaurants(lat, lng, max_results=10)

    # Should be sorted by distance
    assert result[0]["name"] == "Very Close"
    assert result[1]["name"] == "Medium Distance"
    assert result[2]["name"] == "Far Away"


@pytest.mark.asyncio
@respx.mock
async def test_search_nearby_restaurants_no_api_key():
    """Test graceful handling when API key is not set."""
    lat, lng = 37.7749, -122.4194

    with pytest.MonkeyPatch.context() as mp:
        mp.delenv("GOOGLE_MAPS_API_KEY", raising=False)
        result = await search_nearby_restaurants(lat, lng)

    assert result == []


@pytest.mark.asyncio
@respx.mock
async def test_search_nearby_restaurants_api_error():
    """Test handling of API errors."""
    lat, lng = 37.7749, -122.4194

    respx.post(PLACES_API_URL).mock(return_value=httpx.Response(500, json={"error": "Server error"}))

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GOOGLE_MAPS_API_KEY", "test-key")
        result = await search_nearby_restaurants(lat, lng)

    assert result == []


@pytest.mark.asyncio
@respx.mock
async def test_find_nearby_places_custom_types():
    """Test find_nearby_places with custom included types."""
    lat, lng = 37.7749, -122.4194

    mock_response = {"places": []}
    route = respx.post(PLACES_API_URL).mock(return_value=httpx.Response(200, json=mock_response))

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GOOGLE_MAPS_API_KEY", "test-key")
        await find_nearby_places(lat, lng, included_types=["cafe", "bakery"])

    # Verify the request body included custom types
    assert route.called
    request_body = route.calls[0].request.content
    assert b"cafe" in request_body
    assert b"bakery" in request_body


@pytest.mark.asyncio
@respx.mock
async def test_find_nearby_food_tool():
    """Test the discovery tool wrapper."""
    lat, lng = 37.7749, -122.4194

    # Use a simpler mock for the underlying service call
    mock_response = {"places": []}
    respx.post(PLACES_API_URL).mock(return_value=httpx.Response(200, json=mock_response))

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("GOOGLE_MAPS_API_KEY", "test-key")
        result = await find_nearby_food(lat, lng)
        assert isinstance(result, list)


# ============================================
# Geocoding Tests
# ============================================


class TestGeocodeAddress:
    """Tests for geocode_address function."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_geocode_valid_city(self):
        """Test geocoding a valid city name."""
        mock_response = {
            "status": "OK",
            "results": [
                {
                    "geometry": {"location": {"lat": 37.7749, "lng": -122.4194}},
                    "formatted_address": "San Francisco, CA, USA",
                    "place_id": "ChIJIQBpAG2ahYAR_6128GcTUEo",
                }
            ],
        }
        respx.get(GEOCODING_API_URL).mock(return_value=httpx.Response(200, json=mock_response))

        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("GOOGLE_MAPS_API_KEY", "test-key")
            result = await geocode_address("San Francisco, CA")

        assert result is not None
        assert isinstance(result, GeocodingResult)
        assert abs(result.latitude - 37.7749) < 0.001
        assert abs(result.longitude - (-122.4194)) < 0.001
        assert result.formatted_address == "San Francisco, CA, USA"

    @pytest.mark.asyncio
    @respx.mock
    async def test_geocode_invalid_location_returns_none(self):
        """Test geocoding returns None for invalid location."""
        mock_response = {"status": "ZERO_RESULTS", "results": []}
        respx.get(GEOCODING_API_URL).mock(return_value=httpx.Response(200, json=mock_response))

        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("GOOGLE_MAPS_API_KEY", "test-key")
            result = await geocode_address("xyznotarealplace123")

        assert result is None

    @pytest.mark.asyncio
    async def test_geocode_empty_address_raises(self):
        """Test geocoding raises ValueError for empty address."""
        with pytest.raises(ValueError, match="Address cannot be empty"):
            await geocode_address("")

    @pytest.mark.asyncio
    async def test_geocode_whitespace_only_raises(self):
        """Test geocoding raises ValueError for whitespace-only address."""
        with pytest.raises(ValueError, match="Address cannot be empty"):
            await geocode_address("   ")

    @pytest.mark.asyncio
    async def test_geocode_no_api_key_returns_none(self):
        """Test geocoding returns None when API key not configured."""
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("GOOGLE_MAPS_API_KEY", raising=False)
            result = await geocode_address("San Francisco")

        assert result is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_geocode_api_error_returns_none(self):
        """Test geocoding returns None on API error."""
        respx.get(GEOCODING_API_URL).mock(return_value=httpx.Response(500))

        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("GOOGLE_MAPS_API_KEY", "test-key")
            result = await geocode_address("San Francisco")

        assert result is None


class TestFindNearbyFoodWithLocation:
    """Tests for find_nearby_food with location string."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_find_nearby_food_with_location(self):
        """Test find_nearby_food accepts location string."""
        # Mock geocoding
        geocode_response = {
            "status": "OK",
            "results": [
                {
                    "geometry": {"location": {"lat": 37.7749, "lng": -122.4194}},
                    "formatted_address": "San Francisco, CA, USA",
                }
            ],
        }
        respx.get(GEOCODING_API_URL).mock(return_value=httpx.Response(200, json=geocode_response))

        # Mock places search
        places_response = {"places": []}
        respx.post(PLACES_API_URL).mock(return_value=httpx.Response(200, json=places_response))

        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("GOOGLE_MAPS_API_KEY", "test-key")
            result = await find_nearby_food(location="San Francisco, CA")

        assert isinstance(result, list)

    @pytest.mark.asyncio
    @respx.mock
    async def test_find_nearby_food_location_not_found(self):
        """Test find_nearby_food returns empty list when location not found."""
        geocode_response = {"status": "ZERO_RESULTS", "results": []}
        respx.get(GEOCODING_API_URL).mock(return_value=httpx.Response(200, json=geocode_response))

        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("GOOGLE_MAPS_API_KEY", "test-key")
            result = await find_nearby_food(location="xyznotarealplace")

        assert result == []

    @pytest.mark.asyncio
    async def test_find_nearby_food_no_location_or_coords_raises(self):
        """Test find_nearby_food raises when neither location nor coords provided."""
        with pytest.raises(ValueError, match="Either.*latitude.*longitude.*location"):
            await find_nearby_food()
