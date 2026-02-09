#!/usr/bin/env python3
"""Generate mockup visuals for preview"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_mockup(filename, text, color, size=(1920, 1080)):
    """Create a simple mockup image"""
    img = Image.new('RGB', size, color=color)
    draw = ImageDraw.Draw(img)

    # Try to get a font
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)
    except:
        font = ImageFont.load_default()

    # Draw text
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2

    draw.text((x, y), text, fill='white', font=font)
    img.save(filename)
    print(f"✓ Created {filename}")

# Create mockups
create_mockup('screenshots/01_dashboard.png', 'Dashboard View', '#1E1E1E')
create_mockup('screenshots/02_meal_analysis_input.png', 'Upload Meal Photo', '#2196F3')
create_mockup('screenshots/03_meal_analysis_results.png', 'Nutrition Analysis', '#4CAF50')
create_mockup('screenshots/05_voice_logging.png', 'Voice Input', '#9C27B0')
create_mockup('screenshots/06_function_calling.png', 'Function Calling', '#FF9800')
create_mockup('screenshots/08_safety_alert.png', '⚠️ Safety Alert', '#F44336')
create_mockup('screenshots/09_gemini_live_chat.png', 'Live Chat', '#00BCD4')
create_mockup('test_assets/architecture_diagram.png', 'Architecture', '#607D8B')

print("\n✅ Generated 8 mockup visuals")
