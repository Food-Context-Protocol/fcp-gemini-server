"""Conversation state management for Gemini 3 thought signatures.

This module provides state management for multi-turn conversations
with Gemini 3, preserving thought signatures for agentic workflows.
"""

from dataclasses import dataclass, field
from typing import Any

from google.genai import types


@dataclass
class ConversationTurn:
    """A single turn in the conversation with thought signature."""

    role: str  # "user" or "model"
    parts: list[types.Part]
    thought_signature: str | None = None
    function_calls: list[dict[str, Any]] = field(default_factory=list)
    function_responses: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ConversationState:
    """Manages conversation history with thought signatures for agentic workflows.

    Thought signatures are encrypted representations of the model's internal
    reasoning that must be preserved across API calls for Gemini 3 function
    calling to work correctly.
    """

    turns: list[ConversationTurn] = field(default_factory=list)
    system_instruction: str | None = None

    def add_user_message(self, text: str) -> None:
        """Add a user message to the conversation.

        Args:
            text: The user's message text
        """
        self.turns.append(
            ConversationTurn(
                role="user",
                parts=[types.Part(text=text)],
            )
        )

    def add_model_response(
        self,
        response: types.GenerateContentResponse,
    ) -> None:
        """Add model response, preserving thought signatures.

        Args:
            response: The model's response from the API
        """
        parts = []
        thought_sig = None
        function_calls = []

        for part in response.candidates[0].content.parts:  # ty:ignore[not-subscriptable]
            parts.append(part)

            # Capture thought signature (attached to first function call)
            if hasattr(part, "thought_signature") and part.thought_signature:
                thought_sig = part.thought_signature

            # Track function calls
            if hasattr(part, "function_call") and part.function_call:
                function_calls.append(
                    {
                        "name": part.function_call.name,
                        "args": dict(part.function_call.args),  # ty:ignore[no-matching-overload]
                    }
                )

        self.turns.append(
            ConversationTurn(
                role="model",
                parts=parts,
                thought_signature=thought_sig,
                function_calls=function_calls,
            )
        )

    def add_function_responses(
        self,
        responses: list[dict[str, Any]],
    ) -> None:
        """Add function execution results to continue the conversation.

        Args:
            responses: List of function responses with name and result
        """
        # Create function response parts
        # Note: When Gemini 3 SDK is available, use types.Part.from_function_response()
        parts = [
            types.Part(
                function_response=types.FunctionResponse(
                    name=resp["name"],
                    response=resp["result"],  # Pass dict directly, let SDK serialize
                )
            )
            for resp in responses
        ]

        self.turns.append(
            ConversationTurn(
                role="user",
                parts=parts,
                function_responses=responses,
            )
        )

    def to_contents(self) -> list[types.Content]:
        """Convert to Gemini API contents format with signatures preserved.

        Returns:
            List of Content objects for the API
        """
        contents = []

        for turn in self.turns:
            content = types.Content(
                role=turn.role,
                parts=turn.parts,
            )
            contents.append(content)

        return contents

    def get_last_thought_signature(self) -> str | None:
        """Get the most recent thought signature for validation.

        Returns:
            The most recent signature, or None if none exist
        """
        return next(
            (turn.thought_signature for turn in reversed(self.turns) if turn.thought_signature),
            None,
        )
