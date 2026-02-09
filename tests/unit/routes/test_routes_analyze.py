"""Tests for routes/analyze.py endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from fcp.api import app
from fcp.auth.permissions import AuthenticatedUser, UserRole
from tests.constants import TEST_AUTH_HEADER, TEST_USER_ID

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _close_client():
    """Ensure the shared TestClient is properly closed."""
    yield
    client.close()


@pytest.fixture
def mock_auth():
    """Mock authentication to return test user."""
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


class TestAnalyzeImageEndpoint:
    """Tests for POST /analyze endpoint."""

    def test_analyze_image_success(self, mock_auth):
        """Test basic image analysis."""
        mock_result = {
            "dish_name": "Ramen",
            "cuisine": "Japanese",
            "ingredients": ["noodles", "pork", "egg"],
        }

        with patch("fcp.routes.analyze.analyze_meal", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result

            response = client.post(
                "/analyze",
                json={"image_url": "https://firebasestorage.googleapis.com/ramen.jpg"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert "analysis" in data
            assert data["analysis"]["dish_name"] == "Ramen"


class TestAnalyzeImageStreamEndpoint:
    """Tests for POST /analyze/stream endpoint."""

    def test_analyze_stream_success(self, mock_auth):
        """Test streaming image analysis."""

        async def mock_stream(prompt, image_url=None):
            yield "Analyzing the image..."
            yield " This appears to be ramen."
            yield " It contains noodles and pork."

        from fcp.services.gemini import get_gemini

        with patch("fcp.routes.analyze.PROMPTS", {"analyze_meal": "Analyze this food image"}):
            mock_gemini = AsyncMock()
            mock_gemini.generate_content_stream = mock_stream
            app.dependency_overrides[get_gemini] = lambda: mock_gemini
            try:
                response = client.post(
                    "/analyze/stream",
                    json={"image_url": "https://firebasestorage.googleapis.com/ramen.jpg"},
                    headers=TEST_AUTH_HEADER,
                )

                assert response.status_code == 200
                # Streaming response returns SSE content with all mocked chunks
                content = response.content.decode()
                assert "Analyzing the image..." in content
                assert "This appears to be ramen" in content
                assert "noodles and pork" in content
            finally:
                app.dependency_overrides.pop(get_gemini, None)


class TestAnalyzeImageV2Endpoint:
    """Tests for POST /analyze/v2 endpoint."""

    def test_analyze_v2_success(self, mock_auth):
        """Test v2 analysis with function calling."""
        mock_result = {
            "dish_name": "Pad Thai",
            "cuisine": "Thai",
            "nutrition": {"calories": 500},
        }

        with patch("fcp.routes.analyze.analyze_meal_v2", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result

            response = client.post(
                "/analyze/v2",
                json={"image_url": "https://firebasestorage.googleapis.com/padthai.jpg"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["version"] == "v2"
            assert data["method"] == "function_calling"
            assert data["analysis"]["dish_name"] == "Pad Thai"


class TestAnalyzeImageThinkingEndpoint:
    """Tests for POST /analyze/thinking endpoint."""

    def test_analyze_thinking_default_level(self, mock_auth):
        """Test analysis with thinking mode (default high level)."""
        mock_result = {
            "dish_name": "Complex Multi-course Meal",
            "thinking": "I analyzed multiple components...",
            "components": [{"name": "appetizer"}, {"name": "main course"}],
        }

        with patch("fcp.routes.analyze.analyze_meal_with_thinking", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result

            response = client.post(
                "/analyze/thinking",
                json={"image_url": "https://firebasestorage.googleapis.com/complex.jpg"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["thinking_level"] == "high"
            mock_analyze.assert_called_once_with(
                "https://firebasestorage.googleapis.com/complex.jpg",
                thinking_level="high",
            )

    def test_analyze_thinking_low_level(self, mock_auth):
        """Test analysis with low thinking level."""
        with patch("fcp.routes.analyze.analyze_meal_with_thinking", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = {"dish_name": "Simple Dish"}

            response = client.post(
                "/analyze/thinking?thinking_level=low",
                json={"image_url": "https://firebasestorage.googleapis.com/simple.jpg"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["thinking_level"] == "low"
            mock_analyze.assert_called_once_with(
                "https://firebasestorage.googleapis.com/simple.jpg",
                thinking_level="low",
            )

    def test_analyze_thinking_medium_level(self, mock_auth):
        """Test analysis with medium thinking level."""
        with patch("fcp.routes.analyze.analyze_meal_with_thinking", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = {"dish_name": "Medium Dish"}

            response = client.post(
                "/analyze/thinking?thinking_level=medium",
                json={"image_url": "https://firebasestorage.googleapis.com/medium.jpg"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            assert response.json()["thinking_level"] == "medium"

    def test_analyze_thinking_minimal_level(self, mock_auth):
        """Test analysis with minimal thinking level."""
        with patch("fcp.routes.analyze.analyze_meal_with_thinking", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = {"dish_name": "Quick Analysis"}

            response = client.post(
                "/analyze/thinking?thinking_level=minimal",
                json={"image_url": "https://firebasestorage.googleapis.com/quick.jpg"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            assert response.json()["thinking_level"] == "minimal"


class TestAnalyzeAgenticVisionEndpoint:
    """Tests for POST /analyze/agentic-vision endpoint."""

    def test_analyze_agentic_vision_success(self, mock_auth):
        """Test agentic vision analysis."""
        mock_result = {
            "dish_name": "Sushi Platter",
            "pieces_count": 12,
            "varieties": ["salmon", "tuna", "shrimp"],
        }

        with patch("fcp.routes.analyze.analyze_meal_with_agentic_vision", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_result

            response = client.post(
                "/analyze/agentic-vision",
                json={"image_url": "https://firebasestorage.googleapis.com/sushi.jpg"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["method"] == "agentic_vision"
            assert data["analysis"]["pieces_count"] == 12
