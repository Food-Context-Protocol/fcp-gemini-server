"""Real-time cooking assistant using Gemini Live API.

This service provides hands-free cooking guidance with voice interaction,
visual monitoring, and proactive alerts.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import logfire
from google import genai
from google.genai import types
from pydantic import BaseModel, Field


class CookingStep(BaseModel):
    """A step in the cooking process."""

    step_number: int
    instruction: str
    duration_seconds: int | None = None
    temperature: str | None = None
    warning: str | None = None


class CookingSession(BaseModel):
    """Active cooking session state."""

    recipe_name: str
    current_step: int
    total_steps: int
    active_timers: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CookingAssistantService:
    """Real-time cooking assistant using Gemini Live API.

    Provides hands-free cooking guidance with:
    - Voice interaction (ask questions while cooking)
    - Visual monitoring (camera watches for doneness, safety)
    - Proactive alerts (timer reminders, potential issues)
    - Context-aware help (knows current recipe step)
    """

    MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

    def __init__(self, user_id: str):
        """Initialize the cooking assistant.

        Args:
            user_id: The user's ID
        """
        self.user_id = user_id
        self.client = genai.Client()
        self.session: CookingSession | None = None

    async def start_cooking_session(
        self,
        recipe: dict,
        enable_video: bool = True,
    ) -> AsyncIterator[bytes]:
        """Start a real-time cooking assistant session.

        Args:
            recipe: The recipe being cooked (from Firestore)
            enable_video: Whether to enable camera monitoring

        Yields:
            Audio bytes for playback (model responses)
        """
        with logfire.span("cooking_assistant.start", recipe=recipe.get("name")):
            self.session = CookingSession(
                recipe_name=recipe.get("name", "Unknown Recipe"),
                current_step=1,
                total_steps=len(recipe.get("instructions", [])),
                active_timers=[],
                warnings=[],
            )

            # Build system instruction with recipe context
            system_instruction = self._build_system_instruction(recipe)

            # Define cooking-specific tools
            tools = self._build_cooking_tools()

            # Create Live API session config
            config = types.LiveConnectConfig(
                system_instruction=system_instruction,
                tools=tools,
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Kore"  # Warm, encouraging voice
                        )
                    )
                ),
                response_modalities=["AUDIO"],
            )

            async with self.client.aio.live.connect(
                model=self.MODEL,
                config=config,
            ) as session:
                # Greeting
                await session.send(  # ty: ignore[too-many-positional-arguments]
                    types.LiveClientContent(
                        turns=[
                            types.Content(
                                role="user",
                                parts=[
                                    types.Part(
                                        text=f"I'm about to start cooking {recipe.get('name')}. "
                                        "Please guide me through step by step."
                                    )
                                ],
                            )
                        ],
                        turn_complete=True,
                    )  # ty:ignore[too-many-positional-arguments]
                )

                # Process responses
                async for response in session.receive():
                    if response.server_content:
                        for part in response.server_content.model_turn.parts:
                            if part.inline_data:
                                # Audio response
                                yield part.inline_data.data

                    if response.tool_call:
                        # Handle function calls
                        result = await self._handle_tool_call(response.tool_call)
                        await session.send(  # type: ignore[call-arg]
                            types.LiveClientContent(tool_response=types.ToolResponse(function_responses=[result]))  # type: ignore[call-arg]
                        )

    async def send_audio_input(
        self,
        session: Any,
        audio_data: bytes,
    ) -> None:
        """Send audio input from user's microphone.

        Args:
            session: Active Live API session
            audio_data: Raw audio bytes
        """
        await session.send(  # type: ignore[call-arg]
            types.LiveClientContent(
                realtime_input=types.RealtimeInput(  # type: ignore[call-arg]
                    media_chunks=[
                        types.Blob(
                            data=audio_data,
                            mime_type="audio/pcm;rate=16000",
                        )
                    ]
                )
            )
        )

    async def send_video_frame(
        self,
        session: Any,
        frame_data: bytes,
    ) -> None:
        """Send video frame from user's camera for visual monitoring.

        Args:
            session: Active Live API session
            frame_data: JPEG encoded frame
        """
        await session.send(  # type: ignore[call-arg]
            types.LiveClientContent(
                realtime_input=types.RealtimeInput(  # type: ignore[call-arg]
                    media_chunks=[
                        types.Blob(
                            data=frame_data,
                            mime_type="image/jpeg",
                        )
                    ]
                )
            )
        )

    def _build_system_instruction(self, recipe: dict) -> str:
        """Build cooking assistant system instruction.

        Args:
            recipe: Recipe dictionary

        Returns:
            System instruction string
        """
        ingredients = recipe.get("ingredients", [])
        instructions = recipe.get("instructions", [])

        return f"""You are a friendly, encouraging cooking assistant helping the user cook:

**Recipe: {recipe.get("name", "Unknown")}**

**Ingredients:**
{chr(10).join(f"- {ing}" for ing in ingredients)}

**Steps:**
{chr(10).join(f"{i + 1}. {step}" for i, step in enumerate(instructions))}

