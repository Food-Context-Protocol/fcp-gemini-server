"""Tests for research route endpoints."""

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


class TestResearchEndpoint:
    """Tests for /research endpoint."""

    def test_research_success(self, client, mock_auth):
        """Test successful research request."""
        with patch("fcp.routes.research.generate_research_report", new_callable=AsyncMock) as mock_research:
            mock_research.return_value = {
                "status": "completed",
                "report": "Research findings about Mediterranean diet health benefits.",
                "topic": "Mediterranean diet health benefits",
                "interaction_id": "int_123",
            }

            response = client.post(
                "/research",
                json={"topic": "Mediterranean diet health benefits"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["report"] == "Research findings about Mediterranean diet health benefits."
            assert data["topic"] == "Mediterranean diet health benefits"
            assert data["interaction_id"] == "int_123"

    def test_research_with_context(self, client, mock_auth):
        """Test research request with user context."""
        with patch("fcp.routes.research.generate_research_report", new_callable=AsyncMock) as mock_research:
            mock_research.return_value = {
                "status": "completed",
                "report": "Personalized research findings.",
                "topic": "Best foods for runners",
                "interaction_id": "int_456",
            }

            response = client.post(
                "/research",
                json={
                    "topic": "Best foods for runners",
                    "context": "I am training for a marathon",
                    "timeout_seconds": 300,
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["topic"] == "Best foods for runners"

            # Verify context was passed
            call_args = mock_research.call_args
            assert call_args.kwargs["context"] == "I am training for a marathon"
            assert call_args.kwargs["timeout_seconds"] == 300

    def test_research_timeout_status(self, client, mock_auth):
        """Test research request that times out."""
        with patch("fcp.routes.research.generate_research_report", new_callable=AsyncMock) as mock_research:
            mock_research.return_value = {
                "status": "timeout",
                "topic": "Complex topic",
                "interaction_id": "int_789",
                "message": "Research still in progress after 300s.",
            }

            response = client.post(
                "/research",
                json={"topic": "Complex topic"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "timeout"
            assert data["message"] == "Research still in progress after 300s."

    def test_research_failed_status(self, client, mock_auth):
        """Test research request that fails."""
        with patch("fcp.routes.research.generate_research_report", new_callable=AsyncMock) as mock_research:
            mock_research.return_value = {
                "status": "failed",
                "topic": "Failing topic",
                "interaction_id": "int_failed",
                "message": "API error occurred",
            }

            response = client.post(
                "/research",
                json={"topic": "Failing topic"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "failed"
            assert data["message"] == "API error occurred"

    def test_research_api_not_configured(self, client, mock_auth):
        """Test research when API key is not configured."""
        with patch("fcp.routes.research.generate_research_report", new_callable=AsyncMock) as mock_research:
            mock_research.side_effect = RuntimeError("GEMINI_API_KEY not configured")

            response = client.post(
                "/research",
                json={"topic": "Test topic"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 503
            data = response.json()
            assert "Research service unavailable" in data.get("detail", str(data))

    def test_research_generic_exception(self, client, mock_auth):
        """Test research with unexpected exception."""
        with patch("fcp.routes.research.generate_research_report", new_callable=AsyncMock) as mock_research:
            mock_research.side_effect = Exception("Unexpected error")

            response = client.post(
                "/research",
                json={"topic": "Test topic"},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 500
            data = response.json()
            assert "Research failed" in data.get("detail", str(data))

    def test_research_requires_auth(self, client):
        """Test that research endpoint requires authentication."""
        response = client.post(
            "/research",
            json={"topic": "Test topic"},
        )
        assert response.status_code == 403  # Demo users get 403 for write endpoints

    def test_research_validates_topic_length(self, client, mock_auth):
        """Test that topic must meet minimum length."""
        response = client.post(
            "/research",
            json={"topic": "ab"},  # Too short (min 3)
            headers=TEST_AUTH_HEADER,
        )
        assert response.status_code == 422  # Validation error

    def test_research_validates_timeout_range(self, client, mock_auth):
        """Test that timeout must be within valid range."""
        # Test timeout too low
        response = client.post(
            "/research",
            json={"topic": "Test topic", "timeout_seconds": 30},  # Min is 60
            headers=TEST_AUTH_HEADER,
        )
        assert response.status_code == 422

        # Test timeout too high
        response = client.post(
            "/research",
            json={"topic": "Test topic", "timeout_seconds": 1000},  # Max is 600
            headers=TEST_AUTH_HEADER,
        )
        assert response.status_code == 422
