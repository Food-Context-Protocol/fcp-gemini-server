"""Multimodal parsing tools for menus and receipts."""

import logging
import re
from datetime import datetime, timedelta
from typing import Any

from fcp.mcp.registry import tool
from fcp.services.firestore import get_firestore_client
from fcp.services.gemini import gemini

logger = logging.getLogger(__name__)


def _safe_float(value: Any) -> float:
    """Safely parse a value to float, handling currency symbols and edge cases."""
    if value is None:
        return 0.0
    try:
        # Remove common currency symbols and whitespace
        cleaned = str(value).replace("$", "").replace(",", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(value: Any) -> int:
    """Safely parse a value to int, handling units and edge cases."""
    if value is None:
        return 1
    try:
        # Take the first numeric part of a string (e.g., "2 pieces" -> 2)
        cleaned = str(value).split()[0] if str(value).strip() else "1"
        return max(1, int(float(cleaned)))  # At least 1
    except (ValueError, TypeError, IndexError):
        return 1


def _normalize_date(date_str: str | None) -> str:
    """
    Normalize a date string to YYYY-MM-DD format.

    Handles various formats like MM/DD/YYYY, DD-MM-YYYY, etc.
    Returns today's date if parsing fails.
    """
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")

    # Try ISO format first
    try:
        datetime.fromisoformat(date_str)
        return date_str
    except (ValueError, TypeError):
        pass

    # Try common date formats
    formats = [
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue

    # Try to extract date with regex (handles "Jan 22, 2026" etc.)
    date_pattern = r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})"
    if match := re.search(date_pattern, date_str):
        parts = [int(p) for p in match.groups()]
        # Assume MM/DD/YYYY format for US receipts
        if parts[2] < 100:
            parts[2] += 2000
        try:
            return datetime(parts[2], parts[0], parts[1]).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Fall back to today
    return datetime.now().strftime("%Y-%m-%d")


# Default shelf life by category (days)
SHELF_LIFE = {
    "produce": 7,
    "dairy": 14,
    "proteins": 5,
    "frozen": 180,
    "pantry": 365,
    "beverages": 30,
    "bakery": 5,
    "deli": 7,
    "other": 30,
}


def _normalize_category(category: str) -> str:
    """Normalize category to standard values, handling synonyms and casing."""
    if not category:
        return "other"
    category_lower = category.lower()

    # Check for exact/substring matches first
    for std_category in SHELF_LIFE:
        if std_category in category_lower:
            return std_category

    # Handle common synonyms
    synonyms = {
        "produce": ["fruit", "vegetable", "veggie", "fresh"],
        "proteins": ["meat", "poultry", "seafood", "fish", "protein"],
        "dairy": ["milk", "cheese", "yogurt", "cream"],
        "frozen": ["freeze", "ice"],
        "pantry": ["dry goods", "canned", "staple"],
        "beverages": ["drink", "juice", "soda", "water"],
        "bakery": ["bread", "pastry", "baked"],
        "deli": ["lunch meat", "prepared", "ready to eat"],
    }

    for std_category, terms in synonyms.items():
        for term in terms:
            if term in category_lower:
                return std_category

    return "other"


def estimate_expiration(
    category: str,
    purchase_date: datetime,
    storage_type: str = "fridge",
) -> datetime:
    """
    Estimate expiration date based on category and storage.

    Args:
        category: Food category (produce, dairy, proteins, etc.)
        purchase_date: Date of purchase
        storage_type: Storage location (fridge, freezer, pantry)

    Returns:
        Estimated expiration datetime
    """
    base_days = SHELF_LIFE.get(category, 30)

    # Adjust for storage type
    if storage_type == "freezer":
        base_days = min(base_days * 6, 365)  # Freezer extends 6x up to 1 year
    elif storage_type == "pantry" and category not in ["pantry", "beverages"]:
        base_days = base_days // 2  # Pantry storage reduces life for perishables

    return purchase_date + timedelta(days=base_days)


@tool(
    name="dev.fcp.parsing.parse_menu",
    description="Parse a restaurant menu image into structured dish data",
    category="parsing",
)
async def parse_menu(image_url: str, neighborhood: str | None = None) -> dict[str, Any]:
    """
    Parse a restaurant menu image into structured dish data.
    """
    system_instruction = """
    Analyze the menu image and extract all dishes.
    For each dish, identify: Name, Description, Price, and potential Allergens.

    Return as JSON:
    {
        "venue_name": "...",
        "dishes": [
            { "name": "...", "description": "...", "price": 0.0, "allergens": [] }
        ]
    }
    """

    try:
        json_response = await gemini.generate_json(system_instruction, image_url=image_url)
        if isinstance(json_response, list) and json_response:
            return json_response[0]
        return json_response
    except Exception as e:
        logger.exception("Error parsing menu")
        return {"error": str(e)}


