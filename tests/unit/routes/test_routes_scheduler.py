"""Tests for scheduler route endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from fcp.auth.permissions import AuthenticatedUser, UserRole
from tests.constants import TEST_AUTH_HEADER, TEST_USER_ID  # sourcery skip: dont-import-test-modules


def create_tracked_task_mock_closing_coro(task_name: str = "task"):
    """Create a mock create_tracked_task that closes the coroutine to avoid warnings.

    When AsyncMock creates a coroutine but create_tracked_task is mocked,
    the coroutine is never awaited, causing warnings. This helper closes
    the coroutine properly.
    """
    mock_task = MagicMock()
    mock_task.get_name.return_value = task_name

    def side_effect(coro, name=None):
        coro.close()  # Close the coroutine to avoid "never awaited" warning
        return mock_task

    return side_effect, mock_task


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


class TestSchedulerStatusEndpoint:
    """Tests for /scheduler/status endpoint."""

    def test_scheduler_status_unavailable(self, client, mock_auth):
        """Test scheduler status when scheduler is not available."""
        with patch("fcp.routes.scheduler._get_scheduler_module", return_value=(None, False)):
            response = client.get("/scheduler/status", headers=TEST_AUTH_HEADER)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unavailable"
            assert "not installed" in data["message"]

    def test_scheduler_status_stopped(self, client, mock_auth):
        """Test scheduler status when scheduler is stopped."""
        with patch("fcp.routes.scheduler._get_scheduler_module", return_value=(None, True)):
            response = client.get("/scheduler/status", headers=TEST_AUTH_HEADER)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "stopped"
            assert data["jobs"] == []

    def test_scheduler_status_running_with_jobs(self, client, mock_auth):
        """Test scheduler status when running with jobs."""
        from datetime import datetime

        mock_job = MagicMock()
        mock_job.id = "daily_insights"
        mock_job.name = "Daily Insights"
        mock_job.next_run_time = datetime(2026, 1, 30, 8, 0, 0)
        mock_job.trigger = "cron[hour='8', minute='0']"

        mock_scheduler = MagicMock()
        mock_scheduler.get_jobs.return_value = [mock_job]

        with patch("fcp.routes.scheduler._get_scheduler_module", return_value=(mock_scheduler, True)):
            response = client.get("/scheduler/status", headers=TEST_AUTH_HEADER)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "running"
            assert len(data["jobs"]) == 1
            assert data["jobs"][0]["id"] == "daily_insights"

    def test_scheduler_status_job_without_next_run(self, client, mock_auth):
        """Test scheduler status with job that has no next run time."""
        mock_job = MagicMock()
        mock_job.id = "paused_job"
        mock_job.name = "Paused Job"
        mock_job.next_run_time = None
        mock_job.trigger = "cron[hour='8']"

        mock_scheduler = MagicMock()
        mock_scheduler.get_jobs.return_value = [mock_job]

        with patch("fcp.routes.scheduler._get_scheduler_module", return_value=(mock_scheduler, True)):
            response = client.get("/scheduler/status", headers=TEST_AUTH_HEADER)

            assert response.status_code == 200
            data = response.json()
            assert data["jobs"][0]["next_run"] is None

    def test_scheduler_status_allows_demo_user(self, client):
        """Test scheduler status allows demo user (read-only access)."""
        with patch("fcp.routes.scheduler._get_scheduler_module", return_value=(None, False)):
            response = client.get("/scheduler/status")
            assert response.status_code == 200
            assert response.json()["status"] == "unavailable"


class TestSchedulerConfigureEndpoint:
    """Tests for /scheduler/configure endpoint."""

    def test_configure_scheduler_unavailable(self, client, mock_auth):
        """Test configure when scheduler is not available."""
        with patch("fcp.routes.scheduler._get_scheduler_module", return_value=(None, False)):
            response = client.post(
                "/scheduler/configure",
                json={"job_type": "daily_insights", "enabled": True},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 503

    def test_configure_disable_job(self, client, mock_auth):
        """Test disabling a scheduled job."""
        mock_scheduler = MagicMock()

        with patch("fcp.routes.scheduler._get_scheduler_module", return_value=(mock_scheduler, True)):
            response = client.post(
                "/scheduler/configure",
                json={"job_type": "daily_insights", "enabled": False},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "disabled"
            mock_scheduler.remove_job.assert_called_once_with("daily_insights")

    def test_configure_disable_job_without_scheduler(self, client, mock_auth):
        """Test disabling a scheduled job when scheduler is None."""
        with patch("fcp.routes.scheduler._get_scheduler_module", return_value=(None, True)):
            response = client.post(
                "/scheduler/configure",
                json={"job_type": "daily_insights", "enabled": False},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            assert response.json()["status"] == "disabled"

    def test_configure_daily_insights(self, client, mock_auth):
        """Test configuring daily insights job."""
        mock_schedule = MagicMock(return_value="job_123")

        with (
            patch("fcp.routes.scheduler._get_scheduler_module", return_value=(MagicMock(), True)),
            patch(
                "fcp.routes.scheduler._get_scheduler_functions",
                return_value={
                    "schedule_daily_insights": mock_schedule,
                    "schedule_seasonal_reminders": MagicMock(),
                    "schedule_streak_checks": MagicMock(),
                    "schedule_weekly_digests": MagicMock(),
                },
            ),
        ):
            response = client.post(
                "/scheduler/configure",
                json={"job_type": "daily_insights", "enabled": True, "hour": 9, "minute": 30},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "updated"
            assert data["job_id"] == "job_123"
            mock_schedule.assert_called_once_with(hour=9, minute=30)

    def test_configure_weekly_digests(self, client, mock_auth):
        """Test configuring weekly digests job."""
        mock_schedule = MagicMock(return_value="job_456")

        with (
            patch("fcp.routes.scheduler._get_scheduler_module", return_value=(MagicMock(), True)),
            patch(
                "fcp.routes.scheduler._get_scheduler_functions",
                return_value={
                    "schedule_daily_insights": MagicMock(),
                    "schedule_seasonal_reminders": MagicMock(),
                    "schedule_streak_checks": MagicMock(),
                    "schedule_weekly_digests": mock_schedule,
                },
            ),
        ):
            response = client.post(
                "/scheduler/configure",
                json={"job_type": "weekly_digests", "enabled": True, "day_of_week": "mon", "hour": 10},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_schedule.assert_called_once_with(day_of_week="mon", hour=10)

    def test_configure_streak_checks(self, client, mock_auth):
        """Test configuring streak checks job."""
        mock_schedule = MagicMock(return_value="job_789")

        with (
            patch("fcp.routes.scheduler._get_scheduler_module", return_value=(MagicMock(), True)),
            patch(
                "fcp.routes.scheduler._get_scheduler_functions",
                return_value={
                    "schedule_daily_insights": MagicMock(),
                    "schedule_seasonal_reminders": MagicMock(),
                    "schedule_streak_checks": mock_schedule,
                    "schedule_weekly_digests": MagicMock(),
                },
            ),
        ):
            response = client.post(
                "/scheduler/configure",
                json={"job_type": "streak_checks", "enabled": True, "hour": 0, "minute": 5},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_schedule.assert_called_once_with(hour=0, minute=5)

    def test_configure_food_tips(self, client, mock_auth):
        """Test configuring food tips job."""
        with (
            patch("fcp.routes.scheduler._get_scheduler_module", return_value=(MagicMock(), True)),
            patch(
                "fcp.routes.scheduler._get_scheduler_functions",
                return_value={
                    "schedule_daily_insights": MagicMock(),
                    "schedule_seasonal_reminders": MagicMock(),
                    "schedule_streak_checks": MagicMock(),
                    "schedule_weekly_digests": MagicMock(),
                },
            ),
            patch("fcp.scheduler.jobs.schedule_food_tips", return_value="job_999") as mock_schedule,
        ):
            response = client.post(
                "/scheduler/configure",
                json={"job_type": "food_tips", "enabled": True, "hour": 14},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "job_999"
            mock_schedule.assert_called_once_with(hour=14)

    def test_configure_seasonal_reminders(self, client, mock_auth):
        """Test configuring seasonal reminders job."""
        mock_schedule = MagicMock(return_value="job_abc")

        with (
            patch("fcp.routes.scheduler._get_scheduler_module", return_value=(MagicMock(), True)),
            patch(
                "fcp.routes.scheduler._get_scheduler_functions",
                return_value={
                    "schedule_daily_insights": MagicMock(),
                    "schedule_seasonal_reminders": mock_schedule,
                    "schedule_streak_checks": MagicMock(),
                    "schedule_weekly_digests": MagicMock(),
                },
            ),
        ):
            response = client.post(
                "/scheduler/configure",
                json={"job_type": "seasonal_reminders", "enabled": True, "day_of_month": 15, "hour": 9},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            mock_schedule.assert_called_once_with(day=15, hour=9)

    def test_configure_food_tips_defaults(self, client, mock_auth):
        """Test configuring food tips job defaults."""
        with (
            patch("fcp.routes.scheduler._get_scheduler_module", return_value=(MagicMock(), True)),
            patch(
                "fcp.routes.scheduler._get_scheduler_functions",
                return_value={
                    "schedule_daily_insights": MagicMock(),
                    "schedule_seasonal_reminders": MagicMock(),
                    "schedule_streak_checks": MagicMock(),
                    "schedule_weekly_digests": MagicMock(),
                },
            ),
            patch("fcp.scheduler.jobs.schedule_food_tips", return_value="job_tips"),
        ):
            response = client.post(
                "/scheduler/configure",
                json={"job_type": "food_tips", "enabled": True},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["job"] == "food_tips"

    def test_configure_requires_auth(self, client):
        """Test configure requires write access (blocks demo users)."""
        response = client.post(
            "/scheduler/configure",
            json={"job_type": "daily_insights", "enabled": True},
        )
        # Demo users get 403 Forbidden, not 401 Unauthorized
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_configure_food_tips_direct():
    """Directly cover food_tips branch."""
    from starlette.requests import Request

    from fcp.auth.permissions import AuthenticatedUser, UserRole
    from fcp.routes import scheduler as scheduler_routes
    from fcp.routes.scheduler import ScheduleUpdateRequest

    request = Request({"type": "http", "method": "POST", "path": "/scheduler/configure", "headers": []})
    user = AuthenticatedUser(user_id="u1", role=UserRole.AUTHENTICATED)

    with (
        patch("fcp.routes.scheduler._get_scheduler_module", return_value=(MagicMock(), True)),
        patch(
            "fcp.routes.scheduler._get_scheduler_functions",
            return_value={
                "schedule_daily_insights": MagicMock(),
                "schedule_seasonal_reminders": MagicMock(),
                "schedule_streak_checks": MagicMock(),
                "schedule_weekly_digests": MagicMock(),
            },
        ),
        patch("fcp.scheduler.jobs.schedule_food_tips", return_value="job_abc") as mock_schedule,
    ):
        result = await scheduler_routes.configure_schedule(
            request,
            ScheduleUpdateRequest(job_type="food_tips", enabled=True, hour=9),
            user=user,
        )
        assert result["job_id"] == "job_abc"
        mock_schedule.assert_called_once_with(hour=9)


@pytest.mark.asyncio
async def test_configure_food_tips_direct_defaults():
    """Directly cover food_tips branch with default hour."""
    from starlette.requests import Request

    from fcp.auth.permissions import AuthenticatedUser, UserRole
    from fcp.routes import scheduler as scheduler_routes
    from fcp.routes.scheduler import ScheduleUpdateRequest

    request = Request({"type": "http", "method": "POST", "path": "/scheduler/configure", "headers": []})
    user = AuthenticatedUser(user_id="u1", role=UserRole.AUTHENTICATED)

    with (
        patch("fcp.routes.scheduler._get_scheduler_module", return_value=(MagicMock(), True)),
        patch(
            "fcp.routes.scheduler._get_scheduler_functions",
            return_value={
                "schedule_daily_insights": MagicMock(),
                "schedule_seasonal_reminders": MagicMock(),
                "schedule_streak_checks": MagicMock(),
                "schedule_weekly_digests": MagicMock(),
            },
        ),
        patch("fcp.scheduler.jobs.schedule_food_tips", return_value="job_default") as mock_schedule,
    ):
        result = await scheduler_routes.configure_schedule(
            request,
            ScheduleUpdateRequest(job_type="food_tips", enabled=True),
            user=user,
        )
        assert result["job_id"] == "job_default"
        mock_schedule.assert_called_once_with(hour=12)


class TestSchedulerTriggerEndpoint:
    """Tests for /scheduler/trigger/{job_type} endpoint."""

    def test_trigger_scheduler_unavailable(self, client, mock_auth):
        """Test trigger when scheduler is not available."""
        with patch("fcp.routes.scheduler._get_scheduler_module", return_value=(None, False)):
            response = client.post(
                "/scheduler/trigger/daily_insights",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 503

    def test_trigger_unknown_job_type(self, client, mock_auth):
        """Test trigger with unknown job type."""
        with (
            patch("fcp.routes.scheduler._get_scheduler_module", return_value=(MagicMock(), True)),
            patch("fcp.routes.scheduler.create_tracked_task"),
        ):
            # Mock the imports inside trigger_job_manually
            with patch.dict("sys.modules", {"fcp.scheduler.jobs": MagicMock()}):
                response = client.post(
                    "/scheduler/trigger/unknown_job",
                    headers=TEST_AUTH_HEADER,
                )

                assert response.status_code == 400
                data = response.json()
                error_msg = data.get("detail") or data.get("error", {}).get("message", "")
                assert "Unknown job type" in error_msg

    def test_trigger_daily_insights(self, client, mock_auth):
        """Test triggering daily insights job."""
        side_effect, _ = create_tracked_task_mock_closing_coro("task_123")

        with (
            patch("fcp.routes.scheduler._get_scheduler_module", return_value=(MagicMock(), True)),
            patch("fcp.routes.scheduler.create_tracked_task", side_effect=side_effect),
            patch("fcp.scheduler.jobs.run_daily_insights_job", new_callable=AsyncMock),
        ):
            response = client.post(
                "/scheduler/trigger/daily_insights",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "triggered"
            assert data["job"] == "daily_insights"

    def test_trigger_weekly_digests(self, client, mock_auth):
        """Test triggering weekly digests job."""
        side_effect, _ = create_tracked_task_mock_closing_coro("task_456")

        with (
            patch("fcp.routes.scheduler._get_scheduler_module", return_value=(MagicMock(), True)),
            patch("fcp.routes.scheduler.create_tracked_task", side_effect=side_effect),
            patch("fcp.scheduler.jobs.run_weekly_digests_job", new_callable=AsyncMock),
        ):
            response = client.post(
                "/scheduler/trigger/weekly_digests",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["job"] == "weekly_digests"

    def test_trigger_streak_checks(self, client, mock_auth):
        """Test triggering streak checks job."""
        side_effect, _ = create_tracked_task_mock_closing_coro("task_789")

        with (
            patch("fcp.routes.scheduler._get_scheduler_module", return_value=(MagicMock(), True)),
            patch("fcp.routes.scheduler.create_tracked_task", side_effect=side_effect),
            patch("fcp.scheduler.jobs.run_streak_checks_job", new_callable=AsyncMock),
        ):
            response = client.post(
                "/scheduler/trigger/streak_checks",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

    def test_trigger_seasonal_reminders(self, client, mock_auth):
        """Test triggering seasonal reminders job."""
        side_effect, _ = create_tracked_task_mock_closing_coro("task_abc")

        with (
            patch("fcp.routes.scheduler._get_scheduler_module", return_value=(MagicMock(), True)),
            patch("fcp.routes.scheduler.create_tracked_task", side_effect=side_effect),
            patch("fcp.scheduler.jobs.run_seasonal_reminders_job", new_callable=AsyncMock),
        ):
            response = client.post(
                "/scheduler/trigger/seasonal_reminders",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

    def test_trigger_food_tips(self, client, mock_auth):
        """Test triggering food tips job."""
        side_effect, _ = create_tracked_task_mock_closing_coro("task_tips")

        with (
            patch("fcp.routes.scheduler._get_scheduler_module", return_value=(MagicMock(), True)),
            patch("fcp.routes.scheduler.create_tracked_task", side_effect=side_effect),
            patch("fcp.scheduler.jobs.run_food_tips_job", new_callable=AsyncMock),
        ):
            response = client.post(
                "/scheduler/trigger/food_tips",
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 200

    def test_trigger_requires_auth(self, client):
        """Test trigger requires write access (blocks demo users)."""
        response = client.post("/scheduler/trigger/daily_insights")
        # Demo users get 403 Forbidden, not 401 Unauthorized
        assert response.status_code == 403


class TestSchedulerImportError:
    """Tests for scheduler ImportError handling in routes/scheduler.py."""

    def test_scheduler_unavailable_status_endpoint(self, client, mock_auth):
        """Test that scheduler status endpoint handles unavailable scheduler.

        The _get_scheduler_module function returns (None, False) when the
        scheduler is not installed. This test verifies the endpoint handles
        that state.
        """
        with patch("fcp.routes.scheduler._get_scheduler_module", return_value=(None, False)):
            response = client.get("/scheduler/status", headers=TEST_AUTH_HEADER)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unavailable"

    def test_scheduler_unavailable_configure_endpoint(self, client, mock_auth):
        """Test that configure endpoint handles unavailable scheduler."""
        with patch("fcp.routes.scheduler._get_scheduler_module", return_value=(None, False)):
            response = client.post(
                "/scheduler/configure",
                json={"job_type": "daily_insights", "enabled": True},
                headers=TEST_AUTH_HEADER,
            )

            assert response.status_code == 503

    def test_module_exposes_scheduler_module_function(self):
        """Test that routes/scheduler module exposes _get_scheduler_module function."""
        from fcp.routes.scheduler import _get_scheduler_module

        # The function should return a tuple of (scheduler, available)
        result = _get_scheduler_module()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[1], bool)
