"""Background Scheduler for FCP Agents.

Runs agents on schedules for proactive user engagement:
- Daily insights at user's preferred time
- Weekly digests every Sunday
- Streak celebrations when milestones are hit
- Seasonal reminders at month changes
"""

from fcp.scheduler.jobs import (
    schedule_daily_insights,
    schedule_seasonal_reminders,
    schedule_streak_checks,
    schedule_weekly_digests,
    start_scheduler,
    stop_scheduler,
)

__all__ = [
    "schedule_daily_insights",
    "schedule_weekly_digests",
    "schedule_streak_checks",
    "schedule_seasonal_reminders",
    "start_scheduler",
    "stop_scheduler",
]
