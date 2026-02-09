"""Tests for routes/schemas.py shared schemas."""

import pytest
from pydantic import ValidationError

from fcp.routes.schemas import (
    ActionResponse,
    DependencyHealthResponse,
    ImageAnalysisResponse,
    ImageURLRequest,
    MealListResponse,
    MealLog,
    NearbyFoodResponse,
    ReadinessResponse,
    SearchResponse,
    StatusResponse,
)


class TestNearbyFoodResponse:
    """Ensure the NearbyFoodResponse model captures optional metadata."""

    def test_coordinates_optional_fields(self):
        """Coordinates only appear when included in the response data."""
        response = NearbyFoodResponse(
            venues=[{"name": "Cafe"}],
            resolved_location="Oakland, CA",
            coordinates={"latitude": 37.8, "longitude": -122.3},
        )

        assert response.venues[0]["name"] == "Cafe"
        assert response.coordinates is not None
        assert response.coordinates.latitude == 37.8
        assert response.coordinates.longitude == -122.3

    def test_coordinates_can_be_omitted(self):
        """Venue results can omit optional metadata while still validating."""
        response = NearbyFoodResponse(venues=[{"name": "Garden"}])

        assert response.coordinates is None
        assert response.resolved_location is None


class TestImageAnalysisResponse:
    """Ensure the shared image analysis response model behaves predictably."""

    def test_optional_fields_default_to_none(self):
        """Fields like method, version, and thinking_level default to None."""
        response = ImageAnalysisResponse(analysis={"dish": "toast"})
        assert response.analysis["dish"] == "toast"
        assert response.method is None
        assert response.version is None
        assert response.thinking_level is None

    def test_fields_can_be_populated(self):
        """Custom metadata is preserved when provided."""
        response = ImageAnalysisResponse(
            analysis={"dish": "ramen"},
            method="vibing",
            version="v1",
            thinking_level="low",
        )

        assert response.method == "vibing"
        assert response.version == "v1"
        assert response.thinking_level == "low"


class TestHealthSchemas:
    """Ensure status and health response models behave as expected."""

    def test_status_response_models_ok(self):
        response = StatusResponse(status="ok")
        assert response.status == "ok"

    def test_readiness_response_carries_checks(self):
        response = ReadinessResponse(status="degraded", checks={"gemini_api_key": False})
        assert response.checks["gemini_api_key"] is False

    def test_dependency_health_response_includes_request_id(self):
        response = DependencyHealthResponse(
            status="healthy",
            checks={"gemini": {"healthy": True}},
            request_id="req-123",
        )
        assert response.request_id == "req-123"


class TestMealSchemas:
    """Ensure meal-related schemas serialize/parse expected fields."""

    def test_meal_log_can_be_partial(self):
        log = MealLog(dish_name="Tacos")
        assert log.dish_name == "Tacos"
        assert log.updated_at is None

    def test_meal_list_response_reflects_length(self):
        entries = [MealLog(log_id="1"), MealLog(log_id="2")]
        response = MealListResponse(meals=entries, count=len(entries))
        assert response.count == 2
        assert response.meals[1].log_id == "2"

    def test_action_response_accepts_optional_metadata(self):
        response = ActionResponse(success=True, analysis={"score": 1}, storage_note="stored")
        assert response.analysis == {"score": 1}
        assert response.storage_note == "stored"

    def test_action_response_model_dump_removes_empty_storage_note(self):
        response = ActionResponse(success=True, dish_name="test")
        data = response.model_dump()
        assert "storage_note" not in data

    def test_action_response_model_dump_preserves_storage_note(self):
        response = ActionResponse(success=True, storage_note="note")
        data = response.model_dump()
        assert data["storage_note"] == "note"

    def test_search_response_preserves_query(self):
        response = SearchResponse(results=[{"dish_name": "soup"}], query="soup")
        assert response.query == "soup"
        assert response.results[0]["dish_name"] == "soup"


class TestImageURLRequest:
    """Tests for ImageURLRequest model."""

    def test_valid_firebase_storage_url(self):
        """Test valid Firebase Storage URL."""
        request = ImageURLRequest(image_url="https://firebasestorage.googleapis.com/v0/b/bucket/o/image.jpg")
        assert request.image_url.startswith("https://firebasestorage")

    def test_valid_gcs_url(self):
        """Test valid Google Cloud Storage URL."""
        request = ImageURLRequest(image_url="https://storage.googleapis.com/bucket/image.jpg")
        assert "storage.googleapis.com" in request.image_url

    def test_valid_cloudinary_url(self):
        """Test valid Cloudinary URL."""
        request = ImageURLRequest(image_url="https://res.cloudinary.com/demo/image/upload/sample.jpg")
        assert "cloudinary" in request.image_url

    def test_valid_unsplash_url(self):
        """Test valid Unsplash URL."""
        request = ImageURLRequest(image_url="https://images.unsplash.com/photo-123")
        assert "unsplash" in request.image_url

    def test_empty_url_fails(self):
        """Test that empty URL fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            ImageURLRequest(image_url="")

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_invalid_url_scheme_fails(self):
        """Test that invalid URL scheme fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            ImageURLRequest(image_url="ftp://example.com/image.jpg")

        # The error comes from url_validator
        assert "ftp://" in str(exc_info.value) or "not allowed" in str(exc_info.value)

    def test_file_url_fails(self):
        """Test that file:// URL fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            ImageURLRequest(image_url="file:///etc/passwd")

        assert "file://" in str(exc_info.value) or "not allowed" in str(exc_info.value)

    def test_data_url_fails(self):
        """Test that data: URL fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            ImageURLRequest(image_url="data:image/png;base64,abc123")

        assert "data:" in str(exc_info.value) or "not allowed" in str(exc_info.value)

    def test_private_ip_fails(self):
        """Test that private IP addresses fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            ImageURLRequest(image_url="https://192.168.1.1/image.jpg")

        assert "private" in str(exc_info.value).lower() or "not allowed" in str(exc_info.value).lower()

    def test_metadata_url_fails(self):
        """Test that cloud metadata URLs fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            ImageURLRequest(image_url="http://169.254.169.254/latest/meta-data/")

        error_str = str(exc_info.value).lower()
        assert "not allowed" in error_str or "private" in error_str or "169.254" in error_str

    def test_localhost_allowed_in_dev(self):
        """Test that localhost is allowed in non-production."""
        # localhost is in the allowed domains list for development
        request = ImageURLRequest(image_url="http://localhost:8080/image.jpg")
        assert "localhost" in request.image_url

    def test_url_too_long_fails(self):
        """Test that overly long URL fails validation."""
        long_url = "https://firebasestorage.googleapis.com/" + "a" * 2500
        with pytest.raises(ValidationError) as exc_info:
            ImageURLRequest(image_url=long_url)

        assert "at most 2000" in str(exc_info.value)

    def test_disallowed_domain_fails(self):
        """Test that disallowed domain fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            ImageURLRequest(image_url="https://evil-site.com/image.jpg")

        assert "not in the allowed list" in str(exc_info.value) or "Domain" in str(exc_info.value)

    def test_url_with_credentials_fails(self):
        """Test that URL with credentials fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            ImageURLRequest(image_url="https://user:pass@firebasestorage.googleapis.com/image.jpg")

        assert "credentials" in str(exc_info.value).lower()
