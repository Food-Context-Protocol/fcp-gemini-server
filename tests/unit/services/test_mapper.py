import json
import sys
from datetime import datetime

from fcp.services.mapper import to_food_event, to_schema_org_recipe


def test_mapping():
    # Mock data resembling a Firestore document
    mock_log = {
        "dish_name": "Spicy Miso Ramen",
        "venue_name": "Ramen Nagi",
        "timestamp": datetime.now().isoformat(),
        "cuisine": "Japanese",
        "notes": "Best ramen in town!",
        "image_url": "https://example.com/ramen.jpg",
        "nutrition": {
            "calories": 850,
            "protein_g": 25,
            "carbs_g": 80,
            "fat_g": 40,
            "sodium_mg": 2200,
        },
        "ingredients": [
            {"name": "Miso broth", "amount": "500ml"},
            {"name": "Ramen noodles", "amount": "200g"},
            {"name": "Chashu pork", "amount": "2 slices"},
            "Green onions",
        ],
    }

    sys.stderr.write("--- Original Log ---\n")
    sys.stderr.write(json.dumps(mock_log, indent=2) + "\n")

    sys.stderr.write("\n--- Schema.org Recipe ---\n")
    recipe = to_schema_org_recipe(mock_log)
    sys.stderr.write(json.dumps(recipe, indent=2) + "\n")

    sys.stderr.write("\n--- Schema.org FoodEvent ---\n")
    event = to_food_event(mock_log)
    sys.stderr.write(json.dumps(event, indent=2) + "\n")

    # Basic assertions
    assert recipe["@type"] == "Recipe"
    assert recipe["name"] == "Spicy Miso Ramen"
    assert recipe["nutrition"]["calories"] == "850 calories"
    assert "Miso broth" in recipe["recipeIngredient"][0]

    assert event["@type"] == "FoodEvent"
    assert event["location"]["name"] == "Ramen Nagi"

    sys.stderr.write("\n✅ All mapping tests passed!\n")


def test_mapping_minimal_entry():
    """Test mapping with minimal entry - no image, no nutrition, no ingredients."""
    minimal_log = {
        "dish_name": "Simple Toast",
        "timestamp": "2024-01-15T12:00:00Z",
    }

    recipe = to_schema_org_recipe(minimal_log)

    assert recipe["@type"] == "Recipe"
    assert recipe["name"] == "Simple Toast"
    assert "image" not in recipe  # No image_url provided
    assert "nutrition" not in recipe  # No nutrition provided
    assert "recipeIngredient" not in recipe  # No ingredients provided


def test_mapping_without_image():
    """Test mapping with nutrition but no image."""
    log = {
        "dish_name": "Grilled Cheese",
        "nutrition": {"calories": 300, "protein_g": 12},
    }

    recipe = to_schema_org_recipe(log)

    assert recipe["@type"] == "Recipe"
    assert "image" not in recipe
    assert "nutrition" in recipe
    assert recipe["nutrition"]["calories"] == "300 calories"


def test_mapping_string_ingredients_only():
    """Test mapping with string ingredients only."""
    log = {
        "dish_name": "Fruit Salad",
        "ingredients": ["Apple", "Banana", "Orange", "Grapes"],
    }

    recipe = to_schema_org_recipe(log)

    assert recipe["@type"] == "Recipe"
    assert recipe["recipeIngredient"] == ["Apple", "Banana", "Orange", "Grapes"]


def test_mapping_ignores_unknown_ingredient_types():
    """Test mapping skips non-dict, non-string ingredients."""
    log = {
        "dish_name": "Odd Soup",
        "ingredients": [{"name": "Water", "amount": "1 cup"}, 42],
    }

    recipe = to_schema_org_recipe(log)

    assert recipe["recipeIngredient"] == ["1 cup Water"]


def test_mapping_no_timestamp():
    """Test mapping without timestamp."""
    log = {
        "dish_name": "Mystery Dish",
    }

    recipe = to_schema_org_recipe(log)

    assert recipe["@type"] == "Recipe"
    assert "datePublished" not in recipe


def test_food_event_no_venue():
    """Test FoodEvent without venue."""
    log = {
        "dish_name": "Home Cooking",
        "timestamp": "2024-01-15T18:00:00Z",
    }

    event = to_food_event(log)

    assert event["@type"] == "FoodEvent"
    assert "location" not in event


if __name__ == "__main__":
    test_mapping()
