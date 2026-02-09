"""Coverage tests for publishing routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from fcp.auth.permissions import AuthenticatedUser, UserRole
from fcp.routes import publishing


class DummyDB:
    def __init__(self):
        self.drafts = {}
        self.published = {}

    async def save_draft(self, user_id, data):
        draft_id = f"d{len(self.drafts) + 1}"
        self.drafts[draft_id] = data
        return draft_id

    async def get_drafts(self, user_id):
        return list(self.drafts.values())

    async def get_draft(self, user_id, draft_id):
        return self.drafts.get(draft_id)

    async def update_draft(self, user_id, draft_id, updates):
        self.drafts[draft_id].update(updates)

    async def delete_draft(self, user_id, draft_id):
        return self.drafts.pop(draft_id, None) is not None

    async def save_published_content(self, user_id, data):
        published_id = f"p{len(self.published) + 1}"
        self.published[published_id] = data
        return published_id

    async def get_published_content(self, user_id):
        return list(self.published.values())

    async def get_published_content_item(self, user_id, content_id):
        return self.published.get(content_id)

    async def update_published_content(self, user_id, content_id, updates):
        self.published[content_id].update(updates)


class DummyAgent:
    async def generate_blog_post(self, **kwargs):
        return {"title": "Blog"}

    async def generate_weekly_digest(self, **kwargs):
        return {"title": "Digest"}

    async def generate_social_post(self, **kwargs):
        return {"title": "Social"}


def _request(path: str = "/publish"):
    return Request({"type": "http", "method": "POST", "path": path, "headers": []})


@pytest.mark.asyncio
async def test_generate_content_paths():
    user = AuthenticatedUser(user_id="u1", role=UserRole.AUTHENTICATED)
    db = DummyDB()
    logs = [{"id": "1"}]

    with (
        patch("fcp.routes.publishing.get_firestore_client", return_value=db),
        patch("fcp.routes.publishing.ContentGeneratorAgent", return_value=DummyAgent()),
        patch("fcp.routes.publishing.get_meals_by_ids", new=AsyncMock(return_value=[])),
    ):
        with pytest.raises(HTTPException):
            await publishing.generate_content(
                _request(),
                publishing.GenerateContentRequest(content_type="blog_post", log_ids=["1"]),
                user=user,
            )

    with (
        patch("fcp.routes.publishing.get_firestore_client", return_value=db),
        patch("fcp.routes.publishing.ContentGeneratorAgent", return_value=DummyAgent()),
        patch("fcp.routes.publishing.get_meals", new=AsyncMock(return_value=[])),
    ):
        with pytest.raises(HTTPException):
            await publishing.generate_content(
                _request(),
                publishing.GenerateContentRequest(content_type="blog_post"),
                user=user,
            )

    with (
        patch("fcp.routes.publishing.get_firestore_client", return_value=db),
        patch("fcp.routes.publishing.ContentGeneratorAgent", return_value=DummyAgent()),
        patch("fcp.routes.publishing.get_meals_by_ids", new=AsyncMock(return_value=logs)),
    ):
        result = await publishing.generate_content(
            _request(),
            publishing.GenerateContentRequest(content_type="blog_post", log_ids=["1"]),
            user=user,
        )
        assert result.draft_id

    with (
        patch("fcp.routes.publishing.get_firestore_client", return_value=db),
        patch("fcp.routes.publishing.ContentGeneratorAgent", return_value=DummyAgent()),
        patch("fcp.routes.publishing.get_meals", new=AsyncMock(return_value=logs)),
    ):
        result = await publishing.generate_content(
            _request(),
            publishing.GenerateContentRequest(content_type="weekly_digest"),
            user=user,
        )
        assert result.draft_id

    with (
        patch("fcp.routes.publishing.get_firestore_client", return_value=db),
        patch("fcp.routes.publishing.ContentGeneratorAgent", return_value=DummyAgent()),
        patch("fcp.routes.publishing.get_meals", new=AsyncMock(return_value=logs)),
    ):
        result = await publishing.generate_content(
            _request(),
            publishing.GenerateContentRequest(content_type="social_twitter"),
            user=user,
        )
        assert result.draft_id

    with (
        patch("fcp.routes.publishing.get_firestore_client", return_value=db),
        patch("fcp.routes.publishing.ContentGeneratorAgent", return_value=DummyAgent()),
        patch("fcp.routes.publishing.get_meals", new=AsyncMock(return_value=logs)),
    ):
        result = await publishing.generate_content(
            _request(),
            publishing.GenerateContentRequest(content_type="social_instagram"),
            user=user,
        )
        assert result.draft_id


@pytest.mark.asyncio
async def test_draft_crud_and_publish_and_analytics():
    user = AuthenticatedUser(user_id="u1", role=UserRole.AUTHENTICATED)
    db = DummyDB()
    db.drafts["d1"] = {"status": "draft", "content": {}, "content_type": "blog_post"}

    with patch("fcp.routes.publishing.get_firestore_client", return_value=db):
        result = await publishing.list_drafts(user=user)
        assert result.count == 1

        with pytest.raises(HTTPException):
            await publishing.get_draft("missing", user=user)

        assert await publishing.get_draft("d1", user=user)

        with pytest.raises(HTTPException):
            await publishing.update_draft("missing", publishing.UpdateDraftRequest(content={"x": 1}), user=user)

        with pytest.raises(HTTPException):
            await publishing.update_draft("d1", publishing.UpdateDraftRequest(), user=user)

        result = await publishing.update_draft("d1", publishing.UpdateDraftRequest(content={"x": 1}), user=user)
        assert result.success is True
        result = await publishing.update_draft("d1", publishing.UpdateDraftRequest(status="archived"), user=user)
        assert result.success is True
        assert db.drafts["d1"]["status"] == "archived"

        with pytest.raises(HTTPException):
            await publishing.delete_draft("missing", user=user)

        result = await publishing.delete_draft("d1", user=user)
        assert result.success is True

    # Publish paths
    db.drafts["d2"] = {"status": "draft", "content": {}, "content_type": "blog_post"}
    with (
        patch("fcp.routes.publishing.get_firestore_client", return_value=db),
        patch(
            "fcp.routes.publishing.get_astro_bridge",
            return_value=MagicMock(publish_post=AsyncMock(return_value={"success": False})),
        ),
    ):
        result = await publishing.publish_draft(
            _request(),
            "d2",
            publishing.PublishRequest(platforms=["blog"]),
            user=user,
        )
        assert result.success is False

    with patch("fcp.routes.publishing.get_firestore_client", return_value=db):
        with pytest.raises(HTTPException):
            await publishing.publish_draft(_request(), "missing", publishing.PublishRequest(), user=user)

    db.drafts["d3"] = {"status": "published", "content": {}, "content_type": "blog_post"}
    with patch("fcp.routes.publishing.get_firestore_client", return_value=db):
        with pytest.raises(HTTPException):
            await publishing.publish_draft(_request(), "d3", publishing.PublishRequest(), user=user)

    db.drafts["d3b"] = {"status": "draft", "content": {}, "content_type": "blog_post"}
    with patch("fcp.routes.publishing.get_firestore_client", return_value=db):
        result = await publishing.publish_draft(
            _request(),
            "d3b",
            publishing.PublishRequest(platforms=[]),
            user=user,
        )
        assert result.success is False

    db.drafts["d4"] = {"status": "draft", "content": {}, "content_type": "blog_post"}
    astro = MagicMock(publish_post=AsyncMock(return_value={"success": True, "url": "u", "post_id": "p"}))
    with (
        patch("fcp.routes.publishing.get_firestore_client", return_value=db),
        patch("fcp.routes.publishing.get_astro_bridge", return_value=astro),
    ):
        result = await publishing.publish_draft(
            _request(),
            "d4",
            publishing.PublishRequest(platforms=["blog"]),
            user=user,
        )
        assert result.success is True

    db.drafts["d5"] = {"status": "draft", "content": {}, "content_type": "blog_post"}
    astro = MagicMock(publish_post=AsyncMock(return_value={"success": True}))
    with (
        patch("fcp.routes.publishing.get_firestore_client", return_value=db),
        patch("fcp.routes.publishing.get_astro_bridge", return_value=astro),
    ):
        result = await publishing.publish_draft(
            _request(),
            "d5",
            publishing.PublishRequest(platforms=["blog"]),
            user=user,
        )
        assert result.success is True

    # Published list and analytics
    db.published["p1"] = {"external_ids": {"astro_post_id": "p"}, "content": {}}
    with patch("fcp.routes.publishing.get_firestore_client", return_value=db):
        result = await publishing.list_published(user=user)
        assert result.count >= 1

        with pytest.raises(HTTPException):
            await publishing.get_analytics("missing", user=user)

    db.published["p2"] = {"external_ids": {}}
    with patch("fcp.routes.publishing.get_firestore_client", return_value=db):
        result = await publishing.get_analytics("p2", user=user)
        assert result.success is False

    astro = MagicMock(get_analytics=AsyncMock(return_value={"success": True, "analytics": {"views": 1}}))
    with (
        patch("fcp.routes.publishing.get_firestore_client", return_value=db),
        patch("fcp.routes.publishing.get_astro_bridge", return_value=astro),
    ):
        result = await publishing.get_analytics("p1", user=user)
        assert result.success is True
        assert db.published["p1"]["analytics"] == {"views": 1}


@pytest.mark.asyncio
async def test_get_analytics_updates_on_success():
    user = AuthenticatedUser(user_id="u1", role=UserRole.AUTHENTICATED)
    db = DummyDB()
    db.published["p1"] = {"external_ids": {"astro_post_id": "p"}}
    astro = MagicMock(get_analytics=AsyncMock(return_value={"success": True, "analytics": {"views": 2}}))

    with (
        patch("fcp.routes.publishing.get_firestore_client", return_value=db),
        patch("fcp.routes.publishing.get_astro_bridge", return_value=astro),
        patch.object(db, "update_published_content", new_callable=AsyncMock) as mock_update,
    ):
        result = await publishing.get_analytics("p1", user=user)
        assert result.success is True
        mock_update.assert_called_once()


@pytest.mark.asyncio
async def test_get_analytics_does_not_update_on_failure():
    user = AuthenticatedUser(user_id="u1", role=UserRole.AUTHENTICATED)
    db = DummyDB()
    db.published["p1"] = {"external_ids": {"astro_post_id": "p"}}
    astro = MagicMock(get_analytics=AsyncMock(return_value={"success": False, "error": "nope"}))

    with (
        patch("fcp.routes.publishing.get_firestore_client", return_value=db),
        patch("fcp.routes.publishing.get_astro_bridge", return_value=astro),
        patch.object(db, "update_published_content", new_callable=AsyncMock) as mock_update,
    ):
        result = await publishing.get_analytics("p1", user=user)
        assert result.success is False
        mock_update.assert_not_called()
