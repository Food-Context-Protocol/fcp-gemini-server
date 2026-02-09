# Lo-Fi Food Emoji + Kitchen Soundscape Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add floating food emoji visuals to the lo-fi video backgrounds and weave kitchen/restaurant foley (chopping, sizzling, dishing) into the lo-fi music tracks, creating a cohesive food-themed atmosphere.

**Architecture:** Two parallel tracks of work: (1) a `FloatingFoodEmoji` visual effects class in the bookends generator using Apple Color Emoji (the only color emoji renderer that works with Pillow on macOS), and (2) new kitchen foley synthesizers added to the music generator that layer restaurant ambiance underneath the jazz chords. Both integrate into the existing pipeline without changing the assembly script.

**Tech Stack:** Pillow (Apple Color Emoji via `/System/Library/Fonts/Apple Color Emoji.ttc`), programmatic audio synthesis (same primitives as `generate_lofi_music.py`), ffmpeg for encoding.

---

## Design: Visual Layer — Floating Food Emoji

### The Problem
The current bookends have soft bokeh lights and film grain but no food personality. The user wants floating food emoji that feel lo-fi (soft, dreamy, slow-drifting) rather than game-y (hard-edged, bouncing, pixelated).

### Emoji Font Constraint
- **Noto Color Emoji** (`NotoColorEmoji-Regular.ttf`): CBDT bitmap format, **does not render in Pillow** — produces invisible output.
- **Apple Color Emoji** (`/System/Library/Fonts/Apple Color Emoji.ttc`): **Works perfectly** with `embedded_color=True`. macOS-only, but we're generating locally.
- Fallback: If Apple Color Emoji is missing, skip emoji layer gracefully (bokeh still provides ambient movement).

### Emoji Catalog — Curated for Food/Restaurant/Kitchen Vibes

```python
FOOD_EMOJI = {
    # Dishes & meals (the "main characters")
    "dishes": ['🍕', '🍣', '🌮', '🍜', '🍝', '🍲', '🥗', '🍱', '🫕', '🥘'],
    # Ingredients (supporting cast)
    "ingredients": ['🥑', '🧄', '🌶️', '🍅', '🧅', '🥕', '🫑', '🌽', '🍋'],
    # Kitchen tools (restaurant/chef vibe)
    "kitchen": ['🔪', '🍳', '🥄', '🧂', '🫙'],
    # Desserts & drinks (sweet accents)
    "sweet": ['🧁', '🍰', '🍩', '🧋', '☕'],
}
```

**Intro** uses mostly dishes + ingredients (establishing "food intelligence").
**Outro** uses dishes + kitchen + sweet (restaurant wrap-up vibe).
**Composite terminal** uses a sparse selection in the margin areas only (not over the terminal).

### Visual Treatment — "Dreamy Kitchen Window"

Each emoji is rendered to a separate RGBA layer, then the entire layer is:
1. **Gaussian blurred** at radius 2-4 (soft/dreamy, not crisp)
2. **Alpha reduced** to 30-50% (transparent, not in-your-face)
3. **Composited** between the bokeh layer and the vignette (so vignette darkens edges, emoji fade at borders)

### Animation Behavior

