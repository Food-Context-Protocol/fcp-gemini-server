"""Coverage tests for custom APIRouter."""

from __future__ import annotations

from fcp.routes.router import APIRouter
from fcp.routes.schemas import AnyResponse


def test_router_defaults_response_model():
    router = APIRouter()

    def handler():
        return {"ok": True}

    router.add_api_route("/example", handler, methods=["GET"])
    route = router.routes[-1]
    assert route.response_model is AnyResponse
