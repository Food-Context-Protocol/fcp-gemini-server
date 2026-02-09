"""Tests for lofi_themes.py — shared color/emoji theme system."""

import pytest
from lofi_themes import (
    DEFAULT_THEME,
    EMOJI_VALID_SIZES,
    THEMES,
    get_theme,
    list_themes,
)

REQUIRED_KEYS = {
    "name",
    "emoji_categories",
    "bg_dark",
    "bg_gradient",
    "accent_warm",
    "accent_secondary",
    "accent_cream",
    "text_primary",
    "text_secondary",
    "text_dim",
    "border_glow",
    "description",
}


class TestThemeStructure:
    """Every theme must have the same required keys and valid types."""

    @pytest.mark.parametrize("theme_name", list(THEMES.keys()))
    def test_theme_has_required_keys(self, theme_name):
        theme = THEMES[theme_name]
        assert REQUIRED_KEYS.issubset(theme.keys()), f"{theme_name} missing: {REQUIRED_KEYS - theme.keys()}"

    @pytest.mark.parametrize("theme_name", list(THEMES.keys()))
    def test_color_tuples_are_rgb(self, theme_name):
        theme = THEMES[theme_name]
        color_keys = [
            "bg_dark",
            "bg_gradient",
            "accent_warm",
            "accent_secondary",
            "accent_cream",
            "text_primary",
            "text_secondary",
            "text_dim",
            "border_glow",
        ]
        for key in color_keys:
            val = theme[key]
            assert isinstance(val, tuple), f"{theme_name}.{key} not a tuple"
            assert len(val) == 3, f"{theme_name}.{key} not RGB (len={len(val)})"
            assert all(0 <= c <= 255 for c in val), f"{theme_name}.{key} out of range"

    @pytest.mark.parametrize("theme_name", list(THEMES.keys()))
    def test_emoji_categories_not_empty(self, theme_name):
        theme = THEMES[theme_name]
        assert len(theme["emoji_categories"]) > 0

    @pytest.mark.parametrize("theme_name", list(THEMES.keys()))
    def test_name_and_description_non_empty(self, theme_name):
        theme = THEMES[theme_name]
        assert len(theme["name"]) > 0
        assert len(theme["description"]) > 0


class TestGetTheme:
    def test_returns_default_when_none(self):
        theme = get_theme(None)
        assert theme == THEMES[DEFAULT_THEME]

    def test_returns_default_when_invalid(self):
        theme = get_theme("nonexistent_theme")
        assert theme == THEMES[DEFAULT_THEME]

    def test_returns_named_theme(self):
        theme = get_theme("allergen_alert")
        assert theme["name"] == "Allergen Alert"

    @pytest.mark.parametrize("theme_name", list(THEMES.keys()))
    def test_all_themes_retrievable(self, theme_name):
        theme = get_theme(theme_name)
        assert theme["name"] == THEMES[theme_name]["name"]


class TestListThemes:
    def test_list_themes_prints_all(self, capsys):
        list_themes()
        output = capsys.readouterr().out
        for key in THEMES:
            assert key in output


class TestEmojiValidSizes:
    def test_sizes_are_sorted(self):
        assert EMOJI_VALID_SIZES == sorted(EMOJI_VALID_SIZES)

    def test_known_apple_sizes(self):
        # These are the only sizes Apple Color Emoji supports
        assert 48 in EMOJI_VALID_SIZES
        assert 64 in EMOJI_VALID_SIZES
        assert 96 in EMOJI_VALID_SIZES
        assert 160 in EMOJI_VALID_SIZES

    def test_all_positive(self):
        assert all(s > 0 for s in EMOJI_VALID_SIZES)


class TestDefaultTheme:
    def test_default_is_recipe_quest(self):
        assert DEFAULT_THEME == "recipe_quest"

    def test_default_exists_in_themes(self):
        assert DEFAULT_THEME in THEMES
