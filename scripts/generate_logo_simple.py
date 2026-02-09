#!/usr/bin/env python3
"""Generate FCP logos programmatically using PIL/Pillow (no API required).

This creates clean, professional logos without requiring Gemini API access.
Uses typography and geometric shapes to create various logo styles.

Usage:
    # Generate all logo styles
    python scripts/generate_logo_simple.py --all

    # Generate specific style
    python scripts/generate_logo_simple.py --style wordmark

    # List available styles
    python scripts/generate_logo_simple.py --list
"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: Pillow package not installed")
    print("Install with: pip install pillow")
    sys.exit(1)


# FCP Brand Colors
COLORS = {
    "green": "#2E7D32",      # Forest Green - natural, healthy
    "orange": "#FF6F00",     # Orange - energy, food
    "blue": "#1976D2",       # Blue - trust, technology
    "dark": "#212121",       # Dark gray - professional
    "light": "#FAFAFA",      # Off-white - clean
    "white": "#FFFFFF",      # Pure white
}


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def create_wordmark(output_path: str, size=(1400, 800)):
    """Create a clean wordmark logo."""
    img = Image.new("RGB", size, hex_to_rgb(COLORS["white"]))
    draw = ImageDraw.Draw(img)

    # Try to use a nice font, fall back to default if not available
    try:
        # Try SF Pro or Helvetica on macOS
        font_large = ImageFont.truetype("/System/Library/Fonts/SFNSDisplay.ttf", 120)
        font_medium = ImageFont.truetype("/System/Library/Fonts/SFNSDisplay.ttf", 80)
        font_small = ImageFont.truetype("/System/Library/Fonts/SFNSDisplay.ttf", 60)
    except:
        try:
            # Fall back to Arial/Helvetica
            font_large = ImageFont.truetype("/Library/Fonts/Arial.ttf", 120)
            font_medium = ImageFont.truetype("/Library/Fonts/Arial.ttf", 80)
            font_small = ImageFont.truetype("/Library/Fonts/Arial.ttf", 60)
        except:
            # Last resort: default font
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

    # Calculate text positions
    center_x = size[0] // 2
    center_y = size[1] // 2

    # Draw "FCP" large
    fcp_text = "FCP"
    bbox = draw.textbbox((0, 0), fcp_text, font=font_large)
    fcp_width = bbox[2] - bbox[0]
    fcp_x = center_x - fcp_width // 2
    fcp_y = center_y - 150
    draw.text((fcp_x, fcp_y), fcp_text, fill=hex_to_rgb(COLORS["green"]), font=font_large)

    # Draw "Food Context Protocol" below
    full_text = "Food Context Protocol"
    bbox = draw.textbbox((0, 0), full_text, font=font_small)
    full_width = bbox[2] - bbox[0]
    full_x = center_x - full_width // 2
    full_y = fcp_y + 150
    draw.text((full_x, full_y), full_text, fill=hex_to_rgb(COLORS["dark"]), font=font_small)

    img.save(output_path)
    return output_path


def create_icon(output_path: str, size=(1024, 1024)):
    """Create a circular app icon with fork/spoon symbol."""
    img = Image.new("RGB", size, hex_to_rgb(COLORS["white"]))
    draw = ImageDraw.Draw(img)

    # Draw circle background
    margin = 50
    circle_bbox = [margin, margin, size[0] - margin, size[1] - margin]
    draw.ellipse(circle_bbox, fill=hex_to_rgb(COLORS["green"]))

    # Draw simple fork shape (three tines)
    center_x = size[0] // 2
    center_y = size[1] // 2

    # Fork handle
    handle_width = 40
    handle_height = 400
    handle_x = center_x - handle_width // 2
    handle_y = center_y - 50
    draw.rectangle(
        [handle_x, handle_y, handle_x + handle_width, handle_y + handle_height],
        fill=hex_to_rgb(COLORS["white"])
    )

    # Fork tines (three vertical lines)
    tine_width = 30
    tine_height = 200
    tine_spacing = 80
    tine_y = handle_y - tine_height

    for i in range(3):
        tine_x = center_x - tine_width // 2 + (i - 1) * tine_spacing
        draw.rectangle(
            [tine_x, tine_y, tine_x + tine_width, tine_y + tine_height],
            fill=hex_to_rgb(COLORS["white"])
        )

    # Add small "FCP" text at bottom
    try:
        font = ImageFont.truetype("/System/Library/Fonts/SFNSDisplay.ttf", 80)
    except:
        font = ImageFont.load_default()

    text = "FCP"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_x = center_x - text_width // 2
    text_y = center_y + 250
    draw.text((text_x, text_y), text, fill=hex_to_rgb(COLORS["white"]), font=font)

    img.save(output_path)
    return output_path


def create_badge(output_path: str, size=(1200, 1200)):
    """Create a circular badge/seal logo."""
    img = Image.new("RGB", size, hex_to_rgb(COLORS["white"]))
    draw = ImageDraw.Draw(img)

    center = size[0] // 2

    # Outer circle (border)
    margin = 50
    border_width = 20
    draw.ellipse(
        [margin, margin, size[0] - margin, size[1] - margin],
        outline=hex_to_rgb(COLORS["green"]),
        width=border_width
    )

    # Inner circle (lighter)
    inner_margin = margin + 80
    draw.ellipse(
        [inner_margin, inner_margin, size[0] - inner_margin, size[1] - inner_margin],
        outline=hex_to_rgb(COLORS["blue"]),
        width=5
    )

    # Center text "FCP"
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/SFNSDisplay.ttf", 200)
        font_small = ImageFont.truetype("/System/Library/Fonts/SFNSDisplay.ttf", 50)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw "FCP"
    text = "FCP"
    bbox = draw.textbbox((0, 0), text, font=font_large)
    text_width = bbox[2] - bbox[0]
    text_x = center - text_width // 2
    text_y = center - 150
    draw.text((text_x, text_y), text, fill=hex_to_rgb(COLORS["green"]), font=font_large)

    # Draw subtitle
    subtitle = "FOOD CONTEXT PROTOCOL"
    bbox = draw.textbbox((0, 0), subtitle, font=font_small)
    sub_width = bbox[2] - bbox[0]
    sub_x = center - sub_width // 2
    sub_y = text_y + 250
    draw.text((sub_x, sub_y), subtitle, fill=hex_to_rgb(COLORS["dark"]), font=font_small)

    img.save(output_path)
    return output_path


def create_monochrome(output_path: str, size=(1400, 800)):
    """Create a black and white minimal logo."""
    img = Image.new("RGB", size, (255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/SFNSDisplay.ttf", 150)
        font_small = ImageFont.truetype("/System/Library/Fonts/SFNSDisplay.ttf", 60)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    center_x = size[0] // 2
    center_y = size[1] // 2

    # Draw "FCP"
    text = "FCP"
    bbox = draw.textbbox((0, 0), text, font=font_large)
    text_width = bbox[2] - bbox[0]
    text_x = center_x - text_width // 2
    text_y = center_y - 120
    draw.text((text_x, text_y), text, fill=(0, 0, 0), font=font_large)

    # Draw underline
    line_y = text_y + 170
    line_margin = 100
    draw.line(
        [(line_margin, line_y), (size[0] - line_margin, line_y)],
        fill=(0, 0, 0),
        width=5
    )

    # Draw subtitle
    subtitle = "Food Context Protocol"
    bbox = draw.textbbox((0, 0), subtitle, font=font_small)
    sub_width = bbox[2] - bbox[0]
    sub_x = center_x - sub_width // 2
    sub_y = line_y + 30
    draw.text((sub_x, sub_y), subtitle, fill=(0, 0, 0), font=font_small)

    img.save(output_path)
    return output_path


def create_social(output_path: str, size=(1200, 1200)):
    """Create a square social media profile logo."""
    img = Image.new("RGB", size, hex_to_rgb(COLORS["white"]))
    draw = ImageDraw.Draw(img)

    # Draw gradient-like background (two-tone)
    top_color = hex_to_rgb(COLORS["green"])
    bottom_color = hex_to_rgb(COLORS["blue"])

    # Top half
    draw.rectangle([0, 0, size[0], size[1] // 2], fill=top_color)
    # Bottom half
    draw.rectangle([0, size[1] // 2, size[0], size[1]], fill=bottom_color)

    # Draw "FCP" in white
    try:
        font = ImageFont.truetype("/System/Library/Fonts/SFNSDisplay.ttf", 300)
    except:
        font = ImageFont.load_default()

    text = "FCP"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (size[0] - text_width) // 2
    text_y = (size[1] - text_height) // 2 - 50

    # Draw text with outline for contrast
    outline_width = 8
    for offset_x in range(-outline_width, outline_width + 1):
        for offset_y in range(-outline_width, outline_width + 1):
            if offset_x != 0 or offset_y != 0:
                draw.text(
                    (text_x + offset_x, text_y + offset_y),
                    text,
                    fill=hex_to_rgb(COLORS["dark"]),
                    font=font
                )
    draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)

    img.save(output_path)
    return output_path


def create_full(output_path: str, size=(1600, 600)):
    """Create a full logo with icon and text."""
    img = Image.new("RGB", size, hex_to_rgb(COLORS["white"]))
    draw = ImageDraw.Draw(img)

    # Draw icon on left (simple circle with fork)
    icon_size = 400
    icon_x = 100
    icon_y = (size[1] - icon_size) // 2

    # Circle
    draw.ellipse(
        [icon_x, icon_y, icon_x + icon_size, icon_y + icon_size],
        fill=hex_to_rgb(COLORS["green"])
    )

    # Simple fork in circle
    fork_center_x = icon_x + icon_size // 2
    fork_center_y = icon_y + icon_size // 2
    fork_width = 15
    fork_height = 200

    # Fork tines
    for i in range(3):
        tine_x = fork_center_x - fork_width // 2 + (i - 1) * 40
        tine_y = fork_center_y - fork_height // 2
        draw.rectangle(
            [tine_x, tine_y, tine_x + fork_width, tine_y + fork_height],
            fill=hex_to_rgb(COLORS["white"])
        )

    # Text on right
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/SFNSDisplay.ttf", 120)
        font_small = ImageFont.truetype("/System/Library/Fonts/SFNSDisplay.ttf", 50)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    text_x = icon_x + icon_size + 100
    text_y_center = size[1] // 2

    # Draw "FCP"
    draw.text((text_x, text_y_center - 80), "FCP", fill=hex_to_rgb(COLORS["green"]), font=font_large)

    # Draw subtitle
    draw.text((text_x, text_y_center + 50), "Food Context Protocol", fill=hex_to_rgb(COLORS["dark"]), font=font_small)

    img.save(output_path)
    return output_path


LOGO_GENERATORS = {
    "wordmark": create_wordmark,
    "icon": create_icon,
    "badge": create_badge,
    "monochrome": create_monochrome,
    "social": create_social,
    "full": create_full,
}


def main():
    parser = argparse.ArgumentParser(
        description="Generate FCP logos programmatically (no API required)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--style",
        choices=list(LOGO_GENERATORS.keys()),
        help="Logo style to generate",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate all logo styles",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available logo styles",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="static/logos",
        help="Output directory (default: static/logos)",
    )

    args = parser.parse_args()

    if args.list:
        print("\nAvailable logo styles:")
        for style in LOGO_GENERATORS.keys():
            print(f"  - {style}")
        print()
        return

    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    output_dir = project_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("FCP Logo Generator (Programmatic)")
    print("=" * 60)
    print()

    if args.all:
        results = []
        for style_name, generator_func in LOGO_GENERATORS.items():
            output_path = output_dir / f"fcp-{style_name}.png"
            print(f"Generating {style_name}...")
            try:
                generator_func(str(output_path))
                results.append(str(output_path))
                print(f"✓ Saved to: {output_path}")
            except Exception as e:
                print(f"✗ Error: {e}")
            print()

        print("=" * 60)
        print(f"✓ Generated {len(results)}/{len(LOGO_GENERATORS)} logos")
        print()
        print("Generated logos:")
        for path in results:
            print(f"  - {path}")
        print()
        print(f"View all: open {output_dir}")

    elif args.style:
        output_path = output_dir / f"fcp-{args.style}.png"
        print(f"Generating {args.style}...")
        try:
            LOGO_GENERATORS[args.style](str(output_path))
            print(f"✓ Saved to: {output_path}")
            print()
            print(f"View: open {output_path}")
        except Exception as e:
            print(f"✗ Error: {e}")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
