"""Food Safety Routes.

Endpoints for food safety information using Google Search grounding:
- FDA recall checks
- Allergen alerts
- Restaurant safety info
- Drug-food interactions
- Seasonal safety tips
- Nutrition claim verification
"""

from typing import Any

from fastapi import Depends, Query, Request
from pydantic import BaseModel, Field

from fcp.auth import AuthenticatedUser, get_current_user, require_write_access
from fcp.routes.router import APIRouter
from fcp.security.rate_limit import RATE_LIMIT_SEARCH, limiter
from fcp.tools.safety import (
    check_allergen_alerts,
    check_drug_food_interactions,
    check_food_recalls,
    get_restaurant_safety_info,
    get_seasonal_food_safety,
    verify_nutrition_claim,
)

router = APIRouter()


@router.get("/recalls")
@limiter.limit(RATE_LIMIT_SEARCH)
async def get_food_recalls(
    request: Request,
    food_name: str = Query(..., min_length=1, max_length=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Check for FDA food recalls using Google Search grounding.

    Returns real-time recall information with sources.
    """
    return await check_food_recalls(food_name)


@router.get("/allergens")
@limiter.limit(RATE_LIMIT_SEARCH)
async def get_allergen_alerts(
    request: Request,
    food_name: str = Query(..., min_length=1, max_length=200),
    allergens: str = Query(..., min_length=1, max_length=500),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Check for allergen alerts and cross-contamination risks.

    Args:
        food_name: Name of the food to check
        allergens: Comma-separated list of allergens to check for
    """
    allergen_list = [a.strip() for a in allergens.split(",")]
    return await check_allergen_alerts(food_name, allergen_list)


@router.get("/restaurant/{restaurant_name}")
@limiter.limit(RATE_LIMIT_SEARCH)
async def get_restaurant_info(
    request: Request,
    restaurant_name: str,
    location: str | None = Query(default=None, max_length=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get real-time restaurant safety information.

    Uses Google Search grounding for current:
    - Health inspection scores
    - Recent reviews mentioning food safety
    - Operating status
    """
    return await get_restaurant_safety_info(restaurant_name, location)


@router.get("/drug-interactions")
@limiter.limit(RATE_LIMIT_SEARCH)
async def get_drug_interactions(
    request: Request,
    food_name: str = Query(..., min_length=1, max_length=200),
    medications: str = Query(..., min_length=1, max_length=500),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Check for drug-food interactions.

    Args:
        food_name: Name of the food
        medications: Comma-separated list of medications
    """
    medication_list = [m.strip() for m in medications.split(",")]
    return await check_drug_food_interactions(food_name, medication_list)


@router.get("/seasonal")
@limiter.limit(RATE_LIMIT_SEARCH)
async def get_seasonal_safety(
    request: Request,
    location: str = Query(..., min_length=1, max_length=200),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get seasonal food safety tips for a location.

    Returns grounded information about:
    - Foods to avoid this season
    - Storage tips for current weather
    - Local food safety alerts
    """
    return await get_seasonal_food_safety(location)


class NutritionClaimRequest(BaseModel):
    """Request model for nutrition claim verification."""

    claim: str = Field(..., min_length=1, max_length=500)
    food_name: str = Field(..., min_length=1, max_length=200)


# --- POST Request Models for CLI compatibility ---


class RecallsRequest(BaseModel):
    """Request model for food recalls check (CLI compatibility)."""

    food_items: list[str] = Field(..., min_length=1)
    user_id: str | None = None


class DrugInteractionsRequest(BaseModel):
    """Request model for drug-food interactions check (CLI compatibility)."""

    food_items: list[str] = Field(..., min_length=1)
    medications: list[str] = Field(..., min_length=1)
    user_id: str | None = None


class AllergenAlertsRequest(BaseModel):
    """Request model for allergen alerts check (CLI compatibility)."""

    food_items: list[str] = Field(..., min_length=1)
    allergies: list[str] = Field(..., min_length=1)
    user_id: str | None = None


# --- POST endpoints for CLI compatibility ---


@router.post("/recalls")
@limiter.limit(RATE_LIMIT_SEARCH)
async def post_food_recalls(
    request: Request,
    body: RecallsRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Check for FDA food recalls (POST version for CLI). Requires authentication."""
    food_name = ", ".join(body.food_items)
    return await check_food_recalls(food_name)


@router.post("/drug-interactions")
@limiter.limit(RATE_LIMIT_SEARCH)
async def post_drug_interactions(
    request: Request,
    body: DrugInteractionsRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Check for drug-food interactions (POST version for CLI). Requires authentication."""
    food_name = ", ".join(body.food_items)
    return await check_drug_food_interactions(food_name, body.medications)


@router.post("/allergens")
@limiter.limit(RATE_LIMIT_SEARCH)
async def post_allergen_alerts(
    request: Request,
    body: AllergenAlertsRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Check for allergen alerts (POST version for CLI). Requires authentication."""
    food_name = ", ".join(body.food_items)
    return await check_allergen_alerts(food_name, body.allergies)


@router.post("/verify-claim")
@limiter.limit(RATE_LIMIT_SEARCH)
async def verify_claim(
    request: Request,
    claim_request: NutritionClaimRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """
    Verify a nutrition or health claim about food. Requires authentication.

    Uses grounding to fact-check claims like:
    - "Avocados are high in protein"
    - "Eating carrots improves night vision"
    """
    return await verify_nutrition_claim(claim_request.claim, claim_request.food_name)
