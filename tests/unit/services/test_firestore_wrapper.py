"""Tests for fcp.services.firestore wrapper module."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import fcp.services.firestore as firestore_mod
from fcp.services.firestore import (
    FirestoreClient,
    _FirestoreClientProxy,
    _get_legacy_client,
    get_db,
    get_firestore_client,
    get_firestore_status,
    reset_firestore_client,
    reset_firestore_state,
)


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset all module-level singletons between tests."""
    firestore_mod._firestore_client = None
    reset_firestore_client()
    yield
    firestore_mod._firestore_client = None
    reset_firestore_client()


# ---------------------------------------------------------------------------
# FirestoreClient __init__ and properties
# ---------------------------------------------------------------------------


class TestFirestoreClientInit:
    def test_uses_provided_db(self):
        mock_db = MagicMock()
        client = FirestoreClient(db=mock_db)
        assert client.db is mock_db

    def test_creates_default_db_when_none(self):
        with patch("fcp.services.firestore.Database") as mock_cls:
            mock_cls.return_value = MagicMock()
            client = FirestoreClient()
            mock_cls.assert_called_once()
            assert client.db is mock_cls.return_value


# ---------------------------------------------------------------------------
# Lifecycle methods
# ---------------------------------------------------------------------------


class TestFirestoreClientLifecycle:
    @pytest.mark.asyncio
    async def test_connect_delegates(self):
        mock_db = AsyncMock()
        client = FirestoreClient(db=mock_db)
        await client.connect()
        mock_db.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_delegates(self):
        mock_db = AsyncMock()
        client = FirestoreClient(db=mock_db)
        await client.close()
        mock_db.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# Food Log methods
# ---------------------------------------------------------------------------


class TestFirestoreClientFoodLogs:
    @pytest.mark.asyncio
    async def test_get_user_logs(self):
        mock_db = AsyncMock()
        mock_db.get_user_logs.return_value = [{"id": "1"}]
        client = FirestoreClient(db=mock_db)
        start = datetime(2026, 1, 1)
        end = datetime(2026, 1, 31)
        result = await client.get_user_logs("u1", limit=10, days=7, start_date=start, end_date=end)
        mock_db.get_user_logs.assert_awaited_once_with("u1", limit=10, days=7, start_date=start, end_date=end)
        assert result == [{"id": "1"}]

    @pytest.mark.asyncio
    async def test_get_log(self):
        mock_db = AsyncMock()
        mock_db.get_log.return_value = {"id": "log1"}
        client = FirestoreClient(db=mock_db)
        result = await client.get_log("u1", "log1")
        mock_db.get_log.assert_awaited_once_with("u1", "log1")
        assert result == {"id": "log1"}

    @pytest.mark.asyncio
    async def test_get_logs_by_ids(self):
        mock_db = AsyncMock()
        mock_db.get_logs_by_ids.return_value = [{"id": "a"}, {"id": "b"}]
        client = FirestoreClient(db=mock_db)
        result = await client.get_logs_by_ids("u1", ["a", "b"])
        mock_db.get_logs_by_ids.assert_awaited_once_with("u1", ["a", "b"])
        assert result == [{"id": "a"}, {"id": "b"}]

    @pytest.mark.asyncio
    async def test_create_log(self):
        mock_db = AsyncMock()
        mock_db.create_log.return_value = "new-id"
        client = FirestoreClient(db=mock_db)
        result = await client.create_log("u1", {"dish_name": "Test"})
        mock_db.create_log.assert_awaited_once_with("u1", {"dish_name": "Test"})
        assert result == "new-id"

    @pytest.mark.asyncio
    async def test_update_log(self):
        mock_db = AsyncMock()
        mock_db.update_log.return_value = True
        client = FirestoreClient(db=mock_db)
        result = await client.update_log("u1", "log1", {"notes": "updated"})
        mock_db.update_log.assert_awaited_once_with("u1", "log1", {"notes": "updated"})
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_log(self):
        mock_db = AsyncMock()
        mock_db.delete_log.return_value = True
        client = FirestoreClient(db=mock_db)
        result = await client.delete_log("u1", "log1")
        mock_db.delete_log.assert_awaited_once_with("u1", "log1")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_all_user_logs(self):
        mock_db = AsyncMock()
        mock_db.get_all_user_logs.return_value = [{"id": "x"}]
        client = FirestoreClient(db=mock_db)
        result = await client.get_all_user_logs("u1", limit=50)
        mock_db.get_all_user_logs.assert_awaited_once_with("u1", limit=50)
        assert result == [{"id": "x"}]

    @pytest.mark.asyncio
    async def test_get_user_logs_paginated(self):
        mock_db = AsyncMock()
        mock_db.get_user_logs_paginated.return_value = ([{"id": "p1"}], 5)
        client = FirestoreClient(db=mock_db)
        result = await client.get_user_logs_paginated("u1", page=2, page_size=10)
        mock_db.get_user_logs_paginated.assert_awaited_once_with("u1", page=2, page_size=10)
        assert result == ([{"id": "p1"}], 5)

    @pytest.mark.asyncio
    async def test_count_user_logs(self):
        mock_db = AsyncMock()
        mock_db.count_user_logs.return_value = 42
        client = FirestoreClient(db=mock_db)
        result = await client.count_user_logs("u1")
        mock_db.count_user_logs.assert_awaited_once_with("u1")
        assert result == 42


