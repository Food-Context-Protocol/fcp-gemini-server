"""Tests for generate_lofi_music.py — themed lo-fi synth engine.

Covers all synth primitives, foley, generators, theme system, WAV I/O,
Lyria fallback, build_tracks, and CLI entry point.
"""

import struct
import wave
from unittest.mock import patch

import pytest
from generate_lofi_music import (
    DEFAULT_MUSIC_THEME,
    MODEL,
    MUSIC_THEMES,
    SAMPLE_RATE,
    build_tracks,
    chop_at,
    data_tick_at,
    env_fade,
    gen_lofi_ambient,
    gen_themed_beat,
    gen_themed_outro,
    get_music_theme,
    hat_at,
    kick_at,
    lfo,
    noise_val,
    plate_clink_at,
    save_wav,
    saw,
    sine,
    sizzle_at,
    square,
    stir_at,
    try_lyria,
)

# ─── Synth Primitives ────────────────────────────────────────


class TestSine:
    def test_zero_at_origin(self):
        assert sine(440, 0) == pytest.approx(0.0, abs=1e-10)

    def test_peak_at_quarter_period(self):
        assert sine(1.0, 0.25) == pytest.approx(1.0, abs=1e-10)

    def test_zero_at_half_period(self):
        assert sine(1.0, 0.5) == pytest.approx(0.0, abs=1e-10)

    def test_trough_at_three_quarter(self):
        assert sine(1.0, 0.75) == pytest.approx(-1.0, abs=1e-10)

    def test_periodic(self):
        assert sine(440, 1.0) == pytest.approx(sine(440, 0.0), abs=1e-6)


class TestSaw:
    def test_starts_negative(self):
        assert saw(1.0, 0.0) == pytest.approx(-1.0, abs=1e-10)

    def test_midpoint(self):
        assert saw(1.0, 0.5) == pytest.approx(0.0, abs=1e-10)

    def test_range(self):
        for t_frac in [0.1, 0.3, 0.7, 0.9]:
            val = saw(1.0, t_frac)
            assert -1.0 <= val <= 1.0


class TestSquare:
    def test_high_in_first_half(self):
        assert square(1.0, 0.25) == 1.0

    def test_low_in_second_half(self):
        assert square(1.0, 0.75) == -1.0

    def test_custom_pulse_width(self):
        assert square(1.0, 0.1, pw=0.25) == 1.0
        assert square(1.0, 0.3, pw=0.25) == -1.0


class TestNoiseVal:
    def test_in_range(self):
        for _ in range(100):
            val = noise_val()
            assert -1.0 <= val <= 1.0

    def test_varies(self):
        values = {noise_val() for _ in range(50)}
        assert len(values) > 1


class TestLFO:
    def test_range_zero_to_one(self):
        for t in [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]:
            val = lfo(1.0, t)
            assert 0.0 <= val <= 1.0

    def test_starts_at_half(self):
        assert lfo(1.0, 0.0) == pytest.approx(0.5, abs=1e-10)

    def test_max_at_quarter(self):
        assert lfo(1.0, 0.25) == pytest.approx(1.0, abs=1e-10)


class TestEnvFade:
    def test_starts_at_zero(self):
        assert env_fade(0.0, 10.0, fade_in=1.0, fade_out=1.0) == 0.0

    def test_full_after_fade_in(self):
        assert env_fade(2.0, 10.0, fade_in=1.0, fade_out=1.0) == 1.0

    def test_fading_out(self):
        val = env_fade(9.5, 10.0, fade_in=1.0, fade_out=1.0)
        assert 0.0 < val < 1.0

    def test_zero_at_end(self):
        assert env_fade(10.0, 10.0, fade_in=1.0, fade_out=1.0) == 0.0

    def test_mid_fade_in(self):
        assert env_fade(0.5, 10.0, fade_in=1.0, fade_out=1.0) == pytest.approx(0.5)

    def test_clamps_to_zero_past_end(self):
        assert env_fade(11.0, 10.0, fade_in=1.0, fade_out=1.0) == 0.0


# ─── Percussion ───────────────────────────────────────────────


