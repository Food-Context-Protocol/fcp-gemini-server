"""Shared fixtures for scheduler unit tests."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_firestore_for_scheduler():
    """Mock Firestore so scheduler tests never touch a real database."""
    mock_client = AsyncMock()
    mock_client.get_active_users = AsyncMock(return_value=[])
    mock_client.get_user_preferences = AsyncMock(return_value={})
    mock_client.get_user_stats = AsyncMock(return_value={})
    mock_client.store_notification = AsyncMock(return_value="notif-id")

    with (
        patch("fcp.services.firestore._get_legacy_client", return_value=mock_client),
        patch("fcp.scheduler.jobs._firestore_ready", return_value=(True, None)),
    ):
        yield mock_client
