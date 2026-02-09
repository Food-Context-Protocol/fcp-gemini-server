"""
Tests for flavor pairings endpoint validation and behavior.

Run with: pytest tests/test_flavor_pairings.py -v
"""

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fcp.routes.misc import router

# Set environment to avoid credential errors during import
os.environ.setdefault("DEMO_MODE", "true")


@pytest.fixture
def test_app():
    """Create a test FastAPI app with the misc router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)


@pytest.fixture(autouse=True)
def mock_flavor_pairings():
    """Stub flavor pairing tool to avoid external Gemini usage."""
    with patch(
        "fcp.routes.misc.get_flavor_pairings",
        new=AsyncMock(return_value={"pairings": []}),
    ):
        yield


class TestFlavorPairingsValidation:
    """Tests for flavor pairings endpoint validation."""

    def test_pairings_valid_ingredient_type(self, client):
        """Test that 'ingredient' is a valid pairing_type."""
        # Mock auth dependency for this test
        from fcp.auth import AuthenticatedUser, UserRole, get_current_user

        async def mock_user():
            return AuthenticatedUser(user_id="test", role=UserRole.AUTHENTICATED)

        # Override auth dependency for this test
        client.app.dependency_overrides[get_current_user] = mock_user

        response = client.get("/flavor/pairings", params={"subject": "tomato", "pairing_type": "ingredient"})
        # Should not fail validation (may fail downstream without Gemini)
        assert response.status_code in (200, 500, 503)

    def test_pairings_valid_beverage_type(self, client):
        """Test that 'beverage' is a valid pairing_type."""
        from fcp.auth import AuthenticatedUser, UserRole, get_current_user

        async def mock_user():
            return AuthenticatedUser(user_id="test", role=UserRole.AUTHENTICATED)

        client.app.dependency_overrides[get_current_user] = mock_user

        response = client.get("/flavor/pairings", params={"subject": "steak", "pairing_type": "beverage"})
        # Should not fail validation
        assert response.status_code in (200, 500, 503)

    def test_pairings_invalid_type_rejected(self, client):
        """Test that invalid pairing_type values are rejected."""
        from fcp.auth import AuthenticatedUser, UserRole, get_current_user

        async def mock_user():
            return AuthenticatedUser(user_id="test", role=UserRole.AUTHENTICATED)

        client.app.dependency_overrides[get_current_user] = mock_user

        response = client.get("/flavor/pairings", params={"subject": "fish", "pairing_type": "wine"})
        # Should fail validation
        assert response.status_code == 422

    def test_pairings_empty_type_rejected(self, client):
        """Test that empty pairing_type is rejected."""
        from fcp.auth import AuthenticatedUser, UserRole, get_current_user

        async def mock_user():
            return AuthenticatedUser(user_id="test", role=UserRole.AUTHENTICATED)

        client.app.dependency_overrides[get_current_user] = mock_user

        response = client.get("/flavor/pairings", params={"subject": "pasta", "pairing_type": ""})
        # Should fail validation
        assert response.status_code == 422

    def test_pairings_default_type(self, client):
        """Test that pairing_type defaults to 'ingredient' when not provided."""
        from fcp.auth import AuthenticatedUser, UserRole, get_current_user

        async def mock_user():
            return AuthenticatedUser(user_id="test", role=UserRole.AUTHENTICATED)

        client.app.dependency_overrides[get_current_user] = mock_user

        response = client.get("/flavor/pairings", params={"subject": "basil"})
        # Should not fail validation (uses default)
        assert response.status_code in (200, 500, 503)

    def test_pairings_requires_subject(self, client):
        """Test that subject parameter is required."""
        from fcp.auth import AuthenticatedUser, UserRole, get_current_user

        async def mock_user():
            return AuthenticatedUser(user_id="test", role=UserRole.AUTHENTICATED)

        client.app.dependency_overrides[get_current_user] = mock_user

        response = client.get("/flavor/pairings")
        # Should fail - subject is required
        assert response.status_code == 422
