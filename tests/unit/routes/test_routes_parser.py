"""Tests for parser routes."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fcp.auth import require_write_access
from fcp.routes.parser import router
from tests.constants import TEST_AUTH_HEADER, TEST_USER  # sourcery skip: dont-import-test-modules

# Create test app with parser router
parser_test_app = FastAPI()
parser_test_app.include_router(router, prefix="")

AUTH_HEADER = TEST_AUTH_HEADER


def mock_require_write_access():
    """Mock write access that returns test user."""
    return TEST_USER


@pytest.fixture(autouse=True)
def mock_auth():
    """Mock authentication for all tests using FastAPI dependency overrides."""
    parser_test_app.dependency_overrides[require_write_access] = mock_require_write_access
    yield
    parser_test_app.dependency_overrides.clear()


@pytest.fixture
def client():
    """Create test client."""
    with TestClient(parser_test_app) as client:
        yield client


class TestParseReceiptRoute:
    """Tests for POST /parse/receipt endpoint."""

    def test_parse_receipt_success(self, client):
        """Should parse receipt successfully."""
        mock_result = {
            "success": True,
            "store": "Whole Foods",
            "date": "2026-01-22",
            "items": [
                {
                    "name": "Bananas",
                    "price": 2.99,
                    "quantity": 1,
                    "category": "produce",
                    "unit": "lbs",
                }
            ],
            "total": 2.99,
            "tax": 0.25,
        }

        with patch("fcp.routes.parser.parse_receipt", new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = mock_result

            response = client.post(
                "/parse/receipt",
                json={"image_url": "https://example.com/receipt.jpg"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["store"] == "Whole Foods"

    def test_parse_receipt_with_store_hint(self, client):
        """Should pass store hint to parser."""
        mock_result = {
            "success": True,
            "store": "Costco",
            "items": [],
            "date": "2026-01-22",
            "total": 0,
            "tax": 0,
        }

        with patch("fcp.routes.parser.parse_receipt", new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = mock_result

            response = client.post(
                "/parse/receipt",
                json={"image_url": "https://example.com/receipt.jpg", "store_hint": "Costco"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_parse.assert_called_once_with(
                "https://example.com/receipt.jpg",
                store_hint="Costco",
            )

    def test_parse_receipt_failure(self, client):
        """Should return 400 on parse failure."""
        mock_result = {"success": False, "error": "Could not read receipt"}

        with patch("fcp.routes.parser.parse_receipt", new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = mock_result

            response = client.post(
                "/parse/receipt",
                json={"image_url": "https://example.com/bad.jpg"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 400
            assert "Could not read receipt" in response.json()["detail"]


class TestAddReceiptToPantryRoute:
    """Tests for POST /parse/receipt/add-to-pantry endpoint."""

    def test_add_to_pantry_success(self, client):
        """Should add items to pantry successfully."""
        items = [
            {"name": "Milk", "quantity": 1, "category": "dairy", "price": 4.99},
            {"name": "Bread", "quantity": 1, "category": "bakery", "price": 3.49},
        ]
        mock_result = {
            "success": True,
            "added_count": 2,
            "items": [
                {**items[0], "id": "item1", "expiration_date": "2026-02-05"},
                {**items[1], "id": "item2", "expiration_date": "2026-01-27"},
            ],
        }

        with patch("fcp.routes.parser.add_items_from_receipt", new_callable=AsyncMock) as mock_add:
            mock_add.return_value = mock_result

            response = client.post(
                "/parse/receipt/add-to-pantry",
                json={"items": items},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["added_count"] == 2

    def test_add_to_pantry_with_purchase_date(self, client):
        """Should pass purchase date to function."""
        items = [{"name": "Eggs", "quantity": 12}]
        mock_result = {"success": True, "added_count": 1, "items": []}

        with patch("fcp.routes.parser.add_items_from_receipt", new_callable=AsyncMock) as mock_add:
            mock_add.return_value = mock_result

            response = client.post(
                "/parse/receipt/add-to-pantry",
                json={"items": items, "purchase_date": "2026-01-22T10:00:00"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            # Verify datetime was parsed
            call_args = mock_add.call_args
            assert call_args.kwargs["purchase_date"] == datetime(2026, 1, 22, 10, 0, 0)

    def test_add_to_pantry_with_storage(self, client):
        """Should pass storage location to function."""
        items = [{"name": "Ice Cream", "category": "frozen"}]
        mock_result = {"success": True, "added_count": 1, "items": []}

        with patch("fcp.routes.parser.add_items_from_receipt", new_callable=AsyncMock) as mock_add:
            mock_add.return_value = mock_result

            response = client.post(
                "/parse/receipt/add-to-pantry",
                json={"items": items, "default_storage": "freezer"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            call_args = mock_add.call_args
            assert call_args.kwargs["default_storage"] == "freezer"

    def test_add_to_pantry_invalid_date(self, client):
        """Should return 400 for invalid date format."""
        response = client.post(
            "/parse/receipt/add-to-pantry",
            json={"items": [{"name": "Test"}], "purchase_date": "not-a-date"},
            headers=AUTH_HEADER,
        )

        assert response.status_code == 400
        assert "Invalid purchase_date format" in response.json()["detail"]
