#!/usr/bin/env python3
"""
Assemble the lo-fi demo video from generated assets.

Combines: intro_lofi + composited terminal demo + outro_lofi
Audio: continuous lo-fi music + voiceover + optional SFX
Transitions: 1-second crossfades between segments

Output: fcp_demo_lofi.mp4
"""

import subprocess
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
OUTPUT = str(SCRIPT_DIR / "fcp_demo_lofi.mp4")
TEMP_DIR = SCRIPT_DIR / "assembly_tmp"

# ─── Timeline ─────────────────────────────────────────────────

TIMELINE = [
    {
        "id": "intro",
        "video": "intro_lofi.mp4",
        "audio_layers": [
            {"path": "music/lofi_intro.wav", "volume": 0.5},
        ],
        "duration": 6,
    },
    {
        "id": "recipe_quest",
        "video": "recordings/recipe_quest_composited.mp4",
        "audio_layers": [
            {"path": "audio/vo_recipe_quest.wav", "volume": 1.0, "delay_ms": 2000},
            {"path": "music/lofi_recipe_quest.wav", "volume": 0.20},
        ],
        "duration": None,  # Auto-detect from video
    },
    {
        "id": "outro",
        "video": "outro_lofi.mp4",
        "audio_layers": [
            {"path": "music/lofi_outro.wav", "volume": 0.4},
        ],
        "duration": 9,
    },
]

CROSSFADE_DURATION = 1.0  # seconds


def get_duration(path: str) -> float:
    """Get video duration via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip()) if result.returncode == 0 else 0.0


def resolve_path(p: str) -> Path:
    """Resolve a path relative to the script directory."""
    return SCRIPT_DIR / p


def check_assets():
    """Check which assets exist."""
    print("\nChecking assets...")
    available = []
    missing = []
    for seg in TIMELINE:
        vid = resolve_path(seg["video"])
        seg["video"] = str(vid)  # Resolve to absolute
        if vid.exists():
            dur = get_duration(str(vid))
            if seg["duration"] is None:
                seg["duration"] = dur
            available.append(seg["id"])
            print(f"  [ok] {seg['id']}: {seg['video']} ({dur:.1f}s)")
        else:
            missing.append(seg["id"])
            print(f"  [!!] {seg['id']}: {seg['video']} MISSING")

        for layer in seg.get("audio_layers", []):
            layer["path"] = str(resolve_path(layer["path"]))
            p = Path(layer["path"])
            if not p.exists():
                print(f"       audio missing: {layer['path']}")

    return available, missing


def normalize_segment(src: Path, dst: Path):
    """Re-encode segment to consistent format (h264, 30fps, video only)."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(src),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-s", "1920x1080",
            "-an", str(dst),
        ],
        check=True, capture_output=True,
    )


def concat_with_crossfade(segments: list[dict], output: str) -> bool:
    """Concatenate video segments with crossfade transitions.

    Uses ffmpeg xfade filter for smooth 1-second fades between segments.
    Falls back to concat demuxer if xfade is not available.
    """
    TEMP_DIR.mkdir(exist_ok=True)
    norm_dir = TEMP_DIR / "normalized"
    norm_dir.mkdir(exist_ok=True)

    # Normalize all segments
    norm_paths = []
    for i, seg in enumerate(segments):
        vid = Path(seg["video"])
        if not vid.exists():
            continue
        norm_path = norm_dir / f"seg_{i:03d}.mp4"
        normalize_segment(vid, norm_path)
        norm_paths.append((norm_path, seg["duration"]))

    if len(norm_paths) < 2:
        # Not enough segments for crossfade, just use concat
        if norm_paths:
            shutil.copy(str(norm_paths[0][0]), output)
            return True
        return False

    print(f"\nConcatenating {len(norm_paths)} segments with crossfade...")

    # Build xfade filter chain
    # For N segments: N-1 xfade operations
    inputs = []
    filter_parts = []
    for i, (path, _) in enumerate(norm_paths):
        inputs.extend(["-i", str(path)])

    # Chain xfades: [0][1]xfade -> [v01], [v01][2]xfade -> [v012], etc.
    offset = norm_paths[0][1] - CROSSFADE_DURATION
    prev_label = "[0:v]"

    for i in range(1, len(norm_paths)):
        out_label = f"[v{i}]"
        filter_parts.append(
            f"{prev_label}[{i}:v]xfade=transition=fade:duration={CROSSFADE_DURATION}:offset={offset:.2f}{out_label}"
        )
        if i < len(norm_paths) - 1:
            offset += norm_paths[i][1] - CROSSFADE_DURATION
        prev_label = out_label

    final_label = prev_label
    filter_complex = ";".join(filter_parts)

    video_only = str(TEMP_DIR / "video_only.mp4")
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", final_label,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
        video_only,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  xfade failed, falling back to concat demuxer")
        print(f"  {result.stderr[-300:]}")
        return _fallback_concat(norm_paths, video_only)

    dur = get_duration(video_only)
    print(f"  Video track: {dur:.1f}s")
    return True


