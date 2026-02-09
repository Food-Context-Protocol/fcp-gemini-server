"""Receipt and document parsing routes."""

from datetime import datetime
from typing import Any

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from fcp.auth import AuthenticatedUser, require_write_access
from fcp.routes.router import APIRouter
from fcp.tools.parser import add_items_from_receipt, parse_receipt

router = APIRouter()


# --- Request Models ---


class ParseReceiptRequest(BaseModel):
    """Request model for parsing a receipt."""

    image_url: str
    store_hint: str | None = None


class AddFromReceiptRequest(BaseModel):
    """Request model for adding parsed receipt items to pantry."""

    items: list[dict[str, Any]]
    purchase_date: str | None = None
    default_storage: str = "fridge"


# --- Routes ---


@router.post("/parse/receipt")
async def post_parse_receipt(
    request: ParseReceiptRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Parse receipt image and extract items."""
    result = await parse_receipt(
        request.image_url,
        store_hint=request.store_hint,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/parse/receipt/add-to-pantry")
async def post_add_receipt_to_pantry(
    request: AddFromReceiptRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Add parsed receipt items to pantry."""
    purchase_date = None
    if request.purchase_date:
        try:
            purchase_date = datetime.fromisoformat(request.purchase_date)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid purchase_date format") from e

    return await add_items_from_receipt(
        user.user_id,
        request.items,
        purchase_date=purchase_date,
        default_storage=request.default_storage,
    )
