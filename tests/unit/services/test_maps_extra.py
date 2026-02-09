"""Coverage tests for maps service."""

from __future__ import annotations

import pytest

from fcp.services import maps


@pytest.mark.asyncio
async def test_find_nearby_places_default_types_no_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    result = await maps.find_nearby_places(1.0, 2.0, included_types=None)
    assert result == []
