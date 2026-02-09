"""Social Routes.

Social media and content generation endpoints:
- POST /social/blog-post - Generate a blog post from a food log
"""

from typing import Any

from fastapi import Depends, HTTPException, Query

from fcp.auth import AuthenticatedUser, require_write_access
from fcp.routes.router import APIRouter
from fcp.tools import generate_blog_post, get_meal

router = APIRouter()


# --- Routes ---


@router.post("/social/blog-post")
async def post_generate_blog(
    log_id: str = Query(...),
    style: str = Query(default="lifestyle"),
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Generate a full blog post from a food log entry."""
    log = await get_meal(user.user_id, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    content = await generate_blog_post(log, style)
    return {"content": content}
