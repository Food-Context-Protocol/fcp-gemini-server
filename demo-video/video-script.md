# Food Context Protocol - Demonstration Video Plan
## Gemini 3 Devpost Entry Video Creation Guide

---

## 🎯 Project Overview

**Objective:** Create a 2-3 minute demonstration video for the Food Context Protocol Devpost submission using Gemini 3 technologies throughout the production pipeline.

**Narrative Theme:** "Built with Gemini 3, Demonstrated with Gemini 3" - showcasing the full stack of Google's AI capabilities.

**Target Audience:** Devpost judges, developers, and potential FCP adopters

**Key Message:** FCP is like "Stripe for payments, but for food AI" - a standardized protocol enabling interoperability between AI agents, applications, and food data providers.

---

## 📋 Video Structure (2:30 - 2:45 total)

```
[0:00-0:10]  Title Sequence + Logo Reveal
              → Veo-generated animated intro

[0:10-0:30]  Problem Statement
              → Why food AI systems are fragmented
              → Current pain points

[0:30-1:00]  Solution Overview
              → FCP Architecture
              → 40+ Tools across 5 domains
              → Dual transport (MCP + REST)

[1:00-1:45]  Live Demonstration
              → Meal analysis with photo
              → Recipe search
              → Food safety recalls
              → CLI and API usage

[1:45-2:15]  Gemini 3 Integration Showcase
              → 15+ Gemini features in action
              → Technical architecture
              → Performance highlights

[2:15-2:30]  Call to Action
              → GitHub repository
              → Documentation site
              → Get started guide

[2:30-2:45]  Credits & Acknowledgments
              → Powered by Gemini 3
              → Technology stack
              → Team/contributors
```

---

## 🎬 Phase 1: Pre-Production & Scripting

### 1.1 Script Development with Gemini 3 Pro

**Tool:** Gemini 3 Pro with Extended Thinking Mode

**Process:**
```
Feed Gemini 3 Pro your project documentation:
- fcp/README.md
- fcp/specification/FCP.md
- review.md
- fcp-gemini-server architecture docs
```

**Prompt Template:**
```
Context: I'm creating a demonstration video for a Devpost submission.

Project: Food Context Protocol (FCP) - an open standard for food AI
interoperability, similar to how Stripe standardized payments.

Key Features:
- 40+ typed tools across nutrition, recipes, safety, inventory, planning
- Dual transport: MCP stdio + REST HTTP
- Deep Gemini 3 integration (15+ features)
- 100% test coverage, production-ready
- Auto-generated SDKs

Target: Create a compelling 2-3 minute video script that:
1. Opens with the fragmentation problem in food AI
2. Introduces FCP as the solution
3. Demonstrates core capabilities
4. Highlights Gemini 3 integration
5. Ends with a strong call to action

Tone: Professional, innovative, approachable
Audience: Technical judges and developers

Generate a complete script with:
- Narration text for each scene
- Visual descriptions
- Timing breakdowns
- Technical callouts
```

### 1.2 Scene Breakdown

**Scene List:**

| Scene # | Duration | Content | Visual Style | Audio |
|---------|----------|---------|--------------|-------|
| 1 | 10s | Title reveal | Animated FCP logo | Ambient build-up |
| 2 | 20s | Problem statement | Mixed real food + broken systems | Tension |
| 3 | 30s | Solution overview | Architecture diagram | Uplifting |
| 4 | 15s | Nutrition analysis demo | App screenshots | Steady |
| 5 | 15s | Recipe search demo | Terminal + UI | Professional |
| 6 | 15s | Food safety demo | Alert notifications | Alert tone |
| 7 | 30s | Gemini integration | Code + visualizations | Tech |
| 8 | 15s | Call to action | Clean graphics | Triumphant |
| 9 | 15s | Credits | Scrolling text | Fade out |

---

## 🎨 Phase 2: Asset Creation

### 2.1 Title Sequence with Veo 3.1

**Opening Title (10 seconds):**

```python
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key="YOUR_API_KEY")

# Generate title sequence
title_video = genai.generate_video(
    model="veo-3.1",
    prompt="""
    Cinematic title sequence for a tech protocol launch.

    Scene: A rotating holographic display of fresh food ingredients
    (colorful vegetables, fruits, grains, proteins) slowly materializing
    from digital particles. As they rotate, they begin transforming into
    flowing data streams and network connections, all converging into a
    central glowing protocol symbol (abstract geometric design).

    Style: Modern tech aesthetic, clean and professional
    Lighting: Soft volumetric lighting with blue-green gradients
    Camera: Slow orbital rotation, starting wide and pushing in
    Effects: Subtle particle systems, holographic shimmer
    Color palette: Deep blues, vibrant greens, warm food tones

    Duration: 8 seconds
    Resolution: 1080p
    Aspect ratio: 16:9
    """,
    duration=8,
    resolution="1080p",
    audio_enabled=True  # Native ambient sound
)

# Save output
title_video.save("assets/01_title_sequence.mp4")
```

**Expected Output:** Professional title card with organic-to-digital transformation, suitable for text overlay: "Food Context Protocol"

---

### 2.2 Background Visuals with Veo 3.1

**Transition Backgrounds (for text overlays):**

```python
# Scene backgrounds for different sections
background_prompts = {
    "problem_bg": """
    Slow camera pan across a modern kitchen counter with fresh ingredients
    (vegetables, cutting board, smartphone). Natural window lighting, shallow
    depth of field, slightly desaturated color grade suggesting a challenge
    to be solved. 10 seconds, cinematic composition.
    """,

    "architecture_bg": """
    Abstract visualization of a distributed system with flowing data streams.
    Clean geometric nodes connected by animated lines, representing the FCP
    protocol connecting different services (AI agents, databases, APIs).
    Dark background with cyan and white accents. Technical but elegant.
    15 seconds, suitable for diagram overlay.
    """,

    "demo_bg": """
    Over-shoulder view of hands using a modern smartphone to photograph a
    colorful meal on a restaurant table. Warm ambient lighting, professional
    product photography style, focus on the device interaction.
    12 seconds, smooth motion.
    """,

    "tech_stack_bg": """
    Code editor screen with Python code scrolling smoothly, showing imports
    from the FCP SDK and Gemini integration. Syntax highlighted, dark theme,
    professional development environment. Subtle cursor movements.
    15 seconds, developer-focused aesthetic.
    """,

    "cta_bg": """
    Clean, bright minimal background with subtle geometric patterns suggesting
    connectivity and data flow. White to light blue gradient, professional
    corporate style suitable for text and logos. 10 seconds, smooth subtle motion.
    """
}

# Generate all backgrounds
backgrounds = {}
for name, prompt in background_prompts.items():
    video = genai.generate_video(
        model="veo-3.1",
        prompt=prompt,
        resolution="1080p",
        audio_enabled=False  # Silent backgrounds
    )
    backgrounds[name] = video
    video.save(f"assets/bg_{name}.mp4")
```

