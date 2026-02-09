#!/usr/bin/env python3
"""
Kitchen-themed lo-fi sound effects for the demo video.
Pure numpy + wave synthesis — no API keys needed.
"""

import wave
import struct
import math
import random
from pathlib import Path

SAMPLE_RATE = 44100
output_dir = Path(__file__).parent / "sfx"
output_dir.mkdir(exist_ok=True)


def save_wav(filename: str, samples: list[float], rate: int = SAMPLE_RATE):
    """Save float samples (-1.0 to 1.0) as 16-bit WAV."""
    path = output_dir / filename
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        for s in samples:
            s = max(-1.0, min(1.0, s))
            wf.writeframes(struct.pack("<h", int(s * 32767)))
    print(f"  {path}")


def sine(freq: float, t: float) -> float:
    return math.sin(2 * math.pi * freq * t)


def noise() -> float:
    return random.uniform(-1, 1)


def envelope(t: float, attack: float, sustain: float, release: float) -> float:
    """Simple ASR envelope."""
    total = attack + sustain + release
    if t < 0 or t > total:
        return 0.0
    if t < attack:
        return t / attack
    if t < attack + sustain:
        return 1.0
    return 1.0 - (t - attack - sustain) / release


# ─── SFX Generators ──────────────────────────────────────────


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
            s += noise() * 0.4
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
        s += sine(800, t) * math.exp(-t * 25) * 0.2
        s *= envelope(t, 0.002, 0.1, 0.39)
        samples.append(s * 0.6)
    return samples


def gen_data_tick(duration: float = 2.0) -> list[float]:
    """Soft digital ticking for data streaming sequences."""
    samples = []
    n = int(SAMPLE_RATE * duration)
    tick_interval = 0.08  # seconds between ticks
    tick_len = 0.015
    for i in range(n):
        t = i / SAMPLE_RATE
        phase = t % tick_interval
        if phase < tick_len:
            env = envelope(phase, 0.002, 0.003, 0.01)
            s = sine(2400, t) * env * 0.3
        else:
            s = 0.0
        # Overall fade
        s *= envelope(t, 0.1, duration - 0.4, 0.3)
        samples.append(s)
    return samples


def gen_pour_water(duration: float = 2.0) -> list[float]:
    """Water pouring — rising filtered noise."""
    samples = []
    n = int(SAMPLE_RATE * duration)
    for i in range(n):
        t = i / SAMPLE_RATE
        intensity = min(1.0, t / 0.5) * envelope(t, 0.3, duration - 0.7, 0.4)
        s = noise() * intensity * 0.2
        bubble = 0.5 + 0.5 * sine(12 + sine(0.5, t) * 4, t)
        s *= bubble
        samples.append(s)
    return samples


def gen_pot_stir(duration: float = 3.0) -> list[float]:
    """Wooden spoon stirring in a pot — rhythmic swoosh."""
    samples = []
    n = int(SAMPLE_RATE * duration)
    stir_rate = 0.8
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


# ─── Main ────────────────────────────────────────────────────

SFX_MAP = {
    "knife_chop": ("sfx_knife_chop.wav", gen_knife_chop),
    "pan_sizzle": ("sfx_pan_sizzle.wav", gen_pan_sizzle),
    "plate_set": ("sfx_plate_set.wav", gen_plate_set),
    "pour_water": ("sfx_pour_water.wav", gen_pour_water),
    "pot_stir": ("sfx_pot_stir.wav", gen_pot_stir),
    "data_tick": ("sfx_data_tick.wav", gen_data_tick),
}

if __name__ == "__main__":
    print("\nGenerating kitchen lo-fi SFX...")
    for name, (filename, gen_fn) in SFX_MAP.items():
        try:
            samples = gen_fn()
            save_wav(filename, samples)
        except Exception as e:
            print(f"  Failed {name}: {e}")
    print(f"\nSFX generation complete! Files in {output_dir}/")
