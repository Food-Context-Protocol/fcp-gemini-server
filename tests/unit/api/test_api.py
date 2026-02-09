"""Tests for FCP HTTP API."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from fcp.api import app
from fcp.auth import get_current_user, require_write_access
from tests.constants import TEST_AUTH_HEADER, TEST_USER  # sourcery skip: dont-import-test-modules

# Auth header for all requests - use centralized constant
AUTH_HEADER = TEST_AUTH_HEADER


def _mock_get_current_user():
    """Mock get_current_user to return TEST_USER."""
    return TEST_USER


def _mock_require_write_access():
    """Mock require_write_access to return TEST_USER."""
    return TEST_USER


def _override_gemini(mock_gemini):
    """Override Gemini dependency for the app and return the override key."""
    from fcp.services.gemini import get_gemini

    app.dependency_overrides[get_gemini] = lambda: mock_gemini
    return get_gemini


@pytest.fixture(autouse=True)
def mock_auth_dependencies():
    """Override auth dependencies for all tests."""
    app.dependency_overrides[get_current_user] = _mock_get_current_user
    app.dependency_overrides[require_write_access] = _mock_require_write_access
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth():
    """Create test client without auth overrides (for demo mode tests)."""
    app.dependency_overrides.clear()
    yield TestClient(app)
    # Restore auth overrides
    app.dependency_overrides[get_current_user] = _mock_get_current_user
    app.dependency_overrides[require_write_access] = _mock_require_write_access


client = TestClient(app)


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_root_returns_ok(self):
        """Test health check returns ok status."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["service"] == "FoodLog FCP API"


class TestMcpToolsList:
    """Tests for /mcp/v1/tools/list endpoint."""

    def test_list_mcp_tools(self):
        """api.py line 416: GET /mcp/v1/tools/list returns tool list."""
        response = client.get("/mcp/v1/tools/list")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data


class TestAuthentication:
    """Tests for authentication."""

    def test_missing_auth_header_allows_demo_read(self, client_no_auth):
        """Test that missing auth header allows read access for demo user."""
        with patch("fcp.routes.meals.get_meals") as mock_get:
            mock_get.return_value = []
            response = client_no_auth.get("/meals")
            # Demo users can read
            assert response.status_code == 200

    def test_missing_auth_header_blocks_write(self, client_no_auth):
        """Test that missing auth header blocks write access for demo user."""
        response = client_no_auth.post("/meals", json={"dish_name": "Test"})
        # Demo users get 403 for write operations
        assert response.status_code == 403
        data = response.json()
        # Error format: {"error": {"code": "FORBIDDEN", "message": "..."}}
        assert "error" in data
        assert data["error"]["code"] == "FORBIDDEN"
        assert "demo" in data["error"]["message"].lower() or "read-only" in data["error"]["message"].lower()

    def test_valid_auth_header(self):
        """Test that valid auth header works."""
        with patch("fcp.routes.meals.get_meals") as mock_get:
            mock_get.return_value = []
            response = client.get("/meals", headers=AUTH_HEADER)
            assert response.status_code == 200


# NOTE: TestMealsEndpoints has been moved to test_routes_meals.py
# NOTE: TestSearchEndpoint has been moved to test_routes_search.py
# as part of the api.py route module extraction.