---

### 2.3 Static Assets with Imagen 3

**Logo and Branding:**

```python
# Generate FCP logo variations
logo_prompts = {
    "main_logo": """
    Professional logo design for 'Food Context Protocol' (FCP).
    Design: Minimalist fusion of a fork icon and data/protocol symbol
    (interconnected nodes). Clean lines, modern sans-serif typography.
    Colors: Gradient from fresh green (#4CAF50) to tech blue (#2196F3).
    Style: Flat design, suitable for tech brand, scalable.
    Background: Transparent.
    Format: High contrast, works on light and dark backgrounds.
    """,

    "badge_gemini": """
    Badge design reading 'Powered by Gemini 3'.
    Design: Rectangular badge with rounded corners, Google Gemini sparkle
    icon on left, text on right.
    Colors: Google brand colors (blue, red, yellow, green accents).
    Style: Professional, can be overlaid on video.
    Background: Semi-transparent dark with subtle glow.
    """,

    "icon_nutrition": """
    Icon representing nutrition analysis.
    Design: Circular outline with fork and magnifying glass, examining food.
    Style: Line art, monochromatic, modern UI icon.
    Size: 512x512px, transparent background.
    """,

    "icon_recipes": """
    Icon representing recipe search.
    Design: Book/cookbook with chef hat above it.
    Style: Line art, monochromatic, consistent with nutrition icon.
    Size: 512x512px, transparent background.
    """,

    "icon_safety": """
    Icon representing food safety.
    Design: Shield with checkmark and food symbol inside.
    Style: Line art, monochromatic, consistent with other icons.
    Size: 512x512px, transparent background.
    """,

    "icon_inventory": """
    Icon representing pantry/inventory tracking.
    Design: Shelves with containers and a list/clipboard.
    Style: Line art, monochromatic, consistent with other icons.
    Size: 512x512px, transparent background.
    """
}

# Generate images
images = {}
for name, prompt in logo_prompts.items():
    image = genai.generate_image(
        model="imagen-3",
        prompt=prompt,
        aspect_ratio="1:1",
        quality="high"
    )
    images[name] = image
    image.save(f"assets/{name}.png")
```

**Architecture Diagram:**

```python
# Generate architecture visualization
arch_prompt = """
High-quality technical architecture diagram for the Food Context Protocol.

Layout: Three-tier architecture shown horizontally
- Top tier: Client applications (mobile app icon, web browser icon,
  CLI terminal icon, Claude Desktop logo)
- Middle tier: FCP Server (central box) with bidirectional arrows
  showing 'MCP stdio' and 'REST HTTP' protocols
- Bottom tier: Gemini 3 capabilities (icons for Vision, Grounding,
  Thinking, Code Execution, Live API)

Style: Modern technical diagram, clean lines, professional
Colors: Blue for clients, green for FCP, orange/red for Gemini
Background: Light gray or white, suitable for presentation
Icons: Simple, recognizable, consistent style
Arrows: Labeled, showing data flow direction
Text: Sans-serif, clear hierarchy, readable at video resolution

Format: Wide horizontal layout (16:9), high resolution
"""

arch_diagram = genai.generate_image(
    model="imagen-3",
    prompt=arch_prompt,
    aspect_ratio="16:9",
    quality="high"
)
arch_diagram.save("assets/architecture_diagram.png")
```

---

## 🎥 Phase 3: Core Content Creation

### 3.1 Live Demo - Image-to-Video Conversion

**Strategy:** Capture screenshots of your actual FCP interfaces, then use Veo 3.1's image-to-video feature to add professional motion.

**Demo Scenes:**

```python
# 1. Meal Analysis Demo
meal_analysis = genai.generate_video_from_image(
    model="veo-3.1",
    source_image="screenshots/meal_analysis_ui.png",
    prompt="""
    Smooth zoom into the meal analysis interface showing a colorful salad photo.
    As camera moves in, nutrition data cards animate in from the sides with a
    subtle fade: calories, macros, allergen warnings. UI elements have soft
    drop shadows. Professional product demo style, emphasizing the clean
    interface design. 6 seconds, smooth ease-in motion.
    """,
    duration=6,
    resolution="1080p"
)

# 2. CLI Terminal Demo
cli_demo = genai.generate_video_from_image(
    model="veo-3.1",
    source_image="screenshots/fcp_cli_terminal.png",
    prompt="""
    Terminal window showing FCP CLI commands. Simulated typing effect showing:
    '$ fcp meal analyze --image meal.jpg'
    followed by structured JSON response scrolling in line by line.
    Classic developer screencast style, green text on dark background,
    cursor blinking. 8 seconds, steady composition.
    """,
    duration=8,
    resolution="1080p"
)

# 3. API Request Visualization
api_viz = genai.generate_video_from_image(
    model="veo-3.1",
    source_image="screenshots/api_request_flow.png",
    prompt="""
    Animated sequence showing HTTP request flow:
    1. Request arrow flowing from client to FCP server
    2. Server icon pulses as it processes
    3. Internal call to Gemini 3 (indicated by colorful sparkle icon)
    4. Response data flowing back to client
    All with smooth animated arrows and subtle glow effects.
    Technical diagram animation style. 8 seconds.
    """,
    duration=8,
    resolution="1080p"
)

# 4. Food Safety Alert Demo
safety_alert = genai.generate_video_from_image(
    model="veo-3.1",
    source_image="screenshots/safety_alert.png",
    prompt="""
    Smartphone screen showing push notification arriving at top:
    'FDA Recall Alert: Romaine Lettuce - E. coli Risk'
    User taps notification, screen transitions to detailed alert view
    with affected products, sources, and citations from Google Search.
    Modern app interaction, natural finger tap animation, smooth transitions.
    6 seconds, portrait mode smartphone (9:16 aspect).
    """,
    duration=6,
    resolution="1080p",
    aspect_ratio="9:16"
)

# Save all demos
demos = {
    "meal_analysis": meal_analysis,
    "cli_demo": cli_demo,
    "api_viz": api_viz,
    "safety_alert": safety_alert
}

for name, video in demos.items():
    video.save(f"assets/demo_{name}.mp4")
```

