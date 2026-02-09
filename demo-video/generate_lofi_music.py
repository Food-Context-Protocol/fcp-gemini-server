#!/usr/bin/env python3
"""
Generate lo-fi hip-hop soundtrack for the demo video.

Theme-aware: each FCP scenario gets a unique musical identity
(different chord progressions, BPMs, foley mixes) while sharing
the same lo-fi synth engine.

Tries Lyria RealTime first, falls back to programmatic synth.
Requires GOOGLE_API_KEY for Lyria.

Usage:
    python generate_lofi_music.py --synth-only
    python generate_lofi_music.py --synth-only --theme allergen_alert
    python generate_lofi_music.py --list-themes
"""

import asyncio
import wave
import struct
import math
import random
import os
import sys
from pathlib import Path

SAMPLE_RATE = 44100
output_dir = Path(__file__).parent / "music"
output_dir.mkdir(exist_ok=True)


# ─── Synth Primitives ────────────────────────────────────────

def sine(freq, t):
    return math.sin(2 * math.pi * freq * t)


def saw(freq, t):
    return 2.0 * ((freq * t) % 1.0) - 1.0


def square(freq, t, pw=0.5):
    return 1.0 if (freq * t) % 1.0 < pw else -1.0


def noise_val():
    return random.uniform(-1, 1)


def lfo(rate, t):
    return (sine(rate, t) + 1.0) / 2.0


def env_fade(t, duration, fade_in=0.5, fade_out=1.0):
    if t < fade_in:
        return t / fade_in
    if t > duration - fade_out:
        return max(0.0, (duration - t) / fade_out)
    return 1.0


def kick_at(t, hit_time):
    dt = t - hit_time
    if dt < 0 or dt > 0.15:
        return 0.0
    return sine(150 * math.exp(-dt * 30), dt) * math.exp(-dt * 20) * 0.6


def hat_at(t, hit_time):
    dt = t - hit_time
    if dt < 0 or dt > 0.05:
        return 0.0
    return noise_val() * math.exp(-dt * 100) * 0.15


# ─── Kitchen Foley Primitives ────────────────────────────────

def chop_at(t, hit_time):
    """Knife on cutting board — short percussive thud + noise burst."""
    dt = t - hit_time
    if dt < 0 or dt > 0.06:
        return 0.0
    thud = sine(120, dt) * math.exp(-dt * 50) * 0.3
    board = noise_val() * math.exp(-dt * 60) * 0.4
    return (thud + board) * 0.08


def sizzle_at(t, intensity=1.0):
    """Pan sizzle — continuous high-frequency noise with slow breathing."""
    breath = 0.5 + 0.5 * sine(0.25, t)
    crackle = noise_val() * 0.015 * intensity * breath
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


def data_tick_at(t, hit_time):
    """Soft digital click — for tech-themed scenarios (mcp_toolbox, etc)."""
    dt = t - hit_time
    if dt < 0 or dt > 0.03:
        return 0.0
    return sine(2200, dt) * math.exp(-dt * 120) * 0.04


def save_wav(filename: str, samples: list[float]):
    path = output_dir / filename
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        for s in samples:
            s = max(-1.0, min(1.0, s))
            wf.writeframes(struct.pack("<h", int(s * 32767)))


# ─── Lyria RealTime ──────────────────────────────────────────

MODEL = "models/lyria-realtime-exp"


async def generate_lyria_track(prompt: str, output_path: str, duration: float):
    """Generate music via Lyria RealTime WebSocket."""
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set")

    client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})
    audio_chunks: list[bytes] = []
    sample_rate = 48000
    target_bytes = int(duration * sample_rate * 2)

    async with client.aio.live.music.connect(model=MODEL) as session:
        await session.set_weighted_prompts(
            prompts=[types.WeightedPrompt(text=prompt, weight=1.0)]
        )
        collected = 0
        async for message in session.receive():
            if message.server_content and message.server_content.model_turn:
                for part in message.server_content.model_turn.parts:
                    if part.inline_data and part.inline_data.data:
                        audio_chunks.append(part.inline_data.data)
                        collected += len(part.inline_data.data)
                        if collected >= target_bytes:
                            break
            if collected >= target_bytes:
                break

    pcm_data = b"".join(audio_chunks)[:target_bytes]
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)


def try_lyria(prompt: str, output_path: str, duration: float) -> bool:
    try:
        asyncio.run(generate_lyria_track(prompt, output_path, duration))
        return True
    except Exception as e:
        print(f"    Lyria unavailable ({type(e).__name__}), using synth fallback")
        return False


