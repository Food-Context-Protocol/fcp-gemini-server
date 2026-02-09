"""Nutrition analytics with Gemini Code Execution.

This module provides data analysis capabilities using Gemini's
code execution feature. Gemini writes and runs Python code to:
- Calculate nutrition statistics
- Analyze eating patterns
- Generate trend reports
- Create data visualizations

Security: User-provided text fields in food logs (dish_name, cuisine, venue,
notes, cooking_method) are sanitized before inclusion in prompts to prevent
prompt injection attacks. Numeric and structured fields pass through unchanged.
"""

import json
from typing import Any

from fcp.security.input_sanitizer import sanitize_user_input
from fcp.services.gemini import gemini

# Text fields in food logs that should be sanitized (user-provided content)
_SANITIZE_FIELDS = ("dish_name", "cuisine", "venue", "notes", "cooking_method")

# Valid metric values for trend analysis
_VALID_METRICS = {"calories", "protein", "carbs", "fat", "fiber", "sodium", "sugar"}


def _sanitize_food_logs(food_logs: list[dict]) -> list[dict]:
    """
    Sanitize food log entries to prevent prompt injection.

    Sanitizes user-provided text fields that could contain malicious content.
    See _SANITIZE_FIELDS for the list of fields.

    Numeric and structured fields (nutrition, timestamps) are passed through.
    """
    sanitized = []
    for log in food_logs:
        safe_log = log.copy()
        # Sanitize text fields that come from user input
        for field in _SANITIZE_FIELDS:
            if field in safe_log and safe_log[field]:
                safe_log[field] = sanitize_user_input(
                    safe_log[field],
                    max_length=500,
                    field_name=field,
                )
        sanitized.append(safe_log)
    return sanitized


def _validate_metric(metric: str) -> str:
    """
    Validate metric parameter to prevent injection.

    Args:
        metric: The metric to validate

    Returns:
        The validated metric

    Raises:
        ValueError: If metric is not in the allowed list
    """
    if metric.lower() not in _VALID_METRICS:
        raise ValueError(f"Invalid metric '{metric}'. Must be one of: {', '.join(sorted(_VALID_METRICS))}")
    return metric.lower()


async def calculate_nutrition_stats(
    food_logs: list[dict],
    period: str = "week",
) -> dict[str, Any]:
    """
    Calculate nutrition statistics from food logs.

    Uses Gemini Code Execution to run Python calculations on the data.

    Args:
        food_logs: List of food log entries with nutrition data
        period: Time period label for the analysis

    Returns:
        dict with calculated statistics and the code used
    """
    # Sanitize user-provided fields to prevent prompt injection
    safe_logs = _sanitize_food_logs(food_logs)

    prompt = f"""Analyze this nutrition data and calculate comprehensive statistics.

Data ({len(safe_logs)} entries, {period}):
{json.dumps(safe_logs, indent=2)}

Write Python code to calculate:
1. Total and average daily calories
2. Average daily macros (protein, carbs, fat in grams)
3. Macronutrient ratio (% of calories from each macro)
4. Standard deviation of daily calories
5. Highest and lowest calorie days
6. Most frequent foods/dishes

Use pandas if helpful. Print the results in a clear format."""

    result = await gemini.generate_with_code_execution(prompt)

    return {
        "period": period,
        "entry_count": len(food_logs),
        "analysis": result["text"],
        "code_executed": result["code"],
        "raw_output": result["execution_result"],
    }


async def analyze_eating_patterns(
    food_logs: list[dict],
) -> dict[str, Any]:
    """
    Analyze eating patterns and habits from food logs.

    Uses code execution to identify patterns in:
    - Meal timing
    - Cuisine preferences over time
    - Weekend vs weekday eating
    - Venue frequency

    Args:
        food_logs: List of food log entries

    Returns:
        dict with pattern analysis
    """
    # Sanitize user-provided fields to prevent prompt injection
    safe_logs = _sanitize_food_logs(food_logs)

    prompt = f"""Analyze eating patterns in this food log data.

Data ({len(safe_logs)} entries):
{json.dumps(safe_logs, indent=2)}

Write Python code to analyze:
1. Meal timing patterns (what time do they usually eat)
2. Day of week patterns (weekend vs weekday differences)
3. Cuisine distribution over time
4. Home cooking vs restaurant ratio
5. Favorite venues (most visited)
6. Food variety score (unique dishes / total meals)

Create clear statistics and identify notable patterns."""

    result = await gemini.generate_with_code_execution(prompt)

    return {
        "entry_count": len(food_logs),
        "pattern_analysis": result["text"],
        "code_executed": result["code"],
        "raw_output": result["execution_result"],
    }


async def calculate_trend_report(
    food_logs: list[dict],
    metric: str = "calories",
) -> dict[str, Any]:
    """
    Calculate trends over time for a nutrition metric.

    Uses code execution to perform time series analysis.

    Args:
        food_logs: List of food log entries (should span multiple weeks)
        metric: Metric to analyze (calories, protein, carbs, fat, fiber, sodium, sugar)

    Returns:
        dict with trend analysis

    Raises:
        ValueError: If metric is not in the allowed list
    """
    # Validate metric parameter to prevent injection
    safe_metric = _validate_metric(metric)

    # Sanitize user-provided fields to prevent prompt injection
    safe_logs = _sanitize_food_logs(food_logs)

    prompt = f"""Analyze the trend of {safe_metric} over time in this food data.

Data ({len(safe_logs)} entries):
{json.dumps(safe_logs, indent=2)}

Write Python code to:
1. Group data by week
2. Calculate weekly averages for {safe_metric}
3. Determine if the trend is increasing, decreasing, or stable
4. Calculate week-over-week change percentages
5. Identify any significant spikes or dips
6. Provide a linear regression trend line if there's enough data

Print a clear trend summary with numbers."""

    result = await gemini.generate_with_code_execution(prompt)

    return {
        "metric": safe_metric,
        "entry_count": len(food_logs),
        "trend_analysis": result["text"],
        "code_executed": result["code"],
        "raw_output": result["execution_result"],
    }


