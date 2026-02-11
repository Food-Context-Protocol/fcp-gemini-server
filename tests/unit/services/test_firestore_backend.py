"""Tests for Firestore backend implementation."""

import importlib
import sys
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fcp.services.firestore_backend import FirestoreBackend


class MockDocument:
    """Mock Firestore document."""

    def __init__(self, doc_id: str, data: dict, exists: bool = True):
        self.id = doc_id
        self._data = data
        self.exists = exists

    def to_dict(self):
        return self._data


class MockAsyncCollection:
    """Mock async Firestore collection with async streaming."""

    def __init__(self, docs: dict[str, MockDocument]):
        self._docs = docs

    def document(self, doc_id: str):
        mock_doc_ref = AsyncMock()
        doc = self._docs.get(doc_id, MockDocument(doc_id, {}, exists=False))

        async def async_get():
            return doc

        async def async_set(data, merge=False):
            if merge:
                self._docs[doc_id] = MockDocument(doc_id, {**doc.to_dict(), **data}, exists=True)
            else:
                self._docs[doc_id] = MockDocument(doc_id, data, exists=True)

        async def async_update(data):
            if doc_id in self._docs:
                existing_data = self._docs[doc_id].to_dict()
                self._docs[doc_id] = MockDocument(doc_id, {**existing_data, **data}, exists=True)

        async def async_delete():
            if doc_id in self._docs:
                del self._docs[doc_id]

        mock_doc_ref.get = async_get
        mock_doc_ref.set = async_set
        mock_doc_ref.update = async_update
        mock_doc_ref.delete = async_delete

        return mock_doc_ref

    def where(self, field, op, value):
        query = MockQuery(list(self._docs.values()))
        return query.where(field, op, value)

    def order_by(self, field, direction=None):
        query = MockQuery(list(self._docs.values()))
        return query.order_by(field, direction)

    def limit(self, count):
        query = MockQuery(list(self._docs.values()))
        return query.limit(count)


class MockQuery:
    """Mock Firestore query."""

    def __init__(self, docs: list[MockDocument]):
        self._docs = docs
        self._filters = []
        self._order = None
        self._limit_val = None
        self._offset_val = 0

    def where(self, field, op, value):
        self._filters.append((field, op, value))
        return self

    def order_by(self, field, direction=None):
        self._order = (field, direction)
        return self

    def limit(self, count):
        self._limit_val = count
        return self

    def offset(self, count):
        self._offset_val = count
        return self

    async def stream(self):
        """Async generator that yields documents."""
        filtered_docs = self._docs[:]

        # Apply filters
        for field, op, value in self._filters:
            new_filtered = []
            for doc in filtered_docs:
                if not doc.exists:
                    continue
                data = doc.to_dict()
                field_value = data.get(field)

                match = False
                if op == "==":
                    match = field_value == value
                elif op == ">=":
                    match = field_value is not None and field_value >= value
                elif op == "<=":
                    match = field_value is not None and field_value <= value

                if match:
                    new_filtered.append(doc)
            filtered_docs = new_filtered

        # Apply offset
        if self._offset_val:
            filtered_docs = filtered_docs[self._offset_val :]

        # Apply limit
        if self._limit_val:
            filtered_docs = filtered_docs[: self._limit_val]

        for doc in filtered_docs:
            yield doc

    def get(self):
        """Return first document (for aggregations)."""
        mock_result = MagicMock()
        mock_result.count = len(self._docs)
        return mock_result


class MockFirestoreClient:
    """Mock Firestore AsyncClient."""

    def __init__(self):
        self._collections = {}

    def collection(self, name: str):
        if name not in self._collections:
            self._collections[name] = MockAsyncCollection({})
        return self._collections[name]

    def close(self):
        pass


@pytest.fixture
def mock_firestore_client():
    """Provide a mock Firestore client for testing."""
    return MockFirestoreClient()


# ============================================================================
# Init and Connection Tests
# ============================================================================


@pytest.mark.asyncio
async def test_init_with_project_id():
    """FirestoreBackend should accept a project_id parameter."""
    backend = FirestoreBackend(project_id="test-project")
    assert backend._project_id == "test-project"


@pytest.mark.asyncio
async def test_init_with_injected_client(mock_firestore_client):
    """FirestoreBackend should accept an injected client for testing."""
    backend = FirestoreBackend(client=mock_firestore_client)
    assert backend._client is mock_firestore_client


@pytest.mark.asyncio
async def test_connect_with_injected_client(mock_firestore_client):
    """Connect should use the injected client if provided."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()
    assert backend._db is mock_firestore_client


@pytest.mark.asyncio
async def test_connect_without_firestore_installed():
    """Connect should raise RuntimeError if google-cloud-firestore not installed."""
    with patch("fcp.services.firestore_backend.FIRESTORE_AVAILABLE", False):
        backend = FirestoreBackend(project_id="test-project")
        with pytest.raises(RuntimeError, match="google-cloud-firestore not installed"):
            await backend.connect()


@pytest.mark.asyncio
async def test_connect_creates_async_client(mock_firestore_client):
    """Connect should create an AsyncClient when no client injected."""
    with (
        patch("fcp.services.firestore_backend.FIRESTORE_AVAILABLE", True),
        patch("fcp.services.firestore_backend.firestore") as mock_fs,
    ):
        mock_fs.AsyncClient.return_value = mock_firestore_client

        backend = FirestoreBackend(project_id="test-project")
        await backend.connect()

        mock_fs.AsyncClient.assert_called_once_with(project="test-project")
        assert backend._db is mock_firestore_client


@pytest.mark.asyncio
async def test_close(mock_firestore_client):
    """Close should clear client and db references."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    await backend.close()

    assert backend._client is None
    assert backend._db is None


@pytest.mark.asyncio
async def test_db_property_when_connected(mock_firestore_client):
    """db property should return the client when connected."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()
    assert backend.db is mock_firestore_client


@pytest.mark.asyncio
async def test_db_property_when_not_connected():
    """db property should raise RuntimeError when not connected."""
    backend = FirestoreBackend()
    with pytest.raises(RuntimeError, match="Firestore not connected"):
        _ = backend.db


@pytest.mark.asyncio
async def test_ensure_connected_auto_connects(mock_firestore_client):
    """_ensure_connected should auto-connect if not yet connected."""
    backend = FirestoreBackend(client=mock_firestore_client)
    assert backend._db is None

    await backend._ensure_connected()

    assert backend._db is not None


# ============================================================================
# Food Logs Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_logs_empty(mock_firestore_client):
    """get_user_logs should return empty list when no logs exist."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    logs = await backend.get_user_logs("user1")

    assert logs == []


