"""Tests for voice route endpoints."""

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


class TestVoiceMealLogEndpoint:
    """Tests for /voice/meal endpoint."""

    def test_voice_meal_log_success(self, client):
        """Test successful voice meal logging."""
        audio_base64 = base64.b64encode(b"test_audio").decode("utf-8")

        with patch("fcp.routes.voice.process_voice_meal_log", new_callable=AsyncMock) as mock_voice:
            mock_voice.return_value = {
                "status": "logged",
                "meal_data": {"dish_name": "Ramen", "venue": "Local restaurant"},
                "response_text": "I logged your ramen.",
            }

            response = client.post(
                "/voice/meal",
                json={"audio_base64": audio_base64},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "logged"
            assert data["meal_data"]["dish_name"] == "Ramen"
            assert data["response_text"] == "I logged your ramen."

    def test_voice_meal_log_with_options(self, client):
        """Test voice meal logging with custom audio options."""
        audio_base64 = base64.b64encode(b"test_audio").decode("utf-8")

        with patch("fcp.routes.voice.process_voice_meal_log", new_callable=AsyncMock) as mock_voice:
            mock_voice.return_value = {
                "status": "logged",
                "meal_data": {"dish_name": "Pizza"},
                "response_text": "Got it!",
            }

            response = client.post(
                "/voice/meal",
                json={
                    "audio_base64": audio_base64,
                    "mime_type": "audio/webm",
                    "sample_rate": 44100,
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

            # Verify params were passed
            call_args = mock_voice.call_args.kwargs
            assert call_args["audio_data"] == audio_base64
            assert call_args["mime_type"] == "audio/webm"
            assert call_args["sample_rate"] == 44100

    def test_voice_meal_log_clarification_needed(self, client):
        """Test voice meal logging when clarification is needed."""
        audio_base64 = base64.b64encode(b"audio").decode("utf-8")

        with patch("fcp.routes.voice.process_voice_meal_log", new_callable=AsyncMock) as mock_voice:
            mock_voice.return_value = {
                "status": "clarification_needed",
                "meal_data": None,
                "response_text": "What did you eat?",
            }

            response = client.post(
                "/voice/meal",
                json={"audio_base64": audio_base64},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "clarification_needed"
            assert data["meal_data"] is None
            assert data["response_text"] == "What did you eat?"

    def test_voice_meal_log_with_audio_response(self, client):
        """Test voice meal logging with audio response."""
        audio_base64 = base64.b64encode(b"audio").decode("utf-8")
        response_audio = base64.b64encode(b"response_audio").decode("utf-8")

        with patch("fcp.routes.voice.process_voice_meal_log", new_callable=AsyncMock) as mock_voice:
            mock_voice.return_value = {
                "status": "logged",
                "meal_data": {"dish_name": "Salad"},
                "response_text": "Logged!",
                "response_audio_base64": response_audio,
            }

            response = client.post(
                "/voice/meal",
                json={"audio_base64": audio_base64},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["response_audio_base64"] == response_audio

    def test_voice_meal_log_error_status(self, client):
        """Test voice meal logging with error status."""
        audio_base64 = base64.b64encode(b"audio").decode("utf-8")

        with patch("fcp.routes.voice.process_voice_meal_log", new_callable=AsyncMock) as mock_voice:
            mock_voice.return_value = {
                "status": "error",
                "meal_data": None,
                "error": "Invalid audio format",
            }

            response = client.post(
                "/voice/meal",
                json={"audio_base64": audio_base64},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert data["error"] == "Invalid audio format"

    def test_voice_meal_log_api_not_configured(self, client, mock_auth):
        """Test voice meal logging when API key is not configured."""
        audio_base64 = base64.b64encode(b"audio").decode("utf-8")

        with patch("fcp.routes.voice.process_voice_meal_log", new_callable=AsyncMock) as mock_voice:
            mock_voice.side_effect = RuntimeError("GEMINI_API_KEY not configured")

            response = client.post(
                "/voice/meal",
                json={"audio_base64": audio_base64},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 503
            data = response.json()
            error_msg = data.get("detail") or data.get("error", {}).get("message", "")
            assert "Voice service unavailable" in error_msg or "unavailable" in str(data)

    def test_voice_meal_log_generic_exception(self, client, mock_auth):
        """Test voice meal logging with unexpected exception."""
        audio_base64 = base64.b64encode(b"audio").decode("utf-8")

        with patch("fcp.routes.voice.process_voice_meal_log", new_callable=AsyncMock) as mock_voice:
            mock_voice.side_effect = Exception("Connection error")

            response = client.post(
                "/voice/meal",
                json={"audio_base64": audio_base64},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 500
            data = response.json()
            error_msg = data.get("detail") or data.get("error", {}).get("message", "")
            assert "Voice processing failed" in error_msg or "Connection error" in str(data)

    def test_voice_meal_log_requires_auth(self, client):
        """Test that voice meal endpoint requires authentication."""
        audio_base64 = base64.b64encode(b"audio").decode("utf-8")

        response = client.post(
            "/voice/meal",
            json={"audio_base64": audio_base64},
        )
        assert response.status_code == 403  # Demo users get 403 for write endpoints


class TestVoiceFoodQueryEndpoint:
    """Tests for /voice/query endpoint."""

    def test_voice_food_query_search_requested(self, client):
        """Test voice food query that triggers search."""
        audio_base64 = base64.b64encode(b"test_audio").decode("utf-8")

        with patch("fcp.routes.voice.voice_food_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = {
                "status": "search_requested",
                "query": "pasta dishes",
                "user_id": "test_user",
                "response_text": "Searching for pasta dishes.",
            }

            response = client.post(
                "/voice/query",
                json={"audio_base64": audio_base64},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "search_requested"
            assert data["query"] == "pasta dishes"
            assert data["response_text"] == "Searching for pasta dishes."

    def test_voice_food_query_response_status(self, client, mock_auth):
        """Test voice food query with general response."""
        audio_base64 = base64.b64encode(b"audio").decode("utf-8")

        with patch("fcp.routes.voice.voice_food_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = {
                "status": "response",
                "query": None,
                "user_id": "test_user",
                "response_text": "I can help you find meals.",
            }

            response = client.post(
                "/voice/query",
                json={"audio_base64": audio_base64},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "response"
            assert data["query"] is None

    def test_voice_food_query_with_options(self, client, mock_auth):
        """Test voice food query with custom audio options."""
        audio_base64 = base64.b64encode(b"audio").decode("utf-8")

        with patch("fcp.routes.voice.voice_food_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = {
                "status": "response",
                "query": None,
                "user_id": "test_user",
                "response_text": "Ok",
            }

            response = client.post(
                "/voice/query",
                json={
                    "audio_base64": audio_base64,
                    "mime_type": "audio/wav",
                    "sample_rate": 22050,
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

            # Verify params were passed
            call_args = mock_query.call_args.kwargs
            assert call_args["audio_data"] == audio_base64
            assert call_args["mime_type"] == "audio/wav"
            assert call_args["sample_rate"] == 22050

    def test_voice_food_query_with_audio_response(self, client, mock_auth):
        """Test voice food query with audio response."""
        audio_base64 = base64.b64encode(b"audio").decode("utf-8")
        response_audio = base64.b64encode(b"reply_audio").decode("utf-8")

        with patch("fcp.routes.voice.voice_food_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = {
                "status": "search_requested",
                "query": "lunch",
                "user_id": "test_user",
                "response_text": "Here are your results.",
                "response_audio_base64": response_audio,
            }

            response = client.post(
                "/voice/query",
                json={"audio_base64": audio_base64},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["response_audio_base64"] == response_audio

    def test_voice_food_query_error_status(self, client, mock_auth):
        """Test voice food query with error status."""
        audio_base64 = base64.b64encode(b"audio").decode("utf-8")

        with patch("fcp.routes.voice.voice_food_query", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = {
                "status": "error",
                "query": None,
                "user_id": "test_user",
                "error": "Audio processing failed",
            }

            response = client.post(
                "/voice/query",
                json={"audio_base64": audio_base64},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert data["error"] == "Audio processing failed"

    def test_voice_food_query_api_not_configured(self, client, mock_auth):
        """Test voice food query when API key is not configured."""
        audio_base64 = base64.b64encode(b"audio").decode("utf-8")

        with patch("fcp.routes.voice.voice_food_query", new_callable=AsyncMock) as mock_query:
            mock_query.side_effect = RuntimeError("GEMINI_API_KEY not configured")

            response = client.post(
                "/voice/query",
                json={"audio_base64": audio_base64},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 503
            data = response.json()
            error_msg = data.get("detail") or data.get("error", {}).get("message", "")
            assert "Voice service unavailable" in error_msg or "unavailable" in str(data)

    def test_voice_food_query_generic_exception(self, client, mock_auth):
        """Test voice food query with unexpected exception."""
        audio_base64 = base64.b64encode(b"audio").decode("utf-8")

        with patch("fcp.routes.voice.voice_food_query", new_callable=AsyncMock) as mock_query:
            mock_query.side_effect = Exception("Network error")

            response = client.post(
                "/voice/query",
                json={"audio_base64": audio_base64},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 500
            data = response.json()
            error_msg = data.get("detail") or data.get("error", {}).get("message", "")
            assert "Voice query failed" in error_msg or "Network error" in str(data)

    def test_voice_food_query_requires_auth(self, client):
        """Test that voice query endpoint requires authentication."""
        audio_base64 = base64.b64encode(b"audio").decode("utf-8")

        response = client.post(
            "/voice/query",
            json={"audio_base64": audio_base64},
        )
        assert response.status_code == 403  # Demo users get 403 for write endpoints
