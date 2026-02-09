"""Coverage tests for audio helper functions."""

from __future__ import annotations

from fcp.tools.audio import _normalize_confidence


def test_normalize_confidence_invalid_value():
    assert _normalize_confidence("not-a-number") == 0.0