@pytest.mark.asyncio
async def test_get_user_logs_with_data(mock_firestore_client):
    """get_user_logs should return user's logs."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    # Add test data
    collection = backend.db.collection("food_logs")
    collection._docs = {
        "log1": MockDocument(
            "log1",
            {
                "user_id": "user1",
                "dish_name": "Pizza",
                "deleted": False,
                "created_at": "2026-01-01T00:00:00Z",
            },
        ),
        "log2": MockDocument(
            "log2",
            {
                "user_id": "user2",
                "dish_name": "Burger",
                "deleted": False,
                "created_at": "2026-01-01T00:00:00Z",
            },
        ),
    }

    logs = await backend.get_user_logs("user1")

    assert len(logs) == 1
    assert logs[0]["id"] == "log1"
    assert logs[0]["dish_name"] == "Pizza"


@pytest.mark.asyncio
async def test_get_log_found(mock_firestore_client):
    """get_log should return log if found and user matches."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    # Add test data
    collection = backend.db.collection("food_logs")
    collection._docs["log1"] = MockDocument("log1", {"user_id": "user1", "dish_name": "Pizza"})

    log = await backend.get_log("user1", "log1")

    assert log is not None
    assert log["id"] == "log1"
    assert log["dish_name"] == "Pizza"


@pytest.mark.asyncio
async def test_get_log_not_found(mock_firestore_client):
    """get_log should return None if log doesn't exist."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    log = await backend.get_log("user1", "nonexistent")

    assert log is None


@pytest.mark.asyncio
async def test_get_log_wrong_user(mock_firestore_client):
    """get_log should return None if log belongs to different user."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("food_logs")
    collection._docs["log1"] = MockDocument("log1", {"user_id": "user1", "dish_name": "Pizza"})

    log = await backend.get_log("user2", "log1")

    assert log is None


@pytest.mark.asyncio
async def test_get_user_logs_with_start_date(mock_firestore_client):
    """get_user_logs should filter by start_date when provided."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    # Add test data with different dates
    collection = backend.db.collection("food_logs")
    collection._docs = {
        "log1": MockDocument(
            "log1",
            {
                "user_id": "user1",
                "dish_name": "Old Pizza",
                "deleted": False,
                "created_at": "2026-01-01T00:00:00Z",
            },
        ),
        "log2": MockDocument(
            "log2",
            {
                "user_id": "user1",
                "dish_name": "Recent Burger",
                "deleted": False,
                "created_at": "2026-02-01T00:00:00Z",
            },
        ),
    }

    start_date = datetime(2026, 1, 15, tzinfo=UTC)
    logs = await backend.get_user_logs("user1", start_date=start_date)

    # Should only return logs after start_date
    assert len(logs) == 1
    assert logs[0]["dish_name"] == "Recent Burger"


@pytest.mark.asyncio
async def test_get_user_logs_with_end_date(mock_firestore_client):
    """get_user_logs should filter by end_date when provided."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    # Add test data with different dates
    collection = backend.db.collection("food_logs")
    collection._docs = {
        "log1": MockDocument(
            "log1",
            {
                "user_id": "user1",
                "dish_name": "Old Pizza",
                "deleted": False,
                "created_at": "2026-01-01T00:00:00Z",
            },
        ),
        "log2": MockDocument(
            "log2",
            {
                "user_id": "user1",
                "dish_name": "Recent Burger",
                "deleted": False,
                "created_at": "2026-02-01T00:00:00Z",
            },
        ),
    }

    end_date = datetime(2026, 1, 15, tzinfo=UTC)
    logs = await backend.get_user_logs("user1", end_date=end_date)

    # Should only return logs before end_date
    assert len(logs) == 1
    assert logs[0]["dish_name"] == "Old Pizza"


@pytest.mark.asyncio
async def test_get_logs_by_ids_empty(mock_firestore_client):
    """get_logs_by_ids should return empty list for empty input."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    logs = await backend.get_logs_by_ids("user1", [])

    assert logs == []


@pytest.mark.asyncio
async def test_get_logs_by_ids_filters_by_user(mock_firestore_client):
    """get_logs_by_ids should iterate and filter by user_id."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    # Add test data for multiple users
    collection = backend.db.collection("food_logs")
    collection._docs = {
        "log1": MockDocument("log1", {"user_id": "user1", "dish_name": "Pizza"}),
        "log2": MockDocument("log2", {"user_id": "user2", "dish_name": "Burger"}),
        "log3": MockDocument("log3", {"user_id": "user1", "dish_name": "Pasta"}),
    }

    # Request all three log IDs but only as user1
    logs = await backend.get_logs_by_ids("user1", ["log1", "log2", "log3"])

    # Should only return logs belonging to user1
    assert len(logs) == 2
    assert logs[0]["dish_name"] == "Pizza"
    assert logs[1]["dish_name"] == "Pasta"


@pytest.mark.asyncio
async def test_create_log(mock_firestore_client):
    """create_log should create a new log and return its ID."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    log_id = await backend.create_log("user1", {"dish_name": "Ramen"})

    assert log_id is not None
    assert len(log_id) > 0


@pytest.mark.asyncio
async def test_update_log_success(mock_firestore_client):
    """update_log should update existing log."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    # Create a log first
    collection = backend.db.collection("food_logs")
    collection._docs["log1"] = MockDocument("log1", {"user_id": "user1", "dish_name": "Pizza"})

    result = await backend.update_log("user1", "log1", {"dish_name": "Pasta"})

    assert result is True


@pytest.mark.asyncio
async def test_update_log_not_found(mock_firestore_client):
    """update_log should return False if log doesn't exist."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    result = await backend.update_log("user1", "nonexistent", {"dish_name": "Pasta"})

    assert result is False


@pytest.mark.asyncio
async def test_delete_log_success(mock_firestore_client):
    """delete_log should delete existing log."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("food_logs")
    collection._docs["log1"] = MockDocument("log1", {"user_id": "user1", "dish_name": "Pizza"})

    result = await backend.delete_log("user1", "log1")

    assert result is True


