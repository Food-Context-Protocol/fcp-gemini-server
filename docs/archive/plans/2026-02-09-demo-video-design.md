# FCP Demo Video Design: "The Food Matrix"

## Concept

A 3-minute Matrix-themed demo video where FCP is presented as "seeing the hidden data in food." Green-on-black terminal aesthetic throughout. Food emojis fall like Matrix code rain. Real CLI demos are native to the style. Gemini-powered audio (TTS voice + Lyria chiptune).

**Tagline:** "There is no spoon... use a fork."

## Video Requirements (Devpost rules)

- Max 3 minutes (only first 3 min evaluated)
- Must show project functioning on its platform
- English or English subtitles
- No third-party logos or sponsorship indicators
- Upload to YouTube or Vimeo (publicly visible)

## Matrix Food References

| Matrix Quote | FCP Version | Used In |
|-------------|-------------|---------|
| "What is the Matrix?" | "What is the Protocol?" | Intro |
| "There is no spoon" | "There is no spoon... use a fork." | Transition |
| Blue pill / Red pill | Safe food (blueberry) / Allergen (tomato) | Allergen level |
| "I know this steak doesn't exist" | AI analyzing food photos | Food Scanner |
| "Free your mind" | "Free your food data" | Outro |
| Neo sees the code | Developer sees nutrition data streaming | Throughout |
| "Follow the white rabbit" | "Follow the recipe" | Recipe level |
| "He is The One" | "It is The Protocol" | MCP level |
| The green code rain | Food emojis + JSON data rain | Background |

## Video Structure

| Time | Section | CLI | Matrix Reference |
|------|---------|-----|-----------------|
| 0:00-0:10 | **Intro** | - | Food data rain. "What if your food has secrets?" |
| 0:10-0:35 | **Food Scanner** | FCP CLI | "I know this steak doesn't exist" |
| 0:35-1:00 | **Recipe Quest** | Gemini CLI | "Follow the recipe" / "There is no spoon" |
| 1:00-1:20 | **Meal Log** | FCP CLI | "Feed your mind... and your phone" |
| 1:20-1:45 | **Allergen Alert** | Gemini CLI | Blue pill or red pill? |
| 1:45-2:10 | **MCP Toolbox** | FCP CLI | "He is The One... It is The Protocol" |
| 2:10-2:35 | **Gemini Brain** | Gemini CLI | Neo sees the code = AI sees nutrition |
| 2:35-2:50 | **Montage** | - | Quick cuts, all levels |
| 2:50-3:00 | **Outro** | - | Food Catchers + "Free your food data" |

## Visual Design

### Dominant Aesthetic: Matrix Green-on-Black

- Background: black (#000000) or near-black (#0A0A0A)
- Primary text: Matrix green (#00FF64)
- Accent: bright white for titles
- Secondary: cyan (#00BCD4) for data readouts
- Danger: red (#FF3333) for allergen alerts
- Food emojis: full color (pop against dark background)

### Screen Layout

```
+------------------------------------------+
|  > FOOD_SCANNER.exe                      |  <- Green terminal header
|  "I know this steak doesn't exist"       |  <- Matrix quote in dim green
+------------------------------------------+
|                                          |
|     [TERMINAL RECORDING AREA]            |  <- Full-width CLI demo
|     $ fcp analyze steak.jpg              |     Green on black = native
|     > Analyzing...                       |
|     > Calories: 450                      |
|     > Protein: 42g                       |
|                                          |
+------------------------------------------+
|  > CALORIES_ANALYZED: 1,847  |  FCP v1.0 |  <- Terminal-style status bar
+------------------------------------------+
```

### Transitions Between Levels

Food data rain (emojis + JSON) fills the screen for ~2 seconds, then parts/clears to reveal the next level. Like Neo seeing through the Matrix code.

### Food Data Rain Elements

- Food emojis: full color, 40% of items
- Code snippets: `{"calories": 450}`, `GET /api/meals`, `analyze_meal()`, etc.
- Matrix green for code, full color for emojis
- Speed: fast and continuous (already tuned)

## Audio Design

### Three Layers (all Gemini-powered)

| Layer | Tech | Description |
|-------|------|-------------|
| **Voice** | Gemini TTS (`gemini-2.5-flash-preview-tts`) | Dramatic narrator, Matrix style |
| **Music** | Lyria RealTime (`lyria-realtime-exp`) | Dark electronic/chiptune hybrid |
| **SFX** | Programmatic (numpy + wave) | Retro game sounds |

### Voiceover Script (Draft)

**Intro (0:00-0:10):**
> "What if I told you... your food has secrets? Hidden data. Nutrition. Allergens. Recipes. All encoded... in the food matrix."

**Food Scanner (0:10):**
> "Level one. See the food for what it really is."

**Recipe Quest (0:35):**
> "There is no spoon. Use a fork. Follow the recipe."

**Meal Log (1:00):**
> "Feed your mind. Feed your phone. Log everything."

**Allergen Alert (1:20):**
> "You take the blueberry... the story ends. You take the tomato... and I show you how deep the allergen goes."

**MCP Toolbox (1:45):**
> "It is The Protocol. One protocol to connect them all."

**Gemini Brain (2:10):**
> "I know this steak doesn't exist. But the AI knows exactly what's in it."

**Outro (2:50):**
> "Free your food data. Food Context Protocol."

### Sound Effects

| Event | Sound | When |
|-------|-------|------|
| Food data rain | Low synth hum + digital patter | Transitions |
| Level title appears | Dramatic hit + whoosh | Each level start |
| Food detected | Power-up bling | During CLI demos |
| Allergen found | Warning buzzer | Allergen level |
| Data streaming | Soft digital ticking | During analysis |
| Outro food catch | Pac-Man chomp | Food Catchers |

### Music Prompts (Lyria RealTime)

- Intro: `"dark ambient electronic, mysterious, matrix style, slow build"`
- Levels: `"minimal dark techno, cyberpunk, 100bpm, atmospheric"`
- Allergen: `"tense electronic, warning, suspenseful"`
- Outro: `"upbeat chiptune, retro arcade, celebratory"`

## Implementation Scripts

All in `demo-video/`:

| Script | Purpose | Status |
|--------|---------|--------|
| `generate_matrix_bookends.py` | Intro (food rain) + Outro (Food Catchers) | Done |
| `prototype_levels.py` | Static level card prototypes | Done (needs Matrix restyle) |
| `generate_tts_voice.py` | Gemini TTS voiceover | To build |
| `generate_music.py` | Lyria RealTime soundtrack | To build |
| `generate_sfx.py` | Programmatic retro SFX | To build |
| `generate_transitions.py` | Animated level transitions | To build |
| `assemble_video.py` | Final video assembly | To build |

## Dependencies

```
pip install google-genai Pillow rich numpy
```

Required: `GOOGLE_API_KEY` environment variable

## Existing Assets

- `intro_matrix_audio.mp4` - Matrix food rain intro (working)
- `outro_matrix_audio.mp4` - Food Catchers outro (working)
- `prototypes/` - 8-bit level cards (to be restyled to Matrix)
- `gemini3_hero.png` - Hackathon branding (removed per rules)
- `gemini_logo.svg` - Gemini logo (removed per rules)
