"""Inventory and pantry tools for FCP."""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from fcp.mcp.registry import tool
from fcp.services.firestore import firestore_client
from fcp.services.gemini import gemini
from fcp.utils.errors import tool_error

logger = logging.getLogger(__name__)


@tool(
    name="dev.fcp.inventory.get_pantry_suggestions",
    description="Suggest recipes based on what's currently in the user's pantry",
    category="inventory",
)
async def suggest_recipe_from_pantry(
    user_id: str,
    context: str = "dinner",
) -> dict[str, Any]:
    """
    Suggest recipes based on what's currently in the user's pantry.

    Args:
        user_id: The user ID.
        context: Context for the suggestion (e.g., "quick lunch", "fancy dinner").

    Returns:
        Structured recipe suggestions.
    """
    # 1. Fetch pantry and taste profile
    pantry = await firestore_client.get_pantry(user_id)
    preferences = await firestore_client.get_user_preferences(user_id)

    if not pantry:
        return {"message": "Your pantry is empty! Add some items first.", "suggestions": []}

    pantry_list = [item.get("name") for item in pantry]

    # 2. Ask Gemini for suggestions
    prompt = f"""
    You are a professional chef. Suggest 3 recipes based ONLY on the items in the user's pantry.

    PANTRY ITEMS:
    {", ".join(str(item) for item in pantry_list)}

    USER PREFERENCES:
    Cuisines: {preferences.get("top_cuisines")}
    Dietary: {preferences.get("dietary_patterns")}

    CONTEXT: {context}

    Return your suggestions as a JSON object:
    {{
        "suggestions": [
            {{
                "name": "Recipe Name",
                "reason": "Why this is a good match",
                "ingredients_used": ["item1", "item2"],
                "missing_ingredients": ["optional_item1"],
                "difficulty": "easy/medium/hard"
            }}
        ]
    }}
    """

    try:
        result = await gemini.generate_json(prompt)
        return {
            "pantry_count": len(pantry),
            "suggestions": result.get("suggestions", []),
            "context": context,
        }
    except Exception as e:
        return {**tool_error(e, "suggesting recipes from pantry"), "status": "failed"}


@tool(
    name="dev.fcp.inventory.check_pantry_expiry",
    description="Scan the user's pantry and identify items nearing expiry",
    category="inventory",
)
async def check_pantry_expiry(user_id: str) -> dict[str, Any]:
    """
    Scan the user's pantry and identify items nearing expiry.
    """
    pantry = await firestore_client.get_pantry(user_id)

    if not pantry:
        return {"alerts": [], "message": "Pantry is empty."}

    # Helper to handle non-serializable objects (like Firestore timestamps)
    def serialize_pantry(p):
        clean = []
        for item in p:
            item_copy = dict(item)
            for k, v in item_copy.items():
                if hasattr(v, "isoformat"):
                    item_copy[k] = v.isoformat()
            clean.append(item_copy)
        return clean

    system_instruction = """
    Analyze the following pantry items and their purchase dates.
    Identify items that are likely to expire within 7 days or are already past their prime.

    Return as JSON:
    {
        "alerts": [
            { "item": "...", "status": "expiring_soon/expired", "days_remaining": 0, "action": "e.g. 'Eat tonight'" }
        ],
        "recipe_suggestion": "A dish that uses the most urgent item"
    }
    """

    prompt = f"Pantry Data:\n{json.dumps(serialize_pantry(pantry), indent=2)}"

    try:
        return await gemini.generate_json(f"{system_instruction}\n\n{prompt}")
    except Exception as e:
        return tool_error(e, "checking pantry expiry")


async def add_to_pantry(user_id: str, items: list[str]) -> list[str]:
    """Add multiple items to user's pantry."""
    items_data = [{"name": item} for item in items]
    return await firestore_client.update_pantry_items_batch(user_id, items_data)


@tool(
    name="dev.fcp.inventory.list_pantry",
    description="List pantry items for the authenticated user",
    category="inventory",
)
async def list_pantry(user_id: str) -> dict[str, Any]:
    """List pantry items with a stable response shape."""
    items = await firestore_client.get_pantry(user_id)
    return {"items": items, "count": len(items)}


