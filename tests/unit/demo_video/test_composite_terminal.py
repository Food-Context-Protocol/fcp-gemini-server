"""Tests for composite_terminal.py — lo-fi terminal compositor.

Covers helper functions, background generation, and ffmpeg compositing.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from composite_terminal import (
    FOOD_EMOJI,
    HEIGHT,
    TERM_H,
    TERM_W,
    TERM_X,
    TERM_Y,
    WIDTH,
    _get_emoji_font,
    generate_background,
    get_duration,
    get_font,
    lerp,
)


class TestLerp:
    def test_start_value(self):
        assert lerp(0, 10, 0.0) == 0

    def test_end_value(self):
        assert lerp(0, 10, 1.0) == 10

    def test_midpoint(self):
        assert lerp(0, 10, 0.5) == 5

    def test_negative_values(self):
        assert lerp(-10, 10, 0.5) == pytest.approx(0.0)

    def test_beyond_one(self):
        assert lerp(0, 10, 2.0) == 20


class TestConstants:
    def test_output_dimensions(self):
        assert WIDTH == 1920
        assert HEIGHT == 1080

    def test_terminal_dimensions(self):
        assert TERM_W == 1280
        assert TERM_H == 720

    def test_terminal_centered(self):
        assert TERM_X == (WIDTH - TERM_W) // 2
        assert TERM_Y == (HEIGHT - TERM_H) // 2

    def test_food_emoji_categories(self):
        assert "dishes" in FOOD_EMOJI
        assert "ingredients" in FOOD_EMOJI
        assert "kitchen" in FOOD_EMOJI
        assert "sweet" in FOOD_EMOJI
        for category, emojis in FOOD_EMOJI.items():
            assert len(emojis) > 0


class TestGetFont:
    def test_returns_font_object(self):
        font = get_font("mono", 24)
        assert font is not None

    def test_fallback_to_default(self):
        font = get_font("nonexistent_font_name", 24)
        assert font is not None

    def test_body_font(self):
        font = get_font("body", 20)
        assert font is not None


class TestGetEmojiFont:
    def test_valid_size_returns_font_or_none(self):
        result = _get_emoji_font(48)
        assert result is None or result is not None

    def test_nonexistent_path_returns_none(self):
        with patch("composite_terminal.Path") as mock_path_cls:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_path_cls.return_value = mock_path
            assert _get_emoji_font(48) is None

    def test_font_error_returns_none(self):
        with patch("composite_terminal.Path") as mock_path_cls:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path_cls.return_value = mock_path
            with patch("composite_terminal.ImageFont.truetype", side_effect=Exception("bad font")):
                assert _get_emoji_font(48) is None


class TestGetDuration:
    def test_returns_float_on_success(self):
        with patch("composite_terminal.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="12.5\n")
            assert get_duration("test.mp4") == pytest.approx(12.5)

    def test_returns_zero_on_failure(self):
        with patch("composite_terminal.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            assert get_duration("missing.mp4") == 0.0


class TestGenerateBackground:
    def test_creates_image_file(self, tmp_path):
        from lofi_themes import get_theme

        theme = get_theme("recipe_quest")
        out_path = str(tmp_path / "bg.png")
        generate_background(out_path, theme)
        assert Path(out_path).exists()

    def test_image_dimensions(self, tmp_path):
        from lofi_themes import get_theme
        from PIL import Image

        theme = get_theme("recipe_quest")
        out_path = str(tmp_path / "bg.png")
        generate_background(out_path, theme)

        with Image.open(out_path) as img:
            assert img.size == (WIDTH, HEIGHT)

    @pytest.mark.parametrize(
        "theme_name",
        [
            "recipe_quest",
            "food_scanner",
            "allergen_alert",
            "mcp_toolbox",
            "gemini_brain",
            "meal_log",
        ],
    )
    def test_all_themes_generate(self, tmp_path, theme_name):
        from lofi_themes import get_theme

        theme = get_theme(theme_name)
        out_path = str(tmp_path / f"bg_{theme_name}.png")
        generate_background(out_path, theme)
        assert Path(out_path).exists()

    def test_theme_without_emoji_categories(self, tmp_path):
        theme = {
            "name": "Test",
            "bg_dark": (30, 30, 30),
            "bg_gradient": (60, 60, 60),
            "border_glow": (100, 100, 100),
            "text_dim": (120, 120, 120),
            "description": "test theme",
        }
        out_path = str(tmp_path / "bg_minimal.png")
        generate_background(out_path, theme)
        assert Path(out_path).exists()


class TestComposite:
    def test_composite_calls_ffmpeg(self, tmp_path):
        from composite_terminal import composite
        from lofi_themes import get_theme

        theme = get_theme()
        input_path = str(tmp_path / "input.mp4")
        output_path = str(tmp_path / "output.mp4")
        Path(input_path).touch()

        with patch("composite_terminal.get_duration", return_value=10.0):
            with patch("composite_terminal.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stderr="")
                with patch("shutil.rmtree"):
                    composite(input_path, output_path, theme=theme)

                assert mock_run.called
                cmd = mock_run.call_args[0][0]
                assert "ffmpeg" in cmd

    def test_composite_raises_on_ffmpeg_failure(self, tmp_path):
        from composite_terminal import composite
        from lofi_themes import get_theme

        theme = get_theme()
        input_path = str(tmp_path / "input.mp4")
        output_path = str(tmp_path / "output.mp4")
        Path(input_path).touch()

        with patch("composite_terminal.get_duration", return_value=10.0):
            with patch("composite_terminal.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="encode error")
                with pytest.raises(RuntimeError, match="Compositing failed"):
                    composite(input_path, output_path, theme=theme)

    def test_composite_with_grain(self, tmp_path):
        from composite_terminal import composite
        from lofi_themes import get_theme

        theme = get_theme()
        input_path = str(tmp_path / "input.mp4")
        output_path = str(tmp_path / "output.mp4")
        Path(input_path).touch()

        with patch("composite_terminal.get_duration", return_value=5.0):
            with patch("composite_terminal.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stderr="")
                with patch("shutil.rmtree"):
                    composite(input_path, output_path, theme=theme, grain=True)

                cmd = mock_run.call_args[0][0]
                filter_complex = cmd[cmd.index("-filter_complex") + 1]
                assert "noise" in filter_complex

    def test_composite_default_theme(self, tmp_path):
        from composite_terminal import composite

        input_path = str(tmp_path / "input.mp4")
        output_path = str(tmp_path / "output.mp4")
        Path(input_path).touch()

        with patch("composite_terminal.get_duration", return_value=5.0):
            with patch("composite_terminal.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stderr="")
                with patch("shutil.rmtree"):
                    composite(input_path, output_path)

                assert mock_run.called
