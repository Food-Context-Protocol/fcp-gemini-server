"""Pytest fixtures for FCP server tests.

Note: Test constants (user IDs, URLs, sample data) are centralized in
tests/constants.py. Import from there instead of hard-coding values.
"""

import logging
import os

os.environ["ENVIRONMENT"] = "test"
os.environ["DEMO_MODE"] = "false"

import asyncio
import warnings
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from freezegun import freeze_time
from hypothesis import Verbosity, settings

from tests.constants import (  # sourcery skip: dont-import-test-modules
    TEST_AUTH_TOKEN,
    TEST_SOURCE_URL,
)

logger = logging.getLogger("tests.conftest")

# Set test environment defaults
os.environ.setdefault("GEMINI_API_KEY", "AIzaTest1234567890123456789012345678901")
os.environ.setdefault("FCP_TOKEN", TEST_AUTH_TOKEN)
os.environ.setdefault("ENABLE_METRICS", "false")
os.environ.setdefault("ENABLE_TELEMETRY", "false")

# =============================================================================
# Hypothesis Configuration
# =============================================================================
# Register profiles for different environments
# Usage: HYPOTHESIS_PROFILE=ci pytest ...

settings.register_profile(
    "ci",
    max_examples=500,
    deadline=None,
    suppress_health_check=[],
)

settings.register_profile(
    "dev",
    max_examples=100,
    deadline=5000,
)

settings.register_profile(
    "quick",
    max_examples=10,
    deadline=1000,
)

settings.register_profile(
    "debug",
    max_examples=10,
    verbosity=Verbosity.verbose,
    deadline=None,
)

# Load profile from environment variable, default to "dev"
_hypothesis_profile = os.environ.get("HYPOTHESIS_PROFILE", "dev")
settings.load_profile(_hypothesis_profile)


# =============================================================================
# Test Size Classification
# =============================================================================
def pytest_collection_modifyitems(config, items):
    """Auto-assign size markers based on test paths and enforce size tags."""
    size_markers = {"small", "medium", "large"}
    missing_size = []

    for item in items:
        path_str = str(item.fspath)
        if "/tests/integration/" in path_str:
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.large)
        elif "/tests/unit/cli/property_based/" in path_str:
            item.add_marker(pytest.mark.property)
            item.add_marker(pytest.mark.medium)
        elif "/tests/unit/" in path_str:
            item.add_marker(pytest.mark.small)
        elif "/tests/" in path_str:
            item.add_marker(pytest.mark.small)

        if not any(item.get_closest_marker(name) for name in size_markers):
            missing_size.append(item.nodeid)

    if missing_size:
        preview = "\n".join(missing_size[:10])
        raise pytest.UsageError(
            "All tests must be marked with a size marker (small/medium/large).\n"
            f"Missing size marker for {len(missing_size)} tests. Examples:\n{preview}"
        )


# =============================================================================
# Deterministic Time Helpers
# =============================================================================
@pytest.fixture
def frozen_time():
    """Freeze time for tests that need deterministic now()."""
    with freeze_time("2026-01-01T00:00:00Z"):
        yield


@pytest.fixture(autouse=True)
def block_httpx_network(respx_mock, request):
    """Block any unmocked HTTPX requests in unit tests.

    Integration tests are allowed to hit real services.
    """
    is_integration = "tests/integration" in str(request.fspath) or "integration" in request.keywords
    # respx uses a private flag for this; set it directly.
    respx_mock._assert_all_mocked = not is_integration
    yield respx_mock


