"""Function definitions for Gemini 3 Function Calling.

This module defines all the tools/functions that Gemini can call
for structured data extraction and actions.

These are used with gemini.generate_with_tools() for reliable
structured output via function calling instead of JSON mode.
"""

# =============================================================================
# Food Analysis Tools
# =============================================================================

EXTRACT_NUTRITION = {
    "name": "extract_nutrition",
    "description": "Extract nutritional information from identified food. Call this to report the estimated nutrition values.",
    "parameters": {
        "type": "object",
        "properties": {
            "calories": {
                "type": "number",
                "description": "Estimated calories per serving",
            },
            "protein_g": {
                "type": "number",
                "description": "Protein in grams",
            },
            "carbs_g": {
                "type": "number",
                "description": "Carbohydrates in grams",
            },
            "fat_g": {
                "type": "number",
                "description": "Fat in grams",
            },
            "fiber_g": {
                "type": "number",
                "description": "Fiber in grams",
            },
            "sodium_mg": {
                "type": "number",
                "description": "Sodium in milligrams",
            },
            "sugar_g": {
                "type": "number",
                "description": "Sugar in grams",
            },
            "serving_size": {
                "type": "string",
                "description": "Estimated serving size (e.g., '1 cup', '1 plate')",
            },
        },
        "required": ["calories", "protein_g", "carbs_g", "fat_g"],
    },
}

IDENTIFY_DISH = {
    "name": "identify_dish",
    "description": "Identify the dish name and cuisine from the food image or description.",
    "parameters": {
        "type": "object",
        "properties": {
            "dish_name": {
                "type": "string",
                "description": "Name of the dish",
            },
            "cuisine": {
                "type": "string",
                "description": "Cuisine type (e.g., Italian, Japanese, Mexican)",
            },
            "cooking_method": {
                "type": "string",
                "description": "How the food was prepared (e.g., grilled, fried, steamed)",
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score from 0 to 1",
            },
        },
        "required": ["dish_name"],
    },
}

IDENTIFY_INGREDIENTS = {
    "name": "identify_ingredients",
    "description": "Identify the ingredients visible or likely present in the food.",
    "parameters": {
        "type": "object",
        "properties": {
            "ingredients": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "amount": {"type": "string"},
                        "is_visible": {"type": "boolean"},
                    },
                },
                "description": "List of ingredients with estimated amounts",
            },
        },
        "required": ["ingredients"],
    },
}

IDENTIFY_ALLERGENS = {
    "name": "identify_allergens",
    "description": "Identify potential allergens present in the food.",
    "parameters": {
        "type": "object",
        "properties": {
            "allergens": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of allergens (e.g., gluten, dairy, nuts, shellfish, eggs, soy)",
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score from 0 to 1",
            },
            "warnings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Additional warnings about potential cross-contamination",
            },
        },
        "required": ["allergens"],
    },
}

CLASSIFY_DIETARY_TAGS = {
    "name": "classify_dietary_tags",
    "description": "Classify the food's dietary compatibility.",
    "parameters": {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Dietary tags (e.g., vegetarian, vegan, keto, paleo, low-carb)",
            },
            "vegetarian": {
                "type": "boolean",
                "description": "Whether the dish is vegetarian",
            },
            "vegan": {
                "type": "boolean",
                "description": "Whether the dish is vegan",
            },
            "gluten_free": {
                "type": "boolean",
                "description": "Whether the dish is gluten-free",
            },
            "dairy_free": {
                "type": "boolean",
                "description": "Whether the dish is dairy-free",
            },
            "keto_friendly": {
                "type": "boolean",
                "description": "Whether the dish is keto-friendly",
            },
        },
        "required": ["tags", "vegetarian", "vegan", "gluten_free"],
    },
}

RATE_SPICE_LEVEL = {
    "name": "rate_spice_level",
    "description": "Rate the spiciness level of the food.",
    "parameters": {
        "type": "object",
        "properties": {
            "spice_level": {
                "type": "integer",
                "description": "Spice level from 0 (not spicy) to 5 (extremely spicy)",
                "minimum": 0,
                "maximum": 5,
            },
            "spice_notes": {
                "type": "string",
                "description": "Description of the spiciness (e.g., 'mild jalapeño heat')",
            },
        },
        "required": ["spice_level"],
    },
}

# All food analysis tools combined
FOOD_ANALYSIS_TOOLS = [
    IDENTIFY_DISH,
    IDENTIFY_INGREDIENTS,
    EXTRACT_NUTRITION,
    IDENTIFY_ALLERGENS,
    CLASSIFY_DIETARY_TAGS,
    RATE_SPICE_LEVEL,
]


# =============================================================================
# Media Processing Tools (for autonomous agents)
# =============================================================================

DETECT_FOOD_IN_IMAGE = {
    "name": "detect_food_in_image",
    "description": "Detect whether an image contains food and should be processed.",
    "parameters": {
        "type": "object",
        "properties": {
            "is_food": {
                "type": "boolean",
                "description": "Whether the image contains food",
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score from 0 to 1",
            },
            "food_type": {
                "type": "string",
                "description": "Type of food if detected (meal, snack, drink, ingredient)",
            },
        },
        "required": ["is_food", "confidence"],
    },
}

