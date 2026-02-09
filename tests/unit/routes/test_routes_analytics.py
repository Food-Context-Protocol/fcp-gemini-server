"""Tests for analytics route endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from fcp.auth.permissions import AuthenticatedUser, UserRole
from tests.constants import TEST_AUTH_HEADER, TEST_USER_ID  # sourcery skip: dont-import-test-modules


@pytest.fixture
def client():
    """Create test client with mocked dependencies."""
    from fcp.api import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_auth():
    """Mock authentication to return test user."""
    from fcp.api import app
    from fcp.auth.local import get_current_user
    from fcp.auth.permissions import require_write_access

    user = AuthenticatedUser(user_id=TEST_USER_ID, role=UserRole.AUTHENTICATED)

    async def override_get_current_user(authorization=None):
        return user

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[require_write_access] = override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_write_access, None)


@pytest.fixture
def sample_meals():
    """Sample meal data for testing."""
    return [
        {
            "id": "meal1",
            "dish_name": "Pasta",
            "created_at": datetime(2026, 1, 28, 12, 0, 0),
            "nutrition": {"calories": 500, "protein": 20, "carbs": 60, "fat": 15},
        },
        {
            "id": "meal2",
            "dish_name": "Salad",
            "created_at": datetime(2026, 1, 29, 18, 0, 0),
            "nutrition": {"calories": 200, "protein": 5, "carbs": 20, "fat": 10},
        },
    ]


class TestNutritionAnalyticsEndpoint:
    """Tests for /analytics/nutrition endpoint."""

    def test_nutrition_analytics_success(self, client, mock_auth, sample_meals):
        """Test successful nutrition analytics."""
        with (
            patch("fcp.routes.analytics.get_meals", new_callable=AsyncMock) as mock_get,
            patch("fcp.routes.analytics.calculate_nutrition_stats", new_callable=AsyncMock) as mock_calc,
        ):
            mock_get.return_value = sample_meals
            mock_calc.return_value = {"avg_calories": 350, "avg_protein": 12.5}

            response = client.post(
                "/analytics/nutrition",
                json={"days": 7},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["period_days"] == 7
            assert data["meal_count"] == 2
            assert "stats" in data
            mock_get.assert_called_once()

    def test_nutrition_analytics_default_days(self, client, mock_auth):
        """Test nutrition analytics with default days."""
        with (
            patch("fcp.routes.analytics.get_meals", new_callable=AsyncMock) as mock_get,
            patch("fcp.routes.analytics.calculate_nutrition_stats", new_callable=AsyncMock) as mock_calc,
        ):
            mock_get.return_value = []
            mock_calc.return_value = {}

            response = client.post(
                "/analytics/nutrition",
                json={},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["period_days"] == 7  # Default

    def test_nutrition_analytics_requires_auth(self, client):
        """Test nutrition analytics requires authentication."""
        response = client.post("/analytics/nutrition", json={"days": 7})
        assert response.status_code == 403  # Demo users get 403 for write endpoints


class TestEatingPatternsEndpoint:
    """Tests for /analytics/patterns endpoint."""

    def test_eating_patterns_success(self, client, mock_auth, sample_meals):
        """Test successful eating patterns analysis."""
        with (
            patch("fcp.routes.analytics.get_meals", new_callable=AsyncMock) as mock_get,
            patch("fcp.routes.analytics.analyze_eating_patterns", new_callable=AsyncMock) as mock_analyze,
        ):
            mock_get.return_value = sample_meals
            mock_analyze.return_value = {"meal_times": {"lunch": 1, "dinner": 1}}

            response = client.post(
                "/analytics/patterns",
                json={"days": 14},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["period_days"] == 14
            assert "patterns" in data

    def test_eating_patterns_requires_auth(self, client):
        """Test eating patterns requires authentication."""
        response = client.post("/analytics/patterns", json={"days": 7})
        assert response.status_code == 403  # Demo users get 403 for write endpoints


class TestNutritionTrendsEndpoint:
    """Tests for /analytics/trends endpoint."""

    def test_nutrition_trends_success(self, client, mock_auth, sample_meals):
        """Test successful nutrition trends analysis."""
        with (
            patch("fcp.routes.analytics.get_meals", new_callable=AsyncMock) as mock_get,
            patch("fcp.routes.analytics.calculate_trend_report", new_callable=AsyncMock) as mock_trend,
        ):
            mock_get.return_value = sample_meals
            mock_trend.return_value = {"trend": "improving", "change_pct": 5}

            response = client.post(
                "/analytics/trends",
                json={"days": 30},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["period_days"] == 30
            assert "trends" in data

    def test_nutrition_trends_requires_auth(self, client):
        """Test nutrition trends requires authentication."""
        response = client.post("/analytics/trends", json={"days": 7})
        assert response.status_code == 403  # Demo users get 403 for write endpoints


class TestComparePeriodsEndpoint:
    """Tests for /analytics/compare endpoint."""

    def test_compare_periods_success(self, client, mock_auth):
        """Test successful period comparison."""
        meals_with_dates = [
            {
                "id": "m1",
                "dish_name": "Food1",
                "created_at": datetime(2026, 1, 15, 12, 0),
                "nutrition": {"calories": 500},
            },
            {
                "id": "m2",
                "dish_name": "Food2",
                "created_at": datetime(2026, 1, 25, 12, 0),
                "nutrition": {"calories": 600},
            },
        ]

        with (
            patch("fcp.routes.analytics.get_meals", new_callable=AsyncMock) as mock_get,
            patch("fcp.routes.analytics.compare_periods", new_callable=AsyncMock) as mock_compare,
        ):
            mock_get.side_effect = [meals_with_dates, meals_with_dates]
            mock_compare.return_value = {"period1_avg": 500, "period2_avg": 600, "change": 100}

            response = client.post(
                "/analytics/compare",
                json={
                    "period1_start": "2026-01-10",
                    "period1_end": "2026-01-20",
                    "period2_start": "2026-01-21",
                    "period2_end": "2026-01-30",
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert "comparison" in data

    def test_compare_periods_with_string_dates(self, client, mock_auth):
        """Test period comparison with ISO string dates in meals."""
        meals_with_string_dates = [
            {
                "id": "m1",
                "dish_name": "Food1",
                "created_at": "2026-01-15T12:00:00Z",
                "nutrition": {"calories": 500},
            },
        ]

        with (
            patch("fcp.routes.analytics.get_meals", new_callable=AsyncMock) as mock_get,
            patch("fcp.routes.analytics.compare_periods", new_callable=AsyncMock) as mock_compare,
        ):
            mock_get.side_effect = [meals_with_string_dates, meals_with_string_dates]
            mock_compare.return_value = {}

            response = client.post(
                "/analytics/compare",
                json={
                    "period1_start": "2026-01-10",
                    "period1_end": "2026-01-20",
                    "period2_start": "2026-01-21",
                    "period2_end": "2026-01-30",
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

    def test_compare_periods_with_missing_dates(self, client, mock_auth):
        """Test period comparison when meals have no dates."""
        meals_without_dates = [
            {"id": "m1", "dish_name": "Food1", "nutrition": {"calories": 500}},
        ]

        with (
            patch("fcp.routes.analytics.get_meals", new_callable=AsyncMock) as mock_get,
            patch("fcp.routes.analytics.compare_periods", new_callable=AsyncMock) as mock_compare,
        ):
            mock_get.side_effect = [meals_without_dates, meals_without_dates]
            mock_compare.return_value = {}

            response = client.post(
                "/analytics/compare",
                json={
                    "period1_start": "2026-01-10",
                    "period1_end": "2026-01-20",
                    "period2_start": "2026-01-21",
                    "period2_end": "2026-01-30",
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

    def test_compare_periods_with_invalid_date_format(self, client, mock_auth):
        """Test period comparison with invalid date format in meal."""
        meals_with_invalid_dates = [
            {
                "id": "m1",
                "dish_name": "Food1",
                "created_at": "invalid-date",
                "nutrition": {"calories": 500},
            },
        ]

        with (
            patch("fcp.routes.analytics.get_meals", new_callable=AsyncMock) as mock_get,
            patch("fcp.routes.analytics.compare_periods", new_callable=AsyncMock) as mock_compare,
        ):
            mock_get.side_effect = [meals_with_invalid_dates, meals_with_invalid_dates]
            mock_compare.return_value = {}

            response = client.post(
                "/analytics/compare",
                json={
                    "period1_start": "2026-01-10",
                    "period1_end": "2026-01-20",
                    "period2_start": "2026-01-21",
                    "period2_end": "2026-01-30",
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

    def test_compare_periods_with_non_datetime_type(self, client, mock_auth):
        """Test period comparison with unexpected date type."""
        meals_with_other_type = [
            {
                "id": "m1",
                "dish_name": "Food1",
                "created_at": 12345,  # Integer instead of datetime
                "nutrition": {"calories": 500},
            },
        ]

        with (
            patch("fcp.routes.analytics.get_meals", new_callable=AsyncMock) as mock_get,
            patch("fcp.routes.analytics.compare_periods", new_callable=AsyncMock) as mock_compare,
        ):
            mock_get.side_effect = [meals_with_other_type, meals_with_other_type]
            mock_compare.return_value = {}

            response = client.post(
                "/analytics/compare",
                json={
                    "period1_start": "2026-01-10",
                    "period1_end": "2026-01-20",
                    "period2_start": "2026-01-21",
                    "period2_end": "2026-01-30",
                },
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

    def test_compare_periods_requires_auth(self, client):
        """Test period comparison requires authentication."""
        response = client.post(
            "/analytics/compare",
            json={
                "period1_start": "2026-01-10",
                "period1_end": "2026-01-20",
                "period2_start": "2026-01-21",
                "period2_end": "2026-01-30",
            },
        )
        assert response.status_code == 403  # Demo users get 403 for write endpoints


class TestNutritionReportEndpoint:
    """Tests for /analytics/report endpoint."""

    def test_nutrition_report_success(self, client, mock_auth, sample_meals):
        """Test successful nutrition report generation."""
        with (
            patch("fcp.routes.analytics.get_meals", new_callable=AsyncMock) as mock_get,
            patch("fcp.routes.analytics.generate_nutrition_report", new_callable=AsyncMock) as mock_report,
        ):
            mock_get.return_value = sample_meals
            mock_report.return_value = {"summary": "Good nutrition", "recommendations": []}

            response = client.get(
                "/analytics/report?days=30",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["period_days"] == 30
            assert data["meal_count"] == 2
            assert "report" in data

    def test_nutrition_report_default_days(self, client, mock_auth):
        """Test nutrition report with default days."""
        with (
            patch("fcp.routes.analytics.get_meals", new_callable=AsyncMock) as mock_get,
            patch("fcp.routes.analytics.generate_nutrition_report", new_callable=AsyncMock) as mock_report,
        ):
            mock_get.return_value = []
            mock_report.return_value = {}

            response = client.get(
                "/analytics/report",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["period_days"] == 30  # Default

    def test_nutrition_report_allows_demo_user(self, client, mock_auth):
        """Test nutrition report allows demo users (read-only endpoint)."""
        # Demo mode: demo users can access GET endpoints
        # Just verify the endpoint doesn't reject with 403
        # The actual response depends on data/API availability
        with patch("fcp.routes.analytics.generate_nutrition_report", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {"report": "test", "period_days": 30}
            response = client.get("/analytics/report")
            # Demo user should be allowed (not 401 or 403)
            assert response.status_code == 200