@pytest.fixture
def sample_food_logs():
    """Sample food log data for testing."""
    now = datetime.now()
    return [
        {
            "id": "log1",
            "dish_name": "Tonkotsu Ramen",
            "venue_name": "Ichiran",
            "cuisine": "Japanese",
            "notes": "Amazing rich broth",
            "ingredients": ["pork", "noodles", "egg", "green onion"],
            "spice_level": 2,
            "created_at": (now - timedelta(days=1)).isoformat(),
            "nutrition": {"calories": 800, "protein_g": 35},
        },
        {
            "id": "log2",
            "dish_name": "Margherita Pizza",
            "venue_name": "Pizzeria Mozza",
            "cuisine": "Italian",
            "notes": "Perfect crust",
            "ingredients": ["tomato", "mozzarella", "basil"],
            "spice_level": 1,
            "created_at": (now - timedelta(days=2)).isoformat(),
            "nutrition": {"calories": 600, "protein_g": 20},
        },
        {
            "id": "log3",
            "dish_name": "Spicy Thai Basil Chicken",
            "venue_name": "Thai Palace",
            "cuisine": "Thai",
            "notes": "Very spicy, loved it",
            "ingredients": ["chicken", "thai basil", "chili", "garlic"],
            "spice_level": 5,
            "created_at": (now - timedelta(days=3)).isoformat(),
            "nutrition": {"calories": 450, "protein_g": 40},
        },
        {
            "id": "log4",
            "dish_name": "Carbonara",
            "venue_name": "Osteria Mozza",
            "cuisine": "Italian",
            "notes": "Best pasta ever",
            "ingredients": ["pasta", "egg", "pecorino", "guanciale"],
            "spice_level": 1,
            "created_at": (now - timedelta(days=7)).isoformat(),
            "nutrition": {"calories": 700, "protein_g": 25},
        },
        {
            "id": "log5",
            "dish_name": "Tacos al Pastor",
            "venue_name": "Street Vendor",
            "cuisine": "Mexican",
            "notes": "Street food heaven",
            "ingredients": ["pork", "pineapple", "onion", "cilantro"],
            "spice_level": 3,
            "created_at": (now - timedelta(days=10)).isoformat(),
            "nutrition": {"calories": 350, "protein_g": 20},
        },
    ]


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response."""
    return {
        "dish_name": "Tonkotsu Ramen",
        "cuisine": "Japanese",
        "ingredients": ["pork broth", "chashu", "noodles", "soft-boiled egg"],
        "nutrition": {
            "calories": 800,
            "protein_g": 35,
            "carbs_g": 80,
            "fat_g": 30,
        },
        "dietary_tags": [],
        "allergens": ["gluten", "egg", "soy"],
        "spice_level": 2,
        "cooking_method": "simmered",
    }


@pytest.fixture
def mock_gemini():
    """Mock Gemini client."""
    with patch("fcp.services.gemini.genai") as mock_genai:
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        async def mock_generate(*args, **kwargs):
            response = MagicMock()
            response.text = '{"dish_name": "Test Dish", "cuisine": "Test"}'
            return response

        mock_model.generate_content_async = mock_generate
        yield mock_model


@pytest.fixture
def mock_firestore_client(sample_food_logs):
    """Mock FirestoreClient with sample data."""
    mock = AsyncMock()
    mock.get_user_logs = AsyncMock(return_value=sample_food_logs)
    mock.get_log = AsyncMock(return_value=sample_food_logs[0])
    mock.create_log = AsyncMock(return_value="new_log_id")
    mock.update_log = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_gemini_client(mock_gemini_response):
    """Mock GeminiClient."""
    mock = AsyncMock()
    mock.generate_json = AsyncMock(return_value=mock_gemini_response)
    mock.generate_content = AsyncMock(return_value='{"test": "response"}')
    return mock


@pytest.fixture
def mock_gemini_v2():
    """Mock Gemini client with all v2 features."""
    mock = AsyncMock()

    # Function calling
    mock.generate_with_tools = AsyncMock(
        return_value={
            "text": "Analysis complete",
            "function_calls": [
                {"name": "identify_dish", "args": {"dish_name": "Ramen", "cuisine": "Japanese"}},
            ],
        }
    )

    # Google Search grounding
    mock.generate_with_grounding = AsyncMock(
        return_value={
            "text": "Real-time information",
            "sources": [{"title": "Source", "url": TEST_SOURCE_URL}],
        }
    )

    # Extended thinking
    mock.generate_with_thinking = AsyncMock(return_value='{"analysis": "deep analysis"}')

    # Code execution
    mock.generate_with_code_execution = AsyncMock(
        return_value={
            "text": "Calculated",
            "code": "result = 1 + 1",
            "result": {"value": 2},
        }
    )

    # Combined features
    mock.generate_with_all_tools = AsyncMock(
        return_value={
            "text": "Combined result",
            "function_calls": [],
            "sources": [],
        }
    )

    # JSON with thinking
    mock.generate_json_with_thinking = AsyncMock(
        return_value={
            "key": "value",
        }
    )

    # Large context
    mock.generate_json_with_large_context = AsyncMock(
        return_value={
            "analysis": "lifetime analysis",
        }
    )

    # Agentic Vision (code execution + image)
    mock.generate_json_with_agentic_vision = AsyncMock(
        return_value={
            "analysis": {
                "dish_name": "Sushi Platter",
                "cuisine": "Japanese",
                "ingredients": ["rice", "salmon"],
                "portion_analysis": {"item_count": 8},
            },
            "code": "# Counted 8 pieces",
            "execution_result": "8",
        }
    )

    return mock


@pytest.fixture
def sample_taste_profile():
    """Sample taste profile for agent tests."""
    return {
        "top_cuisines": ["Japanese", "Italian", "Mexican"],
        "spice_tolerance": "medium",
        "dietary_patterns": ["pescatarian-friendly"],
        "favorite_ingredients": ["garlic", "ginger", "lime"],
        "avoids": ["shellfish"],
        "recent_favorites": ["ramen", "pasta carbonara", "tacos"],
    }


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter state before each test.

    This prevents rate limit errors when running multiple tests
    that hit the same endpoints.
    """
    # Import here to avoid circular imports
    try:
        from fcp.security.rate_limit import limiter

        # Reset limiter state - slowapi stores state in limiter._storage
        if hasattr(limiter, "_storage") and limiter._storage:
            limiter._storage.reset()
    except (ImportError, AttributeError):
        pass
    yield