class TestEnrichEndpoint:
    """Tests for /enrich endpoint."""

    def test_enrich_success(self):
        """Test successful enrichment."""
        with patch("fcp.routes.misc.enrich_entry", new_callable=AsyncMock) as mock_enrich:
            mock_enrich.return_value = {
                "success": True,
                "log_id": "log1",
                "enrichment": {"dish_name": "Ramen"},
            }
            response = client.post(
                "/enrich",
                json={"log_id": "log1"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_enrich_failure(self):
        """Test enrichment failure."""
        with patch("fcp.routes.misc.enrich_entry", new_callable=AsyncMock) as mock_enrich:
            mock_enrich.return_value = {"success": False, "error": "No image"}
            response = client.post(
                "/enrich",
                json={"log_id": "log1"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 400


class TestProfileEndpoint:
    """Tests for /profile endpoint."""

    def test_get_profile(self):
        """Test getting taste profile."""
        with patch("fcp.routes.profile.get_taste_profile", new_callable=AsyncMock) as mock_profile:
            mock_profile.return_value = {
                "total_meals": 50,
                "top_cuisines": [{"name": "Italian", "percentage": 30}],
            }
            response = client.get("/profile", headers=AUTH_HEADER)

            assert response.status_code == 200
            assert "profile" in response.json()

    def test_get_profile_with_period(self):
        """Test profile with period parameter."""
        with patch("fcp.routes.profile.get_taste_profile", new_callable=AsyncMock) as mock_profile:
            mock_profile.return_value = {"total_meals": 10, "period": "week"}
            response = client.get("/profile?period=week", headers=AUTH_HEADER)

            assert response.status_code == 200
            mock_profile.assert_called_once()
            # period is passed as positional arg: get_taste_profile(user_id, period)
            assert mock_profile.call_args[0][1] == "week"


class TestSuggestEndpoint:
    """Tests for /suggest endpoint."""

    def test_get_suggestions(self):
        """Test getting meal suggestions."""
        with patch("fcp.routes.misc.suggest_meal", new_callable=AsyncMock) as mock_suggest:
            mock_suggest.return_value = [
                {"dish_name": "Carbonara", "type": "favorite", "reason": "You loved it"},
            ]
            response = client.post(
                "/suggest",
                json={"context": "dinner"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert "suggestions" in data
            assert data["context"] == "dinner"


class TestVoiceCorrectionEndpoint:
    """Tests for /audio/voice-correction endpoint."""

    def test_voice_correction_success(self):
        """Test successful voice correction extraction."""
        with patch("fcp.routes.misc.extract_voice_correction", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {
                "field": "dish_name",
                "new_value": "Tonkotsu Ramen",
                "confidence": 0.95,
            }
            response = client.post(
                "/audio/voice-correction",
                json={"voice_input": "Actually that was tonkotsu ramen not miso"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["field"] == "dish_name"
            assert data["new_value"] == "Tonkotsu Ramen"
            assert data["confidence"] == 0.95

    def test_voice_correction_unclear_input(self):
        """Test voice correction with unclear input."""
        with patch("fcp.routes.misc.extract_voice_correction", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {
                "field": None,
                "new_value": None,
                "confidence": 0,
            }
            response = client.post(
                "/audio/voice-correction",
                json={"voice_input": "hello there"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["field"] is None
            assert data["confidence"] == 0

    def test_voice_correction_empty_input(self):
        """Test voice correction rejects empty input."""
        response = client.post(
            "/audio/voice-correction",
            json={"voice_input": ""},
            headers=AUTH_HEADER,
        )
        assert response.status_code == 422  # Validation error

    def test_voice_correction_overly_long_input(self):
        """Test voice correction rejects input exceeding max_length."""
        long_input = "a" * 1001  # exceeds max_length=1000
        response = client.post(
            "/audio/voice-correction",
            json={"voice_input": long_input},
            headers=AUTH_HEADER,
        )
        assert response.status_code == 422  # Validation error

    def test_voice_correction_allows_demo_users(self, client_no_auth):
        """Test voice correction allows demo users (read-only endpoint)."""
        with patch("fcp.routes.misc.extract_voice_correction", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {
                "field": "dish_name",
                "new_value": "Corrected Dish",
                "confidence": 0.9,
            }
            response = client_no_auth.post(
                "/audio/voice-correction",
                json={"voice_input": "correct the dish name"},
            )
            # Voice correction is a read-only endpoint (uses get_current_user)
            assert response.status_code == 200

    def test_voice_correction_error_flag(self):
        """Test voice correction returns error flag on service failure."""
        with patch("fcp.routes.misc.extract_voice_correction", new_callable=AsyncMock) as mock_extract:
            # Simulate an error from the extraction service
            mock_extract.return_value = {
                "field": None,
                "new_value": None,
                "confidence": 0,
                "error": True,
            }
            response = client.post(
                "/audio/voice-correction",
                json={"voice_input": "correct something"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["error"] is True


class TestAnalyzeEndpoint:
    """Tests for /analyze endpoint."""

    def test_analyze_image(self, mock_gemini_response):
        """Test image analysis without creating log."""
        with patch("fcp.routes.analyze.analyze_meal", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_gemini_response
            # Use an allowed domain (firebasestorage.googleapis.com is in the whitelist)
            response = client.post(
                "/analyze",
                json={"image_url": "https://firebasestorage.googleapis.com/food.jpg"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            assert "analysis" in response.json()
            assert response.json()["analysis"]["dish_name"] == "Tonkotsu Ramen"

    def test_analyze_with_agentic_vision(self):
        """Test image analysis with Agentic Vision (code execution)."""
        with patch("fcp.routes.analyze.analyze_meal_with_agentic_vision", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = {
                "dish_name": "Sushi Platter",
                "cuisine": "Japanese",
                "ingredients": ["rice", "salmon", "tuna"],
                "nutrition": {"calories": 450},
                "portion_analysis": {"item_count": 8},
                "_agentic_vision": {
                    "code_executed": "# Counted 8 pieces",
                    "execution_result": "8",
                },
            }
            response = client.post(
                "/analyze/agentic-vision",
                json={"image_url": "https://firebasestorage.googleapis.com/sushi.jpg"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["method"] == "agentic_vision"
            assert data["analysis"]["dish_name"] == "Sushi Platter"
            assert data["analysis"]["portion_analysis"]["item_count"] == 8
            assert data["analysis"]["_agentic_vision"]["code_executed"] is not None

    def test_analyze_with_agentic_vision_no_code(self):
        """Test Agentic Vision when model doesn't execute code."""
        with patch("fcp.routes.analyze.analyze_meal_with_agentic_vision", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = {
                "dish_name": "Caesar Salad",
                "cuisine": "American",
                "ingredients": ["romaine", "parmesan"],
                "nutrition": {},
                "_agentic_vision": {
                    "code_executed": None,
                    "execution_result": None,
                },
            }
            response = client.post(
                "/analyze/agentic-vision",
                json={"image_url": "https://firebasestorage.googleapis.com/salad.jpg"},
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["analysis"]["dish_name"] == "Caesar Salad"
            assert data["analysis"]["_agentic_vision"]["code_executed"] is None

    def test_analyze_with_agentic_vision_missing_image_url(self):
        """Test validation error when image_url is missing."""
        response = client.post(
            "/analyze/agentic-vision",
            json={},
            headers=AUTH_HEADER,
        )
        assert response.status_code == 422
        data = response.json()
        assert "error" in data or "detail" in data

    def test_analyze_with_agentic_vision_requires_auth(self, client_no_auth):
        """Test that auth is required for agentic vision endpoint (demo gets 403)."""
        response = client_no_auth.post(
            "/analyze/agentic-vision",
            json={"image_url": "https://firebasestorage.googleapis.com/test.jpg"},
        )
        # Write endpoints return 403 for demo users
        assert response.status_code == 403


class TestLifetimeProfileEndpoint:
    """Tests for /profile/lifetime endpoint with pagination."""

    def test_lifetime_profile_default_params(self, sample_food_logs):
        """Test lifetime profile with default parameters."""
        with (
            patch("fcp.routes.profile.firestore_client") as mock_fs,
            patch("fcp.routes.profile._lifetime_cache", {}),  # Clear cache
        ):
            mock_fs.get_user_logs_paginated = AsyncMock(return_value=(sample_food_logs, len(sample_food_logs)))
            mock_fs.get_all_user_logs = AsyncMock(return_value=sample_food_logs)
            mock_gem = AsyncMock()
            mock_gem.generate_json_with_large_context = AsyncMock(return_value={"analysis": "test analysis"})
            override_key = _override_gemini(mock_gem)

            response = client.get("/profile/lifetime", headers=AUTH_HEADER)
            app.dependency_overrides.pop(override_key, None)

            assert response.status_code == 200
            data = response.json()
            assert "lifetime_analysis" in data
            assert "pagination" in data
            assert data["pagination"]["page"] == 1
            assert data["total_entries"] == len(sample_food_logs)
            assert data["analyzed_entries"] == len(sample_food_logs)
            assert data["analysis_capped"] is False
            assert data["analysis_limit"] is None
            assert data["cached"] is False

    def test_lifetime_profile_pagination_params(self, sample_food_logs):
        """Test lifetime profile with custom pagination parameters."""
        with (
            patch("fcp.routes.profile.firestore_client") as mock_fs,
            patch("fcp.routes.profile._lifetime_cache", {}),  # Clear cache
        ):
            mock_fs.get_user_logs_paginated = AsyncMock(return_value=(sample_food_logs[:2], 10))
            mock_fs.get_all_user_logs = AsyncMock(return_value=sample_food_logs)
            mock_gem = AsyncMock()
            mock_gem.generate_json_with_large_context = AsyncMock(return_value={"analysis": "test"})
            override_key = _override_gemini(mock_gem)

            response = client.get(
                "/profile/lifetime?page=1&page_size=50",
                headers=AUTH_HEADER,
            )
            app.dependency_overrides.pop(override_key, None)

            assert response.status_code == 200
            data = response.json()
            assert data["pagination"]["page"] == 1
            assert data["pagination"]["page_size"] == 50
            assert data["pagination"]["total_count"] == 10

    def test_lifetime_profile_pagination_page_2(self, sample_food_logs):
        """Test lifetime profile page 2 returns meals without re-analysis."""
        with (
            patch("fcp.routes.profile.firestore_client") as mock_fs,
            patch("fcp.routes.profile._lifetime_cache", {}),  # Clear cache
        ):
            mock_fs.get_user_logs_paginated = AsyncMock(return_value=(sample_food_logs, 200))

            response = client.get(
                "/profile/lifetime?page=2&page_size=100",
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert "meals" in data
            assert "pagination" in data
            assert "note" in data  # Should have note about analysis on page 1
            assert "lifetime_analysis" not in data  # No analysis on page 2

    def test_lifetime_profile_caching(self, sample_food_logs):
        """Test that lifetime analysis is cached."""

        with (
            patch("fcp.routes.profile.firestore_client") as mock_fs,
            patch("fcp.routes.profile._lifetime_cache", {}),
            patch("fcp.routes.profile.time.time", return_value=1000.0),
        ):
            mock_fs.get_user_logs_paginated = AsyncMock(return_value=(sample_food_logs, 5))
            mock_fs.get_all_user_logs = AsyncMock(return_value=sample_food_logs)
            mock_gem = AsyncMock()
            mock_gem.generate_json_with_large_context = AsyncMock(return_value={"analysis": "cached"})
            override_key = _override_gemini(mock_gem)

            # First call - should generate
            response = client.get("/profile/lifetime", headers=AUTH_HEADER)
            assert response.status_code == 200

            # Verify generate was called
            mock_gem.generate_json_with_large_context.assert_called_once()
            app.dependency_overrides.pop(override_key, None)

    def test_lifetime_profile_refresh_bypasses_cache(self, sample_food_logs):
        """Test that refresh=true bypasses cache."""
        with (
            patch("fcp.routes.profile.firestore_client") as mock_fs,
        ):
            mock_fs.get_user_logs_paginated = AsyncMock(return_value=(sample_food_logs, 5))
            mock_fs.get_all_user_logs = AsyncMock(return_value=sample_food_logs)
            mock_gem = AsyncMock()
            mock_gem.generate_json_with_large_context = AsyncMock(return_value={"analysis": "refreshed"})
            override_key = _override_gemini(mock_gem)

            response = client.get(
                "/profile/lifetime?refresh=true",
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["cached"] is False
            mock_gem.generate_json_with_large_context.assert_called_once()
            app.dependency_overrides.pop(override_key, None)

    def test_lifetime_profile_pagination_metadata(self, sample_food_logs):
        """Test pagination metadata calculation."""
        with (
            patch("fcp.routes.profile.firestore_client") as mock_fs,
            patch("fcp.routes.profile._lifetime_cache", {}),  # Clear cache
        ):
            # 250 total items, 100 per page = 3 pages
            mock_fs.get_user_logs_paginated = AsyncMock(return_value=(sample_food_logs, 250))
            mock_fs.get_all_user_logs = AsyncMock(return_value=sample_food_logs)
            mock_gem = AsyncMock()
            mock_gem.generate_json_with_large_context = AsyncMock(return_value={"analysis": "test"})
            override_key = _override_gemini(mock_gem)

            response = client.get(
                "/profile/lifetime?page=1&page_size=100",
                headers=AUTH_HEADER,
            )

            assert response.status_code == 200
            pagination = response.json()["pagination"]
            assert pagination["total_count"] == 250
            assert pagination["total_pages"] == 3
            assert pagination["has_more"] is True
            app.dependency_overrides.pop(override_key, None)

    def test_lifetime_profile_analysis_capped(self, sample_food_logs):
        """Test analysis is capped when user has many meals (memory safety)."""
        with (
            patch("fcp.routes.profile.firestore_client") as mock_fs,
            patch("fcp.routes.profile._lifetime_cache", {}),
            patch("fcp.routes.profile._ANALYSIS_LIMIT", 100),  # Lower limit for test
        ):
            # User has 500 total meals, but we only analyze 100 (the limit)
            mock_fs.get_user_logs_paginated = AsyncMock(return_value=(sample_food_logs, 500))
            mock_fs.get_all_user_logs = AsyncMock(return_value=sample_food_logs)
            mock_gem = AsyncMock()
            mock_gem.generate_json_with_large_context = AsyncMock(return_value={"analysis": "test"})
            override_key = _override_gemini(mock_gem)

            response = client.get("/profile/lifetime", headers=AUTH_HEADER)

            assert response.status_code == 200
            data = response.json()
            # Verify get_all_user_logs was called with the limit parameter
            call_kwargs = mock_fs.get_all_user_logs.call_args.kwargs
            assert call_kwargs.get("limit") == 100
            # Verify response indicates analysis was capped
            assert data["total_entries"] == 500
            assert data["analyzed_entries"] == len(sample_food_logs)
            assert data["analysis_capped"] is True
            assert data["analysis_limit"] == 100
            app.dependency_overrides.pop(override_key, None)

    def test_lifetime_profile_invalid_page_size(self):
        """Test that invalid page_size is rejected."""
        response = client.get(
            "/profile/lifetime?page_size=5",  # Below minimum of 10
            headers=AUTH_HEADER,
        )
        assert response.status_code == 422  # Validation error

    def test_lifetime_profile_invalid_page(self):
        """Test that invalid page is rejected."""
        response = client.get(
            "/profile/lifetime?page=0",  # Below minimum of 1
            headers=AUTH_HEADER,
        )
        assert response.status_code == 422  # Validation error


class TestMetricsEndpoint:
    """Tests for /metrics endpoint."""

    def test_setup_metrics_is_noop(self):
        """Test that setup_metrics is a no-op (instrumentator removed)."""
        from fastapi import FastAPI

        from fcp.utils.metrics import setup_metrics

        test_app = FastAPI()
        # Should not raise
        setup_metrics(test_app)
        # No /metrics route should be added
        route_paths = [r.path for r in test_app.routes]
        assert "/metrics" not in route_paths

    def test_metrics_endpoint_no_auth_required(self):
        """Test that /metrics endpoint does not require authentication."""
        # Should not return 401 Unauthorized (either 200 or 404 is acceptable)
        response = client.get("/metrics")
        assert response.status_code != 401
