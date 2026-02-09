"""Test Constants.

Centralized constants for test data to avoid magic strings scattered
across test files. Import these constants instead of hard-coding values.

Usage:
    from tests.constants import TEST_USER_ID, TEST_AUTH_HEADER, TEST_USER  # sourcery skip: dont-import-test-modules

    def test_something():
        result = await some_function(TEST_USER.user_id)
"""

from fcp.auth.permissions import AuthenticatedUser, UserRole

# ============================================
# Authentication Constants
# ============================================

# Test user identifier
TEST_USER_ID = "test_user"

# Test authentication token
TEST_AUTH_TOKEN = "test_user"

# Authorization header for API tests
TEST_AUTH_HEADER = {"Authorization": f"Bearer {TEST_AUTH_TOKEN}"}

# Authenticated user object for mocking get_current_user
TEST_USER = AuthenticatedUser(user_id=TEST_USER_ID, role=UserRole.AUTHENTICATED)

# Demo user object for testing demo mode
DEMO_USER = AuthenticatedUser(user_id="demo_user_hackathon", role=UserRole.DEMO)


def make_test_user(user_id: str) -> AuthenticatedUser:
    """Create an authenticated test user with the given user_id.

    Use this when tests need a specific user_id for mocking.
    """
    return AuthenticatedUser(user_id=user_id, role=UserRole.AUTHENTICATED)


# ============================================
# Document/Entity IDs
# ============================================

# Test food log IDs
TEST_LOG_ID = "log-test-123"
TEST_LOG_ID_2 = "log-test-456"
TEST_LOG_ID_3 = "log-test-789"

# Test meal IDs
TEST_MEAL_ID = "meal-test-abc"


# ============================================
# URLs
# ============================================

# Base test URLs
TEST_IMAGE_URL = "https://test.example.com/food.jpg"
TEST_MENU_URL = "https://test.example.com/menu.jpg"
TEST_RECEIPT_URL = "https://test.example.com/receipt.jpg"
TEST_AUDIO_URL = "https://test.example.com/voice.mp3"
TEST_SOURCE_URL = "https://test.example.com/source"


# ============================================
# Location Data
# ============================================

TEST_LOCATION = "Seattle, WA"
TEST_LATITUDE = 47.6062
TEST_LONGITUDE = -122.3321
TEST_RESTAURANT_NAME = "Test Restaurant"


# ============================================
# Sample Food Data
# ============================================

TEST_DISH_NAME = "Tonkotsu Ramen"
TEST_VENUE = "Ramen House"
TEST_CUISINE = "Japanese"

TEST_INGREDIENTS = ["noodles", "pork belly", "soft-boiled egg", "green onions"]
TEST_ALLERGENS = ["gluten", "eggs", "soy"]

TEST_CALORIES = 650
TEST_PROTEIN = 35
TEST_CARBS = 75
TEST_FAT = 25


# ============================================
# Sample Log Entry
# ============================================

SAMPLE_LOG_ENTRY = {
    "id": TEST_LOG_ID,
    "dish_name": TEST_DISH_NAME,
    "venue": TEST_VENUE,
    "cuisine": TEST_CUISINE,
    "image_url": TEST_IMAGE_URL,
    "ingredients": TEST_INGREDIENTS,
    "calories": TEST_CALORIES,
    "created_at": "2024-01-15T12:00:00Z",
}


# ============================================
# Analysis Response Templates
# ============================================

SAMPLE_ANALYSIS_RESPONSE = {
    "dish_name": TEST_DISH_NAME,
    "cuisine": TEST_CUISINE,
    "ingredients": TEST_INGREDIENTS,
    "nutrition": {
        "calories": TEST_CALORIES,
        "protein_g": TEST_PROTEIN,
        "carbs_g": TEST_CARBS,
        "fat_g": TEST_FAT,
    },
    "dietary_tags": ["high-protein"],
    "allergens": TEST_ALLERGENS,
}


SAMPLE_SAFETY_RESPONSE = {
    "food_item": TEST_DISH_NAME,
    "recall_info": "No active recalls found for this item.",
    "has_active_recall": False,
    "sources": [
        {"title": "FDA Food Recalls", "uri": TEST_SOURCE_URL},
    ],
}


SAMPLE_PROFILE_RESPONSE = {
    "top_cuisines": [
        {"name": "Japanese", "percentage": 40},
        {"name": "Italian", "percentage": 25},
    ],
    "spice_preference": "medium",
    "dietary_patterns": ["regular meals", "weekend dining out"],
}
