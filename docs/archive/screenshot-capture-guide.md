# UI Screenshot Capture Guide

Complete guide for capturing high-quality screenshots for Image-to-Video conversion.

---

## 🎯 Overview

Screenshots will be converted to animated videos using Veo 3.1's Image-to-Video feature. High-quality screenshots = better animated results.

## 📋 Prerequisites

### Browser Setup

1. **Use Incognito/Private Mode**
   - Chrome: `Cmd+Shift+N` (Mac) or `Ctrl+Shift+N` (Windows)
   - Firefox: `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows)
   - Safari: `Cmd+Shift+N` (Mac)

2. **Clean Browser Environment**
   ```bash
   # Checklist:
   - [ ] No browser extensions visible
   - [ ] No bookmarks bar
   - [ ] No other tabs visible
   - [ ] Full screen or consistent window size (1920×1080)
   - [ ] Disable notifications
   ```

3. **Set Window Size**
   ```javascript
   // Open browser console and run:
   window.resizeTo(1920, 1080);

   // Or manually resize to 1920×1080
   ```

### Demo Environment

1. **Populate with Sample Data**
   ```bash
   # Run demo data seed script
   python scripts/seed_demo_data.py

   # Or manually:
   # - Add 7-10 sample meals
   # - Include various food types
   # - Ensure nutrition data is complete
   ```

2. **Use High-Quality Food Images**
   - Resolution: Minimum 1024×1024
   - Good lighting, clear focus
   - Appetizing, colorful meals
   - Sources:
     - Unsplash: `https://unsplash.com/s/photos/food`
     - Pexels: `https://www.pexels.com/search/food/`
     - Your own food photography

---

## 📸 Screenshot List (Required)

### Priority 1: Essential Shots

#### 1. Dashboard/Homepage
**File**: `01_dashboard.png`
**What to Show**:
- Clean, populated dashboard
- 7-day meal log visible
- At least 3-4 meals with photos
- Nutrition stats visible

**How to Capture**:
```bash
# 1. Navigate to homepage
open http://localhost:8080

# 2. Wait for page to fully load
# 3. Take screenshot:
#    Mac: Cmd+Shift+4, then Space, click window
#    Windows: Win+Shift+S
#    Or use browser: Cmd/Ctrl+Shift+P → "Screenshot"
```

---

#### 2. Meal Analysis - Input State
**File**: `02_meal_analysis_input.png`
**What to Show**:
- Upload interface ready
- "Upload Photo" or "Take Photo" button prominent
- Clean, minimal UI
- Before any meal is uploaded

**Camera Setup**:
- Full interface visible
- Capture at moment when button is clickable
- No loading states

---

#### 3. Meal Analysis - Results
**File**: `03_meal_analysis_results.png`
**What to Show**:
- Food photo at top (chicken caesar salad recommended)
- Nutrition breakdown cards:
  - Calories: 450
  - Protein: 35g
  - Carbs: 28g
  - Fat: 22g
- Allergen warnings visible (Dairy, Gluten badges)
- Ingredient list displayed
- Clean layout, all data visible

**Pro Tips**:
- Use a visually appealing food photo
- Ensure all cards/sections have rendered
- Wait for any animations to complete
- Capture "final state" not mid-loading

---

#### 4. Voice Logging Interface
**File**: `05_voice_logging.png`
**What to Show**:
- Microphone icon prominent (center or bottom)
- Either idle state (ready to record) or recording state
- Clean UI, minimal distractions
- Transcription area visible (can be empty or with text)

**States to Capture**:
- **Option A**: Idle state (mic ready, no text)
- **Option B**: Recording state (mic active, "Listening..." indicator)
- **Option C**: Transcribed state (text visible: "Log 3 scrambled eggs...")

Choose Option A or B for animation purposes.

---

#### 5. Function Calling Split Screen
**File**: `06_function_calling.png`
**What to Show**:
- **Left side**: Voice input/command
  - Text: "Log 3 scrambled eggs with toast and coffee"
  - Or: Audio waveform visualization
- **Right side**: JSON output
  ```json
  {
    "tool": "log_meal",
    "params": {
      "meal_name": "Scrambled Eggs & Toast",
      "calories": 380,
      "macros": {
        "protein": 24,
        "carbs": 28,
        "fat": 16
      }
    }
  }
  ```
- Split vertically or horizontally
- Both sides clearly visible

**How to Create**:
If your app doesn't have this view, create manually:
```bash
# Option 1: Use design tool (Figma, Sketch)
# Option 2: Use HTML mockup
# Option 3: Screenshot code editor + voice UI side-by-side
```

---

