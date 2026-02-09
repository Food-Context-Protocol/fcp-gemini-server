"""Tests for API CORS configuration."""

from __future__ import annotations

import importlib
import sys


def test_cors_origins_production(monkeypatch):
    """Production should not include dev localhost origins."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("DEV_CORS_ORIGINS", raising=False)

    sys.modules.pop("fcp.api", None)
    api = importlib.import_module("fcp.api")

    assert "https://fcp.dev" in api.CORS_ORIGINS
    assert "http://localhost:3000" not in api.CORS_ORIGINS
