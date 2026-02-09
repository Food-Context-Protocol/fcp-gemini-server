"""Tests for Search Routes Module.

Tests the search routes extracted to routes/search.py.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fcp.auth import require_write_access
from fcp.routes.search import router
from tests.constants import TEST_AUTH_HEADER, TEST_USER  # sourcery skip: dont-import-test-modules

# Create test app with search router
search_test_app = FastAPI()
search_test_app.include_router(router, prefix="")

# Mock auth dependency - use centralized constant
AUTH_HEADER = TEST_AUTH_HEADER


def mock_require_write_access():
    """Mock write access that returns test user."""
    return TEST_USER


@pytest.fixture(autouse=True)
def mock_auth():
    """Mock authentication for all tests using FastAPI dependency overrides."""
    search_test_app.dependency_overrides[require_write_access] = mock_require_write_access
    yield
    search_test_app.dependency_overrides.clear()


@pytest.fixture
def client():
    """Create test client."""
    with TestClient(search_test_app) as client:
        yield client


class TestSearchEndpoint:
    """Tests for POST /search endpoint."""

    def test_search_meals(self, client, sample_food_logs):
        """Test semantic search."""
        with patch("fcp.routes.search.search_meals", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = sample_food_logs[:2]
            response = client.post(
                "/search",
                json={"query": "spicy ramen", "limit": 5},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert data["query"] == "spicy ramen"
            mock_search.assert_called_once()

    def test_search_missing_query(self, client):
        """Test that query is required."""
        response = client.post(
            "/search",
            json={"limit": 5},
            headers=AUTH_HEADER,
        )
        assert response.status_code == 422  # Validation error

    def test_search_with_default_limit(self, client, sample_food_logs):
        """Test search with default limit value."""
        with patch("fcp.routes.search.search_meals", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = sample_food_logs
            response = client.post(
                "/search",
                json={"query": "pizza"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            # Default limit is 10
            call_args = mock_search.call_args
            assert call_args[0][2] == 10  # Third positional arg is limit

    def test_search_sanitizes_query(self, client, sample_food_logs):
        """Test that query is sanitized."""
        with patch("fcp.routes.search.search_meals", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            response = client.post(
                "/search",
                json={"query": "  spicy   ramen  ", "limit": 5},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            # Query should be passed to search_meals (sanitized)
            mock_search.assert_called_once()

    def test_search_empty_results(self, client):
        """Test search with no results."""
        with patch("fcp.routes.search.search_meals", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            response = client.post(
                "/search",
                json={"query": "nonexistent dish xyz"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["results"] == []
            assert data["query"] == "nonexistent dish xyz"


class TestRouterIntegration:
    """Tests for router integration."""

    def test_search_endpoint_exists(self, client):
        """Test that search endpoint is registered."""
        with patch("fcp.routes.search.search_meals", new_callable=AsyncMock) as mock:
            mock.return_value = []

            # POST /search should work
            response = client.post(
                "/search",
                json={"query": "test"},
                headers=AUTH_HEADER,
            )
            assert response.status_code == 200