async def deduct_from_pantry(
    user_id: str,
    ingredients: list[str],
    servings: int = 1,
) -> dict[str, Any]:
    """
    Deduct ingredients from pantry when a meal is logged.

    Uses AI to fuzzy-match logged ingredients to pantry items.

    Args:
        user_id: User ID
        ingredients: List of ingredient names from food log
        servings: Number of servings (affects quantity deduction)

    Returns:
        {
            "success": bool,
            "deducted": [{"item": str, "quantity": float}],
            "not_found": [str],
            "low_stock": [str]
        }
    """
    # Get current pantry
    pantry = await firestore_client.get_pantry(user_id)
    pantry_names = [item["name"] for item in pantry]

    if not pantry_names:
        return {
            "success": True,
            "deducted": [],
            "not_found": ingredients,
            "low_stock": [],
        }

    # Use AI to match ingredients to pantry items
    match_prompt = f"""Match these ingredients to pantry items.
Ingredients: {ingredients}
Pantry items: {pantry_names}

For each ingredient, find the best matching pantry item (or null if no match).
Return JSON: {{"matches": [{{"ingredient": "...", "pantry_item": "..." or null, "estimated_quantity": 1}}]}}
"""
    matches = await gemini.generate_json(match_prompt)

    # Handle list response
    if isinstance(matches, list) and matches:
        matches = matches[0]

    deducted = []
    not_found = []
    low_stock = []

    for match in matches.get("matches", []):
        ingredient = match.get("ingredient", "")
        pantry_item_name = match.get("pantry_item")

        # Guard against non-numeric or negative estimated_quantity from model
        raw_qty = match.get("estimated_quantity", 1)
        try:
            qty = float(raw_qty)
        except (TypeError, ValueError):
            qty = 1.0
        qty = max(qty, 0)
        quantity_to_deduct = qty * servings

        if not pantry_item_name:
            not_found.append(ingredient)
            continue

        # Find the pantry item
        pantry_item = next(
            (p for p in pantry if p["name"].lower() == pantry_item_name.lower()),
            None,
        )

        if not pantry_item:
            not_found.append(ingredient)
            continue

        # Deduct quantity
        current_qty = pantry_item.get("quantity", 1)
        new_quantity = current_qty - quantity_to_deduct
        if new_quantity <= 0:
            # Remove item from pantry
            await firestore_client.delete_pantry_item(user_id, pantry_item["id"])
            deducted.append(
                {
                    "item": pantry_item_name,
                    "quantity": current_qty,
                    "removed": True,
                }
            )
        else:
            # Update quantity
            await firestore_client.update_pantry_item(
                user_id,
                {"id": pantry_item["id"], "name": pantry_item_name, "quantity": new_quantity},
            )
            deducted.append(
                {
                    "item": pantry_item_name,
                    "quantity": quantity_to_deduct,
                    "remaining": new_quantity,
                }
            )

            # Check for low stock
            if new_quantity <= 2:
                low_stock.append(pantry_item_name)

    return {
        "success": True,
        "deducted": deducted,
        "not_found": not_found,
        "low_stock": low_stock,
    }


async def check_expiring_items(
    user_id: str,
    days_threshold: int = 3,
) -> dict[str, Any]:
    """
    Check for items expiring within threshold.

    Args:
        user_id: User ID
        days_threshold: Number of days to check for expiring items

    Returns:
        {
            "expiring_soon": [{"id": str, "name": str, "expiration_date": str, "days_left": int}],
            "expired": [{"id": str, "name": str, "expiration_date": str}]
        }
    """
    pantry = await firestore_client.get_pantry(user_id)

    # Normalize to date only (no time component) to avoid off-by-one issues
    today = datetime.now().date()
    threshold_date = today + timedelta(days=days_threshold)

    expiring_soon = []
    expired = []

    for item in pantry:
        exp_date_str = item.get("expiration_date")
        if not exp_date_str:
            continue

        try:
            exp_date = datetime.fromisoformat(exp_date_str).date()
        except (ValueError, TypeError):
            continue

        if exp_date < today:
            expired.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "expiration_date": exp_date_str,
                }
            )
        elif exp_date <= threshold_date:
            days_left = (exp_date - today).days
            expiring_soon.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "expiration_date": exp_date_str,
                    "days_left": days_left,
                }
            )

    return {
        "expiring_soon": expiring_soon,
        "expired": expired,
    }