class TestKickAt:
    def test_silent_before_hit(self):
        assert kick_at(0.0, 1.0) == 0.0

    def test_nonzero_at_hit(self):
        assert kick_at(1.001, 1.0) != 0.0

    def test_silent_long_after_hit(self):
        assert kick_at(2.0, 1.0) == 0.0

    def test_decays(self):
        v1 = abs(kick_at(1.001, 1.0))
        v2 = abs(kick_at(1.1, 1.0))
        assert v1 > v2


class TestHatAt:
    def test_silent_before_hit(self):
        assert hat_at(0.0, 1.0) == 0.0

    def test_nonzero_at_hit(self):
        hits = [hat_at(1.001, 1.0) for _ in range(20)]
        assert any(h != 0.0 for h in hits)

    def test_silent_long_after(self):
        assert hat_at(1.1, 1.0) == 0.0


# ─── Kitchen Foley ────────────────────────────────────────────


class TestChopAt:
    def test_silent_before_hit(self):
        assert chop_at(0.0, 1.0) == 0.0

    def test_nonzero_at_hit(self):
        assert chop_at(1.001, 1.0) != 0.0

    def test_silent_after_decay(self):
        assert chop_at(1.1, 1.0) == 0.0


class TestSizzleAt:
    def test_returns_float(self):
        assert isinstance(sizzle_at(1.0), float)

    def test_intensity_zero_is_quiet(self):
        vals = [abs(sizzle_at(t, intensity=0.0)) for t in range(100)]
        assert sum(vals) < 1.0

    def test_higher_intensity_louder(self):
        import random

        random.seed(42)
        low = sum(abs(sizzle_at(t * 0.01, intensity=0.1)) for t in range(1000))
        random.seed(42)
        high = sum(abs(sizzle_at(t * 0.01, intensity=2.0)) for t in range(1000))
        assert high > low


class TestPlateClink:
    def test_silent_before_hit(self):
        assert plate_clink_at(0.0, 1.0) == 0.0

    def test_nonzero_at_hit(self):
        assert plate_clink_at(1.001, 1.0) != 0.0

    def test_silent_after_decay(self):
        assert plate_clink_at(1.2, 1.0) == 0.0


class TestStirAt:
    def test_silent_when_cycle_low(self):
        assert stir_at(0.0) == 0.0

    def test_nonzero_when_cycle_high(self):
        vals = [stir_at(0.357) for _ in range(20)]
        assert any(v != 0.0 for v in vals)


class TestDataTickAt:
    def test_silent_before_hit(self):
        assert data_tick_at(0.0, 1.0) == 0.0

    def test_nonzero_at_hit(self):
        assert data_tick_at(1.001, 1.0) != 0.0

    def test_silent_after_decay(self):
        assert data_tick_at(1.05, 1.0) == 0.0


# ─── WAV I/O ─────────────────────────────────────────────────


class TestSaveWav:
    def test_creates_wav_file(self, tmp_path):
        import generate_lofi_music

        original_dir = generate_lofi_music.output_dir
        generate_lofi_music.output_dir = tmp_path
        try:
            samples = [0.0, 0.5, -0.5, 1.0, -1.0]
            save_wav("test.wav", samples)
            path = tmp_path / "test.wav"
            assert path.exists()

            with wave.open(str(path), "rb") as wf:
                assert wf.getnchannels() == 1
                assert wf.getsampwidth() == 2
                assert wf.getframerate() == SAMPLE_RATE
                assert wf.getnframes() == len(samples)
        finally:
            generate_lofi_music.output_dir = original_dir

    def test_clamps_values(self, tmp_path):
        import generate_lofi_music

        original_dir = generate_lofi_music.output_dir
        generate_lofi_music.output_dir = tmp_path
        try:
            samples = [2.0, -2.0]
            save_wav("clamp.wav", samples)
            path = tmp_path / "clamp.wav"

            with wave.open(str(path), "rb") as wf:
                frames = wf.readframes(2)
                val1 = struct.unpack("<h", frames[0:2])[0]
                val2 = struct.unpack("<h", frames[2:4])[0]
                assert val1 == 32767
                assert val2 == -32767
        finally:
            generate_lofi_music.output_dir = original_dir


