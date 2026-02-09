"""Tests for social route endpoints."""

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


class TestBlogPostEndpoint:
    """Tests for /social/blog-post endpoint."""

    def test_generate_blog_post_success(self, client, mock_auth):
        """Test successful blog post generation."""
        mock_log = {
            "id": "log123",
            "dish_name": "Ramen",
            "venue_name": "Ichiran",
            "rating": 5,
        }
        mock_content = "---\ntitle: My Amazing Ramen\n---\n# The Best Ramen Ever!"

        with (
            patch(
                "fcp.routes.social.get_meal",
                new_callable=AsyncMock,
            ) as mock_get_meal,
            patch(
                "fcp.routes.social.generate_blog_post",
                new_callable=AsyncMock,
            ) as mock_generate,
        ):
            mock_get_meal.return_value = mock_log
            mock_generate.return_value = mock_content

            response = client.post(
                "/social/blog-post?log_id=log123&style=lifestyle",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert "content" in data
            assert "My Amazing Ramen" in data["content"]

            mock_get_meal.assert_called_once_with("admin", "log123")
            mock_generate.assert_called_once_with(mock_log, "lifestyle")

    def test_generate_blog_post_with_different_style(self, client, mock_auth):
        """Test blog post generation with different style."""
        mock_log = {"id": "log123", "dish_name": "Sushi"}

        with (
            patch(
                "fcp.routes.social.get_meal",
                new_callable=AsyncMock,
            ) as mock_get_meal,
            patch(
                "fcp.routes.social.generate_blog_post",
                new_callable=AsyncMock,
            ) as mock_generate,
        ):
            mock_get_meal.return_value = mock_log
            mock_generate.return_value = "# Sushi Review"

            response = client.post(
                "/social/blog-post?log_id=log123&style=professional",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_generate.assert_called_once_with(mock_log, "professional")

    def test_generate_blog_post_default_style(self, client, mock_auth):
        """Test blog post generation with default style."""
        mock_log = {"id": "log123", "dish_name": "Pizza"}

        with (
            patch(
                "fcp.routes.social.get_meal",
                new_callable=AsyncMock,
            ) as mock_get_meal,
            patch(
                "fcp.routes.social.generate_blog_post",
                new_callable=AsyncMock,
            ) as mock_generate,
        ):
            mock_get_meal.return_value = mock_log
            mock_generate.return_value = "# Pizza Time"

            response = client.post(
                "/social/blog-post?log_id=log123",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_generate.assert_called_once_with(mock_log, "lifestyle")

    def test_generate_blog_post_log_not_found(self, client, mock_auth):
        """Test blog post generation when log is not found."""
        with patch(
            "fcp.routes.social.get_meal",
            new_callable=AsyncMock,
        ) as mock_get_meal:
            mock_get_meal.return_value = None

            response = client.post(
                "/social/blog-post?log_id=nonexistent",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 404

    def test_generate_blog_post_requires_auth(self, client):
        """Test that blog post generation requires authentication."""
        response = client.post("/social/blog-post?log_id=log123")
        assert response.status_code == 403  # Demo users get 403 for write endpoints
