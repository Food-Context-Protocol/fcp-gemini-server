"""Coverage tests for Astro CMS bridge."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from fcp.tools.astro import AstroBridge, get_astro_bridge


@pytest.mark.asyncio
async def test_astro_bridge_disabled():
    with patch.dict(os.environ, {}, clear=True):
        bridge = AstroBridge()
        assert bridge.enabled is False
        result = await bridge.publish_post({}, "u1")
        assert result["success"] is False
        result = await bridge.update_post("1", {})
        assert result["success"] is False
        result = await bridge.delete_post("1")
        assert result["success"] is False
        result = await bridge.get_analytics("1")
        assert result["success"] is False


@pytest.mark.asyncio
async def test_astro_bridge_requests_success_and_errors():
    with patch.dict(os.environ, {"ASTRO_API_KEY": "key", "ASTRO_ENDPOINT": "http://astro/"}):
        bridge = AstroBridge()
        assert bridge.enabled is True

        class DummyClient:
            def __init__(self, response, *args, **kwargs):
                self._response = response

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

            async def post(self, *args, **kwargs):
                return self._response

            async def patch(self, *args, **kwargs):
                return self._response

            async def delete(self, *args, **kwargs):
                return self._response

            async def get(self, *args, **kwargs):
                return self._response

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"url": "http://post", "id": "p1"}
        mock_response.text = ""

        def client_factory(*args, **kwargs):
            return DummyClient(mock_response, *args, **kwargs)

        with patch("fcp.tools.astro.httpx.AsyncClient", new=client_factory):
            result = await bridge.publish_post({"title": "hi"}, "u1", publish_immediately=True)
            assert result["success"] is True, result
            result = await bridge.update_post("p1", {"title": "x"})
            assert result["success"] is True
            result = await bridge.delete_post("p1")
            assert result["success"] is True
            result = await bridge.get_analytics("p1")
            assert result["success"] is True

        # Non-200 responses
        mock_response.status_code = 500
        mock_response.text = "err"
        with patch("fcp.tools.astro.httpx.AsyncClient", new=client_factory):
            result = await bridge.publish_post({"title": "hi"}, "u1")
            assert result["success"] is False
            result = await bridge.update_post("p1", {"title": "x"})
            assert result["success"] is False
            result = await bridge.delete_post("p1")
            assert result["success"] is False
            result = await bridge.get_analytics("p1")
            assert result["success"] is False

        # Timeout and request errors
        class TimeoutClient(DummyClient):
            async def post(self, *args, **kwargs):
                raise httpx.TimeoutException("timeout")

        def timeout_factory(*args, **kwargs):
            return TimeoutClient(mock_response, *args, **kwargs)

        with patch("fcp.tools.astro.httpx.AsyncClient", new=timeout_factory):
            result = await bridge.publish_post({"title": "hi"}, "u1")
            assert "timed out" in result["error"]

        class ErrorClient(DummyClient):
            async def post(self, *args, **kwargs):
                raise httpx.RequestError("bad", request=None)

        def error_factory(*args, **kwargs):
            return ErrorClient(mock_response, *args, **kwargs)

        with patch("fcp.tools.astro.httpx.AsyncClient", new=error_factory):
            result = await bridge.publish_post({"title": "hi"}, "u1")
            assert "Network error" in result["error"]


def test_get_astro_bridge_singleton():
    with patch("fcp.tools.astro._astro_bridge", None):
        bridge = get_astro_bridge()
        assert isinstance(bridge, AstroBridge)


def test_get_astro_bridge_reuses_instance():
    existing = AstroBridge()
    with patch("fcp.tools.astro._astro_bridge", existing):
        assert get_astro_bridge() is existing


@pytest.mark.asyncio
async def test_astro_bridge_update_delete_get_exceptions():
    with patch.dict(os.environ, {"ASTRO_API_KEY": "key", "ASTRO_ENDPOINT": "http://astro/"}):
        bridge = AstroBridge()

        class BaseClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

        class TimeoutClient(BaseClient):
            async def patch(self, *args, **kwargs):
                raise httpx.TimeoutException("timeout")

            async def delete(self, *args, **kwargs):
                raise httpx.TimeoutException("timeout")

            async def get(self, *args, **kwargs):
                raise httpx.TimeoutException("timeout")

        class ErrorClient(BaseClient):
            async def patch(self, *args, **kwargs):
                raise httpx.RequestError("bad", request=None)

            async def delete(self, *args, **kwargs):
                raise httpx.RequestError("bad", request=None)

            async def get(self, *args, **kwargs):
                raise httpx.RequestError("bad", request=None)

        with patch("fcp.tools.astro.httpx.AsyncClient", new=lambda *a, **k: TimeoutClient()):
            result = await bridge.update_post("p1", {"title": "x"})
            assert "timed out" in result["error"]
            result = await bridge.delete_post("p1")
            assert "timed out" in result["error"]
            result = await bridge.get_analytics("p1")
            assert "timed out" in result["error"]

        with patch("fcp.tools.astro.httpx.AsyncClient", new=lambda *a, **k: ErrorClient()):
            result = await bridge.update_post("p1", {"title": "x"})
            assert "Network error" in result["error"]
            result = await bridge.delete_post("p1")
            assert "Network error" in result["error"]
            result = await bridge.get_analytics("p1")
            assert "Network error" in result["error"]
