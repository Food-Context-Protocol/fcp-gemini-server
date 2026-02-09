"""Tests for Gemini module-level singletons and proxy."""

import sys
from unittest.mock import MagicMock


class TestGeminiModuleSingletons:
    """Tests for set/reset_gemini_client and _GeminiProxy."""

    def test_set_gemini_client(self):
        mod = sys.modules["fcp.services.gemini"]
        original = mod._gemini_client
        try:
            sentinel = MagicMock()
            mod.set_gemini_client(sentinel)
            assert mod._gemini_client is sentinel
        finally:
            mod._gemini_client = original

    def test_reset_gemini_client(self):
        mod = sys.modules["fcp.services.gemini"]
        original = mod._gemini_client
        try:
            mod._gemini_client = MagicMock()
            mod.reset_gemini_client()
            assert mod._gemini_client is None
        finally:
            mod._gemini_client = original

    def test_gemini_proxy_call(self):
        mod = sys.modules["fcp.services.gemini"]
        original = mod._gemini_client
        try:
            fake = MagicMock()
            mod.set_gemini_client(fake)
            proxy = mod._GeminiProxy()
            proxy("arg1", key="val")
            fake.assert_called_once_with("arg1", key="val")
        finally:
            mod._gemini_client = original

    def test_gemini_proxy_repr(self):
        mod = sys.modules["fcp.services.gemini"]
        original = mod._gemini_client
        try:
            fake = MagicMock()
            fake.__repr__ = lambda self: "FakeGemini"
            mod.set_gemini_client(fake)
            proxy = mod._GeminiProxy()
            result = repr(proxy)
            assert "GeminiProxy" in result
            assert "FakeGemini" in result
        finally:
            mod._gemini_client = original