---

### 3.2 Feature Showcase - Text-to-Video

**Generate demonstration scenes from scratch:**

```python
feature_showcases = {
    "multimodal_vision": {
        "prompt": """
        First-person POV: Hands holding a smartphone, pointing camera at a
        colorful Buddha bowl on a wooden restaurant table. Camera focuses on
        the food, then AR-style overlay graphics appear showing:
        - Nutrition facts (calories, protein, carbs)
        - Ingredient labels with small icons
        - Allergen warnings (if any)
        Interface is clean, modern, uses cards with subtle shadows.
        Natural restaurant lighting, professional food photography style.
        Duration: 5 seconds, 1080p, aspect 16:9.
        """,
        "duration": 5
    },

    "search_grounding": {
        "prompt": """
        Split-screen visualization:
        Left side: User typing 'recent lettuce recalls' in search bar
        Right side: Real-time Google Search results appearing with highlighted
        FDA sources, news articles, and official recall notices.
        Lines connecting search query to specific result snippets.
        Clean UI design, emphasizing the grounded search citations.
        Modern tech demo aesthetic, white/blue color scheme.
        Duration: 6 seconds, 1080p, aspect 16:9.
        """,
        "duration": 6
    },

    "recipe_scaling": {
        "prompt": """
        Animated recipe card interface showing ingredient list.
        User drags a slider control from '4 servings' to '8 servings'.
        As slider moves, all ingredient quantities smoothly animate and update:
        '2 cups flour' → '4 cups flour'
        '3 eggs' → '6 eggs'
        Numbers transform with a smooth counting animation.
        Clean cooking app interface, warm kitchen colors.
        Duration: 5 seconds, 1080p, aspect 16:9.
        """,
        "duration": 5
    },

    "pantry_tracking": {
        "prompt": """
        Mobile app screen showing a digital pantry inventory.
        Grid of food item cards (milk, eggs, bread, etc.) each with:
        - Product image
        - Expiration date
        - Quantity indicator
        One item (milk) has expiration approaching - card pulses orange,
        then a notification badge appears suggesting 'Use Soon' recipe ideas.
        Modern grocery app UI, clean and organized.
        Duration: 6 seconds, 1080p, aspect 16:9.
        """,
        "duration": 6
    }
}

# Generate feature videos
for name, config in feature_showcases.items():
    video = genai.generate_video(
        model="veo-3.1-fast",  # Use Fast version for cost savings
        prompt=config["prompt"],
        duration=config["duration"],
        resolution="1080p",
        audio_enabled=True  # Native UI sounds
    )
    video.save(f"assets/feature_{name}.mp4")
```

---

## 🎵 Phase 4: Audio Production

### 4.1 Background Music with Lyria RealTime

**Music Composition Strategy:**

```python
from google.generativeai import music

# Main background track - 3 minutes with dynamic sections
music_config = {
    "duration": 180,  # 3 minutes total
    "sections": [
        {
            "name": "intro",
            "start": 0,
            "duration": 15,
            "density": "sparse",
            "brightness": "medium",
            "scale": "minor",
            "tempo": "moderate",
            "description": "Mysterious ambient intro, building anticipation"
        },
        {
            "name": "problem",
            "start": 15,
            "duration": 30,
            "density": "medium",
            "brightness": "medium",
            "scale": "minor",
            "tempo": "moderate",
            "description": "Slightly tense, questioning mood"
        },
        {
            "name": "solution",
            "start": 45,
            "duration": 45,
            "density": "medium",
            "brightness": "bright",
            "scale": "major",
            "tempo": "upbeat",
            "description": "Uplifting reveal, innovative and optimistic"
        },
        {
            "name": "demo",
            "start": 90,
            "duration": 60,
            "density": "medium",
            "brightness": "bright",
            "scale": "major",
            "tempo": "steady",
            "description": "Professional, focused, technological"
        },
        {
            "name": "closing",
            "start": 150,
            "duration": 30,
            "density": "rich",
            "brightness": "very_bright",
            "scale": "major",
            "tempo": "triumphant",
            "description": "Triumphant resolution, inspiring finale"
        }
    ]
}

# Generate adaptive music track
background_music = music.generate_realtime(
    style="electronic_ambient",
    sections=music_config["sections"],
    total_duration=180
)

background_music.export("assets/background_music.mp3", format="mp3")
```

**Music Mixing Levels:**
- Background music: -18dB (subtle, not overpowering)
- Voiceover narration: 0dB (primary focus)
- UI sound effects: -12dB (noticeable but not distracting)

---

### 4.2 Sound Effects via Veo Native Audio

**UI Sound Effects** (generated alongside video):

```python
# When generating UI interaction videos, enable audio
ui_sounds = genai.generate_video(
    model="veo-3.1",
    prompt="""
    Close-up of finger tapping smartphone screen buttons in a food logging app.
    Each tap triggers visual feedback (ripple effect) and satisfying click sound.
    Sequence: tap 'Analyze' button → processing spinner with subtle hum →
    success chime as results appear.
    Modern app UI, professional interaction design, natural finger movements.
    Duration: 4 seconds with synchronized audio.
    """,
    duration=4,
    resolution="1080p",
    audio_enabled=True  # Critical for UI sounds
)

# Extract audio track for reuse
ui_sounds.extract_audio("assets/sfx_ui_interactions.wav")
```