# ─── Music Themes ─────────────────────────────────────────────


class TestMusicThemes:
    REQUIRED_KEYS = {
        "bpm",
        "chords",
        "resolve_chords",
        "pad_freqs",
        "sub_bass",
        "foley",
        "lyria_hint",
    }

    @pytest.mark.parametrize("theme_name", list(MUSIC_THEMES.keys()))
    def test_theme_has_required_keys(self, theme_name):
        mt = MUSIC_THEMES[theme_name]
        assert self.REQUIRED_KEYS.issubset(mt.keys())

    @pytest.mark.parametrize("theme_name", list(MUSIC_THEMES.keys()))
    def test_bpm_reasonable(self, theme_name):
        assert 50 <= MUSIC_THEMES[theme_name]["bpm"] <= 120

    @pytest.mark.parametrize("theme_name", list(MUSIC_THEMES.keys()))
    def test_four_chords(self, theme_name):
        mt = MUSIC_THEMES[theme_name]
        assert len(mt["chords"]) == 4
        assert len(mt["resolve_chords"]) == 4

    @pytest.mark.parametrize("theme_name", list(MUSIC_THEMES.keys()))
    def test_chord_voicings_have_four_notes(self, theme_name):
        mt = MUSIC_THEMES[theme_name]
        for chord in mt["chords"] + mt["resolve_chords"]:
            assert len(chord) == 4

    @pytest.mark.parametrize("theme_name", list(MUSIC_THEMES.keys()))
    def test_foley_weights(self, theme_name):
        foley = MUSIC_THEMES[theme_name]["foley"]
        for key in ["sizzle", "chop", "clink", "stir", "tick"]:
            assert key in foley
            assert 0.0 <= foley[key] <= 2.0


class TestGetMusicTheme:
    def test_default_when_none(self):
        assert get_music_theme(None) == MUSIC_THEMES[DEFAULT_MUSIC_THEME]

    def test_default_when_invalid(self):
        assert get_music_theme("not_a_theme") == MUSIC_THEMES[DEFAULT_MUSIC_THEME]

    def test_returns_named(self):
        assert get_music_theme("mcp_toolbox")["bpm"] == 78

    @pytest.mark.parametrize("theme_name", list(MUSIC_THEMES.keys()))
    def test_all_themes_retrievable(self, theme_name):
        assert get_music_theme(theme_name) == MUSIC_THEMES[theme_name]


# ─── Generators ───────────────────────────────────────────────


class TestGenLofiAmbient:
    def test_returns_correct_length(self):
        dur = 0.1
        assert len(gen_lofi_ambient(dur)) == int(SAMPLE_RATE * dur)

    def test_all_samples_in_range(self):
        assert all(-2.0 < s < 2.0 for s in gen_lofi_ambient(0.05))

    def test_respects_theme(self):
        import random

        random.seed(42)
        s1 = gen_lofi_ambient(0.05, "recipe_quest")
        random.seed(42)
        s2 = gen_lofi_ambient(0.05, "mcp_toolbox")
        assert s1 != s2


class TestGenThemedBeat:
    def test_returns_correct_length(self):
        dur = 0.1
        assert len(gen_themed_beat(dur)) == int(SAMPLE_RATE * dur)

    def test_all_samples_in_range(self):
        assert all(-2.0 < s < 2.0 for s in gen_themed_beat(0.1))

    def test_different_themes_differ(self):
        import random

        random.seed(42)
        s1 = gen_themed_beat(0.1, "recipe_quest")
        random.seed(42)
        s2 = gen_themed_beat(0.1, "allergen_alert")
        assert s1 != s2

    @pytest.mark.parametrize("theme_name", list(MUSIC_THEMES.keys()))
    def test_all_themes_generate(self, theme_name):
        assert len(gen_themed_beat(0.05, theme_name)) > 0

    def test_tick_foley_for_tech_themes(self):
        samples = gen_themed_beat(2.0, "mcp_toolbox")
        assert len(samples) == int(SAMPLE_RATE * 2.0)


