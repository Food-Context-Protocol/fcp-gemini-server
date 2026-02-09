"""Comprehensive unit tests for fcp.services.database – targeting 100 % branch coverage."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import aiosqlite
import pytest
import pytest_asyncio

from fcp.services.database import (
    Database,
    _decode_json,
    _encode_json,
    _new_id,
    _now,
    _row_to_dict,
)

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db():
    database = Database(":memory:")
    await database.connect()
    yield database
    await database.close()


# ===========================================================================
# Helper functions
# ===========================================================================


class TestNow:
    def test_returns_iso_string(self):
        result = _now()
        # Should parse without error
        dt = datetime.fromisoformat(result)
        assert dt.tzinfo is not None

    def test_is_utc(self):
        result = _now()
        dt = datetime.fromisoformat(result)
        assert dt.tzinfo == UTC


class TestNewId:
    def test_returns_hex_string(self):
        result = _new_id()
        assert isinstance(result, str)
        # uuid4().hex is 32 hex chars
        assert len(result) == 32
        int(result, 16)  # must be valid hex

    def test_unique(self):
        ids = {_new_id() for _ in range(100)}
        assert len(ids) == 100


class TestEncodeJson:
    def test_encodes_json_fields(self):
        data = {"tags": ["a", "b"], "dish_name": "Ramen"}
        result = _encode_json(data, frozenset({"tags"}))
        assert result["tags"] == '["a", "b"]'
        assert result["dish_name"] == "Ramen"

    def test_skips_none_values(self):
        data = {"tags": None, "name": "x"}
        result = _encode_json(data, frozenset({"tags"}))
        assert result["tags"] is None

    def test_skips_already_string(self):
        data = {"tags": '["already"]'}
        result = _encode_json(data, frozenset({"tags"}))
        assert result["tags"] == '["already"]'

    def test_non_json_field_unchanged(self):
        data = {"other": [1, 2]}
        result = _encode_json(data, frozenset({"tags"}))
        assert result["other"] == [1, 2]

    def test_missing_json_field_key(self):
        data = {"name": "test"}
        result = _encode_json(data, frozenset({"tags"}))
        assert "tags" not in result


class TestDecodeJson:
    def test_decodes_valid_json_string(self):
        data = {"tags": '["a", "b"]', "name": "x"}
        result = _decode_json(data, frozenset({"tags"}))
        assert result["tags"] == ["a", "b"]

    def test_invalid_json_string_kept_as_is(self):
        data = {"tags": "not-valid-json{{{"}
        result = _decode_json(data, frozenset({"tags"}))
        assert result["tags"] == "not-valid-json{{{"

    def test_none_values_left_as_none(self):
        data = {"tags": None}
        result = _decode_json(data, frozenset({"tags"}))
        assert result["tags"] is None

    def test_non_string_non_none_untouched(self):
        data = {"tags": 42}
        result = _decode_json(data, frozenset({"tags"}))
        assert result["tags"] == 42

    def test_missing_key_no_error(self):
        data = {"name": "x"}
        result = _decode_json(data, frozenset({"tags"}))
        assert "tags" not in result


class TestRowToDict:
    @pytest.mark.asyncio
    async def test_converts_row(self):
        async with aiosqlite.connect(":memory:") as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute("CREATE TABLE t (a TEXT, b INTEGER)")
            await conn.execute("INSERT INTO t VALUES ('hello', 42)")
            async with conn.execute("SELECT * FROM t") as cur:
                row = await cur.fetchone()
            result = _row_to_dict(row)
            assert result == {"a": "hello", "b": 42}


# ===========================================================================
# Database lifecycle
# ===========================================================================


class TestDatabaseLifecycle:
    @pytest.mark.asyncio
    async def test_connect_and_close(self):
        database = Database(":memory:")
        await database.connect()
        assert database._db is not None
        await database.close()
        assert database._db is None

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self):
        database = Database(":memory:")
        # Should not raise
        await database.close()

    @pytest.mark.asyncio
    async def test_db_property_raises_when_not_connected(self):
        database = Database(":memory:")
        with pytest.raises(RuntimeError, match="Database not connected"):
            _ = database.db

    @pytest.mark.asyncio
    async def test_db_property_returns_connection(self, db):
        conn = db.db
        assert conn is not None

    @pytest.mark.asyncio
    async def test_ensure_connected_auto_connects(self):
        database = Database(":memory:")
        assert database._db is None
        await database._ensure_connected()
        assert database._db is not None
        await database.close()

    @pytest.mark.asyncio
    async def test_ensure_connected_noop_when_connected(self, db):
        conn = db._db
        await db._ensure_connected()
        assert db._db is conn

    @pytest.mark.asyncio
    async def test_connect_file_based(self, tmp_path):
        db_path = tmp_path / "sub" / "test.db"
        database = Database(db_path)
        await database.connect()
        assert db_path.exists()
        await database.close()

    @pytest.mark.asyncio
    async def test_default_path(self):
        database = Database()
        # Should use DB_PATH
        from fcp.services.database import DB_PATH

        assert database._db_path == str(DB_PATH)


# ===========================================================================
# Food Logs
# ===========================================================================


class TestGetUserLogs:
    @pytest.mark.asyncio
    async def test_empty(self, db):
        logs = await db.get_user_logs("u1")
        assert logs == []

    @pytest.mark.asyncio
    async def test_returns_user_logs(self, db):
        await db.create_log("u1", {"dish_name": "Ramen"})
        await db.create_log("u1", {"dish_name": "Pizza"})
        await db.create_log("u2", {"dish_name": "Tacos"})
        logs = await db.get_user_logs("u1")
        assert len(logs) == 2

    @pytest.mark.asyncio
    async def test_days_filter(self, db):
        await db.create_log("u1", {"dish_name": "Old"})
        # Manually backdate the old log
        await db.db.execute(
            "UPDATE food_logs SET created_at = ? WHERE dish_name = ?",
            ((datetime.now(UTC) - timedelta(days=15)).isoformat(), "Old"),
        )
        await db.db.commit()
        await db.create_log("u1", {"dish_name": "New"})
        logs = await db.get_user_logs("u1", days=7)
        assert len(logs) == 1
        assert logs[0]["dish_name"] == "New"

    @pytest.mark.asyncio
    async def test_start_date_filter(self, db):
        await db.create_log("u1", {"dish_name": "Old"})
        await db.db.execute(
            "UPDATE food_logs SET created_at = ? WHERE dish_name = ?",
            ((datetime.now(UTC) - timedelta(days=30)).isoformat(), "Old"),
        )
        await db.db.commit()
        await db.create_log("u1", {"dish_name": "New"})
        start = datetime.now(UTC) - timedelta(days=7)
        logs = await db.get_user_logs("u1", start_date=start)
        assert len(logs) == 1
        assert logs[0]["dish_name"] == "New"

    @pytest.mark.asyncio
    async def test_end_date_filter(self, db):
        await db.create_log("u1", {"dish_name": "Recent"})
        end = datetime.now(UTC) + timedelta(days=1)
        logs = await db.get_user_logs("u1", end_date=end)
        assert len(logs) == 1

    @pytest.mark.asyncio
    async def test_start_and_end_date(self, db):
        await db.create_log("u1", {"dish_name": "Match"})
        start = datetime.now(UTC) - timedelta(days=1)
        end = datetime.now(UTC) + timedelta(days=1)
        logs = await db.get_user_logs("u1", start_date=start, end_date=end)
        assert len(logs) == 1

    @pytest.mark.asyncio
    async def test_limit(self, db):
        for i in range(5):
            await db.create_log("u1", {"dish_name": f"Dish{i}"})
        logs = await db.get_user_logs("u1", limit=2)
        assert len(logs) == 2


class TestGetLog:
    @pytest.mark.asyncio
    async def test_found(self, db):
        log_id = await db.create_log("u1", {"dish_name": "Ramen"})
        log = await db.get_log("u1", log_id)
        assert log is not None
        assert log["dish_name"] == "Ramen"

    @pytest.mark.asyncio
    async def test_not_found(self, db):
        log = await db.get_log("u1", "nonexistent")
        assert log is None


class TestGetLogsByIds:
    @pytest.mark.asyncio
    async def test_empty_list(self, db):
        result = await db.get_logs_by_ids("u1", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_found(self, db):
        id1 = await db.create_log("u1", {"dish_name": "A"})
        id2 = await db.create_log("u1", {"dish_name": "B"})
        await db.create_log("u1", {"dish_name": "C"})
        result = await db.get_logs_by_ids("u1", [id1, id2])
        assert len(result) == 2
        names = {r["dish_name"] for r in result}
        assert names == {"A", "B"}


class TestCreateLog:
    @pytest.mark.asyncio
    async def test_creates_and_returns_id(self, db):
        log_id = await db.create_log("u1", {"dish_name": "Ramen", "tags": ["hot"]})
        assert isinstance(log_id, str)
        assert len(log_id) == 32
        log = await db.get_log("u1", log_id)
        assert log is not None
        assert log["tags"] == ["hot"]

    @pytest.mark.asyncio
    async def test_sets_timestamps(self, db):
        log_id = await db.create_log("u1", {"dish_name": "X"})
        log = await db.get_log("u1", log_id)
        assert log["created_at"] is not None
        assert log["updated_at"] is not None

    @pytest.mark.asyncio
    async def test_updates_user_last_active(self, db):
        await db.create_log("u1", {"dish_name": "X"})
        async with db.db.execute("SELECT last_active FROM users WHERE id = ?", ("u1",)) as cur:
            row = await cur.fetchone()
        assert row is not None


class TestUpdateLog:
    @pytest.mark.asyncio
    async def test_updates_existing(self, db):
        log_id = await db.create_log("u1", {"dish_name": "Old"})
        result = await db.update_log("u1", log_id, {"dish_name": "New"})
        assert result is True
        log = await db.get_log("u1", log_id)
        assert log["dish_name"] == "New"

    @pytest.mark.asyncio
    async def test_not_found(self, db):
        result = await db.update_log("u1", "nope", {"dish_name": "x"})
        assert result is False


class TestDeleteLog:
    @pytest.mark.asyncio
    async def test_deletes_existing(self, db):
        log_id = await db.create_log("u1", {"dish_name": "Bye"})
        result = await db.delete_log("u1", log_id)
        assert result is True
        log = await db.get_log("u1", log_id)
        assert log is None

    @pytest.mark.asyncio
    async def test_not_found(self, db):
        result = await db.delete_log("u1", "nope")
        assert result is False


class TestGetAllUserLogs:
    @pytest.mark.asyncio
    async def test_no_limit(self, db):
        for i in range(3):
            await db.create_log("u1", {"dish_name": f"D{i}"})
        logs = await db.get_all_user_logs("u1")
        assert len(logs) == 3

    @pytest.mark.asyncio
    async def test_with_limit(self, db):
        for i in range(5):
            await db.create_log("u1", {"dish_name": f"D{i}"})
        logs = await db.get_all_user_logs("u1", limit=2)
        assert len(logs) == 2


class TestGetUserLogsPaginated:
    @pytest.mark.asyncio
    async def test_pagination(self, db):
        for i in range(5):
            await db.create_log("u1", {"dish_name": f"D{i}"})
        logs, total = await db.get_user_logs_paginated("u1", page=1, page_size=2)
        assert len(logs) == 2
        assert total == 5

    @pytest.mark.asyncio
    async def test_second_page(self, db):
        for i in range(5):
            await db.create_log("u1", {"dish_name": f"D{i}"})
        logs, total = await db.get_user_logs_paginated("u1", page=2, page_size=2)
        assert len(logs) == 2
        assert total == 5

    @pytest.mark.asyncio
    async def test_page_size_cap(self, db):
        # page_size capped at 500
        await db.create_log("u1", {"dish_name": "X"})
        logs, total = await db.get_user_logs_paginated("u1", page=1, page_size=9999)
        assert len(logs) == 1

    @pytest.mark.asyncio
    async def test_page_min(self, db):
        # page min is 1
        await db.create_log("u1", {"dish_name": "X"})
        logs, total = await db.get_user_logs_paginated("u1", page=0, page_size=10)
        assert len(logs) == 1


class TestCountUserLogs:
    @pytest.mark.asyncio
    async def test_empty(self, db):
        count = await db.count_user_logs("u1")
        assert count == 0

    @pytest.mark.asyncio
    async def test_with_logs(self, db):
        for _ in range(3):
            await db.create_log("u1", {"dish_name": "X"})
        count = await db.count_user_logs("u1")
        assert count == 3


# ===========================================================================
# Pantry
# ===========================================================================


class TestGetPantry:
    @pytest.mark.asyncio
    async def test_empty(self, db):
        items = await db.get_pantry("u1")
        assert items == []

    @pytest.mark.asyncio
    async def test_with_items(self, db):
        await db.add_pantry_item("u1", {"name": "Eggs", "quantity": 12})
        items = await db.get_pantry("u1")
        assert len(items) == 1
        assert items[0]["name"] == "Eggs"


class TestUpdatePantryItem:
    @pytest.mark.asyncio
    async def test_with_name(self, db):
        item_id = await db.update_pantry_item("u1", {"name": "Milk", "quantity": 1})
        assert item_id == "milk"
        items = await db.get_pantry("u1")
        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_without_name_raises(self, db):
        with pytest.raises(ValueError, match="Item name is required"):
            await db.update_pantry_item("u1", {"quantity": 1})

    @pytest.mark.asyncio
    async def test_upsert_existing(self, db):
        await db.update_pantry_item("u1", {"name": "Milk", "quantity": 1})
        await db.update_pantry_item("u1", {"name": "Milk", "quantity": 2})
        items = await db.get_pantry("u1")
        assert len(items) == 1
        assert items[0]["quantity"] == 2.0

    @pytest.mark.asyncio
    async def test_with_explicit_id(self, db):
        item_id = await db.update_pantry_item("u1", {"id": "custom-id", "name": "Butter"})
        assert item_id == "custom-id"


class TestUpdatePantryItemsBatch:
    @pytest.mark.asyncio
    async def test_empty(self, db):
        ids = await db.update_pantry_items_batch("u1", [])
        assert ids == []

    @pytest.mark.asyncio
    async def test_with_items(self, db):
        ids = await db.update_pantry_items_batch(
            "u1",
            [{"name": "Eggs", "quantity": 12}, {"name": "Milk", "quantity": 1}],
        )
        assert len(ids) == 2

    @pytest.mark.asyncio
    async def test_items_missing_name_skipped(self, db):
        ids = await db.update_pantry_items_batch(
            "u1",
            [{"quantity": 1}, {"name": "Eggs", "quantity": 12}],
        )
        assert len(ids) == 1


class TestAddPantryItem:
    @pytest.mark.asyncio
    async def test_adds_item(self, db):
        item_id = await db.add_pantry_item("u1", {"name": "Salt"})
        assert len(item_id) == 32
        items = await db.get_pantry("u1")
        assert len(items) == 1


class TestDeletePantryItem:
    @pytest.mark.asyncio
    async def test_found(self, db):
        item_id = await db.add_pantry_item("u1", {"name": "Salt"})
        result = await db.delete_pantry_item("u1", item_id)
        assert result is True
        items = await db.get_pantry("u1")
        assert items == []

    @pytest.mark.asyncio
    async def test_not_found(self, db):
        result = await db.delete_pantry_item("u1", "nope")
        assert result is False


# ===========================================================================
# Recipes
# ===========================================================================


class TestGetRecipes:
    @pytest.mark.asyncio
    async def test_empty(self, db):
        recipes = await db.get_recipes("u1")
        assert recipes == []

    @pytest.mark.asyncio
    async def test_excludes_archived_by_default(self, db):
        r_id = await db.create_recipe("u1", {"name": "Archived"})
        await db.update_recipe("u1", r_id, {"is_archived": 1})
        await db.create_recipe("u1", {"name": "Active"})
        recipes = await db.get_recipes("u1")
        assert len(recipes) == 1
        assert recipes[0]["name"] == "Active"

    @pytest.mark.asyncio
    async def test_include_archived(self, db):
        r_id = await db.create_recipe("u1", {"name": "Archived"})
        await db.update_recipe("u1", r_id, {"is_archived": 1})
        await db.create_recipe("u1", {"name": "Active"})
        recipes = await db.get_recipes("u1", include_archived=True)
        assert len(recipes) == 2

    @pytest.mark.asyncio
    async def test_favorites_only(self, db):
        r_id = await db.create_recipe("u1", {"name": "Fav"})
        await db.update_recipe("u1", r_id, {"is_favorite": 1})
        await db.create_recipe("u1", {"name": "NotFav"})
        recipes = await db.get_recipes("u1", favorites_only=True)
        assert len(recipes) == 1
        assert recipes[0]["name"] == "Fav"


class TestGetRecipe:
    @pytest.mark.asyncio
    async def test_found(self, db):
        r_id = await db.create_recipe("u1", {"name": "Pasta"})
        recipe = await db.get_recipe("u1", r_id)
        assert recipe is not None
        assert recipe["name"] == "Pasta"

    @pytest.mark.asyncio
    async def test_not_found(self, db):
        recipe = await db.get_recipe("u1", "nope")
        assert recipe is None


class TestCreateRecipe:
    @pytest.mark.asyncio
    async def test_creates_recipe(self, db):
        r_id = await db.create_recipe(
            "u1",
            {"name": "Ramen", "ingredients": ["noodles", "broth"]},
        )
        assert len(r_id) == 32
        recipe = await db.get_recipe("u1", r_id)
        assert recipe["ingredients"] == ["noodles", "broth"]
        assert recipe["is_favorite"] == 0
        assert recipe["is_archived"] == 0


class TestUpdateRecipe:
    @pytest.mark.asyncio
    async def test_updates_existing(self, db):
        r_id = await db.create_recipe("u1", {"name": "Old"})
        result = await db.update_recipe("u1", r_id, {"name": "New"})
        assert result is True
        recipe = await db.get_recipe("u1", r_id)
        assert recipe["name"] == "New"

    @pytest.mark.asyncio
    async def test_not_found(self, db):
        result = await db.update_recipe("u1", "nope", {"name": "x"})
        assert result is False


class TestDeleteRecipe:
    @pytest.mark.asyncio
    async def test_deletes_existing(self, db):
        r_id = await db.create_recipe("u1", {"name": "Bye"})
        result = await db.delete_recipe("u1", r_id)
        assert result is True
        assert await db.get_recipe("u1", r_id) is None

    @pytest.mark.asyncio
    async def test_not_found(self, db):
        result = await db.delete_recipe("u1", "nope")
        assert result is False


# ===========================================================================
# Receipts
# ===========================================================================


class TestSaveReceipt:
    @pytest.mark.asyncio
    async def test_saves_receipt(self, db):
        receipt_id = await db.save_receipt("u1", {"items": [{"name": "Apple", "price": 1.5}]})
        assert len(receipt_id) == 32
        # Verify it's in the database
        async with db.db.execute("SELECT * FROM receipts WHERE id = ?", (receipt_id,)) as cur:
            row = await cur.fetchone()
        assert row is not None


# ===========================================================================
# Users / Preferences / Stats
# ===========================================================================


class TestGetActiveUsers:
    @pytest.mark.asyncio
    async def test_empty(self, db):
        users = await db.get_active_users()
        assert users == []

    @pytest.mark.asyncio
    async def test_returns_active(self, db):
        # create_log auto-creates user entry
        await db.create_log("u1", {"dish_name": "X"})
        users = await db.get_active_users()
        assert len(users) == 1
        assert users[0]["id"] == "u1"

    @pytest.mark.asyncio
    async def test_excludes_stale_users(self, db):
        await db.create_log("u1", {"dish_name": "X"})
        # Backdate the user
        old_date = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        await db.db.execute("UPDATE users SET last_active = ? WHERE id = ?", (old_date, "u1"))
        await db.db.commit()
        users = await db.get_active_users(days=7)
        assert users == []


class TestGetUserPreferences:
    @pytest.mark.asyncio
    async def test_no_user_returns_defaults(self, db):
        prefs = await db.get_user_preferences("nonexistent")
        assert prefs["timezone"] == "UTC"
        assert prefs["daily_insights_enabled"] is True
        assert prefs["display_name"] is None

    @pytest.mark.asyncio
    async def test_with_user_preferences(self, db):
        await db.update_user_preferences("u1", {"timezone": "US/Pacific", "extra": "val"})
        prefs = await db.get_user_preferences("u1")
        assert prefs["timezone"] == "US/Pacific"
        assert prefs["extra"] == "val"

    @pytest.mark.asyncio
    async def test_with_invalid_prefs_string(self, db):
        # Insert user row with malformed preferences string
        await db.db.execute(
            "INSERT INTO users (id, preferences) VALUES (?, ?)",
            ("u_bad", "not-valid-json{{{"),
        )
        await db.db.commit()
        prefs = await db.get_user_preferences("u_bad")
        # Should fall back to defaults
        assert prefs["timezone"] == "UTC"

    @pytest.mark.asyncio
    async def test_preferences_already_decoded_dict(self, db):
        # When _decode_json successfully decodes the preferences, it returns a dict
        await db.update_user_preferences("u1", {"timezone": "Europe/London"})
        prefs = await db.get_user_preferences("u1")
        assert prefs["timezone"] == "Europe/London"


class TestUpdateUserPreferences:
    @pytest.mark.asyncio
    async def test_creates_user_if_not_exists(self, db):
        await db.update_user_preferences("u_new", {"timezone": "Asia/Tokyo"})
        prefs = await db.get_user_preferences("u_new")
        assert prefs["timezone"] == "Asia/Tokyo"

    @pytest.mark.asyncio
    async def test_updates_existing(self, db):
        await db.update_user_preferences("u1", {"timezone": "UTC"})
        await db.update_user_preferences("u1", {"timezone": "US/Eastern"})
        prefs = await db.get_user_preferences("u1")
        assert prefs["timezone"] == "US/Eastern"


class TestInvalidateUserStats:
    @pytest.mark.asyncio
    async def test_clears_stats(self, db):
        await db.create_log("u1", {"dish_name": "X"})
        # Build stats cache
        await db.get_user_stats("u1")
        # Invalidate
        await db.invalidate_user_stats("u1")
        # Check stats is NULL
        async with db.db.execute("SELECT stats FROM users WHERE id = ?", ("u1",)) as cur:
            row = await cur.fetchone()
        assert row[0] is None


class TestGetUserStats:
    @pytest.mark.asyncio
    async def test_no_logs(self, db):
        # Ensure user row exists but no logs
        await db.db.execute("INSERT INTO users (id) VALUES (?)", ("u1",))
        await db.db.commit()
        stats = await db.get_user_stats("u1")
        assert stats["total_logs"] == 0
        assert stats["current_streak"] == 0
        assert stats["longest_streak"] == 0
        assert stats["first_log_date"] is None

    @pytest.mark.asyncio
    async def test_with_logs_streak_includes_today(self, db):
        # Create a log dated today
        await db.create_log("u1", {"dish_name": "Today"})
        # Invalidate to force recalc
        await db.invalidate_user_stats("u1")
        stats = await db.get_user_stats("u1")
        assert stats["total_logs"] == 1
        assert stats["current_streak"] >= 1
        assert stats["longest_streak"] >= 1
        assert stats["first_log_date"] is not None
        assert stats["last_log_date"] is not None

    @pytest.mark.asyncio
    async def test_with_cached_stats(self, db):
        await db.create_log("u1", {"dish_name": "X"})
        # Build cache
        stats1 = await db.get_user_stats("u1")
        # Second call should use cache
        stats2 = await db.get_user_stats("u1")
        assert stats1 == stats2

    @pytest.mark.asyncio
    async def test_stale_streak_reset(self, db):
        """When last_log_date is > 1 day ago, current_streak should reset to 0."""
        await db.create_log("u1", {"dish_name": "X"})
        stats = await db.get_user_stats("u1")
        # Manually set last_log_date to 5 days ago in cached stats
        stats["last_log_date"] = (datetime.now(UTC) - timedelta(days=5)).date().isoformat()
        stats["current_streak"] = 3
        stats_json = json.dumps(stats)
        await db.db.execute("UPDATE users SET stats = ? WHERE id = ?", (stats_json, "u1"))
        await db.db.commit()
        result = await db.get_user_stats("u1")
        assert result["current_streak"] == 0

    @pytest.mark.asyncio
    async def test_streak_yesterday_still_active(self, db):
        """Streak that includes yesterday but not today should still count."""
        today = datetime.now(UTC).date()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)

        # Create logs for yesterday and day before
        log_id1 = await db.create_log("u1", {"dish_name": "Y1"})
        log_id2 = await db.create_log("u1", {"dish_name": "Y2"})
        await db.db.execute(
            "UPDATE food_logs SET created_at = ? WHERE id = ?",
            (datetime(yesterday.year, yesterday.month, yesterday.day, 12, 0, 0, tzinfo=UTC).isoformat(), log_id1),
        )
        await db.db.execute(
            "UPDATE food_logs SET created_at = ? WHERE id = ?",
            (
                datetime(two_days_ago.year, two_days_ago.month, two_days_ago.day, 12, 0, 0, tzinfo=UTC).isoformat(),
                log_id2,
            ),
        )
        await db.db.commit()
        await db.invalidate_user_stats("u1")
        stats = await db.get_user_stats("u1")
        assert stats["current_streak"] == 2

    @pytest.mark.asyncio
    async def test_longest_streak_calculation(self, db):
        """Verify longest streak across non-consecutive date runs."""
        today = datetime.now(UTC).date()
        # Create a 3-day streak in the past, then a gap, then a 1-day streak
        dates = [
            today - timedelta(days=20),
            today - timedelta(days=19),
            today - timedelta(days=18),
            # gap
            today - timedelta(days=10),
        ]
        for d in dates:
            log_id = await db.create_log("u1", {"dish_name": f"D{d}"})
            await db.db.execute(
                "UPDATE food_logs SET created_at = ? WHERE id = ?",
                (datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=UTC).isoformat(), log_id),
            )
        await db.db.commit()
        await db.invalidate_user_stats("u1")
        stats = await db.get_user_stats("u1")
        assert stats["longest_streak"] == 3

    @pytest.mark.asyncio
    async def test_cuisine_counting(self, db):
        await db.create_log("u1", {"dish_name": "A", "cuisine": "Japanese"})
        await db.create_log("u1", {"dish_name": "B", "cuisine": "japanese"})  # same, case-insensitive
        await db.create_log("u1", {"dish_name": "C", "cuisine": "Italian"})
        await db.invalidate_user_stats("u1")
        stats = await db.get_user_stats("u1")
        assert stats["cuisines_tried"] == 2

    @pytest.mark.asyncio
    async def test_no_user_row_no_logs(self, db):
        """get_user_stats for a user with no row and no logs."""
        stats = await db.get_user_stats("ghost")
        assert stats["total_logs"] == 0

    @pytest.mark.asyncio
    async def test_cached_stats_without_last_log_date(self, db):
        """Cached stats that have no last_log_date key (falsy) should return as-is."""
        cached = {
            "current_streak": 0,
            "longest_streak": 0,
            "total_logs": 0,
            "cuisines_tried": 0,
            "first_log_date": None,
            "last_log_date": None,
        }
        await db.db.execute(
            "INSERT INTO users (id, stats) VALUES (?, ?)",
            ("u_cached", json.dumps(cached)),
        )
        await db.db.commit()
        stats = await db.get_user_stats("u_cached")
        assert stats["total_logs"] == 0

    @pytest.mark.asyncio
    async def test_cached_stats_with_invalid_last_log_date(self, db):
        """Cached stats with invalid date string in last_log_date."""
        cached = {
            "current_streak": 5,
            "longest_streak": 5,
            "total_logs": 10,
            "cuisines_tried": 3,
            "first_log_date": "2025-01-01",
            "last_log_date": "not-a-date",
        }
        await db.db.execute(
            "INSERT INTO users (id, stats) VALUES (?, ?)",
            ("u_bad_date", json.dumps(cached)),
        )
        await db.db.commit()
        stats = await db.get_user_stats("u_bad_date")
        # ValueError branch: stats returned as-is with original streak
        assert stats["current_streak"] == 5

    @pytest.mark.asyncio
    async def test_logs_with_no_cuisine(self, db):
        """Logs that have NULL cuisine should not be added to cuisines set."""
        await db.create_log("u1", {"dish_name": "NoCuisine"})
        await db.invalidate_user_stats("u1")
        stats = await db.get_user_stats("u1")
        assert stats["cuisines_tried"] == 0

    @pytest.mark.asyncio
    async def test_logs_with_invalid_created_at(self, db):
        """Logs with unparseable created_at should be skipped in streak calc."""
        # We need 3 logs: 2 valid (earliest + latest) so first/last queries
        # return valid dates, plus 1 bad date in the middle that triggers the
        # ValueError branch inside the 90-day loop.
        lid_early = await db.create_log("u1", {"dish_name": "Early"})
        lid_bad = await db.create_log("u1", {"dish_name": "Bad"})
        lid_recent = await db.create_log("u1", {"dish_name": "Recent"})

        early_dt = (datetime.now(UTC) - timedelta(days=60)).isoformat()
        bad_dt = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-") + "XBAD"
        recent_dt = datetime.now(UTC).isoformat()

        await db.db.execute("UPDATE food_logs SET created_at = ? WHERE id = ?", (early_dt, lid_early))
        await db.db.execute("UPDATE food_logs SET created_at = ? WHERE id = ?", (bad_dt, lid_bad))
        await db.db.execute("UPDATE food_logs SET created_at = ? WHERE id = ?", (recent_dt, lid_recent))
        await db.db.commit()
        await db.invalidate_user_stats("u1")
        stats = await db.get_user_stats("u1")
        assert stats["total_logs"] == 3
        # The bad row is skipped; valid rows still counted
        assert stats["first_log_date"] is not None
        assert stats["last_log_date"] is not None

    @pytest.mark.asyncio
    async def test_streak_gap_resets_run(self, db):
        """Longest streak resets current_run when there's a gap."""
        today = datetime.now(UTC).date()
        # Day 1, Day 2 (streak of 2), gap, Day 5 (streak of 1)
        dates = [
            today - timedelta(days=10),
            today - timedelta(days=9),
            today - timedelta(days=5),
        ]
        for d in dates:
            log_id = await db.create_log("u1", {"dish_name": f"D{d}"})
            await db.db.execute(
                "UPDATE food_logs SET created_at = ? WHERE id = ?",
                (datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=UTC).isoformat(), log_id),
            )
        await db.db.commit()
        await db.invalidate_user_stats("u1")
        stats = await db.get_user_stats("u1")
        assert stats["longest_streak"] == 2

    @pytest.mark.asyncio
    async def test_logs_with_null_created_at(self, db):
        """Logs with NULL created_at should be skipped in first/last date queries.

        This covers:
        - The falsy branch of ``if r and r[0]:`` for first_date (line 644->646)
        - The falsy branch of ``if r and r[0]:`` for last_date (line 648->652)
        - Streak calculation when no valid dates exist
        """
        # Directly insert a log with NULL created_at to ensure cross-platform consistency
        await db.db.execute(
            "INSERT INTO food_logs (id, user_id, dish_name, created_at, updated_at, deleted) "
            "VALUES (?, ?, ?, NULL, ?, 0)",
            (_new_id(), "u1", "Null Log", _now()),
        )
        await db.db.commit()
        await db.invalidate_user_stats("u1")
        stats = await db.get_user_stats("u1")
        assert stats["total_logs"] == 1
        # No parseable dates -> streak 0, longest 0
        assert stats["current_streak"] == 0
        assert stats["longest_streak"] == 0
        assert stats["first_log_date"] is None
        assert stats["last_log_date"] is None

    @pytest.mark.asyncio
    async def test_logs_with_empty_created_at_in_window(self, db):
        """Cover the ``if created:`` falsy branch (line 600->605).

        The 90-day window SQL filter ``created_at >= ?`` normally prevents
        NULL / empty created_at rows from appearing.  We wrap the connection's
        execute so that the 90-day cuisine/streak query returns a fake row
        whose ``created_at`` is the empty string, while all other queries
        pass through to the real database.
        """
        # Create a real log so total_logs > 0
        await db.create_log("u1", {"dish_name": "Real"})
        await db.invalidate_user_stats("u1")

        # Build a fake row tuple: (created_at, cuisine) where created_at is ""
        fake_row = ("", "Italian")

        original_execute = db.db.execute

        class _FakeCursorCtx:
            """Mimics aiosqlite's cursor context manager and plain await."""

            def __init__(self, rows):
                self._rows = rows

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                pass

            async def fetchall(self):
                return self._rows

            async def fetchone(self):
                return self._rows[0] if self._rows else None

            # Allow plain ``await execute(...)`` (non-SELECT usage)
            def __await__(self):
                return self._finish().__await__()

            async def _finish(self):
                return self

        def patched_execute(sql, params=None):
            if "created_at, cuisine" in sql:
                return _FakeCursorCtx([fake_row])
            return original_execute(sql, params)

        with patch.object(db._db, "execute", side_effect=patched_execute):
            stats = await db.get_user_stats("u1")

        # The empty created_at is skipped; Italian is still counted
        assert stats["cuisines_tried"] == 1


