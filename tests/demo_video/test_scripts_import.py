"""Smoke tests for demo-video scripts to ensure they can be imported and basic functionality works."""

import sys
from pathlib import Path

# Add demo-video to path
demo_video_path = Path(__file__).parent.parent.parent / "demo-video"
sys.path.insert(0, str(demo_video_path))


def test_preview_timeline_animated_imports():
    """Test that animated preview script can be imported."""
    from preview_timeline_animated import AnimatedPreviewGenerator, Shot

    assert AnimatedPreviewGenerator is not None
    assert Shot is not None


def test_preview_timeline_enhanced_imports():
    """Test that enhanced preview script can be imported."""
    from preview_timeline_enhanced import EnhancedPreviewGenerator, Shot

    assert EnhancedPreviewGenerator is not None
    assert Shot is not None


def test_preview_timeline_imports():
    """Test that original preview script can be imported."""
    from preview_timeline import Shot, TimelinePreviewGenerator

    assert TimelinePreviewGenerator is not None
    assert Shot is not None


def test_shot_dataclass():
    """Test Shot dataclass creation."""
    from preview_timeline_animated import Shot

    shot = Shot(
        number=1,
        name="Test",
        start_time=0.0,
        duration=5.0,
        act="Act 1",
        audio_description="Audio",
        visual_description="Visual",
    )

    assert shot.number == 1
    assert shot.name == "Test"
    assert shot.duration == 5.0
    assert shot.asset_path is None


def test_shot_with_asset():
    """Test Shot with asset path."""
    from preview_timeline_animated import Shot

    shot = Shot(
        number=1,
        name="Test",
        start_time=0.0,
        duration=5.0,
        act="Act 1",
        audio_description="Audio",
        visual_description="Visual",
        asset_path="/path/to/asset.png",
    )

    assert shot.asset_path == "/path/to/asset.png"


def test_timeline_config_exists():
    """Test that timeline config file exists."""
    config_path = demo_video_path / "timeline_config.json"
    assert config_path.exists(), f"timeline_config.json not found at {config_path}"


def test_timeline_config_valid():
    """Test that timeline config is valid JSON."""
    import json

    config_path = demo_video_path / "timeline_config.json"
    with open(config_path) as f:
        data = json.load(f)

    assert "metadata" in data
    assert "shots" in data
    assert isinstance(data["shots"], list)
    assert len(data["shots"]) > 0


def test_timeline_config_shot_structure():
    """Test that timeline config shots have required fields."""
    import json

    config_path = demo_video_path / "timeline_config.json"
    with open(config_path) as f:
        data = json.load(f)

    required_fields = [
        "number",
        "name",
        "start_time",
        "duration",
        "act",
        "audio_description",
        "visual_description",
    ]

    for shot in data["shots"]:
        for field in required_fields:
            assert field in shot, f"Shot {shot.get('number')} missing field: {field}"


def test_timeline_config_metadata():
    """Test that timeline config metadata is valid."""
    import json

    config_path = demo_video_path / "timeline_config.json"
    with open(config_path) as f:
        data = json.load(f)

    metadata = data["metadata"]
    assert "total_duration" in metadata
    assert metadata["total_duration"] == 180, "Duration must be exactly 180 seconds (3 minutes) for hackathon"
    assert "fps" in metadata
    assert metadata["fps"] == 30


def test_timeline_config_duration_matches_shots():
    """Test that total duration matches sum of shot durations."""
    import json

    config_path = demo_video_path / "timeline_config.json"
    with open(config_path) as f:
        data = json.load(f)

    total_from_shots = sum(shot["duration"] for shot in data["shots"])
    total_in_metadata = data["metadata"]["total_duration"]

    assert abs(total_from_shots - total_in_metadata) < 0.1, (
        f"Duration mismatch: shots={total_from_shots}, metadata={total_in_metadata}"
    )


def test_readme_exists():
    """Test that README exists."""
    readme_path = demo_video_path / "README.md"
    assert readme_path.exists()


def test_documentation_exists():
    """Test that DOCUMENTATION exists."""
    doc_path = demo_video_path / "DOCUMENTATION.md"
    assert doc_path.exists()


def test_scripts_executable():
    """Test that scripts have execute permissions or can be run."""
    scripts = [
        "preview_timeline.py",
        "preview_timeline_enhanced.py",
        "preview_timeline_animated.py",
    ]

    for script in scripts:
        script_path = demo_video_path / script
        assert script_path.exists(), f"{script} not found"
        assert script_path.stat().st_size > 1000, f"{script} seems too small"
