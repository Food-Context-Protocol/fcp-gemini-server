# Logo Generators Comparison

Comparison of logo generation scripts across projects: humboldt-tech, foodlog-fcp, and FCP.

---

## Overview

| Project | Script Location | Primary Use Case | Model Used |
|---------|----------------|------------------|------------|
| **humboldt.tech** | `humboldt-tech-branding/generate_logo.py` | Tech organization wordmark | Gemini 3 Pro Image (Nano Banana Pro) |
| **FoodLog (Legacy)** | `foodlog-fcp/scripts/generate_logo.py` | Food tracking app icon | Gemini 2.0 Flash Exp |
| **FCP (Current)** | `fcp-gemini-server/scripts/generate_logo.py` | Multi-style protocol branding | Gemini 3 Pro Image + Flash |

---

## Feature Comparison

### Basic Features

| Feature | humboldt.tech | FoodLog | FCP |
|---------|---------------|---------|-----|
| **CLI Arguments** | Single custom prompt | Single custom prompt | Full argparse with styles |
| **Predefined Styles** | 1 (wordmark) | 1 (icon) | 6 (wordmark, icon, full, badge, monochrome, social) |
| **Model Selection** | Pro only | Flash only | Pro + Flash (switchable) |
| **Output Flexibility** | Fixed filename | Auto-calculated path | Custom path + auto-generated |
| **Error Handling** | Basic | Basic | Comprehensive |
| **Documentation** | Inline comments | Inline comments | Extensive docstrings + external README |

---

### Prompt Engineering

| Feature | humboldt.tech | FoodLog | FCP |
|---------|---------------|---------|-----|
| **Default Prompt Quality** | ⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Exceptional |
| **Prompt Specificity** | Detailed text requirements | Clear icon requirements | Detailed per-style requirements |
| **Color Specification** | Black/white + accent hint | 2-color palette | 5-color brand palette |
| **Size Specification** | Implicit | Implicit | Explicit (per style) |
| **Brand Consistency** | Simple, minimal | Simple food app | Comprehensive brand system |

---

### Code Quality

| Aspect | humboldt.tech | FoodLog | FCP |
|--------|---------------|---------|-----|
| **Python Style** | Clean, simple | Clean, robust | Professional, comprehensive |
| **Type Hints** | ✅ Full | ✅ Full | ✅ Full |
| **Error Messages** | ✅ Clear | ✅ Clear | ✅ Clear + actionable |
| **Path Handling** | ✅ Pathlib | ✅ Pathlib + mkdir | ✅ Pathlib + mkdir |
| **API Key Check** | ✅ Present | ✅ Present | ✅ Present |
| **Success Output** | ⭐⭐ Basic | ⭐⭐ Basic | ⭐⭐⭐ Comprehensive |

---

## Detailed Analysis

### 1. humboldt.tech Logo Generator

**Strengths:**
- ✅ Uses best model (Gemini 3 Pro Image - Nano Banana Pro)
- ✅ Clean, focused on wordmark logos
- ✅ Excellent default prompt for tech branding
- ✅ Simple CLI (easy to use)

**Weaknesses:**
- ❌ Only generates one style (wordmark)
- ❌ No model selection (locked to Pro)
- ❌ Limited customization options
- ❌ Basic success output

**Best For:**
- Quick wordmark generation
- Tech organization branding
- Simple text-based logos

**Code Snippet:**
```python
# Simple, focused approach
def generate_logo(
    prompt: str = DEFAULT_PROMPT,
    model: str = "pro",
    output_path: str = "humboldt-tech-logo.png",
) -> str | None:
```

---

### 2. FoodLog Logo Generator (Legacy)

**Strengths:**
- ✅ Robust path handling (creates directories)
- ✅ Clear food-focused icon prompt
- ✅ Good for app icon generation
- ✅ Calculates relative paths intelligently

**Weaknesses:**
- ❌ Uses older Flash model (not Pro)
- ❌ Only generates one style (icon)
- ❌ Limited CLI (no style selection)
- ❌ Less detailed prompts

**Best For:**
- App icon generation
- Quick food-related icons
- Testing and iteration

**Code Snippet:**
```python
# Robust directory handling
output_file = Path(output_path)
output_file.parent.mkdir(parents=True, exist_ok=True)
```

---

### 3. FCP Logo Generator (Current)

**Strengths:**
- ✅ Comprehensive style system (6 predefined styles)
- ✅ Full CLI with argparse (professional)
- ✅ Switchable models (Pro + Flash)
- ✅ Detailed brand color palette
- ✅ Extensive documentation
- ✅ Custom prompt support
- ✅ Batch generation (`--all` flag)
- ✅ Professional success output with next steps

**Weaknesses:**
- ⚠️ More complex (may be overkill for simple use cases)
- ⚠️ Requires understanding of different styles

**Best For:**
- Complete brand system generation
- Professional logo suites
- Multiple logo variations
- Production use

**Code Snippet:**
```python
# Professional CLI with multiple options
parser.add_argument(
    "--style",
    choices=list(LOGO_PROMPTS.keys()),
    default="wordmark",
    help="Logo style to generate (default: wordmark)",
)
parser.add_argument(
    "--all",
    action="store_true",
    help="Generate all logo styles",
)
```

---

## Model Comparison

### Gemini 3 Pro Image (Nano Banana Pro)
**Used by:** humboldt.tech, FCP

**Characteristics:**
- ✅ Best quality (4K capable)
- ✅ Excellent for text rendering
- ✅ Best for final production logos
- ❌ Slower (~30-60 seconds)
- ❌ Higher cost