#### 6. Food Safety Alert
**File**: `08_safety_alert.png`
**What to Show**:
- Alert notification or results page
- Warning icon/badge (⚠️)
- Text: "RECALL ALERT: Romaine lettuce recalled due to E. coli"
- Source citation: "Source: FDA.gov, updated 2 days ago"
- Red/orange color scheme for urgency
- Clear, readable layout

**Mockup if Needed**:
```html
<!-- Create simple HTML mockup if feature not yet built -->
<div style="max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: #fff3e0; border-left: 4px solid #ff9800; padding: 20px; border-radius: 8px;">
    <h2 style="color: #e65100; margin: 0 0 10px 0;">⚠️ RECALL ALERT</h2>
    <p style="font-size: 18px; margin: 10px 0;">
      Romaine lettuce from Farm X recalled due to E. coli
    </p>
    <p style="color: #666; font-size: 14px;">
      📅 Date: 2 days ago<br>
      🔗 Source: FDA.gov
    </p>
  </div>
</div>
```
Screenshot this in browser.

---

### Priority 2: Nice-to-Have

#### 7. CLI Terminal Demo
**File**: `07_cli_terminal.png`
**What to Show**:
- Terminal with FCP CLI command and output
- Dark theme (classic terminal aesthetic)
- Example:
  ```bash
  $ fcp meal analyze --image meal.jpg

  {
    "dish_name": "Grilled Salmon",
    "calories": 350,
    "protein_g": 42,
    ...
  }
  ```

**How to Capture**:
```bash
# 1. Run actual FCP CLI command
fcp meal analyze --image test_meal.jpg

# 2. Take terminal screenshot
#    Mac: Cmd+Shift+4
#    Windows: Win+Shift+S
#    Linux: gnome-screenshot or Spectacle
```

---

#### 8. Gemini Live Conversation
**File**: `09_gemini_live_chat.png`
**What to Show**:
- Chat bubble interface
- Conversation with 3-4 exchanges:
  ```
  You: "I had salmon for lunch"
  Gemini: "Great choice! How was it prepared?"
  You: "Grilled with vegetables"
  Gemini: "Perfect. About how much salmon?"
  ```
- Clean messaging interface (like iMessage)
- Alternating colors for user/AI

**Create Mockup**:
Use design tool or HTML:
```html
<div style="max-width: 400px; margin: 20px auto; font-family: -apple-system, sans-serif;">
  <div style="display: flex; justify-content: flex-end; margin: 10px 0;">
    <div style="background: #007aff; color: white; padding: 12px 16px; border-radius: 18px; max-width: 70%;">
      I had salmon for lunch
    </div>
  </div>
  <div style="display: flex; justify-content: flex-start; margin: 10px 0;">
    <div style="background: #e9e9eb; padding: 12px 16px; border-radius: 18px; max-width: 70%;">
      Great choice! How was it prepared?
    </div>
  </div>
  <!-- Continue conversation -->
</div>
```

---

## 🎨 Screenshot Quality Standards

### Resolution
- **Minimum**: 1920×1080
- **Recommended**: 2560×1440 (scales down nicely)
- **Format**: PNG (lossless, no JPEG artifacts)

### Composition
- **Framing**: Center main UI element
- **Spacing**: Include 50-100px padding around edges
- **No Cropping**: Capture full interface, not partial

### Clarity
- ✅ Sharp focus, no blur
- ✅ High contrast (text readable)
- ✅ Proper lighting (no glare, shadows)
- ✅ Complete loading (no spinners/skeletons)
- ❌ No compression artifacts
- ❌ No browser UI visible (unless intentional)
- ❌ No cursor in frame

### Consistency
- Same browser window size (1920×1080)
- Same zoom level (100%, not 110% or 90%)
- Same theme/styling (light or dark, but consistent)

---

## 🛠️ Capture Tools

### Mac

**Built-in (Recommended)**:
```bash
# Full screen
Cmd + Shift + 3

# Selection area
Cmd + Shift + 4

# Window capture
Cmd + Shift + 4, then Space, click window

# Saves to Desktop by default
```

**Advanced (CleanShot X)**:
- Scrolling captures
- Annotation tools
- Instant sharing
- Download: https://cleanshot.com

---

### Windows

**Built-in (Snipping Tool)**:
```bash
# Open Snipping Tool
Win + Shift + S

# Or
Windows key → type "Snip" → Enter
```

**Advanced (ShareX)**:
- Scrolling captures
- Region capture with annotations
- Download: https://getsharex.com

---

### Linux

**GNOME**:
```bash
gnome-screenshot

# Or
PrtScn key
```

**KDE (Spectacle)**:
```bash
spectacle
```

---

## 📁 File Organization