**Additional Sound Effects Needed:**

| Sound Effect | Use Case | Source |
|--------------|----------|--------|
| Notification chime | Food recall alerts | Veo native audio |
| Keyboard typing | CLI demo scenes | Veo native audio |
| Success tone | Meal logged successfully | Veo native audio |
| Transition whoosh | Scene transitions | Veo native audio |
| Data processing hum | API calls in progress | Veo native audio |
| Ambient restaurant | Food scene backgrounds | Veo native audio |

---

### 4.3 Voiceover Narration with Gemini TTS

**Script for Voiceover:**

```python
from google.cloud import texttospeech

# Configure TTS client
client = texttospeech.TextToSpeechClient()

# Narration script sections
narration_script = [
    {
        "section": "intro",
        "text": """
        Every food app rebuilds the same features from scratch.
        Nutrition analysis. Recipe search. Safety checks.
        What if there was a better way?
        """,
        "timing": "0:10-0:30"
    },
    {
        "section": "solution",
        "text": """
        Introducing the Food Context Protocol.
        An open standard enabling interoperability between AI agents,
        applications, and food data providers.
        Like Stripe for payments, FCP for food AI.
        """,
        "timing": "0:30-0:50"
    },
    {
        "section": "features",
        "text": """
        Forty-plus typed tools organized across five capability domains.
        Nutrition analysis. Recipe management. Food safety.
        Inventory tracking. And meal planning.
        All with dual transport support: MCP stdio and REST HTTP.
        """,
        "timing": "0:50-1:10"
    },
    {
        "section": "demo",
        "text": """
        Analyze any meal with a photo.
        Get instant nutrition data, allergen detection, and portion analysis.
        Search recipes, scale ingredients, find substitutions.
        Real-time FDA recall alerts, grounded in Google Search with cited sources.
        """,
        "timing": "1:10-1:35"
    },
    {
        "section": "gemini",
        "text": """
        Built with fifteen-plus Gemini 3 features.
        Multimodal vision. Search grounding. Extended thinking.
        Code execution. And the Live API.
        A reference implementation demonstrating production-ready AI integration.
        """,
        "timing": "1:45-2:05"
    },
    {
        "section": "cta",
        "text": """
        The Food Context Protocol. Open source. Production ready.
        Available now.
        Visit F-C-P dot dev to get started.
        """,
        "timing": "2:15-2:30"
    }
]

# Voice configuration
voice_config = texttospeech.VoiceSelectionParams(
    language_code="en-US",
    name="en-US-Studio-M",  # Professional male voice
    ssml_gender=texttospeech.SsmlVoiceGender.MALE
)

audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3,
    speaking_rate=1.0,  # Natural pace
    pitch=0.0,  # Neutral pitch
    volume_gain_db=0.0,  # Standard volume
    effects_profile_id=["large-home-entertainment-class-device"]
)

# Generate voiceover for each section
voiceover_files = []
for segment in narration_script:
    synthesis_input = texttospeech.SynthesisInput(text=segment["text"])

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice_config,
        audio_config=audio_config
    )

    filename = f"assets/vo_{segment['section']}.mp3"
    with open(filename, "wb") as out:
        out.write(response.audio_content)

    voiceover_files.append({
        "file": filename,
        "section": segment["section"],
        "timing": segment["timing"]
    })

print(f"Generated {len(voiceover_files)} voiceover segments")
```

---

## 🎞️ Phase 5: Title Cards & Text Overlays

### 5.1 Animated Title Cards

**Opening Title:**

```python
# Generate animated background for title
opening_bg = genai.generate_video(
    model="veo-3.1",
    prompt="""
    Abstract background: Flowing particles of fresh food ingredients
    (vegetables, fruits, grains) slowly morphing into digital particles
    and data streams. Warm color palette transitioning to cool tech blues.
    Subtle movement, suitable for bold text overlay.
    No specific objects in center - leave space for text.
    Duration: 5 seconds, 1080p, cinematic.
    """,
    duration=5,
    resolution="1080p"
)
opening_bg.save("assets/title_card_bg.mp4")
```

**Text Overlay Configuration** (applied in post):
```
Title: "FOOD CONTEXT PROTOCOL"
Subtitle: "Like Stripe for Payments, FCP for Food AI"
Font: Inter Bold, 72pt
Color: White with subtle drop shadow
Position: Center, safe area margins
Animation: Fade in + scale up (0.95x → 1.0x) over 1 second
```

---

### 5.2 Section Divider Cards

```python
divider_prompts = {
    "problem": """
    Dark abstract background with subtle network connection lines breaking apart,
    representing fragmentation. Deep blues and grays, minimal motion.
    Center area clear for text: 'THE PROBLEM'
    Duration: 3 seconds.
    """,

    "solution": """
    Bright, optimistic background with flowing data streams connecting into
    a unified network pattern. Greens and blues, hopeful aesthetic.
    Center area clear for text: 'THE SOLUTION'
    Duration: 3 seconds.
    """,

    "tech": """
    Code-style background with subtle syntax highlighting colors floating by.
    Dark theme, tech-forward aesthetic.
    Center area clear for text: 'BUILT WITH GEMINI 3'
    Duration: 3 seconds.
    """,

    "action": """
    Clean gradient background, white to light blue, with geometric patterns
    suggesting connectivity. Professional corporate style.
    Center area clear for text: 'GET STARTED'
    Duration: 3 seconds.
    """
}

# Generate divider backgrounds
for name, prompt in divider_prompts.items():
    divider = genai.generate_video(
        model="veo-3.1-fast",  # Fast version sufficient for simple backgrounds
        prompt=prompt,
        duration=3,
        resolution="1080p"
    )
    divider.save(f"assets/divider_{name}.mp4")
```

---

### 5.3 Credits Sequence

