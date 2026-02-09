"""Tests for assemble_lofi.py — lo-fi demo video assembly pipeline.

Covers timeline structure, asset checking, audio mixing, and concat logic.
"""

from unittest.mock import MagicMock, patch

import pytest
from assemble_lofi import (
    CROSSFADE_DURATION,
    TIMELINE,
    check_assets,
    get_duration,
    merge_av,
    mix_audio,
    resolve_path,
)


class TestTimeline:
    def test_has_three_segments(self):
        assert len(TIMELINE) == 3

    def test_segment_ids(self):
        ids = [seg["id"] for seg in TIMELINE]
        assert ids == ["intro", "recipe_quest", "outro"]

    def test_each_segment_has_video(self):
        for seg in TIMELINE:
            assert "video" in seg

    def test_each_segment_has_audio_layers(self):
        for seg in TIMELINE:
            assert "audio_layers" in seg

    def test_recipe_quest_has_voiceover(self):
        rq = next(s for s in TIMELINE if s["id"] == "recipe_quest")
        audio_paths = [layer["path"] for layer in rq["audio_layers"]]
        assert any("vo_recipe_quest" in p for p in audio_paths)

    def test_recipe_quest_duration_auto(self):
        rq = next(s for s in TIMELINE if s["id"] == "recipe_quest")
        assert rq["duration"] is None  # Auto-detected from video


class TestCrossfadeDuration:
    def test_one_second(self):
        assert CROSSFADE_DURATION == 1.0


class TestGetDuration:
    def test_returns_float_on_success(self):
        with patch("assemble_lofi.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="42.5\n")
            assert get_duration("test.mp4") == pytest.approx(42.5)

    def test_returns_zero_on_failure(self):
        with patch("assemble_lofi.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            assert get_duration("missing.mp4") == 0.0


class TestResolvePath:
    def test_resolves_relative_to_script_dir(self):
        result = resolve_path("recordings/test.mp4")
        assert result.name == "test.mp4"
        assert "recordings" in str(result)


class TestCheckAssets:
    def test_reports_missing_files(self, capsys):
        """All video files should be missing in test env (no recordings)."""
        # Reset TIMELINE video paths to relative (check_assets resolves them)
        import assemble_lofi

        original_timeline = [dict(s) for s in assemble_lofi.TIMELINE]
        # Restore original relative paths for test
        assemble_lofi.TIMELINE[0]["video"] = "intro_lofi.mp4"
        assemble_lofi.TIMELINE[1]["video"] = "recordings/recipe_quest_composited.mp4"
        assemble_lofi.TIMELINE[2]["video"] = "outro_lofi.mp4"

        try:
            available, missing = check_assets()
            # In test env, these files don't exist
            output = capsys.readouterr().out
            assert "Checking assets" in output
        finally:
            # Restore original timeline
            assemble_lofi.TIMELINE[:] = original_timeline


class TestMixAudio:
    def test_returns_none_when_no_audio(self):
        segments = [{"video": "/nonexistent.mp4", "audio_layers": [], "duration": 5}]
        result = mix_audio(segments, 5.0)
        assert result is None

    def test_returns_none_when_no_video(self):
        segments = [
            {
                "video": "/nonexistent.mp4",
                "audio_layers": [{"path": "/nonexistent.wav", "volume": 1.0}],
                "duration": 5,
            }
        ]
        result = mix_audio(segments, 5.0)
        assert result is None

    def test_returns_path_on_success(self, tmp_path):
        # Create fake audio file
        audio_file = tmp_path / "audio.wav"
        audio_file.touch()
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        segments = [
            {
                "video": str(video_file),
                "audio_layers": [{"path": str(audio_file), "volume": 1.0}],
                "duration": 5,
            }
        ]

        with patch("assemble_lofi.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            with patch("assemble_lofi.TEMP_DIR", tmp_path):
                result = mix_audio(segments, 5.0)
                assert result is not None

    def test_handles_delay_ms(self, tmp_path):
        audio_file = tmp_path / "audio.wav"
        audio_file.touch()
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        segments = [
            {
                "video": str(video_file),
                "audio_layers": [
                    {
                        "path": str(audio_file),
                        "volume": 0.5,
                        "delay_ms": 2000,
                    }
                ],
                "duration": 10,
            }
        ]

        with patch("assemble_lofi.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            with patch("assemble_lofi.TEMP_DIR", tmp_path):
                mix_audio(segments, 10.0)
                cmd = mock_run.call_args[0][0]
                filter_complex = cmd[cmd.index("-filter_complex") + 1]
                assert "adelay=2000" in filter_complex

    def test_returns_none_on_ffmpeg_failure(self, tmp_path):
        audio_file = tmp_path / "audio.wav"
        audio_file.touch()
        video_file = tmp_path / "video.mp4"
        video_file.touch()

        segments = [
            {
                "video": str(video_file),
                "audio_layers": [{"path": str(audio_file), "volume": 1.0}],
                "duration": 5,
            }
        ]

        with patch("assemble_lofi.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="error")
            with patch("assemble_lofi.TEMP_DIR", tmp_path):
                result = mix_audio(segments, 5.0)
                assert result is None


class TestMergeAV:
    def test_calls_ffmpeg(self, tmp_path):
        with patch("assemble_lofi.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            merge_av(
                str(tmp_path / "video.mp4"),
                str(tmp_path / "audio.wav"),
                str(tmp_path / "output.mp4"),
            )
            cmd = mock_run.call_args[0][0]
            assert "ffmpeg" in cmd
            assert "-c:a" in cmd
            assert "aac" in cmd


class TestConcatWithCrossfade:
    def test_single_segment_copies(self, tmp_path):
        from assemble_lofi import concat_with_crossfade

        seg_file = tmp_path / "seg.mp4"
        seg_file.touch()
        output = str(tmp_path / "out.mp4")

        segments = [{"video": str(seg_file), "duration": 5.0}]

        with patch("assemble_lofi.normalize_segment"):
            with patch("assemble_lofi.TEMP_DIR", tmp_path):
                norm_dir = tmp_path / "normalized"
                norm_dir.mkdir(exist_ok=True)
                # Create fake normalized file
                norm_file = norm_dir / "seg_000.mp4"
                norm_file.touch()

                with patch("assemble_lofi.shutil.copy"):
                    result = concat_with_crossfade(segments, output)
                    assert result is True

    def test_no_segments_returns_false(self, tmp_path):
        from assemble_lofi import concat_with_crossfade

        output = str(tmp_path / "out.mp4")

        with patch("assemble_lofi.TEMP_DIR", tmp_path):
            result = concat_with_crossfade([], output)
            assert result is False


class TestFallbackConcat:
    def test_fallback_uses_concat_demuxer(self, tmp_path):
        from assemble_lofi import _fallback_concat

        seg1 = tmp_path / "seg1.mp4"
        seg1.touch()
        output = str(tmp_path / "out.mp4")

        with patch("assemble_lofi.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with patch("assemble_lofi.TEMP_DIR", tmp_path):
                result = _fallback_concat([(seg1, 5.0)], output)
                assert result is True
                cmd = mock_run.call_args[0][0]
                assert "-f" in cmd
                assert "concat" in cmd