# ─── Music Themes ─────────────────────────────────────────────
# Each scenario gets its own musical personality.
# Foley weights control how much kitchen ambiance vs tech sounds.

MUSIC_THEMES = {
    "recipe_quest": {
        "bpm": 75,
        "chords": [
            [261.6, 329.6, 392.0, 493.9],  # Cmaj7
            [220.0, 261.6, 329.6, 392.0],  # Am7
            [293.7, 349.2, 440.0, 523.3],  # Dm7
            [196.0, 246.9, 293.7, 349.2],  # G7
        ],
        "resolve_chords": [
            [174.6, 220.0, 261.6, 329.6],  # Fmaj7
            [164.8, 196.0, 246.9, 293.7],  # Em7
            [220.0, 261.6, 329.6, 392.0],  # Am7
            [261.6, 329.6, 392.0, 493.9],  # Cmaj7
        ],
        "pad_freqs": [130.8, 164.8, 196.0, 246.9],  # Cmaj7 voicing
        "sub_bass": 55,
        "foley": {"sizzle": 0.8, "chop": 1.0, "clink": 0.5, "stir": 1.0, "tick": 0.0},
        "lyria_hint": "cozy kitchen, warm cooking vibes",
    },
    "food_scanner": {
        "bpm": 72,
        "chords": [
            [220.0, 277.2, 329.6, 415.3],  # Amaj7
            [246.9, 293.7, 370.0, 440.0],  # Bm7
            [174.6, 220.0, 261.6, 329.6],  # Fmaj7
            [196.0, 246.9, 293.7, 392.0],  # G7
        ],
        "resolve_chords": [
            [293.7, 349.2, 440.0, 523.3],  # Dm7
            [261.6, 329.6, 392.0, 493.9],  # Cmaj7
            [174.6, 220.0, 261.6, 329.6],  # Fmaj7
            [220.0, 277.2, 329.6, 415.3],  # Amaj7
        ],
        "pad_freqs": [110.0, 138.6, 164.8, 207.7],  # Amaj7 low voicing
        "sub_bass": 55,
        "foley": {"sizzle": 0.4, "chop": 0.3, "clink": 0.8, "stir": 0.3, "tick": 0.4},
        "lyria_hint": "candlelight dinner, warm amber glow",
    },
    "meal_log": {
        "bpm": 68,
        "chords": [
            [261.6, 329.6, 392.0, 493.9],  # Cmaj7
            [174.6, 220.0, 261.6, 329.6],  # Fmaj7
            [196.0, 246.9, 293.7, 349.2],  # G7
            [164.8, 196.0, 246.9, 293.7],  # Em7
        ],
        "resolve_chords": [
            [220.0, 261.6, 329.6, 392.0],  # Am7
            [293.7, 349.2, 440.0, 523.3],  # Dm7
            [196.0, 246.9, 293.7, 349.2],  # G7
            [261.6, 329.6, 392.0, 493.9],  # Cmaj7
        ],
        "pad_freqs": [130.8, 164.8, 196.0, 246.9],
        "sub_bass": 65,
        "foley": {"sizzle": 0.5, "chop": 0.6, "clink": 0.7, "stir": 0.5, "tick": 0.0},
        "lyria_hint": "morning routine, sunrise warmth, gentle",
    },
    "allergen_alert": {
        "bpm": 80,
        "chords": [
            [220.0, 261.6, 329.6, 392.0],  # Am7
            [164.8, 196.0, 246.9, 293.7],  # Em7
            [174.6, 220.0, 261.6, 329.6],  # Fmaj7
            [196.0, 246.9, 293.7, 349.2],  # G7
        ],
        "resolve_chords": [
            [174.6, 220.0, 261.6, 329.6],  # Fmaj7
            [196.0, 246.9, 293.7, 349.2],  # G7
            [261.6, 329.6, 392.0, 493.9],  # Cmaj7
            [220.0, 261.6, 329.6, 392.0],  # Am7
        ],
        "pad_freqs": [110.0, 130.8, 164.8, 196.0],  # Am voicing
        "sub_bass": 55,
        "foley": {"sizzle": 0.3, "chop": 0.2, "clink": 0.6, "stir": 0.2, "tick": 0.6},
        "lyria_hint": "alert but calm, cool blue, careful",
    },
    "mcp_toolbox": {
        "bpm": 78,
        "chords": [
            [164.8, 196.0, 246.9, 293.7],  # Em7
            [220.0, 261.6, 329.6, 392.0],  # Am7
            [293.7, 349.2, 440.0, 523.3],  # Dm7
            [196.0, 246.9, 293.7, 349.2],  # G7
        ],
        "resolve_chords": [
            [293.7, 349.2, 440.0, 523.3],  # Dm7
            [196.0, 246.9, 293.7, 349.2],  # G7
            [261.6, 329.6, 392.0, 493.9],  # Cmaj7
            [164.8, 196.0, 246.9, 293.7],  # Em7
        ],
        "pad_freqs": [82.4, 103.8, 123.5, 146.8],  # Em low voicing
        "sub_bass": 41,
        "foley": {"sizzle": 0.2, "chop": 0.1, "clink": 0.4, "stir": 0.1, "tick": 1.0},
        "lyria_hint": "deep cosmic, technical, digital vibes",
    },
    "gemini_brain": {
        "bpm": 70,
        "chords": [
            [261.6, 329.6, 392.0, 493.9],  # Cmaj7
            [220.0, 277.2, 329.6, 415.3],  # Amaj7
            [174.6, 220.0, 261.6, 329.6],  # Fmaj7
            [196.0, 246.9, 293.7, 392.0],  # G7
        ],
        "resolve_chords": [
            [220.0, 261.6, 329.6, 392.0],  # Am7
            [174.6, 220.0, 261.6, 329.6],  # Fmaj7
            [196.0, 246.9, 293.7, 349.2],  # G7
            [261.6, 329.6, 392.0, 493.9],  # Cmaj7
        ],
        "pad_freqs": [130.8, 164.8, 196.0, 246.9],
        "sub_bass": 65,
        "foley": {"sizzle": 0.3, "chop": 0.2, "clink": 0.5, "stir": 0.3, "tick": 0.5},
        "lyria_hint": "ethereal AI, golden mystique, dreamy",
    },
}

