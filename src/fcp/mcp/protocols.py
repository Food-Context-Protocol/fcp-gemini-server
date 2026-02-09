"""Protocol interfaces for dependency injection.

These define the contracts that dependencies must satisfy.
Using protocols allows for easy testing with mocks.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Database(Protocol):
    """Database interface for tool dependencies.

    This protocol defines the contract for database operations.
    Tools depend on this interface, not concrete implementations.
    """

    async def get_user_logs(
        self,
        user_id: str,
        *,
        limit: int = 10,
        days: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Get user food logs."""
        ...

    async def get_log(self, user_id: str, log_id: str) -> dict[str, Any] | None:
        """Get a specific log by ID."""
        ...

    async def get_logs_by_ids(self, user_id: str, log_ids: list[str]) -> list[dict[str, Any]]:
        """Get multiple logs by their IDs."""
        ...

    async def create_log(self, user_id: str, data: dict[str, Any]) -> str:
        """Create a new log and return its ID."""
        ...

    async def update_log(self, user_id: str, log_id: str, updates: dict[str, Any]) -> None:
        """Update an existing log."""
        ...

    async def delete_log(self, user_id: str, log_id: str) -> None:
        """Delete a log (soft delete)."""
        ...

    async def get_pantry(self, user_id: str) -> list[dict[str, Any]]:
        """Get user's pantry items."""
        ...

    async def add_pantry_item(self, user_id: str, data: dict[str, Any]) -> str:
        """Add item to pantry."""
        ...

    async def update_pantry_item(self, user_id: str, item_id: str, updates: dict[str, Any]) -> None:
        """Update pantry item."""
        ...

    async def update_pantry_items_batch(self, user_id: str, items_data: list[dict[str, Any]]) -> list[str]:
        """Batch update pantry items."""
        ...

    async def delete_pantry_item(self, user_id: str, item_id: str) -> None:
        """Delete pantry item."""
        ...

    async def get_user_preferences(self, user_id: str) -> dict[str, Any]:
        """Get user preferences and dietary profile."""
        ...

    async def get_recipes(
        self,
        user_id: str,
        *,
        limit: int = 20,
        archived: bool = False,
    ) -> list[dict[str, Any]]:
        """Get user's saved recipes."""
        ...

    async def get_recipe(self, user_id: str, recipe_id: str) -> dict[str, Any] | None:
        """Get a specific recipe."""
        ...

    async def save_recipe(self, user_id: str, data: dict[str, Any]) -> str:
        """Save a new recipe."""
        ...

    async def update_recipe(self, user_id: str, recipe_id: str, updates: dict[str, Any]) -> None:
        """Update a recipe."""
        ...

    async def delete_recipe(self, user_id: str, recipe_id: str) -> None:
        """Delete a recipe."""
        ...


@runtime_checkable
class AIService(Protocol):
    """AI service interface for tool dependencies.

    This protocol defines the contract for AI operations.
    Allows easy mocking of Gemini API in tests.
    """

    async def generate_content(
        self,
        prompt: str,
        image_url: str | None = None,
        media_url: str | None = None,
    ) -> str:
        """Generate text content from prompt."""
        ...

    async def generate_json(
        self,
        prompt: str,
        image_url: str | None = None,
        media_url: str | None = None,
        image_bytes: bytes | None = None,
        image_mime_type: str | None = None,
    ) -> dict[str, Any]:
        """Generate JSON-structured response."""
        ...

    async def analyze_image(
        self,
        image_url: str,
        prompt: str,
        detail: str = "auto",
    ) -> dict[str, Any]:
        """Analyze an image and return structured results."""
        ...

    async def analyze_video(
        self,
        video_url: str,
        prompt: str,
    ) -> dict[str, Any]:
        """Analyze a video and return structured results."""
        ...

    async def analyze_audio(
        self,
        audio_url: str,
        prompt: str,
    ) -> dict[str, Any]:
        """Analyze audio and return structured results."""
        ...

    async def use_search_grounding(
        self,
        prompt: str,
        dynamic_threshold: float = 0.3,
    ) -> dict[str, Any]:
        """Generate content with Google Search grounding."""
        ...

    async def use_thinking_mode(
        self,
        prompt: str,
        thinking_budget: str = "medium",
    ) -> dict[str, Any]:
        """Use extended thinking mode for complex reasoning."""
        ...

    async def execute_code(
        self,
        prompt: str,
    ) -> dict[str, Any]:
        """Generate and execute Python code in sandbox."""
        ...


@runtime_checkable
class HTTPClient(Protocol):
    """HTTP client interface for external API calls.

    Used for calling external services like OpenFoodFacts,
    Google Places, safety databases, etc.
    """

    async def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> Any:
        """Send GET request."""
        ...

    async def post(
        self,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> Any:
        """Send POST request."""
        ...

    async def aclose(self) -> None:
        """Close the HTTP client."""
        ...
