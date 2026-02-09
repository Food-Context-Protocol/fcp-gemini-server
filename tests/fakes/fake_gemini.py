"""Fake Gemini client for testing.

Provides an in-memory implementation of GeminiClient that returns
configurable responses without making actual API calls. This allows
tests to verify AI integration logic without API costs or network
dependencies.

Example:
    fake_gemini = FakeGeminiClient(
        json_response={"dish_name": "Pizza", "cuisine": "Italian"},
        text_response="This is a delicious pizza.",
    )

    # Use in tests
    result = await fake_gemini.generate_json("Analyze this food")
    assert result["dish_name"] == "Pizza"

    # Verify calls were made
    assert len(fake_gemini.call_history) == 1
    assert fake_gemini.call_history[0]["method"] == "generate_json"
"""

from collections.abc import AsyncIterator
from typing import Any


class FakeGeminiClient:
    """In-memory implementation of GeminiClient for testing.

    Returns configurable responses for all methods, tracks call history,
    and can simulate errors when configured to do so.
    """

    def __init__(
        self,
        json_response: dict[str, Any] | list[Any] | None = None,
        text_response: str | None = None,
        grounding_sources: list[dict[str, str]] | None = None,
        function_calls: list[dict[str, Any]] | None = None,
        code: str | None = None,
        execution_result: str | None = None,
        thinking: str | None = None,
        error: Exception | None = None,
    ):
        """Initialize the fake client.

        Args:
            json_response: Default JSON response for generate_json methods
            text_response: Default text response for generate_content methods
            grounding_sources: Default grounding sources for grounding methods
            function_calls: Default function calls for tool methods
            code: Default code for code execution methods
            execution_result: Default execution result
            thinking: Default thinking content
            error: If set, all methods will raise this error
        """
        self.json_response = json_response or {"default": "response"}
        self.text_response = text_response or "Default response"
        self.grounding_sources = grounding_sources or []
        self.function_calls = function_calls or []
        self.code = code
        self.execution_result = execution_result
        self.thinking = thinking
        self.error = error

        # Track all method calls for verification
        self.call_history: list[dict[str, Any]] = []

        # Allow configuring different responses per method
        self._method_responses: dict[str, Any] = {}

    def set_response(self, method: str, response: Any) -> None:
        """Set a specific response for a method."""
        self._method_responses[method] = response

    def _get_response(self, method: str, default: Any) -> Any:
        """Get the response for a method, with fallback to default."""
        return self._method_responses.get(method, default)

    def _record_call(self, method: str, **kwargs: Any) -> None:
        """Record a method call for verification in tests."""
        self.call_history.append({"method": method, **kwargs})

    def _check_error(self) -> None:
        """Raise configured error if set."""
        if self.error:
            raise self.error

    # =========================================================================
    # Basic Generation Methods
    # =========================================================================

    async def generate_content(
        self,
        prompt: str,
        image_url: str | None = None,
        media_url: str | None = None,
    ) -> str:
        """Generate content from prompt and optional media."""
        self._record_call(
            "generate_content",
            prompt=prompt,
            image_url=image_url,
            media_url=media_url,
        )
        self._check_error()
        return self._get_response("generate_content", self.text_response)

    async def generate_content_stream(
        self,
        prompt: str,
        image_url: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream content generation for real-time UI updates."""
        self._record_call("generate_content_stream", prompt=prompt, image_url=image_url)
        self._check_error()

        # Split response into chunks for streaming
        response = self._get_response("generate_content_stream", self.text_response)
        words = response.split()
        for word in words:
            yield f"{word} "

    async def generate_json(
        self,
        prompt: str,
        image_url: str | None = None,
        media_url: str | None = None,
    ) -> dict[str, Any]:
        """Generate content with guaranteed JSON output."""
        self._record_call(
            "generate_json",
            prompt=prompt,
            image_url=image_url,
            media_url=media_url,
        )
        self._check_error()
        return self._get_response("generate_json", self.json_response)

    async def generate_json_stream(
        self,
        prompt: str,
        image_url: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream JSON generation for progressive UI updates."""
        self._record_call("generate_json_stream", prompt=prompt, image_url=image_url)
        self._check_error()

        import json

        response = self._get_response("generate_json_stream", self.json_response)
        json_str = json.dumps(response)
        # Yield in chunks
        for i in range(0, len(json_str), 10):
            yield json_str[i : i + 10]

    # =========================================================================
    # Function Calling
    # =========================================================================

    async def generate_with_tools(
        self,
        prompt: str,
        tools: list[dict],
        image_url: str | None = None,
        media_url: str | None = None,
    ) -> dict[str, Any]:
        """Generate content with function calling support."""
        self._record_call(
            "generate_with_tools",
            prompt=prompt,
            tools=tools,
            image_url=image_url,
            media_url=media_url,
        )
        self._check_error()

        return {
            "text": self._get_response("generate_with_tools_text", self.text_response),
            "function_calls": self._get_response("generate_with_tools_function_calls", self.function_calls),
        }

    # =========================================================================
    # Google Search Grounding
    # =========================================================================

    async def generate_with_grounding(self, prompt: str) -> dict[str, Any]:
        """Generate content grounded with Google Search."""
        self._record_call("generate_with_grounding", prompt=prompt)
        self._check_error()

        return {
            "text": self._get_response("generate_with_grounding_text", self.text_response),
            "sources": self._get_response("generate_with_grounding_sources", self.grounding_sources),
        }

    async def generate_json_with_grounding(self, prompt: str) -> dict[str, Any]:
        """Generate structured JSON grounded with Google Search."""
        self._record_call("generate_json_with_grounding", prompt=prompt)
        self._check_error()

        return {
            "data": self._get_response("generate_json_with_grounding_data", self.json_response),
            "sources": self._get_response("generate_json_with_grounding_sources", self.grounding_sources),
        }

    # =========================================================================
    # Thinking / Reasoning
    # =========================================================================

    async def generate_with_thinking(
        self,
        prompt: str,
        thinking_level: str = "high",
        image_url: str | None = None,
        media_url: str | None = None,
    ) -> str:
        """Generate content with extended thinking for complex reasoning."""
        self._record_call(
            "generate_with_thinking",
            prompt=prompt,
            thinking_level=thinking_level,
            image_url=image_url,
            media_url=media_url,
        )
        self._check_error()
        return self._get_response("generate_with_thinking", self.text_response)

    async def generate_json_with_thinking(
        self,
        prompt: str,
        thinking_level: str = "high",
        image_url: str | None = None,
        media_url: str | None = None,
        include_thinking_output: bool = False,
    ) -> dict[str, Any] | list[Any]:
        """Generate JSON with extended thinking for complex structured analysis."""
        self._record_call(
            "generate_json_with_thinking",
            prompt=prompt,
            thinking_level=thinking_level,
            image_url=image_url,
            media_url=media_url,
            include_thinking_output=include_thinking_output,
        )
        self._check_error()

        analysis = self._get_response("generate_json_with_thinking", self.json_response)

        if include_thinking_output:
            return {
                "analysis": analysis,
                "thinking": self._get_response("generate_json_with_thinking_thoughts", self.thinking),
            }

        return analysis

    # =========================================================================
    # Code Execution
    # =========================================================================

    async def generate_with_code_execution(self, prompt: str) -> dict[str, Any]:
        """Generate content with Python code execution capability."""
        self._record_call("generate_with_code_execution", prompt=prompt)
        self._check_error()

        return {
            "text": self._get_response("generate_with_code_execution_text", self.text_response),
            "code": self._get_response("generate_with_code_execution_code", self.code),
            "execution_result": self._get_response("generate_with_code_execution_result", self.execution_result),
        }

    # =========================================================================
    # Agentic Vision
    # =========================================================================

    async def generate_json_with_agentic_vision(
        self,
        prompt: str,
        image_url: str,
    ) -> dict[str, Any]:
        """Generate JSON using Agentic Vision (code execution + image)."""
        self._record_call(
            "generate_json_with_agentic_vision",
            prompt=prompt,
            image_url=image_url,
        )
        self._check_error()

        return {
            "analysis": self._get_response("generate_json_with_agentic_vision", self.json_response),
            "code": self._get_response("generate_json_with_agentic_vision_code", self.code),
            "execution_result": self._get_response("generate_json_with_agentic_vision_result", self.execution_result),
        }

    # =========================================================================
    # 1M Context Window
    # =========================================================================

    async def generate_with_large_context(
        self,
        prompt: str,
        thinking_level: str = "high",
    ) -> str:
        """Generate content using the full 1M token context window."""
        self._record_call(
            "generate_with_large_context",
            prompt=prompt,
            thinking_level=thinking_level,
        )
        self._check_error()
        return self._get_response("generate_with_large_context", self.text_response)

    async def generate_json_with_large_context(
        self,
        prompt: str,
        thinking_level: str = "high",
        image_url: str | None = None,
        media_url: str | None = None,
    ) -> dict[str, Any]:
        """Generate JSON using the full 1M token context window."""
        self._record_call(
            "generate_json_with_large_context",
            prompt=prompt,
            thinking_level=thinking_level,
            image_url=image_url,
            media_url=media_url,
        )
        self._check_error()
        return self._get_response("generate_json_with_large_context", self.json_response)

    # =========================================================================
    # Context Caching
    # =========================================================================

    async def create_context_cache(
        self,
        name: str,
        content: str,
        ttl_minutes: int = 60,
    ) -> str:
        """Create a cached context for large datasets."""
        self._record_call(
            "create_context_cache",
            name=name,
            content=content,
            ttl_minutes=ttl_minutes,
        )
        self._check_error()
        return f"cache/{name}"

    async def generate_with_cache(
        self,
        prompt: str,
        cache_name: str,
    ) -> str:
        """Generate content using a previously created context cache."""
        self._record_call(
            "generate_with_cache",
            prompt=prompt,
            cache_name=cache_name,
        )
        self._check_error()
        return self._get_response("generate_with_cache", self.text_response)

    # =========================================================================
    # Combined Features
    # =========================================================================

    async def generate_with_all_tools(
        self,
        prompt: str,
        function_tools: list[dict] | None = None,
        enable_grounding: bool = False,
        enable_code_execution: bool = False,
        thinking_level: str = "high",
        image_url: str | None = None,
        media_url: str | None = None,
    ) -> dict[str, Any]:
        """Generate content with multiple Gemini 3 features combined."""
        self._record_call(
            "generate_with_all_tools",
            prompt=prompt,
            function_tools=function_tools,
            enable_grounding=enable_grounding,
            enable_code_execution=enable_code_execution,
            thinking_level=thinking_level,
            image_url=image_url,
            media_url=media_url,
        )
        self._check_error()

        return {
            "text": self._get_response("generate_with_all_tools_text", self.text_response),
            "function_calls": self._get_response("generate_with_all_tools_function_calls", self.function_calls),
            "sources": self._get_response("generate_with_all_tools_sources", self.grounding_sources),
            "code": self._get_response("generate_with_all_tools_code", self.code),
            "execution_result": self._get_response("generate_with_all_tools_result", self.execution_result),
        }

    # =========================================================================
    # Deep Research
    # =========================================================================

    async def generate_deep_research(
        self,
        query: str,
        timeout_seconds: int = 300,
    ) -> dict[str, Any]:
        """Generate deep research report using Interactions API."""
        self._record_call(
            "generate_deep_research",
            query=query,
            timeout_seconds=timeout_seconds,
        )
        self._check_error()

        return self._get_response(
            "generate_deep_research",
            {
                "report": f"Research report for: {query}",
                "interaction_id": "fake-interaction-id",
                "status": "completed",
            },
        )

    # =========================================================================
    # Video Generation
    # =========================================================================

    async def generate_video(
        self,
        prompt: str,
        duration_seconds: int = 8,
        aspect_ratio: str = "16:9",
        timeout_seconds: int = 300,
    ) -> dict[str, Any]:
        """Generate video using Veo 3.1."""
        self._record_call(
            "generate_video",
            prompt=prompt,
            duration_seconds=duration_seconds,
            aspect_ratio=aspect_ratio,
            timeout_seconds=timeout_seconds,
        )
        self._check_error()

        return self._get_response(
            "generate_video",
            {
                "status": "completed",
                "video_bytes": b"fake-video-data",
                "duration": duration_seconds,
            },
        )

    # =========================================================================
    # Live API
    # =========================================================================

    def create_live_session(
        self,
        system_instruction: str | None = None,
        enable_food_tools: bool = True,
    ) -> "FakeLiveSession":
        """Create a Live API session for real-time voice conversations."""
        self._record_call(
            "create_live_session",
            system_instruction=system_instruction,
            enable_food_tools=enable_food_tools,
        )
        self._check_error()
        return FakeLiveSession(self)

    async def process_live_audio(
        self,
        audio_data: bytes,
        mime_type: str = "audio/pcm",
        sample_rate: int = 16000,
    ) -> dict[str, Any]:
        """Process a single audio chunk through the Live API."""
        self._record_call(
            "process_live_audio",
            audio_data_len=len(audio_data),
            mime_type=mime_type,
            sample_rate=sample_rate,
        )
        self._check_error()

        return self._get_response(
            "process_live_audio",
            {
                "transcription": "What I ate for lunch",
                "response_text": "Got it! I've logged your lunch.",
                "response_audio": b"fake-audio-response",
                "function_calls": self.function_calls,
            },
        )

    # =========================================================================
    # Media Resolution (Gemini 3 Specific)
    # =========================================================================

    async def generate_json_with_media_resolution(
        self,
        prompt: str,
        image_url: str,
        resolution: str = "high",
    ) -> dict[str, Any]:
        """Analyze image with configurable token budget."""
        self._record_call(
            "generate_json_with_media_resolution",
            prompt=prompt,
            image_url=image_url,
            resolution=resolution,
        )
        self._check_error()

        return self._get_response(
            "generate_json_with_media_resolution",
            self.json_response,
        )

    # =========================================================================
    # URL Context (Gemini 3 Specific)
    # =========================================================================

    async def generate_json_with_url_context(
        self,
        prompt: str,
        urls: list[str],
    ) -> dict[str, Any]:
        """Process URLs as context for analysis."""
        self._record_call(
            "generate_json_with_url_context",
            prompt=prompt,
            urls=urls,
        )
        self._check_error()

        return self._get_response(
            "generate_json_with_url_context",
            {
                "data": self.json_response,
                "sources": urls,
            },
        )

    # =========================================================================
    # Imagen 3 (Image Generation)
    # =========================================================================

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        number_of_images: int = 1,
    ) -> dict[str, Any]:
        """Generate images using Imagen 3."""
        import base64

        self._record_call(
            "generate_image",
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            number_of_images=number_of_images,
        )
        self._check_error()

        # Generate fake base64 images
        fake_images = [base64.b64encode(f"fake_image_{i}".encode()).decode() for i in range(number_of_images)]

        return self._get_response(
            "generate_image",
            {
                "images": fake_images,
                "mime_type": "image/png",
                "count": number_of_images,
            },
        )