@pytest.mark.asyncio
async def test_delete_log_not_found(mock_firestore_client):
    """delete_log should return False if log doesn't exist."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    result = await backend.delete_log("user1", "nonexistent")

    assert result is False


@pytest.mark.asyncio
async def test_count_user_logs(mock_firestore_client):
    """count_user_logs should count user's non-deleted logs."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("food_logs")
    collection._docs = {
        "log1": MockDocument(
            "log1",
            {"user_id": "user1", "deleted": False},
        ),
        "log2": MockDocument(
            "log2",
            {"user_id": "user1", "deleted": False},
        ),
        "log3": MockDocument(
            "log3",
            {"user_id": "user2", "deleted": False},
        ),
    }

    count = await backend.count_user_logs("user1")

    assert count == 2


# ============================================================================
# Pantry Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_pantry_empty(mock_firestore_client):
    """get_pantry should return empty list when no items exist."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    items = await backend.get_pantry("user1")

    assert items == []


@pytest.mark.asyncio
async def test_update_pantry_item(mock_firestore_client):
    """update_pantry_item should update or create pantry item."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    item_id = await backend.update_pantry_item("user1", {"name": "Milk", "quantity": 2})

    assert item_id is not None


@pytest.mark.asyncio
async def test_update_pantry_item_missing_name(mock_firestore_client):
    """update_pantry_item should raise ValueError if name is missing."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    with pytest.raises(ValueError, match="Item name is required"):
        await backend.update_pantry_item("user1", {"quantity": 2})


@pytest.mark.asyncio
async def test_add_pantry_item(mock_firestore_client):
    """add_pantry_item should create a new pantry item."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    item_id = await backend.add_pantry_item("user1", {"name": "Eggs"})

    assert item_id is not None
    assert len(item_id) > 0


@pytest.mark.asyncio
async def test_delete_pantry_item_success(mock_firestore_client):
    """delete_pantry_item should delete existing item."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("pantry")
    collection._docs["item1"] = MockDocument("item1", {"user_id": "user1", "name": "Milk"})

    result = await backend.delete_pantry_item("user1", "item1")

    assert result is True


@pytest.mark.asyncio
async def test_delete_pantry_item_not_found(mock_firestore_client):
    """delete_pantry_item should return False if item doesn't exist."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    result = await backend.delete_pantry_item("user1", "nonexistent")

    assert result is False


# ============================================================================
# Recipe Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_recipes_empty(mock_firestore_client):
    """get_recipes should return empty list when no recipes exist."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    recipes = await backend.get_recipes("user1")

    assert recipes == []


@pytest.mark.asyncio
async def test_create_recipe(mock_firestore_client):
    """create_recipe should create a new recipe."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    recipe_id = await backend.create_recipe("user1", {"name": "Pasta", "steps": []})

    assert recipe_id is not None
    assert len(recipe_id) > 0


@pytest.mark.asyncio
async def test_update_recipe_success(mock_firestore_client):
    """update_recipe should update existing recipe."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("recipes")
    collection._docs["recipe1"] = MockDocument("recipe1", {"user_id": "user1", "name": "Pasta"})

    result = await backend.update_recipe("user1", "recipe1", {"name": "Better Pasta"})

    assert result is True


@pytest.mark.asyncio
async def test_delete_recipe_success(mock_firestore_client):
    """delete_recipe should delete existing recipe."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("recipes")
    collection._docs["recipe1"] = MockDocument("recipe1", {"user_id": "user1", "name": "Pasta"})

    result = await backend.delete_recipe("user1", "recipe1")

    assert result is True


# ============================================================================
# Receipt Tests
# ============================================================================


@pytest.mark.asyncio
async def test_save_receipt(mock_firestore_client):
    """save_receipt should save receipt data."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    receipt_id = await backend.save_receipt("user1", {"items": ["milk", "bread"]})

    assert receipt_id is not None
    assert len(receipt_id) > 0


# ============================================================================
# User Preferences Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_preferences_no_user(mock_firestore_client):
    """get_user_preferences should return defaults for non-existent user."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    prefs = await backend.get_user_preferences("user1")

    assert prefs["timezone"] == "UTC"
    assert prefs["daily_insights_enabled"] is True


@pytest.mark.asyncio
async def test_update_user_preferences(mock_firestore_client):
    """update_user_preferences should save preferences."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    await backend.update_user_preferences("user1", {"timezone": "America/New_York"})

    # Should not raise an error
    assert True


@pytest.mark.asyncio
async def test_get_user_stats_no_logs(mock_firestore_client):
    """get_user_stats should return zeros when no logs exist."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    stats = await backend.get_user_stats("user1")

    assert stats["total_logs"] == 0
    assert stats["current_streak"] == 0


# ============================================================================
# Notification Tests
# ============================================================================


@pytest.mark.asyncio
async def test_store_notification(mock_firestore_client):
    """store_notification should save a notification."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    nid = await backend.store_notification("user1", "daily_insight", {"message": "Test"})

    assert nid is not None
    assert len(nid) > 0


@pytest.mark.asyncio
async def test_mark_notification_read_success(mock_firestore_client):
    """mark_notification_read should mark notification as read."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("notifications")
    collection._docs["notif1"] = MockDocument(
        "notif1",
        {"user_id": "user1", "type": "daily_insight", "read": False},
    )

    result = await backend.mark_notification_read("user1", "notif1")

    assert result is True


# ============================================================================
# Draft Tests
# ============================================================================


@pytest.mark.asyncio
async def test_save_draft(mock_firestore_client):
    """save_draft should create a new draft."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    draft_id = await backend.save_draft("user1", {"content": "Test draft"})

    assert draft_id is not None
    assert len(draft_id) > 0


@pytest.mark.asyncio
async def test_get_draft_found(mock_firestore_client):
    """get_draft should return draft if found."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("drafts")
    collection._docs["draft1"] = MockDocument("draft1", {"user_id": "user1", "content": "Test"})

    draft = await backend.get_draft("user1", "draft1")

    assert draft is not None
    assert draft["content"] == "Test"


@pytest.mark.asyncio
async def test_delete_draft_success(mock_firestore_client):
    """delete_draft should delete existing draft."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("drafts")
    collection._docs["draft1"] = MockDocument("draft1", {"user_id": "user1", "content": "Test"})

    result = await backend.delete_draft("user1", "draft1")

    assert result is True


# ============================================================================
# Published Content Tests
# ============================================================================


@pytest.mark.asyncio
async def test_save_published_content(mock_firestore_client):
    """save_published_content should save published content."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    content_id = await backend.save_published_content("user1", {"title": "Test Post"})

    assert content_id is not None
    assert len(content_id) > 0


