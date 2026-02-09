"""Custom APIRouter enforcing response models by default."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter as FastAPIRouter

from fcp.routes.schemas import AnyResponse


class APIRouter(FastAPIRouter):
    """APIRouter that defaults to a permissive response model."""

    def add_api_route(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        if "response_model" not in kwargs or kwargs.get("response_model") is None:
            kwargs["response_model"] = AnyResponse
        return super().add_api_route(path, endpoint, **kwargs)
