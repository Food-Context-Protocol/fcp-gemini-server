#!/usr/bin/env python3
"""
Photo → Social Post Pipeline

This example demonstrates a complete FCP workflow:
1. Analyze a food photo
2. Check food safety
3. Generate a social media post

Usage:
    python examples/workflows/photo_to_social.py <image_url>
"""

import asyncio
import json
import sys


async def photo_to_social_pipeline(image_url: str) -> dict:
    """
    Complete pipeline from food photo to shareable social post.

    Args:
        image_url: URL of the food image

    Returns:
        dict with analysis, safety check, and social post
    """
    from fcp.tools import analyze_meal, check_food_recalls

    print(f"Step 1: Analyzing image...")
    analysis = await analyze_meal(image_url)
    print(f"  → Detected: {analysis.get('dish_name', 'Unknown')}")

    dish_name = analysis.get("dish_name", "food")

    print(f"Step 2: Checking food safety...")
    safety = await check_food_recalls(food_name=dish_name)
    print(f"  → Safety status: {'Clear' if not safety.get('has_recall') else 'ALERT'}")

    print(f"Step 3: Generating social post...")
    # Generate a simple social post based on analysis
    cuisine = analysis.get("cuisine", "delicious")
    ingredients = analysis.get("ingredients", [])
    ingredient_names = [i.get("name", "") for i in ingredients[:3]]

    caption = f"Just had amazing {dish_name}! "
    if cuisine:
        caption += f"Love {cuisine} cuisine. "
    if ingredient_names:
        caption += f"Featuring {', '.join(ingredient_names)}. "

    hashtags = [f"#{cuisine.lower().replace(' ', '')}" if cuisine else "#food"]
    hashtags.extend(["#foodie", "#yummy", "#instafood"])

    post = {
        "caption": caption.strip(),
        "hashtags": hashtags,
        "platform_tips": {
            "instagram": "Add location tag for better reach",
            "twitter": "Keep under 280 characters",
        },
    }
    print(f"  → Caption: {post['caption']}")

    return {
        "analysis": analysis,
        "safety": safety,
        "social_post": post,
    }


async def main():
    if len(sys.argv) < 2:
        # Default demo image
        image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Sushi_bento.jpg/1280px-Sushi_bento.jpg"
        print(f"Using default image: {image_url}")
    else:
        image_url = sys.argv[1]

    result = await photo_to_social_pipeline(image_url)

    print("\n" + "=" * 50)
    print("Pipeline Complete!")
    print("=" * 50)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
