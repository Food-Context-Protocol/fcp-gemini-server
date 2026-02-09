#!/usr/bin/env python3
"""Generate Food Context Protocol (FCP) logos using Gemini 3 Pro Image.

This script generates various logo styles for FCP using Gemini's advanced
image generation capabilities (Nano Banana Pro).

Usage:
    # Set your API key
    export GEMINI_API_KEY=your-api-key

    # Generate default wordmark logo
    python scripts/generate_logo.py

    # Generate specific style
    python scripts/generate_logo.py --style icon

    # Generate all styles
    python scripts/generate_logo.py --all

    # Custom prompt
    python scripts/generate_logo.py --custom "minimalist fork and bowl icon"

Available Styles:
    - wordmark: Clean text-based logo
    - icon: Circular app icon with food symbols
    - full: Wordmark + icon combination
    - badge: Circular badge with text
    - monochrome: Black and white version
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from google import genai
except ImportError:
    print("Error: google-genai package not installed")
    print("Install with: pip install google-genai")
    sys.exit(1)


# Available image generation models
MODELS = {
    "pro": "gemini-3-pro-image-preview",  # Nano Banana Pro - best quality, 4K
    "flash": "gemini-2.5-flash-image",     # Nano Banana - faster
}

# Color palette for FCP
COLORS = {
    "primary": "#2E7D32",      # Forest Green - natural, healthy
    "secondary": "#FF6F00",    # Orange - energy, food
    "accent": "#1976D2",       # Blue - trust, technology
    "dark": "#212121",         # Dark gray - professional
    "light": "#FAFAFA",        # Off-white - clean
}

# Logo style prompts
LOGO_PROMPTS = {
    "wordmark": f"""Create a clean, modern wordmark logo for "Food Context Protocol"

Requirements:
- Text arrangement: "FOOD CONTEXT PROTOCOL" or "FCP" with full name below
- Modern, professional sans-serif font (like Montserrat, Inter, or SF Pro)
- Color scheme: {COLORS['primary']} (green) for "FOOD", {COLORS['accent']} (blue) for "PROTOCOL"
- The word "CONTEXT" could be lighter weight or gray
- Clean white or light background
- No icons, just typography
- Suitable for use as a GitHub organization header
- High contrast, legible at small and large sizes
- Professional, trustworthy, tech-forward appearance
- Wide format (1400x800px ideal)
""",

    "icon": f"""Create a minimalist circular app icon for "FCP" (Food Context Protocol)

Requirements:
- Circular icon suitable for mobile app or avatar
- Central symbol: A stylized fork, spoon, or bowl combined with a data/tech element (dots, nodes, or circuit pattern)
- 2-3 colors: {COLORS['primary']} (green), {COLORS['secondary']} (orange), white
- Flat vector style, modern and minimal
- White or transparent background
- No text, just the iconic symbol
- High contrast, recognizable at small sizes (64x64 to 1024x1024)
- Conveys: food, nutrition, technology, intelligence
- Suitable for use as app icon, favicon, or avatar
- Square format (1024x1024px)
""",

    "full": f"""Create a complete horizontal logo combining wordmark and icon for "Food Context Protocol"

Requirements:
- Icon on left: Minimalist food/tech symbol (fork, bowl, or plate with data nodes)
- Text on right: "Food Context Protocol" with optional "FCP" subtitle
- Colors: {COLORS['primary']} (green) for icon, {COLORS['dark']} (dark gray) for text
- Modern sans-serif font
- White or light background
- Balanced composition, professional appearance
- Wide format (1600x600px)
- High contrast, works on light and dark backgrounds
- Suitable for website headers, documentation, presentations
""",

    "badge": f"""Create a circular badge logo for "Food Context Protocol"

Requirements:
- Circular badge design (like a seal or emblem)
- Outer ring: "FOOD CONTEXT PROTOCOL" text curved around the circle
- Center: Stylized food/tech icon (fork + data nodes, or bowl + circuits)
- Colors: {COLORS['primary']} (green) border, {COLORS['dark']} (dark) text, white background
- Professional, authoritative appearance
- Suitable for certificates, documentation, official materials
- Square format (1200x1200px)
- Clean, high-contrast design
""",

    "monochrome": f"""Create a black and white minimalist logo for "Food Context Protocol"