@pytest.mark.asyncio
async def test_publish_draft_not_found(mock_firestore_client):
    """publish_draft should return empty string if draft doesn't exist."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    content_id, success = await backend.publish_draft("user1", "nonexistent", {"title": "Test"})

    assert content_id == ""
    assert success is False


@pytest.mark.asyncio
async def test_publish_draft_already_published(mock_firestore_client):
    """publish_draft should return False if draft already published."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("drafts")
    collection._docs["draft1"] = MockDocument(
        "draft1",
        {"user_id": "user1", "content": "Test", "status": "published"},
    )

    content_id, success = await backend.publish_draft("user1", "draft1", {"title": "Test"})

    assert content_id == ""
    assert success is False


# ============================================================================
# Additional Coverage Tests for Remaining Methods
# ============================================================================


@pytest.mark.asyncio
async def test_get_all_user_logs(mock_firestore_client):
    """get_all_user_logs should return all user logs without limit."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("food_logs")
    collection._docs = {
        "log1": MockDocument(
            "log1",
            {"user_id": "user1", "dish_name": "Pizza", "deleted": False, "created_at": "2026-01-01T00:00:00Z"},
        ),
        "log2": MockDocument(
            "log2",
            {"user_id": "user1", "dish_name": "Burger", "deleted": False, "created_at": "2026-01-02T00:00:00Z"},
        ),
    }

    logs = await backend.get_all_user_logs("user1")

    assert len(logs) == 2


@pytest.mark.asyncio
async def test_get_all_user_logs_with_limit(mock_firestore_client):
    """get_all_user_logs should respect limit parameter."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("food_logs")
    collection._docs = {
        "log1": MockDocument(
            "log1",
            {"user_id": "user1", "dish_name": "Pizza", "deleted": False, "created_at": "2026-01-01T00:00:00Z"},
        ),
        "log2": MockDocument(
            "log2",
            {"user_id": "user1", "dish_name": "Burger", "deleted": False, "created_at": "2026-01-02T00:00:00Z"},
        ),
    }

    logs = await backend.get_all_user_logs("user1", limit=1)

    assert len(logs) == 1


@pytest.mark.asyncio
async def test_get_user_logs_paginated(mock_firestore_client):
    """get_user_logs_paginated should return logs with pagination."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("food_logs")
    collection._docs = {
        "log1": MockDocument(
            "log1",
            {"user_id": "user1", "dish_name": "Pizza", "deleted": False, "created_at": "2026-01-01T00:00:00Z"},
        ),
        "log2": MockDocument(
            "log2",
            {"user_id": "user1", "dish_name": "Burger", "deleted": False, "created_at": "2026-01-02T00:00:00Z"},
        ),
    }

    logs, total = await backend.get_user_logs_paginated("user1", page=1, page_size=10)

    assert len(logs) == 2
    assert total == 2


@pytest.mark.asyncio
async def test_update_pantry_items_batch_empty(mock_firestore_client):
    """update_pantry_items_batch should handle empty list."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    ids = await backend.update_pantry_items_batch("user1", [])

    assert ids == []


@pytest.mark.asyncio
async def test_update_pantry_items_batch_with_items(mock_firestore_client):
    """update_pantry_items_batch should update multiple items."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    items = [{"name": "Milk", "quantity": 2}, {"name": "Eggs", "quantity": 12}]

    ids = await backend.update_pantry_items_batch("user1", items)

    assert len(ids) == 2


@pytest.mark.asyncio
async def test_update_pantry_items_batch_skips_invalid(mock_firestore_client):
    """update_pantry_items_batch should skip items without name."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    items = [{"name": "Milk", "quantity": 2}, {"quantity": 12}]  # Second item has no name

    ids = await backend.update_pantry_items_batch("user1", items)

    assert len(ids) == 1


@pytest.mark.asyncio
async def test_get_recipe(mock_firestore_client):
    """get_recipe should return recipe if found."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("recipes")
    collection._docs["recipe1"] = MockDocument("recipe1", {"user_id": "user1", "name": "Pasta"})

    recipe = await backend.get_recipe("user1", "recipe1")

    assert recipe is not None
    assert recipe["name"] == "Pasta"


@pytest.mark.asyncio
async def test_get_recipe_not_found(mock_firestore_client):
    """get_recipe should return None if recipe doesn't exist."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    recipe = await backend.get_recipe("user1", "nonexistent")

    assert recipe is None


@pytest.mark.asyncio
async def test_get_recipe_wrong_user(mock_firestore_client):
    """get_recipe should return None if recipe belongs to different user."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("recipes")
    collection._docs["recipe1"] = MockDocument("recipe1", {"user_id": "user1", "name": "Pasta"})

    recipe = await backend.get_recipe("user2", "recipe1")

    assert recipe is None


@pytest.mark.asyncio
async def test_get_recipes_with_filters(mock_firestore_client):
    """get_recipes should filter by favorites_only and include_archived."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("recipes")
    collection._docs = {
        "recipe1": MockDocument(
            "recipe1",
            {
                "user_id": "user1",
                "name": "Pasta",
                "is_favorite": True,
                "is_archived": False,
                "created_at": "2026-01-01T00:00:00Z",
            },
        ),
        "recipe2": MockDocument(
            "recipe2",
            {
                "user_id": "user1",
                "name": "Pizza",
                "is_favorite": False,
                "is_archived": False,
                "created_at": "2026-01-02T00:00:00Z",
            },
        ),
        "recipe3": MockDocument(
            "recipe3",
            {
                "user_id": "user1",
                "name": "Salad",
                "is_favorite": True,
                "is_archived": True,
                "created_at": "2026-01-03T00:00:00Z",
            },
        ),
    }

    # Test favorites_only
    favorites = await backend.get_recipes("user1", favorites_only=True)
    assert len(favorites) == 1  # Only recipe1 is favorite and not archived

    # Test include_archived
    all_recipes = await backend.get_recipes("user1", include_archived=True)
    assert len(all_recipes) == 3


@pytest.mark.asyncio
async def test_get_active_users(mock_firestore_client):
    """get_active_users should return users active within the specified days."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("users")
    collection._docs = {
        "user1": MockDocument(
            "user1",
            {
                "email": "user1@test.com",
                "display_name": "User One",
                "last_active": "2026-02-08T00:00:00Z",
            },
        ),
        "user2": MockDocument(
            "user2",
            {
                "email": "user2@test.com",
                "display_name": "User Two",
                "last_active": "2026-01-01T00:00:00Z",
            },
        ),
    }

    users = await backend.get_active_users(days=7)

    # Should return users active in the last 7 days
    assert len(users) == 1
    assert users[0]["email"] == "user1@test.com"


@pytest.mark.asyncio
async def test_invalidate_user_stats(mock_firestore_client):
    """invalidate_user_stats should clear user stats."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    await backend.invalidate_user_stats("user1")

    # Should not raise an error
    assert True


