"""Tests for Logfire service integration."""
# sourcery skip: no-loop-in-tests

import sys
import types
from unittest.mock import MagicMock, patch


class TestLogfireService:
    """Tests for Logfire initialization and shutdown."""

    def test_init_logfire_success(self):
        """Should initialize Logfire successfully."""
        import fcp.services.logfire_service as logfire_module

        # Reset state
        logfire_module._initialized = False

        mock_logfire = MagicMock()
        with patch.dict(sys.modules, {"logfire": mock_logfire}):
            result = logfire_module.init_logfire()

            assert result is True
            assert logfire_module._initialized
            mock_logfire.configure.assert_called_once()

        logfire_module._initialized = False

    def test_init_logfire_already_initialized(self):
        """Should return True if already initialized."""
        import fcp.services.logfire_service as logfire_module

        setattr(logfire_module, "_initialized", True)

        result = logfire_module.init_logfire()

        assert result is True
        logfire_module._initialized = False

    def test_init_logfire_with_token(self):
        """Should enable cloud export when token is set."""
        import fcp.services.logfire_service as logfire_module

        logfire_module._initialized = False

        mock_logfire = MagicMock()
        with (
            patch.dict("os.environ", {"LOGFIRE_TOKEN": "test_token"}),
            patch.dict(sys.modules, {"logfire": mock_logfire}),
        ):
            result = logfire_module.init_logfire()

            assert result is True
            call_kwargs = mock_logfire.configure.call_args.kwargs
            assert call_kwargs["send_to_logfire"] is True

        logfire_module._initialized = False

    def test_init_logfire_without_token(self):
        """Should disable cloud export when token is not set."""
        import os

        import fcp.services.logfire_service as logfire_module

        logfire_module._initialized = False

        # Clear LOGFIRE_TOKEN if it exists
        os.environ.pop("LOGFIRE_TOKEN", None)

        mock_logfire = MagicMock()
        with patch.dict(sys.modules, {"logfire": mock_logfire}):
            result = logfire_module.init_logfire()

            assert result is True
            call_kwargs = mock_logfire.configure.call_args.kwargs
            assert call_kwargs["send_to_logfire"] is False

        logfire_module._initialized = False

    def test_init_logfire_send_disabled(self):
        """Should respect LOGFIRE_SEND_TO_LOGFIRE=false."""
        import fcp.services.logfire_service as logfire_module

        logfire_module._initialized = False

        mock_logfire = MagicMock()
        with (
            patch.dict("os.environ", {"LOGFIRE_TOKEN": "test_token", "LOGFIRE_SEND_TO_LOGFIRE": "false"}),
            patch.dict(sys.modules, {"logfire": mock_logfire}),
        ):
            result = logfire_module.init_logfire()

            assert result is True
            call_kwargs = mock_logfire.configure.call_args.kwargs
            assert call_kwargs["send_to_logfire"] is False

        logfire_module._initialized = False

    def test_init_logfire_instruments_pydantic_ai(self):
        """Should instrument Pydantic AI if available."""
        import fcp.services.logfire_service as logfire_module

        logfire_module._initialized = False

        mock_logfire = MagicMock()
        with patch.dict(sys.modules, {"logfire": mock_logfire}):
            result = logfire_module.init_logfire()

            assert result is True
            mock_logfire.instrument_pydantic_ai.assert_called_once()

        logfire_module._initialized = False

    def test_init_logfire_instruments_fastapi(self):
        """Should instrument FastAPI if available."""
        import fcp.services.logfire_service as logfire_module

        logfire_module._initialized = False

        mock_logfire = MagicMock()
        with patch.dict(sys.modules, {"logfire": mock_logfire}):
            result = logfire_module.init_logfire()

            assert result is True
            mock_logfire.instrument_fastapi.assert_called_once()

        logfire_module._initialized = False

    def test_init_logfire_instruments_httpx(self):
        """Should instrument HTTPX if available."""
        import fcp.services.logfire_service as logfire_module

        logfire_module._initialized = False

        mock_logfire = MagicMock()
        with patch.dict(sys.modules, {"logfire": mock_logfire}):
            result = logfire_module.init_logfire()

            assert result is True
            mock_logfire.instrument_httpx.assert_called_once()

        logfire_module._initialized = False

    def test_init_logfire_handles_instrumentation_errors(self):
        """Should continue if instrumentation fails."""
        import fcp.services.logfire_service as logfire_module

        logfire_module._initialized = False

        mock_logfire = MagicMock()
        mock_logfire.instrument_pydantic_ai.side_effect = Exception("Not available")
        mock_logfire.instrument_fastapi.side_effect = Exception("Not available")
        mock_logfire.instrument_httpx.side_effect = Exception("Not available")

        with patch.dict(sys.modules, {"logfire": mock_logfire}):
            result = logfire_module.init_logfire()

            assert result is True  # Should still succeed

        logfire_module._initialized = False

    def test_shutdown_logfire(self):
        """Should shutdown Logfire properly."""
        import fcp.services.logfire_service as logfire_module

        setattr(logfire_module, "_initialized", True)

        mock_logfire = MagicMock()
        with patch.dict(sys.modules, {"logfire": mock_logfire}):
            logfire_module.shutdown_logfire()

            mock_logfire.shutdown.assert_called_once()
            assert not logfire_module._initialized

    def test_shutdown_logfire_not_initialized(self):
        """Should be a no-op if not initialized."""
        import fcp.services.logfire_service as logfire_module

        logfire_module._initialized = False

        mock_logfire = MagicMock()
        with patch.dict(sys.modules, {"logfire": mock_logfire}):
            logfire_module.shutdown_logfire()

            mock_logfire.shutdown.assert_not_called()

    def test_shutdown_logfire_handles_errors(self):
        """Should handle shutdown errors gracefully."""
        import fcp.services.logfire_service as logfire_module

        setattr(logfire_module, "_initialized", True)

        mock_logfire = MagicMock()
        mock_logfire.shutdown.side_effect = Exception("Shutdown failed")

        with patch.dict(sys.modules, {"logfire": mock_logfire}):
            # Should not raise
            logfire_module.shutdown_logfire()

            assert not logfire_module._initialized

    def test_is_logfire_initialized(self):
        """Should return initialization status."""
        import fcp.services.logfire_service as logfire_module

        logfire_module._initialized = False
        assert logfire_module.is_logfire_initialized() is False

        setattr(logfire_module, "_initialized", True)
        assert logfire_module.is_logfire_initialized() is True

        logfire_module._initialized = False

    def test_init_logfire_configure_error(self):
        """Should handle configure errors gracefully."""
        import fcp.services.logfire_service as logfire_module

        logfire_module._initialized = False

        mock_logfire = MagicMock()
        mock_logfire.configure.side_effect = Exception("Config failed")

        with patch.dict(sys.modules, {"logfire": mock_logfire}):
            result = logfire_module.init_logfire()

            assert result is False
            assert not logfire_module._initialized

    def test_init_logfire_import_error(self):
        """Should handle missing logfire package gracefully."""
        import fcp.services.logfire_service as logfire_module

        logfire_module._initialized = False

        # Simulate ImportError by removing logfire from sys.modules temporarily
        original_modules = sys.modules.copy()

        # Remove logfire module to trigger ImportError
        logfire_related = [k for k in sys.modules if "logfire" in k]
        for mod in logfire_related:
            sys.modules.pop(mod, None)

        # Create a module that raises ImportError when accessed
        class FailImport(types.ModuleType):
            def __getattr__(self, name):
                raise ImportError("No module named 'logfire'")

        sys.modules["logfire"] = FailImport("logfire")

        try:
            result = logfire_module.init_logfire()
            # Should return False due to import/attribute error
            assert result is False
        finally:
            # Restore original modules
            sys.modules.update(original_modules)
            logfire_module._initialized = False
