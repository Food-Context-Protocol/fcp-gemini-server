"""Tests for connector routes."""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fcp.auth import get_current_user, require_write_access
from fcp.routes.connectors import router
from tests.constants import TEST_AUTH_HEADER, TEST_USER  # sourcery skip: dont-import-test-modules

# Create test app with connectors router
connectors_test_app = FastAPI()
connectors_test_app.include_router(router, prefix="")


def mock_get_current_user():
    """Mock auth that returns test user."""
    return TEST_USER


def mock_require_write_access():
    """Mock write access that returns test user."""
    return TEST_USER


@pytest.fixture
def client():
    """Create test client with mocked auth."""
    connectors_test_app.dependency_overrides[get_current_user] = mock_get_current_user
    connectors_test_app.dependency_overrides[require_write_access] = mock_require_write_access
    with TestClient(connectors_test_app) as client:
        yield client
    connectors_test_app.dependency_overrides.clear()


class TestCalendarSyncRoute:
    """Tests for POST /connector/calendar."""

    def test_sync_calendar_success(self, client):
        """Should sync event to calendar."""
        with patch("fcp.routes.connectors.sync_to_calendar") as mock_sync:
            mock_sync.return_value = {
                "service": "Google Calendar",
                "event_id": "evt-123",
                "status": "created",
            }

            response = client.post(
                "/connector/calendar",
                json={
                    "event_title": "Dinner Party",
                    "start_time": "2026-01-25T19:00:00Z",
                    "description": "Birthday dinner",
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "Google Calendar"
            assert data["event_id"] == "evt-123"

            mock_sync.assert_called_once_with(
                TEST_USER.user_id,
                "Dinner Party",
                "2026-01-25T19:00:00Z",
                "Birthday dinner",
            )

    def test_sync_calendar_without_description(self, client):
        """Should sync event without optional description."""
        with patch("fcp.routes.connectors.sync_to_calendar") as mock_sync:
            mock_sync.return_value = {"service": "Google Calendar", "status": "created"}

            response = client.post(
                "/connector/calendar",
                json={
                    "event_title": "Lunch",
                    "start_time": "2026-01-25T12:00:00Z",
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_sync.assert_called_once_with(
                TEST_USER.user_id,
                "Lunch",
                "2026-01-25T12:00:00Z",
                None,
            )


class TestDriveSaveRoute:
    """Tests for POST /connector/drive."""

    def test_save_to_drive_success(self, client):
        """Should save content to Drive."""
        with patch("fcp.routes.connectors.save_to_drive") as mock_save:
            mock_save.return_value = {
                "service": "Google Drive",
                "file_id": "file-456",
                "status": "saved",
            }

            response = client.post(
                "/connector/drive",
                json={
                    "filename": "recipe.md",
                    "content": "# My Recipe\n\nIngredients...",
                    "folder": "Recipes",
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "Google Drive"
            assert data["file_id"] == "file-456"

            mock_save.assert_called_once_with(
                TEST_USER.user_id,
                "recipe.md",
                "# My Recipe\n\nIngredients...",
                "Recipes",
            )

    def test_save_to_drive_default_folder(self, client):
        """Should use default folder when not specified."""
        with patch("fcp.routes.connectors.save_to_drive") as mock_save:
            mock_save.return_value = {"service": "Google Drive", "status": "saved"}

            response = client.post(
                "/connector/drive",
                json={
                    "filename": "report.pdf",
                    "content": "Report content",
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_save.assert_called_once_with(
                TEST_USER.user_id,
                "report.pdf",
                "Report content",
                "FCP",  # Default folder
            )
