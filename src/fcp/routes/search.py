"""Search Routes.

Semantic search endpoint for food logs.
"""

from fastapi import Depends, Request
from pydantic import BaseModel, Field, field_validator

from fcp.auth import AuthenticatedUser, require_write_access
from fcp.routes.router import APIRouter
from fcp.routes.schemas import SearchResponse
from fcp.security.input_sanitizer import sanitize_search_query
from fcp.security.rate_limit import RATE_LIMIT_SEARCH, limiter
from fcp.tools import search_meals

router = APIRouter()


# --- Request Models ---


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=100)

    @field_validator("query")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        return sanitize_search_query(v)


# --- Routes ---


@router.post("/search", response_model=SearchResponse)
@limiter.limit(RATE_LIMIT_SEARCH)
async def semantic_search(
    request: Request,
    search_request: SearchRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> SearchResponse:
    """Semantic search across food logs."""
    results = await search_meals(user.user_id, search_request.query, search_request.limit)
    return SearchResponse(results=results, query=search_request.query)
