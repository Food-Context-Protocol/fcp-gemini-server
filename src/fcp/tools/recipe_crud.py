"""Recipe CRUD tools for FCP.

Provides functions for managing user's saved recipes:
- list_recipes: List user's saved recipes
- get_recipe: Get a single recipe by ID
- save_recipe: Save a new recipe
- update_recipe: Update an existing recipe
- favorite_recipe: Toggle favorite status
- archive_recipe: Archive a recipe (soft delete)
- delete_recipe: Permanently delete a recipe
"""

import logging
from typing import Any, cast

from fcp.mcp.protocols import Database
from fcp.mcp.registry import tool
from fcp.services.firestore import get_firestore_client

logger = logging.getLogger(__name__)


@tool(
    name="dev.fcp.recipes.list",
    description="List user's saved recipes",
    category="recipes",
    requires_write=False,
    dependencies={"db"},
)
async def list_recipes_tool(
    user_id: str,
    limit: int = 50,
    include_archived: bool = False,
    favorites_only: bool = False,
    db: Database | None = None,
) -> dict[str, Any]:
    """MCP tool wrapper for list_recipes."""
    recipes = await list_recipes(user_id, limit, include_archived, favorites_only, db)
    return {"recipes": recipes}


async def list_recipes(
    user_id: str,
    limit: int = 50,
    include_archived: bool = False,
    favorites_only: bool = False,
    db: Database | None = None,
) -> list[dict[str, Any]]:
    """
    List user's saved recipes.

    Args:
        user_id: User ID
        limit: Maximum number of recipes to return
        include_archived: Include archived recipes
        favorites_only: Only return favorite recipes
        db: Injected database dependency

    Returns:
        List of recipe dictionaries
    """
    db = db or cast(Database, get_firestore_client())
    return await db.get_recipes(
        user_id,
        limit=limit,
        include_archived=include_archived,
        favorites_only=favorites_only,
    )


@tool(
    name="dev.fcp.recipes.get",
    description="Get a single recipe by ID from the user's saved recipes",
    category="recipes",
    requires_write=False,
    dependencies={"db"},
)
async def get_recipe(user_id: str, recipe_id: str, db: Database | None = None) -> dict[str, Any] | None:
    """
    Get a single recipe by ID.

    Args:
        user_id: User ID
        recipe_id: Recipe ID

    Returns:
        Recipe dictionary or None if not found
    """
    # Use injected db or fall back to production client for backward compatibility
    db = db or cast(Database, get_firestore_client())
    return await db.get_recipe(user_id, recipe_id)


@tool(
    name="dev.fcp.recipes.save",
    description="Save a new recipe to the user's collection",
    category="recipes",
    requires_write=True,
    dependencies={"db"},
)
async def save_recipe(
    user_id: str,
    name: str,
    ingredients: list[str],
    instructions: list[str] | None = None,
    servings: int = 4,
    description: str | None = None,
    prep_time_minutes: int | None = None,
    cook_time_minutes: int | None = None,
    cuisine: str | None = None,
    tags: list[str] | None = None,
    source: str | None = None,
    source_meal_id: str | None = None,
    image_url: str | None = None,
    nutrition: dict[str, Any] | None = None,
    db: Database | None = None,
) -> dict[str, Any]:
    """
    Save a new recipe.

    Args:
        user_id: User ID
        name: Recipe name (required)
        ingredients: List of ingredients (required)
        instructions: Step-by-step cooking instructions
        servings: Number of servings
        description: Recipe description
        prep_time_minutes: Preparation time in minutes
        cook_time_minutes: Cooking time in minutes
        cuisine: Cuisine type (e.g., "Italian", "Mexican")
        tags: List of tags (e.g., ["vegetarian", "quick"])
        source: Recipe source (URL or "homemade")
        source_meal_id: ID of meal this recipe was created from
        image_url: URL to recipe image
        nutrition: Nutrition information
        db: Injected database dependency

    Returns:
        {"success": True, "recipe_id": str} or {"success": False, "error": str}
    """
    if not name:
        return {"success": False, "error": "Recipe name is required"}
    if not ingredients:
        return {"success": False, "error": "Ingredients are required"}

    db = db or cast(Database, get_firestore_client())

    recipe_data = {
        "name": name,
        "ingredients": ingredients,
        "instructions": instructions or [],
        "servings": servings,
        "description": description,
        "prep_time_minutes": prep_time_minutes,
        "cook_time_minutes": cook_time_minutes,
        "cuisine": cuisine,
        "tags": tags or [],
        "source": source,
        "source_meal_id": source_meal_id,
        "image_url": image_url,
        "nutrition": nutrition,
    }

    # Remove None values
    recipe_data = {k: v for k, v in recipe_data.items() if v is not None}

    try:
        recipe_id = await db.create_recipe(user_id, recipe_data)
        return {"success": True, "status": "saved", "recipe_id": recipe_id}

    except Exception as e:
        logger.exception("Error saving recipe")
        return {"success": False, "error": str(e)}