Requirements:
- Pure black (#000000) on white background
- Can be either wordmark, icon, or combined
- Extremely clean, minimal design
- Must work at any size (vector-style aesthetic)
- High contrast, bold lines
- Suitable for print, black-and-white documentation, watermarks
- Professional, timeless appearance
- Format: 1400x800px for wordmark, 1024x1024px for icon
""",

    "social": f"""Create a square social media profile logo for "FCP"

Requirements:
- Square format (1200x1200px)
- Can contain "FCP" text or food/tech icon, or both
- Optimized for social media: Twitter, LinkedIn, GitHub, Discord
- Colors: {COLORS['primary']} (green) and {COLORS['secondary']} (orange)
- Light or white background
- Bold, recognizable at thumbnail sizes
- Clean, modern, tech-forward appearance
- High contrast
""",
}


def generate_logo(
    prompt: str,
    model: str = "pro",
    output_path: str = "static/logos/fcp-logo.png",
) -> str | None:
    """Generate a logo using Gemini image generation.

    Args:
        prompt: The image generation prompt
        model: Model to use ("pro" or "flash")
        output_path: Where to save the generated image

    Returns:
        Path to saved image, or None if failed
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set")
        print("Get your API key at: https://aistudio.google.com/apikey")
        return None

    model_name = MODELS.get(model, MODELS["pro"])
    print(f"Using model: {model_name}")
    print(f"Generating: {output_path}")
    print()

    # Initialize client
    client = genai.Client(api_key=api_key)

    print("Generating image with Gemini...")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt],
        )
    except Exception as e:
        print(f"Error generating image: {e}")
        return None

    # Extract and save image
    for part in response.parts:
        if hasattr(part, "text") and part.text:
            print(f"Model response: {part.text}")
        elif hasattr(part, "inline_data") and part.inline_data:
            try:
                # Ensure output directory exists
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)

                image = part.as_image()
                image.save(output_file)
                print(f"✓ Logo saved to: {output_file}")
                return str(output_file)
            except Exception as e:
                print(f"Error saving image: {e}")
                return None

    print("⚠ No image was generated. The model may have returned text only.")
    if hasattr(response, "text") and response.text:
        print(f"Response: {response.text}")
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Generate FCP logos using Gemini 3 Pro Image",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
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
    parser.add_argument(
        "--custom",
        type=str,
        help="Custom prompt instead of predefined style",
    )
    parser.add_argument(
        "--model",
        choices=["pro", "flash"],
        default="pro",
        help="Model to use (default: pro for best quality)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output path (default: auto-generated based on style)",
    )

    args = parser.parse_args()

    # Determine project root (script is in scripts/)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    logos_dir = project_root / "static" / "logos"

    print("=" * 60)
    print("FCP Logo Generator")
    print("=" * 60)
    print()

    if args.custom:
        # Custom prompt
        output_path = args.output or str(logos_dir / "fcp-custom.png")
        result = generate_logo(
            prompt=args.custom,
            model=args.model,
            output_path=output_path,
        )
        if result:
            print()
            print(f"✓ Success! View with: open {result}")

    elif args.all:
        # Generate all styles
        results = []
        for style_name, prompt in LOGO_PROMPTS.items():
            output_path = str(logos_dir / f"fcp-{style_name}.png")
            print(f"Generating {style_name} logo...")
            result = generate_logo(
                prompt=prompt,
                model=args.model,
                output_path=output_path,
            )
            if result:
                results.append(result)
            print()

        print("=" * 60)
        print(f"✓ Generated {len(results)}/{len(LOGO_PROMPTS)} logos")
        print()
        print("Generated logos:")
        for path in results:
            print(f"  - {path}")
        print()
        print(f"View all: open {logos_dir}")

    else:
        # Generate single style
        prompt = LOGO_PROMPTS[args.style]
        output_path = args.output or str(logos_dir / f"fcp-{args.style}.png")

        result = generate_logo(
            prompt=prompt,
            model=args.model,
            output_path=output_path,
        )

        if result:
            print()
            print("=" * 60)
            print("Success!")
            print("=" * 60)
            print(f"View logo: open {result}")
            print()
            print("Next steps:")
            print("  - Generate other styles: python scripts/generate_logo.py --all")
            print("  - Try custom prompt: python scripts/generate_logo.py --custom 'your prompt'")
            print("  - Upload to GitHub: https://github.com/organizations/Food-Context-Protocol/settings/profile")
            print()
            print("Available styles:")
            for style in LOGO_PROMPTS.keys():
                print(f"  - {style}")


if __name__ == "__main__":
    main()
