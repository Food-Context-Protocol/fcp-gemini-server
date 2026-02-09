#!/usr/bin/env python3
"""
Composite a 1280x720 terminal recording into a 1920x1080 lo-fi frame.

Generates a themed background with gradient + border chrome + food emoji in margins,
then uses ffmpeg to overlay the terminal recording with subtle vignette.

Supports different color themes per scenario via lofi_themes.py.

Usage:
    python composite_terminal.py recordings/recipe_quest_raw.mp4
    python composite_terminal.py input.mp4 output.mp4
    python composite_terminal.py input.mp4 output.mp4 --theme food_scanner
"""

import subprocess
import sys
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from lofi_themes import get_theme, EMOJI_VALID_SIZES, list_themes

WIDTH = 1920
HEIGHT = 1080
TERM_W = 1280
TERM_H = 720
TERM_X = (WIDTH - TERM_W) // 2   # 320
TERM_Y = (HEIGHT - TERM_H) // 2  # 180

FOOD_EMOJI = {
    "dishes": ["🍕", "🍣", "🌮", "🍜", "🍝", "🍲", "🥗", "🍱", "🫕", "🥘"],
    "ingredients": ["🥑", "🧄", "🌶️", "🍅", "🧅", "🥕", "🫑", "🌽", "🍋"],
    "kitchen": ["🔪", "🍳", "🥄", "🧂", "🫙"],
    "sweet": ["🧁", "🍰", "🍩", "🧋", "☕"],
}

SCRIPT_DIR = Path(__file__).parent
TEMP_DIR = SCRIPT_DIR / "assembly_tmp"


def lerp(a, b, t):
    return a + (b - a) * t


def get_font(name, size):
    """Get font with fallback."""
    fonts_dir = Path(__file__).parent / "fonts"
    candidates = {
        "mono": [
            fonts_dir / "JetBrainsMono.ttf",
            Path("/System/Library/Fonts/SFNSMono.ttf"),
            Path("/System/Library/Fonts/Monaco.ttf"),
        ],
        "body": [
            fonts_dir / "Inter.ttf",
            Path("/System/Library/Fonts/Helvetica.ttc"),
        ],
    }
    for path in candidates.get(name, []):
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                continue
    return ImageFont.load_default()


def _get_emoji_font(size: int):
    """Get Apple Color Emoji font for margin decorations.

    IMPORTANT: Only sizes 20, 26, 32, 40, 48, 52, 64, 96, 160 are valid.
    """
    apple_path = Path("/System/Library/Fonts/Apple Color Emoji.ttc")
    if apple_path.exists():
        try:
            return ImageFont.truetype(str(apple_path), size)
        except Exception:
            pass
    return None


def generate_background(output_path: str, theme: dict):
    """Generate the static 1920x1080 lo-fi background with terminal chrome and margin emoji."""
    img = Image.new("RGB", (WIDTH, HEIGHT), theme["bg_dark"])
    draw = ImageDraw.Draw(img)

    # Vertical gradient
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(lerp(theme["bg_dark"][0], theme["bg_gradient"][0], t))
        g = int(lerp(theme["bg_dark"][1], theme["bg_gradient"][1], t))
        b = int(lerp(theme["bg_dark"][2], theme["bg_gradient"][2], t))
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # Terminal chrome: warm glow layers
    glow_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    gr, gg, gb = theme["border_glow"]

    for offset, alpha in [(8, 10), (6, 18), (4, 30), (2, 45)]:
        glow_draw.rounded_rectangle(
            [
                TERM_X - offset, TERM_Y - offset,
                TERM_X + TERM_W + offset, TERM_Y + TERM_H + offset,
            ],
            radius=12 + offset,
            outline=(gr, gg, gb, alpha),
            width=2,
        )

    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=3))
    img.paste(glow_layer, (0, 0), glow_layer)

    # Inner border (crisp)
    border_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border_layer)
    border_draw.rounded_rectangle(
        [TERM_X - 2, TERM_Y - 2, TERM_X + TERM_W + 2, TERM_Y + TERM_H + 2],
        radius=12,
        outline=(gr, gg, gb, 80),
        width=1,
    )
    img.paste(border_layer, (0, 0), border_layer)

    # Food emoji in margins — crisp and visible (not ghostly)
    emoji_font = _get_emoji_font(48)  # Valid Apple Color Emoji size
    if emoji_font:
        emoji_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        emoji_draw = ImageDraw.Draw(emoji_layer)

        # Build emoji pool from theme categories
        pool = []
        for cat in theme.get("emoji_categories", ["dishes"]):
            pool.extend(FOOD_EMOJI.get(cat, []))

        # Positions in the margins (avoid terminal area)
        margin_positions = [
            (80, 80),
            (TERM_X + TERM_W + 40, 100),
            (100, HEIGHT - 90),
            (TERM_X + TERM_W + 55, HEIGHT - 95),
            (50, HEIGHT // 2 - 20),
            (TERM_X + TERM_W + 45, HEIGHT // 2 + 30),
        ]

        random.seed(42)
        used = set()
        for pos in margin_positions:
            available = [c for c in pool if c not in used]
            if not available:
                available = pool
            char = random.choice(available)
            used.add(char)
            emoji_draw.text(pos, char, font=emoji_font, embedded_color=True)

        # Light blur + moderate alpha — visible but not distracting
        emoji_layer = emoji_layer.filter(ImageFilter.GaussianBlur(radius=1))
        r_ch, g_ch, b_ch, a_ch = emoji_layer.split()
        a_ch = a_ch.point(lambda p: int(p * 0.45))
        emoji_layer = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))
        img.paste(emoji_layer, (0, 0), emoji_layer)

    # Watermark: "FCP" in bottom-right margin
    font_wm = get_font("mono", 18)
    wr, wg, wb = theme["text_dim"]
    draw = ImageDraw.Draw(img)
    draw.text(
        (TERM_X + TERM_W - 40, TERM_Y + TERM_H + 12),
        "FCP",
        fill=(wr, wg, wb),
        font=font_wm,
    )

    # Scenario label in top-left margin
    font_label = get_font("body", 20)
    lr, lg, lb = theme["text_dim"]
    draw.text(
        (TERM_X, TERM_Y - 30),
        theme.get("name", "Demo"),
        fill=(lr, lg, lb),
        font=font_label,
    )

    img.save(output_path)
    print(f"  Background: {output_path}")


