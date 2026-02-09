"""Knowledge Graph Routes.

Food knowledge enrichment endpoints:
- POST /knowledge/enrich/{log_id} - Enrich a food log with OFF/USDA data
- GET /knowledge/search/{query} - Search USDA and OFF databases
- GET /knowledge/compare - Compare nutrition between two foods
- GET /knowledge/cache/{food_name} - Get cached knowledge for a food
"""

from typing import Any

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel

from fcp.auth import AuthenticatedUser, get_current_user, require_write_access
from fcp.routes.router import APIRouter
from fcp.tools import knowledge_graph

router = APIRouter()


# --- Request Models ---


class EnrichRequest(BaseModel):
    """Request model for knowledge enrichment."""

    include_sustainability: bool = True
    include_micronutrients: bool = True


# --- Routes ---


@router.post("/knowledge/enrich/{log_id}")
async def enrich_log(
    log_id: str,
    request: EnrichRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Enrich a food log with OFF/USDA knowledge data.

    Combines data from USDA FoodData Central (micronutrients) and
    Open Food Facts (sustainability scores, additives) to provide
    comprehensive food knowledge.
    """
    result = await knowledge_graph.enrich_with_knowledge_graph(
        user.user_id,
        log_id,
        include_sustainability=request.include_sustainability,
        include_micronutrients=request.include_micronutrients,
    )

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))

    return result


@router.get("/knowledge/search/{query}")
async def search(
    query: str,
    _user: AuthenticatedUser = Depends(get_current_user),  # Auth required but not used in search
) -> dict[str, Any]:
    """Search USDA and OFF databases for food information.

    Returns results from both databases for the given query.
    Requires authentication but results are not user-specific.
    """
    return await knowledge_graph.search_knowledge(query)


@router.get("/knowledge/compare")
async def compare(
    food1: str = Query(..., description="First food to compare"),
    food2: str = Query(..., description="Second food to compare"),
    _user: AuthenticatedUser = Depends(get_current_user),  # Auth required but not used
) -> dict[str, Any]:
    """Compare nutrition between two foods.

    Uses USDA FoodData Central to compare micronutrients.
    Returns 503 if USDA API is not configured, 404 if food not found.
    """
    result = await knowledge_graph.compare_foods(food1, food2)

    if not result.get("success"):
        # Distinguish between service unavailable and not found
        error_code = result.get("error_code")
        if error_code == "SERVICE_UNAVAILABLE":
            raise HTTPException(status_code=503, detail=result.get("error"))
        raise HTTPException(status_code=404, detail=result.get("error"))

    return result


@router.get("/knowledge/cache/{food_name}")
async def get_cached(
    food_name: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get cached knowledge graph data for a food.

    Returns an envelope indicating cache status:
    - {cached: true, ...data} on cache hit
    - {cached: false} on cache miss (returns 200, not 404)
    """
    cached = await knowledge_graph.get_cached_knowledge(user.user_id, food_name)

    return {"cached": True, **cached} if cached else {"cached": False}