### Directory Structure
```
screenshots/
├── 01_dashboard.png                  # Homepage
├── 02_meal_analysis_input.png        # Before upload
├── 03_meal_analysis_results.png      # After analysis
├── 05_voice_logging.png              # Voice interface
├── 06_function_calling.png           # Split screen
├── 08_safety_alert.png               # Recall alert
├── 07_cli_terminal.png               # Optional: CLI
├── 09_gemini_live_chat.png           # Optional: Chat
└── README.md                          # This file
```

### Naming Convention
- Use `01`, `02`, `03` prefixes for ordering
- Descriptive names: `meal_analysis_input` not `screenshot2`
- All lowercase, underscores for spaces
- PNG format only

---

## ✅ Quality Checklist

Before using screenshots for video generation:

### Technical
- [ ] Resolution: 1920×1080 or higher
- [ ] Format: PNG (not JPG)
- [ ] File size: < 5 MB each
- [ ] No compression artifacts visible
- [ ] Sharp focus throughout

### Content
- [ ] UI fully loaded (no loading states)
- [ ] All text readable
- [ ] No sensitive data visible (emails, API keys)
- [ ] Sample data looks realistic
- [ ] Color scheme consistent across all shots

### Composition
- [ ] Main UI element centered
- [ ] Adequate padding around edges
- [ ] No browser UI visible (unless intentional)
- [ ] No cursor visible
- [ ] Window size consistent (all 1920×1080)

---

## 🚀 Quick Start

### Minimal Setup (15 minutes)

1. **Prepare Environment**
   ```bash
   # Start FCP server
   cd fcp-gemini-server
   make dev-http

   # Seed demo data
   python scripts/seed_demo_data.py
   ```

2. **Open in Browser**
   ```bash
   # Incognito mode
   open -na "Google Chrome" --args --incognito http://localhost:8080
   ```

3. **Resize Window**
   ```javascript
   // In browser console
   window.resizeTo(1920, 1080);
   ```

4. **Capture Screenshots**
   ```bash
   # Create screenshots directory
   mkdir -p screenshots

   # Navigate through app, capture each view
   # Mac: Cmd+Shift+4 → Space → Click window
   # Save to screenshots/ folder
   ```

5. **Verify**
   ```bash
   # Check all required screenshots present
   ls -lh screenshots/*.png

   # Should see:
   # 01_dashboard.png
   # 02_meal_analysis_input.png
   # 03_meal_analysis_results.png
   # ... (at least 6 files)
   ```

---

## 🎬 Test Image-to-Video Conversion

After capturing screenshots, test conversion:

```python
import google.generativeai as genai

genai.configure(api_key="YOUR_API_KEY")

# Test with one screenshot
video = genai.generate_video_from_image(
    model="veo-3.1",
    source_image="screenshots/02_meal_analysis_input.png",
    prompt="Smooth zoom in on the interface, highlighting the upload button",
    duration=5,
    resolution="1080p"
)

video.save("test_conversion.mp4")
print("Test conversion complete! Check test_conversion.mp4")
```

If this works, your screenshots are ready for full generation!

---

## 🔍 Troubleshooting

### Problem: Screenshots look blurry

**Cause**: Browser zoom or window scaling

**Solution**:
```bash
# Check browser zoom (should be 100%)
# Mac: Cmd+0 (reset zoom)
# Windows: Ctrl+0

# Check system display scaling
# Mac: System Preferences → Displays → Default
# Windows: Settings → Display → 100% scale
```

---

### Problem: UI elements cut off

**Cause**: Window too small

**Solution**:
```javascript
// Force window size in console
window.resizeTo(1920, 1080);

// Or capture with scrolling tool (CleanShot X, ShareX)
```

---

### Problem: Text too small to read

**Cause**: High-DPI display capturing at wrong scale

**Solution**:
```bash
# Mac: Capture in Retina resolution, downscale later
# Use CleanShot X or Retina DisplayMenu

# Windows: Adjust display scaling before capture
```

---

## 📚 Additional Resources

- **Stock Food Photos**: https://unsplash.com/s/photos/healthy-food
- **UI Mockup Tools**: Figma, Sketch, Adobe XD
- **Browser Extensions**: Full Page Screen Capture, Nimbus Screenshot
- **Video Examples**: See `docs/video-storyboard.md` for animation descriptions

---

## 💡 Pro Tips

1. **Batch Capture**: Set up all views, capture in sequence (5 min total)
2. **Use Real Data**: Fake data looks fake in video. Use appetizing photos.
3. **Consistent Styling**: Don't change themes mid-screenshot
4. **Test Early**: Convert one screenshot to video first, verify quality
5. **Keep Originals**: Save unedited screenshots, edit copies if needed

---

**Next Step**: Run `python generate_video.py --mode hybrid` to convert screenshots to animated videos!
