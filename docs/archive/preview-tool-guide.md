# Timeline Preview Tool Guide

Automated tool for generating visual previews of the video timeline with placeholders and actual assets.

---

## 🎯 Purpose

The preview tool (`preview_timeline.py`) generates an animated timeline preview that:

1. **Visualizes the complete storyboard** - Shows all 25 shots in sequence
2. **Uses actual assets when available** - Automatically detects and includes generated assets (logos, screenshots, diagrams)
3. **Creates placeholders for missing assets** - Shows shot information for assets not yet generated
4. **Supports real-time or fast preview** - Generate full-length (2:47) or sped-up previews
5. **Updates automatically** - Re-run to pick up new assets as they're created
6. **Includes audio support** - Add background music or voiceover (MP4 only)

---

## 🚀 Quick Start

### Basic Usage

```bash
# Generate full-length preview (2:47 at 1x speed)
python preview_timeline.py

# Output: timeline_preview.mp4
```

This creates a real-time preview matching the storyboard duration.

---

## ⚙️ Options

### Speed Control

```bash
# Real-time (default)
python preview_timeline.py --speed 1.0

# 2x speed (half duration)
python preview_timeline.py --speed 2.0

# 5x speed for quick review
python preview_timeline.py --speed 5.0

# 10x speed GIF for ultra-fast preview
python preview_timeline.py --speed 10.0 --format gif
```

**Speed multiplier**: Higher values = faster preview (shorter duration)
- `1.0` = Real-time (2:47 video → 2:47 preview)
- `2.0` = 2x speed (2:47 video → 1:24 preview)
- `5.0` = 5x speed (2:47 video → 33s preview)
- `10.0` = 10x speed (2:47 video → 17s preview)

### Output Format

```bash
# MP4 (default, supports audio)
python preview_timeline.py --format mp4

# Animated GIF (no audio support)
python preview_timeline.py --format gif
```

**Note**: GIF format:
- Does not support audio
- Better for fast previews (use higher --speed)
- Automatically reduced to 10fps for file size

### Add Audio

```bash
# Add background music (MP4 only)
python preview_timeline.py --audio assets/background_music.mp3

# With custom output
python preview_timeline.py --audio music.mp3 --output preview_with_audio.mp4
```

**Audio notes**:
- Only works with MP4 format
- Audio will be mixed with video
- Use `--shortest` to trim to video length

### Custom Output

```bash
# Specify output filename
python preview_timeline.py --output my_preview.mp4

# Different location
python preview_timeline.py --output previews/v1.mp4
```

### Frame Rate

```bash
# Default 30fps (smooth)
python preview_timeline.py --fps 30

# Lower FPS for smaller file size
python preview_timeline.py --fps 15

# Higher FPS for smoother animation
python preview_timeline.py --fps 60
```

---

## 📋 Complete Examples

### Example 1: First Preview (No Assets Yet)

```bash
# Generate initial preview with all placeholders
python preview_timeline.py

# Output shows:
# - 25 placeholder frames
# - Shot names, timings, descriptions
# - Act colors (green/blue/orange)
# - Audio descriptions
```

### Example 2: After Generating Test Assets

```bash
# Generate some test assets first
python test_generation.py --asset logo
python test_generation.py --asset diagram

# Regenerate preview (automatically picks up new assets)
python preview_timeline.py

# Now shows:
# - Logo in Shot 1 (actual asset)
# - Architecture diagram in Shot 22 (actual asset)
# - Placeholders for other shots
```

### Example 3: Fast GIF Preview

```bash
# Quick 20-second GIF preview
python preview_timeline.py \
  --format gif \
  --speed 8.0 \
  --output quick_preview.gif

# Great for:
# - Sharing in Slack/Discord
# - Quick reviews
# - README previews
```

### Example 4: Full Production Preview

```bash
# Full-length preview with music
python preview_timeline.py \
  --speed 1.0 \
  --audio assets/background_music.mp3 \
  --output timeline_preview_v1.mp4

# This creates:
# - Full 2:47 video
# - Background music
# - All available assets
# - Smooth 30fps playback
```

### Example 5: After Capturing Screenshots

```bash
# Capture screenshots following guide
# (see docs/screenshot-capture-guide.md)

# Regenerate preview
python preview_timeline.py

# Now shows:
# - Dashboard screenshot in Shot 20
# - Meal analysis screenshot in Shots 6-8
# - Function calling screenshot in Shots 10-12
# - And more...
```

---

## 📂 Asset Detection

The preview tool automatically searches for assets in these locations:

```
assets/          # Generated assets (logos, backgrounds, etc.)
screenshots/     # UI screenshots from app
test_assets/     # Test generation output
```

### Recognized Asset Names

The tool looks for these specific filenames:

| Shot | Asset Name | Extensions |
|------|------------|------------|
| 1 | `fcp_logo` | .png, .jpg |
| 6 | `02_meal_analysis_input` | .png |
| 7-8 | `03_meal_analysis_results` | .png |
| 10 | `05_voice_logging` | .png |
| 11-12 | `06_function_calling` | .png |
| 16 | `08_safety_alert` | .png |
| 18-19 | `09_gemini_live_chat` | .png |
| 20 | `01_dashboard` | .png |
| 22 | `architecture_diagram` | .png |

**Naming variations**:
- `fcp_logo.png` ✓
- `fcp_logo_test.png` ✓ (test suffix)
- `fcp_logo_v1.png` ✗ (version suffix not supported)

---

## 🎨 Preview Frame Design

### Placeholder Frames

When an asset is not available, the preview shows:

```
┌─────────────────────────────────────────┐
│ [Colored Bar: Act 1/2/3]                │
│                                         │
│           ┌───────────────┐             │
│           │               │             │
│           │   SHOT 5      │             │
│           │               │             │
│           │ Feature 1 -   │             │
│           │   Intro       │             │
│           │               │             │
│           │ [Description] │             │
│           │               │             │
│           └───────────────┘             │
│                                         │
│ ACT 2: DEMO        [Duration: 5s]       │
│ 0:30 - 0:35                             │
│                                         │
│ 🎙️ Audio: "First: Multimodal..."      │
└─────────────────────────────────────────┘
```

### Frames with Assets

When an asset exists:

```
┌─────────────────────────────────────────┐
│ [Colored Bar: Act]                      │
│                                         │
│        [Actual Asset Image]             │
│         (Logo, Screenshot,              │
│          Diagram, etc.)                 │
│                                         │
├─────────────────────────────────────────┤
│ Shot 1: Opening Title    ✓ Asset       │
│ ⏱️ 0:00 - 0:05 (5s)                    │
└─────────────────────────────────────────┘
```

### Color Coding

