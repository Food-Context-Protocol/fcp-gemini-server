# Code Review: preview_timeline.py

## Overall Assessment

**Current Quality**: 6/10 - Functional but needs significant refactoring

**Strengths**:
- ✅ Good type hints throughout
- ✅ Uses dataclasses appropriately
- ✅ Pathlib instead of os.path
- ✅ Clear CLI interface with argparse
- ✅ Good progress indicators with Rich
- ✅ Comprehensive docstrings on main methods

**Weaknesses**:
- ❌ Massive DRY violations (283 lines of hardcoded data)
- ❌ Poor testability (tight coupling, no dependency injection)
- ❌ Long methods (125+ lines)
- ❌ Duplicated logic in multiple places
- ❌ Bare except clauses
- ❌ Magic numbers throughout
- ❌ Unused instance variable (`audio_clips`)

---

## 🔴 Critical Issues

### 1. DRY Violation - Hardcoded Timeline (Lines 75-362)

**Problem**: 283 lines of repetitive `shots.append(Shot(...))` calls

**Impact**:
- Hard to maintain
- Impossible to test in isolation
- Can't easily reuse for different storyboards
- Violates Single Responsibility Principle

**Solution**: Extract to configuration file

```python
# BEFORE (current)
def _build_timeline(self) -> List[Shot]:
    shots = []
    shots.append(Shot(number=1, name="Opening Title", ...))
    shots.append(Shot(number=2, name="Problem Statement", ...))
    # ... 23 more times
    return shots

# AFTER (recommended)
def _load_timeline_from_config(self, config_path: Path) -> List[Shot]:
    """Load timeline from JSON configuration file"""
    with open(config_path) as f:
        data = json.load(f)

    shots = []
    for shot_data in data['shots']:
        asset_path = None
        if shot_data.get('asset_name'):
            asset_path = self._find_asset(
                shot_data['asset_name'],
                shot_data.get('asset_extensions', ['png', 'jpg'])
            )

        shots.append(Shot(
            number=shot_data['number'],
            name=shot_data['name'],
            start_time=shot_data['start_time'],
            duration=shot_data['duration'],
            act=shot_data['act'],
            audio_description=shot_data['audio_description'],
            visual_description=shot_data['visual_description'],
            asset_path=asset_path
        ))

    return shots
```

**Files Created**: `timeline_config.json` with all shot data

**Benefits**:
- Easy to modify timeline without touching code
- Can have multiple timeline configs
- Testable with small mock configs
- Reduces code from 283 lines to ~20 lines

---

### 2. Duplicated Act Color Logic (Lines 423-428, 587-592)

**Problem**: Same act color determination appears twice

```python
# Appears in _create_placeholder_frame() AND _create_frame_with_asset()
if "Act 1" in shot.act:
    act_color = self.colors['act1']
elif "Act 2" in shot.act:
    act_color = self.colors['act2']
else:
    act_color = self.colors['act3']
```

**Solution**: Extract to helper method

```python
def _get_act_color(self, act: str) -> str:
    """Get color for act"""
    if "Act 1" in act:
        return self.colors['act1']
    elif "Act 2" in act:
        return self.colors['act2']
    else:
        return self.colors['act3']

# Usage
act_color = self._get_act_color(shot.act)
```

---

### 3. Duplicated Timing Format (Lines 503, 629)

**Problem**: Timing text formatting duplicated

```python
# Line 503
timing_text = f"{int(shot.start_time // 60)}:{int(shot.start_time % 60):02d} - {int(end_time // 60)}:{int(end_time % 60):02d}"

# Line 629 (slightly different)
timing_text = f"⏱️  {int(shot.start_time // 60)}:{int(shot.start_time % 60):02d} - {int(end_time // 60)}:{int(end_time % 60):02d} ({shot.duration}s)"
```

**Solution**: Extract to helper method

```python
def _format_time(self, seconds: float) -> str:
    """Format seconds as MM:SS"""
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"

def _format_time_range(self, start: float, end: float, include_duration: bool = False) -> str:
    """Format time range with optional duration"""
    range_text = f"{self._format_time(start)} - {self._format_time(end)}"
    if include_duration:
        range_text += f" ({end - start:.0f}s)"
    return range_text

# Usage
timing_text = self._format_time_range(shot.start_time, end_time)
timing_text = f"⏱️  {self._format_time_range(shot.start_time, end_time, include_duration=True)}"
```

---

### 4. Long Methods - Poor Testability

**Problem**: Methods are too long and do too much

**Examples**:
- `_build_timeline()`: 283 lines (should be config loading)
- `_create_placeholder_frame()`: 125 lines (mixing layout logic)
- `_create_frame_with_asset()`: 75 lines (mixing layout logic)

