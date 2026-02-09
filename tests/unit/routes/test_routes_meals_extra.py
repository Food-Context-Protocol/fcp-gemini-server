"""Coverage tests for meals routes."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, patch

import pytest
from starlette.datastructures import UploadFile
from starlette.requests import Request

from fcp.auth.permissions import AuthenticatedUser, UserRole
from fcp.routes.meals import create_meal_with_image


def _make_upload(content: bytes, content_type: str = "image/png") -> UploadFile:
    file = io.BytesIO(content)
    return UploadFile(
        filename="test.png",
        file=file,
        headers={"content-type": content_type},
    )


@pytest.mark.asyncio
async def test_create_meal_with_image_storage_not_configured_paths():
    user = AuthenticatedUser(user_id="u1", role=UserRole.AUTHENTICATED)
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/meals/with-image",
            "headers": [],
        }
    )
    image = _make_upload(b"\x89PNG\r\n\x1a\n" + b"0" * 10, content_type="image/png")

    with patch("fcp.routes.meals.is_storage_configured", return_value=False):
        # auto_analyze True with analysis exception
        with patch("fcp.routes.meals.analyze_meal_from_bytes", new=AsyncMock(side_effect=Exception("boom"))):
            with patch("fcp.routes.meals.add_meal", new=AsyncMock(return_value={"success": True})):
                result = await create_meal_with_image(
                    request=request,
                    image=image,
                    dish_name=None,
                    venue=None,
                    notes=None,
                    auto_analyze=True,
                    user=user,
                )
                assert result.success is True

        # auto_analyze False path
        image2 = _make_upload(b"\x89PNG\r\n\x1a\n" + b"0" * 10, content_type="image/png")
        with patch("fcp.routes.meals.add_meal", new=AsyncMock(return_value={"success": True})):
            result = await create_meal_with_image(
                request=request,
                image=image2,
                dish_name=None,
                venue=None,
                notes=None,
                auto_analyze=False,
                user=user,
            )
            assert result.success is True
