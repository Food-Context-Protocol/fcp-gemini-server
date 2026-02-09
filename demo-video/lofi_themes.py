"""
Lo-fi color themes for FCP demo video scenarios.

Each scenario gets a distinct mood while sharing the same visual framework.
Import a theme dict and pass it to generators/compositors.
"""

# Apple Color Emoji only supports these exact pixel sizes
EMOJI_VALID_SIZES = [48, 64, 96, 160]

# ─── Scenario Themes ─────────────────────────────────────────

THEMES = {
    "recipe_quest": {
        "name": "Recipe Quest",
        "emoji_categories": ["dishes", "ingredients", "kitchen"],
        "bg_dark": (45, 30, 22),
        "bg_gradient": (70, 48, 35),
        "accent_warm": (255, 183, 120),
        "accent_secondary": (220, 140, 130),
        "accent_cream": (255, 240, 210),
        "text_primary": (255, 248, 235),
        "text_secondary": (200, 180, 155),
        "text_dim": (150, 125, 100),
        "border_glow": (180, 120, 60),
        "description": "Warm kitchen browns — cozy cooking vibe",
    },
    "food_scanner": {
        "name": "Food Scanner",
        "emoji_categories": ["ingredients", "dishes"],
        "bg_dark": (40, 28, 15),
        "bg_gradient": (65, 45, 25),
        "accent_warm": (255, 190, 80),
        "accent_secondary": (240, 160, 60),
        "accent_cream": (255, 235, 190),
        "text_primary": (255, 245, 225),
        "text_secondary": (200, 175, 140),
        "text_dim": (155, 130, 95),
        "border_glow": (200, 140, 50),
        "description": "Golden amber — warm candlelight kitchen",
    },
    "meal_log": {
        "name": "Meal Log",
        "emoji_categories": ["dishes", "sweet"],
        "bg_dark": (42, 28, 18),
        "bg_gradient": (72, 50, 30),
        "accent_warm": (255, 170, 90),
        "accent_secondary": (255, 140, 80),
        "accent_cream": (255, 230, 195),
        "text_primary": (255, 248, 230),
        "text_secondary": (210, 180, 145),
        "text_dim": (160, 130, 95),
        "border_glow": (200, 130, 50),
        "description": "Sunrise orange — morning routine warmth",
    },
    "allergen_alert": {
        "name": "Allergen Alert",
        "emoji_categories": ["ingredients", "kitchen"],
        "bg_dark": (22, 28, 42),
        "bg_gradient": (35, 45, 68),
        "accent_warm": (130, 180, 255),
        "accent_secondary": (220, 100, 100),
        "accent_cream": (210, 225, 255),
        "text_primary": (240, 245, 255),
        "text_secondary": (160, 175, 200),
        "text_dim": (110, 125, 155),
        "border_glow": (90, 120, 200),
        "description": "Cool blue with red accents — alert but calm",
    },
    "mcp_toolbox": {
        "name": "MCP Toolbox",
        "emoji_categories": ["kitchen", "dishes"],
        "bg_dark": (25, 18, 38),
        "bg_gradient": (45, 32, 65),
        "accent_warm": (180, 140, 255),
        "accent_secondary": (140, 200, 255),
        "accent_cream": (220, 210, 255),
        "text_primary": (245, 240, 255),
        "text_secondary": (175, 165, 200),
        "text_dim": (120, 110, 155),
        "border_glow": (130, 90, 200),
        "description": "Deep purple — technical cosmic vibe",
    },
    "gemini_brain": {
        "name": "Gemini Brain",
        "emoji_categories": ["dishes", "sweet", "ingredients"],
        "bg_dark": (35, 30, 22),
        "bg_gradient": (60, 52, 38),
        "accent_warm": (255, 220, 140),
        "accent_secondary": (255, 200, 100),
        "accent_cream": (255, 245, 215),
        "text_primary": (255, 250, 240),
        "text_secondary": (200, 190, 165),
        "text_dim": (155, 145, 120),
        "border_glow": (200, 170, 80),
        "description": "Ethereal gold — AI mystique warmth",
    },
}

DEFAULT_THEME = "recipe_quest"


def get_theme(scenario: str = None) -> dict:
    """Get theme by scenario name, fallback to default."""
    if scenario and scenario in THEMES:
        return THEMES[scenario]
    return THEMES[DEFAULT_THEME]


def list_themes():
    """Print available themes."""
    for key, theme in THEMES.items():
        print(f"  {key:20s} — {theme['description']}")
