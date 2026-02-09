"""Demo recording for MCP tool calls.

Captures tool execution results for replay in demo mode.
Recordings are stored as JSON files and can be used to provide
realistic demo experiences without requiring live API calls.

Usage:
    from fcp.utils.demo_recording import should_record_tool, save_recording, DemoRecording

    if should_record_tool("get_recent_meals"):
        recording = DemoRecording(
            tool_name="get_recent_meals",
            arguments={"limit": 10},
            response={"meals": [...]},
            duration_seconds=0.5,
            status="success",
        )
        save_recording(recording)

Environment Variables:
    FCP_DEMO_RECORDING: Set to "true" to enable recording
    FCP_RECORDING_PATH: Directory for recordings (default: ~/.fcp/demo_recordings)
"""

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Environment variable to enable recording mode
RECORDING_ENABLED = os.environ.get("FCP_DEMO_RECORDING", "false").lower() == "true"

# Path for recording output
RECORDING_PATH = Path(os.environ.get("FCP_RECORDING_PATH", "~/.fcp/demo_recordings")).expanduser()

# Tools to record for demo (top 5 from requirements)
DEMO_RECORDING_TOOLS = frozenset(
    {
        "get_recent_meals",
        "get_taste_profile",
        "get_meal_suggestions",
        "search_meals",
        "lookup_product",
    }
)

# Schema version for recordings
RECORDING_SCHEMA_VERSION = "1.0"

# Fields to redact from recordings
SENSITIVE_FIELDS = frozenset({"user_id", "email", "phone", "address", "token", "api_key", "password"})


class DemoRecording:
    """Represents a single tool execution recording."""

    def __init__(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        response: Any,
        duration_seconds: float,
        status: str,
        error_message: str | None = None,
    ):
        self.tool_name = tool_name
        self.arguments = arguments
        self.response = response
        self.duration_seconds = duration_seconds
        self.status = status
        self.error_message = error_message
        self.timestamp = datetime.now(UTC).isoformat()
        self.schema_version = RECORDING_SCHEMA_VERSION

    def sanitize_for_storage(self) -> dict[str, Any]:
        """Sanitize recording for storage, removing PII."""
        return {
            "schema_version": self.schema_version,
            "tool_name": self.tool_name,
            "timestamp": self.timestamp,
            "arguments": self._sanitize_dict(self.arguments),
            "response": self._sanitize_response(self.response),
            "duration_seconds": round(self.duration_seconds, 3),
            "status": self.status,
            "error_message": self.error_message,
        }

    def _sanitize_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Sanitize a dictionary, redacting sensitive fields recursively."""
        sanitized: dict[str, Any] = {
            k: ("[REDACTED]" if k in SENSITIVE_FIELDS else self._sanitize_response(v)) for k, v in data.items()
        }
        return sanitized

    def _sanitize_response(self, response: Any) -> Any:
        """Sanitize response data, removing user-specific information."""
        if isinstance(response, dict):
            return {
                k: ("[REDACTED]" if k in SENSITIVE_FIELDS else self._sanitize_response(v)) for k, v in response.items()
            }
        elif isinstance(response, list):
            return [self._sanitize_response(item) for item in response]
        return response


def should_record_tool(tool_name: str) -> bool:
    """Check if a tool should be recorded.

    Args:
        tool_name: Name of the MCP tool

    Returns:
        True if recording is enabled and tool is in the allowlist
    """
    return RECORDING_ENABLED and tool_name in DEMO_RECORDING_TOOLS


def save_recording(recording: DemoRecording) -> Path | None:
    """Save a recording to disk in JSON format.

    File structure:
    ~/.fcp/demo_recordings/
        get_recent_meals/
            2026-02-03T10-30-00.json
            2026-02-03T11-45-00.json
        get_taste_profile/
            ...

    Args:
        recording: The DemoRecording to save

    Returns:
        Path to saved file, or None if save failed
    """
    if not RECORDING_ENABLED:
        return None

    try:
        tool_dir = RECORDING_PATH / recording.tool_name
        tool_dir.mkdir(parents=True, exist_ok=True)

        # Use timestamp as filename (replace colons for filesystem compatibility)
        filename = recording.timestamp.replace(":", "-").replace("+", "_") + ".json"
        filepath = tool_dir / filename

        with open(filepath, "w") as f:
            json.dump(recording.sanitize_for_storage(), f, indent=2, default=str)

        logger.info("Demo recording saved: %s", filepath)
        return filepath

    except Exception as e:
        logger.warning("Failed to save demo recording: %s", e)
        return None


def load_recordings(tool_name: str, limit: int = 10) -> list[dict[str, Any]]:
    """Load recent recordings for a tool.

    Args:
        tool_name: The tool to load recordings for
        limit: Maximum recordings to return

    Returns:
        List of recording dicts, newest first
    """
    tool_dir = RECORDING_PATH / tool_name
    if not tool_dir.exists():
        return []

    recordings = []
    for filepath in sorted(tool_dir.glob("*.json"), reverse=True)[:limit]:
        try:
            with open(filepath) as f:
                recordings.append(json.load(f))
        except Exception as e:
            logger.warning("Failed to load recording %s: %s", filepath, e)

    return recordings


def get_cached_response(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
    """Get a cached response for demo replay.

    Finds the most recent recording for the tool that matches the arguments
    (ignoring user_id and other sensitive fields).

    Args:
        tool_name: The tool name
        arguments: The tool arguments

    Returns:
        Cached response dict, or None if no match found
    """
    if tool_name not in DEMO_RECORDING_TOOLS:
        return None

    recordings = load_recordings(tool_name, limit=5)
    if not recordings:
        return None

    # Normalize arguments for comparison (remove sensitive fields)
    normalized_args = {k: v for k, v in arguments.items() if k not in SENSITIVE_FIELDS}

    for recording in recordings:
        recorded_args = {k: v for k, v in recording.get("arguments", {}).items() if k not in SENSITIVE_FIELDS}
        if recorded_args == normalized_args:
            return recording.get("response")

    # If no exact match, return the most recent recording's response
    return recordings[0].get("response") if recordings else None
