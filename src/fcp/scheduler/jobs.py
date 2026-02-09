"""Scheduled Jobs for FCP Agents.

Uses APScheduler for background task scheduling.
Jobs can be configured per-user or system-wide.
"""

import asyncio
import logging
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from fcp.agents import ContentGeneratorAgent, FreshnessAgent
from fcp.services.firestore import firestore_client, get_firestore_status
from fcp.tools import get_meals, get_taste_profile

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> AsyncIOScheduler:
    """Start the background scheduler."""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler()
        scheduler.start()
        logger.info("Background scheduler started")
    return scheduler


def stop_scheduler() -> None:
    """Stop the background scheduler."""
    global scheduler
    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("Background scheduler stopped")


async def get_active_users() -> list[dict[str, Any]]:
    """Get list of users who have been active recently."""
    # This would query Firestore for users with recent activity
    # For now, return empty list - implement based on your user schema
    return await firestore_client.get_active_users(days=7)


async def get_user_preferences(user_id: str) -> dict[str, Any]:
    """Get user's notification preferences."""
    return await firestore_client.get_user_preferences(user_id)


def _firestore_ready() -> tuple[bool, str | None]:
    """Return whether Firestore is initialized and available."""
    status = get_firestore_status()
    available = bool(status.get("available") and status.get("initialized"))
    return available, status.get("error")


# --- Daily Insights Job ---


async def generate_daily_insight_for_user(user_id: str) -> dict[str, Any] | None:
    """Generate and store a daily insight for a single user."""
    try:
        profile = await get_taste_profile(user_id)
        recent_logs = await get_meals(user_id, days=7)

        # Get user's location if available
        prefs = await get_user_preferences(user_id)
        location = prefs.get("location")

        agent = FreshnessAgent(user_id)
        insight = await agent.generate_daily_insight(
            taste_profile=profile,
            recent_logs=recent_logs,
            location=location,
        )

        # Store the insight for the user
        await firestore_client.store_notification(
            user_id=user_id,
            notification_type="daily_insight",
            content=insight,
        )

        logger.info(f"Generated daily insight for user {user_id}")
        return insight

    except Exception as e:
        logger.error(f"Failed to generate daily insight for user {user_id}: {e}")
        return None


async def run_daily_insights_job():
    """Run daily insights for all active users."""
    ready, reason = _firestore_ready()
    if not ready:
        logger.warning("Skipping daily insights job because Firestore unavailable: %s", reason or "unknown error")
        return

    logger.info("Starting daily insights job")
    users = await get_active_users()

    for user in users:
        user_id = user.get("id")
        if not isinstance(user_id, str):
            continue

        prefs = await get_user_preferences(user_id)

        # Check if user wants daily insights
        if prefs.get("daily_insights_enabled", True):
            await generate_daily_insight_for_user(user_id)
            # Small delay to avoid overwhelming the API
            await asyncio.sleep(0.5)

    logger.info(f"Completed daily insights for {len(users)} users")


def schedule_daily_insights(hour: int = 8, minute: int = 0) -> str:
    """
    Schedule daily insights to run at a specific time.

    Args:
        hour: Hour to run (0-23), default 8 AM
        minute: Minute to run (0-59), default 0

    Returns:
        Job ID for the scheduled job
    """
    global scheduler
    if scheduler is None:
        start_scheduler()
    assert scheduler is not None

    job = scheduler.add_job(
        run_daily_insights_job,
        CronTrigger(hour=hour, minute=minute),
        id="daily_insights",
        replace_existing=True,
        name="Daily Insights Generator",
    )
    logger.info(f"Scheduled daily insights at {hour:02d}:{minute:02d}")
    return job.id


# --- Weekly Digest Job ---


async def generate_weekly_digest_for_user(user_id: str) -> dict[str, Any] | None:
    """Generate and store a weekly digest for a single user."""
    try:
        food_logs = await get_meals(user_id, days=7)

        if len(food_logs) < 3:
            # Not enough data for a meaningful digest
            logger.info(f"Skipping weekly digest for user {user_id} - insufficient data")
            return None

        prefs = await get_user_preferences(user_id)
        user_name = prefs.get("display_name")

        agent = ContentGeneratorAgent(user_id)
        digest = await agent.generate_weekly_digest(
            food_logs=food_logs,
            user_name=user_name,
        )

        # Store the digest
        await firestore_client.store_notification(
            user_id=user_id,
            notification_type="weekly_digest",
            content=digest,
        )

        logger.info(f"Generated weekly digest for user {user_id}")
        return digest

    except Exception as e:
        logger.error(f"Failed to generate weekly digest for user {user_id}: {e}")
        return None


