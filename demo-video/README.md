# FCP Demo Video Production

This directory contains the complete video production pipeline for generating the 3-minute FCP demo video for the Gemini 3 Hackathon.

## Quick Start

```bash
# Install dependencies
pip install Pillow rich

# Generate final video (3:00 duration)
python preview_timeline_animated.py --format mp4 --speed 1.0 --output timeline_final.mp4
```

## Files

### Production Scripts

- **`preview_timeline_animated.py`** - Main production script (RECOMMENDED)
  - Ken Burns zoom effects
  - Animated overlays and text
  - Progress bar indicator
  - Professional motion graphics

- **`preview_timeline_enhanced.py`** - Enhanced static version
  - Consistent design system
  - No animations (simpler)

- **`preview_timeline.py`** - Original script (legacy)
  - Basic functionality
  - Kept for reference

### Configuration

- **`timeline_config.json`** - Complete timeline specification
  - 24 shots, exactly 180 seconds (3:00)
  - Shot timings, descriptions, asset mappings
  - Acts structure (Hook → Demo → Impact)

### Output

- **`timeline_final.mp4`** - Production video
  - 2.2 MB, 1920×1080, 30fps
  - Ready for YouTube upload (unlisted)
  - Meets Gemini 3 Hackathon 3-minute requirement

## Usage

### Generate Full-Speed Video (3 minutes)
```bash
python preview_timeline_animated.py --format mp4 --speed 1.0 --output timeline_final.mp4
```

### Generate Fast Preview (30 seconds)
```bash
python preview_timeline_animated.py --format mp4 --speed 6.0 --output timeline_preview.mp4
```

### Generate GIF Preview (2x speed)
```bash
python preview_timeline_animated.py --format gif --speed 2.0 --output timeline_preview.gif
```

## Features

### Animated Timeline (`preview_timeline_animated.py`)

**Motion Graphics:**
- 🎬 Ken Burns effect (15% zoom over shot duration)
- 📊 Animated progress bar
- 🎯 Circular shot number badges
- ✨ Text fade-in animations
- 🎨 Professional overlay design

**Specifications:**
- 1920×1080 resolution
- 30fps frame rate
- H.264 encoding (MP4)
- Exactly 180 seconds duration

### Enhanced Static (`preview_timeline_enhanced.py`)

**Design System:**
- Consistent colors and typography throughout
- Fixed-size content cards (1400×600px)
- Unified overlay structure
- No motion (simpler generation)

## Assets

Assets are automatically searched in:
- `../assets/` - Project assets (logos, diagrams)
- `../screenshots/` - UI screenshots
- `../test_assets/` - Generated mockups

Asset mapping is configured in `timeline_config.json` via `asset_name` and `asset_extensions`.

## Output Specifications

### For YouTube Upload
- Format: MP4
- Resolution: 1920×1080
- Frame rate: 30fps
- Duration: Exactly 3:00 (180 seconds)
- Size: ~2-3 MB
- Visibility: **Unlisted** (accessible via link, not searchable)

### For Quick Preview
- Format: GIF or MP4
- Speed: 2x-10x multiplier
- Lower quality acceptable for iteration

## Dependencies

```bash
# Required
pip install Pillow rich

# System requirement
brew install ffmpeg  # macOS
```

## Documentation

Full documentation available:
- **[DOCUMENTATION.md](DOCUMENTATION.md)** - Complete technical guide
- **[Video Storyboard](../docs/video-storyboard.md)** - Shot-by-shot breakdown
- **[Screenshot Capture Guide](../docs/screenshot-capture-guide.md)** - Asset creation guide

## Hackathon Submission

**Gemini 3 Hackathon Requirements:**
- ✅ Maximum 3 minutes (we're exactly 3:00)
- ✅ Demonstrates project functionality
- ✅ Upload to YouTube or Vimeo
- ✅ Must be publicly accessible

**Upload as Unlisted:**
1. Upload `timeline_final.mp4` to YouTube
2. Set visibility to **"Unlisted"** (not Private, not Public)
3. Copy video URL
4. Submit URL in Devpost

**Why Unlisted?**
- Judges can access via direct link
- Not searchable or discoverable publicly
- Standard practice for competition submissions

## Development

### Modifying the Timeline

Edit `timeline_config.json` to:
- Adjust shot durations
- Update descriptions
- Change asset mappings
- Reorder shots

### Adding Animations

In `preview_timeline_animated.py`:
- `_apply_ken_burns()` - Zoom/pan effects
- `_add_animated_overlay()` - Text and UI animations
- `_create_transition_frame()` - Crossfades (not currently used)

### Performance

Generation time for full 3-minute video:
- Frame generation: ~2 minutes (5,400 frames)
- FFmpeg encoding: ~30 seconds
- Total: ~2.5 minutes

## Troubleshooting

**FFmpeg not found:**
```bash
brew install ffmpeg  # macOS
```

**PIL/Pillow missing:**
```bash
pip install Pillow
```

**Assets not loading:**
- Check paths in `timeline_config.json`
- Verify files exist in `assets/`, `screenshots/`, or `test_assets/`
- Check file extensions match configuration

**Video too large:**
- Use higher `--speed` multiplier
- Generate GIF instead of MP4 (smaller for previews)
- Reduce resolution in FFmpeg command

## License

Apache-2.0 - See [../LICENSE](../LICENSE)