# ===========================================================================
# Notifications
# ===========================================================================


class TestStoreNotification:
    @pytest.mark.asyncio
    async def test_stores(self, db):
        nid = await db.store_notification("u1", "info", {"message": "Hello"})
        assert len(nid) == 32


class TestGetUserNotifications:
    @pytest.mark.asyncio
    async def test_all(self, db):
        await db.store_notification("u1", "info", {"msg": "a"})
        await db.store_notification("u1", "warn", {"msg": "b"})
        notifs = await db.get_user_notifications("u1")
        assert len(notifs) == 2

    @pytest.mark.asyncio
    async def test_unread_only(self, db):
        nid = await db.store_notification("u1", "info", {"msg": "a"})
        await db.store_notification("u1", "info", {"msg": "b"})
        await db.mark_notification_read("u1", nid)
        notifs = await db.get_user_notifications("u1", unread_only=True)
        assert len(notifs) == 1


class TestMarkNotificationRead:
    @pytest.mark.asyncio
    async def test_found(self, db):
        nid = await db.store_notification("u1", "info", {"msg": "x"})
        result = await db.mark_notification_read("u1", nid)
        assert result is True

    @pytest.mark.asyncio
    async def test_not_found(self, db):
        result = await db.mark_notification_read("u1", "nope")
        assert result is False


