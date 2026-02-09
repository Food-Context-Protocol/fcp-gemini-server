"""Tests for @tool() wrapper functions.

Each wrapper is a thin MCP tool that calls through to an implementation
function and wraps the result in a dict. We mock the inner function to
verify the wrapper plumbing.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# 1. agents.py  delegate_to_food_agent_tool  (lines 18-23)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_delegate_to_food_agent_tool():
    """Cover agents.py wrapper: fetches user prefs then delegates."""
    from fcp.tools.agents import delegate_to_food_agent_tool

    with patch("fcp.services.firestore.firestore_client") as mock_fs:
        mock_fs.get_user_preferences = AsyncMock(return_value={"diet": "vegan"})
        with patch(
            "fcp.tools.agents.delegate_to_food_agent",
            new_callable=AsyncMock,
        ) as mock_delegate:
            mock_delegate.return_value = {
                "agent": "visual_agent",
                "status": "completed",
                "result": {"design": "menu v1"},
            }
            result = await delegate_to_food_agent_tool("user1", "visual_agent", "design menu")

    assert result["agent"] == "visual_agent"
    assert result["status"] == "completed"
    mock_fs.get_user_preferences.assert_awaited_once_with("user1")
    mock_delegate.assert_awaited_once_with(
        agent_name="visual_agent",
        objective="design menu",
        user_context={"diet": "vegan"},
    )


# ---------------------------------------------------------------------------
# 2. blog.py  generate_blog_post_tool  (lines 17-25)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_generate_blog_post_tool_success():
    """Cover blog.py wrapper: happy path returns blog_post key."""
    from fcp.tools.blog import generate_blog_post_tool

    meal_data = {"dish_name": "Ramen", "venue_name": "Ichiran"}

    with patch(
        "fcp.tools.crud.get_meal",
        new_callable=AsyncMock,
        return_value=meal_data,
    ):
        with patch(
            "fcp.tools.blog.generate_blog_post",
            new_callable=AsyncMock,
            return_value="# Ramen Review\n\nDelicious!",
        ) as mock_gen:
            result = await generate_blog_post_tool("user1", "log1")

    assert "blog_post" in result
    assert result["blog_post"] == "# Ramen Review\n\nDelicious!"
    mock_gen.assert_awaited_once_with(log_data=meal_data, style="lifestyle")


@pytest.mark.asyncio
async def test_generate_blog_post_tool_log_not_found():
    """Cover blog.py wrapper: returns error when log is missing."""
    from fcp.tools.blog import generate_blog_post_tool

    with patch(
        "fcp.tools.crud.get_meal",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await generate_blog_post_tool("user1", "missing_log")

    assert result == {"error": "Log not found"}


# ---------------------------------------------------------------------------
# 3. discovery.py  find_nearby_food_tool  (lines 14-23)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_find_nearby_food_tool():
    """Cover discovery.py wrapper: wraps venue list in dict."""
    from fcp.tools.discovery import find_nearby_food_tool

    venues = [
        {"name": "Taco Stand", "distance_m": 500},
        {"name": "Sushi Bar", "distance_m": 1200},
    ]

    with patch(
        "fcp.tools.discovery.find_nearby_food",
        new_callable=AsyncMock,
        return_value=venues,
    ) as mock_find:
        result = await find_nearby_food_tool(latitude=40.0, longitude=-74.0)

    assert "venues" in result
    assert result["venues"] == venues
    mock_find.assert_awaited_once_with(40.0, -74.0, 2000.0, "restaurant", None)


# ---------------------------------------------------------------------------
# 4. profile.py  get_taste_profile_tool  (lines 17-23)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_taste_profile_tool():
    """Cover profile.py wrapper: wraps profile dict."""
    from fcp.tools.profile import get_taste_profile_tool

    profile_data = {
        "period": "all_time",
        "total_meals": 42,
        "top_cuisines": [{"name": "Japanese", "count": 15}],
        "spice_preference": "medium",
    }

    with patch(
        "fcp.tools.profile.get_taste_profile",
        new_callable=AsyncMock,
        return_value=profile_data,
    ) as mock_profile:
        result = await get_taste_profile_tool("user1")

    assert "profile" in result
    assert result["profile"] == profile_data
    mock_profile.assert_awaited_once_with("user1", "all_time")


@pytest.mark.asyncio
async def test_get_taste_profile_tool_with_period():
    """Cover profile.py wrapper: passes non-default period."""
    from fcp.tools.profile import get_taste_profile_tool

    with patch(
        "fcp.tools.profile.get_taste_profile",
        new_callable=AsyncMock,
        return_value={"period": "week", "total_meals": 5},
    ) as mock_profile:
        result = await get_taste_profile_tool("user1", period="week")

    assert result["profile"]["period"] == "week"
    mock_profile.assert_awaited_once_with("user1", "week")


# ---------------------------------------------------------------------------
# 5. search.py  search_meals_tool  (lines 24-31)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_search_meals_tool():
    """Cover search.py wrapper: wraps search results list."""
    from fcp.tools.search import search_meals_tool

    search_results = [
        {"id": "log1", "dish_name": "Tacos", "relevance_score": 0.95},
        {"id": "log2", "dish_name": "Taco Salad", "relevance_score": 0.72},
    ]

    with patch(
        "fcp.tools.search.search_meals",
        new_callable=AsyncMock,
        return_value=search_results,
    ) as mock_search:
        result = await search_meals_tool("user1", "tacos")

    assert "results" in result
    assert result["results"] == search_results
    mock_search.assert_awaited_once_with("user1", "tacos", 10)


@pytest.mark.asyncio
async def test_search_meals_tool_custom_limit():
    """Cover search.py wrapper: passes custom limit."""
    from fcp.tools.search import search_meals_tool

    with patch(
        "fcp.tools.search.search_meals",
        new_callable=AsyncMock,
        return_value=[],
    ) as mock_search:
        result = await search_meals_tool("user1", "pizza", limit=5)

    assert result == {"results": []}
    mock_search.assert_awaited_once_with("user1", "pizza", 5)


# ---------------------------------------------------------------------------
# 6. visual.py  generate_image_prompt_tool  (lines 94-101)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_generate_image_prompt_tool():
    """Cover visual.py wrapper: wraps prompt string."""
    from fcp.tools.visual import generate_image_prompt_tool

    prompt_text = "A steaming bowl of tonkotsu ramen, macro photography, shallow depth of field"

    with patch(
        "fcp.tools.visual.generate_image_prompt",
        new_callable=AsyncMock,
        return_value=prompt_text,
    ) as mock_gen:
        result = await generate_image_prompt_tool("ramen")

    assert "prompt" in result
    assert result["prompt"] == prompt_text
    mock_gen.assert_awaited_once_with("ramen", "photorealistic", "menu")


@pytest.mark.asyncio
async def test_generate_image_prompt_tool_custom_args():
    """Cover visual.py wrapper: passes non-default style and context."""
    from fcp.tools.visual import generate_image_prompt_tool

    with patch(
        "fcp.tools.visual.generate_image_prompt",
        new_callable=AsyncMock,
        return_value="watercolor sushi",
    ) as mock_gen:
        result = await generate_image_prompt_tool("sushi platter", style="watercolor", context="social_media")

    assert result["prompt"] == "watercolor sushi"
    mock_gen.assert_awaited_once_with("sushi platter", "watercolor", "social_media")


# ---------------------------------------------------------------------------
# 7. suggest.py  get_meal_suggestions_tool  (lines 21-28)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_meal_suggestions_tool():
    """Cover suggest.py wrapper: wraps suggestions list."""
    from fcp.tools.suggest import get_meal_suggestions_tool

    suggestions = [{"dish": "Pad Thai", "reason": "You love Thai food"}]

    with patch(
        "fcp.tools.suggest.suggest_meal",
        new_callable=AsyncMock,
        return_value=suggestions,
    ) as mock_suggest:
        result = await get_meal_suggestions_tool("user1", context="lunch")

    assert "suggestions" in result
    assert result["suggestions"] == suggestions
    mock_suggest.assert_awaited_once_with("user1", "lunch", 3)
