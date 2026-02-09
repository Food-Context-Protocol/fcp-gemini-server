"""Tests for external route endpoints."""

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


class TestLookupProductEndpoint:
    """Tests for /external/lookup-product/{barcode} endpoint."""

    def test_lookup_product_success(self, client, mock_auth):
        """Test successful product lookup."""
        mock_result = {
            "product_name": "Organic Apple Juice",
            "brand": "Nature's Best",
            "nutriscore_grade": "b",
            "ecoscore_grade": "a",
            "ingredients": ["apple juice", "water"],
            "allergens": [],
        }

        with patch(
            "fcp.routes.external.lookup_product",
            new_callable=AsyncMock,
        ) as mock_lookup:
            mock_lookup.return_value = mock_result

            response = client.get(
                "/external/lookup-product/3017620425035",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["product_name"] == "Organic Apple Juice"
            assert data["brand"] == "Nature's Best"
            assert data["nutriscore_grade"] == "b"
            mock_lookup.assert_called_once_with("3017620425035")

    def test_lookup_product_not_found(self, client, mock_auth):
        """Test product lookup when product is not found."""
        with patch(
            "fcp.routes.external.lookup_product",
            new_callable=AsyncMock,
        ) as mock_lookup:
            mock_lookup.return_value = None

            response = client.get(
                "/external/lookup-product/0000000000000",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 404

    def test_lookup_product_with_upc_code(self, client, mock_auth):
        """Test product lookup with UPC barcode."""
        mock_result = {
            "product_name": "Cola",
            "brand": "Pepsi",
            "nutriscore_grade": "e",
        }

        with patch(
            "fcp.routes.external.lookup_product",
            new_callable=AsyncMock,
        ) as mock_lookup:
            mock_lookup.return_value = mock_result

            response = client.get(
                "/external/lookup-product/012000001055",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["product_name"] == "Cola"

    def test_lookup_product_allows_demo_user(self, client, mock_auth):
        """Test that product lookup allows demo users (read endpoint)."""
        with patch("fcp.routes.external.lookup_product", new_callable=AsyncMock) as mock_lookup:
            mock_lookup.return_value = {"product_name": "Test Product"}
            response = client.get("/external/lookup-product/3017620425035")
            # Demo users can access read endpoints
            assert response.status_code == 200