@pytest.fixture(autouse=True)
def reset_gemini_http_client():
    """Reset the shared Gemini HTTP client before and after each test.

    This ensures test isolation when mocking httpx.AsyncClient,
    since GeminiClient uses a shared connection pool.
    """
    try:
        from fcp.services.gemini import GeminiClient

        GeminiClient.reset_http_client()
    except (ImportError, AttributeError):
        pass
    yield
    try:
        from fcp.services.gemini import GeminiClient

        GeminiClient.reset_http_client()
    except (ImportError, AttributeError):
        pass


@pytest.fixture
async def reset_database_connections():
    """Reset database connections between tests to avoid state leakage.

    Apply this fixture explicitly to tests that need Firestore cleanup.
    Removed autouse=True to avoid async fixture issues with sync tests in pytest 9.
    """
    yield
    # Clean up after test
    try:
        from fcp.services.firestore import _firestore_client

        if _firestore_client is not None and hasattr(_firestore_client, "db"):
            if hasattr(_firestore_client.db, "_db") and _firestore_client.db._db is not None:
                await _firestore_client.db.close()
    except (ImportError, AttributeError):
        pass


@pytest.fixture
def event_loop():
    """Create and close a fresh event loop per test to avoid leaks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    if not loop.is_closed():
        loop.close()
    asyncio.set_event_loop(None)


@pytest.fixture(autouse=True)
def close_event_loop_after_test():
    """Close any leftover event loop to prevent ResourceWarnings."""
    yield
    policy = asyncio.get_event_loop_policy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            loop = policy.get_event_loop()
        except RuntimeError:
            return
    if loop is not None and not loop.is_closed():
        loop.close()
    policy.set_event_loop(None)


@pytest.fixture(autouse=True)
def reset_circuit_breakers():
    """Reset all circuit breakers before and after each test.

    This ensures test isolation for circuit breaker state.
    """
    try:
        from fcp.utils.circuit_breaker import reset_all_circuit_breakers

        reset_all_circuit_breakers()
    except (ImportError, AttributeError):
        pass
    yield
    try:
        from fcp.utils.circuit_breaker import reset_all_circuit_breakers

        reset_all_circuit_breakers()
    except (ImportError, AttributeError):
        pass


@pytest.fixture(autouse=True)
def shutdown_observability():
    """Shutdown logfire between tests to avoid background threads."""
    yield
    try:
        from fcp.services.logfire_service import shutdown_logfire

        shutdown_logfire()
    except (ImportError, AttributeError):
        pass