async def update_recipe(
    user_id: str,
    recipe_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """
    Update an existing recipe.

    Args:
        user_id: User ID
        recipe_id: Recipe ID
        updates: Fields to update

    Returns:
        {"success": True} or {"success": False, "error": str}
    """
    if not updates:
        return {"success": False, "error": "No update fields provided"}

    db = get_firestore_client()

    # Verify recipe exists
    existing = await db.get_recipe(user_id, recipe_id)
    if not existing:
        return {"success": False, "error": f"Recipe '{recipe_id}' not found"}

    try:
        success = await db.update_recipe(user_id, recipe_id, updates)
        if success:
            return {"success": True}
        return {"success": False, "error": "Update failed"}
    except Exception as e:
        logger.exception("Error updating recipe")
        return {"success": False, "error": str(e)}


@tool(
    name="dev.fcp.recipes.favorite",
    description="Mark or unmark a recipe as favorite",
    category="recipes",
    requires_write=True,
    dependencies={"db"},
)
async def favorite_recipe(
    user_id: str,
    recipe_id: str,
    is_favorite: bool = True,
    db: Database | None = None,
) -> dict[str, Any]:
    """
    Mark or unmark a recipe as favorite.

    Args:
        user_id: User ID
        recipe_id: Recipe ID
        is_favorite: True to mark as favorite, False to unmark
        db: Injected database dependency

    Returns:
        {"success": True, "is_favorite": bool} or {"success": False, "error": str}
    """
    db = db or cast(Database, get_firestore_client())

    # Verify recipe exists
    existing = await db.get_recipe(user_id, recipe_id)
    if not existing:
        return {"success": False, "error": f"Recipe '{recipe_id}' not found"}

    try:
        success = await db.update_recipe(user_id, recipe_id, {"is_favorite": is_favorite})
        if success:
            return {"success": True, "status": "favorited", "is_favorite": is_favorite}

        return {"success": False, "error": "Update failed"}
    except Exception as e:
        logger.exception("Error updating recipe favorite status")
        return {"success": False, "error": str(e)}


@tool(
    name="dev.fcp.recipes.archive",
    description="Archive a recipe (soft delete)",
    category="recipes",
    requires_write=True,
    dependencies={"db"},
)
async def archive_recipe(
    user_id: str,
    recipe_id: str,
    db: Database | None = None,
) -> dict[str, Any]:
    """
    Archive a recipe (soft delete).

    Args:
        user_id: User ID
        recipe_id: Recipe ID
        db: Injected database dependency

    Returns:
        {"success": True} or {"success": False, "error": str}
    """
    db = db or cast(Database, get_firestore_client())

    # Verify recipe exists
    existing = await db.get_recipe(user_id, recipe_id)
    if not existing:
        return {"success": False, "error": f"Recipe '{recipe_id}' not found"}

    try:
        success = await db.update_recipe(user_id, recipe_id, {"is_archived": True})
        if success:
            return {"success": True, "status": "archived"}

        return {"success": False, "error": "Archive failed"}
    except Exception as e:
        logger.exception("Error archiving recipe")
        return {"success": False, "error": str(e)}


@tool(
    name="dev.fcp.recipes.delete",
    description="Permanently delete a recipe",
    category="recipes",
    requires_write=True,
    dependencies={"db"},
)
async def delete_recipe(
    user_id: str,
    recipe_id: str,
    db: Database | None = None,
) -> dict[str, Any]:
    """
    Permanently delete a recipe.

    Args:
        user_id: User ID
        recipe_id: Recipe ID
        db: Injected database dependency

    Returns:
        {"success": True} or {"success": False, "error": str}
    """
    db = db or cast(Database, get_firestore_client())

    try:
        deleted = await db.delete_recipe(user_id, recipe_id)
        if deleted:
            return {"success": True, "status": "deleted"}
        return {"success": False, "error": f"Recipe '{recipe_id}' not found"}
    except Exception as e:
        logger.exception("Error deleting recipe")
        return {"success": False, "error": str(e)}
