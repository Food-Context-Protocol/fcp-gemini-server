"""Coverage tests for taste buddy warning normalization."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools import taste_buddy


@pytest.mark.asyncio
async def test_taste_buddy_warning_normalization():
    with patch(
        "fcp.tools.taste_buddy.gemini.generate_json",
        new=AsyncMock(return_value={"warnings": None}),
    ):
        result = await taste_buddy.check_dietary_compatibility("Dish", ["ing"], [], [])
        assert result["warnings"] == []

    with patch(
        "fcp.tools.taste_buddy.gemini.generate_json",
        new=AsyncMock(return_value={"warnings": ["a", ""]}),
    ):
        result = await taste_buddy.check_dietary_compatibility("Dish", ["ing"], [], [])
        assert result["warnings"] == ["a"]

    with patch(
        "fcp.tools.taste_buddy.gemini.generate_json",
        new=AsyncMock(return_value={"warnings": 123}),
    ):
        result = await taste_buddy.check_dietary_compatibility("Dish", ["ing"], [], [])
        assert result["warnings"] == []
