"""Profile Routes.

User taste profile endpoints:
- Get taste profile
- Stream taste profile generation
- Lifetime analysis with 1M context window

Security: User-provided data is sanitized before inclusion in prompts
to prevent prompt injection attacks.
"""

import logging
import re
import time
from typing import Any

from fastapi import Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from fcp.auth import AuthenticatedUser, get_current_user
from fcp.routes.router import APIRouter
from fcp.security.input_sanitizer import sanitize_user_input
from fcp.security.rate_limit import RATE_LIMIT_PROFILE, limiter
from fcp.services.firestore import firestore_client
from fcp.services.gemini import GeminiClient, get_gemini
from fcp.tools import get_meals, get_taste_profile

# Valid period values for profile endpoints
VALID_PERIODS = {"all_time", "week", "month", "year"}
_PERIOD_PATTERN = re.compile(r"^(all_time|week|month|year)$")


def _validate_period(period: str) -> str:
    """Validate period parameter to prevent injection."""
    if not _PERIOD_PATTERN.match(period):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period '{period}'. Must be one of: {', '.join(sorted(VALID_PERIODS))}",
        )
    return period


def _sanitize_meal_for_prompt(meal: dict) -> str:
    """
    Sanitize a meal entry for safe inclusion in prompts.

    Returns a sanitized string representation of the meal.
    """
    dish_name = sanitize_user_input(
        meal.get("dish_name", "Unknown"),
        max_length=200,
        field_name="dish_name",
    )
    cuisine = sanitize_user_input(
        meal.get("cuisine", "Unknown cuisine"),
        max_length=100,
        field_name="cuisine",
    )
    return f"- {dish_name} ({cuisine})"


def _sanitize_meals_for_lifetime_analysis(meals: list[dict]) -> str:
    """
    Sanitize a list of meals for lifetime analysis prompts.

    Returns a sanitized string representation of all meals.
    """
    sanitized_entries = []
    for meal in meals:
        dish_name = sanitize_user_input(
            meal.get("dish_name", "Unknown"),
            max_length=200,
            field_name="dish_name",
        )
        cuisine = sanitize_user_input(
            meal.get("cuisine", "Unknown cuisine"),
            max_length=100,
            field_name="cuisine",
        )
        venue = sanitize_user_input(
            meal.get("venue", ""),
            max_length=200,
            field_name="venue",
        )
        timestamp = meal.get("timestamp", "Unknown date")
        entry = f"- {dish_name} ({cuisine})"
        if venue:
            entry += f" at {venue}"
        if timestamp and timestamp != "Unknown date":
            entry += f" [{timestamp}]"
        sanitized_entries.append(entry)
    return "\n".join(sanitized_entries)


router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================
# Lifetime Analysis Cache
# ============================================
# Simple TTL cache for expensive lifetime analysis
# Key: user_id, Value: (timestamp, result)
_lifetime_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_LIFETIME_CACHE_TTL = 3600  # 1 hour
_ANALYSIS_LIMIT = 2000  # Max meals to analyze (memory safety for power users)


# --- Routes ---


