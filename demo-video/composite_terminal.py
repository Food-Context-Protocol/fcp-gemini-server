#!/usr/bin/env python3
"""
Composite a 1280x720 terminal recording into a 1920x1080 lo-fi frame.

Generates a static background with gradient + border chrome + faint food emoji,
then uses ffmpeg to overlay the terminal recording with grain and vignette.

Usage:
    python composite_terminal.py recordings/recipe_quest_raw.mp4
    python composite_terminal.py input.mp4 output.mp4
"""

import subprocess
import sys
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH = 1920
HEIGHT = 1080
TERM_W = 1280
TERM_H = 720
TERM_X = (WIDTH - TERM_W) // 2   # 320
TERM_Y = (HEIGHT - TERM_H) // 2  # 180

LOFI = {
    "bg_dark": (18, 14, 32),
    "bg_gradient": (38, 30, 62),
    "accent_warm": (255, 183, 120),
    "accent_lavender": (180, 160, 220),
    "text_secondary": (160, 150, 170),
    "text_dim": (100, 90, 110),
    "border_glow": (120, 90, 180),
}

MARGIN_EMOJI = ["🍕", "🍣", "🌮", "🍜", "🥗", "🍳"]

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
    """Get Apple Color Emoji font for margin decorations."""
    apple_path = Path("/System/Library/Fonts/Apple Color Emoji.ttc")
    if apple_path.exists():
        try:
            return ImageFont.truetype(str(apple_path), size)
        except Exception:
            pass
    return None


def generate_background(output_path: str):
    """Generate the static 1920x1080 lo-fi background with terminal chrome and margin emoji."""
    img = Image.new("RGB", (WIDTH, HEIGHT), LOFI["bg_dark"])
    draw = ImageDraw.Draw(img)

    # Vertical gradient
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(lerp(LOFI["bg_dark"][0], LOFI["bg_gradient"][0], t))
        g = int(lerp(LOFI["bg_dark"][1], LOFI["bg_gradient"][1], t))
        b = int(lerp(LOFI["bg_dark"][2], LOFI["bg_gradient"][2], t))
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # Terminal chrome: multiple glow layers (outer to inner)
    glow_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    gr, gg, gb = LOFI["border_glow"]

    # Outer glow rings (decreasing alpha)
    for offset, alpha in [(8, 8), (6, 15), (4, 25), (2, 40)]:
        glow_draw.rounded_rectangle(
            [
                TERM_X - offset, TERM_Y - offset,
                TERM_X + TERM_W + offset, TERM_Y + TERM_H + offset,
            ],
            radius=12 + offset,
            outline=(gr, gg, gb, alpha),
            width=2,
        )

    # Apply slight blur to glow
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

    # Faint food emoji in margin areas
    emoji_font = _get_emoji_font(36)
    if emoji_font:
        emoji_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        emoji_draw = ImageDraw.Draw(emoji_layer)

        # Positions in the margins (avoid terminal area)
        margin_positions = [
            (80, 90),                          # top-left
            (TERM_X + TERM_W + 40, 120),       # top-right margin
            (100, HEIGHT - 80),                 # bottom-left
            (TERM_X + TERM_W + 60, HEIGHT - 100),  # bottom-right margin
            (50, HEIGHT // 2 - 30),             # left center
            (TERM_X + TERM_W + 50, HEIGHT // 2 + 40),  # right center
        ]

        random.seed(42)  # Deterministic placement
        for pos in margin_positions:
            char = random.choice(MARGIN_EMOJI)
            emoji_draw.text(pos, char, font=emoji_font, embedded_color=True)

        # Heavy blur + low alpha for dreamy faintness
        emoji_layer = emoji_layer.filter(ImageFilter.GaussianBlur(radius=4))
        r_ch, g_ch, b_ch, a_ch = emoji_layer.split()
        a_ch = a_ch.point(lambda p: int(p * 0.25))
        emoji_layer = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))
        img.paste(emoji_layer, (0, 0), emoji_layer)

    # Watermark: "FCP" in bottom-right margin
    font_wm = get_font("mono", 18)
    wr, wg, wb = LOFI["text_dim"]
    draw = ImageDraw.Draw(img)
    draw.text(
        (TERM_X + TERM_W - 40, TERM_Y + TERM_H + 12),
        "FCP",
        fill=(wr, wg, wb),
        font=font_wm,
    )

    # Section label in top-left margin
    font_label = get_font("body", 20)
    lr, lg, lb = LOFI["text_dim"]
    draw.text(
        (TERM_X, TERM_Y - 30),
        "Recipe Quest",
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


def composite(input_recording: str, output_path: str, grain: bool = True):
    """Composite the terminal recording into the lo-fi frame.

    1. Generate static background PNG
    2. Use ffmpeg filter_complex to overlay terminal + add grain + vignette
    """
    TEMP_DIR.mkdir(exist_ok=True)

    bg_path = str(TEMP_DIR / "lofi_bg.png")
    generate_background(bg_path)

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
        # Film grain via noise filter
        filter_parts.append("[vig]noise=alls=8:allf=t+u[out]")
        final_label = "[out]"
    else:
        final_label = "[vig]"
        # Rename for mapping
        filter_parts[-1] = "[comp]vignette=PI/6[out]"
        final_label = "[out]"

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", bg_path,       # Input 0: background (looped still)
        "-i", input_recording,               # Input 1: terminal recording
        "-filter_complex", filter_complex,
        "-map", final_label,
        "-map", "1:a?",                      # Pass through audio if present
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
    default_input = str(SCRIPT_DIR / "recordings" / "recipe_quest_raw.mp4")
    default_output = str(SCRIPT_DIR / "recordings" / "recipe_quest_composited.mp4")
    input_file = sys.argv[1] if len(sys.argv) > 1 else default_input
    output_file = sys.argv[2] if len(sys.argv) > 2 else default_output

    if not Path(input_file).exists():
        print(f"Input not found: {input_file}")
        print("\nRecord your terminal at 1280x720, then:")
        print(f"  python composite_terminal.py {input_file}")
        sys.exit(1)

    print(f"\nCompositing terminal recording")
    print(f"  Input:  {input_file}")
    print(f"  Output: {output_file}")
    composite(input_file, output_file)
