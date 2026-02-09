"""Google Ecosystem Connector tools."""

from typing import Any

from fcp.mcp.registry import tool


@tool(
    name="dev.fcp.connectors.sync_to_calendar",
    description="Sync a culinary event to Google Calendar",
    category="connectors",
    requires_write=True,
)
async def sync_to_calendar(
    user_id: str, event_title: str, start_time: str, description: str | None = None
) -> dict[str, Any]:
    """
    Sync a culinary event (meal prep, reservation) to Google Calendar.
    Note: In a real app, this would use the Google Calendar API.
    For this prototype, we generate the structured event data.
    """
    return {
        "status": "prepared",
        "service": "Google Calendar",
        "event_id": "mock-event-123",
        "event": {
            "summary": event_title,
            "description": description,
            "start": {"dateTime": start_time},
            "end": {"dateTime": start_time},  # simplified
        },
    }


@tool(
    name="dev.fcp.connectors.save_to_drive",
    description="Save a recipe or report to a Google Drive folder",
    category="connectors",
    requires_write=True,
)
async def save_to_drive(user_id: str, filename: str, content: str, folder: str = "FoodLog") -> dict[str, Any]:
    """
    Save a recipe or report to a Google Drive folder.
    """
    return {
        "status": "prepared",
        "service": "Google Drive",
        "file_id": "mock-file-123",
        "file": {"name": filename, "folder": folder, "mimeType": "text/markdown"},
    }
