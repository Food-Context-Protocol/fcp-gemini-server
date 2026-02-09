# FCP Logo Generation Guide

This guide covers logo generation for the Food Context Protocol using Gemini 3 Pro Image (Nano Banana Pro).

---

## Quick Start

```bash
# Set your Gemini API key
export GEMINI_API_KEY=your-api-key

# Generate default wordmark logo
python scripts/generate_logo.py

# Generate all logo styles
python scripts/generate_logo.py --all

# Generate specific style
python scripts/generate_logo.py --style icon
```

---

## Available Logo Styles

### 1. Wordmark (`--style wordmark`)
**Use for:** GitHub headers, documentation headers, website navigation

**Description:**
- Text-based logo: "Food Context Protocol" or "FCP"
- Modern sans-serif typography
- Color hierarchy: Green for "FOOD", Blue for "PROTOCOL", lighter "CONTEXT"
- Wide format (1400x800px)
- Professional, clean, legible

**Best for:** Headers, banners, documentation

---

### 2. Icon (`--style icon`)
**Use for:** App icons, favicons, avatars, profile pictures

**Description:**
- Circular app icon
- Food + tech symbol (fork/spoon + data nodes/circuits)
- 2-3 colors: Green, Orange, White
- Flat vector style
- Square format (1024x1024px)
- Recognizable at small sizes

**Best for:** GitHub avatar, mobile app icon, favicon, Discord server icon

---

### 3. Full Logo (`--style full`)
**Use for:** Website headers, presentations, official documents

**Description:**
- Horizontal layout: Icon + Wordmark
- Icon on left, text on right
- Balanced composition
- Wide format (1600x600px)
- Professional, complete branding

**Best for:** Website headers, slide decks, official communications

---

### 4. Badge (`--style badge`)
**Use for:** Certificates, seals, official materials

**Description:**
- Circular badge design (emblem/seal style)
- Text curved around outer ring: "FOOD CONTEXT PROTOCOL"
- Icon in center
- Professional, authoritative
- Square format (1200x1200px)

**Best for:** Certificates, documentation watermarks, official seals

---

### 5. Monochrome (`--style monochrome`)
**Use for:** Print materials, black-and-white documentation

**Description:**
- Pure black on white
- Minimal, clean design
- Works at any size
- High contrast
- Format: 1400x800px (wordmark) or 1024x1024px (icon)

**Best for:** Print materials, faxes (!), academic papers, minimalist designs

---

### 6. Social (`--style social`)
**Use for:** Social media profiles

**Description:**
- Square format (1200x1200px)
- "FCP" text or icon or both
- Optimized for Twitter, LinkedIn, GitHub, Discord
- Bold, recognizable at thumbnail sizes
- Colors: Green and Orange

**Best for:** Social media profile pictures, community avatars

---

## Usage Examples

### Generate All Styles
```bash
python scripts/generate_logo.py --all
```

This creates:
- `static/logos/fcp-wordmark.png`
- `static/logos/fcp-icon.png`
- `static/logos/fcp-full.png`
- `static/logos/fcp-badge.png`
- `static/logos/fcp-monochrome.png`
- `static/logos/fcp-social.png`

---

### Generate Specific Style
```bash
# Wordmark for documentation
python scripts/generate_logo.py --style wordmark

# Icon for GitHub avatar
python scripts/generate_logo.py --style icon

# Full logo for website
python scripts/generate_logo.py --style full
```

---

### Custom Prompt
```bash
# Custom design
python scripts/generate_logo.py --custom "geometric fork icon with green gradient"

# Alternative wordmark style
python scripts/generate_logo.py --custom "FCP wordmark in bold serif font with orange accent"

# Icon variation
python scripts/generate_logo.py --custom "minimalist bowl and chopsticks icon, blue and green"
```

---

### Specify Output Path
```bash
# Save to specific location
python scripts/generate_logo.py --style icon --output static/logos/fcp-icon-v2.png
```

---

### Use Flash Model (Faster)
```bash
# Use Flash instead of Pro for faster generation
python scripts/generate_logo.py --style icon --model flash
```

---

## FCP Brand Colors

The logo generator uses these carefully chosen colors:

| Color | Hex | Usage | Meaning |
|-------|-----|-------|---------|
| **Forest Green** | `#2E7D32` | Primary | Natural, healthy, growth |
| **Orange** | `#FF6F00` | Secondary | Energy, food, warmth |
| **Blue** | `#1976D2` | Accent | Trust, technology, protocol |
| **Dark Gray** | `#212121` | Text/UI | Professional, modern |
| **Off-White** | `#FAFAFA` | Background | Clean, fresh |

---

## Model Selection

### Pro Model (Recommended)
```bash
--model pro  # Default
```
- **Model:** `gemini-3-pro-image-preview` (Nano Banana Pro)
- **Quality:** Best (4K capable)
- **Speed:** Slower (~30-60 seconds)
- **Use for:** Final logos, high-quality assets, production use

### Flash Model
```bash
--model flash
```
- **Model:** `gemini-2.5-flash-image` (Nano Banana)
- **Quality:** Good
- **Speed:** Faster (~10-20 seconds)
- **Use for:** Rapid iteration, testing prompts, proof of concept

---

## Design Philosophy

The FCP logo system balances three key aspects:

1. **Food & Nutrition** - Represented through food symbols (fork, spoon, bowl, plate)
2. **Technology & Protocol** - Represented through data elements (nodes, circuits, connections)
3. **Intelligence & Context** - Represented through modern, professional design and color choices

### Visual Language
- **Circular shapes** → Community, wholeness, plate/bowl metaphor
- **Connected nodes** → Protocol, network, context
- **Green color** → Health, natural, growth
- **Orange color** → Energy, food, warmth
- **Blue color** → Trust, technology, reliability

---

## Post-Generation Workflow

After generating logos, you typically want to:

### 1. Review and Select
```bash
# View all generated logos
open static/logos/
```

### 2. Optimize for Web
```bash
# Install optimization tools
brew install imagemagick pngquant

# Optimize PNG
pngquant --quality=80-95 static/logos/fcp-icon.png -o static/logos/fcp-icon-optimized.png

# Convert to WebP
convert static/logos/fcp-icon.png -quality 90 static/logos/fcp-icon.webp
```

### 3. Generate Favicons
```bash
# Create favicon sizes
convert static/logos/fcp-icon.png -resize 16x16 static/logos/favicon-16.png
convert static/logos/fcp-icon.png -resize 32x32 static/logos/favicon-32.png
convert static/logos/fcp-icon.png -resize 192x192 static/logos/favicon-192.png
convert static/logos/fcp-icon.png -resize 512x512 static/logos/favicon-512.png

# Create .ico file (Windows)
convert static/logos/fcp-icon.png -define icon:auto-resize=16,32,48,64,256 static/logos/favicon.ico
```

### 4. Upload to GitHub
```bash
# Organization avatar
# 1. Go to: https://github.com/organizations/Food-Context-Protocol/settings/profile
# 2. Upload: static/logos/fcp-icon.png or static/logos/fcp-social.png
```

---

## Troubleshooting

### Error: "GEMINI_API_KEY not set"
```bash
# Get API key from: https://aistudio.google.com/apikey
export GEMINI_API_KEY=your-api-key

# Or add to your shell profile
echo 'export GEMINI_API_KEY=your-api-key' >> ~/.zshrc
source ~/.zshrc
```

### Error: "google-genai package not installed"
```bash
pip install google-genai
# or
uv pip install google-genai
```

### No image generated, only text response
This can happen if:
- The model interprets the request as a question rather than image generation
- The prompt is ambiguous

**Solution:** Try rephrasing the prompt to be more explicit:
```bash
python scripts/generate_logo.py --custom "GENERATE AN IMAGE: minimalist food icon"
```

### Image quality is poor
- Use `--model pro` instead of flash
- Add more specific details to the prompt
- Generate multiple variations and select the best

---

## Comparison with Other Logo Generators

### vs. humboldt-tech generator
| Feature | FCP | humboldt.tech |
|---------|-----|---------------|
| Model | Pro + Flash | Pro only |
| Styles | 6 predefined | 1 wordmark |
| Colors | 5-color palette | Monochrome + accent |
| Use case | Food/nutrition tech | General tech |

### vs. foodlog-fcp generator
| Feature | FCP | FoodLog |
|---------|-----|---------|
| Model | Pro (better) | Flash-exp |
| Styles | 6 predefined | 1 icon |
| Documentation | Comprehensive | Basic |
| CLI | Full argparse | Simple |

---

## Advanced Usage

### Batch Generation with Variations
```bash
# Generate 3 variations of icon style
for i in {1..3}; do
  python scripts/generate_logo.py --style icon --output "static/logos/fcp-icon-v$i.png"
  sleep 5  # Rate limiting
done
```

### A/B Testing Different Prompts
```bash
# Test different color schemes
python scripts/generate_logo.py --custom "FCP icon, blue and purple theme" --output static/logos/test-blue-purple.png
python scripts/generate_logo.py --custom "FCP icon, green and yellow theme" --output static/logos/test-green-yellow.png
python scripts/generate_logo.py --custom "FCP icon, monochrome gradient" --output static/logos/test-mono.png
```

### Integration with CI/CD
```yaml
# Example GitHub Action
name: Generate Logos
on:
  workflow_dispatch:
    inputs:
      style:
        description: 'Logo style to generate'
        required: true
        default: 'all'

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install google-genai
      - run: python scripts/generate_logo.py --${{ github.event.inputs.style }}
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
      - uses: actions/upload-artifact@v4
        with:
          name: logos
          path: static/logos/
```

---

## Best Practices

1. **Always use Pro model for final logos** - Flash is for iteration only
2. **Generate multiple variations** - AI generation varies each time
3. **Test logos at multiple sizes** - Ensure legibility at 16px to 4000px
4. **Check contrast ratios** - Use tools like WebAIM Contrast Checker
5. **Optimize for web** - Use pngquant and WebP conversion
6. **Version control** - Keep source files and commit to git
7. **Document choices** - Keep notes on why you selected certain designs

---

## Resources

- **Gemini API Docs:** https://ai.google.dev/docs
- **Get API Key:** https://aistudio.google.com/apikey
- **Color Palette Tool:** https://coolors.co
- **Logo Mockups:** https://mockuper.net
- **Icon Guidelines:** https://developer.apple.com/design/human-interface-guidelines/app-icons

---

**Last Updated:** February 9, 2026
**Maintained By:** Food Context Protocol Contributors
