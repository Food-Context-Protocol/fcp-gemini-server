# Timeline Preview Generator - Complete Documentation

## Overview

The timeline preview system generates professional animated previews of video storyboards using Python, Pillow (PIL), and FFmpeg. It creates visually consistent frames for all 25 shots in the FCP demo video timeline.

## Files

### Core Scripts

**`preview_timeline_enhanced.py`** - Main production script with consistent design system
- 600+ lines of production-quality Python
- Unified visual design language across all frame types
- Supports both placeholder frames and frames with actual assets
- Consistent typography, spacing, and color system

**`timeline_config.json`** - Timeline configuration
- 25 shots with metadata (timing, descriptions, act structure)
- Asset mapping for screenshots and visual elements
- Total duration: 3:05 (185 seconds)

**`preview_timeline.py`** - Original script (legacy)
- Initial implementation with hardcoded timeline data
- Has known path bug in FFmpeg file list generation
- Kept for reference but not used in production

### Output Files

**`timeline_consistent.gif`** - Latest production preview
- 273.56 MB
- 1:32 duration (2x speed)
- 2,775 frames at 30fps
- Consistent styling across all shots

## Architecture

### Design System

The preview generator implements a **unified design system** ensuring visual consistency:

#### Color Palette
```python
colors = {
    'act1': '#4CAF50',          # Green - Hook
    'act1_light': '#81C784',
    'act1_dark': '#388E3C',
    'act2': '#2196F3',          # Blue - Demo
    'act2_light': '#64B5F6',
    'act2_dark': '#1976D2',
    'act3': '#FF9800',          # Orange - Impact
    'act3_light': '#FFB74D',
    'act3_dark': '#F57C00',
    'background': '#0A0A0A',    # Near black
    'background_light': '#1E1E1E',
    'text': '#FFFFFF',
    'text_dim': '#B0B0B0',
    'accent': '#00BCD4',        # Cyan
    'placeholder': '#2A2A2A',
    'border': '#404040',
}
```

#### Typography Hierarchy
- **Shot titles**: 48pt bold, act-colored
- **Timing info**: 28pt regular, cyan accent
- **Audio descriptions**: 24pt regular, dimmed
- **Large numbers**: 180pt bold, act-colored (placeholders only)
- **Descriptions**: 36pt regular, white text

#### Layout Structure

**All frames share this consistent structure:**

```
┌─────────────────────────────────────────────────┐
│ Top Accent Bar (6px gradient)                   │ ← Act color
├─────────────────────────────────────────────────┤
│                                                  │
│            Content Area                          │
│         (Image or Placeholder)                   │
│                                                  │
│                                                  │
├─────────────────────────────────────────────────┤
│ Info Overlay (180px height)                     │
│ ┌──────────┐                                    │
│ │ [BADGE]  │  Shot X: Title         [ASSET]    │
│ └──────────┘                                    │
│              0:30 → 0:35  •  5s  •  Act 2       │
│              Audio description...                │
└─────────────────────────────────────────────────┘
```

### Key Methods

#### `_add_consistent_overlay(img, shot, has_asset)`
**Purpose**: Applies identical info overlay to all frame types

**Elements added:**
- Top accent bar (6px gradient in act color)
- Bottom info overlay (180px, 220 alpha black)
- Shot title (48pt bold, centered, act-colored)
- Timing metadata (28pt, cyan, formatted as "0:30 → 0:35 • 5s • Act 2")
- Audio description (24pt, dimmed, one line max)
- Status badge (left corner: "✓ ASSET" or "PLACEHOLDER")

**Consistency guarantee**: Same fonts, sizes, spacing, and positioning regardless of frame content type.

#### `_create_enhanced_placeholder(shot)`
**Purpose**: Creates frames for shots without visual assets