### Gemini 2.5 Flash Image (Nano Banana)
**Used by:** FCP (optional)

**Characteristics:**
- ✅ Fast generation (~10-20 seconds)
- ✅ Good quality
- ✅ Great for iteration
- ❌ Not quite Pro quality
- ✅ Lower cost

### Gemini 2.0 Flash Exp
**Used by:** FoodLog (legacy)

**Characteristics:**
- ✅ Fast experimental model
- ⚠️ Experimental/preview status
- ⚠️ May be deprecated
- ❌ Lower quality than Pro
- ✅ Good for testing

---

## Prompt Engineering Evolution

### Generation 1: humboldt.tech (Simple Text)
```python
DEFAULT_PROMPT = """Create a clean, minimalist wordmark logo for "humboldt.tech"

Requirements:
- All lowercase text: "humboldt.tech"
- Modern, professional sans-serif font
- Simple black text on white background
"""
```

**Analysis:** ⭐⭐⭐⭐
- Clear and concise
- Focuses on typography
- Good for simple wordmarks

---

### Generation 2: FoodLog (Icon Focus)
```python
DEFAULT_PROMPT = """A minimalist, modern app icon for 'FoodLog'.

Requirements:
- Icon features a fork, knife, and spoon arranged in a simple, balanced composition
- 2 colors only: Dark Charcoal (#333333) and Fresh Green (#4CAF50)
- Flat vector style
"""
```

**Analysis:** ⭐⭐⭐⭐
- More specific about visual elements
- Includes exact color codes
- Good for icon generation
- Introduces vector style specification

---

### Generation 3: FCP (Comprehensive Brand System)
```python
LOGO_PROMPTS = {
    "wordmark": """Create a clean, modern wordmark logo for "Food Context Protocol"

Requirements:
- Text arrangement: "FOOD CONTEXT PROTOCOL" or "FCP" with full name below
- Modern, professional sans-serif font (like Montserrat, Inter, or SF Pro)
- Color scheme: #2E7D32 (green) for "FOOD", #1976D2 (blue) for "PROTOCOL"
- The word "CONTEXT" could be lighter weight or gray
- Wide format (1400x800px ideal)
- Professional, trustworthy, tech-forward appearance
""",
    # + 5 more detailed styles...
}
```

**Analysis:** ⭐⭐⭐⭐⭐
- Multiple styles for different use cases
- Explicit size requirements
- Font suggestions
- Hierarchical color usage
- Brand personality descriptors
- Comprehensive brand system

---

## Best Practices Learned

### From humboldt.tech:
1. ✅ Use Gemini 3 Pro Image for best quality
2. ✅ Keep prompts focused and specific
3. ✅ Include typography suggestions

### From FoodLog:
1. ✅ Specify exact hex color codes
2. ✅ Request vector-style aesthetic
3. ✅ Ensure output directories exist

### From FCP:
1. ✅ Create multiple style variants
2. ✅ Build comprehensive brand palette
3. ✅ Use argparse for professional CLI
4. ✅ Provide extensive documentation
5. ✅ Include usage examples and next steps
6. ✅ Allow model selection for iteration vs. production

---

## Recommendations

### For Simple Wordmark Logos:
**Use:** humboldt.tech approach
- Minimal code
- Fast to run
- Good for tech branding

### For App Icons Only:
**Use:** FoodLog approach
- Focused on icon generation
- Good prompts for circular icons
- Quick iteration

### For Complete Brand Systems:
**Use:** FCP approach
- Multiple logo styles
- Professional CLI
- Comprehensive documentation
- Production-ready

### For Rapid Prototyping:
**Use:** FCP with Flash model
```bash
python scripts/generate_logo.py --style icon --model flash
```

### For Final Production:
**Use:** FCP with Pro model
```bash
python scripts/generate_logo.py --all --model pro
```

---

## Evolution Summary

```
humboldt.tech (v1)
    ↓
    Simple wordmark generation
    Single style, Pro model
    ↓
FoodLog (v1.5)
    ↓
    Icon-focused generation
    Single style, Flash model, better paths
    ↓
FCP (v2)
    ↓
    Comprehensive brand system
    6 styles, Pro + Flash, full CLI
    Extensive documentation
```

---

## Migration Guide

### From humboldt.tech to FCP:
```bash
# Old way
python generate_logo.py "custom wordmark prompt"

# New way
python scripts/generate_logo.py --style wordmark
# or
python scripts/generate_logo.py --custom "custom wordmark prompt"
```

### From FoodLog to FCP:
```bash
# Old way
python scripts/generate_logo.py

# New way
python scripts/generate_logo.py --style icon
```

---

## Conclusion

The FCP logo generator represents the evolution of logo generation scripts across projects:

1. **humboldt.tech** established the foundation with Pro model usage
2. **FoodLog** added better path handling and icon focus
3. **FCP** combined best practices and added comprehensive brand system

**Key Innovation:** Moving from single-purpose generators to a unified brand system generator with multiple styles, professional CLI, and extensive documentation.

---

**Recommendation for New Projects:**

Start with the **FCP approach** as a template:
- Copy `scripts/generate_logo.py`
- Update `LOGO_PROMPTS` dictionary with your brand
- Update `COLORS` dictionary with your palette
- Customize the 6 styles or add new ones
- Update the documentation

This provides a production-ready logo generation system from day one.

---

**Last Updated:** February 9, 2026
