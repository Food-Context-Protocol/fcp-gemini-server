"""Coverage tests for api module."""

from __future__ import annotations

import pytest
from starlette.requests import Request
from starlette.responses import Response


@pytest.mark.asyncio
async def test_security_headers_docs_path():
    import fcp.api as api

    request = Request({"type": "http", "method": "GET", "path": "/docs", "headers": []})

    async def call_next(_request):
        return Response("ok")

    response = await api.security_headers_middleware(request, call_next)
    assert "Content-Security-Policy" in response.headers
