"""External Routes.

External API integration endpoints:
- GET /external/lookup-product/{barcode} - Look up product via Open Food Facts
"""

from typing import Any

from fastapi import Depends, HTTPException

from fcp.auth import AuthenticatedUser, get_current_user
from fcp.routes.router import APIRouter
from fcp.tools.external.open_food_facts import lookup_product

router = APIRouter()


# --- Routes ---


@router.get("/external/lookup-product/{barcode}")
async def get_product_info(
    barcode: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Look up a food product by barcode using Open Food Facts."""
    result = await lookup_product(barcode)
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return result
