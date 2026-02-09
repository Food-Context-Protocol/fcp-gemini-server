#!/usr/bin/env python3
"""
Generate lo-fi style intro and outro videos with embedded audio.

Intro (6s): Warm gradient + big floating food emoji + soft bokeh + title text + lo-fi music
Outro (9s): Same cozy style + CTA text + fade to black + lo-fi music

The food emoji are the star — large, colorful, clearly visible, gently floating.
Uses Apple Color Emoji (only color emoji renderer that works with Pillow on macOS).
"""

import subprocess
import random
import math
import shutil
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from rich.console import Console

console = Console()

WIDTH = 1920
HEIGHT = 1080
FPS = 30

# ─── Warm Lo-fi Color Palette ────────────────────────────────

LOFI = {
    "bg_dark": (45, 30, 22),         # Warm brown (visible on screens)
    "bg_gradient": (70, 48, 35),     # Lighter warm brown
    "accent_warm": (255, 183, 120),  # Peach/amber
    "accent_rose": (220, 140, 130),  # Warm rose
    "accent_cream": (255, 240, 210), # Cream highlight
    "text_primary": (255, 248, 235), # Warm white
    "text_secondary": (200, 180, 155), # Warm muted
    "text_dim": (150, 125, 100),     # Warm dim
    "glow_warm": (180, 120, 60),     # Amber glow
}

# ─── Font Management ──────────────────────────────────────────

FONTS_DIR = Path(__file__).parent / "fonts"
SCRIPT_DIR = Path(__file__).parent

FONT_URLS = {
    "Inter.ttf": "https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf",
    "JetBrainsMono.ttf": "https://github.com/google/fonts/raw/main/ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",
}


def ensure_fonts():
    """Download Google Fonts if not already present."""
    FONTS_DIR.mkdir(exist_ok=True)
    for filename, url in FONT_URLS.items():
        path = FONTS_DIR / filename
        if not path.exists():
            console.print(f"  Downloading {filename}...")
            try:
                urllib.request.urlretrieve(url, path)
            except Exception as e:
                console.print(f"  [yellow]Warning: Could not download {filename}: {e}[/yellow]")


