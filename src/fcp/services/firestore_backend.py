"""Real Cloud Firestore backend implementation.

This module provides a Firestore backend that matches the Database interface.
Used in production (Cloud Run) when DATABASE_BACKEND=firestore.
"""

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

# Import firestore at module level for easier mocking in tests
try:
    from google.cloud import firestore  # type: ignore[import-untyped]

    FIRESTORE_AVAILABLE = True
except ImportError:
    firestore = None  # type: ignore[assignment]
    FIRESTORE_AVAILABLE = False


class FirestoreBackend:
    """Async Firestore backend that matches the Database interface."""

    def __init__(self, project_id: str | None = None, client: Any = None):
        """Initialize Firestore client.

        Args:
            project_id: GCP project ID. If None, uses GOOGLE_CLOUD_PROJECT env var.
            client: Optional pre-configured Firestore client (for testing).
        """
        self._project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self._db = None
        self._client = client

    async def connect(self) -> None:
        """Initialize Firestore client."""
        if self._client is None:
            # Only check for firestore availability if we need to create a client
            if not FIRESTORE_AVAILABLE:
                raise RuntimeError(
                    "google-cloud-firestore not installed. Install with: pip install google-cloud-firestore"
                )
            self._client = firestore.AsyncClient(project=self._project_id)

        self._db = self._client
        logger.info(f"Connected to Firestore project: {self._project_id}")

    async def close(self) -> None:
        """Close Firestore client."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None

    @property
    def db(self) -> Any:
        """Get Firestore client (mimics Database.db property)."""
        if self._db is None:
            raise RuntimeError("Firestore not connected. Call connect() first.")
        return self._db

    async def _ensure_connected(self) -> None:
        """Auto-connect if not yet connected."""
        if self._db is None:
            await self.connect()

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def _new_id(self) -> str:
        return uuid4().hex

    # =========================================================================
    # Food Logs
    # =========================================================================

    async def get_user_logs(
        self,
        user_id: str,
        limit: int = 100,
        days: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        await self._ensure_connected()
        query = self.db.collection("food_logs").where("user_id", "==", user_id).where("deleted", "==", False)

        if start_date:
            query = query.where("created_at", ">=", start_date.isoformat())
        elif days:
            cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
            query = query.where("created_at", ">=", cutoff)

        if end_date:
            query = query.where("created_at", "<=", end_date.isoformat())

        query = query.order_by("created_at", direction="DESCENDING").limit(limit)
        docs = query.stream()

        logs = []
        async for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            logs.append(data)
        return logs

    async def get_log(self, user_id: str, log_id: str) -> dict[str, Any] | None:
        await self._ensure_connected()
        doc = await self.db.collection("food_logs").document(log_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        if data.get("user_id") != user_id:
            return None
        data["id"] = doc.id
        return data

    async def get_logs_by_ids(self, user_id: str, log_ids: list[str]) -> list[dict[str, Any]]:
        await self._ensure_connected()
        if not log_ids:
            return []

        logs = []
        for log_id in log_ids:
            log = await self.get_log(user_id, log_id)
            if log:
                logs.append(log)
        return logs

    async def create_log(self, user_id: str, data: dict[str, Any]) -> str:
        await self._ensure_connected()
        log_id = self._new_id()
        now = self._now()

        data["user_id"] = user_id
        data["created_at"] = now
        data["updated_at"] = now
        data.setdefault("deleted", False)

        await self.db.collection("food_logs").document(log_id).set(data)

        # Update user last_active
        await self.db.collection("users").document(user_id).set({"last_active": now}, merge=True)
        await self.invalidate_user_stats(user_id)
        return log_id

    async def update_log(self, user_id: str, log_id: str, data: dict[str, Any]) -> bool:
        await self._ensure_connected()
        existing = await self.get_log(user_id, log_id)
        if existing is None:
            return False

        data["updated_at"] = self._now()
        await self.db.collection("food_logs").document(log_id).update(data)
        await self.invalidate_user_stats(user_id)
        return True

    async def delete_log(self, user_id: str, log_id: str) -> bool:
        await self._ensure_connected()
        existing = await self.get_log(user_id, log_id)
        if existing is None:
            return False

        await self.db.collection("food_logs").document(log_id).delete()
        await self.invalidate_user_stats(user_id)
        return True

    async def get_all_user_logs(self, user_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        await self._ensure_connected()
        query = (
            self.db.collection("food_logs")
            .where("user_id", "==", user_id)
            .where("deleted", "==", False)
            .order_by("created_at", direction="DESCENDING")
        )
        if limit:
            query = query.limit(limit)

        docs = query.stream()
        logs = []
        async for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            logs.append(data)
        return logs

    async def get_user_logs_paginated(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[dict[str, Any]], int]:
        await self._ensure_connected()
        page_size = min(page_size, 500)
        page = max(page, 1)

        total = await self.count_user_logs(user_id)
        offset = (page - 1) * page_size

        query = (
            self.db.collection("food_logs")
            .where("user_id", "==", user_id)
            .where("deleted", "==", False)
            .order_by("created_at", direction="DESCENDING")
            .offset(offset)
            .limit(page_size)
        )

        docs = query.stream()
        logs = []
        async for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            logs.append(data)

        return logs, total

    async def count_user_logs(self, user_id: str) -> int:
        await self._ensure_connected()
        query = self.db.collection("food_logs").where("user_id", "==", user_id).where("deleted", "==", False)
        # Firestore doesn't have efficient COUNT, so we have to fetch all docs
        # For production, consider maintaining a counter in a separate document
        docs = query.stream()
        count = 0
        async for _ in docs:
            count += 1
        return count

    # =========================================================================
    # Pantry
    # =========================================================================

    async def get_pantry(self, user_id: str) -> list[dict[str, Any]]:
        await self._ensure_connected()
        query = self.db.collection("pantry").where("user_id", "==", user_id)
        docs = query.stream()

        items = []
        async for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            items.append(data)
        return items

    async def update_pantry_item(self, user_id: str, item_data: dict[str, Any]) -> str:
        await self._ensure_connected()
        name = item_data.get("name")
        if not name:
            raise ValueError("Item name is required")

        item_id = item_data.get("id") or name.lower().replace(" ", "_")
        now = self._now()

        item_data["user_id"] = user_id
        item_data["updated_at"] = now
        item_data.setdefault("created_at", now)

        await self.db.collection("pantry").document(item_id).set(item_data, merge=True)
        return item_id

    async def update_pantry_items_batch(self, user_id: str, items_data: list[dict[str, Any]]) -> list[str]:
        await self._ensure_connected()
        if not items_data:
            return []

        ids = []
        for item in items_data:
            name = item.get("name")
            if not name:
                continue
            item_id = await self.update_pantry_item(user_id, item)
            ids.append(item_id)
        return ids

    async def add_pantry_item(self, user_id: str, item: dict[str, Any]) -> str:
        await self._ensure_connected()
        item_id = self._new_id()
        now = self._now()

        item["user_id"] = user_id
        item["created_at"] = now
        item.setdefault("updated_at", now)

        await self.db.collection("pantry").document(item_id).set(item)
        return item_id

    async def delete_pantry_item(self, user_id: str, item_id: str) -> bool:
        await self._ensure_connected()
        doc = await self.db.collection("pantry").document(item_id).get()
        if not doc.exists:
            return False

        data = doc.to_dict()
        if data.get("user_id") != user_id:
            return False

        await self.db.collection("pantry").document(item_id).delete()
        return True

    # =========================================================================
    # Recipes (placeholder - implement similar pattern)
    # =========================================================================

    async def get_recipes(
        self,
        user_id: str,
        limit: int = 50,
        include_archived: bool = False,
        favorites_only: bool = False,
    ) -> list[dict[str, Any]]:
        await self._ensure_connected()
        query = self.db.collection("recipes").where("user_id", "==", user_id)

        if not include_archived:
            query = query.where("is_archived", "==", False)
        if favorites_only:
            query = query.where("is_favorite", "==", True)

        query = query.order_by("created_at", direction="DESCENDING").limit(limit)
        docs = query.stream()

        recipes = []
        async for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            recipes.append(data)
        return recipes

    async def get_recipe(self, user_id: str, recipe_id: str) -> dict[str, Any] | None:
        await self._ensure_connected()
        doc = await self.db.collection("recipes").document(recipe_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        if data.get("user_id") != user_id:
            return None
        data["id"] = doc.id
        return data

    async def create_recipe(self, user_id: str, recipe_data: dict[str, Any]) -> str:
        await self._ensure_connected()
        recipe_id = self._new_id()
        now = self._now()

        recipe_data["user_id"] = user_id
        recipe_data.setdefault("is_favorite", False)
        recipe_data.setdefault("is_archived", False)
        recipe_data["created_at"] = now
        recipe_data["updated_at"] = now

        await self.db.collection("recipes").document(recipe_id).set(recipe_data)
        return recipe_id

    async def update_recipe(self, user_id: str, recipe_id: str, updates: dict[str, Any]) -> bool:
        await self._ensure_connected()
        existing = await self.get_recipe(user_id, recipe_id)
        if existing is None:
            return False

        updates["updated_at"] = self._now()
        await self.db.collection("recipes").document(recipe_id).update(updates)
        return True

    async def delete_recipe(self, user_id: str, recipe_id: str) -> bool:
        await self._ensure_connected()
        existing = await self.get_recipe(user_id, recipe_id)
        if existing is None:
            return False

        await self.db.collection("recipes").document(recipe_id).delete()
        return True

    # =========================================================================
    # Receipts
    # =========================================================================

    async def save_receipt(self, user_id: str, receipt_data: dict[str, Any]) -> str:
        await self._ensure_connected()
        receipt_id = self._new_id()
        now = self._now()

        data = {
            "user_id": user_id,
            "data": receipt_data,
            "parsed_at": now,
        }

        await self.db.collection("receipts").document(receipt_id).set(data)
        return receipt_id

    # =========================================================================
    # Users / Preferences / Stats
    # =========================================================================

    async def get_active_users(self, days: int = 7) -> list[dict[str, Any]]:
        await self._ensure_connected()
        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        query = self.db.collection("users").where("last_active", ">=", cutoff)
        docs = query.stream()

        users = []
        async for doc in docs:
            data = doc.to_dict()
            users.append(
                {
                    "id": doc.id,
                    "email": data.get("email"),
                    "display_name": data.get("display_name"),
                    "last_active": data.get("last_active"),
                }
            )
        return users

    async def get_user_preferences(self, user_id: str) -> dict[str, Any]:
        await self._ensure_connected()
        defaults = {
            "display_name": None,
            "location": None,
            "timezone": "UTC",
            "daily_insights_enabled": True,
            "weekly_digest_enabled": True,
            "streak_celebrations_enabled": True,
            "seasonal_reminders_enabled": True,
            "food_tips_enabled": True,
            "notification_hour": 8,
        }

        doc = await self.db.collection("users").document(user_id).get()
        if not doc.exists:
            return defaults

        data = doc.to_dict()
        preferences = data.get("preferences") or {}
        return {
            **defaults,
            **preferences,
            "display_name": data.get("display_name"),
            "email": data.get("email"),
        }

    async def update_user_preferences(self, user_id: str, preferences: dict[str, Any]) -> None:
        await self._ensure_connected()
        now = self._now()
        await (
            self.db.collection("users")
            .document(user_id)
            .set(
                {
                    "preferences": preferences,
                    "last_active": now,
                },
                merge=True,
            )
        )

    async def invalidate_user_stats(self, user_id: str) -> None:
        await self._ensure_connected()
        await (
            self.db.collection("users")
            .document(user_id)
            .set(
                {"stats": None},
                merge=True,
            )
        )

    async def get_user_stats(self, user_id: str) -> dict[str, Any]:
        await self._ensure_connected()
        # Check cache first
        doc = await self.db.collection("users").document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            stats = data.get("stats")
            if stats:
                # Check if streak needs reset
                if last_log_iso := stats.get("last_log_date"):
                    try:
                        last_log_date = datetime.fromisoformat(last_log_iso).date()
                        today = datetime.now(UTC).date()
                        if (today - last_log_date).days > 1:
                            stats["current_streak"] = 0
                    except ValueError:
                        pass
                return stats

        # Calculate stats from scratch
        total_logs = await self.count_user_logs(user_id)
        if total_logs == 0:
            stats = {
                "current_streak": 0,
                "longest_streak": 0,
                "total_logs": 0,
                "cuisines_tried": 0,
                "first_log_date": None,
                "last_log_date": None,
            }
            await self._cache_stats(user_id, stats)
            return stats

        # Get recent logs for streak calculation (90 days)
        now = datetime.now(UTC)
        today = now.date()
        window = (now - timedelta(days=90)).isoformat()
        query = (
            self.db.collection("food_logs")
            .where("user_id", "==", user_id)
            .where("deleted", "==", False)
            .where("created_at", ">=", window)
            .order_by("created_at", direction="DESCENDING")
        )

        log_dates: set = set()
        cuisines: set = set()

        docs = query.stream()
        async for doc in docs:
            data = doc.to_dict()
            created = data.get("created_at")
            if created:
                try:
                    log_dates.add(datetime.fromisoformat(created).date())
                except ValueError:
                    pass
            cuisine = data.get("cuisine")
            if cuisine:
                cuisines.add(cuisine.lower())

        # Get first and last log dates
        first_query = (
            self.db.collection("food_logs")
            .where("user_id", "==", user_id)
            .where("deleted", "==", False)
            .order_by("created_at", direction="ASCENDING")
            .limit(1)
        )
        last_query = (
            self.db.collection("food_logs")
            .where("user_id", "==", user_id)
            .where("deleted", "==", False)
            .order_by("created_at", direction="DESCENDING")
            .limit(1)
        )

        first_date = None
        last_date = None

        first_docs = first_query.stream()
        async for doc in first_docs:
            data = doc.to_dict()
            if created := data.get("created_at"):
                first_date = datetime.fromisoformat(created)
            break

        last_docs = last_query.stream()
        async for doc in last_docs:
            data = doc.to_dict()
            if created := data.get("created_at"):
                last_date = datetime.fromisoformat(created)
            break

        # Calculate streaks
        current_streak = 0
        check_date = today
        while check_date in log_dates:
            current_streak += 1
            check_date -= timedelta(days=1)
        if current_streak == 0:
            check_date = today - timedelta(days=1)
            while check_date in log_dates:
                current_streak += 1
                check_date -= timedelta(days=1)

        if log_dates:
            sorted_dates = sorted(log_dates)
            longest_streak = 1
            current_run = 1
            for i in range(1, len(sorted_dates)):
                if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
                    current_run += 1
                    longest_streak = max(longest_streak, current_run)
                else:
                    current_run = 1
        else:
            longest_streak = 0

        stats = {
            "current_streak": current_streak,
            "longest_streak": max(longest_streak, current_streak),
            "total_logs": total_logs,
            "cuisines_tried": len(cuisines),
            "first_log_date": first_date.date().isoformat() if first_date else None,
            "last_log_date": last_date.date().isoformat() if last_date else None,
        }
        await self._cache_stats(user_id, stats)
        return stats

    async def _cache_stats(self, user_id: str, stats: dict[str, Any]) -> None:
        now = self._now()
        await (
            self.db.collection("users")
            .document(user_id)
            .set(
                {
                    "stats": stats,
                    "last_active": now,
                },
                merge=True,
            )
        )

    # =========================================================================
    # Notifications
    # =========================================================================

    async def store_notification(
        self,
        user_id: str,
        notification_type: str,
        content: dict[str, Any],
    ) -> str:
        await self._ensure_connected()
        nid = self._new_id()
        now = self._now()

        data = {
            "user_id": user_id,
            "type": notification_type,
            "content": content,
            "read": False,
            "delivered": False,
            "created_at": now,
        }

        await self.db.collection("notifications").document(nid).set(data)
        return nid

    async def get_user_notifications(
        self,
        user_id: str,
        limit: int = 20,
        unread_only: bool = False,
    ) -> list[dict[str, Any]]:
        await self._ensure_connected()
        query = self.db.collection("notifications").where("user_id", "==", user_id)

        if unread_only:
            query = query.where("read", "==", False)

        query = query.order_by("created_at", direction="DESCENDING").limit(limit)
        docs = query.stream()

        notifications = []
        async for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            notifications.append(data)
        return notifications

    async def mark_notification_read(self, user_id: str, notification_id: str) -> bool:
        await self._ensure_connected()
        doc = await self.db.collection("notifications").document(notification_id).get()
        if not doc.exists:
            return False

        data = doc.to_dict()
        if data.get("user_id") != user_id:
            return False

        now = self._now()
        await (
            self.db.collection("notifications")
            .document(notification_id)
            .update(
                {
                    "read": True,
                    "read_at": now,
                }
            )
        )
        return True

    # =========================================================================
    # Drafts
    # =========================================================================

    async def save_draft(self, user_id: str, draft: dict[str, Any]) -> str:
        await self._ensure_connected()
        draft_id = self._new_id()
        now = self._now()

        draft["user_id"] = user_id
        draft["created_at"] = now
        draft["updated_at"] = now

        await self.db.collection("drafts").document(draft_id).set(draft)
        return draft_id

    async def get_drafts(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        await self._ensure_connected()
        query = (
            self.db.collection("drafts")
            .where("user_id", "==", user_id)
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
        )
        docs = query.stream()

        drafts = []
        async for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            drafts.append(data)
        return drafts

    async def get_draft(self, user_id: str, draft_id: str) -> dict[str, Any] | None:
        await self._ensure_connected()
        doc = await self.db.collection("drafts").document(draft_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        if data.get("user_id") != user_id:
            return None
        data["id"] = doc.id
        return data

    async def update_draft(self, user_id: str, draft_id: str, updates: dict[str, Any]) -> bool:
        await self._ensure_connected()
        existing = await self.get_draft(user_id, draft_id)
        if existing is None:
            return False

        updates["updated_at"] = self._now()
        await self.db.collection("drafts").document(draft_id).update(updates)
        return True

    async def delete_draft(self, user_id: str, draft_id: str) -> bool:
        await self._ensure_connected()
        existing = await self.get_draft(user_id, draft_id)
        if existing is None:
            return False

        await self.db.collection("drafts").document(draft_id).delete()
        return True

    # =========================================================================
    # Published Content
    # =========================================================================

    async def save_published_content(self, user_id: str, content: dict[str, Any]) -> str:
        await self._ensure_connected()
        content_id = self._new_id()
        now = self._now()

        content["user_id"] = user_id
        content["published_at"] = now

        await self.db.collection("published").document(content_id).set(content)
        return content_id

    async def get_published_content(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        await self._ensure_connected()
        query = (
            self.db.collection("published")
            .where("user_id", "==", user_id)
            .order_by("published_at", direction="DESCENDING")
            .limit(limit)
        )
        docs = query.stream()

        content = []
        async for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            content.append(data)
        return content

    async def get_published_content_item(self, user_id: str, content_id: str) -> dict[str, Any] | None:
        await self._ensure_connected()
        doc = await self.db.collection("published").document(content_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        if data.get("user_id") != user_id:
            return None
        data["id"] = doc.id
        return data

    async def update_published_content(self, user_id: str, content_id: str, updates: dict[str, Any]) -> None:
        await self._ensure_connected()
        await self.db.collection("published").document(content_id).update(updates)

    async def publish_draft(
        self,
        user_id: str,
        draft_id: str,
        published_content: dict[str, Any],
    ) -> tuple[str, bool]:
        await self._ensure_connected()
        draft = await self.get_draft(user_id, draft_id)
        if draft is None:
            return "", False
        if draft.get("status") == "published":
            return "", False

        # Update draft status
        await self.update_draft(user_id, draft_id, {"status": "published"})

        # Create published content
        published_content["draft_id"] = draft_id
        content_id = await self.save_published_content(user_id, published_content)
        return content_id, True