DEFAULT_MUSIC_THEME = "recipe_quest"


def get_music_theme(name: str = None) -> dict:
    if name and name in MUSIC_THEMES:
        return MUSIC_THEMES[name]
    return MUSIC_THEMES[DEFAULT_MUSIC_THEME]


# ─── Theme-Aware Generators ──────────────────────────────────

def gen_lofi_ambient(duration: float, theme_name: str = None) -> list[float]:
    """Warm ambient pad — no drums, just chords + vinyl crackle + kitchen sizzle.

    Used for intro and outro backgrounds. Adapts pad freqs and foley from theme.
    """
    mt = get_music_theme(theme_name)
    n = int(SAMPLE_RATE * duration)
    samples = []

    pad_freqs = mt["pad_freqs"]
    foley = mt["foley"]

    for i in range(n):
        t = i / SAMPLE_RATE
        fade = env_fade(t, duration, 2.0, 1.5)

        s = 0.0

        # Warm pad with detuned pairs (chorus effect)
        for j, freq in enumerate(pad_freqs):
            wobble = 1.0 + 0.004 * sine(0.3 + j * 0.05, t)
            s += sine(freq * wobble, t) * 0.06
            s += sine(freq * 1.003 * wobble, t) * 0.04

        # Slow volume modulation (simulated filter sweep)
        s *= 0.5 + 0.5 * lfo(0.08, t)

        # Sub bass drone
        s += sine(mt["sub_bass"], t) * 0.10 * (0.7 + 0.3 * lfo(0.15, t))

        # Vinyl crackle — sparse pops
        if random.random() < 0.008:
            s += noise_val() * 0.05
        # Continuous low hiss
        s += noise_val() * 0.006

        # Kitchen ambiance — faint sizzle (scaled by theme)
        s += sizzle_at(t, intensity=0.6 * foley.get("sizzle", 0.5))

        samples.append(s * fade)

    return samples


