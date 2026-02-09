"""Tests for Phase 2: Receipt Parser and Inventory management."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools.parser import (
    SHELF_LIFE,
    _normalize_category,
    _normalize_date,
    _safe_float,
    _safe_int,
    add_items_from_receipt,
    estimate_expiration,
    parse_receipt,
)


class TestSafeFloat:
    """Tests for _safe_float helper."""

    def test_safe_float_with_number(self):
        """Should handle numeric values."""
        assert _safe_float(5.99) == 5.99
        assert _safe_float(10) == 10.0

    def test_safe_float_with_string(self):
        """Should handle string values."""
        assert _safe_float("5.99") == 5.99
        assert _safe_float("$5.99") == 5.99
        assert _safe_float(" 5.99 ") == 5.99

    def test_safe_float_with_currency_and_commas(self):
        """Should handle currency symbols and commas."""
        assert _safe_float("$1,234.56") == 1234.56
        assert _safe_float("$100") == 100.0

    def test_safe_float_with_invalid(self):
        """Should return 0.0 for invalid values."""
        assert _safe_float(None) == 0.0
        assert _safe_float("invalid") == 0.0
        assert _safe_float("") == 0.0


class TestSafeInt:
    """Tests for _safe_int helper."""

    def test_safe_int_with_number(self):
        """Should handle numeric values."""
        assert _safe_int(5) == 5
        assert _safe_int(5.7) == 5

    def test_safe_int_with_string(self):
        """Should handle string values."""
        assert _safe_int("5") == 5
        assert _safe_int("3 pieces") == 3

    def test_safe_int_minimum_is_one(self):
        """Should return at least 1."""
        assert _safe_int(0) == 1
        assert _safe_int(-5) == 1

    def test_safe_int_with_invalid(self):
        """Should return 1 for invalid values."""
        assert _safe_int(None) == 1
        assert _safe_int("invalid") == 1
        assert _safe_int("") == 1


class TestNormalizeDate:
    """Tests for _normalize_date helper."""

    def test_normalize_date_iso_format(self):
        """Should pass through valid ISO format."""
        assert _normalize_date("2026-01-22") == "2026-01-22"

    def test_normalize_date_us_format(self):
        """Should handle MM/DD/YYYY format."""
        assert _normalize_date("01/22/2026") == "2026-01-22"
        assert _normalize_date("1/22/2026") == "2026-01-22"

    def test_normalize_date_dashes(self):
        """Should handle MM-DD-YYYY format."""
        assert _normalize_date("01-22-2026") == "2026-01-22"

    def test_normalize_date_none_returns_today(self):
        """Should return today for None."""
        result = _normalize_date(None)
        assert result == datetime.now().strftime("%Y-%m-%d")

    def test_normalize_date_empty_returns_today(self):
        """Should return today for empty string."""
        result = _normalize_date("")
        assert result == datetime.now().strftime("%Y-%m-%d")

    def test_normalize_date_invalid_returns_today(self):
        """Should return today for unparseable date."""
        result = _normalize_date("not a date")
        assert result == datetime.now().strftime("%Y-%m-%d")

    def test_normalize_date_short_year(self):
        """Should handle 2-digit years."""
        result = _normalize_date("01/22/26")
        assert result == "2026-01-22"

    def test_normalize_date_invalid_date_values(self):
        """Should return today for dates with invalid values (e.g., month 13)."""
        result = _normalize_date("13/45/2026")  # Invalid month/day
        assert result == datetime.now().strftime("%Y-%m-%d")


class TestNormalizeCategory:
    """Tests for category normalization."""

    def test_normalize_produce(self):
        """Should normalize produce category."""
        assert _normalize_category("produce") == "produce"
        assert _normalize_category("PRODUCE") == "produce"
        assert _normalize_category("fresh produce") == "produce"

    def test_normalize_produce_synonyms(self):
        """Should normalize produce synonyms."""
        assert _normalize_category("Fruits") == "produce"
        assert _normalize_category("vegetables") == "produce"
        assert _normalize_category("Fresh Items") == "produce"

    def test_normalize_dairy(self):
        """Should normalize dairy category."""
        assert _normalize_category("dairy") == "dairy"
        assert _normalize_category("DAIRY") == "dairy"

    def test_normalize_dairy_synonyms(self):
        """Should normalize dairy synonyms."""
        assert _normalize_category("Milk Products") == "dairy"
        assert _normalize_category("cheese") == "dairy"

    def test_normalize_proteins(self):
        """Should normalize proteins category."""
        assert _normalize_category("proteins") == "proteins"
        assert _normalize_category("meat proteins") == "proteins"

    def test_normalize_proteins_synonyms(self):
        """Should normalize protein synonyms."""
        assert _normalize_category("Meat") == "proteins"
        assert _normalize_category("Seafood") == "proteins"
        assert _normalize_category("Fish") == "proteins"

    def test_normalize_frozen(self):
        """Should normalize frozen category."""
        assert _normalize_category("frozen") == "frozen"
        assert _normalize_category("frozen foods") == "frozen"

    def test_normalize_frozen_synonyms(self):
        """Should normalize frozen synonyms."""
        assert _normalize_category("Frozen Dinners") == "frozen"
        assert _normalize_category("Freeze Pops") == "frozen"

    def test_normalize_pantry(self):
        """Should normalize pantry category."""
        assert _normalize_category("pantry") == "pantry"
        assert _normalize_category("pantry staples") == "pantry"

    def test_normalize_beverages(self):
        """Should normalize beverages category."""
        assert _normalize_category("beverages") == "beverages"
        assert _normalize_category("soft beverages") == "beverages"

    def test_normalize_bakery(self):
        """Should normalize bakery category."""
        assert _normalize_category("bakery") == "bakery"
        assert _normalize_category("fresh bakery") == "bakery"

    def test_normalize_deli(self):
        """Should normalize deli category."""
        assert _normalize_category("deli") == "deli"
        assert _normalize_category("deli meats") == "deli"

    def test_normalize_unknown(self):
        """Should return other for unknown categories."""
        assert _normalize_category("random") == "other"
        assert _normalize_category("xyz") == "other"

    def test_normalize_empty(self):
        """Should return other for empty/None category."""
        assert _normalize_category("") == "other"
        assert _normalize_category(None) == "other"


class TestEstimateExpiration:
    """Tests for expiration date estimation."""

    def test_produce_expires_in_7_days(self):
        """Produce should expire in ~7 days in fridge."""
        purchase_date = datetime.now()
        exp_date = estimate_expiration("produce", purchase_date)
        days = (exp_date - purchase_date).days
        assert days == SHELF_LIFE["produce"]

    def test_dairy_expires_in_14_days(self):
        """Dairy should expire in ~14 days in fridge."""
        purchase_date = datetime.now()
        exp_date = estimate_expiration("dairy", purchase_date)
        days = (exp_date - purchase_date).days
        assert days == SHELF_LIFE["dairy"]

    def test_proteins_expires_in_5_days(self):
        """Proteins should expire in ~5 days in fridge."""
        purchase_date = datetime.now()
        exp_date = estimate_expiration("proteins", purchase_date)
        days = (exp_date - purchase_date).days
        assert days == SHELF_LIFE["proteins"]

    def test_frozen_expires_in_180_days(self):
        """Frozen should expire in ~180 days."""
        purchase_date = datetime.now()
        exp_date = estimate_expiration("frozen", purchase_date, "freezer")
        days = (exp_date - purchase_date).days
        assert days == 365  # Capped at 1 year for freezer

    def test_freezer_extends_shelf_life(self):
        """Freezer storage should extend shelf life up to 6x."""
        purchase_date = datetime.now()
        exp_date = estimate_expiration("dairy", purchase_date, storage_type="freezer")
        days = (exp_date - purchase_date).days
        assert days > SHELF_LIFE["dairy"]  # More than fridge storage

    def test_pantry_storage_reduces_life_for_perishables(self):
        """Pantry storage should reduce life for perishables."""
        purchase_date = datetime.now()
        exp_date = estimate_expiration("dairy", purchase_date, storage_type="pantry")
        days = (exp_date - purchase_date).days
        assert days < SHELF_LIFE["dairy"]  # Less than fridge storage

    def test_pantry_storage_for_pantry_items(self):
        """Pantry items in pantry should not be reduced."""
        purchase_date = datetime.now()
        exp_date = estimate_expiration("pantry", purchase_date, storage_type="pantry")
        days = (exp_date - purchase_date).days
        assert days == SHELF_LIFE["pantry"]

    def test_unknown_category_defaults_to_30_days(self):
        """Unknown category should default to 30 days."""
        purchase_date = datetime.now()
        exp_date = estimate_expiration("unknown", purchase_date)
        days = (exp_date - purchase_date).days
        assert days == 30


class TestParseReceipt:
    """Tests for receipt parsing."""

    @pytest.mark.asyncio
    async def test_parse_receipt_success(self):
        """Should successfully parse receipt image."""
        mock_response = {
            "store": "Whole Foods",
            "date": "2026-01-22",
            "items": [
                {
                    "name": "Organic Bananas",
                    "price": 2.99,
                    "quantity": 1,
                    "category": "produce",
                    "unit": "lbs",
                },
                {
                    "name": "Milk",
                    "price": 4.99,
                    "quantity": 1,
                    "category": "dairy",
                    "unit": "gal",
                },
            ],
            "total": 7.98,
            "tax": 0.50,
        }

        with patch("fcp.tools.parser.gemini.generate_json", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response

            result = await parse_receipt("https://example.com/receipt.jpg")

            assert result["success"] is True
            assert result["store"] == "Whole Foods"
            assert len(result["items"]) == 2
            assert result["items"][0]["name"] == "Organic Bananas"
            assert result["items"][0]["category"] == "produce"
            assert result["total"] == 7.98

    @pytest.mark.asyncio
    async def test_parse_receipt_with_store_hint(self):
        """Should include store hint in prompt."""
        mock_response = {
            "store": "Trader Joe's",
            "date": "2026-01-22",
            "items": [],
            "total": 0,
            "tax": 0,
        }

        with patch("fcp.tools.parser.gemini.generate_json", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response

            result = await parse_receipt(
                "https://example.com/receipt.jpg",
                store_hint="Trader Joe's",
            )

            assert result["success"] is True
            assert result["store"] == "Trader Joe's"

    @pytest.mark.asyncio
    async def test_parse_receipt_handles_list_response(self):
        """Should handle list response from Gemini."""
        mock_response = [
            {
                "store": "Costco",
                "date": "2026-01-22",
                "items": [],
                "total": 100.00,
                "tax": 8.00,
            }
        ]

        with patch("fcp.tools.parser.gemini.generate_json", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response

            result = await parse_receipt("https://example.com/receipt.jpg")

            assert result["success"] is True
            assert result["store"] == "Costco"

    @pytest.mark.asyncio
    async def test_parse_receipt_normalizes_items(self):
        """Should normalize items with default values."""
        mock_response = {
            "store": "Store",
            "date": "2026-01-22",
            "items": [
                {"name": "Eggs"},  # Missing fields
                {"quantity": "3", "price": "5.99", "category": "xyz"},  # No name
            ],
            "total": 5.99,
        }

        with patch("fcp.tools.parser.gemini.generate_json", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response

            result = await parse_receipt("https://example.com/receipt.jpg")

            assert result["success"] is True
            assert result["items"][0]["name"] == "Eggs"
            assert result["items"][0]["price"] == 0
            assert result["items"][0]["quantity"] == 1
            assert result["items"][0]["unit"] == "pieces"
            assert result["items"][1]["category"] == "other"

    @pytest.mark.asyncio
    async def test_parse_receipt_handles_error(self):
        """Should handle parsing errors gracefully."""
        with patch("fcp.tools.parser.gemini.generate_json", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = Exception("API Error")

            result = await parse_receipt("https://example.com/receipt.jpg")

            assert result["success"] is False
            assert "API Error" in result["error"]

    @pytest.mark.asyncio
    async def test_parse_receipt_defaults_date_to_today_when_missing(self):
        """If the model output omits date, parse_receipt should default to today."""
        mock_response = {
            "store": "Test Store",
            "items": [],
            "total": 0.0,
            "tax": 0.0,
            # No "date" field
        }

        with patch("fcp.tools.parser.gemini.generate_json", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response

            result = await parse_receipt("https://example.com/receipt.jpg")

            assert result["success"] is True
            assert result["date"] == datetime.now().strftime("%Y-%m-%d")

    @pytest.mark.asyncio
    async def test_parse_receipt_handles_currency_strings(self):
        """Should handle price and quantity as strings with currency symbols."""
        mock_response = {
            "store": "Store",
            "date": "2026-01-22",
            "items": [
                {
                    "name": "Apples",
                    "price": "$3.99",
                    "quantity": "2 lbs",
                    "category": "produce",
                },
            ],
            "total": "$3.99",
            "tax": "$0.25",
        }

        with patch("fcp.tools.parser.gemini.generate_json", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response

            result = await parse_receipt("https://example.com/receipt.jpg")

            assert result["success"] is True
            assert result["items"][0]["price"] == 3.99
            assert result["items"][0]["quantity"] == 2
            assert result["total"] == 3.99
            assert result["tax"] == 0.25

    @pytest.mark.asyncio
    async def test_parse_receipt_normalizes_non_iso_date(self):
        """Should normalize non-ISO date formats."""
        mock_response = {
            "store": "Store",
            "date": "01/22/2026",  # US format
            "items": [],
            "total": 0,
            "tax": 0,
        }

        with patch("fcp.tools.parser.gemini.generate_json", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response

            result = await parse_receipt("https://example.com/receipt.jpg")

            assert result["success"] is True
            assert result["date"] == "2026-01-22"


class TestAddItemsFromReceipt:
    """Tests for adding items from receipt to pantry."""

    @pytest.mark.asyncio
    async def test_add_items_success(self):
        """Should add items from receipt to pantry."""
        receipt_items = [
            {
                "name": "Bananas",
                "quantity": 6,
                "unit": "pieces",
                "category": "produce",
                "price": 2.99,
            },
            {"name": "Milk", "quantity": 1, "unit": "gal", "category": "dairy", "price": 4.99},
        ]

        with patch("fcp.tools.parser.get_firestore_client") as mock_get_db:
            mock_db = AsyncMock()
            mock_db.add_pantry_item = AsyncMock(side_effect=["item1", "item2"])
            mock_get_db.return_value = mock_db

            result = await add_items_from_receipt("user123", receipt_items)

            assert result["success"] is True
            assert result["added_count"] == 2
            assert len(result["items"]) == 2
            assert mock_db.add_pantry_item.call_count == 2

    @pytest.mark.asyncio
    async def test_add_items_normalizes_category_casing(self):
        """Should normalize category casing and synonyms."""
        receipt_items = [
            {"name": "Milk", "quantity": 1, "category": "DAIRY"},  # Uppercase
            {"name": "Ice Cream", "quantity": 1, "category": "Frozen Foods"},  # Synonym
            {"name": "Apples", "quantity": 1, "category": "Fruits"},  # Synonym
        ]

        with patch("fcp.tools.parser.get_firestore_client") as mock_get_db:
            mock_db = AsyncMock()
            mock_db.add_pantry_item = AsyncMock(side_effect=["id1", "id2", "id3"])
            mock_get_db.return_value = mock_db

            await add_items_from_receipt("user123", receipt_items)

            calls = mock_db.add_pantry_item.call_args_list
            # DAIRY -> dairy, stored in fridge
            assert calls[0][0][1]["category"] == "dairy"
            assert calls[0][0][1]["storage_location"] == "fridge"
            # Frozen Foods -> frozen, stored in freezer
            assert calls[1][0][1]["category"] == "frozen"
            assert calls[1][0][1]["storage_location"] == "freezer"
            # Fruits -> produce
            assert calls[2][0][1]["category"] == "produce"

    @pytest.mark.asyncio
    async def test_add_items_assigns_storage_based_on_category(self):
        """Should assign storage location based on category."""
        receipt_items = [
            {"name": "Ice Cream", "quantity": 1, "category": "frozen"},
            {"name": "Rice", "quantity": 1, "category": "pantry"},
            {"name": "Chicken", "quantity": 1, "category": "proteins"},
        ]

        with patch("fcp.tools.parser.get_firestore_client") as mock_get_db:
            mock_db = AsyncMock()
            mock_db.add_pantry_item = AsyncMock(side_effect=["id1", "id2", "id3"])
            mock_get_db.return_value = mock_db

            await add_items_from_receipt("user123", receipt_items)

            calls = mock_db.add_pantry_item.call_args_list
            # Frozen -> freezer
            assert calls[0][0][1]["storage_location"] == "freezer"
            # Pantry -> pantry
            assert calls[1][0][1]["storage_location"] == "pantry"
            # Proteins -> fridge (default)
            assert calls[2][0][1]["storage_location"] == "fridge"

    @pytest.mark.asyncio
    async def test_add_items_calculates_expiration_dates(self):
        """Should calculate expiration dates for items."""
        receipt_items = [
            {"name": "Bread", "quantity": 1, "category": "bakery"},
        ]
        purchase_date = datetime(2026, 1, 22)

        with patch("fcp.tools.parser.get_firestore_client") as mock_get_db:
            mock_db = AsyncMock()
            mock_db.add_pantry_item = AsyncMock(return_value="id1")
            mock_get_db.return_value = mock_db

            await add_items_from_receipt(
                "user123",
                receipt_items,
                purchase_date=purchase_date,
            )

            calls = mock_db.add_pantry_item.call_args_list
            item = calls[0][0][1]
            assert item["purchase_date"] == purchase_date.isoformat()
            # Bakery expires in 5 days
            exp_date = datetime.fromisoformat(item["expiration_date"])
            assert (exp_date - purchase_date).days == SHELF_LIFE["bakery"]

    @pytest.mark.asyncio
    async def test_add_items_uses_current_date_by_default(self):
        """Should use current date when no purchase date provided."""
        receipt_items = [
            {"name": "Eggs", "quantity": 12, "category": "dairy"},
        ]

        with patch("fcp.tools.parser.get_firestore_client") as mock_get_db:
            mock_db = AsyncMock()
            mock_db.add_pantry_item = AsyncMock(return_value="id1")
            mock_get_db.return_value = mock_db

            before = datetime.now()
            await add_items_from_receipt("user123", receipt_items)
            after = datetime.now()

            calls = mock_db.add_pantry_item.call_args_list
            item = calls[0][0][1]
            purchase_date = datetime.fromisoformat(item["purchase_date"])
            assert before <= purchase_date <= after

    @pytest.mark.asyncio
    async def test_add_items_handles_missing_fields(self):
        """Should handle items with missing fields and set source to receipt."""
        receipt_items = [
            {"name": "Mystery Item"},  # Missing most fields
        ]

        with patch("fcp.tools.parser.get_firestore_client") as mock_get_db:
            mock_db = AsyncMock()
            mock_db.add_pantry_item = AsyncMock(return_value="id1")
            mock_get_db.return_value = mock_db

            await add_items_from_receipt("user123", receipt_items)

            calls = mock_db.add_pantry_item.call_args_list
            item = calls[0][0][1]
            assert item["name"] == "Mystery Item"
            assert item["quantity"] == 1
            assert item["unit"] == "pieces"
            assert item["category"] == "other"
            assert item["price"] == 0
            # Verify source is always set to receipt
            assert item["source"] == "receipt"
            # Verify default storage is fridge for uncategorized items
            assert item["storage_location"] == "fridge"
