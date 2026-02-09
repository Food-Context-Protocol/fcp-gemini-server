"""CRUD operations for food logs and pantry items."""

from datetime import datetime
from typing import Any, cast

from fcp.mcp.protocols import Database
from fcp.mcp.registry import tool
from fcp.services.firestore import firestore_client
from fcp.services.mapper import to_schema_org_recipe


@tool(
    name="dev.fcp.nutrition.get_recent_meals",
    description="Get recent meals from the user's nutrition log",
    category="nutrition",
    requires_write=False,
    dependencies={"db"},
)
async def get_recent_meals_tool(
    user_id: str,
    limit: int = 10,
    days: int | None = None,
    include_nutrition: bool = False,
    output_format: str | None = None,
    db: Database | None = None,
) -> dict[str, Any]:
    """MCP tool wrapper for get_meals."""
    meals = await get_meals(
        user_id=user_id,
        limit=limit,
        days=days,
        include_nutrition=include_nutrition,
        output_format=output_format,
        db=db,
    )
    return {"meals": meals}


async def get_meals(
    user_id: str,
    limit: int = 10,
    days: int | None = None,
    include_nutrition: bool = False,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    output_format: str | None = None,
    db: Database | None = None,
) -> list[dict[str, Any]]:
    """Get recent meals for a user."""
    # Use injected db or fall back to production client for backward compatibility
    db = db or cast(Database, firestore_client)
    logs = await db.get_user_logs(user_id, limit=limit, days=days, start_date=start_date, end_date=end_date)

    if not include_nutrition:
        for log in logs:
            log.pop("nutrition", None)

    if output_format == "schema_org":
        return [to_schema_org_recipe(meal) for meal in logs]

    return logs


async def get_meal(user_id: str, log_id: str) -> dict[str, Any] | None:
    """Get a specific meal."""
    return await firestore_client.get_log(user_id, log_id)


async def get_meals_by_ids(user_id: str, log_ids: list[str]) -> list[dict[str, Any]]:
    """
    Get multiple meals by their IDs in a batch.

    More efficient than calling get_meal in a loop (avoids N+1 queries).
    Returns only logs that exist, in no particular order.
    """
    if not log_ids:
        return []

    return await firestore_client.get_logs_by_ids(user_id, log_ids)


@tool(
    name="dev.fcp.nutrition.add_meal",
    description="Add a new meal to the user's nutrition log",
    category="nutrition",
    requires_write=True,
    dependencies={"db"},
)
async def add_meal(
    user_id: str,
    dish_name: str,
    venue: str | None = None,
    notes: str | None = None,
    image_path: str | None = None,
    db: Database | None = None,
) -> dict[str, Any]:
    """Add a new meal and trigger pantry deduction."""
    # Use injected db or fall back to production client for backward compatibility
    db = db or cast(Database, firestore_client)
    data = {
        "dish_name": dish_name,
        "venue_name": venue,
        "notes": notes,
        "image_path": image_path,
        "processing_status": "pending",
    }
    log_id = await db.create_log(user_id, data)
    return {"success": True, "log_id": log_id}


async def update_meal(
    user_id: str,
    log_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Update an existing meal."""
    # 1. Check if log exists
    log = await firestore_client.get_log(user_id, log_id)
    if not log:
        return {"success": False, "error": "Log not found"}

    # 2. Filter allowed fields
    allowed_fields = {
        "dish_name",
        "venue_name",
        "notes",
        "rating",
        "tags",
        "public",
        "image_path",
    }
    valid_updates = {k: v for k, v in updates.items() if k in allowed_fields}

    if not valid_updates:
        return {"success": False, "error": "No valid fields to update"}

    try:
        await firestore_client.update_log(user_id, log_id, valid_updates)
        return {"success": True, "updated_fields": list(valid_updates.keys())}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="dev.fcp.nutrition.delete_meal",
    description="Delete a meal from the user's nutrition log (soft delete)",
    category="nutrition",
    requires_write=True,
    dependencies={"db"},
)
async def delete_meal(user_id: str, log_id: str, db: Database | None = None) -> dict[str, Any]:
    """Delete a meal (soft delete)."""
    # Use injected db or fall back to production client for backward compatibility
    db = db or cast(Database, firestore_client)
    # 1. Check if log exists
    log = await db.get_log(user_id, log_id)
    if not log:
        return {"success": False, "error": "Log not found"}

    try:
        # Soft delete
        await db.update_log(user_id, log_id, {"deleted": True})
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool(
    name="dev.fcp.business.donate_meal",
    description="Pledge a meal for donation to a food program",
    category="business",
    requires_write=True,
    dependencies={"db"},
)
async def donate_meal(
    user_id: str,
    log_id: str,
    organization: str = "Local Food Bank",
    db: Database | None = None,
) -> dict[str, Any]:
    """
    Pledge a meal for donation to a food program.

    Args:
        user_id: The user's ID.
        log_id: The meal log ID to donate.
        organization: Target organization (default: Local Food Bank).
        db: Injected database dependency.

    Returns:
        Success status and donation details.
    """
    # Use injected db or fall back to production client for backward compatibility
    db = db or cast(Database, firestore_client)

    # Verify meal exists
    meal = await db.get_log(user_id, log_id)
    if not meal:
        return {"success": False, "error": "Meal not found"}

    # Mark as donated
    try:
        await db.update_log(user_id, log_id, {"donated": True, "donation_organization": organization})
        return {
            "success": True,
            "status": "pledged",
            "log_id": log_id,
            "organization": organization,
            "message": f"Meal pledged for donation to {organization}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Pantry Operations (Phase 2) ---


@tool(
    name="dev.fcp.inventory.add_to_pantry",
    description="Add multiple items to the user's pantry inventory",
    category="inventory",
    requires_write=True,
    dependencies={"db"},
)
async def add_to_pantry(user_id: str, items: list[str], db: Database | None = None) -> list[str]:
    """Add multiple items to pantry."""
    # Use injected db or fall back to production client for backward compatibility
    db = db or cast(Database, firestore_client)
    items_data = [{"name": item, "quantity": 1, "status": "in_stock"} for item in items]
    return await db.update_pantry_items_batch(user_id, items_data)