Each emoji particle has:
- **Slow upward drift** (speed_y: -5 to -15 px/s) — like steam rising from a kitchen
- **Gentle horizontal sine wave** (amplitude 10-25px, period 3-8s) — lazy swaying
- **Slow rotation** (not implemented in Pillow natively — we'll skip rotation, the drift is enough)
- **Size variation**: 36-72pt, randomly assigned at spawn
- **Alpha pulse**: gentle 0.7-1.0 breathing at 0.2-0.5 Hz
- **Respawn**: when an emoji drifts above the top edge, it respawns at bottom with a new random emoji

Count: ~15-18 emoji on screen at once. Dense enough to notice, sparse enough to not distract from text.

### Layer Order (back to front)
1. Gradient background (breathing color shift)
2. Bokeh lights (8 lights, reduced from 12 — emoji replaces some visual density)
3. **Floating food emoji** (new)
4. Vignette (radial edge darkening)
5. Film grain (soft organic noise)
6. Text (title, subtitle, CTA)
7. Fade overlays (black fade-in / fade-out)

---

## Design: Audio Layer — Kitchen Foley in the Lo-Fi Mix

### The Concept
Real lo-fi "cooking" videos layer ambient kitchen sounds under the music: a knife on a cutting board, oil sizzling in a pan, a plate being set down, a spoon stirring. These become rhythmic texture — like vinyl crackle but food-themed.

### New Synth Foley Functions

All synthesized from noise + filtered envelopes (same approach as the existing synth primitives):

#### 1. `chop_at(t, hit_time)` — Knife on cutting board
- Short burst of bandpass-filtered noise (200-800 Hz)
- Fast attack (2ms), quick decay (40ms)
- Slight "thud" component: low sine at 120Hz, 20ms decay
- Sounds like: *tok tok tok* — rhythmic chopping

#### 2. `sizzle(t, intensity)` — Oil/pan sizzle
- Continuous high-frequency noise (2kHz+) with slow amplitude modulation
- Intensity varies 0.0-1.0 via slow LFO (breathes in and out over ~4s)
- Very low volume (0.02-0.04) — background texture, not foreground
- Sounds like: *shhhh* with crackle — a pan on low heat

#### 3. `plate_clink(t, hit_time)` — Dish/glass clink
- High-frequency sine (1200-2000 Hz) with fast exponential decay
- Two detuned sines for metallic/ceramic quality
- Very short (80ms total)
- Sounds like: *ting* — a plate being set down

#### 4. `stir_loop(t)` — Wooden spoon in a pot
- Slow-period filtered noise sweep (0.5-1.0 Hz cycle)
- Bandpass centered around 400Hz, narrow Q
- Very subtle volume (0.01-0.02)
- Sounds like: soft rhythmic *swish swish*

### Where Kitchen Sounds Go

| Track | Kitchen Foley | Timing |
|-------|--------------|--------|
| `lofi_intro` (ambient pad) | Light sizzle only, very faint | Continuous, fading in/out with LFO |
| `lofi_recipe_quest` (main beat) | Chops on beat 2 (every 2 bars), sizzle continuous, plate clink every 8 bars, stir loop continuous | Rhythmic — chops sync to the drum pattern |
| `lofi_outro` (resolving) | Sizzle fading out with drums, one final plate clink at the end | Fading with the beat |

### Mixing Levels
Kitchen foley sits *underneath* everything — quieter than vinyl crackle:
- Sizzle: 0.02-0.04 amplitude (vs vinyl crackle at 0.04-0.05)
- Chops: 0.06-0.08 amplitude (percussive hits cut through briefly)
- Plate clink: 0.04 amplitude (sparse accent)
- Stir: 0.01-0.02 amplitude (barely there)

### Lyria Prompt Updates
Update the Lyria prompts to include food ambiance keywords for when Lyria is available:

```python
"lofi_intro": "lo-fi ambient pad, warm jazzy chords, vinyl crackle, kitchen ambiance, gentle sizzle, no drums, mellow, chill cooking vibes, tape hiss"
"lofi_recipe_quest": "lo-fi hip hop beat, 75bpm, jazzy piano chords, warm sub bass, vinyl crackle, kitchen sounds, chopping rhythm, chill cooking music, mellow lazy drums, tape wobble"
"lofi_outro": "lo-fi hip hop outro, 75bpm, resolving warm jazz chords, drums fading out, kitchen ambiance fading, vinyl crackle, peaceful ending, tape hiss"
```

---

## Design: Composite Terminal — Margin Emoji

The composited terminal view (1920x1080 with 1280x720 terminal centered) has dark margin space. We'll add a few static (non-animated) food emoji in the margins — very faint, like decorations on a restaurant wall.

- 4-6 emoji placed in the margin areas (corners, sides)
- Baked into the static background PNG (not animated — avoids frame-by-frame processing for 50+ seconds of footage)
- Very low alpha (20-30%) and gaussian blur (radius 4)
- Uses Apple Color Emoji, same font fallback pattern

---

## Tasks

### Task 1: Add `FloatingFoodEmoji` class to bookends generator

**Files:**
- Modify: `demo-video/generate_lofi_bookends.py:101-242` (Visual Effects section)

**Step 1: Write the FloatingFoodEmoji class**

Add after the `BokehLights` class (after line 178), before `FilmGrain`:

```python
FOOD_EMOJI = {
    "dishes": ['🍕', '🍣', '🌮', '🍜', '🍝', '🍲', '🥗', '🍱', '🫕', '🥘'],
    "ingredients": ['🥑', '🧄', '🌶️', '🍅', '🧅', '🥕', '🫑', '🌽', '🍋'],
    "kitchen": ['🔪', '🍳', '🥄', '🧂', '🫙'],
    "sweet": ['🧁', '🍰', '🍩', '🧋', '☕'],
}


def _get_emoji_font(size: int):
    """Get Apple Color Emoji font (the only color emoji Pillow can render on macOS)."""
    apple_path = Path("/System/Library/Fonts/Apple Color Emoji.ttc")
    if apple_path.exists():
        try:
            return ImageFont.truetype(str(apple_path), size)
        except Exception:
            pass
    return None


class FloatingFoodEmoji:
    """Soft, dreamy floating food emoji — like steam rising from a kitchen.

    Rendered with gaussian blur and reduced alpha for lo-fi warmth.
    Uses Apple Color Emoji (Noto Color Emoji doesn't render in Pillow).
    """

    def __init__(self, num_emoji=16, categories=None):
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
            "x": random.uniform(60, WIDTH - 60),
            "y": random.uniform(60, HEIGHT - 60) if random_y else HEIGHT + random.uniform(30, 120),
            "size": random.randint(36, 72),
            "alpha_base": random.uniform(0.30, 0.50),
            "speed_y": random.uniform(-5, -15),
            "drift_offset": random.uniform(0, math.pi * 2),
            "drift_speed": random.uniform(0.15, 0.35),
            "drift_amp": random.uniform(10, 25),
            "pulse_speed": random.uniform(0.2, 0.5),
            "pulse_offset": random.uniform(0, math.pi * 2),
        }

    def update(self, dt: float, time: float):
        for e in self.emoji_list:
            e["y"] += e["speed_y"] * dt
            e["x"] += math.sin(time * e["drift_speed"] + e["drift_offset"]) * e["drift_amp"] * dt
            if e["y"] < -80:
                new_e = self._new_emoji(random_y=False)
                e.update(new_e)

    def draw(self, img: Image.Image, time: float = 0.0):
        emoji_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        edraw = ImageDraw.Draw(emoji_layer)

        for e in self.emoji_list:
            font = self._get_font(e["size"])
            if font is None:
                continue
            pulse = 0.7 + 0.3 * math.sin(time * e["pulse_speed"] + e["pulse_offset"])
            edraw.text(
                (int(e["x"]), int(e["y"])),
                e["char"],
                font=font,
                embedded_color=True,
            )

        # Soft blur for dreamy look
        emoji_layer = emoji_layer.filter(ImageFilter.GaussianBlur(radius=3))

        # Reduce alpha globally
        r, g, b, a = emoji_layer.split()
        # Apply per-emoji pulse via global alpha scaling (approximation — good enough)
        avg_alpha = 0.38
        a = a.point(lambda p: int(p * avg_alpha))
        emoji_layer = Image.merge("RGBA", (r, g, b, a))

        img.paste(emoji_layer, (0, 0), emoji_layer)
```

**Step 2: Run a quick render test**

Run:
```bash
uv run python -c "
import sys; sys.path.insert(0, 'demo-video')
from generate_lofi_bookends import *
ensure_fonts()
img = Image.new('RGB', (WIDTH, HEIGHT), (0, 0, 0))
draw_gradient_background(img, 2.0)
emoji_fx = FloatingFoodEmoji(num_emoji=16, categories=['dishes', 'ingredients'])
for i in range(60): emoji_fx.update(1/30, i/30)
emoji_fx.draw(img, 2.0)
draw_vignette(img, 0.3)
img.save('demo-video/emoji_test_class.png')
print('Saved')
"
```

Expected: PNG with soft, blurred food emoji floating over dark gradient.

**Step 3: Commit**

```bash
git add demo-video/generate_lofi_bookends.py
git commit -m "feat: add FloatingFoodEmoji class with Apple Color Emoji rendering"
```

---

### Task 2: Wire FloatingFoodEmoji into intro and outro generators

**Files:**
- Modify: `demo-video/generate_lofi_bookends.py:246-260` (generate_intro)
- Modify: `demo-video/generate_lofi_bookends.py:362-382` (generate_outro)

**Step 1: Update generate_intro to add emoji layer**

In `generate_intro()`, after the BokehLights init and before the frame loop, add emoji init. In the frame loop, add emoji update/draw between bokeh and vignette:

```python
# In generate_intro():
bokeh = BokehLights(num_lights=8)  # Reduced from 12 — emoji adds density
grain = FilmGrain(intensity=15, density=0.15)
food_emoji = FloatingFoodEmoji(num_emoji=16, categories=["dishes", "ingredients"])

# Inside frame loop, after bokeh.draw and before draw_vignette:
food_emoji.update(dt, time)
food_emoji.draw(img, time)
```

**Step 2: Update generate_outro to add emoji layer**

Same pattern but with different categories for restaurant wrap-up feel:

```python
# In generate_outro():
bokeh = BokehLights(num_lights=10)  # Reduced from 15
grain = FilmGrain(intensity=15, density=0.15)
food_emoji = FloatingFoodEmoji(num_emoji=18, categories=["dishes", "kitchen", "sweet"])

# Inside frame loop, same position as intro:
food_emoji.update(dt, time)
food_emoji.draw(img, time)
```

**Step 3: Run generate_lofi_bookends.py and verify output**

Run:
```bash
uv run python demo-video/generate_lofi_bookends.py
```

Expected: `intro_lofi.mp4` (5s) and `outro_lofi.mp4` (8s) with visible soft food emoji drifting upward.

**Step 4: Visually inspect a frame**

Run:
```bash
ffmpeg -y -i demo-video/intro_lofi.mp4 -vf "select=eq(n\,45)" -frames:v 1 demo-video/intro_frame_check.png
```

Expected: Frame 45 (1.5s in) shows gradient + bokeh + blurred food emoji + text fading in.

**Step 5: Commit**

```bash
git add demo-video/generate_lofi_bookends.py
git commit -m "feat: wire floating food emoji into intro and outro bookends"
```

---

### Task 3: Add kitchen foley synthesizers to music generator

**Files:**
- Modify: `demo-video/generate_lofi_music.py:58-70` (after hat_at, before save_wav)

**Step 1: Add four kitchen foley functions**

Add after `hat_at()` (line 70), before `save_wav()`:

```python
def chop_at(t, hit_time):
    """Knife on cutting board — short percussive thud + noise burst."""
    dt = t - hit_time
    if dt < 0 or dt > 0.06:
        return 0.0
    # Thud component (low sine)
    thud = sine(120, dt) * math.exp(-dt * 50) * 0.3
    # Board noise (bandpass approximation — shaped noise)
    board = noise_val() * math.exp(-dt * 60) * 0.4
    return (thud + board) * 0.08


def sizzle_at(t, intensity=1.0):
    """Pan sizzle — continuous high-frequency noise with slow breathing."""
    # High-freq noise shaped by slow LFO
    breath = 0.5 + 0.5 * sine(0.25, t)
    crackle = noise_val() * 0.015 * intensity * breath
    # Occasional louder pop
    if random.random() < 0.003 * intensity:
        crackle += noise_val() * 0.03
    return crackle


def plate_clink_at(t, hit_time):
    """Ceramic plate clink — two detuned high sines with fast decay."""
    dt = t - hit_time
    if dt < 0 or dt > 0.12:
        return 0.0
    s = sine(1400, dt) * math.exp(-dt * 45) * 0.5
    s += sine(1650, dt) * math.exp(-dt * 50) * 0.3
    return s * 0.04


def stir_at(t):
    """Wooden spoon stirring — slow-cycle filtered noise."""
    cycle = sine(0.7, t)
    if abs(cycle) < 0.3:
        return 0.0
    return noise_val() * abs(cycle) * 0.012
```

**Step 2: Run a quick audio test**

Run:
```bash
uv run python -c "
import sys; sys.path.insert(0, 'demo-video')
from generate_lofi_music import *
# Quick 2-second test of chop sound
samples = []
for i in range(SAMPLE_RATE * 2):
    t = i / SAMPLE_RATE
    s = chop_at(t, 0.5) + chop_at(t, 1.0) + chop_at(t, 1.5)
    s += sizzle_at(t, 0.8)
    samples.append(s)
save_wav('test_kitchen.wav', samples)
print('Saved music/test_kitchen.wav')
"
```

Expected: WAV file with audible chop sounds at 0.5s intervals over continuous sizzle.

**Step 3: Commit**

```bash
git add demo-video/generate_lofi_music.py
git commit -m "feat: add kitchen foley synthesizers (chop, sizzle, clink, stir)"
```

---

### Task 4: Mix kitchen foley into the three lo-fi music tracks

**Files:**
- Modify: `demo-video/generate_lofi_music.py:137-174` (gen_lofi_ambient)
- Modify: `demo-video/generate_lofi_music.py:177-246` (gen_lofi_beat)
- Modify: `demo-video/generate_lofi_music.py:249-311` (gen_lofi_outro)

**Step 1: Add sizzle to gen_lofi_ambient (intro/outro pad)**

After the vinyl crackle section (~line 170), add:
```python
        # Kitchen ambiance — faint sizzle
        s += sizzle_at(t, intensity=0.6)
```

**Step 2: Add full kitchen foley to gen_lofi_beat (main demo track)**

After the vinyl crackle section (~line 242), add:
```python
        # ─── Kitchen foley (food ambiance) ───────────────
        # Continuous sizzle (background)
        s += sizzle_at(t, intensity=0.8)

        # Chops on beat 2 of every other bar (synced to rhythm)
        bar_in_progression = bar % 2
        if bar_in_progression == 0:
            chop_beat_time = (t // (beat * 4)) * (beat * 4) + beat  # beat 2
            s += chop_at(t, chop_beat_time)
            s += chop_at(t, chop_beat_time + beat * 0.5)  # and the "and" of 2

        # Plate clink every 8 bars (sparse accent)
        if bar % 8 == 4:
            clink_time = (t // (beat * 4 * 8)) * (beat * 4 * 8) + beat * 4 * 4
            s += plate_clink_at(t, clink_time)

        # Continuous stir (very subtle)
        s += stir_at(t)
```

**Step 3: Add fading foley to gen_lofi_outro**

After the vinyl section (~line 307), add:
```python
        # Kitchen foley — fading out with drums
        s += sizzle_at(t, intensity=0.6 * drum_fade)
        s += stir_at(t) * drum_fade

        # Final plate clink near the end (resolution moment)
        final_clink_time = duration - 2.5
        s += plate_clink_at(t, final_clink_time) * 1.5
```

**Step 4: Update Lyria prompts**

Update the TRACKS dict lyria_prompts:
```python
"lofi_intro": {
    "lyria_prompt": "lo-fi ambient pad, warm jazzy chords, vinyl crackle, kitchen ambiance, gentle sizzle, no drums, mellow, chill cooking vibes, tape hiss",
    ...
},
"lofi_recipe_quest": {
    "lyria_prompt": "lo-fi hip hop beat, 75bpm, jazzy piano chords, warm sub bass, vinyl crackle, kitchen sounds, chopping rhythm, chill cooking music, mellow lazy drums, tape wobble",
    ...
},
"lofi_outro": {
    "lyria_prompt": "lo-fi hip hop outro, 75bpm, resolving warm jazz chords, drums fading out, kitchen ambiance fading, vinyl crackle, peaceful ending, tape hiss",
    ...
},
```

**Step 5: Regenerate all music tracks**

Run:
```bash
uv run python demo-video/generate_lofi_music.py --synth-only
```

Expected: 3 WAV files in `music/` with audible (but subtle) kitchen ambiance underneath the lo-fi beats.

**Step 6: Listen and verify**

Play the recipe quest track and confirm:
- Sizzle is audible but not overpowering
- Chop hits are rhythmic and blend with drums
- Plate clink appears as a sparse accent
- Stir is barely perceptible (felt more than heard)

**Step 7: Commit**

```bash
git add demo-video/generate_lofi_music.py
git commit -m "feat: mix kitchen foley (sizzle, chop, clink, stir) into lo-fi tracks"
```

---

### Task 5: Add static margin emoji to composite_terminal.py

**Files:**
- Modify: `demo-video/composite_terminal.py:67-134` (generate_background)

**Step 1: Add margin emoji to the static background**

After the section label text (~line 131) and before `img.save()`, add:

```python
    # Margin food emoji — faint decorations like a restaurant wall
    apple_emoji = Path("/System/Library/Fonts/Apple Color Emoji.ttc")
    if apple_emoji.exists():
        try:
            margin_emoji = ['🍕', '🥑', '🍣', '🌮', '🧁', '☕']
            emoji_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            emoji_draw = ImageDraw.Draw(emoji_layer)

            # Place in margin corners and sides (outside terminal area)
            positions = [
                (80, 80, 48),       # top-left
                (WIDTH - 130, 80, 42),  # top-right
                (60, HEIGHT - 100, 44),  # bottom-left
                (WIDTH - 120, HEIGHT - 90, 40),  # bottom-right
                (160, HEIGHT // 2 - 20, 36),  # mid-left
                (WIDTH - 100, HEIGHT // 2 + 30, 38),  # mid-right
            ]
            for i, (ex, ey, esize) in enumerate(positions):
                emoji_char = margin_emoji[i % len(margin_emoji)]
                efont = ImageFont.truetype(str(apple_emoji), esize)
                emoji_draw.text((ex, ey), emoji_char, font=efont, embedded_color=True)

            # Heavy blur + very low alpha for subtle background decoration
            emoji_layer = emoji_layer.filter(ImageFilter.GaussianBlur(radius=4))
            r, g, b, a = emoji_layer.split()
            a = a.point(lambda p: int(p * 0.25))
            emoji_layer = Image.merge("RGBA", (r, g, b, a))
            img.paste(emoji_layer, (0, 0), emoji_layer)
        except Exception:
            pass  # Skip if emoji rendering fails
```

**Step 2: Add ImageFilter import if missing**

Check that `ImageFilter` is in the import line (it already is at line 16).

**Step 3: Regenerate composited recording (if raw recording exists)**

Run:
```bash
ls demo-video/recordings/recipe_quest_raw.mp4 && uv run python demo-video/composite_terminal.py || echo "No raw recording yet — will composite when available"
```

**Step 4: Commit**

```bash
git add demo-video/composite_terminal.py
git commit -m "feat: add faint food emoji decorations in composite terminal margins"
```

---

### Task 6: Replace old SFX with kitchen-themed sounds

**Files:**
- Modify: `demo-video/generate_sfx.py` (replace game SFX with kitchen foley)

**Step 1: Replace the SFX generators**

The current SFX are game-themed (level_hit, power_up, chomp). Replace with lo-fi kitchen versions that can optionally be mixed into the assembly:

Replace the `SFX_MAP` and generators:

```python
SFX_MAP = {
    "knife_chop": ("sfx_knife_chop.wav", gen_knife_chop),
    "pan_sizzle": ("sfx_pan_sizzle.wav", gen_pan_sizzle),
    "plate_set": ("sfx_plate_set.wav", gen_plate_set),
    "pour_water": ("sfx_pour_water.wav", gen_pour_water),
    "pot_stir": ("sfx_pot_stir.wav", gen_pot_stir),
    "data_tick": ("sfx_data_tick.wav", gen_data_tick),  # Keep — useful for terminal
}
```

New generator functions:

```python
def gen_knife_chop(duration: float = 1.5) -> list[float]:
    """Rhythmic knife chopping on a cutting board — 4 chops."""
    samples = []
    n = int(SAMPLE_RATE * duration)
    chop_times = [0.1, 0.4, 0.7, 1.0]
    for i in range(n):
        t = i / SAMPLE_RATE
        s = 0.0
        for ct in chop_times:
            dt = t - ct
            if 0 <= dt < 0.06:
                s += sine(120, dt) * math.exp(-dt * 50) * 0.3
                s += noise() * math.exp(-dt * 60) * 0.5
        s *= envelope(t, 0.01, duration - 0.2, 0.19)
        samples.append(s * 0.7)
    return samples


def gen_pan_sizzle(duration: float = 3.0) -> list[float]:
    """Continuous pan sizzle with slow intensity breathing."""
    samples = []
    n = int(SAMPLE_RATE * duration)
    for i in range(n):
        t = i / SAMPLE_RATE
        breath = 0.5 + 0.5 * sine(0.3, t)
        s = noise() * breath * 0.25
        if random.random() < 0.01:
            s += noise() * 0.4  # pop
        s *= envelope(t, 0.3, duration - 0.8, 0.5)
        samples.append(s)
    return samples


def gen_plate_set(duration: float = 0.5) -> list[float]:
    """Ceramic plate being set down — brief high clink."""
    samples = []
    n = int(SAMPLE_RATE * duration)
    for i in range(n):
        t = i / SAMPLE_RATE
        s = sine(1400, t) * math.exp(-t * 40) * 0.5
        s += sine(1650, t) * math.exp(-t * 45) * 0.3
        s += sine(800, t) * math.exp(-t * 25) * 0.2  # body resonance
        s *= envelope(t, 0.002, 0.1, 0.39)
        samples.append(s * 0.6)
    return samples


def gen_pour_water(duration: float = 2.0) -> list[float]:
    """Water pouring — rising filtered noise."""
    samples = []
    n = int(SAMPLE_RATE * duration)
    for i in range(n):
        t = i / SAMPLE_RATE
        # Rising intensity
        intensity = min(1.0, t / 0.5) * envelope(t, 0.3, duration - 0.7, 0.4)
        s = noise() * intensity * 0.2
        # Bubbling — periodic amplitude modulation
        bubble = 0.5 + 0.5 * sine(12 + sine(0.5, t) * 4, t)
        s *= bubble
        samples.append(s)
    return samples


def gen_pot_stir(duration: float = 3.0) -> list[float]:
    """Wooden spoon stirring in a pot — rhythmic swoosh."""
    samples = []
    n = int(SAMPLE_RATE * duration)
    stir_rate = 0.8  # Hz
    for i in range(n):
        t = i / SAMPLE_RATE
        cycle = sine(stir_rate, t)
        if abs(cycle) > 0.3:
            s = noise() * abs(cycle) * 0.15
        else:
            s = 0.0
        s *= envelope(t, 0.2, duration - 0.5, 0.3)
        samples.append(s)
    return samples
```

**Step 2: Update script description**

Change the module docstring from "retro game-style" to "kitchen-themed lo-fi".

**Step 3: Fix the output_dir path (it currently uses relative `Path("sfx")`)**

Change line 14 to:
```python
output_dir = Path(__file__).parent / "sfx"
```

**Step 4: Run the generator**

Run:
```bash
uv run python demo-video/generate_sfx.py
```

Expected: New kitchen SFX files in `sfx/`.

**Step 5: Commit**

```bash
git add demo-video/generate_sfx.py
git commit -m "feat: replace game SFX with kitchen-themed lo-fi foley"
```

---

### Task 7: Clean up old game SFX files

**Files:**
- Delete: `demo-video/sfx/sfx_level_hit.wav`
- Delete: `demo-video/sfx/sfx_power_up.wav`
- Delete: `demo-video/sfx/sfx_chomp.wav`
- Delete: `demo-video/sfx/sfx_warning_buzzer.wav`
- Delete: `demo-video/sfx/sfx_synth_hum.wav`

**Step 1: Remove old game SFX**

Run:
```bash
rm demo-video/sfx/sfx_level_hit.wav demo-video/sfx/sfx_power_up.wav demo-video/sfx/sfx_chomp.wav demo-video/sfx/sfx_warning_buzzer.wav demo-video/sfx/sfx_synth_hum.wav
```

**Step 2: Verify only kitchen + data_tick SFX remain**

Run:
```bash
ls demo-video/sfx/
```

Expected: `sfx_knife_chop.wav`, `sfx_pan_sizzle.wav`, `sfx_plate_set.wav`, `sfx_pour_water.wav`, `sfx_pot_stir.wav`, `sfx_data_tick.wav`

**Step 3: Commit**

```bash
git add -A demo-video/sfx/
git commit -m "chore: remove old game-themed SFX"
```

---

### Task 8: Regenerate everything and test full assembly

**Files:**
- No new modifications — just running the pipeline

**Step 1: Regenerate bookends**

Run:
```bash
uv run python demo-video/generate_lofi_bookends.py
```

Expected: `intro_lofi.mp4` and `outro_lofi.mp4` with floating food emoji visible.

**Step 2: Regenerate music**

Run:
```bash
uv run python demo-video/generate_lofi_music.py --synth-only
```

Expected: 3 WAV files in `music/` with subtle kitchen ambiance.

**Step 3: Assemble (intro + outro only, no terminal recording yet)**

Run:
```bash
uv run python demo-video/assemble_lofi.py
```

Expected: `fcp_demo_lofi.mp4` assembled from available segments.

**Step 4: Verify output**

Run:
```bash
ffprobe -v error -show_entries format=duration -show_entries stream=width,height,codec_name -of default=noprint_wrappers=1 demo-video/fcp_demo_lofi.mp4
```

Expected: H.264, 1920x1080, duration ~12s (5s intro + 8s outro - 1s crossfade).

**Step 5: Commit**

```bash
git add demo-video/intro_lofi.mp4 demo-video/outro_lofi.mp4 demo-video/music/
git commit -m "chore: regenerate bookends and music with food emoji + kitchen foley"
```

---

## Verification Checklist

- [ ] Floating food emoji visible in intro and outro, drifting softly upward
- [ ] Emoji are blurred and semi-transparent (dreamy, not crisp/game-y)
- [ ] Emoji don't overlap title text badly (they drift behind it)
- [ ] Bokeh lights still visible (reduced count, complementing emoji)
- [ ] Kitchen sizzle audible in music (subtle, below vinyl crackle level)
- [ ] Chop hits rhythmic in main beat track (every other bar on beat 2)
- [ ] Plate clink sparse and pleasant (not jarring)
- [ ] Margin emoji visible in composite terminal background (very faint)
- [ ] No Apple Color Emoji errors on systems where it's not available (graceful fallback)
- [ ] Full assembly produces valid MP4 under 3 minutes