**Your Role:**
1. Guide the user through each step clearly and patiently
2. Watch for potential issues (burning, under-cooking) via camera
3. Proactively alert about timing-sensitive moments
4. Answer questions about technique, substitutions, or modifications
5. Be encouraging and supportive, especially if things go wrong
6. Use the provided tools to set timers and track progress

**Voice Style:**
- Warm and encouraging
- Clear and concise (they're cooking, not reading)
- Proactive with warnings
- Patient with questions

**Camera Monitoring:**
When you see video frames, watch for:
- Color changes indicating doneness
- Smoke or burning
- Safety concerns (knife position, hot handles)
- Readiness to move to next step
"""

    def _build_cooking_tools(self) -> list[types.Tool]:
        """Build cooking-specific function tools.

        Returns:
            List of tools for the cooking assistant
        """
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="set_timer",
                        description="Set a cooking timer",
                        parameters=types.Schema(
                            type="object",
                            properties={
                                "duration_seconds": types.Schema(
                                    type="integer",
                                    description="Timer duration in seconds",
                                ),
                                "label": types.Schema(
                                    type="string",
                                    description="What the timer is for",
                                ),
                            },
                            required=["duration_seconds", "label"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="advance_step",
                        description="Move to the next step in the recipe",
                        parameters=types.Schema(
                            type="object",
                            properties={
                                "step_number": types.Schema(
                                    type="integer",
                                    description="The step number to advance to",
                                ),
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="log_cooking_note",
                        description="Log a note about the cooking session",
                        parameters=types.Schema(
                            type="object",
                            properties={
                                "note": types.Schema(
                                    type="string",
                                    description="The note to log",
                                ),
                                "category": types.Schema(
                                    type="string",
                                    enum=["success", "modification", "issue", "tip"],
                                ),
                            },
                            required=["note", "category"],
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="emergency_alert",
                        description="Trigger an emergency alert",
                        parameters=types.Schema(
                            type="object",
                            properties={
                                "alert_type": types.Schema(
                                    type="string",
                                    enum=["smoke", "fire", "burn_risk", "safety"],
                                ),
                                "message": types.Schema(
                                    type="string",
                                    description="Description of the emergency",
                                ),
                            },
                            required=["alert_type", "message"],
                        ),
                    ),
                ]
            )
        ]

    async def _handle_tool_call(self, tool_call: Any) -> types.FunctionResponse:
        """Handle function calls from the cooking assistant.

        Args:
            tool_call: Tool call from the model

        Returns:
            Function response to send back
        """
        name = tool_call.function_calls[0].name
        args = dict(tool_call.function_calls[0].args)

        match name:
            case "set_timer":
                timer_id = await self._create_timer(
                    args["duration_seconds"],
                    args["label"],
                )
                return types.FunctionResponse(
                    name=name,
                    response={"timer_id": timer_id, "status": "started"},
                )

            case "advance_step":
                if self.session:
                    self.session.current_step = args.get("step_number", self.session.current_step + 1)
                return types.FunctionResponse(
                    name=name,
                    response={"current_step": self.session.current_step if self.session else 1},
                )

            case "log_cooking_note":
                await self._save_cooking_note(args["note"], args["category"])
                return types.FunctionResponse(
                    name=name,
                    response={"status": "logged"},
                )

            case "emergency_alert":
                await self._trigger_emergency_alert(args["alert_type"], args["message"])
                return types.FunctionResponse(
                    name=name,
                    response={"status": "alert_sent"},
                )

        return types.FunctionResponse(
            name=name,
            response={"error": "Unknown function"},
        )

    async def _create_timer(self, duration: int, label: str) -> str:
        """Create a cooking timer.

        Args:
            duration: Duration in seconds
            label: Timer label

        Returns:
            Timer ID
        """
        import uuid

        timer_id = str(uuid.uuid4())[:8]

        if self.session:
            self.session.active_timers.append(
                {
                    "id": timer_id,
                    "duration": duration,
                    "label": label,
                    "started_at": asyncio.get_event_loop().time(),
                }
            )

        # Schedule notification when timer completes
        asyncio.create_task(self._timer_notification(timer_id, duration, label))

        return timer_id

    async def _timer_notification(self, timer_id: str, duration: int, label: str) -> None:
        """Wait for timer and notify.

        Args:
            timer_id: Timer ID
            duration: Duration to wait
            label: Timer label
        """
        await asyncio.sleep(duration)
        logfire.info("Timer complete", timer_id=timer_id, label=label)

    async def _save_cooking_note(self, note: str, category: str) -> None:
        """Save a cooking note.

        Args:
            note: Note content
            category: Note category
        """
        logfire.info("Cooking note", note=note, category=category, user_id=self.user_id)

    async def _trigger_emergency_alert(self, alert_type: str, message: str) -> None:
        """Trigger an emergency alert.

        Args:
            alert_type: Type of emergency
            message: Alert message
        """
        logfire.warn(
            "Emergency alert",
            alert_type=alert_type,
            message=message,
            user_id=self.user_id,
        )
