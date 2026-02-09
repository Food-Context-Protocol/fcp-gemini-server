"""Tests for scheduler lazy import functions."""

import sys
from unittest.mock import patch


class TestIsSchedulerAvailable:
    """Tests for api.py _is_scheduler_available."""

    def test_scheduler_available_when_installed(self):
        from fcp.api import _is_scheduler_available

        # Since fcp.scheduler exists in this codebase, it should be available
        assert _is_scheduler_available() is True

    def test_scheduler_unavailable_when_not_installed(self):
        from fcp.api import _is_scheduler_available

        with patch.dict(sys.modules, {"fcp.scheduler": None}):
            assert _is_scheduler_available() is False


class TestGetSchedulerModule:
    """Tests for scheduler.py _get_scheduler_module."""

    def test_returns_scheduler_when_available(self):
        from fcp.routes.scheduler import _get_scheduler_module

        scheduler, available = _get_scheduler_module()
        assert available is True

    def test_returns_none_when_unavailable(self):
        from fcp.routes.scheduler import _get_scheduler_module

        with patch.dict(sys.modules, {"fcp.scheduler": None, "fcp.scheduler.jobs": None}):
            scheduler, available = _get_scheduler_module()
            assert available is False
            assert scheduler is None


class TestGetSchedulerFunctions:
    """Tests for scheduler.py _get_scheduler_functions."""

    def test_returns_all_functions(self):
        from fcp.routes.scheduler import _get_scheduler_functions

        fns = _get_scheduler_functions()
        assert "schedule_daily_insights" in fns
        assert "schedule_seasonal_reminders" in fns
        assert "schedule_streak_checks" in fns
        assert "schedule_weekly_digests" in fns
        assert all(callable(fn) for fn in fns.values())