```python
# Generate credits background
credits_bg = genai.generate_video(
    model="veo-3.1",
    prompt="""
    Slow upward camera movement through abstract visualization of interconnected
    food data nodes and network connections. Starts dense at bottom, gradually
    fading to a clean blue-to-white gradient at top.
    Professional, corporate style, suitable for scrolling credits text overlay.
    Smooth motion, no jarring movements.
    Duration: 15 seconds, 1080p, portrait composition (9:16) for vertical scroll.
    """,
    duration=15,
    resolution="1080p",
    aspect_ratio="9:16"
)
credits_bg.save("assets/credits_background.mp4")
```

**Credits Text Content:**
```
FOOD CONTEXT PROTOCOL
An Open Standard for Food AI

━━━━━━━━━━━━━━━━━━━━━

POWERED BY
Google Gemini 3 • Veo 3.1 • Imagen 3 • Lyria

TECHNOLOGY STACK
Python • FastAPI • Pydantic
Model Context Protocol
OpenAPI • JSON Schema

━━━━━━━━━━━━━━━━━━━━━

LEARN MORE
fcp.dev
github.com/Food-Context-Protocol

━━━━━━━━━━━━━━━━━━━━━

© 2026 Food Context Protocol
Apache 2.0 License
```

---

## 🎬 Phase 6: Video Assembly & Editing

### 6.1 Assembly with FFmpeg

**Complete Video Assembly Script:**

```python
import ffmpeg
import json
from pathlib import Path

# Define video structure
video_timeline = [
    {
        "file": "assets/01_title_sequence.mp4",
        "duration": 10,
        "audio": ["assets/background_music.mp3"],
        "overlays": [
            {
                "type": "text",
                "content": "FOOD CONTEXT PROTOCOL",
                "start": 2,
                "duration": 6,
                "style": "title"
            }
        ]
    },
    {
        "file": "assets/divider_problem.mp4",
        "duration": 3,
        "audio": ["assets/background_music.mp3", "assets/vo_intro.mp3"],
        "overlays": [
            {
                "type": "text",
                "content": "THE PROBLEM",
                "start": 0.5,
                "duration": 2,
                "style": "section_header"
            }
        ]
    },
    {
        "file": "assets/bg_problem_bg.mp4",
        "duration": 20,
        "audio": ["assets/background_music.mp3", "assets/vo_intro.mp3"],
        "overlays": [
            {
                "type": "text",
                "content": "Every food app rebuilds the same features",
                "start": 0,
                "duration": 20,
                "style": "body_text"
            }
        ]
    },
    {
        "file": "assets/divider_solution.mp4",
        "duration": 3,
        "audio": ["assets/background_music.mp3"],
        "overlays": [
            {
                "type": "text",
                "content": "THE SOLUTION",
                "start": 0.5,
                "duration": 2,
                "style": "section_header"
            }
        ]
    },
    {
        "file": "assets/architecture_diagram.png",  # Static image, convert to video
        "duration": 30,
        "audio": ["assets/background_music.mp3", "assets/vo_solution.mp3"],
        "effects": ["ken_burns"]  # Slow zoom
    },
    {
        "file": "assets/demo_meal_analysis.mp4",
        "duration": 6,
        "audio": ["assets/background_music.mp3", "assets/vo_demo.mp3"]
    },
    {
        "file": "assets/demo_cli_demo.mp4",
        "duration": 8,
        "audio": ["assets/background_music.mp3"]
    },
    {
        "file": "assets/demo_safety_alert.mp4",
        "duration": 6,
        "audio": ["assets/background_music.mp3"]
    },
    {
        "file": "assets/divider_tech.mp4",
        "duration": 3,
        "audio": ["assets/background_music.mp3"],
        "overlays": [
            {
                "type": "text",
                "content": "BUILT WITH GEMINI 3",
                "start": 0.5,
                "duration": 2,
                "style": "section_header"
            }
        ]
    },
    {
        "file": "assets/feature_multimodal_vision.mp4",
        "duration": 5,
        "audio": ["assets/background_music.mp3", "assets/vo_gemini.mp3"],
        "overlays": [
            {
                "type": "badge",
                "content": "assets/badge_gemini.png",
                "position": "top_right",
                "start": 0,
                "duration": 5
            }
        ]
    },
    {
        "file": "assets/divider_action.mp4",
        "duration": 3,
        "audio": ["assets/background_music.mp3"],
        "overlays": [
            {
                "type": "text",
                "content": "GET STARTED",
                "start": 0.5,
                "duration": 2,
                "style": "section_header"
            }
        ]
    },
    {
        "file": "assets/cta_slide.mp4",
        "duration": 15,
        "audio": ["assets/background_music.mp3", "assets/vo_cta.mp3"],
        "overlays": [
            {
                "type": "text",
                "content": "fcp.dev",
                "start": 3,
                "duration": 10,
                "style": "cta"
            }
        ]
    },
    {
        "file": "assets/credits_background.mp4",
        "duration": 15,
        "audio": ["assets/background_music.mp3"],
        "overlays": [
            {
                "type": "scrolling_credits",
                "content": "credits_text.txt",
                "start": 0,
                "duration": 15
            }
        ]
    }
]

def create_final_video(timeline, output_file="fcp_demo_final.mp4"):
    """
    Assembles video from timeline specification
    """

    # Step 1: Concatenate all video clips
    video_inputs = []
    for segment in timeline:
        video = ffmpeg.input(segment["file"])

        # Apply effects if specified
        if "effects" in segment:
            for effect in segment["effects"]:
                if effect == "ken_burns":
                    # Slow zoom effect for static images
                    video = video.filter('zoompan',
                                        z='min(zoom+0.0015,1.5)',
                                        d=segment["duration"]*30,
                                        s='1920x1080')

        video_inputs.append(video)

    # Concatenate video segments
    concatenated = ffmpeg.concat(*video_inputs, v=1, a=0)

    # Step 2: Mix audio tracks
    music = ffmpeg.input("assets/background_music.mp3").audio

    # Collect all voiceover segments
    voiceover_segments = []
    for segment in timeline:
        if "audio" in segment:
            for audio_file in segment["audio"]:
                if "vo_" in audio_file:
                    voiceover_segments.append(ffmpeg.input(audio_file).audio)

    # Mix audio: background music at -18dB, voiceover at 0dB
    music_filtered = music.filter('volume', volume=-18, eval='frame')

    # Concatenate voiceovers
    if voiceover_segments:
        voiceover_concat = ffmpeg.concat(*voiceover_segments, v=0, a=1)
        mixed_audio = ffmpeg.filter([music_filtered, voiceover_concat],
                                     'amix', inputs=2, duration='longest')
    else:
        mixed_audio = music_filtered

    # Step 3: Combine video and audio
    output = ffmpeg.output(
        concatenated, mixed_audio,
        output_file,
        vcodec='libx264',
        acodec='aac',
        video_bitrate='5M',
        audio_bitrate='192k',
        preset='slow',  # Better quality
        pix_fmt='yuv420p',  # Compatibility
        movflags='faststart'  # Web optimization
    )

    # Run ffmpeg
    output.run(overwrite_output=True)
    print(f"✅ Final video created: {output_file}")

# Execute assembly
create_final_video(video_timeline)
```

