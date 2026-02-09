"""Coverage tests for image generation service."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from fcp.services.image_generation import AspectRatio, ImageGenerationService, Resolution


@pytest.mark.asyncio
async def test_generate_food_image_thought_signature_bytes():
    class DummyClient:
        def __init__(self):
            async def _generate_content(**kwargs):
                return SimpleNamespace(
                    candidates=[
                        SimpleNamespace(
                            content=SimpleNamespace(
                                parts=[
                                    SimpleNamespace(
                                        inline_data=SimpleNamespace(
                                            data=b"img",
                                            mime_type="image/png",
                                        ),
                                        thought_signature=b"sig",
                                    )
                                ]
                            )
                        )
                    ]
                )

            self.aio = SimpleNamespace(models=SimpleNamespace(generate_content=_generate_content))

    with patch("fcp.services.image_generation.genai.Client", return_value=DummyClient()):
        service = ImageGenerationService()
        result = await service.generate_food_image(
            "Dish",
            aspect_ratio=AspectRatio.SQUARE,
            resolution=Resolution.STANDARD,
        )
        assert result.mime_type == "image/png"
        assert isinstance(result.thought_signature, str)
