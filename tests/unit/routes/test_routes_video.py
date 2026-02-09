"""Tests for video generation route endpoints."""

import base64
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from fcp.auth.permissions import AuthenticatedUser, UserRole
from tests.constants import TEST_AUTH_HEADER, TEST_USER_ID  # sourcery skip: dont-import-test-modules


@pytest.fixture
def client():
    """Create test client with mocked dependencies."""
    from fcp.api import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_auth():
    """Mock authentication to return test user."""
    from fcp.api import app
    from fcp.auth.local import get_current_user
    from fcp.auth.permissions import require_write_access

    user = AuthenticatedUser(user_id=TEST_USER_ID, role=UserRole.AUTHENTICATED)

    async def override_get_current_user(authorization=None):
        return user

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_write_access] = override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_write_access, None)


class TestRecipeVideoEndpoint:
    """Tests for /video/recipe endpoint."""

    def test_recipe_video_success(self, client, mock_auth):
        """Test successful recipe video generation."""
        with patch("fcp.routes.video.generate_recipe_video", new_callable=AsyncMock) as mock_video:
            mock_video.return_value = {
                "status": "completed",
                "video_bytes": b"fake_video_data",
                "duration": 8,
                "dish_name": "Spaghetti Carbonara",
                "style": "cinematic",
            }

            response = client.post(
                "/video/recipe",
                json={"dish_name": "Spaghetti Carbonara"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["dish_name"] == "Spaghetti Carbonara"
            assert data["style"] == "cinematic"
            assert data["duration"] == 8
            # Video bytes should be base64 encoded
            expected_b64 = base64.b64encode(b"fake_video_data").decode("utf-8")
            assert data["video_base64"] == expected_b64

    def test_recipe_video_with_options(self, client, mock_auth):
        """Test recipe video with custom options."""
        with patch("fcp.routes.video.generate_recipe_video", new_callable=AsyncMock) as mock_video:
            mock_video.return_value = {
                "status": "completed",
                "video_bytes": b"video_data",
                "duration": 4,
                "dish_name": "Pizza",
                "style": "social",
            }

            response = client.post(
                "/video/recipe",
                json={
                    "dish_name": "Pizza",
                    "description": "Close-up of melting cheese",
                    "style": "social",
                    "duration_seconds": 4,
                    "aspect_ratio": "9:16",
                    "timeout_seconds": 400,
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["style"] == "social"

            # Verify all params were passed
            call_args = mock_video.call_args.kwargs
            assert call_args["dish_name"] == "Pizza"
            assert call_args["description"] == "Close-up of melting cheese"
            assert call_args["style"] == "social"
            assert call_args["duration_seconds"] == 4
            assert call_args["aspect_ratio"] == "9:16"
            assert call_args["timeout_seconds"] == 400

    def test_recipe_video_timeout_status(self, client, mock_auth):
        """Test recipe video that times out."""
        with patch("fcp.routes.video.generate_recipe_video", new_callable=AsyncMock) as mock_video:
            mock_video.return_value = {
                "status": "timeout",
                "dish_name": "Steak",
                "operation_name": "op_123",
                "message": "Video still generating after 300s.",
            }

            response = client.post(
                "/video/recipe",
                json={"dish_name": "Steak"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "timeout"
            assert data["operation_name"] == "op_123"
            assert "Video still generating" in data["message"]

    def test_recipe_video_failed_status(self, client, mock_auth):
        """Test recipe video that fails."""
        with patch("fcp.routes.video.generate_recipe_video", new_callable=AsyncMock) as mock_video:
            mock_video.return_value = {
                "status": "failed",
                "dish_name": "Salad",
                "message": "Generation failed",
            }

            response = client.post(
                "/video/recipe",
                json={"dish_name": "Salad"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "failed"
            assert data["message"] == "Generation failed"

    def test_recipe_video_api_not_configured(self, client, mock_auth):
        """Test recipe video when API key is not configured."""
        with patch("fcp.routes.video.generate_recipe_video", new_callable=AsyncMock) as mock_video:
            mock_video.side_effect = RuntimeError("GEMINI_API_KEY not configured")

            response = client.post(
                "/video/recipe",
                json={"dish_name": "Test"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 503
            data = response.json()
            assert "Video service unavailable" in data.get("detail", str(data))

    def test_recipe_video_generic_exception(self, client, mock_auth):
        """Test recipe video with unexpected exception."""
        with patch("fcp.routes.video.generate_recipe_video", new_callable=AsyncMock) as mock_video:
            mock_video.side_effect = Exception("Unexpected error")

            response = client.post(
                "/video/recipe",
                json={"dish_name": "Test"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 500
            data = response.json()
            assert "Video generation failed" in data.get("detail", str(data))

    def test_recipe_video_requires_auth(self, client):
        """Test that recipe video endpoint requires authentication."""
        response = client.post(
            "/video/recipe",
            json={"dish_name": "Test"},
        )
        assert response.status_code == 403  # Demo users get 403 for write endpoints


class TestCookingClipEndpoint:
    """Tests for /video/clip endpoint."""

    def test_cooking_clip_success(self, client, mock_auth):
        """Test successful cooking clip generation."""
        with patch("fcp.routes.video.generate_cooking_clip", new_callable=AsyncMock) as mock_clip:
            mock_clip.return_value = {
                "status": "completed",
                "video_bytes": b"clip_data",
                "duration": 8,
                "action": "chopping vegetables",
            }

            response = client.post(
                "/video/clip",
                json={"action": "chopping vegetables"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["action"] == "chopping vegetables"
            assert data["video_base64"] is not None

    def test_cooking_clip_with_ingredients(self, client, mock_auth):
        """Test cooking clip with ingredients."""
        with patch("fcp.routes.video.generate_cooking_clip", new_callable=AsyncMock) as mock_clip:
            mock_clip.return_value = {
                "status": "completed",
                "video_bytes": b"data",
                "duration": 4,
                "action": "sautéing",
            }

            response = client.post(
                "/video/clip",
                json={
                    "action": "sautéing",
                    "ingredients": ["onions", "garlic", "peppers"],
                    "duration_seconds": 4,
                    "timeout_seconds": 180,
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

            # Verify params were passed
            call_args = mock_clip.call_args.kwargs
            assert call_args["action"] == "sautéing"
            assert call_args["ingredients"] == ["onions", "garlic", "peppers"]
            assert call_args["duration_seconds"] == 4
            assert call_args["timeout_seconds"] == 180

    def test_cooking_clip_timeout_status(self, client, mock_auth):
        """Test cooking clip that times out."""
        with patch("fcp.routes.video.generate_cooking_clip", new_callable=AsyncMock) as mock_clip:
            mock_clip.return_value = {
                "status": "timeout",
                "action": "flipping",
                "operation_name": "op_456",
                "message": "Clip still generating",
            }

            response = client.post(
                "/video/clip",
                json={"action": "flipping"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "timeout"

    def test_cooking_clip_api_not_configured(self, client, mock_auth):
        """Test cooking clip when API key is not configured."""
        with patch("fcp.routes.video.generate_cooking_clip", new_callable=AsyncMock) as mock_clip:
            mock_clip.side_effect = RuntimeError("GEMINI_API_KEY not configured")

            response = client.post(
                "/video/clip",
                json={"action": "Test action"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 503
            data = response.json()
            assert "Video service unavailable" in data.get("detail", str(data))

    def test_cooking_clip_generic_exception(self, client, mock_auth):
        """Test cooking clip with unexpected exception."""
        with patch("fcp.routes.video.generate_cooking_clip", new_callable=AsyncMock) as mock_clip:
            mock_clip.side_effect = Exception("Unexpected error")

            response = client.post(
                "/video/clip",
                json={"action": "Test action"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 500
            data = response.json()
            assert "Clip generation failed" in data.get("detail", str(data))

    def test_cooking_clip_requires_auth(self, client):
        """Test that cooking clip endpoint requires authentication."""
        response = client.post(
            "/video/clip",
            json={"action": "test"},
        )
        assert response.status_code == 403  # Demo users get 403 for write endpoints


class TestRecipeVideoRawEndpoint:
    """Tests for /video/recipe/raw endpoint."""

    def test_recipe_video_raw_success(self, client, mock_auth):
        """Test successful raw video response."""
        with patch("fcp.routes.video.generate_recipe_video", new_callable=AsyncMock) as mock_video:
            mock_video.return_value = {
                "status": "completed",
                "video_bytes": b"raw_video_bytes",
                "duration": 8,
            }

            response = client.post(
                "/video/recipe/raw",
                json={"dish_name": "Pasta"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "video/mp4"
            assert b"raw_video_bytes" in response.content

    def test_recipe_video_raw_not_completed(self, client, mock_auth):
        """Test raw video when generation times out."""
        with patch("fcp.routes.video.generate_recipe_video", new_callable=AsyncMock) as mock_video:
            mock_video.return_value = {
                "status": "timeout",
                "message": "Video generation timed out",
            }

            response = client.post(
                "/video/recipe/raw",
                json={"dish_name": "Pasta"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 504
            data = response.json()
            # Check either FastAPI detail or custom error format
            error_msg = data.get("detail") or data.get("error", {}).get("message", "")
            assert "Video generation" in error_msg or "did not complete" in error_msg

    def test_recipe_video_raw_no_video_bytes(self, client, mock_auth):
        """Test raw video when no video bytes returned."""
        with patch("fcp.routes.video.generate_recipe_video", new_callable=AsyncMock) as mock_video:
            mock_video.return_value = {
                "status": "completed",
                "video_bytes": None,
            }

            response = client.post(
                "/video/recipe/raw",
                json={"dish_name": "Pasta"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 504

    def test_recipe_video_raw_api_not_configured(self, client, mock_auth):
        """Test raw video when API key is not configured."""
        with patch("fcp.routes.video.generate_recipe_video", new_callable=AsyncMock) as mock_video:
            mock_video.side_effect = RuntimeError("GEMINI_API_KEY not configured")

            response = client.post(
                "/video/recipe/raw",
                json={"dish_name": "Test"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 503

    def test_recipe_video_raw_generic_exception(self, client, mock_auth):
        """Test raw video with unexpected exception."""
        with patch("fcp.routes.video.generate_recipe_video", new_callable=AsyncMock) as mock_video:
            mock_video.side_effect = Exception("Unexpected error")

            response = client.post(
                "/video/recipe/raw",
                json={"dish_name": "Test"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 500

    def test_recipe_video_raw_requires_auth(self, client):
        """Test that raw video endpoint requires authentication."""
        response = client.post(
            "/video/recipe/raw",
            json={"dish_name": "Test"},
        )
        assert response.status_code == 403  # Demo users get 403 for write endpoints