**Solution**: Split into smaller, focused methods

```python
# BEFORE: _create_placeholder_frame() does everything

# AFTER: Split into focused methods
def _create_placeholder_frame(self, shot: Shot) -> Image.Image:
    """Create placeholder frame - orchestration only"""
    img = self._create_base_frame(shot)
    draw = ImageDraw.Draw(img)
    act_color = self._get_act_color(shot.act)

    self._draw_top_bar(img, act_color)
    self._draw_placeholder_box(img, shot, act_color)
    self._draw_bottom_info(img, shot, act_color)
    self._draw_audio_description(img, shot)

    return img

def _draw_top_bar(self, img: Image.Image, color: str) -> None:
    """Draw colored bar at top"""
    draw = ImageDraw.Draw(img)
    draw.rectangle(
        [(0, 0), (self.width, 10)],
        fill=self._hex_to_rgb(color)
    )

def _draw_placeholder_box(self, img: Image.Image, shot: Shot, act_color: str) -> None:
    """Draw central placeholder box with shot info"""
    # ... focused logic here

def _draw_bottom_info(self, img: Image.Image, shot: Shot, act_color: str) -> None:
    """Draw bottom info bar with timing and act"""
    # ... focused logic here

def _draw_audio_description(self, img: Image.Image, shot: Shot) -> None:
    """Draw audio description at very bottom"""
    # ... focused logic here
```

**Benefits**:
- Each method is testable in isolation
- Easy to understand what each part does
- Can reuse drawing methods across placeholder and asset frames
- Easier to modify layout

---

## 🟡 Medium Issues

### 5. Bare Except Clauses (Lines 405, 786)

**Problem**: Catching all exceptions silently

```python
# Line 405
try:
    return ImageFont.truetype(font_path, size)
except:  # BAD: catches KeyboardInterrupt, SystemExit, etc
    continue

# Line 786
try:
    duration = float(subprocess.check_output(probe_cmd).decode().strip())
    console.print(f"  Duration: {int(duration // 60)}:{int(duration % 60):02d}")
except:  # BAD
    pass
```

**Solution**: Catch specific exceptions

```python
# GOOD
try:
    return ImageFont.truetype(font_path, size)
except (OSError, IOError) as e:
    # Font file not found or invalid
    continue

try:
    duration = float(subprocess.check_output(probe_cmd).decode().strip())
    console.print(f"  Duration: {int(duration // 60)}:{int(duration % 60):02d}")
except (subprocess.CalledProcessError, ValueError) as e:
    # ffprobe failed or returned invalid duration
    pass
```

---

### 6. Magic Numbers Throughout

**Problem**: Hardcoded values with no explanation

```python
box_width = 1200  # Why 1200?
box_height = 675  # Why 675?
box_x = (self.width - box_width) // 2
box_y = (self.height - box_height) // 2 - 50  # Why -50?

# Font sizes
font_huge = self._get_font(120, bold=True)  # Why 120?
font_large = self._get_font(48, bold=True)  # Why 48?
font_medium = self._get_font(28)  # Why 28?
```

**Solution**: Extract to constants or config

```python
# At class level or config
class LayoutConfig:
    """Layout configuration for frame rendering"""
    PLACEHOLDER_BOX_WIDTH = 1200  # 16:9 aspect ratio scaled
    PLACEHOLDER_BOX_HEIGHT = 675  # 1200 / 16 * 9
    PLACEHOLDER_Y_OFFSET = -50  # Shift up slightly from center

    FONT_SIZE_HUGE = 120  # Shot number
    FONT_SIZE_LARGE = 48  # Shot name
    FONT_SIZE_MEDIUM = 28  # Description text
    FONT_SIZE_SMALL = 24  # Info bar
    FONT_SIZE_AUDIO = 20  # Audio description

    TOP_BAR_HEIGHT = 10
    BOTTOM_OVERLAY_HEIGHT = 120

    # Margins
    SIDE_MARGIN = 50
    CONTENT_PADDING = 100

# Usage
box_width = LayoutConfig.PLACEHOLDER_BOX_WIDTH
box_height = LayoutConfig.PLACEHOLDER_BOX_HEIGHT
font_huge = self._get_font(LayoutConfig.FONT_SIZE_HUGE, bold=True)
```

---

### 7. Unused Instance Variable

**Problem**: `self.audio_clips` defined but never used

```python
# Line 59
self.audio_clips = {}  # Map shot number to audio file path
# Never referenced anywhere in the code
```

**Solution**: Either use it or remove it

