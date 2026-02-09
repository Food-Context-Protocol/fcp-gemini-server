"""Coverage tests for logfire service."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import fcp.services.logfire_service as lf


def _install_fake_logfire(monkeypatch):
    logfire = types.ModuleType("logfire")

    class ConsoleOptions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    logfire.ConsoleOptions = ConsoleOptions
    logfire.configure = MagicMock()
    logfire.instrument_pydantic_ai = MagicMock()
    logfire.instrument_fastapi = MagicMock()
    logfire.instrument_httpx = MagicMock()
    logfire.instrument_asyncio = MagicMock()
    logfire.instrument_aiohttp_client = MagicMock()
    logfire.shutdown = MagicMock()
    logfire.info = MagicMock()
    logfire.warn = MagicMock()
    logfire.error = MagicMock()
    logfire.debug = MagicMock()

    class SpanCtx:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    logfire.span = MagicMock(return_value=SpanCtx())

    monkeypatch.setitem(sys.modules, "logfire", logfire)


def test_init_logfire_and_shutdown(monkeypatch):
    _install_fake_logfire(monkeypatch)
    with patch.dict(
        "os.environ",
        {"LOGFIRE_TOKEN": "t", "FCP_LOGFIRE_CAPTURE_BODIES": "true"},
        clear=True,
    ):
        lf._initialized = False
        assert lf.init_logfire("proj") is True
        lf.shutdown_logfire()


def test_logfire_log_helpers(monkeypatch):
    _install_fake_logfire(monkeypatch)
    lf._initialized = False
    lf.log_info("msg", user_id="u1")
    lf.log_warn("msg", user_id="u1")
    lf.log_error("msg", user_id="u1")
    lf.log_debug("msg", user_id="u1")

    with lf.log_span("op", key="val"):
        pass

    setattr(lf, "_initialized", True)
    lf.log_info("msg", user_id="u1")
    lf.log_warn("msg", user_id="u1")
    lf.log_error("msg", user_id="u1")
    lf.log_debug("msg", user_id="u1")

    with lf.log_span("op", key="val"):
        pass


def test_logfire_helpers_fallback_on_exception(monkeypatch):
    logfire = types.ModuleType("logfire")

    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    logfire.info = _boom
    logfire.warn = _boom
    logfire.error = _boom
    logfire.debug = _boom

    class BadSpan:
        def __enter__(self):
            raise RuntimeError("boom")

        def __exit__(self, exc_type, exc, tb):
            return False

    logfire.span = MagicMock(return_value=BadSpan())
    monkeypatch.setitem(sys.modules, "logfire", logfire)

    setattr(lf, "_initialized", True)
    lf.log_info("msg", user_id="u1")
    lf.log_warn("msg", user_id="u1")
    lf.log_error("msg", user_id="u1")
    lf.log_debug("msg", user_id="u1")
    with lf.log_span("op", key="val"):
        pass
