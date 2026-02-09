"""Coverage tests for visual tool helpers."""

from __future__ import annotations

from unittest.mock import patch

from fcp.tools import visual


def test_get_image_service_singleton():
    class DummyService:
        pass

    with patch("fcp.tools.visual.ImageGenerationService", DummyService):
        visual._image_service = None
        service = visual._get_image_service()
        assert isinstance(service, DummyService)
        # Calling again should return the same instance without reinitializing
        again = visual._get_image_service()
        assert again is service
