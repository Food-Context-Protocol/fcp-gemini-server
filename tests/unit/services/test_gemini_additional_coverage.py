"""Additional coverage tests for Gemini client."""

from __future__ import annotations

import asyncio
import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

gemini = importlib.import_module("fcp.services.gemini")


def _dummy_client_with_models(response=None, stream_chunks=None):
    async def _generate_content(**kwargs):
        return response

    class _StreamWrapper:
        def __init__(self, chunks):
            self._chunks = list(chunks or [])

        def __aiter__(self):
            async def _stream():
                for chunk in self._chunks:
                    yield chunk

            return _stream()

        def __await__(self):
            async def _coro():
                return self

            return _coro().__await__()

    def _generate_content_stream(**kwargs):
        return _StreamWrapper(stream_chunks)

    models = SimpleNamespace(generate_content=_generate_content, generate_content_stream=_generate_content_stream)
    aio = SimpleNamespace(models=models)
    return SimpleNamespace(aio=aio)


def test_get_thinking_budget_default():
    assert gemini._get_thinking_budget("unknown") == 16384


@pytest.mark.asyncio
async def test_prepare_parts_bytes_and_urls(monkeypatch):
    client = gemini.GeminiClient()

    class DummyPart:
        def __init__(self, text=None):
            self.text = text

        @classmethod
        def from_bytes(cls, data=None, mime_type=None):
            return SimpleNamespace(data=data, mime_type=mime_type)

    monkeypatch.setattr(gemini.types, "Part", DummyPart)

    parts = await client._prepare_parts("hi", image_bytes=b"x", image_mime_type="image/png")
    assert len(parts) == 2

    async def _fetch_media(url, expected_type="image"):
        return b"data", "image/png" if expected_type == "image" else "audio/mpeg"

    client._fetch_media = _fetch_media
    parts = await client._prepare_parts("hi", image_url="http://img", media_url="http://media")
    assert len(parts) == 3


@pytest.mark.asyncio
async def test_generate_content_stream_and_json_stream():
    response = SimpleNamespace(text="ok", candidates=[])
    stream_chunks = [SimpleNamespace(text="a"), SimpleNamespace(text="b")]
    client = gemini.GeminiClient()
    client.client = _dummy_client_with_models(response=response, stream_chunks=stream_chunks)

    chunks = []
    async for chunk in client.generate_content_stream("prompt"):
        chunks.append(chunk)
    assert chunks == ["a", "b"]

    chunks = []
    async for chunk in client.generate_json_stream("prompt"):
        chunks.append(chunk)
    assert chunks == ["a", "b"]


@pytest.mark.asyncio
async def test_generate_with_grounding_and_json_with_grounding():
    web = SimpleNamespace(uri="u", title="t")
    grounding_metadata = SimpleNamespace(grounding_chunks=[SimpleNamespace(web=web)])
    candidate = SimpleNamespace(grounding_metadata=grounding_metadata)
    response = SimpleNamespace(text="ok", candidates=[candidate])
    client = gemini.GeminiClient()
    client.client = _dummy_client_with_models(response=response)

    result = await client.generate_with_grounding("prompt")
    assert result["sources"][0]["uri"] == "u"

    response = SimpleNamespace(text='{"a": 1}', candidates=[candidate])
    client.client = _dummy_client_with_models(response=response)
    result = await client.generate_json_with_grounding("prompt")
    assert result["data"]["a"] == 1

    response = SimpleNamespace(text=None, candidates=[candidate])
    client.client = _dummy_client_with_models(response=response)
    with pytest.raises(ValueError):
        await client.generate_json_with_grounding("prompt")


