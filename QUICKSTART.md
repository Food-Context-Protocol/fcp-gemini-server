# Quick Start: Hybrid Video Generation

**Goal**: Create a 3-minute demo video in ~15 hours using a hybrid approach (manual recording + AI enhancement).

**Cost**: $50-100 • **Time**: 15 hours over 3 days

---

## 📋 Prerequisites

### Required
- [x] Gemini API key ([get one](https://ai.google.dev))
- [x] Python 3.11+ installed
- [x] FCP server running locally
- [x] 15 hours availability over 3 days

### Optional (but helpful)
- [x] Google Cloud account (for TTS)
- [x] Basic video editing skills
- [x] Screen recording tool (QuickTime, OBS, etc.)

---

## 🚀 Quick Setup (5 minutes)

### 1. Install Dependencies

```bash
# Navigate to project directory
cd fcp-gemini-server

# Install required packages using uv
uv sync

# Verify FFmpeg is installed
ffmpeg -version

# If not installed:
# Mac: brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg
# Windows: https://ffmpeg.org/download.html
```

### 2. Set API Key

```bash
# Set Gemini API key
export GEMINI_API_KEY=your_api_key_here

# Verify it works
python test_generation.py

# Should see: ✓ API access test complete!
```

### 3. Test Asset Generation

```bash
# Generate a test logo (takes ~30 seconds)
python test_generation.py --asset logo

# Check output
open test_assets/fcp_logo_test.png

# If it works, you're ready!
```

### 4. Generate Timeline Preview

```bash
# Create animated preview of entire storyboard
python preview_timeline.py

# This creates timeline_preview.mp4 showing:
# - All 25 shots in sequence
# - Placeholders for assets not yet generated
# - Actual assets when available
# - Shot timings and descriptions

# Output: Full 2:47 video (real-time)

# For quick review (faster preview):
python preview_timeline.py --speed 5.0 --format gif
# Output: ~33 second GIF
```

**Benefits**:
- Visualize complete video structure before generating assets
- Track progress as assets are created
- Share quick previews with team
- Verify timing and flow

---

## 📅 3-Day Production Schedule

### Day 1: Capture & Generate (5 hours)

#### Morning (2 hours): Record Screen Demos

**Option A: Record Everything Manually** (Recommended for beginners)
```bash
# 1. Start FCP server
make dev-http

# 2. Open screen recorder
# Mac: QuickTime (Cmd+Space, type "QuickTime")
# Windows: Win+G (Game Bar)
# Linux: OBS Studio

# 3. Record each feature demo:
#    - Dashboard overview (30 sec)
#    - Meal analysis (45 sec)
#    - Voice logging (30 sec)
#    - Food safety check (30 sec)

# 4. Save recordings to recordings/ folder
```

**Option B: Use Screenshots + AI** (More cost-effective)
```bash
# 1. Follow screenshot guide
open docs/screenshot-capture-guide.md

# 2. Capture 6-8 screenshots (15 min)
mkdir screenshots
# Take screenshots of each feature

# 3. Let AI animate them (Day 2)
```

#### Afternoon (3 hours): Generate AI Assets

```bash
# 1. Generate initial timeline preview (5 min)
python preview_timeline.py
# Shows structure with all placeholders
# Output: timeline_preview.mp4 (2:47)

# 2. Generate logo and graphics
python generate_video.py --mode hybrid

# This generates:
# - FCP logo (Imagen 3)
# - Gemini badge (Imagen 3)
# - Architecture diagram (Imagen 3)
# - Background videos (Veo 3.1) - optional

# Takes ~2-3 hours, runs automatically
# Go take a break, it'll notify when done

# 3. Regenerate preview to see progress
python preview_timeline.py
# Now shows logo and diagrams!
```

---

### Day 2: Audio & Animation (4 hours)

#### Morning (2 hours): Generate Audio

**Music** (AI-generated, optional)
```bash
# Option A: Use Lyria (if available)
# See generate_video.py music generation code

# Option B: Use royalty-free music
# Download from:
# - YouTube Audio Library
# - Free Music Archive
# - Uppbeat (free tier)

# Save as: assets/background_music.mp3
```

**Voiceover** (Choose one)
```bash
# Option A: Record yourself (free)
# 1. Write script from docs/video-storyboard.md
# 2. Record with phone/mic
# 3. Edit with Audacity (free)

# Option B: AI voiceover (requires Google Cloud TTS)
python generate_video.py --mode hybrid
# Includes TTS generation

# Option C: Hire on Fiverr ($25-50)
# Search: "professional voiceover"
```

#### Afternoon (2 hours): Animate Screenshots

```bash
# If you chose Option B (screenshots):
python generate_video.py --mode hybrid --screenshots ./screenshots

# This converts screenshots to animated videos
# using Veo 3.1's Image-to-Video feature

# Takes 1-2 hours for 6-8 screenshots

# Regenerate preview to see all assets
python preview_timeline.py --audio assets/background_music.mp3
# Now includes audio + screenshots!
```

---

### Day 3: Assembly & Export (6 hours)

#### Morning (3 hours): Video Assembly

**Create Timeline File** (`video_timeline.json`)
```json
{
  "total_duration": 180,
  "segments": [
    {
      "name": "title",
      "file": "assets/01_title_sequence.mp4",
      "start": 0,
      "duration": 8,
      "audio": ["assets/background_music.mp3"]
    },
    {
      "name": "demo1",
      "file": "recordings/meal_analysis.mp4",
      "start": 30,
      "duration": 30,
      "audio": ["assets/background_music.mp3", "assets/vo_demo.mp3"]
    }
    // ... add all segments
  ]
}
```

**Assemble with FFmpeg**
```python
# Create assembly script: assemble.py

import ffmpeg
import json

# Load timeline
with open("video_timeline.json") as f:
    timeline = json.load(f)

# Concatenate video clips
clips = [seg["file"] for seg in timeline["segments"]]

# Simple concatenation
concatenated = ffmpeg.concat(*[ffmpeg.input(clip) for clip in clips])

# Add audio
music = ffmpeg.input("assets/background_music.mp3")
mixed = ffmpeg.filter([concatenated, music], 'amix')

# Output
ffmpeg.output(mixed, "fcp_demo_v1.mp4",
              vcodec='libx264',
              acodec='aac').run()

print("✓ Video assembled!")
```

```bash
# Run assembly
python assemble.py

# Output: fcp_demo_v1.mp4
```

#### Afternoon (2 hours): Polish & Export

**Add Text Overlays** (Using iMovie, DaVinci Resolve, or Premiere)
```
1. Import fcp_demo_v1.mp4 into editor
2. Add text overlays:
   - "FOOD CONTEXT PROTOCOL" at 2 seconds
   - Feature labels during demos
   - "api.fcp.dev" at end
3. Export as fcp_demo_v2.mp4
```

**Color Grading** (Optional but recommended)
```python
# Or use FFmpeg color filters
import ffmpeg

stream = ffmpeg.input("fcp_demo_v2.mp4")

# Apply color adjustments
stream = stream.filter('eq',
                      contrast=1.1,
                      brightness=0.05,
                      saturation=1.15)

# Add subtle teal/orange look
stream = stream.filter('curves',
                      red='0/0 0.5/0.48 1/1',
                      green='0/0 0.5/0.52 1/1',
                      blue='0/0.05 0.5/0.5 1/0.95')

ffmpeg.output(stream, "fcp_demo_FINAL.mp4",
             vcodec='libx264',
             preset='slow').run()

print("✓ Final video ready!")
```

#### Final Hour: Quality Check

```bash
# Check duration
ffprobe -v error -show_entries format=duration \
        -of default=noprint_wrappers=1:nokey=1 fcp_demo_FINAL.mp4

# Should be: 175-185 seconds (2:55 - 3:05)

# Check resolution
ffprobe -v error -select_streams v:0 -show_entries \
        stream=width,height -of csv=s=x:p=0 fcp_demo_FINAL.mp4

# Should be: 1920x1080

# Check file size
ls -lh fcp_demo_FINAL.mp4

# Should be: < 500 MB
```

**Validation Checklist**
- [ ] Duration: 2:55 - 3:05 (under 3:00 for judges)
- [ ] Resolution: 1920×1080
- [ ] Format: MP4 (H.264)
- [ ] Audio: Clear, no clipping
- [ ] Text: All overlays readable
- [ ] Quality: No compression artifacts
- [ ] Content: Shows all 4 features (image analysis, function calling, grounding, live API)

---

## 🎯 Simplified Workflow (Choose One)

### Path A: Maximum AI (Expensive but Fast)
```bash
# Day 1
python generate_video.py --mode full

# Day 2-3
# Assemble with FFmpeg
# Add text overlays
# Export

# Cost: ~$150 • Time: 10 hours
```

### Path B: Hybrid (Recommended)
```bash
# Day 1
# Take screenshots (Option B)
python generate_video.py --mode hybrid --screenshots ./screenshots

# Day 2
# Record voiceover yourself (free)
# Or use TTS

# Day 3
# Assemble in video editor
# Add text overlays
# Export

# Cost: ~$75 • Time: 15 hours
```

### Path C: Minimal AI (Cheapest)
```bash
# Day 1-2
# Record all demos yourself
# Find royalty-free music
# Record voiceover

# Day 3
# Use Imagen for logo only
python test_generation.py --asset logo

# Assemble in video editor
# Add text overlays
# Export

# Cost: ~$25 • Time: 12 hours
```

---

## 💰 Cost Breakdown (Hybrid Path)

| Item | Cost | Notes |
|------|------|-------|
| **Imagen 3** | $15-20 | Logo, badge, diagram (3-4 images) |
| **Veo 3.1** | $40-60 | Title sequence + backgrounds (5-8 clips) |
| **Gemini TTS** | $5-10 | Voiceover narration (500 words) |
| **Royalty-free music** | $0-15 | Free options available |
| **TOTAL** | **$60-105** | |

**Cost Savings**:
- Record demos yourself: Save $30-50 (vs Veo Image-to-Video)
- Use free music: Save $15
- Record own voiceover: Save $10

**Minimum cost**: ~$20 (just logo + basics)

---

## 🛠️ Tools You'll Need

### Free Options
- **Video Editor**: iMovie (Mac), DaVinci Resolve (all platforms)
- **Screen Recorder**: QuickTime (Mac), OBS Studio (all platforms)
- **Audio Editor**: Audacity (free)
- **Music**: YouTube Audio Library, Free Music Archive

### Paid Options (Optional)
- **Video Editor**: Final Cut Pro ($300), Adobe Premiere ($21/mo)
- **Screen Recorder**: CleanShot X ($29)
- **Music**: Epidemic Sound ($15/mo), Artlist ($16/mo)

---

## 📚 Reference Materials

### In This Repo
- Full storyboard: `docs/video-storyboard.md`
- Screenshot guide: `docs/screenshot-capture-guide.md`
- Preview tool guide: `docs/preview-tool-guide.md`
- Original video script: `/Users/jwegis/Projects/fcp-protocol/video-script.md`

### Scripts
- Test generation: `test_generation.py`
- Full generation: `generate_video.py`
- Timeline preview: `preview_timeline.py`

### External Resources
- Gemini API Docs: https://ai.google.dev/gemini-api/docs
- FFmpeg Guide: https://ffmpeg.org/documentation.html
- DaVinci Resolve: https://www.blackmagicdesign.com/products/davinciresolve

---

## ⚡ Quick Commands

```bash
# Test API access
python test_generation.py

# Generate single test asset
python test_generation.py --asset logo

# Generate timeline preview (shows progress)
python preview_timeline.py

# Fast preview GIF for quick review
python preview_timeline.py --speed 5.0 --format gif

# Full hybrid generation
python generate_video.py --mode hybrid

# Preview with audio
python preview_timeline.py --audio assets/background_music.mp3

# Assemble video
python assemble.py

# Check video duration
ffprobe -v error -show_entries format=duration \
        -of default=noprint_wrappers=1:nokey=1 video.mp4

# Compress video
ffmpeg -i input.mp4 -vcodec libx264 -crf 23 output.mp4
```

---

## 🚨 Common Issues

### "GEMINI_API_KEY not set"
```bash
export GEMINI_API_KEY=your_key_here

# Make permanent (add to ~/.bashrc or ~/.zshrc):
echo 'export GEMINI_API_KEY=your_key_here' >> ~/.zshrc
source ~/.zshrc
```

### "Rate limit exceeded"
Wait 10-15 minutes, then retry. Or use Veo 3.1 Fast instead of full Veo.

### "Video too large (>500 MB)"
```bash
# Compress with CRF
ffmpeg -i input.mp4 -vcodec libx264 -crf 23 output.mp4

# CRF 23 = good quality, reasonable size
```

### "Audio out of sync"
Use video editor (iMovie, DaVinci) to manually sync audio to video.

---

## ✅ Success Checklist

Before uploading to Devpost:

- [ ] Duration: Under 3:00 (2:55 ideal)
- [ ] Shows FCP features working
- [ ] Mentions "Gemini 3" explicitly
- [ ] Audio clear and balanced
- [ ] Text readable at 1080p
- [ ] No sensitive data visible
- [ ] Uploaded to YouTube (unlisted OK)
- [ ] Tested playback on multiple devices

---

## 🎬 You're Ready!

Run this to get started:

```bash
# 1. Test API
python test_generation.py

# 2. Generate test asset
python test_generation.py --asset logo

# 3. Generate timeline preview (see the structure!)
python preview_timeline.py

# 4. If test works, start full generation
python generate_video.py --mode hybrid

# 5. Regenerate preview as assets are created
python preview_timeline.py

# 6. Follow the 3-day schedule above
```

**Preview Tool Benefits**:
- See complete video structure before generating
- Track progress as you add assets
- Verify timing and transitions
- Share quick previews with team/judges
- Automatically updates when you regenerate

**Questions?** Check `docs/video-storyboard.md` and `docs/preview-tool-guide.md` for detailed guidance.

**Good luck! 🚀**