async def run_weekly_digests_job():
    """Run weekly digests for all active users."""
    ready, reason = _firestore_ready()
    if not ready:
        logger.warning("Skipping weekly digests job because Firestore unavailable: %s", reason or "unknown error")
        return

    logger.info("Starting weekly digests job")
    users = await get_active_users()

    for user in users:
        user_id = user.get("id")
        if not isinstance(user_id, str):
            continue

        prefs = await get_user_preferences(user_id)

        # Check if user wants weekly digests
        if prefs.get("weekly_digest_enabled", True):
            await generate_weekly_digest_for_user(user_id)
            await asyncio.sleep(1)  # Longer delay for heavier job

    logger.info(f"Completed weekly digests for {len(users)} users")


def schedule_weekly_digests(day_of_week: str = "sun", hour: int = 10) -> str:
    """
    Schedule weekly digests to run on a specific day.

    Args:
        day_of_week: Day to run (mon, tue, wed, thu, fri, sat, sun)
        hour: Hour to run (0-23)

    Returns:
        Job ID for the scheduled job
    """
    global scheduler
    if scheduler is None:
        start_scheduler()
    assert scheduler is not None

    job = scheduler.add_job(
        run_weekly_digests_job,
        CronTrigger(day_of_week=day_of_week, hour=hour),
        id="weekly_digests",
        replace_existing=True,
        name="Weekly Digest Generator",
    )
    logger.info(f"Scheduled weekly digests on {day_of_week} at {hour:02d}:00")
    return job.id


# --- Streak Check Job ---


async def check_and_celebrate_streak(user_id: str) -> dict[str, Any] | None:
    """Check user's streak and generate celebration if milestone hit."""
    try:
        stats = await firestore_client.get_user_stats(user_id)
        current_streak = stats.get("current_streak", 0)

        # Only celebrate certain milestones
        milestones = [3, 7, 14, 21, 30, 50, 75, 100, 150, 200, 365]

        if current_streak in milestones:
            prefs = await get_user_preferences(user_id)
            user_name = prefs.get("display_name")

            agent = FreshnessAgent(user_id)
            celebration = await agent.generate_streak_celebration(
                streak_days=current_streak,
                user_name=user_name,
            )

            # Store the celebration
            await firestore_client.store_notification(
                user_id=user_id,
                notification_type="streak_celebration",
                content=celebration,
            )

            logger.info(f"Generated streak celebration for user {user_id} ({current_streak} days)")
            return celebration

        return None

    except Exception as e:
        logger.error(f"Failed to check streak for user {user_id}: {e}")
        return None


async def run_streak_checks_job():
    """Check streaks for all active users."""
    ready, reason = _firestore_ready()
    if not ready:
        logger.warning("Skipping streak checks job because Firestore unavailable: %s", reason or "unknown error")
        return

    logger.info("Starting streak checks job")
    users = await get_active_users()

    for user in users:
        user_id = user.get("id")
        if not isinstance(user_id, str):
            continue

        await check_and_celebrate_streak(user_id)
        await asyncio.sleep(0.2)

    logger.info(f"Completed streak checks for {len(users)} users")


def schedule_streak_checks(hour: int = 0, minute: int = 5) -> str:
    """
    Schedule streak checks to run daily (just after midnight).

    Args:
        hour: Hour to run
        minute: Minute to run

    Returns:
        Job ID for the scheduled job
    """
    global scheduler
    if scheduler is None:
        start_scheduler()
    assert scheduler is not None

    job = scheduler.add_job(
        run_streak_checks_job,
        CronTrigger(hour=hour, minute=minute),
        id="streak_checks",
        replace_existing=True,
        name="Streak Checker",
    )
    logger.info(f"Scheduled streak checks at {hour:02d}:{minute:02d}")
    return job.id


# --- Seasonal Reminders Job ---


