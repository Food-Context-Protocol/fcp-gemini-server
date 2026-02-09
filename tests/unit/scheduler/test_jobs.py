"""Tests for scheduler jobs module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSchedulerLifecycle:
    """Tests for scheduler start/stop functions."""

    def test_start_scheduler_creates_new_scheduler(self):
        """Test starting scheduler creates a new instance."""
        with patch("fcp.scheduler.jobs.AsyncIOScheduler") as mock_scheduler_class:
            mock_scheduler = MagicMock()
            mock_scheduler_class.return_value = mock_scheduler

            # Reset global scheduler
            import fcp.scheduler.jobs as jobs_module

            jobs_module.scheduler = None

            scheduler = jobs_module.start_scheduler()

            assert scheduler is not None
            mock_scheduler.start.assert_called_once()

    def test_start_scheduler_returns_existing(self):
        """Test starting scheduler returns existing instance if running."""
        import fcp.scheduler.jobs as jobs_module

        mock_existing = MagicMock()
        jobs_module.scheduler = mock_existing

        scheduler = jobs_module.start_scheduler()

        assert scheduler is mock_existing

    def test_stop_scheduler(self):
        """Test stopping the scheduler."""
        import fcp.scheduler.jobs as jobs_module

        mock_scheduler = MagicMock()
        jobs_module.scheduler = mock_scheduler

        jobs_module.stop_scheduler()

        mock_scheduler.shutdown.assert_called_once()
        assert jobs_module.scheduler is None

    def test_stop_scheduler_when_not_running(self):
        """Test stopping scheduler when not running does nothing."""
        import fcp.scheduler.jobs as jobs_module

        jobs_module.scheduler = None

        # Should not raise
        jobs_module.stop_scheduler()

        assert jobs_module.scheduler is None


class TestGetActiveUsers:
    """Tests for get_active_users function."""

    @pytest.mark.asyncio
    async def test_get_active_users(self):
        """Test getting active users."""
        from fcp.scheduler.jobs import get_active_users

        mock_users = [{"id": "user1"}, {"id": "user2"}]

        with patch("fcp.scheduler.jobs.firestore_client") as mock_db:
            mock_db.get_active_users = AsyncMock(return_value=mock_users)

            users = await get_active_users()

            assert len(users) == 2
            mock_db.get_active_users.assert_called_once_with(days=7)


class TestGetUserPreferences:
    """Tests for get_user_preferences function."""

    @pytest.mark.asyncio
    async def test_get_user_preferences(self):
        """Test getting user preferences."""
        from fcp.scheduler.jobs import get_user_preferences

        mock_prefs = {"daily_insights_enabled": True, "location": "Seattle"}

        with patch("fcp.scheduler.jobs.firestore_client") as mock_db:
            mock_db.get_user_preferences = AsyncMock(return_value=mock_prefs)

            prefs = await get_user_preferences("user123")

            assert prefs["daily_insights_enabled"] is True
            assert prefs["location"] == "Seattle"


class TestDailyInsightsJob:
    """Tests for daily insights job functions."""

    @pytest.mark.asyncio
    async def test_generate_daily_insight_for_user_success(self):
        """Test generating daily insight for a single user."""
        from fcp.scheduler.jobs import generate_daily_insight_for_user

        mock_profile = {"preferences": {}}
        mock_logs = [{"dish_name": "Salad"}]
        mock_prefs = {"location": "Seattle"}
        mock_insight = {"insight": "Today is soup weather!"}

        with (
            patch(
                "fcp.scheduler.jobs.get_taste_profile",
                new_callable=AsyncMock,
            ) as mock_get_profile,
            patch(
                "fcp.scheduler.jobs.get_meals",
                new_callable=AsyncMock,
            ) as mock_get_meals,
            patch(
                "fcp.scheduler.jobs.get_user_preferences",
                new_callable=AsyncMock,
            ) as mock_get_prefs,
            patch("fcp.scheduler.jobs.FreshnessAgent") as mock_agent_class,
            patch("fcp.scheduler.jobs.firestore_client") as mock_db,
        ):
            mock_get_profile.return_value = mock_profile
            mock_get_meals.return_value = mock_logs
            mock_get_prefs.return_value = mock_prefs
            mock_agent = MagicMock()
            mock_agent.generate_daily_insight = AsyncMock(return_value=mock_insight)
            mock_agent_class.return_value = mock_agent
            mock_db.store_notification = AsyncMock()

            result = await generate_daily_insight_for_user("user123")

            assert result == mock_insight
            mock_db.store_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_daily_insight_for_user_failure(self):
        """Test handling failure when generating insight."""
        from fcp.scheduler.jobs import generate_daily_insight_for_user

        with patch(
            "fcp.scheduler.jobs.get_taste_profile",
            new_callable=AsyncMock,
        ) as mock_get_profile:
            mock_get_profile.side_effect = Exception("API Error")

            result = await generate_daily_insight_for_user("user123")

            assert result is None

    @pytest.mark.asyncio
    async def test_run_daily_insights_job(self):
        """Test running daily insights for all users."""
        from fcp.scheduler.jobs import run_daily_insights_job

        mock_users = [{"id": "user1"}, {"id": "user2"}]
        mock_prefs = {"daily_insights_enabled": True}

        with (
            patch(
                "fcp.scheduler.jobs.get_active_users",
                new_callable=AsyncMock,
            ) as mock_get_users,
            patch(
                "fcp.scheduler.jobs.get_user_preferences",
                new_callable=AsyncMock,
            ) as mock_get_prefs,
            patch(
                "fcp.scheduler.jobs.generate_daily_insight_for_user",
                new_callable=AsyncMock,
            ) as mock_generate,
            patch(
                "asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            mock_get_users.return_value = mock_users
            mock_get_prefs.return_value = mock_prefs
            mock_generate.return_value = {"insight": "test"}

            await run_daily_insights_job()

            assert mock_generate.call_count == 2

    @pytest.mark.asyncio
    async def test_run_daily_insights_job_respects_preferences(self):
        """Test that daily insights respects user preferences."""
        from fcp.scheduler.jobs import run_daily_insights_job

        mock_users = [{"id": "user1"}]

        with (
            patch(
                "fcp.scheduler.jobs.get_active_users",
                new_callable=AsyncMock,
            ) as mock_get_users,
            patch(
                "fcp.scheduler.jobs.get_user_preferences",
                new_callable=AsyncMock,
            ) as mock_get_prefs,
            patch(
                "fcp.scheduler.jobs.generate_daily_insight_for_user",
                new_callable=AsyncMock,
            ) as mock_generate,
            patch(
                "asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            mock_get_users.return_value = mock_users
            mock_get_prefs.return_value = {"daily_insights_enabled": False}

            await run_daily_insights_job()

            mock_generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_daily_insights_job_skips_invalid_user_id(self):
        """Test that daily insights skips users without valid string id."""
        from fcp.scheduler.jobs import run_daily_insights_job

        # One user with None id, one with valid id
        mock_users = [{"id": None}, {"id": 123}, {"name": "no_id"}, {"id": "valid_user"}]

        with (
            patch(
                "fcp.scheduler.jobs.get_active_users",
                new_callable=AsyncMock,
            ) as mock_get_users,
            patch(
                "fcp.scheduler.jobs.get_user_preferences",
                new_callable=AsyncMock,
            ) as mock_get_prefs,
            patch(
                "fcp.scheduler.jobs.generate_daily_insight_for_user",
                new_callable=AsyncMock,
            ) as mock_generate,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_get_users.return_value = mock_users
            mock_get_prefs.return_value = {"daily_insights_enabled": True}
            mock_generate.return_value = {"insight": "test"}

            await run_daily_insights_job()

            # Only valid_user should have been processed
            assert mock_generate.call_count == 1
            mock_generate.assert_called_with("valid_user")

    def test_schedule_daily_insights(self):
        """Test scheduling daily insights job."""
        import fcp.scheduler.jobs as jobs_module

        mock_scheduler = MagicMock()
        mock_job = MagicMock()
        mock_job.id = "daily_insights"
        mock_scheduler.add_job.return_value = mock_job
        jobs_module.scheduler = mock_scheduler

        job_id = jobs_module.schedule_daily_insights(hour=9, minute=30)

        assert job_id == "daily_insights"
        mock_scheduler.add_job.assert_called_once()

    def test_schedule_daily_insights_starts_scheduler_if_needed(self):
        """Test that scheduling starts scheduler if not running."""
        import fcp.scheduler.jobs as jobs_module

        jobs_module.scheduler = None

        with patch("fcp.scheduler.jobs.start_scheduler") as mock_start:
            mock_scheduler = MagicMock()
            mock_job = MagicMock()
            mock_job.id = "daily_insights"
            mock_scheduler.add_job.return_value = mock_job

            def set_scheduler():
                jobs_module.scheduler = mock_scheduler
                return mock_scheduler

            mock_start.side_effect = set_scheduler

            jobs_module.schedule_daily_insights()

            mock_start.assert_called_once()


class TestWeeklyDigestsJob:
    """Tests for weekly digests job functions."""

    @pytest.mark.asyncio
    async def test_generate_weekly_digest_for_user_success(self):
        """Test generating weekly digest for a single user."""
        from fcp.scheduler.jobs import generate_weekly_digest_for_user

        mock_logs = [{"dish_name": f"Meal{i}"} for i in range(5)]
        mock_prefs = {"display_name": "Chef"}
        mock_digest = {"title": "Your Week in Food"}

        with (
            patch(
                "fcp.scheduler.jobs.get_meals",
                new_callable=AsyncMock,
            ) as mock_get_meals,
            patch(
                "fcp.scheduler.jobs.get_user_preferences",
                new_callable=AsyncMock,
            ) as mock_get_prefs,
            patch("fcp.scheduler.jobs.ContentGeneratorAgent") as mock_agent_class,
            patch("fcp.scheduler.jobs.firestore_client") as mock_db,
        ):
            mock_get_meals.return_value = mock_logs
            mock_get_prefs.return_value = mock_prefs
            mock_agent = MagicMock()
            mock_agent.generate_weekly_digest = AsyncMock(return_value=mock_digest)
            mock_agent_class.return_value = mock_agent
            mock_db.store_notification = AsyncMock()

            result = await generate_weekly_digest_for_user("user123")

            assert result == mock_digest

    @pytest.mark.asyncio
    async def test_generate_weekly_digest_insufficient_data(self):
        """Test skipping digest when insufficient data."""
        from fcp.scheduler.jobs import generate_weekly_digest_for_user

        with patch(
            "fcp.scheduler.jobs.get_meals",
            new_callable=AsyncMock,
        ) as mock_get_meals:
            mock_get_meals.return_value = [{"dish_name": "Only one meal"}]

            result = await generate_weekly_digest_for_user("user123")

            assert result is None

    @pytest.mark.asyncio
    async def test_generate_weekly_digest_failure(self):
        """Test handling failure when generating digest."""
        from fcp.scheduler.jobs import generate_weekly_digest_for_user

        with patch(
            "fcp.scheduler.jobs.get_meals",
            new_callable=AsyncMock,
        ) as mock_get_meals:
            mock_get_meals.side_effect = Exception("DB Error")

            result = await generate_weekly_digest_for_user("user123")

            assert result is None

    @pytest.mark.asyncio
    async def test_run_weekly_digests_job(self):
        """Test running weekly digests for all users."""
        from fcp.scheduler.jobs import run_weekly_digests_job

        mock_users = [{"id": "user1"}]
        mock_prefs = {"weekly_digest_enabled": True}

        with (
            patch(
                "fcp.scheduler.jobs.get_active_users",
                new_callable=AsyncMock,
            ) as mock_get_users,
            patch(
                "fcp.scheduler.jobs.get_user_preferences",
                new_callable=AsyncMock,
            ) as mock_get_prefs,
            patch(
                "fcp.scheduler.jobs.generate_weekly_digest_for_user",
                new_callable=AsyncMock,
            ) as mock_generate,
            patch(
                "asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            mock_get_users.return_value = mock_users
            mock_get_prefs.return_value = mock_prefs
            mock_generate.return_value = {"digest": "test"}

            await run_weekly_digests_job()

            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_weekly_digests_job_skips_invalid_user_id(self):
        """Test that weekly digests skips users without valid string id."""
        from fcp.scheduler.jobs import run_weekly_digests_job

        mock_users = [{"id": None}, {"id": "valid_user"}]

        with (
            patch(
                "fcp.scheduler.jobs.get_active_users",
                new_callable=AsyncMock,
            ) as mock_get_users,
            patch(
                "fcp.scheduler.jobs.get_user_preferences",
                new_callable=AsyncMock,
            ) as mock_get_prefs,
            patch(
                "fcp.scheduler.jobs.generate_weekly_digest_for_user",
                new_callable=AsyncMock,
            ) as mock_generate,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_get_users.return_value = mock_users
            mock_get_prefs.return_value = {"weekly_digest_enabled": True}
            mock_generate.return_value = {"digest": "test"}

            await run_weekly_digests_job()

            assert mock_generate.call_count == 1
            mock_generate.assert_called_with("valid_user")

    @pytest.mark.asyncio
    async def test_run_weekly_digests_job_skips_disabled(self):
        """Test weekly digests skips when preference disabled."""
        from fcp.scheduler.jobs import run_weekly_digests_job

        with (
            patch("fcp.scheduler.jobs.get_active_users", new_callable=AsyncMock, return_value=[{"id": "user1"}]),
            patch(
                "fcp.scheduler.jobs.get_user_preferences",
                new_callable=AsyncMock,
                return_value={"weekly_digest_enabled": False},
            ),
            patch("fcp.scheduler.jobs.generate_weekly_digest_for_user", new_callable=AsyncMock) as mock_generate,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            await run_weekly_digests_job()
            mock_generate.assert_not_called()

    def test_schedule_weekly_digests(self):
        """Test scheduling weekly digests job."""
        import fcp.scheduler.jobs as jobs_module

        mock_scheduler = MagicMock()
        mock_job = MagicMock()
        mock_job.id = "weekly_digests"
        mock_scheduler.add_job.return_value = mock_job
        jobs_module.scheduler = mock_scheduler

        job_id = jobs_module.schedule_weekly_digests(day_of_week="mon", hour=10)

        assert job_id == "weekly_digests"

    def test_schedule_weekly_digests_starts_scheduler_if_needed(self):
        """Test that scheduling starts scheduler if not running."""
        import fcp.scheduler.jobs as jobs_module

        jobs_module.scheduler = None

        with patch("fcp.scheduler.jobs.start_scheduler") as mock_start:
            mock_scheduler = MagicMock()
            mock_job = MagicMock()
            mock_job.id = "weekly_digests"
            mock_scheduler.add_job.return_value = mock_job

            def set_scheduler():
                jobs_module.scheduler = mock_scheduler
                return mock_scheduler

            mock_start.side_effect = set_scheduler

            jobs_module.schedule_weekly_digests()

            mock_start.assert_called_once()


class TestStreakChecksJob:
    """Tests for streak checks job functions."""

    @pytest.mark.asyncio
    async def test_check_and_celebrate_streak_milestone(self):
        """Test celebrating a streak milestone."""
        from fcp.scheduler.jobs import check_and_celebrate_streak

        mock_stats = {"current_streak": 7}
        mock_prefs = {"display_name": "Champion"}
        mock_celebration = {"message": "7 day streak!"}

        with (
            patch("fcp.scheduler.jobs.firestore_client") as mock_db,
            patch(
                "fcp.scheduler.jobs.get_user_preferences",
                new_callable=AsyncMock,
            ) as mock_get_prefs,
            patch("fcp.scheduler.jobs.FreshnessAgent") as mock_agent_class,
        ):
            mock_db.get_user_stats = AsyncMock(return_value=mock_stats)
            mock_db.store_notification = AsyncMock()
            mock_get_prefs.return_value = mock_prefs
            mock_agent = MagicMock()
            mock_agent.generate_streak_celebration = AsyncMock(return_value=mock_celebration)
            mock_agent_class.return_value = mock_agent

            result = await check_and_celebrate_streak("user123")

            assert result == mock_celebration
            mock_db.store_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_and_celebrate_streak_not_milestone(self):
        """Test that non-milestone streaks don't get celebrated."""
        from fcp.scheduler.jobs import check_and_celebrate_streak

        mock_stats = {"current_streak": 5}  # Not a milestone

        with patch("fcp.scheduler.jobs.firestore_client") as mock_db:
            mock_db.get_user_stats = AsyncMock(return_value=mock_stats)

            result = await check_and_celebrate_streak("user123")

            assert result is None

    @pytest.mark.asyncio
    async def test_check_and_celebrate_streak_failure(self):
        """Test handling failure in streak check."""
        from fcp.scheduler.jobs import check_and_celebrate_streak

        with patch("fcp.scheduler.jobs.firestore_client") as mock_db:
            mock_db.get_user_stats = AsyncMock(side_effect=Exception("Error"))

            result = await check_and_celebrate_streak("user123")

            assert result is None

    @pytest.mark.asyncio
    async def test_run_streak_checks_job(self):
        """Test running streak checks for all users."""
        from fcp.scheduler.jobs import run_streak_checks_job

        mock_users = [{"id": "user1"}, {"id": "user2"}]

        with (
            patch(
                "fcp.scheduler.jobs.get_active_users",
                new_callable=AsyncMock,
            ) as mock_get_users,
            patch(
                "fcp.scheduler.jobs.check_and_celebrate_streak",
                new_callable=AsyncMock,
            ) as mock_check,
            patch(
                "asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            mock_get_users.return_value = mock_users
            mock_check.return_value = None

            await run_streak_checks_job()

            assert mock_check.call_count == 2

    @pytest.mark.asyncio
    async def test_run_streak_checks_job_skips_invalid_user_id(self):
        """Test that streak checks skips users without valid string id."""
        from fcp.scheduler.jobs import run_streak_checks_job

        mock_users = [{"id": None}, {"id": "valid_user"}]

        with (
            patch(
                "fcp.scheduler.jobs.get_active_users",
                new_callable=AsyncMock,
            ) as mock_get_users,
            patch(
                "fcp.scheduler.jobs.check_and_celebrate_streak",
                new_callable=AsyncMock,
            ) as mock_check,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_get_users.return_value = mock_users
            mock_check.return_value = None

            await run_streak_checks_job()

            assert mock_check.call_count == 1
            mock_check.assert_called_with("valid_user")

    def test_schedule_streak_checks(self):
        """Test scheduling streak checks job."""
        import fcp.scheduler.jobs as jobs_module

        mock_scheduler = MagicMock()
        mock_job = MagicMock()
        mock_job.id = "streak_checks"
        mock_scheduler.add_job.return_value = mock_job
        jobs_module.scheduler = mock_scheduler

        job_id = jobs_module.schedule_streak_checks(hour=0, minute=5)

        assert job_id == "streak_checks"

    def test_schedule_streak_checks_starts_scheduler_if_needed(self):
        """Test that scheduling starts scheduler if not running."""
        import fcp.scheduler.jobs as jobs_module

        jobs_module.scheduler = None

        with patch("fcp.scheduler.jobs.start_scheduler") as mock_start:
            mock_scheduler = MagicMock()
            mock_job = MagicMock()
            mock_job.id = "streak_checks"
            mock_scheduler.add_job.return_value = mock_job

            def set_scheduler():
                jobs_module.scheduler = mock_scheduler
                return mock_scheduler

            mock_start.side_effect = set_scheduler

            jobs_module.schedule_streak_checks()

            mock_start.assert_called_once()


class TestSeasonalRemindersJob:
    """Tests for seasonal reminders job functions."""

    @pytest.mark.asyncio
    async def test_generate_seasonal_reminder_for_user_success(self):
        """Test generating seasonal reminder for a user."""
        from fcp.scheduler.jobs import generate_seasonal_reminder_for_user

        mock_prefs = {"location": "Seattle"}
        mock_profile = {"preferences": {}}
        mock_reminder = {"reminder": "Apples are in season!"}

        with (
            patch(
                "fcp.scheduler.jobs.get_user_preferences",
                new_callable=AsyncMock,
            ) as mock_get_prefs,
            patch(
                "fcp.scheduler.jobs.get_taste_profile",
                new_callable=AsyncMock,
            ) as mock_get_profile,
            patch("fcp.scheduler.jobs.FreshnessAgent") as mock_agent_class,
            patch("fcp.scheduler.jobs.firestore_client") as mock_db,
        ):
            mock_get_prefs.return_value = mock_prefs
            mock_get_profile.return_value = mock_profile
            mock_agent = MagicMock()
            mock_agent.generate_seasonal_reminder = AsyncMock(return_value=mock_reminder)
            mock_agent_class.return_value = mock_agent
            mock_db.store_notification = AsyncMock()

            result = await generate_seasonal_reminder_for_user("user123")

            assert result == mock_reminder

    @pytest.mark.asyncio
    async def test_generate_seasonal_reminder_no_location(self):
        """Test skipping reminder when user has no location."""
        from fcp.scheduler.jobs import generate_seasonal_reminder_for_user

        with patch(
            "fcp.scheduler.jobs.get_user_preferences",
            new_callable=AsyncMock,
        ) as mock_get_prefs:
            mock_get_prefs.return_value = {}  # No location

            result = await generate_seasonal_reminder_for_user("user123")

            assert result is None

    @pytest.mark.asyncio
    async def test_generate_seasonal_reminder_failure(self):
        """Test handling failure in seasonal reminder."""
        from fcp.scheduler.jobs import generate_seasonal_reminder_for_user

        with patch(
            "fcp.scheduler.jobs.get_user_preferences",
            new_callable=AsyncMock,
        ) as mock_get_prefs:
            mock_get_prefs.side_effect = Exception("Error")

            result = await generate_seasonal_reminder_for_user("user123")

            assert result is None

    @pytest.mark.asyncio
    async def test_run_seasonal_reminders_job(self):
        """Test running seasonal reminders for all users."""
        from fcp.scheduler.jobs import run_seasonal_reminders_job

        mock_users = [{"id": "user1"}]
        mock_prefs = {"seasonal_reminders_enabled": True}

        with (
            patch(
                "fcp.scheduler.jobs.get_active_users",
                new_callable=AsyncMock,
            ) as mock_get_users,
            patch(
                "fcp.scheduler.jobs.get_user_preferences",
                new_callable=AsyncMock,
            ) as mock_get_prefs,
            patch(
                "fcp.scheduler.jobs.generate_seasonal_reminder_for_user",
                new_callable=AsyncMock,
            ) as mock_generate,
            patch(
                "asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            mock_get_users.return_value = mock_users
            mock_get_prefs.return_value = mock_prefs
            mock_generate.return_value = {"reminder": "test"}

            await run_seasonal_reminders_job()

            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_seasonal_reminders_job_skips_invalid_user_id(self):
        """Test that seasonal reminders skips users without valid string id."""
        from fcp.scheduler.jobs import run_seasonal_reminders_job

        mock_users = [{"id": None}, {"id": "valid_user"}]

        with (
            patch(
                "fcp.scheduler.jobs.get_active_users",
                new_callable=AsyncMock,
            ) as mock_get_users,
            patch(
                "fcp.scheduler.jobs.get_user_preferences",
                new_callable=AsyncMock,
            ) as mock_get_prefs,
            patch(
                "fcp.scheduler.jobs.generate_seasonal_reminder_for_user",
                new_callable=AsyncMock,
            ) as mock_generate,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_get_users.return_value = mock_users
            mock_get_prefs.return_value = {"seasonal_reminders_enabled": True}
            mock_generate.return_value = {"reminder": "test"}

            await run_seasonal_reminders_job()

            assert mock_generate.call_count == 1
            mock_generate.assert_called_with("valid_user")

    @pytest.mark.asyncio
    async def test_run_seasonal_reminders_job_skips_disabled(self):
        """Test seasonal reminders skips when preference disabled."""
        from fcp.scheduler.jobs import run_seasonal_reminders_job

        with (
            patch("fcp.scheduler.jobs.get_active_users", new_callable=AsyncMock, return_value=[{"id": "user1"}]),
            patch(
                "fcp.scheduler.jobs.get_user_preferences",
                new_callable=AsyncMock,
                return_value={"seasonal_reminders_enabled": False},
            ),
            patch("fcp.scheduler.jobs.generate_seasonal_reminder_for_user", new_callable=AsyncMock) as mock_generate,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            await run_seasonal_reminders_job()
            mock_generate.assert_not_called()

    def test_schedule_seasonal_reminders(self):
        """Test scheduling seasonal reminders job."""
        import fcp.scheduler.jobs as jobs_module

        mock_scheduler = MagicMock()
        mock_job = MagicMock()
        mock_job.id = "seasonal_reminders"
        mock_scheduler.add_job.return_value = mock_job
        jobs_module.scheduler = mock_scheduler

        job_id = jobs_module.schedule_seasonal_reminders(day=15, hour=9)

        assert job_id == "seasonal_reminders"

    def test_schedule_seasonal_reminders_starts_scheduler_if_needed(self):
        """Test that scheduling starts scheduler if not running."""
        import fcp.scheduler.jobs as jobs_module

        jobs_module.scheduler = None

        with patch("fcp.scheduler.jobs.start_scheduler") as mock_start:
            mock_scheduler = MagicMock()
            mock_job = MagicMock()
            mock_job.id = "seasonal_reminders"
            mock_scheduler.add_job.return_value = mock_job

            def set_scheduler():
                jobs_module.scheduler = mock_scheduler
                return mock_scheduler

            mock_start.side_effect = set_scheduler

            jobs_module.schedule_seasonal_reminders()

            mock_start.assert_called_once()


class TestFoodTipsJob:
    """Tests for food tips job functions."""

    @pytest.mark.asyncio
    async def test_generate_food_tip_for_user_success(self):
        """Test generating food tip for a user."""
        from fcp.scheduler.jobs import generate_food_tip_for_user

        mock_profile = {"preferences": {}}
        mock_tip = {"tip": "Try adding herbs!"}

        with (
            patch(
                "fcp.scheduler.jobs.get_taste_profile",
                new_callable=AsyncMock,
            ) as mock_get_profile,
            patch("fcp.scheduler.jobs.FreshnessAgent") as mock_agent_class,
            patch("fcp.scheduler.jobs.firestore_client") as mock_db,
        ):
            mock_get_profile.return_value = mock_profile
            mock_agent = MagicMock()
            mock_agent.generate_food_tip_of_day = AsyncMock(return_value=mock_tip)
            mock_agent_class.return_value = mock_agent
            mock_db.store_notification = AsyncMock()

            result = await generate_food_tip_for_user("user123")

            assert result == mock_tip

    @pytest.mark.asyncio
    async def test_generate_food_tip_for_user_failure(self):
        """Test handling failure in food tip generation."""
        from fcp.scheduler.jobs import generate_food_tip_for_user

        with patch(
            "fcp.scheduler.jobs.get_taste_profile",
            new_callable=AsyncMock,
        ) as mock_get_profile:
            mock_get_profile.side_effect = Exception("Error")

            result = await generate_food_tip_for_user("user123")

            assert result is None

    @pytest.mark.asyncio
    async def test_run_food_tips_job(self):
        """Test running food tips for all users."""
        from fcp.scheduler.jobs import run_food_tips_job

        mock_users = [{"id": "user1"}]
        mock_prefs = {"food_tips_enabled": True}

        with (
            patch(
                "fcp.scheduler.jobs.get_active_users",
                new_callable=AsyncMock,
            ) as mock_get_users,
            patch(
                "fcp.scheduler.jobs.get_user_preferences",
                new_callable=AsyncMock,
            ) as mock_get_prefs,
            patch(
                "fcp.scheduler.jobs.generate_food_tip_for_user",
                new_callable=AsyncMock,
            ) as mock_generate,
            patch(
                "asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            mock_get_users.return_value = mock_users
            mock_get_prefs.return_value = mock_prefs
            mock_generate.return_value = {"tip": "test"}

            await run_food_tips_job()

            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_food_tips_job_skips_invalid_user_id(self):
        """Test that food tips skips users without valid string id."""
        from fcp.scheduler.jobs import run_food_tips_job

        mock_users = [{"id": None}, {"id": "valid_user"}]

        with (
            patch(
                "fcp.scheduler.jobs.get_active_users",
                new_callable=AsyncMock,
            ) as mock_get_users,
            patch(
                "fcp.scheduler.jobs.get_user_preferences",
                new_callable=AsyncMock,
            ) as mock_get_prefs,
            patch(
                "fcp.scheduler.jobs.generate_food_tip_for_user",
                new_callable=AsyncMock,
            ) as mock_generate,
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_get_users.return_value = mock_users
            mock_get_prefs.return_value = {"food_tips_enabled": True}
            mock_generate.return_value = {"tip": "test"}

            await run_food_tips_job()

            assert mock_generate.call_count == 1
            mock_generate.assert_called_with("valid_user")

    @pytest.mark.asyncio
    async def test_run_food_tips_job_respects_preferences(self):
        """Test that food tips respects user preferences."""
        from fcp.scheduler.jobs import run_food_tips_job

        mock_users = [{"id": "user1"}]

        with (
            patch(
                "fcp.scheduler.jobs.get_active_users",
                new_callable=AsyncMock,
            ) as mock_get_users,
            patch(
                "fcp.scheduler.jobs.get_user_preferences",
                new_callable=AsyncMock,
            ) as mock_get_prefs,
            patch(
                "fcp.scheduler.jobs.generate_food_tip_for_user",
                new_callable=AsyncMock,
            ) as mock_generate,
            patch(
                "asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            mock_get_users.return_value = mock_users
            mock_get_prefs.return_value = {"food_tips_enabled": False}

            await run_food_tips_job()

            mock_generate.assert_not_called()

    def test_schedule_food_tips(self):
        """Test scheduling food tips job."""
        import fcp.scheduler.jobs as jobs_module

        mock_scheduler = MagicMock()
        mock_job = MagicMock()
        mock_job.id = "food_tips"
        mock_scheduler.add_job.return_value = mock_job
        jobs_module.scheduler = mock_scheduler

        job_id = jobs_module.schedule_food_tips(hour=12)

        assert job_id == "food_tips"

    def test_schedule_food_tips_starts_scheduler_if_needed(self):
        """Test that scheduling starts scheduler if not running."""
        import fcp.scheduler.jobs as jobs_module

        jobs_module.scheduler = None

        with patch("fcp.scheduler.jobs.start_scheduler") as mock_start:
            mock_scheduler = MagicMock()
            mock_job = MagicMock()
            mock_job.id = "food_tips"
            mock_scheduler.add_job.return_value = mock_job

            def set_scheduler():
                jobs_module.scheduler = mock_scheduler
                return mock_scheduler

            mock_start.side_effect = set_scheduler

            jobs_module.schedule_food_tips()

            mock_start.assert_called_once()


class TestInitializeAllSchedules:
    """Tests for initialize_all_schedules function."""

    def test_initialize_all_schedules(self):
        """Test initializing all scheduled jobs."""
        import fcp.scheduler.jobs as jobs_module

        with (
            patch.object(jobs_module, "schedule_daily_insights") as mock_daily,
            patch.object(jobs_module, "schedule_weekly_digests") as mock_weekly,
            patch.object(jobs_module, "schedule_streak_checks") as mock_streak,
            patch.object(jobs_module, "schedule_seasonal_reminders") as mock_seasonal,
            patch.object(jobs_module, "schedule_food_tips") as mock_tips,
        ):
            mock_daily.return_value = "daily_insights"
            mock_weekly.return_value = "weekly_digests"
            mock_streak.return_value = "streak_checks"
            mock_seasonal.return_value = "seasonal_reminders"
            mock_tips.return_value = "food_tips"

            result = jobs_module.initialize_all_schedules()

            assert len(result) == 5
            assert result["daily_insights"] == "daily_insights"
            assert result["weekly_digests"] == "weekly_digests"
            assert result["streak_checks"] == "streak_checks"
            assert result["seasonal_reminders"] == "seasonal_reminders"
            assert result["food_tips"] == "food_tips"
