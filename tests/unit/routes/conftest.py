"""Shared fixtures for route tests."""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_firestore_client_for_routes():
    """Auto-mock the firestore_client proxy so route tests don't hit real DB.

    Tests that explicitly mock firestore at a more specific level will override this.
    """
    mock_client = AsyncMock()
    mock_client.get_user_logs = AsyncMock(return_value=[])
    mock_client.get_log = AsyncMock(return_value=None)
    mock_client.get_logs_by_ids = AsyncMock(return_value=[])
    mock_client.create_log = AsyncMock(return_value="new-log-id")
    mock_client.update_log = AsyncMock(return_value=None)
    mock_client.delete_log = AsyncMock(return_value=None)
    mock_client.get_pantry = AsyncMock(return_value=[])
    mock_client.add_pantry_item = AsyncMock(return_value="new-item-id")
    mock_client.update_pantry_item = AsyncMock(return_value=None)
    mock_client.delete_pantry_item = AsyncMock(return_value=None)
    mock_client.get_recipes = AsyncMock(return_value=[])
    mock_client.get_recipe = AsyncMock(return_value=None)
    mock_client.create_recipe = AsyncMock(return_value="new-recipe-id")
    mock_client.update_recipe = AsyncMock(return_value=None)
    mock_client.delete_recipe = AsyncMock(return_value=None)
    mock_client.get_user_preferences = AsyncMock(return_value={})
    mock_client.update_user_preferences = AsyncMock(return_value=None)
    mock_client.get_drafts = AsyncMock(return_value=[])
    mock_client.create_draft = AsyncMock(return_value="new-draft-id")
    mock_client.get_notifications = AsyncMock(return_value=[])
    mock_client.get_user_stats = AsyncMock(return_value={})
    mock_client.db = mock_client  # for health check compatibility

    with patch("fcp.services.firestore.firestore_client", mock_client):
        with patch("fcp.services.firestore._get_legacy_client", return_value=mock_client):
            yield mock_client
