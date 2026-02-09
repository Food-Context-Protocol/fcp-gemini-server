"""Coverage tests for MCP server module."""

from __future__ import annotations

import importlib
import logging
from unittest.mock import MagicMock, mock_open, patch

import pytest


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


def test_main_default_mcp(monkeypatch):
    """main() with no args defaults to MCP mode."""
    import fcp.server as server

    monkeypatch.setattr("sys.argv", ["fcp-server"])
    fake_coro = "fake_mcp_coro"
    monkeypatch.setattr(server, "run_mcp_server", lambda: fake_coro)
    with patch("asyncio.run") as mock_asyncio:
        server.main()
        mock_asyncio.assert_called_once_with(fake_coro)


def test_main_http_mode(monkeypatch):
    """main() --http runs uvicorn."""
    import fcp.server as server

    monkeypatch.setattr("sys.argv", ["fcp-server", "--http", "--port", "9090"])
    monkeypatch.setattr(server, "run_mcp_server", lambda: None)
    with patch("uvicorn.run") as mock_uvicorn:
        server.main()
        mock_uvicorn.assert_called_once()
        assert mock_uvicorn.call_args.kwargs["port"] == 9090


def test_main_both_modes_exits(monkeypatch):
    """main() --mcp --http is an error."""
    import fcp.server as server

    monkeypatch.setattr("sys.argv", ["fcp-server", "--mcp", "--http"])
    with pytest.raises(SystemExit):
        server.main()


def test_main_explicit_mcp_mode(monkeypatch):
    """main() --mcp explicitly runs MCP server."""
    import fcp.server as server

    monkeypatch.setattr("sys.argv", ["fcp-server", "--mcp"])
    fake_coro = "fake_mcp_coro"
    monkeypatch.setattr(server, "run_mcp_server", lambda: fake_coro)
    with patch("asyncio.run") as mock_asyncio:
        server.main()
        mock_asyncio.assert_called_once_with(fake_coro)