@router.get("/profile")
@limiter.limit(RATE_LIMIT_PROFILE)
async def taste_profile(
    request: Request,
    period: str = "all_time",
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get user's taste profile."""
    _validate_period(period)
    profile = await get_taste_profile(user.user_id, period)
    return {"profile": profile}


@router.get("/profile/stream")
@limiter.limit(RATE_LIMIT_PROFILE)
async def taste_profile_stream(
    request: Request,
    period: str = "all_time",
    user: AuthenticatedUser = Depends(get_current_user),
    gemini: GeminiClient = Depends(get_gemini),
):
    """
    Stream taste profile generation.

    Uses Gemini's 1M token context to analyze full food history and
    stream the profile analysis in real-time.
    """
    _validate_period(period)

    async def generate():
        # Load user's food history
        meals = await get_meals(user.user_id, limit=100)  # Get lots of history

        # Build context for Gemini with sanitized meal data
        meal_summaries = [_sanitize_meal_for_prompt(m) for m in meals]
        history = "\n".join(meal_summaries)

        prompt = f"""Based on this food history, analyze the user's taste profile.
Include: favorite cuisines, dietary patterns, flavor preferences, eating habits.
Be conversational and insightful.

Food History:
{history}
"""
        async for chunk in gemini.generate_content_stream(prompt):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/profile/lifetime")
@limiter.limit(RATE_LIMIT_PROFILE)
async def get_lifetime_profile(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=100, ge=10, le=500, description="Items per page"),
    refresh: bool = Query(default=False, description="Bypass cache and re-analyze"),
    gemini: GeminiClient = Depends(get_gemini),
) -> dict[str, Any]:
    """
    Analyze user's complete food history using 1M context window.

    Provides deep insights across entire food journey:
    - Long-term dietary evolution
    - Seasonal patterns over years
    - Life event correlations
    - Adventurousness progression

    Supports pagination for data fetching and caches analysis results.
    Use refresh=true to force re-analysis.
    """
    # Check cache first (only for page 1, unless refresh requested)
    # Cache is only valid for page 1 since pagination data is embedded in the cached response
    cache_key = user.user_id
    if page == 1 and not refresh and cache_key in _lifetime_cache:
        cached_time, cached_result = _lifetime_cache[cache_key]
        if time.time() - cached_time < _LIFETIME_CACHE_TTL:
            # Update pagination in cached result to match current request's page_size
            cached_with_pagination = {**cached_result}
            # Recalculate pagination for current page_size
            total_count = cached_result.get("total_entries", 0)
            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
            cached_with_pagination["pagination"] = {
                "page": 1,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_more": total_pages > 1,
            }
            cached_with_pagination["cached"] = True
            logger.info(f"Returning cached lifetime analysis for user {user.user_id}")
            return cached_with_pagination

    # Get paginated meals with total count
    meals, total_count = await firestore_client.get_user_logs_paginated(user.user_id, page=page, page_size=page_size)

    # Calculate pagination metadata
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
    has_more = page < total_pages

    if page != 1 and not refresh:
        # For subsequent pages, just return the paginated data without re-analysis
        return {
            "meals": meals,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_more": has_more,
            },
            "note": "Analysis is only performed on page 1. Use page=1 or refresh=true to get analysis.",
        }
    all_meals = await firestore_client.get_all_user_logs(user.user_id, limit=_ANALYSIS_LIMIT)
    analyzed_count = len(all_meals)
    is_capped = total_count > _ANALYSIS_LIMIT

    history_label = "Most Recent Entries" if is_capped else "Complete History"
    insights_basis = f"their most recent {analyzed_count} meals" if is_capped else "their complete history"

    # Sanitize meal data before including in prompt to prevent injection
    sanitized_history = _sanitize_meals_for_lifetime_analysis(all_meals)

    prompt = f"""Analyze this user's food history ({analyzed_count} entries{f" of {total_count} total" if is_capped else ""}).

Identify:
1. Long-term dietary evolution (how eating changed over time)
2. Seasonal patterns (summer vs winter preferences)
3. Cuisine exploration journey (how adventurous they've become)
4. Recurring favorites vs one-time tries
5. Health trend indicators

Provide actionable insights based on {insights_basis}.

{history_label}:
{sanitized_history}"""

    result = await gemini.generate_json_with_large_context(prompt)

    # Cache the analysis result
    response = {
        "lifetime_analysis": result,
        "analyzed_entries": analyzed_count,
        "total_entries": total_count,
        "analysis_capped": is_capped,
        "analysis_limit": _ANALYSIS_LIMIT if is_capped else None,
        "method": "1m_context",
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_more": has_more,
        },
        "cached": False,
    }
    _lifetime_cache[cache_key] = (time.time(), response)
    return response


# Export cache for testing
def clear_lifetime_cache():
    """Clear the lifetime analysis cache (for testing)."""
    _lifetime_cache.clear()


def get_lifetime_cache_size() -> int:
    """Get current cache size (for testing/monitoring)."""
    return len(_lifetime_cache)
