"""Coverage tests for demo recording utilities."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from fcp.utils import demo_recording as dr


def test_demo_recording_sanitization():
    recording = dr.DemoRecording(
        tool_name="get_recent_meals",
        arguments={"user_id": "u1", "nested": {"token": "x"}},
        response={"email": "a@b.com", "items": [{"password": "p"}]},
        duration_seconds=1.2345,
        status="success",
    )
    data = recording.sanitize_for_storage()
    assert data["arguments"]["user_id"] == "[REDACTED]"
    assert data["arguments"]["nested"]["token"] == "[REDACTED]"
    assert data["response"]["email"] == "[REDACTED]"
    assert data["response"]["items"][0]["password"] == "[REDACTED]"


def test_should_record_tool():
    with patch.object(dr, "RECORDING_ENABLED", False):
        assert dr.should_record_tool("get_recent_meals") is False
    with patch.object(dr, "RECORDING_ENABLED", True):
        assert dr.should_record_tool("get_recent_meals") is True
        assert dr.should_record_tool("unknown") is False


def test_save_and_load_recordings(tmp_path: Path):
    with patch.object(dr, "RECORDING_ENABLED", True):
        with patch.object(dr, "RECORDING_PATH", tmp_path):
            rec = dr.DemoRecording(
                tool_name="get_recent_meals",
                arguments={"x": 1},
                response={"ok": True},
                duration_seconds=0.1,
                status="success",
            )
            rec.timestamp = "2026-02-03T10:30:00"
            path = dr.save_recording(rec)
            assert path is not None
            assert path.exists()

            # Add an invalid file to trigger warning path
            bad = tmp_path / "get_recent_meals" / "bad.json"
            bad.write_text("not-json")
            recordings = dr.load_recordings("get_recent_meals")
            assert recordings


def test_save_recording_disabled():
    rec = dr.DemoRecording(
        tool_name="get_recent_meals",
        arguments={"x": 1},
        response={"ok": True},
        duration_seconds=0.1,
        status="success",
    )
    with patch.object(dr, "RECORDING_ENABLED", False):
        assert dr.save_recording(rec) is None


def test_save_recording_error(tmp_path: Path):
    with patch.object(dr, "RECORDING_ENABLED", True):
        with patch.object(dr, "RECORDING_PATH", tmp_path):
            rec = dr.DemoRecording(
                tool_name="get_recent_meals",
                arguments={"x": 1},
                response={"ok": True},
                duration_seconds=0.1,
                status="success",
            )
            with patch("fcp.utils.demo_recording.open", side_effect=OSError("boom")):
                assert dr.save_recording(rec) is None


def test_load_recordings_missing_dir(tmp_path: Path):
    with patch.object(dr, "RECORDING_PATH", tmp_path):
        assert dr.load_recordings("missing_tool") == []


def test_get_cached_response_no_recordings(tmp_path: Path):
    with patch.object(dr, "RECORDING_PATH", tmp_path):
        with patch.object(dr, "RECORDING_ENABLED", True):
            assert dr.get_cached_response("get_recent_meals", {"x": 1}) is None


def test_get_cached_response(tmp_path: Path):
    with patch.object(dr, "RECORDING_PATH", tmp_path):
        with patch.object(dr, "RECORDING_ENABLED", True):
            tool_dir = tmp_path / "get_recent_meals"
            tool_dir.mkdir(parents=True)
            (tool_dir / "a.json").write_text(json.dumps({"arguments": {"x": 1}, "response": {"ok": 1}}))
            (tool_dir / "b.json").write_text(json.dumps({"arguments": {"x": 2}, "response": {"ok": 2}}))

            result = dr.get_cached_response("get_recent_meals", {"x": 2})
            assert result is not None
            assert result["ok"] == 2

            result = dr.get_cached_response("get_recent_meals", {"x": 999})
            assert result is not None
            assert result["ok"] in {1, 2}

            assert dr.get_cached_response("unknown", {"x": 1}) is None
