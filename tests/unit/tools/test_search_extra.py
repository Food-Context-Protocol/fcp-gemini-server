"""Coverage tests for search tool."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from fcp.tools import search


@pytest.mark.asyncio
async def test_search_meals_empty_query_returns_empty():
    with patch("fcp.tools.search.sanitize_search_query", return_value=""):
        result = await search.search_meals("u1", "   ")
        assert result == []


def test_keyword_search_respects_limit_break():
    logs = [
        {"id": "1", "dish_name": "Pasta", "notes": "tomato"},
        {"id": "2", "dish_name": "Salad", "notes": "tomato"},
    ]
    result = search._keyword_search(logs, "tomato", limit=1)
    assert len(result) == 1