async def compare_periods(
    period1_logs: list[dict],
    period2_logs: list[dict],
    period1_name: str = "Period 1",
    period2_name: str = "Period 2",
) -> dict[str, Any]:
    """
    Compare nutrition between two time periods.

    Uses code execution to calculate differences and improvements.

    Args:
        period1_logs: Food logs from first period
        period2_logs: Food logs from second period
        period1_name: Label for first period
        period2_name: Label for second period

    Returns:
        dict with comparison analysis
    """
    # Sanitize user-provided fields to prevent prompt injection
    safe_logs1 = _sanitize_food_logs(period1_logs)
    safe_logs2 = _sanitize_food_logs(period2_logs)

    prompt = f"""Compare nutrition between two time periods.

{period1_name} ({len(safe_logs1)} entries):
{json.dumps(safe_logs1, indent=2)}

{period2_name} ({len(safe_logs2)} entries):
{json.dumps(safe_logs2, indent=2)}

Write Python code to compare:
1. Average daily calories (and % change)
2. Macronutrient averages (and % change)
3. Food variety (unique dishes)
4. Cuisine diversity
5. Eating frequency patterns

Highlight improvements and areas of concern. Use clear formatting."""

    result = await gemini.generate_with_code_execution(prompt)

    return {
        "period1": {"name": period1_name, "entries": len(period1_logs)},
        "period2": {"name": period2_name, "entries": len(period2_logs)},
        "comparison": result["text"],
        "code_executed": result["code"],
        "raw_output": result["execution_result"],
    }


async def generate_nutrition_report(
    food_logs: list[dict],
    user_goals: dict | None = None,
) -> dict[str, Any]:
    """
    Generate a comprehensive nutrition report.

    Uses code execution for detailed calculations and analysis.

    Args:
        food_logs: List of food log entries
        user_goals: Optional dict with user's nutrition goals

    Returns:
        dict with comprehensive report
    """
    # Sanitize user-provided fields to prevent prompt injection
    safe_logs = _sanitize_food_logs(food_logs)

    goals_str = ""
    if user_goals:
        goals_str = f"""
User's nutrition goals:
{json.dumps(user_goals, indent=2)}

Compare actual intake against these goals."""

    prompt = f"""Generate a comprehensive nutrition report from this food log data.

Data ({len(safe_logs)} entries):
{json.dumps(safe_logs, indent=2)}
{goals_str}

Write Python code to create a full report including:

1. SUMMARY STATISTICS
   - Total days tracked
   - Average daily intake (calories, protein, carbs, fat)
   - Consistency score (how regular is their logging)

2. MACRO ANALYSIS
   - Macronutrient breakdown (grams and percentages)
   - Comparison to recommended ranges (if goals provided)
   - Balance assessment

3. EATING HABITS
   - Most common foods/dishes
   - Cuisine variety
   - Meal timing patterns
   - Home vs restaurant ratio

4. TRENDS
   - Week-over-week calorie trend
   - Any notable changes in eating patterns

5. RECOMMENDATIONS
   - Based on the data, suggest 2-3 actionable improvements

Format the output as a clear, readable report."""

    result = await gemini.generate_with_code_execution(prompt)

    return {
        "report_type": "comprehensive_nutrition",
        "entry_count": len(food_logs),
        "has_goals": user_goals is not None,
        "report": result["text"],
        "code_executed": result["code"],
        "raw_output": result["execution_result"],
    }


async def calculate_macro_targets(
    current_logs: list[dict],
    goal: str,
    body_weight_kg: float | None = None,
) -> dict[str, Any]:
    """
    Calculate recommended macro targets based on a goal.

    Uses code execution to calculate personalized targets.

    Args:
        current_logs: Recent food logs to understand current intake
        goal: Goal type (maintain, lose_weight, gain_muscle, etc.)
        body_weight_kg: Optional body weight for protein calculations

    Returns:
        dict with recommended macro targets
    """
    # Sanitize user-provided fields to prevent prompt injection
    safe_logs = _sanitize_food_logs(current_logs)

    weight_str = ""
    if body_weight_kg:
        weight_str = f"User's body weight: {body_weight_kg} kg"

    prompt = f"""Calculate recommended macro targets based on this data and goal.

Current eating data ({len(safe_logs)} entries):
{json.dumps(safe_logs, indent=2)}

Goal: {goal}
{weight_str}

Write Python code to:

1. Calculate current average daily intake
2. Based on the goal "{goal}", recommend:
   - Daily calorie target
   - Protein target (g and % of calories)
   - Carb target (g and % of calories)
   - Fat target (g and % of calories)

Use these guidelines:
- Maintain: Keep current if balanced, adjust if not
- Lose weight: Moderate deficit (300-500 cal below maintenance)
- Gain muscle: Slight surplus + higher protein (1.6-2.2g/kg if weight provided)
- Performance: Higher carbs, adequate protein

Explain the reasoning behind each recommendation."""

    result = await gemini.generate_with_code_execution(prompt)

    return {
        "goal": goal,
        "body_weight_kg": body_weight_kg,
        "current_entries": len(current_logs),
        "recommendations": result["text"],
        "code_executed": result["code"],
        "raw_output": result["execution_result"],
    }