# ---------------------------------------------------------------------------
# Pantry methods
# ---------------------------------------------------------------------------


class TestFirestoreClientPantry:
    @pytest.mark.asyncio
    async def test_get_pantry(self):
        mock_db = AsyncMock()
        mock_db.get_pantry.return_value = [{"name": "eggs"}]
        client = FirestoreClient(db=mock_db)
        result = await client.get_pantry("u1")
        mock_db.get_pantry.assert_awaited_once_with("u1")
        assert result == [{"name": "eggs"}]

    @pytest.mark.asyncio
    async def test_update_pantry_item(self):
        mock_db = AsyncMock()
        mock_db.update_pantry_item.return_value = "item-id"
        client = FirestoreClient(db=mock_db)
        result = await client.update_pantry_item("u1", {"name": "milk"})
        mock_db.update_pantry_item.assert_awaited_once_with("u1", {"name": "milk"})
        assert result == "item-id"

    @pytest.mark.asyncio
    async def test_update_pantry_items_batch(self):
        mock_db = AsyncMock()
        mock_db.update_pantry_items_batch.return_value = ["id1", "id2"]
        client = FirestoreClient(db=mock_db)
        items = [{"name": "a"}, {"name": "b"}]
        result = await client.update_pantry_items_batch("u1", items)
        mock_db.update_pantry_items_batch.assert_awaited_once_with("u1", items)
        assert result == ["id1", "id2"]

    @pytest.mark.asyncio
    async def test_add_pantry_item(self):
        mock_db = AsyncMock()
        mock_db.add_pantry_item.return_value = "new-item"
        client = FirestoreClient(db=mock_db)
        result = await client.add_pantry_item("u1", {"name": "bread"})
        mock_db.add_pantry_item.assert_awaited_once_with("u1", {"name": "bread"})
        assert result == "new-item"

    @pytest.mark.asyncio
    async def test_delete_pantry_item(self):
        mock_db = AsyncMock()
        mock_db.delete_pantry_item.return_value = True
        client = FirestoreClient(db=mock_db)
        result = await client.delete_pantry_item("u1", "item-id")
        mock_db.delete_pantry_item.assert_awaited_once_with("u1", "item-id")
        assert result is True


# ---------------------------------------------------------------------------
# Recipe methods
# ---------------------------------------------------------------------------


