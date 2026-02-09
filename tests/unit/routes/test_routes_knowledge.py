"""Tests for knowledge route endpoints."""

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


class TestEnrichLogEndpoint:
    """Tests for /knowledge/enrich/{log_id} endpoint."""

    def test_enrich_log_success(self, client, mock_auth):
        """Test successful knowledge enrichment."""
        mock_result = {
            "success": True,
            "knowledge_graph": {
                "usda_data": {"fdc_id": 123, "micronutrients": {"protein_g": 5.0}},
                "off_data": {"ecoscore": {"grade": "b"}, "nova_group": 2},
                "related_foods": ["Apple", "Orange"],
                "enriched_at": "2026-01-30T10:00:00Z",
            },
        }

        with patch(
            "fcp.routes.knowledge.knowledge_graph.enrich_with_knowledge_graph",
            new_callable=AsyncMock,
        ) as mock_enrich:
            mock_enrich.return_value = mock_result

            response = client.post(
                "/knowledge/enrich/log123",
                json={"include_sustainability": True, "include_micronutrients": True},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "knowledge_graph" in data
            assert data["knowledge_graph"]["usda_data"]["fdc_id"] == 123

            mock_enrich.assert_called_once_with(
                "admin",
                "log123",
                include_sustainability=True,
                include_micronutrients=True,
            )

    def test_enrich_log_not_found(self, client, mock_auth):
        """Test enrichment when log is not found."""
        with patch(
            "fcp.routes.knowledge.knowledge_graph.enrich_with_knowledge_graph",
            new_callable=AsyncMock,
        ) as mock_enrich:
            mock_enrich.return_value = {"success": False, "error": "Log not found"}

            response = client.post(
                "/knowledge/enrich/nonexistent",
                json={},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 404

    def test_enrich_log_with_options_disabled(self, client, mock_auth):
        """Test enrichment with options disabled."""
        with patch(
            "fcp.routes.knowledge.knowledge_graph.enrich_with_knowledge_graph",
            new_callable=AsyncMock,
        ) as mock_enrich:
            mock_enrich.return_value = {
                "success": True,
                "knowledge_graph": {"enriched_at": "2026-01-30T10:00:00Z"},
            }

            response = client.post(
                "/knowledge/enrich/log123",
                json={"include_sustainability": False, "include_micronutrients": False},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_enrich.assert_called_once_with(
                "admin",
                "log123",
                include_sustainability=False,
                include_micronutrients=False,
            )

    def test_enrich_log_requires_auth(self, client):
        """Test that enrichment requires authentication."""
        response = client.post(
            "/knowledge/enrich/log123",
            json={},
        )
        assert response.status_code == 403  # Demo users get 403 for write endpoints


class TestSearchEndpoint:
    """Tests for /knowledge/search/{query} endpoint."""

    def test_search_success(self, client, mock_auth):
        """Test successful knowledge search."""
        mock_result = {
            "usda": [{"fdcId": 123, "description": "Apple"}],
            "off": [{"product_name": "Apple Juice", "brand": "Brand"}],
            "combined_count": 2,
        }

        with patch(
            "fcp.routes.knowledge.knowledge_graph.search_knowledge",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = mock_result

            response = client.get(
                "/knowledge/search/apple",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["usda"]) == 1
            assert len(data["off"]) == 1
            assert data["combined_count"] == 2
            mock_search.assert_called_once_with("apple")

    def test_search_empty_results(self, client, mock_auth):
        """Test search with no results."""
        with patch(
            "fcp.routes.knowledge.knowledge_graph.search_knowledge",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = {"usda": [], "off": [], "combined_count": 0}

            response = client.get(
                "/knowledge/search/nonexistent",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["combined_count"] == 0

    def test_search_allows_demo_user(self, client, mock_auth):
        """Test that search allows demo users (read endpoint)."""
        with patch("fcp.routes.knowledge.knowledge_graph.search_knowledge", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {"results": [], "combined_count": 0}
            response = client.get("/knowledge/search/apple")
            # Demo users can access read endpoints
            assert response.status_code == 200


class TestCompareEndpoint:
    """Tests for /knowledge/compare endpoint."""

    def test_compare_success(self, client, mock_auth):
        """Test successful food comparison."""
        mock_result = {
            "success": True,
            "food1": "apple",
            "food2": "banana",
            "comparison": {
                "protein_g": {"food1": 0.3, "food2": 1.1, "difference": -0.8},
                "fiber_g": {"food1": 2.4, "food2": 2.6, "difference": -0.2},
            },
        }

        with patch(
            "fcp.routes.knowledge.knowledge_graph.compare_foods",
            new_callable=AsyncMock,
        ) as mock_compare:
            mock_compare.return_value = mock_result

            response = client.get(
                "/knowledge/compare?food1=apple&food2=banana",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["food1"] == "apple"
            assert data["food2"] == "banana"
            assert "protein_g" in data["comparison"]

    def test_compare_service_unavailable(self, client, mock_auth):
        """Test comparison when USDA API is not configured."""
        with patch(
            "fcp.routes.knowledge.knowledge_graph.compare_foods",
            new_callable=AsyncMock,
        ) as mock_compare:
            mock_compare.return_value = {
                "success": False,
                "error_code": "SERVICE_UNAVAILABLE",
                "error": "USDA API key not configured",
            }

            response = client.get(
                "/knowledge/compare?food1=apple&food2=banana",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 503

    def test_compare_food_not_found(self, client, mock_auth):
        """Test comparison when food is not found."""
        with patch(
            "fcp.routes.knowledge.knowledge_graph.compare_foods",
            new_callable=AsyncMock,
        ) as mock_compare:
            mock_compare.return_value = {
                "success": False,
                "error": "Food 'nonexistent' not found",
            }

            response = client.get(
                "/knowledge/compare?food1=nonexistent&food2=banana",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 404

    def test_compare_allows_demo_user(self, client, mock_auth):
        """Test that comparison allows demo users (read endpoint)."""
        with patch("fcp.routes.knowledge.knowledge_graph.compare_foods", new_callable=AsyncMock) as mock_compare:
            mock_compare.return_value = {"success": True, "comparison": "test"}
            response = client.get("/knowledge/compare?food1=apple&food2=banana")
            # Demo users can access read endpoints
            assert response.status_code == 200


class TestGetCachedEndpoint:
    """Tests for /knowledge/cache/{food_name} endpoint."""

    def test_get_cached_hit(self, client, mock_auth):
        """Test getting cached knowledge data."""
        mock_cached = {
            "food_name": "Apple",
            "usda_data": {"fdc_id": 123},
            "cached_at": "2026-01-30T10:00:00Z",
        }

        with patch(
            "fcp.routes.knowledge.knowledge_graph.get_cached_knowledge",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = mock_cached

            response = client.get(
                "/knowledge/cache/Apple",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["cached"] is True
            assert data["food_name"] == "Apple"
            assert data["usda_data"]["fdc_id"] == 123

    def test_get_cached_miss(self, client, mock_auth):
        """Test getting cached data when not cached."""
        with patch(
            "fcp.routes.knowledge.knowledge_graph.get_cached_knowledge",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = None

            response = client.get(
                "/knowledge/cache/Unknown",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["cached"] is False

    def test_get_cached_allows_demo_user(self, client, mock_auth):
        """Test that getting cached data allows demo users (read endpoint)."""
        with patch("fcp.routes.knowledge.knowledge_graph.get_cached_knowledge", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"cached": True}
            response = client.get("/knowledge/cache/Apple")
            # Demo users can access read endpoints
            assert response.status_code == 200
