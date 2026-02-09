"""Scheduler Routes.

Background scheduler management endpoints:
- GET /scheduler/status - Get scheduler status and job list
- POST /scheduler/configure - Configure scheduled jobs
- POST /scheduler/trigger/{job_type} - Manually trigger a job
"""

from typing import Any

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, Field

from fcp.auth import AuthenticatedUser, get_current_user, require_write_access
from fcp.routes.router import APIRouter
from fcp.security.rate_limit import RATE_LIMIT_CRUD, limiter
from fcp.utils.background_tasks import create_tracked_task

router = APIRouter()


def _get_scheduler_module():
    """Lazy import of scheduler. Returns (scheduler_module, True) or (None, False)."""
    try:
        from fcp.scheduler.jobs import scheduler

        return scheduler, True
    except ImportError:
        return None, False


def _get_scheduler_functions():
    """Lazy import of scheduler configuration functions."""
    from fcp.scheduler import (
        schedule_daily_insights,
        schedule_seasonal_reminders,
        schedule_streak_checks,
        schedule_weekly_digests,
    )

    return {
        "schedule_daily_insights": schedule_daily_insights,
        "schedule_seasonal_reminders": schedule_seasonal_reminders,
        "schedule_streak_checks": schedule_streak_checks,
        "schedule_weekly_digests": schedule_weekly_digests,
    }


# --- Request Models ---


class ScheduleUpdateRequest(BaseModel):
    job_type: str = Field(..., pattern=r"^(daily_insights|weekly_digests|streak_checks|seasonal_reminders|food_tips)$")
    enabled: bool = Field(default=True)
    hour: int | None = Field(default=None, ge=0, le=23)
    minute: int | None = Field(default=None, ge=0, le=59)
    day_of_week: str | None = Field(default=None, pattern=r"^(mon|tue|wed|thu|fri|sat|sun)$")
    day_of_month: int | None = Field(default=None, ge=1, le=28)


# --- Routes ---


@router.get("/scheduler/status")
@limiter.limit(RATE_LIMIT_CRUD)
async def get_scheduler_status(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get the status of the background scheduler.

    Returns information about running jobs and their schedules.
    """
    scheduler, available = _get_scheduler_module()
    if not available:
        return {"status": "unavailable", "message": "Scheduler not installed"}

    if scheduler is None:
        return {"status": "stopped", "jobs": []}

    jobs = [
        {
            "id": job.id,
            "name": job.name,
            "next_run": (job.next_run_time.isoformat() if job.next_run_time else None),
            "trigger": str(job.trigger),
        }
        for job in scheduler.get_jobs()
    ]
    return {
        "status": "running",
        "jobs": jobs,
    }


@router.post("/scheduler/configure")
@limiter.limit(RATE_LIMIT_CRUD)
async def configure_schedule(
    request: Request,
    schedule_request: ScheduleUpdateRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """
    Configure a scheduled job.

    Allows updating the schedule for background agent jobs.
    Note: This is an admin endpoint - in production, add proper authorization.
    """
    scheduler, available = _get_scheduler_module()
    if not available:
        raise HTTPException(status_code=503, detail="Scheduler not available")

    job_type = schedule_request.job_type

    if not schedule_request.enabled:
        if scheduler:
            scheduler.remove_job(job_type)
        return {"status": "disabled", "job": job_type}

    fns = _get_scheduler_functions()

    def _schedule_daily_insights() -> str:
        hour = schedule_request.hour or 8
        minute = schedule_request.minute or 0
        return fns["schedule_daily_insights"](hour=hour, minute=minute)

    def _schedule_weekly_digests() -> str:
        day = schedule_request.day_of_week or "sun"
        hour = schedule_request.hour or 10
        return fns["schedule_weekly_digests"](day_of_week=day, hour=hour)

    def _schedule_streak_checks() -> str:
        hour = schedule_request.hour or 0
        minute = schedule_request.minute or 5
        return fns["schedule_streak_checks"](hour=hour, minute=minute)

    def _schedule_seasonal_reminders() -> str:
        day = schedule_request.day_of_month or 1
        hour = schedule_request.hour or 9
        return fns["schedule_seasonal_reminders"](day=day, hour=hour)

    def _schedule_food_tips() -> str:
        from fcp.scheduler.jobs import schedule_food_tips

        hour = schedule_request.hour or 12
        return schedule_food_tips(hour=hour)

    handlers = {
        "daily_insights": _schedule_daily_insights,
        "weekly_digests": _schedule_weekly_digests,
        "streak_checks": _schedule_streak_checks,
        "seasonal_reminders": _schedule_seasonal_reminders,
        "food_tips": _schedule_food_tips,
    }

    job_id = handlers[job_type]()
    return {"status": "updated", "job": job_type, "job_id": job_id}


@router.post("/scheduler/trigger/{job_type}")
@limiter.limit(RATE_LIMIT_CRUD)
async def trigger_job_manually(
    request: Request,
    job_type: str,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """
    Manually trigger a scheduled job to run immediately.

    Useful for testing or on-demand generation.
    """
    _, available = _get_scheduler_module()
    if not available:
        raise HTTPException(status_code=503, detail="Scheduler not available")

    from fcp.scheduler.jobs import (
        run_daily_insights_job,
        run_food_tips_job,
        run_seasonal_reminders_job,
        run_streak_checks_job,
        run_weekly_digests_job,
    )

    job_map = {
        "daily_insights": run_daily_insights_job,
        "weekly_digests": run_weekly_digests_job,
        "streak_checks": run_streak_checks_job,
        "seasonal_reminders": run_seasonal_reminders_job,
        "food_tips": run_food_tips_job,
    }

    if job_type not in job_map:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown job type. Valid types: {list(job_map.keys())}",
        )

    # Run the job in the background with proper tracking
    task = create_tracked_task(job_map[job_type](), name=f"manual_job_{job_type}")

    return {
        "status": "triggered",
        "job": job_type,
        "task_id": task.get_name(),
        "message": f"Job {job_type} triggered and running in background",
    }