@pytest.mark.asyncio
async def test_get_user_notifications(mock_firestore_client):
    """get_user_notifications should return user notifications."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("notifications")
    collection._docs = {
        "notif1": MockDocument(
            "notif1",
            {
                "user_id": "user1",
                "type": "daily_insight",
                "content": {"message": "Test"},
                "read": False,
                "created_at": "2026-01-01T00:00:00Z",
            },
        ),
        "notif2": MockDocument(
            "notif2",
            {
                "user_id": "user2",
                "type": "weekly_digest",
                "content": {"message": "Test"},
                "read": False,
                "created_at": "2026-01-02T00:00:00Z",
            },
        ),
    }

    notifications = await backend.get_user_notifications("user1")

    assert len(notifications) == 1
    assert notifications[0]["type"] == "daily_insight"


@pytest.mark.asyncio
async def test_get_user_notifications_unread_only(mock_firestore_client):
    """get_user_notifications should filter by unread_only."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("notifications")
    collection._docs = {
        "notif1": MockDocument(
            "notif1",
            {
                "user_id": "user1",
                "type": "daily_insight",
                "content": {"message": "Test"},
                "read": True,
                "created_at": "2026-01-01T00:00:00Z",
            },
        ),
        "notif2": MockDocument(
            "notif2",
            {
                "user_id": "user1",
                "type": "weekly_digest",
                "content": {"message": "Test"},
                "read": False,
                "created_at": "2026-01-02T00:00:00Z",
            },
        ),
    }

    notifications = await backend.get_user_notifications("user1", unread_only=True)

    assert len(notifications) == 1
    assert notifications[0]["read"] is False


@pytest.mark.asyncio
async def test_get_drafts(mock_firestore_client):
    """get_drafts should return user drafts."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("drafts")
    collection._docs = {
        "draft1": MockDocument(
            "draft1",
            {"user_id": "user1", "content": "Test 1", "created_at": "2026-01-01T00:00:00Z"},
        ),
        "draft2": MockDocument(
            "draft2",
            {"user_id": "user2", "content": "Test 2", "created_at": "2026-01-02T00:00:00Z"},
        ),
    }

    drafts = await backend.get_drafts("user1")

    assert len(drafts) == 1
    assert drafts[0]["content"] == "Test 1"


@pytest.mark.asyncio
async def test_update_draft_success(mock_firestore_client):
    """update_draft should update existing draft."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("drafts")
    collection._docs["draft1"] = MockDocument("draft1", {"user_id": "user1", "content": "Test"})

    result = await backend.update_draft("user1", "draft1", {"content": "Updated"})

    assert result is True


@pytest.mark.asyncio
async def test_update_draft_not_found(mock_firestore_client):
    """update_draft should return False if draft doesn't exist."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    result = await backend.update_draft("user1", "nonexistent", {"content": "Updated"})

    assert result is False


@pytest.mark.asyncio
async def test_get_published_content(mock_firestore_client):
    """get_published_content should return user's published content."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("published")
    collection._docs = {
        "pub1": MockDocument(
            "pub1",
            {"user_id": "user1", "title": "Post 1", "published_at": "2026-01-01T00:00:00Z"},
        ),
        "pub2": MockDocument(
            "pub2",
            {"user_id": "user2", "title": "Post 2", "published_at": "2026-01-02T00:00:00Z"},
        ),
    }

    content = await backend.get_published_content("user1")

    assert len(content) == 1
    assert content[0]["title"] == "Post 1"


@pytest.mark.asyncio
async def test_get_published_content_item(mock_firestore_client):
    """get_published_content_item should return specific content item."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("published")
    collection._docs["pub1"] = MockDocument("pub1", {"user_id": "user1", "title": "Post 1"})

    item = await backend.get_published_content_item("user1", "pub1")

    assert item is not None
    assert item["title"] == "Post 1"


@pytest.mark.asyncio
async def test_get_published_content_item_not_found(mock_firestore_client):
    """get_published_content_item should return None if item doesn't exist."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    item = await backend.get_published_content_item("user1", "nonexistent")

    assert item is None


@pytest.mark.asyncio
async def test_get_published_content_item_wrong_user(mock_firestore_client):
    """get_published_content_item should return None if item belongs to different user."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("published")
    collection._docs["pub1"] = MockDocument("pub1", {"user_id": "user1", "title": "Post 1"})

    item = await backend.get_published_content_item("user2", "pub1")

    assert item is None


@pytest.mark.asyncio
async def test_update_published_content(mock_firestore_client):
    """update_published_content should update existing published content."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("published")
    collection._docs["pub1"] = MockDocument("pub1", {"user_id": "user1", "title": "Post 1"})

    await backend.update_published_content("user1", "pub1", {"title": "Updated Post"})

    # Should not raise an error
    assert True


@pytest.mark.asyncio
async def test_mark_notification_read_not_found(mock_firestore_client):
    """mark_notification_read should return False if notification doesn't exist."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    result = await backend.mark_notification_read("user1", "nonexistent")

    assert result is False


@pytest.mark.asyncio
async def test_mark_notification_read_wrong_user(mock_firestore_client):
    """mark_notification_read should return False if notification belongs to different user."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("notifications")
    collection._docs["notif1"] = MockDocument(
        "notif1",
        {"user_id": "user1", "type": "daily_insight", "read": False},
    )

    result = await backend.mark_notification_read("user2", "notif1")

    assert result is False


@pytest.mark.asyncio
async def test_delete_pantry_item_wrong_user(mock_firestore_client):
    """delete_pantry_item should return False if item belongs to different user."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("pantry")
    collection._docs["item1"] = MockDocument("item1", {"user_id": "user1", "name": "Milk"})

    result = await backend.delete_pantry_item("user2", "item1")

    assert result is False


@pytest.mark.asyncio
async def test_get_draft_not_found(mock_firestore_client):
    """get_draft should return None if draft doesn't exist."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    draft = await backend.get_draft("user1", "nonexistent")

    assert draft is None


@pytest.mark.asyncio
async def test_get_draft_wrong_user(mock_firestore_client):
    """get_draft should return None if draft belongs to different user."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("drafts")
    collection._docs["draft1"] = MockDocument("draft1", {"user_id": "user1", "content": "Test"})

    draft = await backend.get_draft("user2", "draft1")

    assert draft is None


@pytest.mark.asyncio
async def test_update_recipe_not_found(mock_firestore_client):
    """update_recipe should return False if recipe doesn't exist."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    result = await backend.update_recipe("user1", "nonexistent", {"name": "Updated"})

    assert result is False


