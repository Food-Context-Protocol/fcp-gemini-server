"""Recipes Routes.

Recipe processing endpoints:
- POST /standardize-recipe - Convert recipe text to Schema.org/Recipe JSON-LD
- POST /scaling/scale-recipe - Scale recipe ingredients
- POST /recipes/extract - Extract structured recipe from media
- POST /recipes/generate - Generate a recipe from ingredients using Gemini

Recipe CRUD endpoints:
- GET /recipes - List user's saved recipes
- GET /recipes/{recipe_id} - Get a single recipe
- POST /recipes - Save a new recipe
- PATCH /recipes/{recipe_id} - Update a recipe
- POST /recipes/{recipe_id}/favorite - Toggle favorite status
- POST /recipes/{recipe_id}/archive - Archive a recipe
- DELETE /recipes/{recipe_id} - Delete a recipe
"""

from typing import Any

from fastapi import Depends, Query
from pydantic import BaseModel, Field

from fcp.auth import AuthenticatedUser, get_current_user, require_write_access
from fcp.routes.router import APIRouter
from fcp.tools import (
    archive_recipe,
    delete_recipe,
    extract_recipe_from_media,
    favorite_recipe,
    generate_recipe,
    get_recipe,
    list_recipes,
    save_recipe,
    scale_recipe,
    standardize_recipe,
    update_recipe,
)

router = APIRouter()


# --- Request Models ---


class StandardizeRecipeRequest(BaseModel):
    raw_text: str = Field(..., min_length=1)


class ScaleRecipeRequest(BaseModel):
    recipe_json: dict[str, Any]
    target_servings: int


class MultimodalRecipeRequest(BaseModel):
    image_url: str | None = Field(default=None)
    media_url: str | None = Field(default=None)
    additional_notes: str | None = Field(default=None)


class GenerateRecipeRequest(BaseModel):
    ingredients: list[str] = Field(..., min_length=1)
    dish_name: str | None = Field(default=None)
    cuisine: str | None = Field(default=None)
    dietary_restrictions: str | None = Field(default=None)


class SaveRecipeRequest(BaseModel):
    """Request model for saving a new recipe."""

    name: str = Field(..., min_length=1)
    ingredients: list[str] = Field(..., min_length=1)
    instructions: list[str] | None = Field(default=None)
    servings: int = Field(default=4, ge=1)
    description: str | None = Field(default=None)
    prep_time_minutes: int | None = Field(default=None, ge=0)
    cook_time_minutes: int | None = Field(default=None, ge=0)
    cuisine: str | None = Field(default=None)
    tags: list[str] | None = Field(default=None)
    source: str | None = Field(default=None)
    image_url: str | None = Field(default=None)


class UpdateRecipeRequest(BaseModel):
    """Request model for updating a recipe."""

    name: str | None = Field(default=None)
    ingredients: list[str] | None = Field(default=None)
    instructions: list[str] | None = Field(default=None)
    servings: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None)
    prep_time_minutes: int | None = Field(default=None, ge=0)
    cook_time_minutes: int | None = Field(default=None, ge=0)
    cuisine: str | None = Field(default=None)
    tags: list[str] | None = Field(default=None)
    source: str | None = Field(default=None)
    image_url: str | None = Field(default=None)


class FavoriteRecipeRequest(BaseModel):
    """Request model for toggling favorite status."""

    is_favorite: bool = Field(default=True)


# --- Routes ---


@router.post("/standardize-recipe")
async def post_standardize_recipe(
    recipe_request: StandardizeRecipeRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Convert unstructured recipe text into standard Schema.org/Recipe JSON-LD. Requires authentication."""
    return await standardize_recipe(recipe_request.raw_text)


@router.post("/scaling/scale-recipe")
async def post_scale_recipe(
    scaling_request: ScaleRecipeRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Scale recipe ingredients to a target number of servings. Requires authentication."""
    return await scale_recipe(scaling_request.recipe_json, scaling_request.target_servings)


@router.post("/recipes/extract")
async def post_extract_recipe(
    recipe_request: MultimodalRecipeRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Extract a structured recipe from an image, video, or audio file. Requires authentication."""
    return await extract_recipe_from_media(
        recipe_request.image_url,
        recipe_request.media_url,
        recipe_request.additional_notes,
    )


@router.post("/recipes/generate")
async def post_generate_recipe(
    recipe_request: GenerateRecipeRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Generate a recipe from a list of ingredients. Requires authentication."""
    return await generate_recipe(
        ingredients=recipe_request.ingredients,
        dish_name=recipe_request.dish_name,
        cuisine=recipe_request.cuisine,
        dietary_restrictions=recipe_request.dietary_restrictions,
    )


# --- Recipe CRUD Routes ---


@router.get("/recipes")
async def get_recipes_list(
    limit: int = Query(default=50, ge=1, le=100),
    include_archived: bool = Query(default=False),
    favorites_only: bool = Query(default=False),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List user's saved recipes."""
    recipes = await list_recipes(
        user_id=user.user_id,
        limit=limit,
        include_archived=include_archived,
        favorites_only=favorites_only,
    )
    return {"recipes": recipes}


@router.get("/recipes/{recipe_id}")
async def get_recipe_by_id(
    recipe_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a single recipe by ID."""
    recipe = await get_recipe(user_id=user.user_id, recipe_id=recipe_id)
    if recipe:
        return {"recipe": recipe}
    return {"error": f"Recipe '{recipe_id}' not found"}


@router.post("/recipes")
async def post_save_recipe(
    request: SaveRecipeRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Save a new recipe. Requires authentication."""
    return await save_recipe(
        user_id=user.user_id,
        name=request.name,
        ingredients=request.ingredients,
        instructions=request.instructions,
        servings=request.servings,
        description=request.description,
        prep_time_minutes=request.prep_time_minutes,
        cook_time_minutes=request.cook_time_minutes,
        cuisine=request.cuisine,
        tags=request.tags,
        source=request.source,
        image_url=request.image_url,
    )


@router.patch("/recipes/{recipe_id}")
async def patch_recipe(
    recipe_id: str,
    request: UpdateRecipeRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Update a recipe. Requires authentication."""
    if updates := {k: v for k, v in request.model_dump().items() if v is not None}:
        return await update_recipe(user_id=user.user_id, recipe_id=recipe_id, updates=updates)
    else:
        return {"success": False, "error": "No update fields provided"}


@router.post("/recipes/{recipe_id}/favorite")
async def post_favorite_recipe(
    recipe_id: str,
    request: FavoriteRecipeRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Toggle favorite status on a recipe. Requires authentication."""
    return await favorite_recipe(
        user_id=user.user_id,
        recipe_id=recipe_id,
        is_favorite=request.is_favorite,
    )


@router.post("/recipes/{recipe_id}/archive")
async def post_archive_recipe(
    recipe_id: str,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Archive a recipe (soft delete). Requires authentication."""
    return await archive_recipe(user_id=user.user_id, recipe_id=recipe_id)


@router.delete("/recipes/{recipe_id}")
async def delete_recipe_by_id(
    recipe_id: str,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Permanently delete a recipe. Requires authentication."""
    return await delete_recipe(user_id=user.user_id, recipe_id=recipe_id)
