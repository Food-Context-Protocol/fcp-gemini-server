"""Inventory Routes.

Pantry inventory management endpoints:
- GET /inventory/pantry - Fetch user's pantry inventory
- POST /inventory/pantry - Add items to pantry
- PATCH /inventory/pantry/{item_id} - Update a pantry item
- DELETE /inventory/pantry/{item_id} - Delete a pantry item
- POST /inventory/pantry/deduct - Deduct ingredients from pantry
- GET /inventory/pantry/expiring - Check items nearing expiry
- GET /inventory/pantry/meal-suggestions - Get meal suggestions from pantry items
- GET /inventory/suggestions - Get recipe suggestions from pantry (legacy)
- GET /inventory/expiry - Check items nearing expiry (legacy)
"""

from typing import Any

from fastapi import Depends, Query
from pydantic import BaseModel

from fcp.auth import AuthenticatedUser, get_current_user, require_write_access
from fcp.routes.router import APIRouter
from fcp.tools import (
    add_to_pantry,
    check_pantry_expiry,
    delete_pantry_item,
    suggest_recipe_from_pantry,
    update_pantry_item,
)
from fcp.tools.inventory import check_expiring_items, deduct_from_pantry, suggest_meals_from_pantry

router = APIRouter()


# --- Request Models ---


class PantryItemsRequest(BaseModel):
    items: list[str]


class DeductRequest(BaseModel):
    """Request model for deducting ingredients from pantry."""

    ingredients: list[str]
    servings: int = 1


class UpdatePantryItemRequest(BaseModel):
    """Request model for updating a pantry item."""

    name: str | None = None
    quantity: float | None = None
    unit: str | None = None
    expiration_date: str | None = None


# --- Routes ---


@router.get("/inventory/pantry")
async def get_user_pantry(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Fetch user's current pantry inventory."""
    from fcp.services.firestore import get_firestore_client

    db = get_firestore_client()
    items = await db.get_pantry(user.user_id)
    return {"items": items}


@router.post("/inventory/pantry")
async def post_add_to_pantry(
    pantry_request: PantryItemsRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Add items to your virtual pantry inventory. Requires authentication."""
    ids = await add_to_pantry(user.user_id, pantry_request.items)
    return {"added_ids": ids}


@router.patch("/inventory/pantry/{item_id}")
async def patch_pantry_item(
    item_id: str,
    request: UpdatePantryItemRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Update a pantry item. Requires authentication."""
    if updates := {k: v for k, v in request.model_dump().items() if v is not None}:
        return await update_pantry_item(user.user_id, item_id, updates)
    else:
        return {"success": False, "error": "No update fields provided"}


@router.delete("/inventory/pantry/{item_id}")
async def delete_pantry_item_route(
    item_id: str,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Delete a pantry item. Requires authentication."""
    return await delete_pantry_item(user.user_id, item_id)


@router.get("/inventory/suggestions")
async def get_pantry_recipe_suggestions(
    context: str = Query(default="dinner"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Suggest recipes based on what is currently in your virtual pantry."""
    return await suggest_recipe_from_pantry(user.user_id, context)


@router.get("/inventory/expiry")
async def get_pantry_expiry_check(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Scan your virtual pantry and identify items nearing expiry."""
    return await check_pantry_expiry(user.user_id)


@router.post("/inventory/pantry/deduct")
async def post_deduct_ingredients(
    request: DeductRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Deduct ingredients from pantry after cooking. Requires authentication."""
    return await deduct_from_pantry(
        user.user_id,
        request.ingredients,
        request.servings,
    )


@router.get("/inventory/pantry/expiring")
async def get_expiring_items(
    days: int = Query(default=3, ge=1, le=30),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get items expiring within specified days."""
    return await check_expiring_items(user.user_id, days_threshold=days)


@router.get("/inventory/pantry/meal-suggestions")
async def get_pantry_meal_suggestions(
    prioritize_expiring: bool = Query(default=True),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get meal suggestions based on pantry contents."""
    return await suggest_meals_from_pantry(user.user_id, prioritize_expiring)