---

### 6.2 Text Overlay Styling

**Text Style Definitions:**

```python
text_styles = {
    "title": {
        "font": "Inter-Bold",
        "size": 72,
        "color": "white",
        "shadow": "0px 4px 12px rgba(0,0,0,0.5)",
        "position": "center",
        "animation": "fade_scale"
    },
    "section_header": {
        "font": "Inter-Bold",
        "size": 48,
        "color": "white",
        "shadow": "0px 2px 8px rgba(0,0,0,0.4)",
        "position": "center",
        "animation": "slide_up"
    },
    "body_text": {
        "font": "Inter-Regular",
        "size": 36,
        "color": "white",
        "shadow": "0px 2px 6px rgba(0,0,0,0.6)",
        "position": "lower_third",
        "background": "rgba(0,0,0,0.7)",
        "padding": 20,
        "animation": "fade_in"
    },
    "cta": {
        "font": "Inter-Bold",
        "size": 64,
        "color": "#2196F3",
        "shadow": "0px 4px 10px rgba(33,150,243,0.3)",
        "position": "center",
        "background": "white",
        "padding": 30,
        "border_radius": 10,
        "animation": "pulse"
    },
    "caption": {
        "font": "Inter-Regular",
        "size": 24,
        "color": "white",
        "shadow": "0px 1px 4px rgba(0,0,0,0.8)",
        "position": "lower_third",
        "background": "rgba(0,0,0,0.6)",
        "padding": 10,
        "animation": "fade_in"
    }
}
```

---

### 6.3 Color Grading & Final Polish

**Color Grading LUT (Lookup Table):**

```python
# Apply consistent color grade across all segments
def apply_color_grade(input_video, output_video):
    """
    Applies FCP brand color grading
    """
    stream = ffmpeg.input(input_video)

    # Color adjustments for brand consistency
    stream = stream.filter('eq',
                          contrast=1.1,      # Slight contrast boost
                          brightness=0.05,   # Slightly brighter
                          saturation=1.15)   # More vibrant

    # Add slight teal/orange color grade (cinematic)
    stream = stream.filter('curves',
                          red='0/0 0.5/0.48 1/1',
                          green='0/0 0.5/0.52 1/1',
                          blue='0/0.05 0.5/0.5 1/0.95')

    output = ffmpeg.output(stream, output_video)
    output.run()

# Apply to final video
apply_color_grade("fcp_demo_final.mp4", "fcp_demo_graded.mp4")
```

---

## 📊 Phase 7: Quality Assurance

### 7.1 Technical Specifications Checklist

- [ ] **Resolution:** 1920x1080 (1080p)
- [ ] **Frame Rate:** 30 fps (consistent throughout)
- [ ] **Aspect Ratio:** 16:9
- [ ] **Video Codec:** H.264 (High Profile)
- [ ] **Video Bitrate:** 5-8 Mbps
- [ ] **Audio Codec:** AAC
- [ ] **Audio Bitrate:** 192 kbps
- [ ] **Audio Channels:** Stereo (2.0)
- [ ] **Audio Sample Rate:** 48 kHz
- [ ] **Container Format:** MP4
- [ ] **Color Space:** BT.709
- [ ] **Pixel Format:** YUV 4:2:0
- [ ] **File Size:** < 500 MB (for easy upload)

---

### 7.2 Content Review Checklist

**Visual Quality:**
- [ ] All text is readable at 1080p
- [ ] No visual artifacts or compression issues
- [ ] Consistent color grading throughout
- [ ] Smooth transitions between scenes
- [ ] Branding (FCP logo, Gemini badges) clearly visible

**Audio Quality:**
- [ ] Voiceover is clear and intelligible
- [ ] Background music doesn't overpower narration
- [ ] No audio clipping or distortion
- [ ] Sound effects are appropriately mixed
- [ ] No awkward silences or audio gaps

**Content:**
- [ ] All key features mentioned (40+ tools, dual transport)
- [ ] Gemini 3 integration clearly demonstrated
- [ ] Problem → Solution → Demo flow is clear
- [ ] Call to action is prominent
- [ ] Credits acknowledge all technologies used

**Technical Demos:**
- [ ] Meal analysis shown with real UI
- [ ] CLI demo shows actual commands
- [ ] API flow visualization is accurate
- [ ] Food safety alerts demonstrate grounding

**Pacing:**
- [ ] Total duration: 2:30 - 2:45
- [ ] No scene feels rushed or too slow
- [ ] Information density is appropriate
- [ ] Maintains viewer engagement throughout

---

## ⏱️ Production Timeline

### Realistic Schedule (Total: 20-25 hours)