- **Green bar** (#4CAF50): Act 1 - The Hook
- **Blue bar** (#2196F3): Act 2 - The Demo
- **Orange bar** (#FF9800): Act 3 - The Impact

---

## 🔄 Iterative Workflow

The preview tool is designed for iterative development:

### Iteration 1: Initial Preview
```bash
# No assets yet
python preview_timeline.py

# Result: All placeholders showing structure
```

### Iteration 2: After Test Generation
```bash
# Generate test assets
python test_generation.py --asset all

# Regenerate preview
python preview_timeline.py

# Result: Logo, diagram visible. Rest placeholders.
```

### Iteration 3: After Screenshot Capture
```bash
# Capture UI screenshots
# (see screenshot-capture-guide.md)

# Regenerate preview
python preview_timeline.py

# Result: Logo, diagram, screenshots visible
```

### Iteration 4: After Full Generation
```bash
# Generate all AI assets
python generate_video.py --mode hybrid

# Regenerate preview with audio
python preview_timeline.py --audio assets/background_music.mp3

# Result: Full preview with all assets + music
```

---

## 🛠️ Technical Details

### Frame Generation

- **Resolution**: 1920×1080 (Full HD)
- **Default FPS**: 30 (smooth playback)
- **Frame format**: PNG (lossless)
- **Frame calculation**: `frames = shot_duration / speed_multiplier * fps`

### Video Encoding

**MP4**:
- Codec: H.264 (libx264)
- Preset: medium
- CRF: 23 (good quality)
- Pixel format: yuv420p (compatible)

**GIF**:
- Reduced FPS: 10 (for file size)
- Scaled: 1280×720 (smaller)
- Palette optimization: Lanczos

### File Sizes (Approximate)

| Format | Speed | Duration | Size |
|--------|-------|----------|------|
| MP4 | 1.0x | 2:47 | ~50 MB |
| MP4 | 2.0x | 1:24 | ~25 MB |
| GIF | 5.0x | 33s | ~15 MB |
| GIF | 10.0x | 17s | ~8 MB |

---

## 📊 Output Information

After generation, the tool displays:

```
FCP Timeline Preview Generator
============================================================

Timeline Summary:
  Total Shots: 25
  With Assets: 8
  Placeholders: 17
  Storyboard Duration: 2:47
  Preview Duration: 2:47 (1.0x speed)
  Output Format: MP4
  Frame Rate: 30 fps

🎬 Generating Timeline Frames...
✓ Generated 5010 frames (167.0s at 30fps)

🎥 Creating Video...
Adding audio: assets/background_music.mp3
✓ Video created: timeline_preview.mp4
  Size: 48.32 MB
  Duration: 2:47

✅ Timeline Preview Complete!

Output: timeline_preview.mp4

To regenerate with updated assets:
  python preview_timeline.py --output timeline_preview.mp4

To create a faster preview:
  python preview_timeline.py --speed 2.0  # 2x speed
  python preview_timeline.py --speed 5.0 --format gif  # 5x GIF
```

---

## 🚨 Troubleshooting

### Issue: FFmpeg Not Found

**Error**: `FFmpeg not found. Please install FFmpeg`

**Solution**:
```bash
# Mac
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

### Issue: Out of Memory

**Error**: Python crashes during frame generation

**Solutions**:
1. Use higher speed multiplier (fewer frames)
   ```bash
   python preview_timeline.py --speed 5.0
   ```

2. Lower frame rate
   ```bash
   python preview_timeline.py --fps 15
   ```

3. Use GIF format (automatic optimization)
   ```bash
   python preview_timeline.py --format gif
   ```

### Issue: Large File Size

**Problem**: Output video is too large (>100 MB)

**Solutions**:
1. Use higher speed multiplier
   ```bash
   python preview_timeline.py --speed 2.0
   ```

2. Lower FPS
   ```bash
   python preview_timeline.py --fps 15
   ```

3. Use GIF for sharing
   ```bash
   python preview_timeline.py --format gif --speed 5.0
   ```

### Issue: Asset Not Detected

**Problem**: Generated asset not appearing in preview

**Checklist**:
- [ ] Asset file exists in `assets/`, `screenshots/`, or `test_assets/`
- [ ] Filename matches expected pattern (see Asset Detection section)
- [ ] File extension is `.png` or `.jpg`
- [ ] File is not corrupted (open manually to verify)

**Debug**:
```bash
# Check what files exist
ls -lh assets/*.png
ls -lh screenshots/*.png
ls -lh test_assets/*.png

# Regenerate with verbose output
python preview_timeline.py
```

### Issue: Audio Out of Sync

**Problem**: Audio doesn't match video duration

**Solutions**:
1. Trim audio to video length (automatic with `--shortest`)
2. Generate audio with exact storyboard duration
3. Use audio editing tool to match lengths first

---

## 🎯 Best Practices

### 1. Generate Preview Early and Often
```bash
# Generate preview at each stage
python preview_timeline.py

# Helps catch:
# - Timing issues
# - Asset naming problems
# - Missing content
# - Visual flow problems
```

### 2. Use Speed Tiers for Different Purposes

**Real-time (1.0x)** - Final review
```bash
python preview_timeline.py --speed 1.0 --audio music.mp3
```

**2x speed** - Quick review of changes
```bash
python preview_timeline.py --speed 2.0
```

**5-10x speed GIF** - Share progress in chat
```bash
python preview_timeline.py --speed 8.0 --format gif
```

### 3. Organize Preview Versions
```bash
# Create previews/ directory
mkdir previews

# Save dated versions
python preview_timeline.py --output previews/preview_2025-02-08.mp4

# Keep latest as default
python preview_timeline.py --output timeline_preview.mp4
```

### 4. Test Audio Separately
```bash
# Generate preview without audio first
python preview_timeline.py

# If looks good, add audio
python preview_timeline.py --audio assets/background_music.mp3
```

---

## 📚 Integration with Other Tools

### With Test Generation
```bash
# Generate test assets
python test_generation.py --asset all

# Preview result
python preview_timeline.py
```

### With Full Generation
```bash
# Generate all assets
python generate_video.py --mode hybrid

# Preview with audio
python preview_timeline.py --audio assets/background_music.mp3
```

### With Screenshot Capture
```bash
# Capture screenshots (see guide)
# Then regenerate preview
python preview_timeline.py
```

---

## 🔗 Related Documentation

- **Storyboard**: `docs/video-storyboard.md` - Complete shot-by-shot breakdown
- **Screenshot Guide**: `docs/screenshot-capture-guide.md` - How to capture UI shots
- **Generation Script**: `generate_video.py` - Full video generation automation
- **Test Script**: `test_generation.py` - Quick asset testing
- **Quick Start**: `QUICKSTART.md` - 3-day production guide

---

## ⚡ Quick Reference

```bash
# Most common commands

# Initial preview (all placeholders)
python preview_timeline.py

# After generating some assets
python preview_timeline.py

# Fast preview for quick review
python preview_timeline.py --speed 5.0

# Quick GIF for sharing
python preview_timeline.py --speed 10.0 --format gif

# Full preview with audio
python preview_timeline.py --audio assets/background_music.mp3

# Custom output location
python preview_timeline.py --output previews/latest.mp4
```

---

**Next Steps**:
1. Run initial preview to see structure
2. Generate test assets with `test_generation.py`
3. Regenerate preview to see progress
4. Iterate as you add more assets
