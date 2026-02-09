"""Tests for Discovery Routes Module.

Tests for discovery routes including:
- Coordinate validation (latitude, longitude bounds)
- Radius validation (min/max bounds)
- Food type validation (literal type)
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fcp.auth import get_current_user, require_write_access
from fcp.routes.discovery import router
from tests.constants import TEST_USER  # sourcery skip: dont-import-test-modules

# Create test app with discovery router
discovery_test_app = FastAPI()
discovery_test_app.include_router(router)


def mock_get_current_user():
    """Mock auth that returns test user."""
    return TEST_USER


def mock_require_write_access():
    """Mock write access that returns test user."""
    return TEST_USER


@pytest.fixture
def client():
    """Create test client with mocked auth."""
    discovery_test_app.dependency_overrides[get_current_user] = mock_get_current_user
    discovery_test_app.dependency_overrides[require_write_access] = mock_require_write_access
    with TestClient(discovery_test_app) as client:
        yield client
    discovery_test_app.dependency_overrides.clear()


# ============================================
# Coordinate Validation Tests
# ============================================


class TestLatitudeValidation:
    """Tests for latitude parameter validation."""

    def test_valid_latitude_positive(self, client):
        """Test valid positive latitude is accepted."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.post(
                "/discovery/nearby",
                json={"latitude": 47.6, "longitude": -122.3},
            )
            assert response.status_code == 200

    def test_valid_latitude_negative(self, client):
        """Test valid negative latitude is accepted."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.post(
                "/discovery/nearby",
                json={"latitude": -33.9, "longitude": 151.2},
            )
            assert response.status_code == 200

    def test_valid_latitude_boundary_max(self, client):
        """Test latitude at maximum boundary (90) is accepted."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.post(
                "/discovery/nearby",
                json={"latitude": 90, "longitude": 0},
            )
            assert response.status_code == 200

    def test_valid_latitude_boundary_min(self, client):
        """Test latitude at minimum boundary (-90) is accepted."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.post(
                "/discovery/nearby",
                json={"latitude": -90, "longitude": 0},
            )
            assert response.status_code == 200

    def test_invalid_latitude_too_high(self, client):
        """Test latitude above 90 is rejected."""
        response = client.post(
            "/discovery/nearby",
            json={"latitude": 91, "longitude": 0},
        )
        assert response.status_code == 422
        assert "latitude" in response.text.lower()

    def test_invalid_latitude_too_low(self, client):
        """Test latitude below -90 is rejected."""
        response = client.post(
            "/discovery/nearby",
            json={"latitude": -91, "longitude": 0},
        )
        assert response.status_code == 422
        assert "latitude" in response.text.lower()


class TestLongitudeValidation:
    """Tests for longitude parameter validation."""

    def test_valid_longitude_positive(self, client):
        """Test valid positive longitude is accepted."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.post(
                "/discovery/nearby",
                json={"latitude": 0, "longitude": 151.2},
            )
            assert response.status_code == 200

    def test_valid_longitude_negative(self, client):
        """Test valid negative longitude is accepted."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.post(
                "/discovery/nearby",
                json={"latitude": 0, "longitude": -122.3},
            )
            assert response.status_code == 200

    def test_valid_longitude_boundary_max(self, client):
        """Test longitude at maximum boundary (180) is accepted."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.post(
                "/discovery/nearby",
                json={"latitude": 0, "longitude": 180},
            )
            assert response.status_code == 200

    def test_valid_longitude_boundary_min(self, client):
        """Test longitude at minimum boundary (-180) is accepted."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.post(
                "/discovery/nearby",
                json={"latitude": 0, "longitude": -180},
            )
            assert response.status_code == 200

    def test_invalid_longitude_too_high(self, client):
        """Test longitude above 180 is rejected."""
        response = client.post(
            "/discovery/nearby",
            json={"latitude": 0, "longitude": 181},
        )
        assert response.status_code == 422
        assert "longitude" in response.text.lower()

    def test_invalid_longitude_too_low(self, client):
        """Test longitude below -180 is rejected."""
        response = client.post(
            "/discovery/nearby",
            json={"latitude": 0, "longitude": -181},
        )
        assert response.status_code == 422
        assert "longitude" in response.text.lower()


class TestRadiusValidation:
    """Tests for radius parameter validation."""

    def test_valid_radius_default(self, client):
        """Test default radius (2000) is used."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.post(
                "/discovery/nearby",
                json={"latitude": 47.6, "longitude": -122.3},
            )
            assert response.status_code == 200
            mock.assert_called_once()
            call_args = mock.call_args[0]
            assert call_args[2] == 2000.0  # Default radius

    def test_valid_radius_minimum(self, client):
        """Test minimum radius (100) is accepted."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.post(
                "/discovery/nearby",
                json={"latitude": 47.6, "longitude": -122.3, "radius": 100},
            )
            assert response.status_code == 200

    def test_valid_radius_maximum(self, client):
        """Test maximum radius (50000) is accepted."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.post(
                "/discovery/nearby",
                json={"latitude": 47.6, "longitude": -122.3, "radius": 50000},
            )
            assert response.status_code == 200

    def test_invalid_radius_too_small(self, client):
        """Test radius below 100 is rejected."""
        response = client.post(
            "/discovery/nearby",
            json={"latitude": 47.6, "longitude": -122.3, "radius": 50},
        )
        assert response.status_code == 422
        assert "radius" in response.text.lower()

    def test_invalid_radius_too_large(self, client):
        """Test radius above 50000 is rejected."""
        response = client.post(
            "/discovery/nearby",
            json={"latitude": 47.6, "longitude": -122.3, "radius": 60000},
        )
        assert response.status_code == 422
        assert "radius" in response.text.lower()