class TestFirestoreClientRecipes:
    @pytest.mark.asyncio
    async def test_get_recipes(self):
        mock_db = AsyncMock()
        mock_db.get_recipes.return_value = [{"title": "Pasta"}]
        client = FirestoreClient(db=mock_db)
        result = await client.get_recipes("u1", limit=25, include_archived=True, favorites_only=True)
        mock_db.get_recipes.assert_awaited_once_with("u1", limit=25, include_archived=True, favorites_only=True)
        assert result == [{"title": "Pasta"}]

    @pytest.mark.asyncio
    async def test_get_recipe(self):
        mock_db = AsyncMock()
        mock_db.get_recipe.return_value = {"id": "r1"}
        client = FirestoreClient(db=mock_db)
        result = await client.get_recipe("u1", "r1")
        mock_db.get_recipe.assert_awaited_once_with("u1", "r1")
        assert result == {"id": "r1"}

    @pytest.mark.asyncio
    async def test_create_recipe(self):
        mock_db = AsyncMock()
        mock_db.create_recipe.return_value = "recipe-id"
        client = FirestoreClient(db=mock_db)
        result = await client.create_recipe("u1", {"title": "Soup"})
        mock_db.create_recipe.assert_awaited_once_with("u1", {"title": "Soup"})
        assert result == "recipe-id"

    @pytest.mark.asyncio
    async def test_update_recipe(self):
        mock_db = AsyncMock()
        mock_db.update_recipe.return_value = True
        client = FirestoreClient(db=mock_db)
        result = await client.update_recipe("u1", "r1", {"title": "Better Soup"})
        mock_db.update_recipe.assert_awaited_once_with("u1", "r1", {"title": "Better Soup"})
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_recipe(self):
        mock_db = AsyncMock()
        mock_db.delete_recipe.return_value = True
        client = FirestoreClient(db=mock_db)
        result = await client.delete_recipe("u1", "r1")
        mock_db.delete_recipe.assert_awaited_once_with("u1", "r1")
        assert result is True


# ---------------------------------------------------------------------------
# Receipt methods
# ---------------------------------------------------------------------------


class TestFirestoreClientReceipts:
    @pytest.mark.asyncio
    async def test_save_receipt(self):
        mock_db = AsyncMock()
        mock_db.save_receipt.return_value = "receipt-id"
        client = FirestoreClient(db=mock_db)
        result = await client.save_receipt("u1", {"store": "Costco"})
        mock_db.save_receipt.assert_awaited_once_with("u1", {"store": "Costco"})
        assert result == "receipt-id"


# ---------------------------------------------------------------------------
# Users / Preferences / Stats
# ---------------------------------------------------------------------------


class TestFirestoreClientUsersPrefsStats:
    @pytest.mark.asyncio
    async def test_get_active_users(self):
        mock_db = AsyncMock()
        mock_db.get_active_users.return_value = [{"user_id": "u1"}]
        client = FirestoreClient(db=mock_db)
        result = await client.get_active_users(days=14)
        mock_db.get_active_users.assert_awaited_once_with(days=14)
        assert result == [{"user_id": "u1"}]

    @pytest.mark.asyncio
    async def test_get_user_preferences(self):
        mock_db = AsyncMock()
        mock_db.get_user_preferences.return_value = {"theme": "dark"}
        client = FirestoreClient(db=mock_db)
        result = await client.get_user_preferences("u1")
        mock_db.get_user_preferences.assert_awaited_once_with("u1")
        assert result == {"theme": "dark"}

    @pytest.mark.asyncio
    async def test_update_user_preferences(self):
        mock_db = AsyncMock()
        client = FirestoreClient(db=mock_db)
        await client.update_user_preferences("u1", {"theme": "light"})
        mock_db.update_user_preferences.assert_awaited_once_with("u1", {"theme": "light"})

    @pytest.mark.asyncio
    async def test_invalidate_user_stats(self):
        mock_db = AsyncMock()
        client = FirestoreClient(db=mock_db)
        await client.invalidate_user_stats("u1")
        mock_db.invalidate_user_stats.assert_awaited_once_with("u1")

    @pytest.mark.asyncio
    async def test_get_user_stats(self):
        mock_db = AsyncMock()
        mock_db.get_user_stats.return_value = {"total_logs": 100}
        client = FirestoreClient(db=mock_db)
        result = await client.get_user_stats("u1")
        mock_db.get_user_stats.assert_awaited_once_with("u1")
        assert result == {"total_logs": 100}


# ---------------------------------------------------------------------------
# Notification methods
# ---------------------------------------------------------------------------


