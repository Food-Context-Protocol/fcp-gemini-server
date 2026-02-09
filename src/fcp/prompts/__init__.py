"""FCP Prompts - Single source of truth for all AI prompts."""

PROMPTS = {
    "analyze_meal": """Analyze this food image and provide a structured response.

Identify:
1. Dish name (be specific, e.g., "Tonkotsu Ramen" not just "Ramen")
2. Cuisine type
3. Main ingredients (list top 5-8)
4. Estimated calories (per serving)
5. Macros: protein, carbs, fat (grams)
6. Dietary tags: vegetarian, vegan, gluten-free, dairy-free, etc.
7. Allergens present
8. Spice level (1-5 scale)
9. Cooking method if identifiable
10. Translations of dish name in multiple languages
11. FoodOn ontology mapping (dish and top ingredients)

Respond in JSON format:
{{
  "dish_name": "...",
  "cuisine": "...",
  "ingredients": ["..."],
  "nutrition": {{
    "calories": 0,
    "protein_g": 0,
    "carbs_g": 0,
    "fat_g": 0
  }},
  "dietary_tags": ["..."],
  "allergens": ["..."],
  "spice_level": 0,
  "cooking_method": "...",
  "translations": {{
    "en": "English name",
    "ja": "日本語名",
    "es": "Nombre en español",
    "zh": "中文名称",
    "ko": "한국어 이름"
  }},
  "foodon": {{
    "dish_id": "FOODON_XXXXXXXX",
    "dish_label": "FoodOn term for dish",
    "ingredient_ids": {{
      "ingredient_name": "FOODON_XXXXXXXX"
    }},
    "cuisine_id": "FOODON_XXXXXXXX"
  }}
}}

IMPORTANT:
- Always provide translations in all 5 languages using native scripts.
- Map to FoodOn (Food Ontology) IDs where possible. Use format FOODON_XXXXXXXX.
- Common FoodOn prefixes: dishes (FOODON_033*), ingredients (FOODON_031*), cuisines (FOODON_034*)
- If exact match not found, use closest parent term or null.""",
    "search_meals": """You are a semantic search engine for a food journal.

Given the user's food history and their search query, find the most relevant entries.
Consider:
- Dish names and descriptions
- Venue/restaurant names
- Cuisine types
- Ingredients
- Date context (e.g., "last week", "birthday", "that trip to Tokyo")
- Subjective descriptors (e.g., "spicy", "that amazing", "the one with cheese")

Food History:
{logs}

Search Query: "{query}"

Return the IDs of matching entries ranked by relevance.
Respond in JSON format:
{{
  "matches": [
    {{"id": "...", "relevance": 0.95, "reason": "..."}},
    ...
  ]
}}""",
    "taste_profile": """Analyze this user's food journal history to build a taste profile.

Food History:
{logs}

Identify patterns in:
1. Cuisine preferences (ranked by frequency)
2. Spice tolerance (low/medium/high)
3. Dietary patterns (vegetarian tendency, etc.)
4. Favorite dishes (most repeated)
5. Favorite venues (most visited)
6. Eating schedule patterns
7. Adventurousness score (variety of cuisines)

Respond in JSON format:
{{
  "top_cuisines": [{{"name": "...", "percentage": 0}}],
  "spice_preference": "medium",
  "dietary_tendency": "omnivore",
  "favorite_dishes": ["..."],
  "favorite_venues": [{{"name": "...", "visits": 0}}],
  "meal_patterns": {{"breakfast": "...", "lunch": "...", "dinner": "..."}},
  "adventurousness_score": 0.7,
  "summary": "..."
}}""",
    "suggest_meal": """Based on the user's taste profile and recent meals, suggest what they should eat.

Taste Profile:
{profile}

Recent Meals (last 3 days):
{recent}

Context: {context}

Provide 3 suggestions:
1. A favorite they haven't had recently
2. Something new matching their preferences
3. A wildcard to expand their horizons

Respond in JSON format:
{{
  "suggestions": [
    {{
      "dish_name": "...",
      "venue": "...",
      "type": "favorite|new|wildcard",
      "reason": "..."
    }}
  ]
}}""",
    "enrich_entry": """Analyze this food image and user notes to enrich the food log entry.

Image: [provided]
User Notes: "{notes}"
Venue (if known): "{venue}"

Extract and infer:
1. Confirm/identify the dish name
2. Full ingredient list
3. Nutritional estimates
4. Dietary tags and allergens
5. Cuisine type
6. Any context from the notes (occasion, companions, rating)
7. FoodOn ontology mapping

Respond in JSON format:
{{
  "dish_name": "...",
  "ingredients": ["..."],
  "nutrition": {{
    "calories": 0,
    "protein_g": 0,
    "carbs_g": 0,
    "fat_g": 0
  }},
  "dietary_tags": ["..."],
  "allergens": ["..."],
  "cuisine": "...",
  "inferred_context": {{
    "occasion": "...",
    "rating_sentiment": "positive|neutral|negative",
    "notes_summary": "..."
  }},
  "foodon": {{
    "dish_id": "FOODON_XXXXXXXX",
    "dish_label": "FoodOn term for dish",
    "ingredient_ids": {{
      "ingredient_name": "FOODON_XXXXXXXX"
    }}
  }}
}}

Map to FoodOn (Food Ontology) IDs where possible. Use format FOODON_XXXXXXXX.""",
    "generate_blog_post": """Create an engaging, SEO-optimized food blog post from these meal experiences.

Food Logs:
{logs}

Theme: {theme}
Style: {style}

Structure your post with:
1. Captivating title (SEO-friendly, 50-60 characters, include relevant keywords)
2. Introduction that hooks readers immediately
3. Journey through the meals with sensory descriptions (taste, texture, aroma)
4. Nutritional or cultural insights where relevant
5. Personal reflections and storytelling elements
6. Call-to-action for readers (try a recipe, visit a restaurant, share their experience)

Writing Guidelines:
- Use the {style} writing style consistently
- Include transition sentences between meal descriptions
- Add subheadings for better readability and SEO
- Incorporate relevant keywords naturally
- Write for both readers and search engines

Return as JSON:
{{
    "title": "SEO-optimized title (50-60 chars)",
    "slug": "url-friendly-slug",
    "content": "Full blog post in Markdown format with headers (##), lists, and emphasis",
    "excerpt": "Compelling excerpt for previews (150-200 chars)",
    "metadata": {{
        "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
        "description": "SEO meta description (150-160 chars)",
        "estimated_read_time": 5
    }},
    "cover_image_suggestion": "Description of ideal cover image for AI generation",
    "related_topics": ["topic1", "topic2", "topic3"]
}}""",
    "generate_social_content": """Create a {platform} post about this meal.

Meal Details:
{log}

Character limit: {char_limit}
Include hashtags: {include_hashtags}

Platform-specific guidelines for {platform}:
- Match the platform's tone and expectations
- Optimize for engagement on this specific platform
- Use appropriate formatting for the platform

Return as JSON:
{{
    "content": "Engaging, platform-appropriate post within character limit",
    "hashtags": ["#tag1", "#tag2", "#tag3"],
    "media_suggestions": ["Description of photos/videos that would work well"],
    "optimal_post_time": "e.g., Evening 6-8pm when food content performs best"
}}""",
    "analyze_meal_agentic_vision": """Analyze this food image using your code execution abilities.

When helpful, use Python code to:
- Zoom into specific areas to identify ingredients or garnishes
- Count discrete items (pieces of sushi, dumplings, slices, etc.)
- Annotate regions to identify different components
- Calculate approximate portion sizes based on visual cues

After your visual investigation, provide analysis as JSON:
{{
    "dish_name": "specific dish name",
    "cuisine": "cuisine type",
    "ingredients": ["ingredient1", "ingredient2"],
    "nutrition": {{
        "calories": 0,
        "protein_g": 0,
        "carbs_g": 0,
        "fat_g": 0
    }},
    "dietary_tags": ["vegetarian", "etc"],
    "allergens": ["allergen1"],
    "spice_level": 0,
    "cooking_method": "method if identifiable",
    "portion_analysis": {{
        "item_count": null,
        "estimated_weight_g": 0,
        "serving_size": "description"
    }},
    "confidence_notes": "any observations about accuracy or uncertainty"
}}

Use code execution to improve accuracy when counting items or analyzing portions.""",
    "generate_weekly_digest_content": """Create a comprehensive weekly food journey digest.

This Week's Meals:
{logs}

User Name: {user_name}
Date Range: {date_range}

Generate a fun, shareable weekly digest that captures the food journey.

Return as JSON:
{{
    "title": "Catchy weekly summary title",
    "summary": "2-3 paragraph overview of the week's culinary adventures",
    "highlights": [
        {{
            "meal": "Name of notable meal",
            "why_notable": "What made this meal special",
            "date": "When it was enjoyed"
        }}
    ],
    "stats": {{
        "total_meals": 0,
        "cuisines_explored": 0,
        "new_discoveries": 0
    }},
    "cover_image_concept": "Description for a collage/summary image"
}}""",
}