class FakeLiveSession:
    """Fake Live API session for testing."""

    def __init__(self, client: FakeGeminiClient):
        self.client = client
        self.messages_sent: list[Any] = []

    async def __aenter__(self) -> "FakeLiveSession":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    async def send(self, input: Any, end_of_turn: bool = False) -> None:
        """Send input to the live session."""
        self.messages_sent.append({"input": input, "end_of_turn": end_of_turn})

    async def receive(self) -> AsyncIterator[Any]:
        """Receive responses from the live session."""

        # Create a fake response object
        class FakeResponse:
            def __init__(self):
                self.server_content = None
                self.tool_call = None

        class FakeModelTurn:
            def __init__(self, parts):
                self.parts = parts

        class FakePart:
            def __init__(self, text=None):
                self.text = text
                self.inline_data = None

        class FakeServerContent:
            def __init__(self, model_turn):
                self.model_turn = model_turn

        response = FakeResponse()
        response.server_content = FakeServerContent(FakeModelTurn([FakePart(text=self.client.text_response)]))

        yield response


class FakeGeminiClientWithSignatures(FakeGeminiClient):
    """Extended fake client that simulates thought signatures.

    This client extends FakeGeminiClient to support Gemini 3's thought
    signatures, which are required for multi-turn function calling.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize the fake client with signature support."""
        super().__init__(*args, **kwargs)
        self._signature_counter = 0

    def _generate_thought_signature(self) -> str:
        """Generate a fake thought signature for testing.

        Returns:
            A fake signature string
        """
        self._signature_counter += 1
        return f"fake_thought_sig_{self._signature_counter}"

    async def generate_with_tools_and_signatures(
        self,
        contents: list[Any],
        tools: list[Any],
    ) -> dict[str, Any]:
        """Generate with function calling, including thought signatures.

        Args:
            contents: Conversation contents
            tools: Available tools

        Returns:
            Response with function calls and signatures
        """
        self._record_call(
            "generate_with_tools_and_signatures",
            contents=contents,
            tools=tools,
        )
        self._check_error()

        # Simulate function calls with signatures
        # Use deep copy to avoid mutating self.function_calls when adding signature
        import copy

        function_calls = self._get_response(
            "generate_with_tools_function_calls",
            copy.deepcopy(self.function_calls) if self.function_calls else [],
        )

        # Attach signature to first call (per Gemini 3 spec)
        if function_calls:
            function_calls[0]["thought_signature"] = self._generate_thought_signature()

        return {
            "text": self._get_response("generate_with_tools_text", self.text_response),
            "function_calls": function_calls,
        }
