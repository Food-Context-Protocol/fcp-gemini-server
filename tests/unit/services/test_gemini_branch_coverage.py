"""Branch coverage tests for Gemini client."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fcp.services.gemini import GeminiClient, get_gemini_client


class DummyChunk:
    def __init__(self, text: str | None):
        self.text = text


class DummyStream:
    def __init__(self, chunks):
        self._chunks = chunks

    def __aiter__(self):
        async def _gen():
            for chunk in self._chunks:
                yield chunk

        return _gen()


class DummyModelsAwaitable:
    def __init__(self, response=None, stream=None):
        self._response = response
        self._stream = stream

    async def generate_content(self, *args, **kwargs):
        return self._response

    async def generate_content_stream(self, *args, **kwargs):
        return self._stream


class DummyModelsDirect:
    def __init__(self, response=None, stream=None):
        self._response = response
        self._stream = stream

    async def generate_content(self, *args, **kwargs):
        return self._response

    def generate_content_stream(self, *args, **kwargs):
        return self._stream


class DummyFunctionCall:
    def __init__(self, name: str, args=None):
        self.name = name
        self.args = args


class DummyPart:
    def __init__(self, function_call=None, executable_code=None, code_execution_result=None):
        self.function_call = function_call
        self.executable_code = executable_code
        self.code_execution_result = code_execution_result


class DummyContent:
    def __init__(self, parts):
        self.parts = parts


class DummyCandidate:
    def __init__(self, content=None, grounding_metadata=None):
        self.content = content
        self.grounding_metadata = grounding_metadata


class DummyResponse:
    def __init__(self, text="", candidates=None):
        self.text = text
        self.candidates = candidates or []


class DummyExecutableCode:
    def __init__(self, code: str):
        self.code = code


class DummyCodeExecutionResult:
    def __init__(self, output: str):
        self.output = output


class DummyWeb:
    def __init__(self, uri: str, title: str):
        self.uri = uri
        self.title = title


class DummyChunkMeta:
    def __init__(self, web=None):
        self.web = web


class DummyGrounding:
    def __init__(self, chunks):
        self.grounding_chunks = chunks


@pytest.mark.asyncio
async def test_generate_content_stream_skips_empty_chunks():
    client = GeminiClient()
    client.client = SimpleNamespace(
        aio=SimpleNamespace(
            models=DummyModelsAwaitable(
                stream=DummyStream([DummyChunk(""), DummyChunk("hi")]),
            )
        )
    )
    setattr(client, "_prepare_parts", AsyncMock(return_value=["parts"]))

    chunks = [chunk async for chunk in client.generate_content_stream("prompt")]
    assert chunks == ["hi"]


@pytest.mark.asyncio
async def test_generate_json_stream_skips_empty_chunks():
    client = GeminiClient()
    client.client = SimpleNamespace(
        aio=SimpleNamespace(
            models=DummyModelsDirect(
                stream=DummyStream([DummyChunk(""), DummyChunk('{"ok": true}')]),
            )
        )
    )
    setattr(client, "_prepare_parts", AsyncMock(return_value=["parts"]))

    chunks = [chunk async for chunk in client.generate_json_stream("prompt")]
    assert chunks == ['{"ok": true}']


@pytest.mark.asyncio
async def test_generate_with_tools_handles_no_candidates():
    client = GeminiClient()
    client.client = SimpleNamespace(
        aio=SimpleNamespace(models=DummyModelsAwaitable(response=DummyResponse(text="ok", candidates=[])))
    )
    setattr(client, "_prepare_parts", AsyncMock(return_value=["parts"]))

    result = await client.generate_with_tools("prompt", tools=[{"name": "t"}])
    assert result["function_calls"] == []


@pytest.mark.asyncio
async def test_generate_with_tools_extracts_function_call():
    client = GeminiClient()
    response = DummyResponse(
        text="ok",
        candidates=[
            DummyCandidate(content=DummyContent([DummyPart(function_call=DummyFunctionCall("tool", args=None))]))
        ],
    )
    client.client = SimpleNamespace(aio=SimpleNamespace(models=DummyModelsAwaitable(response=response)))
    setattr(client, "_prepare_parts", AsyncMock(return_value=["parts"]))

    result = await client.generate_with_tools("prompt", tools=[{"name": "tool"}])
    assert result["function_calls"][0]["name"] == "tool"
    assert result["function_calls"][0]["args"] == {}


@pytest.mark.asyncio
async def test_generate_with_tools_skips_empty_parts():
    client = GeminiClient()
    response = DummyResponse(
        text="ok",
        candidates=[DummyCandidate(content=DummyContent([]))],
    )
    client.client = SimpleNamespace(aio=SimpleNamespace(models=DummyModelsAwaitable(response=response)))
    setattr(client, "_prepare_parts", AsyncMock(return_value=["parts"]))

    result = await client.generate_with_tools("prompt", tools=[{"name": "tool"}])
    assert result["function_calls"] == []


@pytest.mark.asyncio
async def test_generate_with_tools_ignores_parts_without_function_call():
    client = GeminiClient()
    response = DummyResponse(
        text="ok",
        candidates=[DummyCandidate(content=DummyContent([DummyPart()]))],
    )
    client.client = SimpleNamespace(aio=SimpleNamespace(models=DummyModelsAwaitable(response=response)))
    setattr(client, "_prepare_parts", AsyncMock(return_value=["parts"]))

    result = await client.generate_with_tools("prompt", tools=[{"name": "tool"}])
    assert result["function_calls"] == []


@pytest.mark.asyncio
async def test_generate_with_code_execution_no_candidates():
    client = GeminiClient()
    client.client = SimpleNamespace(aio=SimpleNamespace(models=DummyModelsAwaitable(response=DummyResponse(text="ok"))))

    result = await client.generate_with_code_execution("prompt")
    assert result["code"] is None
    assert result["execution_result"] is None


@pytest.mark.asyncio
async def test_generate_with_code_execution_extracts_code_and_result():
    client = GeminiClient()
    response = DummyResponse(
        text="ok",
        candidates=[
            DummyCandidate(
                content=DummyContent(
                    [
                        DummyPart(
                            executable_code=DummyExecutableCode("print(1)"),
                            code_execution_result=DummyCodeExecutionResult("1"),
                        )
                    ]
                )
            )
        ],
    )
    client.client = SimpleNamespace(aio=SimpleNamespace(models=DummyModelsAwaitable(response=response)))

    result = await client.generate_with_code_execution("prompt")
    assert result["code"] == "print(1)"
    assert result["execution_result"] == "1"


@pytest.mark.asyncio
async def test_generate_with_code_execution_empty_parts():
    client = GeminiClient()
    response = DummyResponse(
        text="ok",
        candidates=[DummyCandidate(content=DummyContent([]))],
    )
    client.client = SimpleNamespace(aio=SimpleNamespace(models=DummyModelsAwaitable(response=response)))

    result = await client.generate_with_code_execution("prompt")
    assert result["code"] is None
    assert result["execution_result"] is None


@pytest.mark.asyncio
async def test_generate_with_code_execution_mixed_parts():
    client = GeminiClient()
    response = DummyResponse(
        text="ok",
        candidates=[
            DummyCandidate(
                content=DummyContent(
                    [
                        DummyPart(executable_code=DummyExecutableCode("print(4)")),
                        DummyPart(code_execution_result=DummyCodeExecutionResult("4")),
                    ]
                )
            )
        ],
    )
    client.client = SimpleNamespace(aio=SimpleNamespace(models=DummyModelsAwaitable(response=response)))

    result = await client.generate_with_code_execution("prompt")
    assert result["code"] == "print(4)"
    assert result["execution_result"] == "4"


@pytest.mark.asyncio
async def test_generate_with_all_tools_no_candidates_no_tools():
    client = GeminiClient()
    response = DummyResponse(text="ok", candidates=[])
    client.client = SimpleNamespace(aio=SimpleNamespace(models=DummyModelsAwaitable(response=response)))
    setattr(client, "_prepare_parts", AsyncMock(return_value=["parts"]))

    result = await client.generate_with_all_tools("prompt")
    assert result["sources"] == []
    assert result["function_calls"] == []
    assert result["code"] is None
    assert result["execution_result"] is None


@pytest.mark.asyncio
async def test_generate_with_all_tools_extracts_sources_and_calls():
    client = GeminiClient()
    response = DummyResponse(
        text="ok",
        candidates=[
            DummyCandidate(
                grounding_metadata=DummyGrounding([DummyChunkMeta(web=DummyWeb("u", "t"))]),
                content=DummyContent(
                    [
                        DummyPart(
                            function_call=DummyFunctionCall("tool", args={"a": 1}),
                            executable_code=DummyExecutableCode("print(2)"),
                            code_execution_result=DummyCodeExecutionResult("2"),
                        )
                    ]
                ),
            )
        ],
    )
    client.client = SimpleNamespace(aio=SimpleNamespace(models=DummyModelsAwaitable(response=response)))
    setattr(client, "_prepare_parts", AsyncMock(return_value=["parts"]))

    result = await client.generate_with_all_tools(
        "prompt",
        function_tools=[{"name": "tool"}],
        enable_grounding=True,
        enable_code_execution=True,
    )
    assert result["sources"][0]["uri"] == "u"
    assert result["function_calls"][0]["name"] == "tool"
    assert result["code"] == "print(2)"
    assert result["execution_result"] == "2"


@pytest.mark.asyncio
async def test_generate_with_all_tools_handles_empty_grounding_and_parts():
    client = GeminiClient()
    response = DummyResponse(
        text="ok",
        candidates=[
            DummyCandidate(grounding_metadata=DummyGrounding([]), content=DummyContent([])),
        ],
    )
    client.client = SimpleNamespace(aio=SimpleNamespace(models=DummyModelsAwaitable(response=response)))
    setattr(client, "_prepare_parts", AsyncMock(return_value=["parts"]))

    result = await client.generate_with_all_tools("prompt", enable_grounding=True, enable_code_execution=True)
    assert result["sources"] == []
    assert result["function_calls"] == []


@pytest.mark.asyncio
async def test_generate_with_all_tools_skips_grounding_without_web():
    client = GeminiClient()
    response = DummyResponse(
        text="ok",
        candidates=[
            DummyCandidate(
                grounding_metadata=DummyGrounding([DummyChunkMeta(web=None)]),
                content=DummyContent([]),
            ),
        ],
    )
    client.client = SimpleNamespace(aio=SimpleNamespace(models=DummyModelsAwaitable(response=response)))
    setattr(client, "_prepare_parts", AsyncMock(return_value=["parts"]))

    result = await client.generate_with_all_tools("prompt", enable_grounding=True)
    assert result["sources"] == []


@pytest.mark.asyncio
async def test_generate_with_all_tools_executes_code_without_function_call():
    client = GeminiClient()
    response = DummyResponse(
        text="ok",
        candidates=[
            DummyCandidate(
                content=DummyContent(
                    [
                        DummyPart(
                            executable_code=DummyExecutableCode("print(3)"),
                            code_execution_result=DummyCodeExecutionResult("3"),
                        )
                    ]
                )
            )
        ],
    )
    client.client = SimpleNamespace(aio=SimpleNamespace(models=DummyModelsAwaitable(response=response)))
    setattr(client, "_prepare_parts", AsyncMock(return_value=["parts"]))

    result = await client.generate_with_all_tools("prompt", enable_code_execution=True)
    assert result["code"] == "print(3)"
    assert result["execution_result"] == "3"


@pytest.mark.asyncio
async def test_generate_with_all_tools_execution_result_only():
    client = GeminiClient()
    response = DummyResponse(
        text="ok",
        candidates=[
            DummyCandidate(
                content=DummyContent(
                    [
                        DummyPart(code_execution_result=DummyCodeExecutionResult("5")),
                    ]
                )
            )
        ],
    )
    client.client = SimpleNamespace(aio=SimpleNamespace(models=DummyModelsAwaitable(response=response)))
    setattr(client, "_prepare_parts", AsyncMock(return_value=["parts"]))

    result = await client.generate_with_all_tools("prompt", enable_code_execution=True)
    assert result["execution_result"] == "5"


@pytest.mark.asyncio
async def test_generate_with_all_tools_executable_code_only():
    client = GeminiClient()
    response = DummyResponse(
        text="ok",
        candidates=[
            DummyCandidate(
                content=DummyContent(
                    [
                        DummyPart(executable_code=DummyExecutableCode("print(6)")),
                    ]
                )
            )
        ],
    )
    client.client = SimpleNamespace(aio=SimpleNamespace(models=DummyModelsAwaitable(response=response)))
    setattr(client, "_prepare_parts", AsyncMock(return_value=["parts"]))

    result = await client.generate_with_all_tools("prompt", enable_code_execution=True)
    assert result["code"] == "print(6)"


def test_get_gemini_client_double_checked_lock(monkeypatch):
    sentinel = MagicMock()

    class FakeLock:
        def __enter__(self):
            import importlib

            gemini_module = importlib.import_module("fcp.services.gemini")

            gemini_module._gemini_client = sentinel
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    import importlib

    gemini_module = importlib.import_module("fcp.services.gemini")

    monkeypatch.setattr(gemini_module, "_gemini_client", None)
    monkeypatch.setattr(gemini_module, "_gemini_lock", FakeLock())
    with patch("fcp.services.gemini.GeminiClient") as mock_client:
        client = get_gemini_client()
        assert client is sentinel
        mock_client.assert_not_called()