| Phase | Task | Estimated Time |
|-------|------|----------------|
| **Day 1** | | |
| | Script development with Gemini 3 Pro | 2 hours |
| | Storyboard and scene planning | 2 hours |
| | Screenshot capture of UI/demos | 1 hour |
| | **Day 1 Total** | **5 hours** |
| **Day 2** | | |
| | Generate static assets (Imagen 3) | 2 hours |
| | Generate title sequence (Veo 3.1) | 1 hour |
| | Generate background videos (Veo 3.1) | 2 hours |
| | **Day 2 Total** | **5 hours** |
| **Day 3** | | |
| | Convert screenshots to video (Image-to-Video) | 2 hours |
| | Generate feature showcase videos | 3 hours |
| | Generate dividers and transitions | 1 hour |
| | **Day 3 Total** | **6 hours** |
| **Day 4** | | |
| | Create background music (Lyria) | 2 hours |
| | Generate voiceover (Gemini TTS) | 1 hour |
| | Extract and organize sound effects | 1 hour |
| | **Day 4 Total** | **4 hours** |
| **Day 5** | | |
| | Assemble video with FFmpeg | 2 hours |
| | Add text overlays and graphics | 2 hours |
| | Color grading and final polish | 1 hour |
| | Quality assurance and exports | 1 hour |
| | **Day 5 Total** | **6 hours** |
| | | |
| **TOTAL PRODUCTION TIME** | | **26 hours** |

**Accelerated Schedule:** Could be completed in 3 intensive days by parallelizing asset generation.

---

## 💰 Cost Estimation

### Gemini 3 API Costs (Approximate)

| Service | Usage | Est. Cost |
|---------|-------|-----------|
| **Veo 3.1** | 10-15 video generations (8-15 sec each) | $50-75 |
| **Veo 3.1 Fast** | 20-30 shorter clips (3-6 sec each) | $30-45 |
| **Imagen 3** | 15-20 high-quality images | $15-20 |
| **Lyria RealTime** | 3 minutes of music | $5-10 |
| **Gemini TTS** | 500-800 words of narration | $2-5 |
| **Gemini 3 Pro** | Script generation and planning | $3-5 |
| | | |
| **TOTAL ESTIMATED COST** | | **$105-160** |

**Cost Optimization Tips:**
1. Use Veo 3.1 Fast for backgrounds and non-critical scenes (saves ~40%)
2. Generate at 720p first to preview, then 1080p for finals
3. Batch similar scenes together
4. Reuse backgrounds with different overlays
5. Use free trial credits if available

---

## 🔧 Technical Implementation

### Complete Python Automation Script

```python
"""
FCP Demonstration Video Generator
Automates video creation using Gemini 3 technologies
"""

import google.generativeai as genai
from google.cloud import texttospeech
import ffmpeg
import json
from pathlib import Path
from typing import List, Dict
import time

class FCPVideoGenerator:
    """
    Automated video generator for Food Context Protocol demo
    """

    def __init__(self, api_key: str, output_dir: str = "assets"):
        self.api_key = api_key
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Configure Gemini
        genai.configure(api_key=api_key)

        # TTS client
        self.tts_client = texttospeech.TextToSpeechClient()

    def generate_title_sequence(self) -> str:
        """Generate opening title animation"""
        print("🎬 Generating title sequence...")

        video = genai.generate_video(
            model="veo-3.1",
            prompt="""
            Cinematic title sequence: Rotating holographic display of fresh
            food ingredients transforming into data streams, converging into
            a central protocol symbol. Modern tech aesthetic, blue-green
            gradients, 8 seconds, 1080p.
            """,
            duration=8,
            resolution="1080p"
        )

        output_path = self.output_dir / "01_title_sequence.mp4"
        video.save(str(output_path))
        return str(output_path)

    def generate_backgrounds(self) -> Dict[str, str]:
        """Generate all background videos"""
        print("🎨 Generating background videos...")

        backgrounds = {
            "problem": """Slow pan across modern kitchen counter with fresh
                         ingredients, natural lighting, 10 seconds.""",

            "architecture": """Abstract distributed system visualization with
                              flowing data, dark background, 15 seconds.""",

            "demo": """Over-shoulder view of smartphone photographing meal,
                      professional style, 12 seconds."""
        }

        generated = {}
        for name, prompt in backgrounds.items():
            video = genai.generate_video(
                model="veo-3.1",
                prompt=prompt,
                resolution="1080p"
            )
            path = self.output_dir / f"bg_{name}.mp4"
            video.save(str(path))
            generated[name] = str(path)
            time.sleep(2)  # Rate limiting

        return generated

    def generate_static_assets(self) -> Dict[str, str]:
        """Generate logos, icons, diagrams with Imagen 3"""
        print("🖼️  Generating static assets...")

        assets = {
            "logo": """Professional logo for Food Context Protocol, fork and
                      data symbol fusion, green to blue gradient.""",

            "badge_gemini": """Badge reading 'Powered by Gemini 3' with
                              sparkle icon, Google colors.""",

            "architecture": """Technical architecture diagram: 3-tier with
                              clients, FCP server, Gemini 3 services."""
        }

        generated = {}
        for name, prompt in assets.items():
            image = genai.generate_image(
                model="imagen-3",
                prompt=prompt,
                aspect_ratio="1:1" if "logo" in name or "badge" in name else "16:9",
                quality="high"
            )
            path = self.output_dir / f"{name}.png"
            image.save(str(path))
            generated[name] = str(path)

        return generated

    def convert_screenshots_to_video(self, screenshot_dir: str) -> List[str]:
        """Convert UI screenshots to animated demos"""
        print("📸 Converting screenshots to video...")

        screenshot_path = Path(screenshot_dir)
        demos = []

        # Find all screenshots
        for screenshot in screenshot_path.glob("*.png"):
            video = genai.generate_video_from_image(
                model="veo-3.1",
                source_image=str(screenshot),
                prompt=f"""
                Smooth zoom and pan across this interface screenshot,
                emphasizing key UI elements. Professional product demo style,
                6 seconds, 1080p.
                """,
                duration=6,
                resolution="1080p"
            )

            output_path = self.output_dir / f"demo_{screenshot.stem}.mp4"
            video.save(str(output_path))
            demos.append(str(output_path))
            time.sleep(2)

        return demos

    def generate_music(self, duration: int = 180) -> str:
        """Generate background music with Lyria"""
        print("🎵 Generating background music...")

        # Note: This is pseudo-code - actual Lyria API may differ
        music = genai.generate_music(
            style="electronic_ambient",
            duration=duration,
            density="medium",
            brightness="bright",
            scale="major"
        )

        output_path = self.output_dir / "background_music.mp3"
        music.save(str(output_path))
        return str(output_path)

    def generate_voiceover(self, script: List[Dict]) -> List[str]:
        """Generate voiceover narration"""
        print("🎙️  Generating voiceover...")

        voice_config = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Studio-M"
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0
        )

        voiceovers = []
        for segment in script:
            synthesis_input = texttospeech.SynthesisInput(
                text=segment["text"]
            )

            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice_config,
                audio_config=audio_config
            )

            output_path = self.output_dir / f"vo_{segment['section']}.mp3"
            with open(output_path, "wb") as out:
                out.write(response.audio_content)

            voiceovers.append(str(output_path))

        return voiceovers

    def assemble_final_video(self, timeline: List[Dict],
                            output_file: str = "fcp_demo_final.mp4") -> str:
        """Assemble all components into final video"""
        print("🎞️  Assembling final video...")

        # Collect all video segments
        video_inputs = [ffmpeg.input(seg["file"]) for seg in timeline]

        # Concatenate videos
        concatenated = ffmpeg.concat(*video_inputs, v=1, a=0)

        # Add audio tracks
        music = ffmpeg.input(str(self.output_dir / "background_music.mp3"))

        # Mix and output
        output = ffmpeg.output(
            concatenated,
            music,
            output_file,
            vcodec='libx264',
            acodec='aac',
            video_bitrate='5M',
            preset='slow',
            pix_fmt='yuv420p'
        )

        output.run(overwrite_output=True)
        print(f"✅ Final video created: {output_file}")
        return output_file

    def generate_complete_video(self, screenshot_dir: str = "screenshots"):
        """Run complete video generation pipeline"""
        print("🚀 Starting FCP Demo Video Generation Pipeline")
        print("=" * 60)

        # Phase 1: Script (assume already done)
        print("\n📝 Phase 1: Script Development (manual)")

        # Phase 2: Generate assets
        print("\n🎨 Phase 2: Asset Generation")
        self.generate_title_sequence()
        self.generate_backgrounds()
        self.generate_static_assets()

        # Phase 3: Convert demos
        print("\n🎥 Phase 3: Demo Video Creation")
        self.convert_screenshots_to_video(screenshot_dir)

        # Phase 4: Audio
        print("\n🎵 Phase 4: Audio Production")
        self.generate_music()

        # Voiceover script (example)
        vo_script = [
            {
                "section": "intro",
                "text": "Every food app rebuilds the same features from scratch."
            },
            {
                "section": "solution",
                "text": "Introducing the Food Context Protocol."
            }
        ]
        self.generate_voiceover(vo_script)

        # Phase 5: Assembly (would need full timeline)
        print("\n🎞️  Phase 5: Video Assembly")
        print("Ready for manual assembly with timeline configuration")

        print("\n✅ Video generation pipeline complete!")
        print(f"All assets saved to: {self.output_dir}")


# Usage
if __name__ == "__main__":
    # Initialize generator
    generator = FCPVideoGenerator(
        api_key="YOUR_GEMINI_API_KEY",
        output_dir="video_assets"
    )

    # Run complete pipeline
    generator.generate_complete_video(screenshot_dir="ui_screenshots")
```