@tool(
    name="dev.fcp.parsing.parse_receipt",
    description="Parse a grocery receipt image into itemized pantry data",
    category="parsing",
)
async def parse_receipt(
    image_url: str,
    store_hint: str | None = None,
) -> dict[str, Any]:
    """
    Parse a grocery receipt image into itemized pantry data with categories.

    Args:
        image_url: URL or base64 of receipt image
        store_hint: Optional store name hint

    Returns:
        {
            "success": bool,
            "store": str,
            "date": str (YYYY-MM-DD),
            "items": [
                {
                    "name": str,
                    "price": float,
                    "quantity": int,
                    "category": str,
                    "unit": str
                }
            ],
            "total": float,
            "tax": float
        }
    """
    system_instruction = """Extract all items from this receipt image.

Return JSON with this structure:
{
    "store": "Store name",
    "date": "YYYY-MM-DD",
    "items": [
        {
            "name": "Item name (standardize to common names)",
            "price": 0.00,
            "quantity": 1,
            "category": "produce|dairy|proteins|frozen|pantry|beverages|bakery|deli|other",
            "unit": "pieces|lbs|oz|gal|each"
        }
    ],
    "total": 0.00,
    "tax": 0.00
}

Guidelines:
- Standardize item names (e.g., "ORG BANANAS" -> "Organic Bananas")
- Infer category from item type
- If quantity unclear, default to 1
- Extract exact prices from receipt"""

    if store_hint:
        system_instruction += f"\nStore hint: {store_hint}"

    try:
        result = await gemini.generate_json(system_instruction, image_url=image_url)

        # Handle list response
        if isinstance(result, list) and result:
            result = result[0]

        # Validate and normalize items
        items = []
        for item in result.get("items", []):
            normalized = {
                "name": item.get("name", "Unknown Item"),
                "price": _safe_float(item.get("price", 0)),
                "quantity": _safe_int(item.get("quantity", 1)),
                "category": _normalize_category(item.get("category", "other")),
                "unit": item.get("unit", "pieces"),
            }
            items.append(normalized)

        return {
            "success": True,
            "store": result.get("store", "Unknown Store"),
            "date": _normalize_date(result.get("date")),
            "items": items,
            "total": _safe_float(result.get("total", 0)),
            "tax": _safe_float(result.get("tax", 0)),
        }
    except Exception as e:
        logger.exception("Error parsing receipt")
        return {"success": False, "error": str(e)}


async def add_items_from_receipt(
    user_id: str,
    receipt_items: list[dict[str, Any]],
    purchase_date: datetime | None = None,
    default_storage: str = "fridge",
) -> dict[str, Any]:
    """
    Batch add items from receipt to pantry.

    Args:
        user_id: User ID
        receipt_items: List of items from parse_receipt
        purchase_date: Date of purchase (defaults to today)
        default_storage: Default storage location

    Returns:
        {"success": bool, "added_count": int, "items": [...]}
    """
    db = get_firestore_client()
    purchase_date = purchase_date or datetime.now()
    added_items = []

    for item in receipt_items:
        # Normalize category to handle casing and synonyms
        category = _normalize_category(item.get("category", "other"))

        # Determine storage based on normalized category
        storage = default_storage
        if category == "frozen":
            storage = "freezer"
        elif category in ["pantry", "beverages"]:
            storage = "pantry"

        expiration = estimate_expiration(category, purchase_date, storage)

        pantry_item = {
            "name": item.get("name", "Unknown Item"),
            "quantity": item.get("quantity", 1),
            "unit": item.get("unit", "pieces"),
            "category": category,
            "purchase_date": purchase_date.isoformat(),
            "expiration_date": expiration.isoformat(),
            "storage_location": storage,
            "source": "receipt",
            "price": item.get("price", 0),
        }

        item_id = await db.add_pantry_item(user_id, pantry_item)
        added_items.append({**pantry_item, "id": item_id})

    return {
        "success": True,
        "added_count": len(added_items),
        "items": added_items,
    }