@tool(
    name="dev.fcp.inventory.update_pantry_item",
    description="Update an existing pantry item",
    category="inventory",
    requires_write=True,
)
async def update_pantry_item(
    user_id: str,
    item_id: str,
    name: str | None = None,
    quantity: float | None = None,
    unit: str | None = None,
    expiration_date: str | None = None,
) -> dict[str, Any]:
    """
    Update an existing pantry item.

    Args:
        user_id: User ID
        item_id: ID of the pantry item to update
        name: New name
        quantity: New quantity
        unit: New unit
        expiration_date: New expiration date (ISO format)

    Returns:
        {"success": True, "item_id": str} or {"success": False, "error": str}
    """
    # Filter out None values to build updates dict
    updates = {
        k: v
        for k, v in {
            "name": name,
            "quantity": quantity,
            "unit": unit,
            "expiration_date": expiration_date,
        }.items()
        if v is not None
    }

    if not updates:
        return {"success": False, "error": "No update fields provided"}

    # Verify item exists
    pantry = await firestore_client.get_pantry(user_id)
    existing = next((item for item in pantry if item.get("id") == item_id), None)

    if not existing:
        return {"success": False, "error": f"Pantry item '{item_id}' not found"}

    # Merge updates with existing item
    item_data = {**existing, **updates, "id": item_id}

    try:
        result_id = await firestore_client.update_pantry_item(user_id, item_data)
        return {"success": True, "status": "updated", "item_id": result_id}
    except Exception as e:
        return {**tool_error(e, "updating pantry item"), "success": False}


@tool(
    name="dev.fcp.inventory.delete_pantry_item",
    description="Delete a pantry item",
    category="inventory",
    requires_write=True,
)
async def delete_pantry_item(
    user_id: str,
    item_id: str,
) -> dict[str, Any]:
    """
    Delete a pantry item.

    Args:
        user_id: User ID
        item_id: ID of the pantry item to delete

    Returns:
        {"success": True} or {"success": False, "error": str}
    """
    try:
        deleted = await firestore_client.delete_pantry_item(user_id, item_id)
        if deleted:
            return {"success": True, "status": "deleted"}
        return {"success": False, "error": f"Pantry item '{item_id}' not found"}
    except Exception as e:
        return {**tool_error(e, "deleting pantry item"), "success": False}


async def suggest_meals_from_pantry(
    user_id: str,
    prioritize_expiring: bool = True,
) -> dict[str, Any]:
    """
    Suggest meals based on current pantry inventory.

    Args:
        user_id: User ID
        prioritize_expiring: Prioritize items expiring soon

    Returns:
        {"suggestions": [{"meal": str, "uses_ingredients": [...], "missing": [...]}]}
    """
    pantry = await firestore_client.get_pantry(user_id)
    pantry_items = [item["name"] for item in pantry]

    if not pantry_items:
        return {"suggestions": [], "message": "Pantry is empty"}

    # Get expiring items to prioritize
    expiring = []
    if prioritize_expiring:
        check = await check_expiring_items(user_id, days_threshold=5)
        expiring = [item["name"] for item in check["expiring_soon"]]

    prompt = f"""Suggest 5 meals based on available ingredients.
Available ingredients: {pantry_items}
Expiring soon (prioritize these): {expiring}

For each meal, list which pantry ingredients it uses and any common items that might be missing.
Return JSON: {{
    "suggestions": [
        {{
            "meal": "...",
            "description": "...",
            "uses_ingredients": ["..."],
            "missing_common": ["..."],
            "difficulty": "easy|medium|hard",
            "cook_time_minutes": 30
        }}
    ]
}}"""

    result = await gemini.generate_json(prompt)

    # Handle list response
    if isinstance(result, list) and result:
        result = result[0]

    return result