# ===========================================================================
# Drafts
# ===========================================================================


class TestSaveDraft:
    @pytest.mark.asyncio
    async def test_saves(self, db):
        draft_id = await db.save_draft("u1", {"content": {"text": "hello"}, "content_type": "post"})
        assert len(draft_id) == 32
        draft = await db.get_draft("u1", draft_id)
        assert draft is not None
        assert draft["content"] == {"text": "hello"}


class TestGetDrafts:
    @pytest.mark.asyncio
    async def test_returns_drafts(self, db):
        await db.save_draft("u1", {"content_type": "a"})
        await db.save_draft("u1", {"content_type": "b"})
        drafts = await db.get_drafts("u1")
        assert len(drafts) == 2


class TestGetDraft:
    @pytest.mark.asyncio
    async def test_found(self, db):
        did = await db.save_draft("u1", {"content_type": "x"})
        draft = await db.get_draft("u1", did)
        assert draft is not None

    @pytest.mark.asyncio
    async def test_not_found(self, db):
        draft = await db.get_draft("u1", "nope")
        assert draft is None


class TestUpdateDraft:
    @pytest.mark.asyncio
    async def test_updates(self, db):
        did = await db.save_draft("u1", {"content_type": "old"})
        result = await db.update_draft("u1", did, {"content_type": "new"})
        assert result is True
        draft = await db.get_draft("u1", did)
        assert draft["content_type"] == "new"

    @pytest.mark.asyncio
    async def test_not_found(self, db):
        result = await db.update_draft("u1", "nope", {"content_type": "x"})
        assert result is False


