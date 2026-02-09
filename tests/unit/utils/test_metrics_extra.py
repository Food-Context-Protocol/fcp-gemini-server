"""Coverage tests for metrics utilities."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from fcp.utils import metrics


def test_record_metric_functions():
    # Use real prometheus metrics but patch labels to avoid side effects
    with patch.object(metrics.MEALS_LOGGED, "labels", return_value=MagicMock()) as labels:
        metrics.record_meal_logged("lunch", "italian")
        labels.assert_called_once()

    with patch.object(metrics.MEALS_ANALYZED, "labels", return_value=MagicMock()) as labels:
        with patch.object(metrics.ANALYSIS_DURATION, "labels", return_value=MagicMock()) as duration_labels:
            metrics.record_meal_analyzed("image", 1.0)
            labels.assert_called_once()
            duration_labels.assert_called_once()

    with patch.object(metrics.PANTRY_OPERATIONS, "labels", return_value=MagicMock()):
        metrics.record_pantry_operation("add")

    with patch.object(metrics.RECIPES_GENERATED, "labels", return_value=MagicMock()):
        metrics.record_recipe_generated("ai_generated")

    with patch.object(metrics.SAFETY_CHECKS, "labels", return_value=MagicMock()):
        metrics.record_safety_check("recall", "safe")

    with patch.object(metrics.DISCOVERY_REQUESTS, "labels", return_value=MagicMock()):
        metrics.record_discovery_request("nearby")

    with patch.object(metrics.USER_ACTIVE_SESSIONS, "labels", return_value=MagicMock()):
        metrics.record_user_session("firebase")

    with patch.object(metrics.SECURITY_EVENTS, "labels", return_value=MagicMock()):
        metrics.record_auth_failure("invalid")
        metrics.record_permission_denied("write")
        metrics.record_rate_limit_exceeded("/path")

    with patch.object(metrics.TOOL_CALLS, "labels", return_value=MagicMock()):
        with patch.object(metrics.TOOL_LATENCY, "labels", return_value=MagicMock()):
            metrics.record_tool_call("tool", "success", "demo", 0.1)

    with patch.object(metrics.GEMINI_REQUESTS, "labels", return_value=MagicMock()):
        with patch.object(metrics.GEMINI_TOKENS, "labels", return_value=MagicMock()):
            with patch.object(metrics.GEMINI_LATENCY, "labels", return_value=MagicMock()):
                with patch.object(metrics.GEMINI_COST, "inc", return_value=None):
                    metrics.record_gemini_usage("method", 1, 2, 0.01, 0.2, success=False)


def test_setup_metrics_disabled():
    with patch.dict(os.environ, {"ENABLE_METRICS": "false"}):
        metrics.setup_metrics(MagicMock())