@pytest.mark.asyncio
async def test_delete_recipe_not_found(mock_firestore_client):
    """delete_recipe should return False if recipe doesn't exist."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    result = await backend.delete_recipe("user1", "nonexistent")

    assert result is False


@pytest.mark.asyncio
async def test_publish_draft_success(mock_firestore_client):
    """publish_draft should publish draft and create published content."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("drafts")
    collection._docs["draft1"] = MockDocument("draft1", {"user_id": "user1", "content": "Test"})

    content_id, success = await backend.publish_draft("user1", "draft1", {"title": "Test Post"})

    assert content_id != ""
    assert success is True


@pytest.mark.asyncio
async def test_get_user_preferences_with_existing_user(mock_firestore_client):
    """get_user_preferences should return user preferences when user exists."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("users")
    collection._docs["user1"] = MockDocument(
        "user1",
        {
            "email": "user1@test.com",
            "display_name": "User One",
            "preferences": {"timezone": "America/New_York", "daily_insights_enabled": False},
        },
    )

    prefs = await backend.get_user_preferences("user1")

    assert prefs["timezone"] == "America/New_York"
    assert prefs["daily_insights_enabled"] is False
    assert prefs["email"] == "user1@test.com"


@pytest.mark.asyncio
async def test_get_user_stats_with_cached_stats(mock_firestore_client):
    """get_user_stats should return cached stats if available and fresh."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    cached_stats = {
        "current_streak": 5,
        "longest_streak": 10,
        "total_logs": 50,
        "cuisines_tried": 15,
        "first_log_date": "2026-01-01",
        "last_log_date": datetime.now(UTC).date().isoformat(),
    }

    collection = backend.db.collection("users")
    collection._docs["user1"] = MockDocument("user1", {"stats": cached_stats})

    stats = await backend.get_user_stats("user1")

    assert stats["current_streak"] == 5
    assert stats["total_logs"] == 50


@pytest.mark.asyncio
async def test_get_user_stats_with_stale_streak(mock_firestore_client):
    """get_user_stats should reset streak if last log is too old."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    # Last log was 3 days ago, so streak should be reset to 0
    old_date = (datetime.now(UTC).date() - timedelta(days=3)).isoformat()
    cached_stats = {
        "current_streak": 5,
        "longest_streak": 10,
        "total_logs": 50,
        "cuisines_tried": 15,
        "first_log_date": "2026-01-01",
        "last_log_date": old_date,
    }

    collection = backend.db.collection("users")
    collection._docs["user1"] = MockDocument("user1", {"stats": cached_stats})

    stats = await backend.get_user_stats("user1")

    assert stats["current_streak"] == 0  # Streak reset due to gap


@pytest.mark.asyncio
async def test_get_user_stats_calculates_from_scratch(mock_firestore_client):
    """get_user_stats should calculate stats from logs when no cache exists."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    # Use dates relative to today so the streak is always current
    now = datetime.now(UTC)
    day0 = (now - timedelta(days=2)).strftime("%Y-%m-%dT10:00:00+00:00")
    day1 = (now - timedelta(days=1)).strftime("%Y-%m-%dT10:00:00+00:00")
    day2 = now.strftime("%Y-%m-%dT10:00:00+00:00")

    food_logs_collection = backend.db.collection("food_logs")
    food_logs_collection._docs = {
        "log1": MockDocument(
            "log1",
            {
                "user_id": "user1",
                "deleted": False,
                "created_at": day0,
                "cuisine": "Italian",
            },
        ),
        "log2": MockDocument(
            "log2",
            {
                "user_id": "user1",
                "deleted": False,
                "created_at": day1,
                "cuisine": "Chinese",
            },
        ),
        "log3": MockDocument(
            "log3",
            {
                "user_id": "user1",
                "deleted": False,
                "created_at": day2,
                "cuisine": "Mexican",
            },
        ),
    }

    stats = await backend.get_user_stats("user1")

    assert stats["total_logs"] == 3
    assert stats["cuisines_tried"] == 3
    assert stats["current_streak"] >= 1  # Should have at least 1 day streak


@pytest.mark.asyncio
async def test_get_user_stats_with_cuisine_tracking(mock_firestore_client):
    """get_user_stats should track unique cuisines tried."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    # Use dates relative to today so stats calculation stays valid
    now = datetime.now(UTC)
    day0 = (now - timedelta(days=2)).strftime("%Y-%m-%dT10:00:00+00:00")
    day1 = (now - timedelta(days=1)).strftime("%Y-%m-%dT10:00:00+00:00")
    day2 = now.strftime("%Y-%m-%dT10:00:00+00:00")

    food_logs_collection = backend.db.collection("food_logs")
    food_logs_collection._docs = {
        "log1": MockDocument(
            "log1",
            {
                "user_id": "user1",
                "deleted": False,
                "created_at": day0,
                "cuisine": "Italian",
            },
        ),
        "log2": MockDocument(
            "log2",
            {
                "user_id": "user1",
                "deleted": False,
                "created_at": day1,
                "cuisine": "Italian",  # Duplicate cuisine
            },
        ),
        "log3": MockDocument(
            "log3",
            {
                "user_id": "user1",
                "deleted": False,
                "created_at": day2,
                "cuisine": "Chinese",
            },
        ),
    }

    stats = await backend.get_user_stats("user1")

    # Should count unique cuisines (Italian and Chinese = 2)
    assert stats["cuisines_tried"] == 2


@pytest.mark.asyncio
async def test_get_user_stats_calculates_longest_streak(mock_firestore_client):
    """get_user_stats should calculate longest streak correctly."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    # Create logs with a streak: Jan 1-3, gap, then Jan 5-7
    food_logs_collection = backend.db.collection("food_logs")
    food_logs_collection._docs = {
        "log1": MockDocument(
            "log1",
            {
                "user_id": "user1",
                "deleted": False,
                "created_at": "2026-01-01T10:00:00+00:00",
            },
        ),
        "log2": MockDocument(
            "log2",
            {
                "user_id": "user1",
                "deleted": False,
                "created_at": "2026-01-02T10:00:00+00:00",
            },
        ),
        "log3": MockDocument(
            "log3",
            {
                "user_id": "user1",
                "deleted": False,
                "created_at": "2026-01-03T10:00:00+00:00",
            },
        ),
        # Gap on Jan 4
        "log4": MockDocument(
            "log4",
            {
                "user_id": "user1",
                "deleted": False,
                "created_at": "2026-01-05T10:00:00+00:00",
            },
        ),
        "log5": MockDocument(
            "log5",
            {
                "user_id": "user1",
                "deleted": False,
                "created_at": "2026-01-06T10:00:00+00:00",
            },
        ),
        "log6": MockDocument(
            "log6",
            {
                "user_id": "user1",
                "deleted": False,
                "created_at": "2026-01-07T10:00:00+00:00",
            },
        ),
    }

    stats = await backend.get_user_stats("user1")

    assert stats["longest_streak"] == 3  # Longest consecutive streak is 3 days


