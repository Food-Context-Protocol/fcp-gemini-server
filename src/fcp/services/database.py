"""SQLite database backend for FCP."""

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import aiosqlite

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get("FCP_DATA_DIR", "data"))
DB_PATH = DATA_DIR / "fcp.db"

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS food_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    dish_name TEXT,
    venue_name TEXT,
    notes TEXT,
    rating INTEGER,
    tags TEXT,
    image_path TEXT,
    analysis TEXT,
    nutrition TEXT,
    cuisine TEXT,
    ingredients TEXT,
    spice_level INTEGER,
    dietary_tags TEXT,
    allergens TEXT,
    processing_status TEXT,
    processing_error TEXT,
    occasion TEXT,
    ai_notes TEXT,
    foodon TEXT,
    donated INTEGER DEFAULT 0,
    donation_organization TEXT,
    public INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT,
    deleted INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS pantry (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT,
    quantity REAL,
    unit TEXT,
    category TEXT,
    expiry_date TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS recipes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT,
    ingredients TEXT,
    instructions TEXT,
    servings INTEGER,
    description TEXT,
    prep_time_minutes INTEGER,
    cook_time_minutes INTEGER,
    cuisine TEXT,
    tags TEXT,
    source TEXT,
    source_meal_id TEXT,
    image_url TEXT,
    nutrition TEXT,
    is_favorite INTEGER DEFAULT 0,
    is_archived INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS drafts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    content_type TEXT,
    content TEXT,
    status TEXT,
    source_log_ids TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS published (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    draft_id TEXT,
    content_type TEXT,
    content TEXT,
    platforms TEXT,
    external_urls TEXT,
    published_at TEXT
);
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    type TEXT,
    content TEXT,
    read INTEGER DEFAULT 0,
    delivered INTEGER DEFAULT 0,
    created_at TEXT,
    read_at TEXT
);
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT,
    display_name TEXT,
    preferences TEXT,
    stats TEXT,
    last_active TEXT
);
CREATE TABLE IF NOT EXISTS receipts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    data TEXT,
    parsed_at TEXT
);
"""

_JSON_FIELDS_LOGS = frozenset(
    {
        "tags",
        "analysis",
        "nutrition",
        "ingredients",
        "dietary_tags",
        "allergens",
        "foodon",
    }
)
_JSON_FIELDS_RECIPES = frozenset({"ingredients", "instructions", "tags", "nutrition"})
_JSON_FIELDS_DRAFTS = frozenset({"content", "source_log_ids"})
_JSON_FIELDS_PUBLISHED = frozenset({"content", "platforms", "external_urls"})
_JSON_FIELDS_NOTIFICATIONS = frozenset({"content"})
_JSON_FIELDS_USERS = frozenset({"preferences", "stats"})
_JSON_FIELDS_RECEIPTS = frozenset({"data"})


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid4().hex


def _encode_json(data: dict[str, Any], json_fields: frozenset[str]) -> dict[str, Any]:
    """Encode JSON fields in a dict for storage."""
    out = dict(data)
    for k in json_fields:
        if k in out and out[k] is not None:
            if not isinstance(out[k], str):
                out[k] = json.dumps(out[k])
    return out


def _decode_json(row: dict[str, Any], json_fields: frozenset[str]) -> dict[str, Any]:
    """Decode JSON fields from storage."""
    out = dict(row)
    for k in json_fields:
        val = out.get(k)
        if isinstance(val, str):
            try:
                out[k] = json.loads(val)
            except (json.JSONDecodeError, ValueError):
                # If decoding fails, leave the original string value unchanged
                pass
        elif val is None:
            # Leave None as-is
            pass
    return out


def _row_to_dict(row: aiosqlite.Row) -> dict[str, Any]:
    """Convert a sqlite Row to a plain dict."""
    return dict(row)


class Database:
    """Async SQLite database backend."""

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = str(db_path) if db_path else str(DB_PATH)
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Initialize DB and create tables."""
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_CREATE_TABLES)
        await self._migrate_food_logs_columns()
        await self._db.commit()

    async def _migrate_food_logs_columns(self) -> None:
        """Ensure newer food_logs columns exist on pre-existing databases."""
        columns: set[str] = set()
        async with self.db.execute("PRAGMA table_info(food_logs)") as cursor:
            async for row in cursor:
                columns.add(row["name"])

        if "donated" not in columns:
            await self.db.execute("ALTER TABLE food_logs ADD COLUMN donated INTEGER DEFAULT 0")
        if "donation_organization" not in columns:
            await self.db.execute("ALTER TABLE food_logs ADD COLUMN donation_organization TEXT")

    async def close(self) -> None:
        """Close DB connection."""
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db

    async def _ensure_connected(self) -> None:
        """Auto-connect if not yet connected."""
        if self._db is None:
            await self.connect()

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
        clauses = ["user_id = ?", "deleted = 0"]
        params: list[Any] = [user_id]

        if start_date:
            clauses.append("created_at >= ?")
            params.append(start_date.isoformat())
        elif days:
            cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
            clauses.append("created_at >= ?")
            params.append(cutoff)

        if end_date:
            clauses.append("created_at <= ?")
            params.append(end_date.isoformat())

        where = " AND ".join(clauses)
        sql = f"SELECT * FROM food_logs WHERE {where} ORDER BY created_at DESC LIMIT ?"  # noqa: S608
        params.append(limit)

        async with self.db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()

        return [_decode_json(_row_to_dict(r), _JSON_FIELDS_LOGS) for r in rows]

    async def get_log(self, user_id: str, log_id: str) -> dict[str, Any] | None:
        await self._ensure_connected()
        sql = "SELECT * FROM food_logs WHERE id = ? AND user_id = ?"
        async with self.db.execute(sql, (log_id, user_id)) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return _decode_json(_row_to_dict(row), _JSON_FIELDS_LOGS)

    async def get_logs_by_ids(self, user_id: str, log_ids: list[str]) -> list[dict[str, Any]]:
        await self._ensure_connected()
        if not log_ids:
            return []
        placeholders = ",".join("?" for _ in log_ids)
        sql = f"SELECT * FROM food_logs WHERE user_id = ? AND id IN ({placeholders})"  # noqa: S608
        params = [user_id, *log_ids]
        async with self.db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
        return [_decode_json(_row_to_dict(r), _JSON_FIELDS_LOGS) for r in rows]

    async def create_log(self, user_id: str, data: dict[str, Any]) -> str:
        await self._ensure_connected()
        log_id = _new_id()
        now = _now()
        data = _encode_json(data, _JSON_FIELDS_LOGS)
        data["id"] = log_id
        data["user_id"] = user_id
        data["created_at"] = now
        data["updated_at"] = now
        data.setdefault("deleted", 0)

        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        sql = f"INSERT INTO food_logs ({cols}) VALUES ({placeholders})"  # noqa: S608
        await self.db.execute(sql, list(data.values()))

        # Update user last_active
        await self.db.execute(
            "INSERT INTO users (id, last_active) VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET last_active = ?",
            (user_id, now, now),
        )
        await self.db.commit()
        await self.invalidate_user_stats(user_id)
        return log_id

    async def update_log(self, user_id: str, log_id: str, data: dict[str, Any]) -> bool:
        await self._ensure_connected()
        existing = await self.get_log(user_id, log_id)
        if existing is None:
            return False
        data = _encode_json(data, _JSON_FIELDS_LOGS)
        data["updated_at"] = _now()
        sets = ", ".join(f"{k} = ?" for k in data)
        params = [*data.values(), log_id, user_id]
        sql = f"UPDATE food_logs SET {sets} WHERE id = ? AND user_id = ?"  # noqa: S608
        await self.db.execute(sql, params)
        await self.db.commit()
        await self.invalidate_user_stats(user_id)
        return True

    async def delete_log(self, user_id: str, log_id: str) -> bool:
        await self._ensure_connected()
        existing = await self.get_log(user_id, log_id)
        if existing is None:
            return False
        await self.db.execute("DELETE FROM food_logs WHERE id = ? AND user_id = ?", (log_id, user_id))
        await self.db.commit()
        await self.invalidate_user_stats(user_id)
        return True

    async def get_all_user_logs(self, user_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        await self._ensure_connected()
        if limit is not None:
            sql = "SELECT * FROM food_logs WHERE user_id = ? AND deleted = 0 ORDER BY created_at DESC LIMIT ?"
            params: list[Any] = [user_id, limit]
        else:
            sql = "SELECT * FROM food_logs WHERE user_id = ? AND deleted = 0 ORDER BY created_at DESC"
            params = [user_id]
        async with self.db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
        return [_decode_json(_row_to_dict(r), _JSON_FIELDS_LOGS) for r in rows]

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
        sql = "SELECT * FROM food_logs WHERE user_id = ? AND deleted = 0 ORDER BY created_at DESC LIMIT ? OFFSET ?"
        async with self.db.execute(sql, (user_id, page_size, offset)) as cursor:
            rows = await cursor.fetchall()
        logs = [_decode_json(_row_to_dict(r), _JSON_FIELDS_LOGS) for r in rows]
        return logs, total

    async def count_user_logs(self, user_id: str) -> int:
        await self._ensure_connected()
        sql = "SELECT COUNT(*) FROM food_logs WHERE user_id = ? AND deleted = 0"
        async with self.db.execute(sql, (user_id,)) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else 0

    # =========================================================================
    # Pantry
    # =========================================================================

    async def get_pantry(self, user_id: str) -> list[dict[str, Any]]:
        await self._ensure_connected()
        sql = "SELECT * FROM pantry WHERE user_id = ?"
        async with self.db.execute(sql, (user_id,)) as cursor:
            rows = await cursor.fetchall()
        return [_row_to_dict(r) for r in rows]

    async def update_pantry_item(self, user_id: str, item_data: dict[str, Any]) -> str:
        await self._ensure_connected()
        name = item_data.get("name")
        if not name:
            raise ValueError("Item name is required")
        item_id = item_data.get("id") or name.lower().replace(" ", "_")
        now = _now()

        # Upsert
        item_data["id"] = item_id
        item_data["user_id"] = user_id
        item_data["updated_at"] = now
        item_data.setdefault("created_at", now)

        cols = ", ".join(item_data.keys())
        placeholders = ", ".join("?" for _ in item_data)
        updates = ", ".join(f"{k} = ?" for k in item_data if k != "id")
        update_vals = [v for k, v in item_data.items() if k != "id"]
        sql = f"INSERT INTO pantry ({cols}) VALUES ({placeholders}) ON CONFLICT(id) DO UPDATE SET {updates}"  # noqa: S608
        await self.db.execute(sql, [*item_data.values(), *update_vals])
        await self.db.commit()
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
        item_id = _new_id()
        now = _now()
        item["id"] = item_id
        item["user_id"] = user_id
        item["created_at"] = now
        item.setdefault("updated_at", now)
        cols = ", ".join(item.keys())
        placeholders = ", ".join("?" for _ in item)
        sql = f"INSERT INTO pantry ({cols}) VALUES ({placeholders})"  # noqa: S608
        await self.db.execute(sql, list(item.values()))
        await self.db.commit()
        return item_id

    async def delete_pantry_item(self, user_id: str, item_id: str) -> bool:
        await self._ensure_connected()
        sql = "SELECT id FROM pantry WHERE id = ? AND user_id = ?"
        async with self.db.execute(sql, (item_id, user_id)) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return False
        await self.db.execute("DELETE FROM pantry WHERE id = ? AND user_id = ?", (item_id, user_id))
        await self.db.commit()
        return True

    # =========================================================================
    # Recipes
    # =========================================================================

    async def get_recipes(
        self,
        user_id: str,
        limit: int = 50,
        include_archived: bool = False,
        favorites_only: bool = False,
    ) -> list[dict[str, Any]]:
        await self._ensure_connected()
        clauses = ["user_id = ?"]
        params: list[Any] = [user_id]
        if not include_archived:
            clauses.append("is_archived = 0")
        if favorites_only:
            clauses.append("is_favorite = 1")
        where = " AND ".join(clauses)
        sql = f"SELECT * FROM recipes WHERE {where} ORDER BY created_at DESC LIMIT ?"  # noqa: S608
        params.append(limit)
        async with self.db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
        return [_decode_json(_row_to_dict(r), _JSON_FIELDS_RECIPES) for r in rows]

    async def get_recipe(self, user_id: str, recipe_id: str) -> dict[str, Any] | None:
        await self._ensure_connected()
        sql = "SELECT * FROM recipes WHERE id = ? AND user_id = ?"
        async with self.db.execute(sql, (recipe_id, user_id)) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return _decode_json(_row_to_dict(row), _JSON_FIELDS_RECIPES)

    async def create_recipe(self, user_id: str, recipe_data: dict[str, Any]) -> str:
        await self._ensure_connected()
        recipe_id = _new_id()
        now = _now()
        recipe_data = _encode_json(recipe_data, _JSON_FIELDS_RECIPES)
        recipe_data["id"] = recipe_id
        recipe_data["user_id"] = user_id
        recipe_data.setdefault("is_favorite", 0)
        recipe_data.setdefault("is_archived", 0)
        recipe_data["created_at"] = now
        recipe_data["updated_at"] = now
        cols = ", ".join(recipe_data.keys())
        placeholders = ", ".join("?" for _ in recipe_data)
        sql = f"INSERT INTO recipes ({cols}) VALUES ({placeholders})"  # noqa: S608
        await self.db.execute(sql, list(recipe_data.values()))
        await self.db.commit()
        return recipe_id

    async def update_recipe(self, user_id: str, recipe_id: str, updates: dict[str, Any]) -> bool:
        await self._ensure_connected()
        existing = await self.get_recipe(user_id, recipe_id)
        if existing is None:
            return False
        updates = _encode_json(updates, _JSON_FIELDS_RECIPES)
        updates["updated_at"] = _now()
        sets = ", ".join(f"{k} = ?" for k in updates)
        params = [*updates.values(), recipe_id, user_id]
        sql = f"UPDATE recipes SET {sets} WHERE id = ? AND user_id = ?"  # noqa: S608
        await self.db.execute(sql, params)
        await self.db.commit()
        return True

    async def delete_recipe(self, user_id: str, recipe_id: str) -> bool:
        await self._ensure_connected()
        existing = await self.get_recipe(user_id, recipe_id)
        if existing is None:
            return False
        await self.db.execute("DELETE FROM recipes WHERE id = ? AND user_id = ?", (recipe_id, user_id))
        await self.db.commit()
        return True

    # =========================================================================
    # Receipts
    # =========================================================================

    async def save_receipt(self, user_id: str, receipt_data: dict[str, Any]) -> str:
        await self._ensure_connected()
        receipt_id = _new_id()
        now = _now()
        sql = "INSERT INTO receipts (id, user_id, data, parsed_at) VALUES (?, ?, ?, ?)"
        await self.db.execute(sql, (receipt_id, user_id, json.dumps(receipt_data), now))
        await self.db.commit()
        return receipt_id

    # =========================================================================
    # Users / Preferences / Stats
    # =========================================================================

    async def get_active_users(self, days: int = 7) -> list[dict[str, Any]]:
        await self._ensure_connected()
        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        sql = "SELECT * FROM users WHERE last_active >= ?"
        async with self.db.execute(sql, (cutoff,)) as cursor:
            rows = await cursor.fetchall()
        users = []
        for r in rows:
            d = _decode_json(_row_to_dict(r), _JSON_FIELDS_USERS)
            users.append(
                {
                    "id": d["id"],
                    "email": d.get("email"),
                    "display_name": d.get("display_name"),
                    "last_active": d.get("last_active"),
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
        sql = "SELECT * FROM users WHERE id = ?"
        async with self.db.execute(sql, (user_id,)) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return defaults
        data = _decode_json(_row_to_dict(row), _JSON_FIELDS_USERS)
        preferences = data.get("preferences") or {}
        if isinstance(preferences, str):
            try:
                preferences = json.loads(preferences)
            except (json.JSONDecodeError, ValueError):
                preferences = {}
        return {
            **defaults,
            **preferences,
            "display_name": data.get("display_name"),
            "email": data.get("email"),
        }

    async def update_user_preferences(self, user_id: str, preferences: dict[str, Any]) -> None:
        await self._ensure_connected()
        now = _now()
        prefs_json = json.dumps(preferences)
        await self.db.execute(
            "INSERT INTO users (id, preferences, last_active) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET preferences = ?, last_active = ?",
            (user_id, prefs_json, now, prefs_json, now),
        )
        await self.db.commit()

    async def invalidate_user_stats(self, user_id: str) -> None:
        await self._ensure_connected()
        await self.db.execute(
            "UPDATE users SET stats = NULL WHERE id = ?",
            (user_id,),
        )
        await self.db.commit()

    async def get_user_stats(self, user_id: str) -> dict[str, Any]:
        await self._ensure_connected()
        # Check cache first
        sql = "SELECT stats FROM users WHERE id = ?"
        async with self.db.execute(sql, (user_id,)) as cursor:
            row = await cursor.fetchone()
        if row and row[0]:
            stats = json.loads(row[0])
            if last_log_iso := stats.get("last_log_date"):
                try:
                    last_log_date = datetime.fromisoformat(last_log_iso).date()
                    today = datetime.now(UTC).date()
                    if (today - last_log_date).days > 1:
                        stats["current_streak"] = 0
                except ValueError:
                    # If the cached last_log_date is invalid, ignore it and leave the streak unchanged
                    pass
            return stats

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

        # Get recent logs for streak calc (90 days)
        now = datetime.now(UTC)
        today = now.date()
        window = (now - timedelta(days=90)).isoformat()
        sql = "SELECT created_at, cuisine FROM food_logs WHERE user_id = ? AND deleted = 0 AND created_at >= ? ORDER BY created_at DESC"
        async with self.db.execute(sql, (user_id, window)) as cursor:
            rows = await cursor.fetchall()

        log_dates: set = set()
        cuisines: set = set()
        for r in rows:
            created = r[0]
            if created:
                try:
                    log_dates.add(datetime.fromisoformat(created).date())
                except ValueError:
                    # Skip logs with invalid created_at timestamps
                    pass
            cuisine_val = r[1]
            if cuisine_val:
                cuisines.add(cuisine_val.lower())

        # First and last log dates
        sql_first = "SELECT created_at FROM food_logs WHERE user_id = ? AND deleted = 0 ORDER BY created_at ASC LIMIT 1"
        sql_last = "SELECT created_at FROM food_logs WHERE user_id = ? AND deleted = 0 ORDER BY created_at DESC LIMIT 1"
        first_date = None
        last_date = None
        async with self.db.execute(sql_first, (user_id,)) as cursor:
            r = await cursor.fetchone()
            if r and r[0]:
                first_date = datetime.fromisoformat(r[0])
            else:
                first_date = None  # Explicitly set to None when no valid timestamp
        async with self.db.execute(sql_last, (user_id,)) as cursor:
            r = await cursor.fetchone()
            if r and r[0]:
                last_date = datetime.fromisoformat(r[0])
            else:
                last_date = None  # Explicitly set to None when no valid timestamp

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
        stats_json = json.dumps(stats)
        now = _now()
        await self.db.execute(
            "INSERT INTO users (id, stats, last_active) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET stats = ?, last_active = ?",
            (user_id, stats_json, now, stats_json, now),
        )
        await self.db.commit()

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
        nid = _new_id()
        now = _now()
        sql = "INSERT INTO notifications (id, user_id, type, content, read, delivered, created_at) VALUES (?, ?, ?, ?, 0, 0, ?)"
        await self.db.execute(sql, (nid, user_id, notification_type, json.dumps(content), now))
        await self.db.commit()
        return nid

    async def get_user_notifications(
        self,
        user_id: str,
        limit: int = 20,
        unread_only: bool = False,
    ) -> list[dict[str, Any]]:
        await self._ensure_connected()
        clauses = ["user_id = ?"]
        params: list[Any] = [user_id]
        if unread_only:
            clauses.append("read = 0")
        where = " AND ".join(clauses)
        sql = f"SELECT * FROM notifications WHERE {where} ORDER BY created_at DESC LIMIT ?"  # noqa: S608
        params.append(limit)
        async with self.db.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
        return [_decode_json(_row_to_dict(r), _JSON_FIELDS_NOTIFICATIONS) for r in rows]

    async def mark_notification_read(self, user_id: str, notification_id: str) -> bool:
        await self._ensure_connected()
        sql = "SELECT id FROM notifications WHERE id = ? AND user_id = ?"
        async with self.db.execute(sql, (notification_id, user_id)) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return False
        now = _now()
        await self.db.execute(
            "UPDATE notifications SET read = 1, read_at = ? WHERE id = ? AND user_id = ?",
            (now, notification_id, user_id),
        )
        await self.db.commit()
        return True

    # =========================================================================
    # Drafts
    # =========================================================================

    async def save_draft(self, user_id: str, draft: dict[str, Any]) -> str:
        await self._ensure_connected()
        draft_id = _new_id()
        now = _now()
        draft = _encode_json(draft, _JSON_FIELDS_DRAFTS)
        draft["id"] = draft_id
        draft["user_id"] = user_id
        draft["created_at"] = now
        draft["updated_at"] = now
        cols = ", ".join(draft.keys())
        placeholders = ", ".join("?" for _ in draft)
        sql = f"INSERT INTO drafts ({cols}) VALUES ({placeholders})"  # noqa: S608
        await self.db.execute(sql, list(draft.values()))
        await self.db.commit()
        return draft_id

    async def get_drafts(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        await self._ensure_connected()
        sql = "SELECT * FROM drafts WHERE user_id = ? ORDER BY created_at DESC LIMIT ?"
        async with self.db.execute(sql, (user_id, limit)) as cursor:
            rows = await cursor.fetchall()
        return [_decode_json(_row_to_dict(r), _JSON_FIELDS_DRAFTS) for r in rows]

    async def get_draft(self, user_id: str, draft_id: str) -> dict[str, Any] | None:
        await self._ensure_connected()
        sql = "SELECT * FROM drafts WHERE id = ? AND user_id = ?"
        async with self.db.execute(sql, (draft_id, user_id)) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return _decode_json(_row_to_dict(row), _JSON_FIELDS_DRAFTS)

    async def update_draft(self, user_id: str, draft_id: str, updates: dict[str, Any]) -> bool:
        await self._ensure_connected()
        existing = await self.get_draft(user_id, draft_id)
        if existing is None:
            return False
        updates = _encode_json(updates, _JSON_FIELDS_DRAFTS)
        updates["updated_at"] = _now()
        sets = ", ".join(f"{k} = ?" for k in updates)
        params = [*updates.values(), draft_id, user_id]
        sql = f"UPDATE drafts SET {sets} WHERE id = ? AND user_id = ?"  # noqa: S608
        await self.db.execute(sql, params)
        await self.db.commit()
        return True

    async def delete_draft(self, user_id: str, draft_id: str) -> bool:
        await self._ensure_connected()
        existing = await self.get_draft(user_id, draft_id)
        if existing is None:
            return False
        await self.db.execute("DELETE FROM drafts WHERE id = ? AND user_id = ?", (draft_id, user_id))
        await self.db.commit()
        return True

    # =========================================================================
    # Published Content
    # =========================================================================

    async def save_published_content(self, user_id: str, content: dict[str, Any]) -> str:
        await self._ensure_connected()
        content_id = _new_id()
        now = _now()
        content = _encode_json(content, _JSON_FIELDS_PUBLISHED)
        content["id"] = content_id
        content["user_id"] = user_id
        content["published_at"] = now
        cols = ", ".join(content.keys())
        placeholders = ", ".join("?" for _ in content)
        sql = f"INSERT INTO published ({cols}) VALUES ({placeholders})"  # noqa: S608
        await self.db.execute(sql, list(content.values()))
        await self.db.commit()
        return content_id

    async def get_published_content(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        await self._ensure_connected()
        sql = "SELECT * FROM published WHERE user_id = ? ORDER BY published_at DESC LIMIT ?"
        async with self.db.execute(sql, (user_id, limit)) as cursor:
            rows = await cursor.fetchall()
        return [_decode_json(_row_to_dict(r), _JSON_FIELDS_PUBLISHED) for r in rows]

    async def get_published_content_item(self, user_id: str, content_id: str) -> dict[str, Any] | None:
        await self._ensure_connected()
        sql = "SELECT * FROM published WHERE id = ? AND user_id = ?"
        async with self.db.execute(sql, (content_id, user_id)) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return _decode_json(_row_to_dict(row), _JSON_FIELDS_PUBLISHED)

    async def update_published_content(self, user_id: str, content_id: str, updates: dict[str, Any]) -> None:
        await self._ensure_connected()
        updates = _encode_json(updates, _JSON_FIELDS_PUBLISHED)
        sets = ", ".join(f"{k} = ?" for k in updates)
        params = [*updates.values(), content_id, user_id]
        sql = f"UPDATE published SET {sets} WHERE id = ? AND user_id = ?"  # noqa: S608
        await self.db.execute(sql, params)
        await self.db.commit()

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