---

## 📚 Additional Resources

### Gemini 3 Documentation
- [Veo 3.1 Video Generation API](https://ai.google.dev/gemini-api/docs/video)
- [Imagen 3 Image Generation](https://ai.google.dev/gemini-api/docs/imagen)
- [Lyria Music Generation](https://ai.google.dev/gemini-api/docs/music-generation)
- [Gemini TTS API](https://ai.google.dev/gemini-api/docs/speech-generation)

### Video Editing Tools
- **FFmpeg:** Command-line video processing
- **DaVinci Resolve:** Professional color grading (free version)
- **Blender:** 3D text animations and effects
- **After Effects:** Advanced motion graphics (if needed)

### Font Recommendations
- **Inter:** Modern, readable, excellent for UI text
- **JetBrains Mono:** Code snippets and terminal
- **Poppins:** Friendly, approachable headers

---

## 🎯 Success Metrics

### Devpost Judging Criteria Alignment

| Criterion | How Video Addresses It |
|-----------|------------------------|
| **Technical Complexity** | Shows 40+ tools, dual transport, production-ready code |
| **Innovation** | Highlights protocol-first approach, like "Stripe for food" |
| **Gemini Integration** | Demonstrates 15+ Gemini 3 features in detail |
| **Practical Impact** | Shows real use cases: meal logging, safety, recipes |
| **Completeness** | Showcases full stack: spec, server, CLI, SDKs, docs |
| **Polish** | Professional video production using Gemini 3 itself |

---

## 🚀 Next Steps

1. **Review and approve this plan**
2. **Gather UI screenshots** of all key features
3. **Set up Gemini API access** and test credentials
4. **Run script generation** phase with Gemini 3 Pro
5. **Begin asset generation** (can parallelize)
6. **Create video timeline** specification
7. **Execute assembly** and quality check
8. **Export and upload** to Devpost

---

## 📝 Notes

- **API Rate Limits:** Be mindful of Gemini API quotas; space out requests
- **Preview First:** Generate at 720p to preview before committing to 1080p
- **Backup Assets:** Save all generated assets before assembly
- **Version Control:** Keep timeline configurations in version control
- **Iterative Approach:** Generate core video first, then polish

---

## ✅ Final Checklist

Before submission:

- [ ] Video demonstrates all core FCP features
- [ ] Gemini 3 integration is clearly highlighted
- [ ] Professional audio quality (no clipping, clear voice)
- [ ] All text is readable and properly timed
- [ ] Branding is consistent throughout
- [ ] Credits acknowledge all technologies
- [ ] Video meets technical specifications
- [ ] File size is reasonable for upload
- [ ] Tested playback on multiple devices
- [ ] Call to action is clear and prominent

---

**Good luck with your Devpost submission! 🎉**

This video plan leverages the full power of Gemini 3 technologies to create a compelling demonstration that showcases both your Food Context Protocol and Google's AI capabilities. The recursive nature of "building with Gemini, demonstrating with Gemini" creates a powerful narrative for judges.