EXTRACT_VENUE_INFO = {
    "name": "extract_venue_info",
    "description": "Extract restaurant or venue information visible in the image or context.",
    "parameters": {
        "type": "object",
        "properties": {
            "venue_name": {
                "type": "string",
                "description": "Name of the restaurant or venue if visible",
            },
            "venue_type": {
                "type": "string",
                "description": "Type of venue (restaurant, cafe, home, food truck, etc.)",
            },
            "location_hint": {
                "type": "string",
                "description": "Any location hints visible (city, neighborhood, etc.)",
            },
        },
    },
}

MEDIA_PROCESSING_TOOLS = [
    DETECT_FOOD_IN_IMAGE,
    IDENTIFY_DISH,
    IDENTIFY_INGREDIENTS,
    EXTRACT_NUTRITION,
    EXTRACT_VENUE_INFO,
]


# =============================================================================
# Discovery Agent Tools
# =============================================================================

SAVE_RECOMMENDATION = {
    "name": "save_recommendation",
    "description": "Save a food recommendation for the user to review later.",
    "parameters": {
        "type": "object",
        "properties": {
            "recommendation_type": {
                "type": "string",
                "enum": ["restaurant", "dish", "recipe", "ingredient"],
                "description": "Type of recommendation",
            },
            "name": {
                "type": "string",
                "description": "Name of the recommended item",
            },
            "reason": {
                "type": "string",
                "description": "Why this is recommended for the user",
            },
            "match_score": {
                "type": "number",
                "description": "How well this matches user preferences (0-1)",
            },
            "details": {
                "type": "object",
                "description": "Additional details about the recommendation",
            },
        },
        "required": ["recommendation_type", "name", "reason"],
    },
}

NOTIFY_USER = {
    "name": "notify_user",
    "description": "Send a notification to the user about a discovery.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Notification title",
            },
            "message": {
                "type": "string",
                "description": "Notification message",
            },
            "priority": {
                "type": "string",
                "enum": ["low", "normal", "high"],
                "description": "Notification priority",
            },
        },
        "required": ["title", "message"],
    },
}

DISCOVERY_AGENT_TOOLS = [
    SAVE_RECOMMENDATION,
    NOTIFY_USER,
]


# =============================================================================
# Content Generation Tools (for blog/social agent)
# =============================================================================

GENERATE_CAPTION = {
    "name": "generate_caption",
    "description": "Generate a social media caption for a food photo or meal.",
    "parameters": {
        "type": "object",
        "properties": {
            "caption": {
                "type": "string",
                "description": "The generated caption",
            },
            "hashtags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Suggested hashtags",
            },
            "platform": {
                "type": "string",
                "enum": ["instagram", "twitter", "facebook", "tiktok"],
                "description": "Target platform for the caption",
            },
        },
        "required": ["caption", "hashtags"],
    },
}

GENERATE_BLOG_SECTION = {
    "name": "generate_blog_section",
    "description": "Generate a section of blog content about food.",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Section title",
            },
            "content": {
                "type": "string",
                "description": "Section content (markdown supported)",
            },
            "section_type": {
                "type": "string",
                "enum": ["intro", "highlight", "recipe", "stats", "conclusion"],
                "description": "Type of section",
            },
        },
        "required": ["title", "content"],
    },
}

CONTENT_GENERATION_TOOLS = [
    GENERATE_CAPTION,
    GENERATE_BLOG_SECTION,
]


# =============================================================================
# Safety Tools (for grounded queries)
# =============================================================================

REPORT_FOOD_SAFETY_ALERT = {
    "name": "report_food_safety_alert",
    "description": "Report a food safety alert or recall found during search.",
    "parameters": {
        "type": "object",
        "properties": {
            "alert_type": {
                "type": "string",
                "enum": ["recall", "contamination", "allergen_warning", "advisory"],
                "description": "Type of safety alert",
            },
            "affected_product": {
                "type": "string",
                "description": "Product or food affected",
            },
            "severity": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
                "description": "Severity of the alert",
            },
            "source": {
                "type": "string",
                "description": "Source of the alert (FDA, CDC, etc.)",
            },
            "action_required": {
                "type": "string",
                "description": "Recommended action for consumers",
            },
            "date_issued": {
                "type": "string",
                "description": "When the alert was issued",
            },
        },
        "required": ["alert_type", "affected_product", "severity"],
    },
}

SAFETY_TOOLS = [
    REPORT_FOOD_SAFETY_ALERT,
]


# =============================================================================
# Analytics Tools (for code execution results)
# =============================================================================

REPORT_NUTRITION_STATS = {
    "name": "report_nutrition_stats",
    "description": "Report calculated nutrition statistics.",
    "parameters": {
        "type": "object",
        "properties": {
            "period": {
                "type": "string",
                "description": "Time period analyzed",
            },
            "avg_daily_calories": {
                "type": "number",
                "description": "Average daily calorie intake",
            },
            "avg_daily_protein": {
                "type": "number",
                "description": "Average daily protein (g)",
            },
            "avg_daily_carbs": {
                "type": "number",
                "description": "Average daily carbs (g)",
            },
            "avg_daily_fat": {
                "type": "number",
                "description": "Average daily fat (g)",
            },
            "macro_ratio": {
                "type": "object",
                "properties": {
                    "protein_pct": {"type": "number"},
                    "carbs_pct": {"type": "number"},
                    "fat_pct": {"type": "number"},
                },
                "description": "Macronutrient ratio as percentages",
            },
            "trend": {
                "type": "string",
                "enum": ["increasing", "decreasing", "stable"],
                "description": "Overall calorie trend",
            },
        },
        "required": ["period", "avg_daily_calories"],
    },
}

ANALYTICS_TOOLS = [
    REPORT_NUTRITION_STATS,
]