If planning to use:
```python
def _load_audio_clips(self, audio_dir: Path) -> None:
    """Load audio clips for shots"""
    if not audio_dir.exists():
        return

    for shot in self.shots:
        audio_file = audio_dir / f"shot_{shot.number:03d}.mp3"
        if audio_file.exists():
            self.audio_clips[shot.number] = str(audio_file)
```

If not using: Remove line 59

---

### 8. No Input Validation

**Problem**: No validation of inputs

```python
def __init__(self, output_dir: str = "preview_output"):
    self.output_dir = Path(output_dir)
    # What if output_dir is invalid? What if permissions denied?

    self.width = 1920  # What if someone sets fps=0? Or negative?
    self.height = 1080
    self.fps = 30
```

**Solution**: Add validation

```python
def __init__(self, output_dir: str = "preview_output", width: int = 1920,
             height: int = 1080, fps: int = 30):
    """
    Args:
        output_dir: Directory for output files
        width: Video width in pixels (must be > 0)
        height: Video height in pixels (must be > 0)
        fps: Frames per second (must be > 0 and <= 120)

    Raises:
        ValueError: If dimensions or fps are invalid
        OSError: If output directory cannot be created
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"Dimensions must be positive, got {width}x{height}")
    if fps <= 0 or fps > 120:
        raise ValueError(f"FPS must be between 1 and 120, got {fps}")

    self.width = width
    self.height = height
    self.fps = fps

    try:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    except OSError as e:
        raise OSError(f"Cannot create output directory {output_dir}: {e}")
```

---

## 🟢 Minor Issues

### 9. Missing Type Hints

**Problem**: `_hex_to_rgb` return type not fully specified

```python
# Line 411 - returns Tuple but type system doesn't know it's RGB
def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
```

**Better**: Use a type alias

```python
from typing import Tuple

RGB = Tuple[int, int, int]  # Type alias at module level

def _hex_to_rgb(self, hex_color: str) -> RGB:
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
```

---

### 10. Inconsistent Naming

**Problem**: Mix of naming styles

```python
file_list_path  # snake_case
output_path     # snake_case
frame_paths     # snake_case
# But:
box_width       # also snake_case, but conceptually different (config vs path)
box_height
box_x, box_y    # single letter suffixes
```

**Solution**: Be more consistent with prefixes

```python
# Paths
file_list_path
output_path
frame_paths
temp_dir_path

# Dimensions
layout_box_width
layout_box_height
layout_box_x
layout_box_y

# Or even better: group in dataclass
@dataclass
class BoxLayout:
    width: int
    height: int
    x: int
    y: int

box = BoxLayout(
    width=1200,
    height=675,
    x=(self.width - 1200) // 2,
    y=(self.height - 675) // 2 - 50
)
```

---

## 📊 Test Coverage Analysis

### Current Testability: 3/10

**Hard to Test**:
1. `_build_timeline()` - 283 lines of hardcoded data
2. `create_video()` - subprocess calls not mockable
3. `_create_placeholder_frame()` - 125 lines, many dependencies
4. `generate_frames()` - file I/O side effects

**Easy to Test**:
1. `_hex_to_rgb()` - pure function ✅
2. `_wrap_text()` - mostly pure (creates temp Image) ✅
3. `_find_asset()` - can mock Path.exists() ✅

---

## 🎯 Recommended Refactoring Plan

### Phase 1: Extract Configuration (High Priority)

1. ✅ Create `timeline_config.json` with all shot data
2. Replace `_build_timeline()` with `_load_timeline_from_config()`
3. Add validation for timeline config structure

**Benefit**: Reduces code by 260+ lines, enables testing

---

### Phase 2: Extract Helper Methods (Medium Priority)

1. Extract `_get_act_color()`
2. Extract `_format_time()` and `_format_time_range()`
3. Extract drawing methods from `_create_placeholder_frame()`:
   - `_draw_top_bar()`
   - `_draw_placeholder_box()`
   - `_draw_bottom_info()`
   - `_draw_audio_description()`

**Benefit**: Each method becomes testable, easier to maintain

---

### Phase 3: Extract Constants (Medium Priority)

1. Create `LayoutConfig` dataclass or config dict
2. Replace all magic numbers
3. Make layout configurable

**Benefit**: Easier to customize, self-documenting

---

### Phase 4: Improve Error Handling (Low Priority)

1. Replace bare `except:` with specific exceptions
2. Add input validation to `__init__`
3. Add validation to Shot dataclass

**Benefit**: Better error messages, catches bugs earlier

---

### Phase 5: Dependency Injection (Low Priority)

1. Make FFmpeg wrapper injectable
2. Make file system operations mockable
3. Add interfaces for testability

**Benefit**: Enables unit testing without actual FFmpeg/filesystem

---

## 📝 Example: Refactored _build_timeline()