class TestFoodTypeValidation:
    """Tests for food_type parameter validation."""

    def test_valid_food_type_restaurant(self, client):
        """Test restaurant type is accepted."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.post(
                "/discovery/nearby",
                json={"latitude": 47.6, "longitude": -122.3, "food_type": "restaurant"},
            )
            assert response.status_code == 200

    def test_valid_food_type_cafe(self, client):
        """Test cafe type is accepted."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.post(
                "/discovery/nearby",
                json={"latitude": 47.6, "longitude": -122.3, "food_type": "cafe"},
            )
            assert response.status_code == 200

    def test_valid_food_type_bar(self, client):
        """Test bar type is accepted."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.post(
                "/discovery/nearby",
                json={"latitude": 47.6, "longitude": -122.3, "food_type": "bar"},
            )
            assert response.status_code == 200

    def test_valid_food_type_bakery(self, client):
        """Test bakery type is accepted."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.post(
                "/discovery/nearby",
                json={"latitude": 47.6, "longitude": -122.3, "food_type": "bakery"},
            )
            assert response.status_code == 200

    def test_valid_food_type_meal_delivery(self, client):
        """Test meal_delivery type is accepted."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock:
            mock.return_value = []
            response = client.post(
                "/discovery/nearby",
                json={
                    "latitude": 47.6,
                    "longitude": -122.3,
                    "food_type": "meal_delivery",
                },
            )
            assert response.status_code == 200

    def test_invalid_food_type_rejected(self, client):
        """Test invalid food type is rejected."""
        response = client.post(
            "/discovery/nearby",
            json={"latitude": 47.6, "longitude": -122.3, "food_type": "invalid_type"},
        )
        assert response.status_code == 422
        assert "food_type" in response.text.lower()

    def test_injection_in_food_type_rejected(self, client):
        """Test injection attempt in food type is rejected."""
        response = client.post(
            "/discovery/nearby",
            json={
                "latitude": 47.6,
                "longitude": -122.3,
                "food_type": "restaurant; DROP TABLE users;",
            },
        )
        assert response.status_code == 422


# ============================================
# Location String Tests
# ============================================


class TestLocationStringValidation:
    """Tests for location string parameter (geocoding)."""

    def test_location_string_accepted(self, client):
        """Test location string as alternative to coordinates."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock_find:
            with patch("fcp.routes.discovery.geocode_address", new_callable=AsyncMock) as mock_geo:
                from fcp.services.maps import GeocodingResult

                mock_geo.return_value = GeocodingResult(
                    latitude=37.7749,
                    longitude=-122.4194,
                    formatted_address="San Francisco, CA, USA",
                )
                mock_find.return_value = [{"name": "Test Restaurant"}]

                response = client.post(
                    "/discovery/nearby",
                    json={"location": "San Francisco, CA"},
                )
                assert response.status_code == 200
                data = response.json()
                assert data["resolved_location"] == "San Francisco, CA, USA"
                assert data["coordinates"]["latitude"] == 37.7749
                assert len(data["venues"]) == 1

    def test_location_not_found_returns_error(self, client):
        """Test location not found returns error with empty venues."""
        with patch("fcp.routes.discovery.geocode_address", new_callable=AsyncMock) as mock_geo:
            mock_geo.return_value = None

            response = client.post(
                "/discovery/nearby",
                json={"location": "xyznotarealplace123"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["error"] == "location_not_found"
            assert data["venues"] == []

    def test_coordinates_take_precedence_over_location(self, client):
        """Test that coordinates are used when both are provided."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = []

            response = client.post(
                "/discovery/nearby",
                json={
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "location": "San Francisco, CA",
                },
            )
            assert response.status_code == 200
            # Geocoding should not be called when coords provided
            mock_find.assert_called_once()
            call_args = mock_find.call_args
            assert call_args[0][0] == 40.7128  # latitude
            assert call_args[0][1] == -74.0060  # longitude

    def test_neither_coords_nor_location_rejected(self, client):
        """Test request rejected when neither coords nor location provided."""
        response = client.post(
            "/discovery/nearby",
            json={"radius": 1000},
        )
        assert response.status_code == 422

    def test_location_with_radius_and_food_type(self, client):
        """Test location with optional parameters."""
        with patch("fcp.routes.discovery.find_nearby_food", new_callable=AsyncMock) as mock_find:
            with patch("fcp.routes.discovery.geocode_address", new_callable=AsyncMock) as mock_geo:
                from fcp.services.maps import GeocodingResult

                mock_geo.return_value = GeocodingResult(
                    latitude=37.7749,
                    longitude=-122.4194,
                    formatted_address="San Francisco, CA, USA",
                )
                mock_find.return_value = []

                response = client.post(
                    "/discovery/nearby",
                    json={
                        "location": "San Francisco",
                        "radius": 5000,
                        "food_type": "cafe",
                    },
                )
                assert response.status_code == 200
                mock_find.assert_called_once_with(37.7749, -122.4194, 5000, "cafe")

    def test_empty_location_rejected(self, client):
        """Test empty location string is rejected."""
        response = client.post(
            "/discovery/nearby",
            json={"location": ""},
        )
        assert response.status_code == 422

    def test_location_too_long_rejected(self, client):
        """Test location string over 500 chars is rejected."""
        response = client.post(
            "/discovery/nearby",
            json={"location": "a" * 501},
        )
        assert response.status_code == 422
