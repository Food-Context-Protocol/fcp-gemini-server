"""Coverage tests for MCP server module."""

from __future__ import annotations

import importlib
import logging
from unittest.mock import MagicMock, mock_open, patch


def test_server_logging_file_branch(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")

    class DummyHandler(logging.Handler):
        def emit(self, record):
            return None

    with (
        patch("os.path.expanduser", return_value="/tmp/mcp.log"),
        patch("os.makedirs"),
        patch("logging.FileHandler", return_value=DummyHandler()),
    ):
        import fcp.server as server

        importlib.reload(server)


def test_load_icon_exception():
    import fcp.server as server

    with patch("pathlib.Path.exists", side_effect=Exception("boom")):
        assert server._load_icon() is None


def test_server_logging_test_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    logger = MagicMock()
    with patch("logging.getLogger", return_value=logger):
        import fcp.server as server

        importlib.reload(server)
    assert logger.addHandler.called


def test_load_icon_success(monkeypatch):
    import fcp.server as server

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("builtins.open", new_callable=mock_open, read_data=b"pngdata"),
    ):
        icons = server._load_icon()

    assert icons is not None
    assert len(icons) == 1
    assert icons[0].mimeType == "image/png"


def test_load_icon_missing_file():
    import fcp.server as server

    with patch("pathlib.Path.exists", return_value=False):
        assert server._load_icon() is None