# ============================================================================
# Edge Case Tests for get_user_stats and delete_draft
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_stats_invalid_cached_date(mock_firestore_client):
    """Cached stats with malformed last_log_date should not crash."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    cached_stats = {
        "current_streak": 5,
        "longest_streak": 10,
        "total_logs": 50,
        "cuisines_tried": 15,
        "first_log_date": "2026-01-01",
        "last_log_date": "not-a-date",
    }

    collection = backend.db.collection("users")
    collection._docs["user1"] = MockDocument("user1", {"stats": cached_stats})

    stats = await backend.get_user_stats("user1")

    # ValueError is silently caught, streak is NOT reset
    assert stats["current_streak"] == 5
    assert stats["total_logs"] == 50


@pytest.mark.asyncio
async def test_get_user_stats_invalid_log_dates(mock_firestore_client):
    """Logs with malformed created_at should be skipped in streak calc (lines 523-524).

    A valid-date log is included so the first/last query (line 552) does not
    crash (fromisoformat is called without try/except there).  The invalid-date
    logs exercise the ValueError catch on lines 523-524, and since they add
    nothing to log_dates the longest_streak still comes from the single valid
    date (= 1).
    """
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    food_logs_collection = backend.db.collection("food_logs")
    # The valid-date log must come first in iteration order so that the
    # first_query / last_query (which use .limit(1)) pick it up instead
    # of an invalid-date log -- the first/last path calls fromisoformat
    # without try/except.
    food_logs_collection._docs = {
        "log3": MockDocument(
            "log3",
            {
                "user_id": "user1",
                "deleted": False,
                "created_at": "2026-01-15T10:00:00+00:00",
            },
        ),
        "log1": MockDocument(
            "log1",
            {
                "user_id": "user1",
                "deleted": False,
                "created_at": "invalid-date-1",
            },
        ),
        "log2": MockDocument(
            "log2",
            {
                "user_id": "user1",
                "deleted": False,
                "created_at": "not-a-real-date",
            },
        ),
    }

    stats = await backend.get_user_stats("user1")

    # All 3 docs are counted by count_user_logs
    assert stats["total_logs"] == 3
    # Only 1 valid date parsed -> longest_streak = 1
    assert stats["longest_streak"] >= 1
    # first/last dates come from the valid log
    assert stats["first_log_date"] is not None


@pytest.mark.asyncio
async def test_get_user_stats_missing_created_at(mock_firestore_client):
    """First/last log docs without created_at field yield None dates (lines 551-553, 558-560).

    When created_at is missing, the walrus operator evaluates to falsy, so
    first_date and last_date remain None.  The streak query also filters
    by created_at >= window, so docs without created_at are excluded from
    the streak loop -- meaning log_dates is empty and longest_streak = 0
    (line 585).
    """
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    # Logs exist but have no created_at field at all
    food_logs_collection = backend.db.collection("food_logs")
    food_logs_collection._docs = {
        "log1": MockDocument(
            "log1",
            {
                "user_id": "user1",
                "deleted": False,
                "cuisine": "Italian",
            },
        ),
    }

    stats = await backend.get_user_stats("user1")

    assert stats["total_logs"] == 1
    assert stats["first_log_date"] is None
    assert stats["last_log_date"] is None
    # Doc doesn't pass the streak query's created_at >= window filter,
    # so cuisine is not tracked in the streak loop
    assert stats["cuisines_tried"] == 0
    # Empty log_dates -> line 585: longest_streak = 0
    assert stats["longest_streak"] == 0


@pytest.mark.asyncio
async def test_delete_draft_not_found(mock_firestore_client):
    """delete_draft returns False when draft doesn't exist."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    result = await backend.delete_draft("user1", "nonexistent-draft-id")

    assert result is False


@pytest.mark.asyncio
async def test_get_user_logs_with_days_filter(mock_firestore_client):
    """get_user_logs should filter by days parameter."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    # Add logs with different dates
    collection = backend.db.collection("food_logs")
    collection._docs = {
        "log1": MockDocument(
            "log1",
            {
                "user_id": "user1",
                "dish_name": "Old Pizza",
                "deleted": False,
                "created_at": "2026-01-01T00:00:00Z",
            },
        ),
        "log2": MockDocument(
            "log2",
            {
                "user_id": "user1",
                "dish_name": "Recent Burger",
                "deleted": False,
                "created_at": datetime.now(UTC).isoformat(),
            },
        ),
    }

    # Get logs from last 7 days
    logs = await backend.get_user_logs("user1", days=7)

    # Should only return recent logs (within 7 days)
    assert len(logs) == 1
    assert logs[0]["dish_name"] == "Recent Burger"


# ============================================================================
# Coverage Gap Tests
# ============================================================================


def test_firestore_unavailable_flag():
    """FIRESTORE_AVAILABLE is False when google.cloud is missing (lines 20-22)."""
    import fcp.services.firestore_backend as fb_mod

    with patch.dict(sys.modules, {"google.cloud": None, "google.cloud.firestore": None}):
        importlib.reload(fb_mod)
        assert fb_mod.FIRESTORE_AVAILABLE is False
    # Restore the module to its original state
    importlib.reload(fb_mod)


@pytest.mark.asyncio
async def test_close_when_not_connected(mock_firestore_client):
    """close() when _client is None is a no-op (branch 51->exit)."""
    backend = FirestoreBackend(client=mock_firestore_client)
    backend._client = None
    await backend.close()  # Should not raise
    assert backend._client is None


@pytest.mark.asyncio
async def test_get_pantry_with_items(mock_firestore_client):
    """get_pantry should iterate over pantry docs (lines 241-243)."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("pantry")
    collection._docs = {
        "item1": MockDocument(
            "item1",
            {"user_id": "user1", "name": "Milk", "quantity": 2},
        ),
        "item2": MockDocument(
            "item2",
            {"user_id": "user1", "name": "Eggs", "quantity": 12},
        ),
        "item3": MockDocument(
            "item3",
            {"user_id": "user2", "name": "Bread", "quantity": 1},
        ),
    }

    items = await backend.get_pantry("user1")

    assert len(items) == 2
    names = {item["name"] for item in items}
    assert names == {"Milk", "Eggs"}
    # Each item should have its doc id injected
    assert all("id" in item for item in items)