**Design:**
- Diagonal gradient background (dark to lighter dark)
- Subtle noise texture overlay (2% blend)
- Large shot number (#1-25) in act color (180pt)
- Visual description (3 lines max, 36pt)
- Consistent overlay applied via `_add_consistent_overlay()`

#### `_create_frame_with_image(shot)`
**Purpose**: Creates frames for shots with actual images/screenshots

**Design:**
- Same gradient background as placeholders
- Asset image centered, properly scaled
- Maximum size: 1820×680px to fit content area
- Consistent overlay applied via `_add_consistent_overlay()`

**Error handling**: Falls back to placeholder if image fails to load

### Frame Generation Pipeline

1. **Load timeline** from `timeline_config.json`
2. **Find assets** in multiple directories:
   - `assets/` - Original assets
   - `screenshots/` - UI screenshots
   - `test_assets/` - Generated mockups
3. **Generate frames** for each shot:
   - Calculate frame count: `duration / speed_multiplier * fps`
   - Create frame (with asset or placeholder)
   - Replicate frame N times for duration
4. **Create video** with FFmpeg:
   - Generate file list with absolute paths
   - Use concat demuxer for assembly
   - For GIF: Scale to 1280px, 10fps
   - For MP4: H.264, CRF 23, 30fps

## Usage

### Basic Generation

```bash
# Generate MP4 at normal speed (3:05 duration)
python preview_timeline_enhanced.py

# Generate GIF at 2x speed (1:32 duration)
python preview_timeline_enhanced.py --format gif --speed 2.0 --output timeline_2x.gif

# Generate fast preview at 10x speed (18.5s duration)
python preview_timeline_enhanced.py --format gif --speed 10.0 --output timeline_fast.gif
```

### Command-Line Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output` | string | `timeline_preview_enhanced.mp4` | Output file path |
| `--format` | `mp4`, `gif` | `mp4` | Output format |
| `--speed` | float | `1.0` | Speed multiplier (higher = faster) |
| `--fps` | int | `30` | Frames per second |

### Speed Multiplier Guide

| Speed | Total Duration | Use Case |
|-------|---------------|----------|
| 1.0x | 3:05 | Full real-time preview |
| 2.0x | 1:32 | Viewable review speed |
| 5.0x | 37s | Quick overview |
| 10.0x | 18.5s | Very fast scan |

**Note**: GIF size increases with duration. 2x speed (1:32) = ~274MB.

## Dependencies

### Required Software

- **Python 3.11+**
- **FFmpeg 8.0+** - Video encoding
  ```bash
  brew install ffmpeg  # macOS
  ```

### Python Packages

- **Pillow (PIL)** - Image generation and manipulation
- **rich** - Beautiful terminal output with progress bars
- **uv** (recommended) - Fast Python package manager

### Installation

```bash
# Using uv (recommended)
uv run --with Pillow --with rich python preview_timeline_enhanced.py

# Or install packages
uv add Pillow rich
python preview_timeline_enhanced.py
```

## Asset Management

### Asset Search Strategy

The generator searches for assets in this order:

1. `assets/` - Original project assets
2. `screenshots/` - Captured UI screenshots
3. `test_assets/` - Generated mockups

### Asset Naming

**From `timeline_config.json`:**
```json
{
  "asset_name": "fcp_logo",
  "asset_extensions": ["png", "jpg"]
}
```

**Search pattern:**
- `assets/fcp_logo.png`
- `assets/fcp_logo.jpg`
- `assets/fcp_logo_test.png`
- `screenshots/fcp_logo.png`
- `test_assets/fcp_logo.png`

### Current Assets

| Shot | Asset Name | Found | Location |
|------|-----------|-------|----------|
| 1 | `fcp_logo` | ✓ | `assets/fcp_logo.png` |
| 6 | `02_meal_analysis_input` | ✓ | `screenshots/02_meal_analysis_input.png` |
| 7-8 | `03_meal_analysis_results` | ✓ | `screenshots/03_meal_analysis_results.png` |
| 10 | `05_voice_logging` | ✓ | `screenshots/05_voice_logging.png` |
| 11-12 | `06_function_calling` | ✓ | `screenshots/06_function_calling.png` |
| 16 | `08_safety_alert` | ✓ | `screenshots/08_safety_alert.png` |
| 18-19 | `09_gemini_live_chat` | ✓ | `screenshots/09_gemini_live_chat.png` |
| 20 | `01_dashboard` | ✓ | `screenshots/01_dashboard.png` |
| 22 | `architecture_diagram` | ✓ | `assets/architecture_diagram.png` |
| Others | - | ✗ | Placeholder frames |

## Design Principles

### Consistency First

Every design element follows strict rules:
- **Same fonts** for equivalent content (titles always 48pt bold)
- **Same spacing** (overlay always 180px high, 20px from edges)
- **Same colors** for semantic meaning (timing always cyan)
- **Same layout** (badge always bottom-left, title always centered)

### Visual Hierarchy

1. **Shot title** - Most prominent, act-colored
2. **Content** - Image or large shot number
3. **Timing/metadata** - Secondary, cyan accent
4. **Audio description** - Tertiary, dimmed

### Progressive Enhancement

- **Placeholders** - Elegant, informative, act-colored
- **With assets** - Same layout, real content instead of number
- **Transitions** - FFmpeg handles smoothly via concat demuxer

### Color as Communication

- **Act 1 (Green)** - Hook, introduction
- **Act 2 (Blue)** - Demo, features
- **Act 3 (Orange)** - Impact, call-to-action

## Development History

### Iteration 1: Basic Preview
- Generated 167-frame timeline
- Plain text on black background
- Proved concept, but not production-ready

### Iteration 2: Enhanced Design
- Added gradients, shadows, card layouts
- Improved typography with Helvetica
- Added act colors and badges
- **Problem**: Inconsistent design between placeholders and asset frames

### Iteration 3: Unified Design System
- Extracted `_add_consistent_overlay()` method
- Applied identical overlay to all frame types
- Standardized all fonts, sizes, and spacing
- **Result**: Professional, consistent preview ready for production

## Technical Challenges & Solutions

### Challenge 1: Path Bug in FFmpeg
**Problem**: FFmpeg file list had relative paths causing "file not found" errors

**Solution**: Use absolute paths in file list:
```python
for frame_path in frame_paths:
    abs_path = Path(frame_path).resolve()
    f.write(f"file '{abs_path}'\n")
```

### Challenge 2: Inconsistent Frame Designs
**Problem**: Placeholder frames had elaborate cards, asset frames had minimal overlays

**Solution**: Extract overlay logic into shared method, apply to both frame types

### Challenge 3: Large GIF Sizes
**Problem**: Full-speed (3:05) GIF would be 400+ MB

**Mitigation**:
- Use speed multipliers (2x recommended)
- Scale to 1280px width for GIF
- Reduce GIF fps to 10 (from 30 for MP4)

### Challenge 4: Font Availability
**Problem**: Fonts vary across macOS, Linux, Windows

**Solution**: Font fallback chain:
```python
font_paths = [
    "/System/Library/Fonts/Helvetica.ttc",  # macOS
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
    "C:\\Windows\\Fonts\\arial.ttf",  # Windows
]
```

## Output Statistics

### Current Production Preview

**File**: `timeline_consistent.gif`
- **Duration**: 1:32 (92.5 seconds)
- **Speed**: 2x (original 3:05)
- **Size**: 273.56 MB
- **Frames**: 2,775 frames
- **Resolution**: 1920×1080 → scaled to 1280×720 for GIF
- **Frame rate**: 30fps generation → 10fps GIF
- **Shots**: 25 total (9 with assets, 16 placeholders)

### Performance

- **Frame generation**: ~3-4 seconds per shot
- **Total generation time**: ~2 minutes for 2,775 frames
- **FFmpeg encoding**: ~30 seconds for GIF
- **Total pipeline**: ~2.5 minutes end-to-end

## YouTube Upload for Submission

### Recommended: Upload as Unlisted

For hackathon/competition submissions (like Gemini 3 Devpost):

**Upload as "Unlisted" video:**
- ✅ Publicly accessible via direct link
- ✅ Can be submitted to Devpost/competition platforms
- ✅ No YouTube account required to view
- ❌ Not searchable on YouTube
- ❌ Not shown on your channel page
- ❌ Not in recommendations or suggested videos

**Steps:**
1. Upload `timeline_final.mp4` to YouTube
2. Set **Visibility → Unlisted** (not Private, not Public)
3. Copy the video URL
4. Paste URL in your submission form

**Why Unlisted?**
- Judges can watch with just the link
- Won't get random views or comments
- Keeps your channel clean
- Standard practice for competition submissions

## Future Enhancements

### Planned Features

1. **AI-Generated Visuals**
   - Use Imagen 3 to generate missing shot visuals
   - Consistent art style across all placeholders

2. **Audio Narration**
   - Generate voiceover with Google Cloud TTS
   - Add background music (Lyria or royalty-free)
   - Sync audio with shot timings

3. **Subtitles/Captions**
   - Burn-in captions for audio descriptions
   - Accessibility compliance

4. **Smooth Transitions**
   - Fade/crossfade between shots
   - Ken Burns effect on static images
   - Zoom/pan animations

5. **Export Formats**
   - YouTube-optimized MP4
   - Social media formats (square, vertical)
   - Individual shot exports for editing

## Troubleshooting

### FFmpeg Not Found
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows (with Chocolatey)
choco install ffmpeg
```

### Python Dependencies Missing
```bash
# Use uv (recommended)
uv run --with Pillow --with rich python preview_timeline_enhanced.py

# Or pip
uv add Pillow rich
```

### Image Not Loading
**Symptoms**: "Could not load image" warning, frame shows placeholder instead

**Checks**:
1. Verify asset exists: `ls -la assets/fcp_logo.png`
2. Check file permissions: `chmod 644 assets/*.png`
3. Validate image format: `file assets/fcp_logo.png`
4. Test manual load:
   ```python
   from PIL import Image
   Image.open("assets/fcp_logo.png").show()
   ```

### GIF Too Large
**Solutions**:
- Increase speed multiplier: `--speed 5.0`
- Reduce resolution in FFmpeg command (edit line 579)
- Use MP4 instead: `--format mp4`

## Contributing

### Code Style

- Follow PEP 8 conventions
- Use type hints for public methods
- Add docstrings for all classes and methods
- Keep methods under 50 lines (extract helpers)

### Testing Changes

```bash
# Quick test with fast preview
python preview_timeline_enhanced.py --format gif --speed 10.0 --output test.gif

# Review output
open test.gif
```

### Pull Request Checklist

- [ ] Consistent with design system (fonts, colors, spacing)
- [ ] Works for both placeholder and asset frames
- [ ] No regression in existing shots
- [ ] Updated documentation
- [ ] Tested on macOS (primary platform)

## License

Apache-2.0 - See [LICENSE](../LICENSE)

---

**Part of**: FCP Gemini Server
**Purpose**: Demo video production
**Status**: Production-ready with consistent design system