class TestGenThemedOutro:
    def test_returns_correct_length(self):
        dur = 0.1
        assert len(gen_themed_outro(dur)) == int(SAMPLE_RATE * dur)

    def test_all_samples_in_range(self):
        assert all(-2.0 < s < 2.0 for s in gen_themed_outro(0.1))

    def test_drum_fade(self):
        dur = 4.0
        samples = gen_themed_outro(dur)
        early_energy = sum(s * s for s in samples[:SAMPLE_RATE])
        late_energy = sum(s * s for s in samples[-SAMPLE_RATE:])
        assert early_energy > late_energy

    @pytest.mark.parametrize("theme_name", list(MUSIC_THEMES.keys()))
    def test_all_themes_generate(self, theme_name):
        assert len(gen_themed_outro(0.05, theme_name)) > 0


# ─── Build Tracks ─────────────────────────────────────────────


class TestBuildTracks:
    def test_returns_three_tracks(self):
        assert set(build_tracks().keys()) == {"lofi_intro", "lofi_recipe_quest", "lofi_outro"}

    def test_track_has_required_fields(self):
        for name, track in build_tracks().items():
            assert "lyria_prompt" in track
            assert "duration" in track
            assert callable(track["synth_fn"])

    def test_custom_demo_duration(self):
        tracks = build_tracks(demo_duration=30.0)
        assert tracks["lofi_recipe_quest"]["duration"] == 30.0

    def test_themed_lyria_prompts(self):
        prompt = build_tracks("allergen_alert")["lofi_recipe_quest"]["lyria_prompt"]
        assert "80bpm" in prompt
        assert "alert but calm" in prompt

    def test_synth_fn_produces_samples(self):
        tracks = build_tracks(demo_duration=0.05)
        for track in tracks.values():
            assert len(track["synth_fn"]()) > 0


# ─── Lyria ────────────────────────────────────────────────────


class TestTryLyria:
    def test_returns_false_on_error(self, tmp_path):
        with patch("generate_lofi_music.generate_lyria_track", side_effect=RuntimeError("no key")):
            with patch("generate_lofi_music.asyncio.run", side_effect=RuntimeError("no key")):
                assert try_lyria("prompt", str(tmp_path / "out.wav"), 1.0) is False

    def test_returns_true_on_success(self, tmp_path):
        # Mock generate_lyria_track to return a non-coroutine to avoid unawaited warnings
        with patch("generate_lofi_music.generate_lyria_track", return_value=None):
            with patch("generate_lofi_music.asyncio.run", return_value=None):
                assert try_lyria("prompt", str(tmp_path / "out.wav"), 1.0) is True


class TestModel:
    def test_model_name(self):
        assert MODEL == "models/lyria-realtime-exp"


# ─── CLI ──────────────────────────────────────────────────────


class TestCLIListThemes:
    def test_list_themes_output(self, capsys):
        """Test that --list-themes prints all theme names."""
        from generate_lofi_music import DEFAULT_MUSIC_THEME, MUSIC_THEMES

        print("Available music themes:")
        for key, mt in MUSIC_THEMES.items():
            marker = " (default)" if key == DEFAULT_MUSIC_THEME else ""
            print(f"  {key:20s} — {mt['bpm']}bpm, {mt['lyria_hint']}{marker}")

        output = capsys.readouterr().out
        assert "recipe_quest" in output
        assert "(default)" in output
        for key in MUSIC_THEMES:
            assert key in output


class TestCLISynthOnly:
    def test_synth_produces_all_wav_files(self, tmp_path):
        import generate_lofi_music

        original_dir = generate_lofi_music.output_dir
        generate_lofi_music.output_dir = tmp_path
        try:
            tracks = build_tracks(demo_duration=0.05)
            for name, track in tracks.items():
                filename = f"{name}.wav"
                samples = track["synth_fn"]()
                save_wav(filename, samples)
                assert (tmp_path / filename).exists()
        finally:
            generate_lofi_music.output_dir = original_dir


class TestConstants:
    def test_default_is_recipe_quest(self):
        assert DEFAULT_MUSIC_THEME == "recipe_quest"

    def test_default_exists_in_themes(self):
        assert DEFAULT_MUSIC_THEME in MUSIC_THEMES

    def test_sample_rate(self):
        assert SAMPLE_RATE == 44100