def get_duration(path: str) -> float:
    """Get video duration in seconds."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip()) if result.returncode == 0 else 0.0


def composite(input_recording: str, output_path: str, theme: dict = None, grain: bool = False):
    """Composite the terminal recording into the lo-fi frame.

    1. Generate themed background PNG
    2. Use ffmpeg filter_complex to overlay terminal + vignette
    """
    if theme is None:
        theme = get_theme()

    TEMP_DIR.mkdir(exist_ok=True)

    bg_path = str(TEMP_DIR / "lofi_bg.png")
    generate_background(bg_path, theme)

    duration = get_duration(input_recording)
    print(f"  Recording duration: {duration:.1f}s")

    # Build ffmpeg filter chain
    filter_parts = []

    # Scale terminal to exact size (safety net)
    filter_parts.append(f"[1:v]scale={TERM_W}:{TERM_H}:flags=lanczos[term]")

    # Overlay terminal on background
    filter_parts.append(f"[0:v][term]overlay={TERM_X}:{TERM_Y}[comp]")

    # Vignette (subtle edge darkening)
    filter_parts.append("[comp]vignette=PI/6[vig]")

    if grain:
        filter_parts.append("[vig]noise=alls=5:allf=t+u[out]")
        final_label = "[out]"
    else:
        filter_parts[-1] = "[comp]vignette=PI/6[out]"
        final_label = "[out]"

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", bg_path,
        "-i", input_recording,
        "-filter_complex", filter_complex,
        "-map", final_label,
        "-map", "1:a?",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-t", str(duration),
        "-r", "30",
        output_path,
    ]

    print("  Compositing...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ffmpeg error: {result.stderr[-500:]}")
        raise RuntimeError("Compositing failed")

    # Cleanup
    import shutil
    shutil.rmtree(TEMP_DIR, ignore_errors=True)

    out_dur = get_duration(output_path)
    print(f"  Done: {output_path} ({out_dur:.1f}s)")


if __name__ == "__main__":
    # Parse args
    theme_name = None
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for i, a in enumerate(sys.argv[1:]):
        if a == "--theme" and i + 2 < len(sys.argv):
            theme_name = sys.argv[i + 2]
        if a == "--list-themes":
            print("Available themes:")
            list_themes()
            sys.exit(0)

    theme = get_theme(theme_name)

    default_input = str(SCRIPT_DIR / "recordings" / "recipe_quest_raw.mp4")
    default_output = str(SCRIPT_DIR / "recordings" / "recipe_quest_composited.mp4")
    input_file = args[0] if len(args) > 0 else default_input
    output_file = args[1] if len(args) > 1 else default_output

    if not Path(input_file).exists():
        print(f"Input not found: {input_file}")
        print("\nRecord your terminal at 1280x720, then:")
        print(f"  python composite_terminal.py {input_file}")
        print(f"\nAvailable themes (--theme <name>):")
        list_themes()
        sys.exit(1)

    print(f"\nCompositing terminal recording")
    print(f"  Input:  {input_file}")
    print(f"  Output: {output_file}")
    print(f"  Theme:  {theme['name']} — {theme['description']}")
    composite(input_file, output_file, theme=theme)