class TestDeleteDraft:
    @pytest.mark.asyncio
    async def test_deletes(self, db):
        did = await db.save_draft("u1", {"content_type": "x"})
        result = await db.delete_draft("u1", did)
        assert result is True
        assert await db.get_draft("u1", did) is None

    @pytest.mark.asyncio
    async def test_not_found(self, db):
        result = await db.delete_draft("u1", "nope")
        assert result is False


# ===========================================================================
# Published Content
# ===========================================================================


class TestSavePublishedContent:
    @pytest.mark.asyncio
    async def test_saves(self, db):
        cid = await db.save_published_content(
            "u1",
            {"content": {"text": "published"}, "platforms": ["twitter"]},
        )
        assert len(cid) == 32


class TestGetPublishedContent:
    @pytest.mark.asyncio
    async def test_returns_list(self, db):
        await db.save_published_content("u1", {"content_type": "post"})
        await db.save_published_content("u1", {"content_type": "reel"})
        items = await db.get_published_content("u1")
        assert len(items) == 2


class TestGetPublishedContentItem:
    @pytest.mark.asyncio
    async def test_found(self, db):
        cid = await db.save_published_content("u1", {"content_type": "post"})
        item = await db.get_published_content_item("u1", cid)
        assert item is not None

    @pytest.mark.asyncio
    async def test_not_found(self, db):
        item = await db.get_published_content_item("u1", "nope")
        assert item is None


