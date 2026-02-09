"""Connectors Routes.

External service integration endpoints:
- POST /connector/calendar - Sync event to Google Calendar
- POST /connector/drive - Save content to Google Drive
"""

from typing import Any

from fastapi import Depends
from pydantic import BaseModel

from fcp.auth import AuthenticatedUser, require_write_access
from fcp.routes.router import APIRouter
from fcp.tools import save_to_drive, sync_to_calendar

router = APIRouter()


# --- Request Models ---


class CalendarSyncRequest(BaseModel):
    event_title: str
    start_time: str
    description: str | None = None


class DriveSaveRequest(BaseModel):
    filename: str
    content: str
    folder: str = "FCP"


# --- Routes ---


@router.post("/connector/calendar")
async def post_sync_calendar(
    sync_request: CalendarSyncRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Sync a culinary event to Google Calendar."""
    return await sync_to_calendar(
        user.user_id,
        sync_request.event_title,
        sync_request.start_time,
        sync_request.description,
    )


@router.post("/connector/drive")
async def post_save_drive(
    save_request: DriveSaveRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """Save a recipe or report to a Google Drive folder."""
    return await save_to_drive(user.user_id, save_request.filename, save_request.content, save_request.folder)