@pytest.mark.asyncio
async def test_generate_with_thinking_and_json_with_thinking():
    part = SimpleNamespace(thought=True, text="thinking")
    content = SimpleNamespace(parts=[part])
    candidate = SimpleNamespace(content=content)
    response = SimpleNamespace(text='{"a": 1}', candidates=[candidate])
    client = gemini.GeminiClient()
    client.client = _dummy_client_with_models(response=response)

    text = await client.generate_with_thinking("prompt", thinking_level="high")
    assert text

    result = await client.generate_json_with_thinking("prompt", include_thinking_output=True)
    assert result["analysis"]["a"] == 1
    assert result["thinking"] == "thinking"

    result = await client.generate_json_with_thinking("prompt", include_thinking_output=False)
    assert result["a"] == 1


@pytest.mark.asyncio
async def test_generate_with_code_execution():
    part = SimpleNamespace(
        executable_code=SimpleNamespace(code="x=1"),
        code_execution_result=SimpleNamespace(output="out"),
    )
    candidate = SimpleNamespace(content=SimpleNamespace(parts=[part]))
    response = SimpleNamespace(text="ok", candidates=[candidate])
    client = gemini.GeminiClient()
    client.client = _dummy_client_with_models(response=response)

    result = await client.generate_with_code_execution("prompt")
    assert result["code"] == "x=1"
    assert result["execution_result"] == "out"


@pytest.mark.asyncio
async def test_generate_json_with_agentic_vision_empty_text():
    response = SimpleNamespace(text=None, candidates=[])
    client = gemini.GeminiClient()
    client.client = _dummy_client_with_models(response=response)
    setattr(client, "_prepare_parts", AsyncMock(return_value=[SimpleNamespace()]))
    with pytest.raises(ValueError):
        await client.generate_json_with_agentic_vision("prompt", "http://img")


@pytest.mark.asyncio
async def test_generate_with_large_context_and_json_large_context():
    response = SimpleNamespace(text="ok", candidates=[])
    client = gemini.GeminiClient()
    client.client = _dummy_client_with_models(response=response)
    assert await client.generate_with_large_context("prompt")

    response = SimpleNamespace(text='{"a": 1}', candidates=[])
    client.client = _dummy_client_with_models(response=response)
    result = await client.generate_json_with_large_context("prompt")
    assert result["a"] == 1

    response = SimpleNamespace(text=None, candidates=[])
    client.client = _dummy_client_with_models(response=response)
    with pytest.raises(ValueError):
        await client.generate_json_with_large_context("prompt")


@pytest.mark.asyncio
async def test_generate_with_all_tools():
    web = SimpleNamespace(uri="u", title="t")
    grounding_metadata = SimpleNamespace(grounding_chunks=[SimpleNamespace(web=web)])
    part = SimpleNamespace(
        function_call=SimpleNamespace(name="fn", args={"a": 1}),
        executable_code=SimpleNamespace(code="x=1"),
        code_execution_result=SimpleNamespace(output="out"),
    )
    candidate = SimpleNamespace(content=SimpleNamespace(parts=[part]), grounding_metadata=grounding_metadata)
    response = SimpleNamespace(text="ok", candidates=[candidate])
    client = gemini.GeminiClient()
    client.client = _dummy_client_with_models(response=response)

    result = await client.generate_with_all_tools(
        "prompt",
        function_tools=[{"name": "fn", "parameters": {}}],
        enable_grounding=True,
        enable_code_execution=True,
    )
    assert result["sources"][0]["uri"] == "u"
    assert result["function_calls"][0]["name"] == "fn"
    assert result["code"] == "x=1"


@pytest.mark.asyncio
async def test_generate_deep_research_error_retries(monkeypatch):
    class DummyInteractions:
        def __init__(self):
            self.calls = 0

        async def create(self, **kwargs):
            return SimpleNamespace(id="i", status="running")

        async def get(self, _id):
            self.calls += 1
            raise RuntimeError("boom")

    client = gemini.GeminiClient()
    client.client = SimpleNamespace(aio=SimpleNamespace(interactions=DummyInteractions()))

    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    result = await client.generate_deep_research("q", timeout_seconds=1)
    assert result["status"] == "failed"