def gen_themed_beat(duration: float, theme_name: str = None) -> list[float]:
    """Lo-fi hip-hop beat with theme-specific chords, tempo, and foley mix.

    Plays continuously under the terminal demo section.
    """
    mt = get_music_theme(theme_name)
    bpm = mt["bpm"]
    chords = mt["chords"]
    foley = mt["foley"]
    n = int(SAMPLE_RATE * duration)
    beat = 60.0 / bpm
    samples = []

    for i in range(n):
        t = i / SAMPLE_RATE
        fade = env_fade(t, duration, 1.5, 2.0)

        # Select chord (changes every 2 bars = 8 beats)
        bar = int(t / (beat * 4))
        chord_idx = bar % len(chords)
        chord = chords[chord_idx]
        bar_pos = t % (beat * 4)

        s = 0.0

        # ─── Chords (detuned sines with tape wobble) ─────
        for j, freq in enumerate(chord):
            wobble = 1.0 + 0.003 * sine(0.8 + j * 0.1, t)
            note_freq = freq * wobble
            s += sine(note_freq, t) * 0.04
            s += sine(note_freq * 1.003, t) * 0.03

        # Chord envelope: onset per bar, slow release
        chord_env = math.exp(-bar_pos * 1.5) * 0.8 + 0.2
        s *= chord_env

        # ─── Bass (sub sine, root of chord) ──────────────
        bass_freq = chord[0] / 2
        bass_wobble = 1.0 + 0.002 * sine(0.5, t)
        bass_env = math.exp(-(t % beat) * 3)
        s += sine(bass_freq * bass_wobble, t) * 0.18 * bass_env

        # ─── Drums (lazy, slightly swung) ─────────────────
        swing = 0.02
        kick_time = (t // beat) * beat + swing
        s += kick_at(t, kick_time) * 0.7

        # Snare on beats 2 and 4 (noise burst)
        snare_beat = t % (beat * 2)
        if snare_beat > beat - 0.01:
            snare_dt = snare_beat - beat
            if 0 <= snare_dt < 0.08:
                s += noise_val() * math.exp(-snare_dt * 40) * 0.12

        # Hi-hats: eighth notes, soft
        eighth = beat / 2
        s += hat_at(t, (t // eighth) * eighth) * 0.6

        # ─── Vinyl crackle ────────────────────────────────
        if random.random() < 0.005:
            s += noise_val() * 0.04
        s += noise_val() * 0.008

        # ─── Foley (theme-weighted) ──────────────────────
        s += sizzle_at(t, intensity=foley.get("sizzle", 0.5))

        bar_in_progression = bar % 2
        chop_weight = foley.get("chop", 0.5)
        if chop_weight > 0 and bar_in_progression == 0:
            chop_beat_time = (t // (beat * 4)) * (beat * 4) + beat
            s += chop_at(t, chop_beat_time) * chop_weight
            s += chop_at(t, chop_beat_time + beat * 0.5) * chop_weight

        clink_weight = foley.get("clink", 0.5)
        if clink_weight > 0 and bar % 8 == 4:
            clink_time = (t // (beat * 4 * 8)) * (beat * 4 * 8) + beat * 4 * 4
            s += plate_clink_at(t, clink_time) * clink_weight

        s += stir_at(t) * foley.get("stir", 0.5)

        # Data tick for tech themes
        tick_weight = foley.get("tick", 0.0)
        if tick_weight > 0 and bar_in_progression == 1:
            tick_time = (t // (beat * 2)) * (beat * 2) + beat * 1.5
            s += data_tick_at(t, tick_time) * tick_weight

        samples.append(s * fade * 0.85)

    return samples


def gen_themed_outro(duration: float, theme_name: str = None) -> list[float]:
    """Resolving lo-fi outro — drums fade out, chords resolve, foley fades.

    Uses theme-specific resolution chord progression.
    """
    mt = get_music_theme(theme_name)
    bpm = mt["bpm"]
    chords = mt["resolve_chords"]
    foley = mt["foley"]
    n = int(SAMPLE_RATE * duration)
    beat = 60.0 / bpm
    samples = []

    for i in range(n):
        t = i / SAMPLE_RATE
        fade = env_fade(t, duration, 0.5, 3.0)

        bar = int(t / (beat * 4))
        chord_idx = bar % len(chords)
        chord = chords[chord_idx]
        bar_pos = t % (beat * 4)

        s = 0.0

        # Chords
        for j, freq in enumerate(chord):
            wobble = 1.0 + 0.003 * sine(0.8 + j * 0.1, t)
            s += sine(freq * wobble, t) * 0.04
            s += sine(freq * 1.003 * wobble, t) * 0.03
        chord_env = math.exp(-bar_pos * 1.5) * 0.8 + 0.2
        s *= chord_env

        # Bass
        bass_freq = chord[0] / 2
        s += sine(bass_freq * (1.0 + 0.002 * sine(0.5, t)), t) * 0.15 * math.exp(-(t % beat) * 3)

        # Drums — fade out in last 3 seconds
        drum_fade = max(0.0, 1.0 - max(0.0, t - (duration - 3.0)) / 3.0)
        swing = 0.02
        kick_time = (t // beat) * beat + swing
        s += kick_at(t, kick_time) * 0.7 * drum_fade
        eighth = beat / 2
        s += hat_at(t, (t // eighth) * eighth) * 0.5 * drum_fade

        # Snare
        snare_beat = t % (beat * 2)
        if snare_beat > beat - 0.01:
            snare_dt = snare_beat - beat
            if 0 <= snare_dt < 0.08:
                s += noise_val() * math.exp(-snare_dt * 40) * 0.10 * drum_fade

        # Vinyl
        if random.random() < 0.005:
            s += noise_val() * 0.04
        s += noise_val() * 0.007

        # Kitchen foley — fading out with drums
        s += sizzle_at(t, intensity=foley.get("sizzle", 0.5) * drum_fade)
        s += stir_at(t) * foley.get("stir", 0.5) * drum_fade
        final_clink_time = duration - 2.5
        s += plate_clink_at(t, final_clink_time) * foley.get("clink", 0.5) * 1.5

        samples.append(s * fade * 0.85)

    return samples


# ─── Track Builder ────────────────────────────────────────────

def build_tracks(theme_name: str = None, demo_duration: float = 65.0) -> dict:
    """Build track definitions for a given theme."""
    mt = get_music_theme(theme_name)
    hint = mt.get("lyria_hint", "chill lo-fi")

    return {
        "lofi_intro": {
            "lyria_prompt": f"lo-fi ambient pad, warm jazzy chords, vinyl crackle, {hint}, no drums, mellow, tape hiss",
            "duration": 8.0,
            "synth_fn": lambda: gen_lofi_ambient(8.0, theme_name),
        },
        "lofi_recipe_quest": {
            "lyria_prompt": f"lo-fi hip hop beat, {mt['bpm']}bpm, jazzy chords, warm sub bass, vinyl crackle, {hint}, mellow lazy drums, tape wobble",
            "duration": demo_duration,
            "synth_fn": lambda: gen_themed_beat(demo_duration, theme_name),
        },
        "lofi_outro": {
            "lyria_prompt": f"lo-fi hip hop outro, {mt['bpm']}bpm, resolving warm jazz chords, drums fading out, {hint}, vinyl crackle, peaceful ending",
            "duration": 12.0,
            "synth_fn": lambda: gen_themed_outro(12.0, theme_name),
        },
    }


# ─── Main ─────────────────────────────────────────────────────

if __name__ == "__main__":
    use_lyria = "--synth-only" not in sys.argv

    # Parse theme
    theme_name = None
    for i, a in enumerate(sys.argv[1:]):
        if a == "--theme" and i + 2 < len(sys.argv):
            theme_name = sys.argv[i + 2]
        if a == "--list-themes":
            print("Available music themes:")
            for key, mt in MUSIC_THEMES.items():
                marker = " (default)" if key == DEFAULT_MUSIC_THEME else ""
                print(f"  {key:20s} — {mt['bpm']}bpm, {mt['lyria_hint']}{marker}")
            sys.exit(0)

    lyria_available = None
    tracks = build_tracks(theme_name)
    mt = get_music_theme(theme_name)

    print(f"\nGenerating lo-fi soundtrack [{theme_name or DEFAULT_MUSIC_THEME}]")
    print(f"  BPM: {mt['bpm']}, Foley: {mt['foley']}")
    if use_lyria:
        print("  Attempting Lyria RealTime (falls back to synth)\n")
    else:
        print("  Synth-only mode\n")

    for name, track in tracks.items():
        filename = f"{name}.wav"
        filepath = str(output_dir / filename)
        print(f"  [{name}] ({track['duration']}s)")

        used_lyria = False
        if use_lyria and lyria_available is not False:
            used_lyria = try_lyria(track["lyria_prompt"], filepath, track["duration"])
            if lyria_available is None:
                lyria_available = used_lyria
                if not used_lyria:
                    print("    (Lyria not available -- all tracks will use synth)")

        if not used_lyria:
            samples = track["synth_fn"]()
            save_wav(filename, samples)

        source = "Lyria" if used_lyria else "synth"
        print(f"  Done: {filename} ({source})")

    print(f"\nSoundtrack complete! Files in {output_dir}/")
