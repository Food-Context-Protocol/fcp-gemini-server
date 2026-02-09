"""Analytics Routes.

Nutrition analytics endpoints using Gemini code execution:
- POST /analytics/nutrition - Calculate nutrition statistics
- POST /analytics/patterns - Analyze eating patterns
- POST /analytics/trends - Calculate nutrition trends
- POST /analytics/compare - Compare two time periods
- GET /analytics/report - Generate comprehensive nutrition report
"""

from typing import Any

from fastapi import Depends, Query, Request
from pydantic import BaseModel, Field

from fcp.auth import AuthenticatedUser, get_current_user, require_write_access
from fcp.routes.router import APIRouter
from fcp.security.rate_limit import RATE_LIMIT_PROFILE, limiter
from fcp.tools import get_meals
from fcp.tools.analytics import (
    analyze_eating_patterns,
    calculate_nutrition_stats,
    calculate_trend_report,
    compare_periods,
    generate_nutrition_report,
)

router = APIRouter()


# --- Request Models ---


class AnalyticsRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=365)


class ComparePeriodsRequest(BaseModel):
    period1_start: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    period1_end: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    period2_start: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    period2_end: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")


# --- Routes ---


@router.post("/analytics/nutrition")
@limiter.limit(RATE_LIMIT_PROFILE)
async def get_nutrition_analytics(
    request: Request,
    analytics_request: AnalyticsRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """
    Calculate nutrition statistics using Gemini code execution.

    Returns computed metrics:
    - Daily averages
    - Macronutrient ratios
    - Calorie trends
    """
    meals = await get_meals(user.user_id, days=analytics_request.days, include_nutrition=True)
    result = await calculate_nutrition_stats(meals)
    return {"stats": result, "period_days": analytics_request.days, "meal_count": len(meals)}


@router.post("/analytics/patterns")
@limiter.limit(RATE_LIMIT_PROFILE)
async def get_eating_patterns(
    request: Request,
    analytics_request: AnalyticsRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """
    Analyze eating patterns using code execution.

    Identifies:
    - Meal timing patterns
    - Cuisine preferences by day
    - Weekend vs weekday differences
    """
    meals = await get_meals(user.user_id, days=analytics_request.days, include_nutrition=True)
    result = await analyze_eating_patterns(meals)
    return {"patterns": result, "period_days": analytics_request.days}


@router.post("/analytics/trends")
@limiter.limit(RATE_LIMIT_PROFILE)
async def get_nutrition_trends(
    request: Request,
    analytics_request: AnalyticsRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """
    Calculate nutrition trends over time.

    Uses code execution to compute:
    - Week-over-week changes
    - Rolling averages
    - Trend direction
    """
    meals = await get_meals(user.user_id, days=analytics_request.days, include_nutrition=True)
    result = await calculate_trend_report(meals)
    return {"trends": result, "period_days": analytics_request.days}


@router.post("/analytics/compare")
@limiter.limit(RATE_LIMIT_PROFILE)
async def compare_nutrition_periods(
    request: Request,
    compare_request: ComparePeriodsRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> dict[str, Any]:
    """
    Compare nutrition between two time periods.

    Useful for:
    - Before/after diet changes
    - Seasonal comparisons
    - Progress tracking
    """
    from datetime import UTC, datetime

    # Parse dates
    p1_start = datetime.strptime(compare_request.period1_start, "%Y-%m-%d").replace(tzinfo=UTC)
    p1_end = datetime.strptime(compare_request.period1_end, "%Y-%m-%d").replace(
        hour=23, minute=59, second=59, microsecond=999999, tzinfo=UTC
    )
    p2_start = datetime.strptime(compare_request.period2_start, "%Y-%m-%d").replace(tzinfo=UTC)
    p2_end = datetime.strptime(compare_request.period2_end, "%Y-%m-%d").replace(
        hour=23, minute=59, second=59, microsecond=999999, tzinfo=UTC
    )

    # Get meals for both periods separately
    period1_logs = await get_meals(
        user.user_id, limit=1000, include_nutrition=True, start_date=p1_start, end_date=p1_end
    )
    period2_logs = await get_meals(
        user.user_id, limit=1000, include_nutrition=True, start_date=p2_start, end_date=p2_end
    )

    result = await compare_periods(
        period1_logs,
        period2_logs,
        period1_name=f"{compare_request.period1_start} to {compare_request.period1_end}",
        period2_name=f"{compare_request.period2_start} to {compare_request.period2_end}",
    )
    return {"comparison": result}


@router.get("/analytics/report")
@limiter.limit(RATE_LIMIT_PROFILE)
async def get_nutrition_report(
    request: Request,
    days: int = Query(default=30, ge=7, le=365),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Generate a comprehensive nutrition report.

    Combines multiple analyses into a single report.
    """
    meals = await get_meals(user.user_id, days=days, include_nutrition=True)
    result = await generate_nutrition_report(meals)
    return {"report": result, "period_days": days, "meal_count": len(meals)}
