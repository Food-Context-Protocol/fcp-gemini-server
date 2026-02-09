"""Coverage tests for content-generation tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools import blog, drinks, scaling, social, standardize, visual


@pytest.mark.asyncio
async def test_analyze_beverage_success_and_error():
    with patch("fcp.tools.drinks.gemini.generate_json", new=AsyncMock(return_value={"type": "Wine"})):
        result = await drinks.analyze_beverage("Cabernet")
        assert result["type"] == "Wine"

    with patch("fcp.tools.drinks.gemini.generate_json", new=AsyncMock(side_effect=Exception("boom"))):
        result = await drinks.analyze_beverage("Cabernet")
        assert "error" in result


@pytest.mark.asyncio
async def test_standardize_recipe_success_and_error():
    with patch(
        "fcp.tools.standardize.gemini.generate_json",
        new=AsyncMock(return_value={"name": "Toast"}),
    ):
        result = await standardize.standardize_recipe("Bread and butter")
        assert result["@context"] == "https://schema.org"
        assert result["@type"] == "Recipe"

    with patch(
        "fcp.tools.standardize.gemini.generate_json",
        new=AsyncMock(side_effect=Exception("boom")),
    ):
        result = await standardize.standardize_recipe("Bread and butter")
        assert result["error"] == "Failed to standardize recipe"


@pytest.mark.asyncio
async def test_scale_recipe_success_list_and_error():
    with patch(
        "fcp.tools.scaling.gemini.generate_json",
        new=AsyncMock(return_value=[{"recipeYield": "2"}]),
    ):
        result = await scaling.scale_recipe({"name": "Toast"}, target_servings=2)
        assert result["recipeYield"] == "2"

    with patch(
        "fcp.tools.scaling.gemini.generate_json",
        new=AsyncMock(side_effect=Exception("boom")),
    ):
        result = await scaling.scale_recipe({"name": "Toast"}, target_servings=2)
        assert result["status"] == "failed"


@pytest.mark.asyncio
async def test_social_tools_success_and_error():
    with patch(
        "fcp.tools.social.gemini.generate_json",
        new=AsyncMock(return_value={"content": "ok"}),
    ):
        result = await social.generate_social_post({"dish_name": "Sushi"}, platform="twitter", style="casual")
        assert result["content"] == "ok"

    with patch(
        "fcp.tools.social.gemini.generate_json",
        new=AsyncMock(side_effect=Exception("boom")),
    ):
        result = await social.generate_social_post({"dish_name": "Sushi"}, platform="twitter", style="casual")
        assert "error" in result

    with patch(
        "fcp.tools.social.gemini.generate_json",
        new=AsyncMock(return_value={"title": "Digest"}),
    ):
        result = await social.generate_weekly_digest([{"dish_name": "Sushi"}], user_name="Pat")
        assert result["title"] == "Digest"

    with patch(
        "fcp.tools.social.gemini.generate_json",
        new=AsyncMock(side_effect=Exception("boom")),
    ):
        result = await social.generate_weekly_digest([{"dish_name": "Sushi"}])
        assert "weekly_summary" in result

    with patch(
        "fcp.tools.social.gemini.generate_json",
        new=AsyncMock(return_value={"story": "ok"}),
    ):
        result = await social.generate_food_story([{"dish_name": "Sushi"}], theme="theme")
        assert result["story"] == "ok"

    with patch(
        "fcp.tools.social.gemini.generate_json",
        new=AsyncMock(side_effect=Exception("boom")),
    ):
        result = await social.generate_food_story([{"dish_name": "Sushi"}])
        assert "story" in result


@pytest.mark.asyncio
async def test_generate_blog_post_success_and_error():
    with patch(
        "fcp.tools.blog.gemini.generate_content",
        new=AsyncMock(return_value="# Hello"),
    ):
        result = await blog.generate_blog_post({"dish_name": "Pasta"})
        assert result.startswith("#")

    with patch(
        "fcp.tools.blog.gemini.generate_content",
        new=AsyncMock(side_effect=Exception("boom")),
    ):
        result = await blog.generate_blog_post({"dish_name": "Pasta"})
        assert "Failed to generate" in result


@pytest.mark.asyncio
async def test_visual_generate_image_prompt_success_and_error():
    with patch(
        "fcp.tools.visual.gemini.generate_content",
        new=AsyncMock(return_value=" prompt "),
    ):
        result = await visual.generate_image_prompt("Ramen", style="photo", context="menu")
        assert result == "prompt"

    with patch(
        "fcp.tools.visual.gemini.generate_content",
        new=AsyncMock(side_effect=Exception("boom")),
    ):
        result = await visual.generate_image_prompt("Ramen")
        assert "Ramen" in result


@pytest.mark.asyncio
async def test_visual_generate_food_image_maps_enums():
    class DummyResult:
        def __init__(self):
            self.image_bytes = b"abc"
            self.mime_type = "image/png"
            self.aspect_ratio = visual.AspectRatio.WIDE
            self.resolution = visual.Resolution.ULTRA

    class DummyService:
        async def generate_food_image(self, **kwargs):
            # ensure mapping happened
            assert kwargs["aspect_ratio"] == visual.AspectRatio.WIDE
            assert kwargs["resolution"] == visual.Resolution.ULTRA
            return DummyResult()

    with patch("fcp.tools.visual._get_image_service", return_value=DummyService()):
        result = await visual.generate_food_image("Tacos", aspect_ratio="16:9", resolution="4K")
        assert result["mime_type"] == "image/png"
        assert result["aspect_ratio"] == "16:9"