**Before** (283 lines):
```python
def _build_timeline(self) -> List[Shot]:
    shots = []
    shots.append(Shot(number=1, name="Opening Title", ...))
    # ... 22 more append() calls
    return shots
```

**After** (20 lines):
```python
def _load_timeline_from_config(
    self,
    config_path: Path = Path("timeline_config.json")
) -> List[Shot]:
    """Load timeline from JSON configuration

    Args:
        config_path: Path to timeline config JSON

    Returns:
        List of Shot objects

    Raises:
        FileNotFoundError: If config file doesn't exist
        JSONDecodeError: If config is invalid JSON
        ValidationError: If config structure is invalid
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Timeline config not found: {config_path}")

    with open(config_path) as f:
        data = json.load(f)

    return [self._shot_from_config(shot_data) for shot_data in data['shots']]

def _shot_from_config(self, shot_data: dict) -> Shot:
    """Create Shot from config dictionary"""
    asset_path = None
    if shot_data.get('asset_name'):
        asset_path = self._find_asset(
            shot_data['asset_name'],
            shot_data.get('asset_extensions', ['png', 'jpg'])
        )

    return Shot(
        number=shot_data['number'],
        name=shot_data['name'],
        start_time=shot_data['start_time'],
        duration=shot_data['duration'],
        act=shot_data['act'],
        audio_description=shot_data['audio_description'],
        visual_description=shot_data['visual_description'],
        asset_path=asset_path
    )
```

---

## 🧪 Testing Recommendations

### Unit Tests Needed

```python
# test_timeline_preview.py

def test_hex_to_rgb():
    """Test color conversion"""
    gen = TimelinePreviewGenerator()
    assert gen._hex_to_rgb('#FF0000') == (255, 0, 0)
    assert gen._hex_to_rgb('00FF00') == (0, 255, 0)  # without #

def test_get_act_color():
    """Test act color determination"""
    gen = TimelinePreviewGenerator()
    assert gen._get_act_color("Act 1: Hook") == '#4CAF50'
    assert gen._get_act_color("Act 2: Demo") == '#2196F3'
    assert gen._get_act_color("Act 3: Impact") == '#FF9800'

def test_format_time():
    """Test time formatting"""
    gen = TimelinePreviewGenerator()
    assert gen._format_time(0) == "0:00"
    assert gen._format_time(65) == "1:05"
    assert gen._format_time(3661) == "61:01"

def test_load_timeline_from_config():
    """Test timeline loading"""
    # Create mock config
    config = {
        "shots": [
            {
                "number": 1,
                "name": "Test Shot",
                "start_time": 0,
                "duration": 5,
                "act": "Act 1: Hook",
                "audio_description": "Test audio",
                "visual_description": "Test visual",
                "asset_name": null
            }
        ]
    }

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        config_path = f.name

    try:
        gen = TimelinePreviewGenerator()
        shots = gen._load_timeline_from_config(Path(config_path))
        assert len(shots) == 1
        assert shots[0].name == "Test Shot"
    finally:
        os.unlink(config_path)
```

### Integration Tests Needed

```python
def test_generate_preview_end_to_end():
    """Test complete preview generation"""
    # Requires FFmpeg installed
    with tempfile.TemporaryDirectory() as tmpdir:
        gen = TimelinePreviewGenerator(output_dir=tmpdir)
        output = gen.generate_preview(
            output_path=f"{tmpdir}/test.mp4",
            speed_multiplier=10.0  # Fast for testing
        )
        assert Path(output).exists()
        assert Path(output).stat().st_size > 0
```

---

## Summary Score

| Category | Current Score | Potential Score |
|----------|--------------|-----------------|
| Organization | 6/10 | 9/10 |
| DRY | 3/10 | 9/10 |
| Testability | 3/10 | 9/10 |
| Python Practices | 7/10 | 9/10 |
| Maintainability | 4/10 | 9/10 |
| **Overall** | **4.6/10** | **9/10** |

## Time to Refactor

**Estimated effort**:
- Phase 1 (Config extraction): 2 hours
- Phase 2 (Helper methods): 3 hours
- Phase 3 (Constants): 1 hour
- Phase 4 (Error handling): 1 hour
- Phase 5 (DI for testing): 2 hours
- **Total**: 9 hours

**Priority**: Phase 1 and 2 should be done before adding new features.

---

## Conclusion

The code **works** but is **not production-ready** in its current form. Main issues:

1. **283 lines of hardcoded data** (CRITICAL)
2. **Duplicated logic** in multiple places (HIGH)
3. **Long, untestable methods** (HIGH)
4. **Magic numbers everywhere** (MEDIUM)

**Recommendation**: Refactor Phase 1-2 before using in production. The current version is fine for a prototype/demo.