class TestFirestoreClientNotifications:
    @pytest.mark.asyncio
    async def test_store_notification(self):
        mock_db = AsyncMock()
        mock_db.store_notification.return_value = "notif-id"
        client = FirestoreClient(db=mock_db)
        result = await client.store_notification("u1", "info", {"msg": "hi"})
        mock_db.store_notification.assert_awaited_once_with("u1", "info", {"msg": "hi"})
        assert result == "notif-id"

    @pytest.mark.asyncio
    async def test_get_user_notifications(self):
        mock_db = AsyncMock()
        mock_db.get_user_notifications.return_value = [{"id": "n1"}]
        client = FirestoreClient(db=mock_db)
        result = await client.get_user_notifications("u1", limit=5, unread_only=True)
        mock_db.get_user_notifications.assert_awaited_once_with("u1", limit=5, unread_only=True)
        assert result == [{"id": "n1"}]

    @pytest.mark.asyncio
    async def test_mark_notification_read(self):
        mock_db = AsyncMock()
        mock_db.mark_notification_read.return_value = True
        client = FirestoreClient(db=mock_db)
        result = await client.mark_notification_read("u1", "n1")
        mock_db.mark_notification_read.assert_awaited_once_with("u1", "n1")
        assert result is True


# ---------------------------------------------------------------------------
# Draft methods
# ---------------------------------------------------------------------------


class TestFirestoreClientDrafts:
    @pytest.mark.asyncio
    async def test_save_draft(self):
        mock_db = AsyncMock()
        mock_db.save_draft.return_value = "draft-id"
        client = FirestoreClient(db=mock_db)
        result = await client.save_draft("u1", {"title": "My Draft"})
        mock_db.save_draft.assert_awaited_once_with("u1", {"title": "My Draft"})
        assert result == "draft-id"

    @pytest.mark.asyncio
    async def test_get_drafts(self):
        mock_db = AsyncMock()
        mock_db.get_drafts.return_value = [{"id": "d1"}]
        client = FirestoreClient(db=mock_db)
        result = await client.get_drafts("u1", limit=10)
        mock_db.get_drafts.assert_awaited_once_with("u1", limit=10)
        assert result == [{"id": "d1"}]

    @pytest.mark.asyncio
    async def test_get_draft(self):
        mock_db = AsyncMock()
        mock_db.get_draft.return_value = {"id": "d1", "title": "Draft"}
        client = FirestoreClient(db=mock_db)
        result = await client.get_draft("u1", "d1")
        mock_db.get_draft.assert_awaited_once_with("u1", "d1")
        assert result == {"id": "d1", "title": "Draft"}

    @pytest.mark.asyncio
    async def test_update_draft(self):
        mock_db = AsyncMock()
        mock_db.update_draft.return_value = True
        client = FirestoreClient(db=mock_db)
        result = await client.update_draft("u1", "d1", {"title": "Updated"})
        mock_db.update_draft.assert_awaited_once_with("u1", "d1", {"title": "Updated"})
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_draft(self):
        mock_db = AsyncMock()
        mock_db.delete_draft.return_value = True
        client = FirestoreClient(db=mock_db)
        result = await client.delete_draft("u1", "d1")
        mock_db.delete_draft.assert_awaited_once_with("u1", "d1")
        assert result is True


# ---------------------------------------------------------------------------
# Published Content methods
# ---------------------------------------------------------------------------


class TestFirestoreClientPublishedContent:
    @pytest.mark.asyncio
    async def test_save_published_content(self):
        mock_db = AsyncMock()
        mock_db.save_published_content.return_value = "pub-id"
        client = FirestoreClient(db=mock_db)
        result = await client.save_published_content("u1", {"body": "Hello"})
        mock_db.save_published_content.assert_awaited_once_with("u1", {"body": "Hello"})
        assert result == "pub-id"

    @pytest.mark.asyncio
    async def test_get_published_content(self):
        mock_db = AsyncMock()
        mock_db.get_published_content.return_value = [{"id": "pc1"}]
        client = FirestoreClient(db=mock_db)
        result = await client.get_published_content("u1", limit=25)
        mock_db.get_published_content.assert_awaited_once_with("u1", limit=25)
        assert result == [{"id": "pc1"}]

    @pytest.mark.asyncio
    async def test_get_published_content_item(self):
        mock_db = AsyncMock()
        mock_db.get_published_content_item.return_value = {"id": "pc1"}
        client = FirestoreClient(db=mock_db)
        result = await client.get_published_content_item("u1", "pc1")
        mock_db.get_published_content_item.assert_awaited_once_with("u1", "pc1")
        assert result == {"id": "pc1"}

    @pytest.mark.asyncio
    async def test_update_published_content(self):
        mock_db = AsyncMock()
        client = FirestoreClient(db=mock_db)
        await client.update_published_content("u1", "pc1", {"body": "Updated"})
        mock_db.update_published_content.assert_awaited_once_with("u1", "pc1", {"body": "Updated"})

    @pytest.mark.asyncio
    async def test_publish_draft(self):
        mock_db = AsyncMock()
        mock_db.publish_draft.return_value = ("pub-id", True)
        client = FirestoreClient(db=mock_db)
        result = await client.publish_draft("u1", "d1", {"body": "Published"})
        mock_db.publish_draft.assert_awaited_once_with("u1", "d1", {"body": "Published"})
        assert result == ("pub-id", True)