@pytest.mark.asyncio
async def test_get_user_stats_with_empty_stats(mock_firestore_client):
    """User doc exists but stats field is empty dict (branch 475->488)."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    # User doc has stats as an empty dict (falsy)
    collection = backend.db.collection("users")
    collection._docs["user1"] = MockDocument("user1", {"stats": {}})

    # No food logs -> should calculate from scratch and return zeros
    stats = await backend.get_user_stats("user1")

    assert stats["total_logs"] == 0
    assert stats["current_streak"] == 0


@pytest.mark.asyncio
async def test_get_user_stats_with_none_stats(mock_firestore_client):
    """User doc exists but stats field is None (branch 475->488)."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    collection = backend.db.collection("users")
    collection._docs["user1"] = MockDocument("user1", {"stats": None})

    stats = await backend.get_user_stats("user1")

    assert stats["total_logs"] == 0
    assert stats["current_streak"] == 0


@pytest.mark.asyncio
async def test_get_user_stats_cached_no_last_log_date(mock_firestore_client):
    """Cached stats exist but have no last_log_date field (branch 477->485)."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    # Cached stats without last_log_date - should return stats as-is
    cached_stats = {
        "current_streak": 3,
        "longest_streak": 7,
        "total_logs": 20,
        "cuisines_tried": 5,
        "first_log_date": "2026-01-01",
        # no last_log_date key at all
    }

    collection = backend.db.collection("users")
    collection._docs["user1"] = MockDocument("user1", {"stats": cached_stats})

    stats = await backend.get_user_stats("user1")

    # Should return cached stats without modification
    assert stats["current_streak"] == 3
    assert stats["total_logs"] == 20


@pytest.mark.asyncio
async def test_get_user_stats_log_with_falsy_created_at(mock_firestore_client):
    """Log has created_at but it is falsy - exercises branch 520->525."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    # Patch count_user_logs to return > 0 so we proceed to streak calculation
    with patch.object(backend, "count_user_logs", return_value=1):
        # Create a custom async generator that yields a doc with falsy created_at
        async def fake_stream():
            yield MockDocument(
                "log1",
                {
                    "user_id": "user1",
                    "deleted": False,
                    "created_at": "",  # falsy created_at
                },
            )

        # Create a mock for the streak query chain
        mock_streak_query = MagicMock()
        mock_streak_query.where.return_value = mock_streak_query
        mock_streak_query.order_by.return_value = mock_streak_query
        mock_streak_query.limit.return_value = mock_streak_query
        mock_streak_query.stream.return_value = fake_stream()

        # For first/last queries, return empty stream
        async def empty_stream():
            return
            yield  # pragma: no cover - makes this an async generator

        mock_first_query = MagicMock()
        mock_first_query.where.return_value = mock_first_query
        mock_first_query.order_by.return_value = mock_first_query
        mock_first_query.limit.return_value = mock_first_query
        mock_first_query.stream.return_value = empty_stream()

        mock_last_query = MagicMock()
        mock_last_query.where.return_value = mock_last_query
        mock_last_query.order_by.return_value = mock_last_query
        mock_last_query.limit.return_value = mock_last_query
        mock_last_query.stream.return_value = empty_stream()

        # Mock collection to return our custom queries in sequence
        call_count = 0
        original_collection = backend.db.collection

        def patched_collection(name):
            nonlocal call_count
            if name == "food_logs":
                call_count += 1
                if call_count == 1:
                    return mock_streak_query
                elif call_count == 2:
                    return mock_first_query
                else:
                    return mock_last_query
            return original_collection(name)

        with patch.object(backend._db, "collection", side_effect=patched_collection):
            stats = await backend.get_user_stats("user1")

    assert stats["total_logs"] == 1
    assert stats["first_log_date"] is None
    assert stats["last_log_date"] is None


@pytest.mark.asyncio
async def test_get_user_stats_first_log_no_docs(mock_firestore_client):
    """First/last log queries return no docs (branches 549->555 and 556->563)."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    # Patch count_user_logs to return > 0 so we proceed past the early return
    with patch.object(backend, "count_user_logs", return_value=1):

        async def empty_stream():
            return
            yield  # pragma: no cover - makes this an async generator

        # Create mock queries that return empty streams
        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query

        call_count = 0

        def stream_factory():
            nonlocal call_count
            call_count += 1
            return empty_stream()

        mock_query.stream = stream_factory

        original_collection = backend.db.collection

        def patched_collection(name):
            if name == "food_logs":
                return mock_query
            return original_collection(name)

        with patch.object(backend._db, "collection", side_effect=patched_collection):
            stats = await backend.get_user_stats("user1")

    assert stats["total_logs"] == 1
    assert stats["first_log_date"] is None
    assert stats["last_log_date"] is None
    assert stats["longest_streak"] == 0


@pytest.mark.asyncio
async def test_get_user_stats_streak_starts_yesterday(mock_firestore_client):
    """Streak when today has no log but yesterday and day before do (lines 571-572)."""
    backend = FirestoreBackend(client=mock_firestore_client)
    await backend.connect()

    today = datetime.now(UTC).date()
    yesterday = today - timedelta(days=1)
    day_before = today - timedelta(days=2)

    food_logs_collection = backend.db.collection("food_logs")
    food_logs_collection._docs = {
        "log1": MockDocument(
            "log1",
            {
                "user_id": "user1",
                "deleted": False,
                "created_at": datetime(
                    yesterday.year, yesterday.month, yesterday.day, 10, 0, 0, tzinfo=UTC
                ).isoformat(),
            },
        ),
        "log2": MockDocument(
            "log2",
            {
                "user_id": "user1",
                "deleted": False,
                "created_at": datetime(
                    day_before.year, day_before.month, day_before.day, 10, 0, 0, tzinfo=UTC
                ).isoformat(),
            },
        ),
        # No log for today
    }

    stats = await backend.get_user_stats("user1")

    assert stats["total_logs"] == 2
    # current_streak should be 2 (yesterday + day before)
    assert stats["current_streak"] == 2
    assert stats["longest_streak"] == 2