class TestUpdatePublishedContent:
    @pytest.mark.asyncio
    async def test_updates(self, db):
        cid = await db.save_published_content("u1", {"content_type": "post"})
        await db.update_published_content("u1", cid, {"content_type": "reel"})
        item = await db.get_published_content_item("u1", cid)
        assert item["content_type"] == "reel"


class TestPublishDraft:
    @pytest.mark.asyncio
    async def test_draft_not_found(self, db):
        content_id, ok = await db.publish_draft("u1", "nope", {})
        assert content_id == ""
        assert ok is False

    @pytest.mark.asyncio
    async def test_already_published(self, db):
        did = await db.save_draft("u1", {"content_type": "post"})
        await db.update_draft("u1", did, {"status": "published"})
        content_id, ok = await db.publish_draft("u1", did, {})
        assert content_id == ""
        assert ok is False

    @pytest.mark.asyncio
    async def test_success(self, db):
        did = await db.save_draft("u1", {"content_type": "post", "status": "draft"})
        content_id, ok = await db.publish_draft(
            "u1",
            did,
            {"content": {"text": "published!"}},
        )
        assert ok is True
        assert len(content_id) == 32
        # Draft status should be updated
        draft = await db.get_draft("u1", did)
        assert draft["status"] == "published"
        # Published content should exist
        item = await db.get_published_content_item("u1", content_id)
        assert item is not None
        assert item["draft_id"] == did