# ---------------------------------------------------------------------------
# Module-level functions
# ---------------------------------------------------------------------------


class TestGetFirestoreClient:
    def test_returns_firestore_client(self):
        with patch("fcp.services.firestore.Database"):
            client = get_firestore_client()
            assert isinstance(client, FirestoreClient)

    def test_singleton_returns_same_instance(self):
        with patch("fcp.services.firestore.Database"):
            c1 = get_firestore_client()
            c2 = get_firestore_client()
            assert c1 is c2


class TestGetDb:
    def test_returns_firestore_client(self):
        with patch("fcp.services.firestore.Database"):
            client = get_db()
            assert isinstance(client, FirestoreClient)


class TestGetFirestoreStatus:
    def test_returns_status_dict(self):
        status = get_firestore_status()
        assert status == {"available": True, "error": None, "mode": "sqlite"}


class TestResetFirestoreState:
    def test_is_noop(self):
        # Should not raise
        reset_firestore_state()


class TestResetFirestoreClient:
    def test_clears_cache(self):
        with patch("fcp.services.firestore.Database"):
            c1 = get_firestore_client()
            reset_firestore_client()
            c2 = get_firestore_client()
            assert c1 is not c2


# ---------------------------------------------------------------------------
# Legacy singleton
# ---------------------------------------------------------------------------


class TestGetLegacyClient:
    def test_first_call_creates_singleton(self):
        with patch("fcp.services.firestore.Database"):
            client = _get_legacy_client()
            assert isinstance(client, FirestoreClient)
            assert firestore_mod._firestore_client is client

    def test_second_call_returns_same(self):
        with patch("fcp.services.firestore.Database"):
            c1 = _get_legacy_client()
            c2 = _get_legacy_client()
            assert c1 is c2

    def test_returns_existing_when_already_set(self):
        """When _firestore_client is already set, skip the lock entirely."""
        sentinel = MagicMock(spec=FirestoreClient)
        firestore_mod._firestore_client = sentinel
        result = _get_legacy_client()
        assert result is sentinel

    def test_double_check_locking_race(self):
        """Simulate another thread setting _firestore_client between the outer
        and inner None checks (the 221->223 branch)."""
        sentinel = MagicMock(spec=FirestoreClient)
        original_lock = firestore_mod._firestore_lock

        class _RaceLock:
            """A context manager that simulates a concurrent init."""

            def __enter__(self):
                original_lock.acquire()
                # Another thread "wins" and sets the client before inner check
                firestore_mod._firestore_client = sentinel
                return self

            def __exit__(self, *args):
                original_lock.release()

        firestore_mod._firestore_lock = _RaceLock()  # type: ignore[assignment]
        try:
            result = _get_legacy_client()
            # Should return the sentinel set by the "other thread"
            assert result is sentinel
        finally:
            firestore_mod._firestore_lock = original_lock


# ---------------------------------------------------------------------------
# _FirestoreClientProxy
# ---------------------------------------------------------------------------


class TestFirestoreClientProxy:
    def test_getattr_delegates_to_legacy_client(self):
        mock_client = MagicMock()
        mock_client.some_attr = "hello"
        firestore_mod._firestore_client = mock_client
        # Also need to make get_firestore_client return our mock
        with patch.object(firestore_mod, "get_firestore_client", return_value=mock_client):
            proxy = _FirestoreClientProxy()
            assert proxy.some_attr == "hello"

    def test_repr_when_not_initialized(self):
        firestore_mod._firestore_client = None
        proxy = _FirestoreClientProxy()
        assert repr(proxy) == "<FirestoreClientProxy initialized=False>"

    def test_repr_when_initialized(self):
        firestore_mod._firestore_client = MagicMock()
        proxy = _FirestoreClientProxy()
        assert repr(proxy) == "<FirestoreClientProxy initialized=True>"