def get_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Get a font by name with fallback chain."""
    candidates = []
    if name in ("display", "body"):
        candidates = [
            FONTS_DIR / "Inter.ttf",
            Path("/System/Library/Fonts/Helvetica.ttc"),
        ]
    elif name == "mono":
        candidates = [
            FONTS_DIR / "JetBrainsMono.ttf",
            Path("/System/Library/Fonts/SFNSMono.ttf"),
            Path("/System/Library/Fonts/Monaco.ttf"),
        ]

    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                continue
    return ImageFont.load_default()


# ─── Visual Effects ───────────────────────────────────────────

def lerp(a, b, t):
    return a + (b - a) * t


# Food emoji — the stars of the show
FOOD_EMOJI = {
    "dishes": ["🍕", "🍣", "🌮", "🍜", "🍝", "🍲", "🥗", "🍱", "🫕", "🥘"],
    "ingredients": ["🥑", "🧄", "🌶️", "🍅", "🧅", "🥕", "🫑", "🌽", "🍋"],
    "kitchen": ["🔪", "🍳", "🥄", "🧂", "🫙"],
    "sweet": ["🧁", "🍰", "🍩", "🧋", "☕"],
}


def _get_emoji_font(size: int):
    """Get Apple Color Emoji — the only color emoji that renders in Pillow on macOS."""
    apple_path = Path("/System/Library/Fonts/Apple Color Emoji.ttc")
    if apple_path.exists():
        try:
            return ImageFont.truetype(str(apple_path), size)
        except Exception:
            pass
    return None


class FloatingFoodEmoji:
    """Large, colorful floating food emoji — the visual centerpiece.

    Clearly visible with no heavy blur. These are recognizable food icons
    gently drifting upward like aromas from a warm kitchen.
    """

    def __init__(self, num_emoji=40, categories=None):
        if categories is None:
            categories = ["dishes", "ingredients"]
        self.pool = []
        for cat in categories:
            self.pool.extend(FOOD_EMOJI.get(cat, []))
        if not self.pool:
            self.pool = FOOD_EMOJI["dishes"]
        self.emoji_list = []
        self.font_cache = {}
        for _ in range(num_emoji):
            self.emoji_list.append(self._new_emoji(random_y=True))

    def _get_font(self, size: int):
        if size not in self.font_cache:
            self.font_cache[size] = _get_emoji_font(size)
        return self.font_cache[size]

    def _new_emoji(self, random_y=False):
        return {
            "char": random.choice(self.pool),
            "x": random.uniform(30, WIDTH - 30),
            "y": random.uniform(30, HEIGHT - 30) if random_y else HEIGHT + random.uniform(20, 80),
            "size": random.randint(72, 109),
            "speed_y": random.uniform(-10, -25),
            "drift_offset": random.uniform(0, math.pi * 2),
            "drift_speed": random.uniform(0.2, 0.5),
            "drift_amp": random.uniform(8, 18),
        }

    def update(self, dt: float, time: float):
        for e in self.emoji_list:
            e["y"] += e["speed_y"] * dt
            e["x"] += math.sin(time * e["drift_speed"] + e["drift_offset"]) * e["drift_amp"] * dt
            if e["y"] < -120:
                new_e = self._new_emoji(random_y=False)
                e.update(new_e)

    def draw(self, img: Image.Image, time: float = 0.0):
        emoji_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        edraw = ImageDraw.Draw(emoji_layer)

        for e in self.emoji_list:
            font = self._get_font(e["size"])
            if font is None:
                continue
            edraw.text(
                (int(e["x"]), int(e["y"])),
                e["char"],
                font=font,
                embedded_color=True,
            )

        # No blur — keep emoji crisp and colorful
        # Just reduce alpha slightly so text remains readable over them
        r, g, b, a = emoji_layer.split()
        a = a.point(lambda p: int(p * 0.85))
        emoji_layer = Image.merge("RGBA", (r, g, b, a))

        img.paste(emoji_layer, (0, 0), emoji_layer)


class BokehLights:
    """Warm, soft bokeh circles — like candlelight or kitchen warmth."""

    def __init__(self, num_lights=10):
        self.lights = []
        for _ in range(num_lights):
            self.lights.append(self._new_light(random_y=True))

    def _new_light(self, random_y=False):
        colors = [
            LOFI["accent_warm"],
            LOFI["accent_cream"],
            LOFI["accent_rose"],
            (255, 200, 140),
            (240, 180, 120),
        ]
        return {
            "x": random.uniform(-80, WIDTH + 80),
            "y": random.uniform(-80, HEIGHT + 80) if random_y else HEIGHT + random.uniform(50, 200),
            "radius": random.randint(80, 180),
            "alpha": random.randint(20, 50),
            "speed_y": random.uniform(-6, -15),
            "speed_x": random.uniform(-2, 2),
            "drift_offset": random.uniform(0, math.pi * 2),
            "drift_speed": random.uniform(0.08, 0.25),
            "drift_amp": random.uniform(10, 30),
            "color": random.choice(colors),
            "pulse_speed": random.uniform(0.2, 0.6),
            "pulse_offset": random.uniform(0, math.pi * 2),
        }

    def update(self, dt: float, time: float):
        for light in self.lights:
            light["y"] += light["speed_y"] * dt
            light["x"] += light["speed_x"] * dt
            light["x"] += math.sin(time * light["drift_speed"] + light["drift_offset"]) * light["drift_amp"] * dt
            if light["y"] < -(light["radius"] * 2):
                new_light = self._new_light(random_y=False)
                light.update(new_light)

    def draw(self, img: Image.Image, time: float = 0.0):
        bokeh_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(bokeh_layer)

        for light in self.lights:
            x, y = int(light["x"]), int(light["y"])
            r = light["radius"]
            cr, cg, cb = light["color"]
            pulse = 0.7 + 0.3 * math.sin(time * light["pulse_speed"] + light["pulse_offset"])
            alpha = int(light["alpha"] * pulse)

            for ring in range(3):
                offset = ring * (r // 3)
                ring_alpha = max(1, alpha - ring * (alpha // 4))
                draw.ellipse(
                    [x - r + offset, y - r + offset, x + r - offset, y + r - offset],
                    fill=(cr, cg, cb, ring_alpha),
                )

        bokeh_layer = bokeh_layer.filter(ImageFilter.GaussianBlur(radius=25))
        img.paste(bokeh_layer, (0, 0), bokeh_layer)


def draw_gradient_background(img: Image.Image, time: float = 0.0):
    """Draw warm animated gradient — cozy dark kitchen tones."""
    draw = ImageDraw.Draw(img)
    shift = math.sin(time * 0.3) * 4
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(lerp(LOFI["bg_dark"][0], LOFI["bg_gradient"][0], t) + shift)
        g = int(lerp(LOFI["bg_dark"][1], LOFI["bg_gradient"][1], t) + shift * 0.4)
        b = int(lerp(LOFI["bg_dark"][2], LOFI["bg_gradient"][2], t) + shift * 0.2)
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))


def draw_vignette(img: Image.Image, strength: float = 0.25):
    """Soft radial vignette — gentle edge darkening."""
    vig = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(vig)
    cx, cy = WIDTH // 2, HEIGHT // 2
    max_dist = math.sqrt(cx * cx + cy * cy)

    for ring in range(25):
        t = ring / 25.0
        radius = int(max_dist * (1.0 - t * 0.5))
        alpha = int(255 * strength * (1.0 - t))
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=(0, 0, 0, max(0, min(255, alpha))),
        )

    vig = vig.filter(ImageFilter.GaussianBlur(radius=80))
    img.paste(vig, (0, 0), vig)


def mux_audio(video_path: str, audio_path: str, output_path: str):
    """Mux audio into video for preview playback."""
    if not Path(audio_path).exists():
        console.print(f"  [yellow]Audio not found: {audio_path}, skipping mux[/yellow]")
        return
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path,
        ],
        capture_output=True, check=True,
    )


# ─── Intro Generator ─────────────────────────────────────────

def generate_intro(output_dir: Path, duration: float = 6.0):
    """Generate lo-fi intro — warm food emoji floating with title + music."""
    console.print("\n[cyan]Generating lo-fi INTRO...[/cyan]")

    frames_dir = output_dir / "intro_lofi_frames"
    frames_dir.mkdir(exist_ok=True)

    total_frames = int(duration * FPS)
    dt = 1.0 / FPS

    bokeh = BokehLights(num_lights=10)
    food_emoji = FloatingFoodEmoji(num_emoji=40, categories=["dishes", "ingredients", "kitchen"])

    for frame_idx in range(total_frames):
        progress = frame_idx / max(1, total_frames - 1)
        time = frame_idx * dt

        img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))

        draw_gradient_background(img, time)

        bokeh.update(dt, time)
        bokeh.draw(img, time)

        food_emoji.update(dt, time)
        food_emoji.draw(img, time)

        draw_vignette(img, strength=0.25)

        draw = ImageDraw.Draw(img)

        # Fade from black (first 0.5s)
        if progress < 0.1:
            black_alpha = int(255 * (1.0 - progress / 0.1))
            fade = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, black_alpha))
            img.paste(fade, (0, 0), fade)
            draw = ImageDraw.Draw(img)

        # Text fade-in (starts at 10%, full by 35%)
        if progress > 0.1:
            text_alpha = min(1.0, (progress - 0.1) / 0.25)

            font_title = get_font("display", 80)
            title = "Food Context Protocol"
            bbox = draw.textbbox((0, 0), title, font=font_title)
            tw = bbox[2] - bbox[0]
            r, g, b = LOFI["text_primary"]
            draw.text(
                ((WIDTH - tw) // 2, HEIGHT // 2 - 70),
                title,
                fill=(r, g, b, int(255 * text_alpha)),
                font=font_title,
            )

            line_width = int(400 * text_alpha)
            line_x = (WIDTH - line_width) // 2
            line_y = HEIGHT // 2 + 10
            lr, lg, lb = LOFI["accent_warm"]
            draw.line(
                [(line_x, line_y), (line_x + line_width, line_y)],
                fill=(lr, lg, lb, int(200 * text_alpha)),
                width=2,
            )

            font_sub = get_font("body", 40)
            subtitle = "AI-Powered Food Intelligence"
            bbox = draw.textbbox((0, 0), subtitle, font=font_sub)
            sw = bbox[2] - bbox[0]
            sr, sg, sb = LOFI["accent_cream"]
            draw.text(
                ((WIDTH - sw) // 2, HEIGHT // 2 + 40),
                subtitle,
                fill=(sr, sg, sb, int(255 * text_alpha)),
                font=font_sub,
            )

        img.save(frames_dir / f"frame_{frame_idx:05d}.png")

        if frame_idx % 30 == 0:
            console.print(f"  Frame {frame_idx}/{total_frames}", end="\r")

    # Encode video (no audio)
    video_only = str(output_dir / "intro_lofi_noaudio.mp4")
    console.print("\n  Encoding intro...")
    subprocess.run(
        [
            "ffmpeg", "-y", "-framerate", str(FPS),
            "-i", str(frames_dir / "frame_%05d.png"),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p",
            video_only,
        ],
        check=True, capture_output=True,
    )

    shutil.rmtree(frames_dir)

    # Mux lo-fi music into intro
    final_path = str(output_dir / "intro_lofi.mp4")
    audio_path = str(SCRIPT_DIR / "music" / "lofi_intro.wav")
    mux_audio(video_only, audio_path, final_path)
    Path(video_only).unlink(missing_ok=True)

    console.print("[green]  Done: intro_lofi.mp4 (with audio)[/green]")


# ─── Outro Generator ─────────────────────────────────────────

def generate_outro(output_dir: Path, duration: float = 9.0):
    """Generate lo-fi outro — warm food emoji with CTA, fade to black + music."""
    console.print("\n[cyan]Generating lo-fi OUTRO...[/cyan]")

    frames_dir = output_dir / "outro_lofi_frames"
    frames_dir.mkdir(exist_ok=True)

    total_frames = int(duration * FPS)
    dt = 1.0 / FPS

    bokeh = BokehLights(num_lights=12)
    food_emoji = FloatingFoodEmoji(num_emoji=45, categories=["dishes", "kitchen", "sweet"])

    for frame_idx in range(total_frames):
        progress = frame_idx / max(1, total_frames - 1)
        time = frame_idx * dt

        img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))

        draw_gradient_background(img, time)

        bokeh.update(dt, time)
        bokeh.draw(img, time)

        food_emoji.update(dt, time)
        food_emoji.draw(img, time)

        draw_vignette(img, strength=0.25)

        draw = ImageDraw.Draw(img)

        # Text fade-in (starts at 5%, full by 20%)
        if progress > 0.05:
            text_alpha = min(1.0, (progress - 0.05) / 0.15)

            font_cta = get_font("display", 96)
            cta = "Try FCP today"
            bbox = draw.textbbox((0, 0), cta, font=font_cta)
            cw = bbox[2] - bbox[0]
            r, g, b = LOFI["text_primary"]
            draw.text(
                ((WIDTH - cw) // 2, HEIGHT // 2 - 140),
                cta,
                fill=(r, g, b, int(255 * text_alpha)),
                font=font_cta,
            )

            line_width = int(300 * text_alpha)
            line_x = (WIDTH - line_width) // 2
            lr, lg, lb = LOFI["accent_warm"]
            draw.line(
                [(line_x, HEIGHT // 2 - 30), (line_x + line_width, HEIGHT // 2 - 30)],
                fill=(lr, lg, lb, int(180 * text_alpha)),
                width=2,
            )

            font_url = get_font("mono", 64)
            url = "api.fcp.dev"
            bbox = draw.textbbox((0, 0), url, font=font_url)
            uw = bbox[2] - bbox[0]
            ur, ug, ub = LOFI["accent_warm"]
            draw.text(
                ((WIDTH - uw) // 2, HEIGHT // 2 + 0),
                url,
                fill=(ur, ug, ub, int(255 * text_alpha)),
                font=font_url,
            )

            font_small = get_font("mono", 30)
            github = "github.com/Food-Context-Protocol"
            bbox = draw.textbbox((0, 0), github, font=font_small)
            gw = bbox[2] - bbox[0]
            gr, gg, gb = LOFI["text_secondary"]
            draw.text(
                ((WIDTH - gw) // 2, HEIGHT // 2 + 100),
                github,
                fill=(gr, gg, gb, int(255 * text_alpha)),
                font=font_small,
            )

            font_dim = get_font("body", 28)
            gemini = "Built with Gemini API"
            bbox = draw.textbbox((0, 0), gemini, font=font_dim)
            gew = bbox[2] - bbox[0]
            dr, dg, db = LOFI["text_dim"]
            draw.text(
                ((WIDTH - gew) // 2, HEIGHT // 2 + 155),
                gemini,
                fill=(dr, dg, db, int(200 * text_alpha)),
                font=font_dim,
            )

        # Fade to black in last 1.5s
        fade_start = 1.0 - (1.5 / duration)
        if progress > fade_start:
            fade_alpha = int(255 * ((progress - fade_start) / (1.0 - fade_start)))
            fade_overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, fade_alpha))
            img.paste(fade_overlay, (0, 0), fade_overlay)

        img.save(frames_dir / f"frame_{frame_idx:05d}.png")

        if frame_idx % 30 == 0:
            console.print(f"  Frame {frame_idx}/{total_frames}", end="\r")

    # Encode video (no audio)
    video_only = str(output_dir / "outro_lofi_noaudio.mp4")
    console.print("\n  Encoding outro...")
    subprocess.run(
        [
            "ffmpeg", "-y", "-framerate", str(FPS),
            "-i", str(frames_dir / "frame_%05d.png"),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p",
            video_only,
        ],
        check=True, capture_output=True,
    )

    shutil.rmtree(frames_dir)

    # Mux lo-fi music into outro
    final_path = str(output_dir / "outro_lofi.mp4")
    audio_path = str(SCRIPT_DIR / "music" / "lofi_outro.wav")
    mux_audio(video_only, audio_path, final_path)
    Path(video_only).unlink(missing_ok=True)

    console.print("[green]  Done: outro_lofi.mp4 (with audio)[/green]")


# ─── Main ─────────────────────────────────────────────────────

if __name__ == "__main__":
    console.print("\n[bold]Lo-Fi Bookends Generator[/bold]")
    console.print("=" * 40)

    ensure_fonts()

    output_dir = Path(__file__).parent
    generate_intro(output_dir, duration=6.0)
    generate_outro(output_dir, duration=9.0)

    console.print("\n[green]Lo-fi bookends complete![/green]")
    console.print("  intro_lofi.mp4 (6s, with audio)")
    console.print("  outro_lofi.mp4 (9s, with audio)")
