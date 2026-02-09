"""Firestore-compatible client with pluggable backends.

This module provides a unified interface that works with either:
- SQLite (default, for local development)
- Cloud Firestore (for production on Cloud Run)

Backend selection is controlled by DATABASE_BACKEND environment variable:
- DATABASE_BACKEND=sqlite (default) - uses SQLite
- DATABASE_BACKEND=firestore - uses Cloud Firestore
"""

import logging
import os
import threading
from datetime import datetime
from functools import lru_cache
from typing import Any

# Import Database at module level for test patching
from fcp.services.database import Database

logger = logging.getLogger(__name__)


class FirestoreClient:
    """Unified database client with pluggable backend (SQLite or Firestore)."""

    def __init__(self, backend: str | None = None, db: Any = None):
        """Initialize client with specified backend or inject a database instance.

        Args:
            backend: "sqlite" or "firestore". If None, reads from DATABASE_BACKEND env var.
                     Defaults to "sqlite" if not specified.
            db: Optional database instance for dependency injection (testing).
                If provided, this takes precedence over backend selection.
        """
        # Support dependency injection for testing
        if db is not None:
            self._db = db
            logger.info("Using injected database instance")
            return

        backend_type = backend or os.environ.get("DATABASE_BACKEND", "sqlite")

        if backend_type == "firestore":
            from fcp.services.firestore_backend import FirestoreBackend

            self._db = FirestoreBackend()
            logger.info("Using Cloud Firestore backend")
        else:
            self._db = Database()
            logger.info("Using SQLite backend")

    @property
    def db(self):
        """Get database backend."""
        return self._db

    async def connect(self) -> None:
        await self._db.connect()

    async def close(self) -> None:
        await self._db.close()

    # --- Food Logs ---

    async def get_user_logs(
        self,
        user_id: str,
        limit: int = 100,
        days: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        return await self._db.get_user_logs(user_id, limit=limit, days=days, start_date=start_date, end_date=end_date)

    async def get_log(self, user_id: str, log_id: str) -> dict[str, Any] | None:
        return await self._db.get_log(user_id, log_id)

    async def get_logs_by_ids(self, user_id: str, log_ids: list[str]) -> list[dict[str, Any]]:
        return await self._db.get_logs_by_ids(user_id, log_ids)

    async def create_log(self, user_id: str, data: dict[str, Any]) -> str:
        return await self._db.create_log(user_id, data)

    async def update_log(self, user_id: str, log_id: str, data: dict[str, Any]) -> bool:
        return await self._db.update_log(user_id, log_id, data)

    async def delete_log(self, user_id: str, log_id: str) -> bool:
        return await self._db.delete_log(user_id, log_id)

    async def get_all_user_logs(self, user_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        return await self._db.get_all_user_logs(user_id, limit=limit)

    async def get_user_logs_paginated(
        self, user_id: str, page: int = 1, page_size: int = 100
    ) -> tuple[list[dict[str, Any]], int]:
        return await self._db.get_user_logs_paginated(user_id, page=page, page_size=page_size)

    async def count_user_logs(self, user_id: str) -> int:
        return await self._db.count_user_logs(user_id)

    # --- Pantry ---

    async def get_pantry(self, user_id: str) -> list[dict[str, Any]]:
        return await self._db.get_pantry(user_id)

    async def update_pantry_item(self, user_id: str, item_data: dict[str, Any]) -> str:
        return await self._db.update_pantry_item(user_id, item_data)

    async def update_pantry_items_batch(self, user_id: str, items_data: list[dict[str, Any]]) -> list[str]:
        return await self._db.update_pantry_items_batch(user_id, items_data)

    async def add_pantry_item(self, user_id: str, item: dict[str, Any]) -> str:
        return await self._db.add_pantry_item(user_id, item)

    async def delete_pantry_item(self, user_id: str, item_id: str) -> bool:
        return await self._db.delete_pantry_item(user_id, item_id)

    # --- Recipes ---

    async def get_recipes(
        self, user_id: str, limit: int = 50, include_archived: bool = False, favorites_only: bool = False
    ) -> list[dict[str, Any]]:
        return await self._db.get_recipes(
            user_id, limit=limit, include_archived=include_archived, favorites_only=favorites_only
        )

    async def get_recipe(self, user_id: str, recipe_id: str) -> dict[str, Any] | None:
        return await self._db.get_recipe(user_id, recipe_id)

    async def create_recipe(self, user_id: str, recipe_data: dict[str, Any]) -> str:
        return await self._db.create_recipe(user_id, recipe_data)

    async def update_recipe(self, user_id: str, recipe_id: str, updates: dict[str, Any]) -> bool:
        return await self._db.update_recipe(user_id, recipe_id, updates)

    async def delete_recipe(self, user_id: str, recipe_id: str) -> bool:
        return await self._db.delete_recipe(user_id, recipe_id)

    # --- Receipts ---

    async def save_receipt(self, user_id: str, receipt_data: dict[str, Any]) -> str:
        return await self._db.save_receipt(user_id, receipt_data)

    # --- Users / Preferences / Stats ---

    async def get_active_users(self, days: int = 7) -> list[dict[str, Any]]:
        return await self._db.get_active_users(days=days)

    async def get_user_preferences(self, user_id: str) -> dict[str, Any]:
        return await self._db.get_user_preferences(user_id)

    async def update_user_preferences(self, user_id: str, preferences: dict[str, Any]) -> None:
        await self._db.update_user_preferences(user_id, preferences)

    async def invalidate_user_stats(self, user_id: str) -> None:
        await self._db.invalidate_user_stats(user_id)

    async def get_user_stats(self, user_id: str) -> dict[str, Any]:
        return await self._db.get_user_stats(user_id)

    # --- Notifications ---

    async def store_notification(self, user_id: str, notification_type: str, content: dict[str, Any]) -> str:
        return await self._db.store_notification(user_id, notification_type, content)

    async def get_user_notifications(
        self, user_id: str, limit: int = 20, unread_only: bool = False
    ) -> list[dict[str, Any]]:
        return await self._db.get_user_notifications(user_id, limit=limit, unread_only=unread_only)

    async def mark_notification_read(self, user_id: str, notification_id: str) -> bool:
        return await self._db.mark_notification_read(user_id, notification_id)

    # --- Drafts ---

    async def save_draft(self, user_id: str, draft: dict[str, Any]) -> str:
        return await self._db.save_draft(user_id, draft)

    async def get_drafts(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        return await self._db.get_drafts(user_id, limit=limit)

    async def get_draft(self, user_id: str, draft_id: str) -> dict[str, Any] | None:
        return await self._db.get_draft(user_id, draft_id)

    async def update_draft(self, user_id: str, draft_id: str, updates: dict[str, Any]) -> bool:
        return await self._db.update_draft(user_id, draft_id, updates)

    async def delete_draft(self, user_id: str, draft_id: str) -> bool:
        return await self._db.delete_draft(user_id, draft_id)

    # --- Published Content ---

    async def save_published_content(self, user_id: str, content: dict[str, Any]) -> str:
        return await self._db.save_published_content(user_id, content)

    async def get_published_content(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        return await self._db.get_published_content(user_id, limit=limit)

    async def get_published_content_item(self, user_id: str, content_id: str) -> dict[str, Any] | None:
        return await self._db.get_published_content_item(user_id, content_id)

    async def update_published_content(self, user_id: str, content_id: str, updates: dict[str, Any]) -> None:
        await self._db.update_published_content(user_id, content_id, updates)

    async def publish_draft(self, user_id: str, draft_id: str, published_content: dict[str, Any]) -> tuple[str, bool]:
        return await self._db.publish_draft(user_id, draft_id, published_content)


# =============================================================================
# Dependency Injection Support
# =============================================================================


@lru_cache(maxsize=1)
def get_firestore_client() -> FirestoreClient:
    """Get or create the FirestoreClient singleton."""
    return FirestoreClient()


def get_db() -> FirestoreClient:
    """FastAPI dependency for database client."""
    return get_firestore_client()


def get_firestore_status() -> dict:
    """Get database status for health checks."""
    backend_type = os.environ.get("DATABASE_BACKEND", "sqlite")
    return {"available": True, "error": None, "mode": backend_type}


def reset_firestore_state() -> None:
    """Reset initialization state (for testing only)."""
    pass


def reset_firestore_client() -> None:
    """Reset the client singleton (for testing only)."""
    get_firestore_client.cache_clear()


# Legacy module-level singleton
_firestore_client: FirestoreClient | None = None
_firestore_lock = threading.Lock()


def _get_legacy_client() -> FirestoreClient:
    """Get legacy singleton (deprecated, use get_firestore_client instead)."""
    global _firestore_client  # noqa: PLW0603
    if _firestore_client is None:
        with _firestore_lock:
            if _firestore_client is None:
                _firestore_client = get_firestore_client()
    assert _firestore_client is not None
    return _firestore_client


class _FirestoreClientProxy:
    """Lazy proxy for FirestoreClient."""

    def __getattr__(self, name: str) -> Any:
        return getattr(_get_legacy_client(), name)

    def __repr__(self) -> str:
        return f"<FirestoreClientProxy initialized={_firestore_client is not None}>"


# Backwards-compatible lazy proxy to the singleton client
firestore_client = _FirestoreClientProxy()