def _fallback_concat(norm_paths: list, output: str) -> bool:
    """Fallback: simple concat without crossfade."""
    concat_file = TEMP_DIR / "concat.txt"
    lines = [f"file '{p.resolve()}'" for p, _ in norm_paths]
    concat_file.write_text("\n".join(lines))

    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-c:v", "copy", output,
        ],
        check=True, capture_output=True,
    )
    return True


def mix_audio(segments: list[dict], video_duration: float) -> Path | None:
    """Mix all audio layers into a single track with proper timing."""
    TEMP_DIR.mkdir(exist_ok=True)

    current_time_ms = 0
    audio_inputs = []

    for seg in segments:
        if not Path(seg["video"]).exists():
            continue

        for layer in seg.get("audio_layers", []):
            audio_path = Path(layer["path"])
            if not audio_path.exists():
                continue

            delay = current_time_ms + layer.get("delay_ms", 0)
            volume = layer.get("volume", 1.0)
            audio_inputs.append({
                "path": str(audio_path.resolve()),
                "delay_ms": delay,
                "volume": volume,
            })

        current_time_ms += int((seg["duration"] or 0) * 1000)

    if not audio_inputs:
        print("  No audio layers found")
        return None

    print(f"\nMixing {len(audio_inputs)} audio layers...")

    # Build ffmpeg filter_complex
    inputs = []
    filters = []
    for i, a in enumerate(audio_inputs):
        inputs.extend(["-i", a["path"]])
        filters.append(
            f"[{i}]volume={a['volume']},adelay={a['delay_ms']}|{a['delay_ms']}[a{i}]"
        )

    # Mix all streams, fade out last 2 seconds
    mix_inputs = "".join(f"[a{i}]" for i in range(len(audio_inputs)))
    fade_start = max(0, video_duration - 2.0)
    filters.append(
        f"{mix_inputs}amix=inputs={len(audio_inputs)}:duration=longest,"
        f"afade=t=out:st={fade_start:.1f}:d=2.0[out]"
    )

    mixed_audio = TEMP_DIR / "mixed_audio.wav"
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", ";".join(filters),
        "-map", "[out]",
        str(mixed_audio),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Audio mix error: {result.stderr[-300:]}")
        return None

    print(f"  Mixed audio: {mixed_audio}")
    return mixed_audio


def merge_av(video_path: str, audio_path: str, output: str):
    """Merge video and audio into final output."""
    print(f"\nMerging audio + video -> {output}")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output,
        ],
        check=True, capture_output=True,
    )


def assemble():
    """Full assembly pipeline."""
    available, missing = check_assets()

    if missing:
        print(f"\n{len(missing)} segments missing: {', '.join(missing)}")
        if "recipe_quest" in missing:
            print("\nThe terminal recording is missing. Record your terminal, then run:")
            print("  python composite_terminal.py recordings/recipe_quest_raw.mp4")
            print("  python assemble_lofi.py")
            return
        print("Assembling with available segments.\n")

    if not available:
        print("\nNo segments found. Run the generators first:")
        print("  python generate_lofi_bookends.py")
        print("  python generate_lofi_music.py")
        return

    segments = [s for s in TIMELINE if s["id"] in available]

    # Step 1: Concat video with crossfades
    if not concat_with_crossfade(segments, OUTPUT):
        print("Video concatenation failed.")
        return

    # Step 2: Mix audio
    video_only = str(TEMP_DIR / "video_only.mp4")
    total_duration = sum(
        (s["duration"] or 0) for s in segments
    ) - CROSSFADE_DURATION * max(0, len(segments) - 1)
    mixed = mix_audio(segments, total_duration)

    # Step 3: Merge A/V
    if mixed:
        merge_av(video_only, str(mixed), OUTPUT)
    else:
        shutil.copy(video_only, OUTPUT)
        print(f"\nFinal video (no audio): {OUTPUT}")

    # Cleanup
    shutil.rmtree(TEMP_DIR, ignore_errors=True)

    # Stats
    dur = get_duration(OUTPUT)
    print(f"\nAssembly complete!")
    print(f"  Duration: {dur:.1f}s ({dur/60:.1f} min)")
    print(f"  Output:   {OUTPUT}")
    if dur > 180:
        print(f"  Warning: Over 3 minutes! Only first 3:00 evaluated.")


if __name__ == "__main__":
    print("Lo-Fi Demo Video Assembly")
    print("=" * 40)
    assemble()
