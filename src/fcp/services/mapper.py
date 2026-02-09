"""Schema.org Mapper for FoodLog FCP.

This module maps internal FCP food log entries to standard Schema.org
structured data (JSON-LD). This ensures interoperability with the
broader semantic web and search engines.

References:
- https://schema.org/Recipe
- https://schema.org/FoodEvent
- https://foodon.org/
"""

from typing import Any


def to_schema_org_recipe(log_entry: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a FoodLog entry to a Schema.org Recipe/Dish object.

    Args:
        log_entry: The internal FCP log entry dictionary.

    Returns:
        Dict representing a Schema.org Recipe.
    """
    dish_name = log_entry.get("dish_name", "Unknown Dish")
    image_url = log_entry.get("image_url")
    # Handle both flattened and nested nutrition
    nutrition = log_entry.get("nutrition", {})
    ingredients = log_entry.get("ingredients", [])

    schema = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": dish_name,
        "datePublished": log_entry.get("timestamp", "").split("T")[0] if log_entry.get("timestamp") else None,
        "description": log_entry.get("notes") or f"A delicious {dish_name} logged in FoodLog.",
        "keywords": log_entry.get("cuisine"),
    }

    if image_url:
        schema["image"] = [image_url]

    # Map Nutrition
    if nutrition:
        nutri_map = {
            "@type": "NutritionInformation",
            "calories": f"{nutrition.get('calories')} calories" if nutrition.get("calories") else None,
            "carbohydrateContent": f"{nutrition.get('carbs_g')} g" if nutrition.get("carbs_g") else None,
            "proteinContent": f"{nutrition.get('protein_g')} g" if nutrition.get("protein_g") else None,
            "fatContent": f"{nutrition.get('fat_g')} g" if nutrition.get("fat_g") else None,
            "fiberContent": f"{nutrition.get('fiber_g')} g" if nutrition.get("fiber_g") else None,
            "sugarContent": f"{nutrition.get('sugar_g')} g" if nutrition.get("sugar_g") else None,
            "sodiumContent": f"{nutrition.get('sodium_mg')} mg" if nutrition.get("sodium_mg") else None,
        }
        # Remove None values
        schema["nutrition"] = {k: v for k, v in nutri_map.items() if v}

    # Map Ingredients
    if ingredients:
        # Schema.org expects a list of strings for recipeIngredient
        # If ingredients are dicts with 'name' and 'amount', format them
        formatted_ingredients = []
        for ing in ingredients:
            if isinstance(ing, dict):
                amount = ing.get("amount", "")
                name = ing.get("name", "")
                formatted_ingredients.append(f"{amount} {name}".strip())
            elif isinstance(ing, str):
                formatted_ingredients.append(ing)

        schema["recipeIngredient"] = formatted_ingredients

    # Add FoodOn reference if available (placeholder for future deep integration)
    # schema["sameAs"] = "http://purl.obolibrary.org/obo/FOODON_..."

    return {k: v for k, v in schema.items() if v is not None}


def to_food_event(log_entry: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a FoodLog entry to a Schema.org FoodEvent.

    Useful for representing the act of eating at a specific time/place.
    """
    venue = log_entry.get("venue_name")
    timestamp = log_entry.get("timestamp")

    schema = {
        "@context": "https://schema.org",
        "@type": "FoodEvent",
        "name": f"Meal: {log_entry.get('dish_name', 'Food')}",
        "startDate": timestamp,
        "location": {"@type": "Place", "name": venue} if venue else None,
        "workPerformed": to_schema_org_recipe(log_entry),
    }

    return {k: v for k, v in schema.items() if v is not None}