async def generate_seasonal_reminder_for_user(user_id: str) -> dict[str, Any] | None:
    """Generate seasonal food reminder for a user."""
    try:
        prefs = await get_user_preferences(user_id)
        location = prefs.get("location")

        if not location:
            logger.info(f"Skipping seasonal reminder for user {user_id} - no location")
            return None

        profile = await get_taste_profile(user_id)

        agent = FreshnessAgent(user_id)
        reminder = await agent.generate_seasonal_reminder(
            location=location,
            taste_profile=profile,
        )

        # Store the reminder
        await firestore_client.store_notification(
            user_id=user_id,
            notification_type="seasonal_reminder",
            content=reminder,
        )

        logger.info(f"Generated seasonal reminder for user {user_id}")
        return reminder

    except Exception as e:
        logger.error(f"Failed to generate seasonal reminder for user {user_id}: {e}")
        return None


async def run_seasonal_reminders_job():
    """Run seasonal reminders for all active users."""
    ready, reason = _firestore_ready()
    if not ready:
        logger.warning("Skipping seasonal reminders job because Firestore unavailable: %s", reason or "unknown error")
        return

    logger.info("Starting seasonal reminders job")
    users = await get_active_users()

    for user in users:
        user_id = user.get("id")
        if not isinstance(user_id, str):
            continue

        prefs = await get_user_preferences(user_id)

        # Check if user wants seasonal reminders
        if prefs.get("seasonal_reminders_enabled", True):
            await generate_seasonal_reminder_for_user(user_id)
            await asyncio.sleep(0.5)

    logger.info(f"Completed seasonal reminders for {len(users)} users")


def schedule_seasonal_reminders(day: int = 1, hour: int = 9) -> str:
    """
    Schedule seasonal reminders to run on the 1st of each month.

    Args:
        day: Day of month to run
        hour: Hour to run

    Returns:
        Job ID for the scheduled job
    """
    global scheduler
    if scheduler is None:
        start_scheduler()
    assert scheduler is not None

    job = scheduler.add_job(
        run_seasonal_reminders_job,
        CronTrigger(day=day, hour=hour),
        id="seasonal_reminders",
        replace_existing=True,
        name="Seasonal Reminder Generator",
    )
    logger.info(f"Scheduled seasonal reminders on day {day} at {hour:02d}:00")
    return job.id


# --- Food Tip Job ---


async def generate_food_tip_for_user(user_id: str) -> dict[str, Any] | None:
    """Generate daily food tip for a user."""
    try:
        profile = await get_taste_profile(user_id)

        agent = FreshnessAgent(user_id)
        tip = await agent.generate_food_tip_of_day(taste_profile=profile)

        # Store the tip
        await firestore_client.store_notification(
            user_id=user_id,
            notification_type="food_tip",
            content=tip,
        )

        logger.info(f"Generated food tip for user {user_id}")
        return tip

    except Exception as e:
        logger.error(f"Failed to generate food tip for user {user_id}: {e}")
        return None


async def run_food_tips_job():
    """Run food tips for all active users."""
    ready, reason = _firestore_ready()
    if not ready:
        logger.warning("Skipping food tips job because Firestore unavailable: %s", reason or "unknown error")
        return

    logger.info("Starting food tips job")
    users = await get_active_users()

    for user in users:
        user_id = user.get("id")
        if not isinstance(user_id, str):
            continue

        prefs = await get_user_preferences(user_id)

        if prefs.get("food_tips_enabled", True):
            await generate_food_tip_for_user(user_id)
            await asyncio.sleep(0.5)

    logger.info(f"Completed food tips for {len(users)} users")


def schedule_food_tips(hour: int = 12) -> str:
    """
    Schedule daily food tips at noon.

    Args:
        hour: Hour to run

    Returns:
        Job ID for the scheduled job
    """
    global scheduler
    if scheduler is None:
        start_scheduler()
    assert scheduler is not None

    job = scheduler.add_job(
        run_food_tips_job,
        CronTrigger(hour=hour),
        id="food_tips",
        replace_existing=True,
        name="Food Tip Generator",
    )
    logger.info(f"Scheduled food tips at {hour:02d}:00")
    return job.id


# --- Initialize All Schedules ---


def initialize_all_schedules() -> dict[str, str]:
    """
    Initialize all scheduled jobs with default settings.

    Returns:
        Dict mapping job names to job IDs
    """
    return {
        "daily_insights": schedule_daily_insights(hour=8),
        "weekly_digests": schedule_weekly_digests(day_of_week="sun", hour=10),
        "streak_checks": schedule_streak_checks(hour=0, minute=5),
        "seasonal_reminders": schedule_seasonal_reminders(day=1, hour=9),
        "food_tips": schedule_food_tips(hour=12),
    }
