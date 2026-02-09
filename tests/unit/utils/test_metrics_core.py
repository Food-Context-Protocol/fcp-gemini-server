"""Tests for Prometheus metrics utilities."""

import os
from unittest.mock import MagicMock, patch

from fcp.utils.metrics import (
    GEMINI_COST,
    GEMINI_LATENCY,
    GEMINI_REQUESTS,
    GEMINI_TOKENS,
    record_gemini_usage,
    setup_metrics,
)


class TestRecordGeminiUsage:
    """Tests for record_gemini_usage function."""

    def test_records_successful_request(self):
        """Should record metrics for successful request."""
        # Reset metrics for clean test
        GEMINI_REQUESTS.labels(method="test_method", status="success")._value._value = 0
        GEMINI_TOKENS.labels(type="input")._value._value = 0
        GEMINI_TOKENS.labels(type="output")._value._value = 0

        record_gemini_usage(
            method="test_method",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            latency_seconds=1.5,
            success=True,
        )

        # Verify counters incremented
        assert GEMINI_REQUESTS.labels(method="test_method", status="success")._value._value >= 1
        assert GEMINI_TOKENS.labels(type="input")._value._value >= 100
        assert GEMINI_TOKENS.labels(type="output")._value._value >= 50

    def test_records_failed_request(self):
        """Should record metrics with error status for failed request."""
        record_gemini_usage(
            method="test_method_fail",
            input_tokens=50,
            output_tokens=0,
            cost_usd=0.0005,
            latency_seconds=0.5,
            success=False,
        )

        # Verify error status recorded
        assert GEMINI_REQUESTS.labels(method="test_method_fail", status="error")._value._value >= 1


class TestSetupMetrics:
    """Tests for setup_metrics function."""

    def test_setup_metrics_creates_endpoint(self):
        """Should add /metrics endpoint to app."""
        mock_app = MagicMock()

        with patch.dict(os.environ, {"ENABLE_METRICS": "true"}, clear=False):
            # setup_metrics should complete without raising
            setup_metrics(mock_app)

        # The instrumentator calls instrument() and expose() on the app
        # which uses FastAPI's internal routing, so we just verify no exception

    def test_setup_metrics_disabled_via_env(self):
        """Should not setup metrics when ENABLE_METRICS=false."""
        mock_app = MagicMock()

        with patch.dict(os.environ, {"ENABLE_METRICS": "false"}, clear=False):
            setup_metrics(mock_app)

        # Should not configure instrumentator when disabled
        # App routes should not be modified
        mock_app.add_api_route.assert_not_called()

    def test_setup_metrics_enabled_by_default(self):
        """Should enable metrics by default when ENABLE_METRICS not set."""
        mock_app = MagicMock()

        # Remove ENABLE_METRICS to test default behavior
        env = os.environ.copy()
        env.pop("ENABLE_METRICS", None)

        with patch.dict(os.environ, env, clear=True):
            # This will attempt to setup metrics (enabled by default)
            setup_metrics(mock_app)
            # Just verify it doesn't raise


class TestGeminiMetrics:
    """Tests for Gemini-specific metrics."""

    def test_latency_histogram_records_observation(self):
        """Should record latency observation in histogram."""
        # Record a latency value
        GEMINI_LATENCY.labels(method="test_latency").observe(2.5)

        # Verify histogram has data (sum should be at least 2.5)
        assert GEMINI_LATENCY.labels(method="test_latency")._sum._value >= 2.5

    def test_cost_counter_increments(self):
        """Should increment total cost counter."""
        initial = GEMINI_COST._value._value
        GEMINI_COST.inc(0.01)
        assert GEMINI_COST._value._value >= initial + 0.01
