"""Browser automation service using Gemini Computer Use.

This service enables automatic recipe and menu import from any website
by visually navigating and extracting content.
"""

import base64
from typing import Any

from pydantic import BaseModel


class BrowserAction(BaseModel):
    """An action to perform in the browser."""

    action: str
    x: int | None = None
    y: int | None = None
    text: str | None = None
    url: str | None = None
    direction: str | None = None
    keys: str | None = None


class RecipeImportResult(BaseModel):
    """Result of recipe import from a website."""

    title: str
    ingredients: list[str]
    instructions: list[str]
    prep_time: str | None = None
    cook_time: str | None = None
    servings: int | None = None
    source_url: str
    image_url: str | None = None


class BrowserAutomationService:
    """Service for browser automation using Gemini Computer Use.

    This service enables FoodLog to automatically extract recipes
    from any website by visually navigating and reading content.
    """

    MODEL = "gemini-3-flash-preview"
    SCREEN_WIDTH = 1440
    SCREEN_HEIGHT = 900

    def __init__(self):
        """Initialize the browser automation service."""
        from google import genai

        self.client = genai.Client()
        self.browser = None
        self.page = None

    async def import_recipe_from_url(self, url: str) -> RecipeImportResult:
        """Import a recipe from any URL using visual navigation.

        Args:
            url: The URL of the recipe page

        Returns:
            Extracted recipe with ingredients, instructions, etc.
        """
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            self.browser = await p.chromium.launch(headless=True)
            self.page = await self.browser.new_page(viewport={"width": self.SCREEN_WIDTH, "height": self.SCREEN_HEIGHT})

            try:
                # Navigate to the URL
                await self.page.goto(url, wait_until="networkidle")

                # Run the extraction agent loop
                recipe_data = await self._run_extraction_loop()

                return RecipeImportResult(
                    **recipe_data,
                    source_url=url,
                )

            finally:
                await self.browser.close()

    async def _run_extraction_loop(self, max_steps: int = 10) -> dict:
        """Run the agent loop to extract recipe data.

        Args:
            max_steps: Maximum number of interaction steps

        Returns:
            Extracted recipe data dictionary
        """
        conversation_history: list[dict[str, Any]] = []

        # Initial screenshot
        screenshot = await self._take_screenshot()

        # Initial instruction
        user_message = """You are a recipe extraction assistant. Your goal is to extract the complete recipe from this page.

Extract:
1. Recipe title
2. All ingredients with quantities
3. All cooking instructions in order
4. Prep time and cook time if shown
5. Number of servings if shown
6. Main image URL if visible

Navigate the page as needed (scroll, click "show more", close popups).
When you have all the information, call the 'submit_recipe' function with the extracted data.

Current page screenshot is attached."""

        conversation_history.append(
            {
                "role": "user",
                "parts": [
                    {"text": user_message},
                    {"inline_data": {"mime_type": "image/png", "data": screenshot}},
                ],
            }
        )

        for _step in range(max_steps):
            response = await self._generate_with_computer_use(conversation_history)

            # Check for recipe submission
            if self._has_recipe_submission(response):
                return self._extract_recipe_data(response)

            # Execute browser actions
            actions = self._extract_actions(response)

            if not actions:
                # Model is done or stuck
                break

            for action in actions:
                await self._execute_action(action)

            # Take new screenshot after actions
            new_screenshot = await self._take_screenshot()

            # Add to conversation
            conversation_history.append(
                {
                    "role": "model",
                    "parts": response.candidates[0].content.parts,
                }
            )
            conversation_history.append(
                {
                    "role": "user",
                    "parts": [
                        {"text": "Action executed. Here's the updated view:"},
                        {"inline_data": {"mime_type": "image/png", "data": new_screenshot}},
                    ],
                }
            )

        raise ValueError("Failed to extract recipe within step limit")

    async def _generate_with_computer_use(self, history: list) -> Any:
        """Generate response with Computer Use tool enabled.

        Args:
            history: Conversation history

        Returns:
            Model response
        """
        from google.genai import types

        tools = [
            types.Tool(
                computer_use=types.ComputerUse(
                    environment=types.Environment.ENVIRONMENT_BROWSER,
                )
            ),
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="submit_recipe",
                        description="Submit the extracted recipe data",
                        parameters=types.Schema(
                            type="object",
                            properties={
                                "title": types.Schema(type="string"),
                                "ingredients": types.Schema(
                                    type="array",
                                    items=types.Schema(type="string"),
                                ),
                                "instructions": types.Schema(
                                    type="array",
                                    items=types.Schema(type="string"),
                                ),
                                "prep_time": types.Schema(type="string"),
                                "cook_time": types.Schema(type="string"),
                                "servings": types.Schema(type="integer"),
                                "image_url": types.Schema(type="string"),
                            },
                            required=["title", "ingredients", "instructions"],
                        ),
                    ),
                ]
            ),
        ]

        return await self.client.aio.models.generate_content(
            model=self.MODEL,
            contents=history,
            config=types.GenerateContentConfig(
                tools=tools,
                thinking_config=types.ThinkingConfig(thinking_level="high"),
            ),
        )

    async def _take_screenshot(self) -> str:
        """Take a screenshot and return base64 encoded.

        Returns:
            Base64 encoded screenshot string
        """
        screenshot_bytes = await self.page.screenshot()
        return base64.b64encode(screenshot_bytes).decode("utf-8")

    async def _execute_action(self, action: BrowserAction) -> None:
        """Execute a browser action.

        Args:
            action: The action to execute
        """
        # Convert normalized coordinates (0-999) to actual pixels
        actual_x = None
        actual_y = None
        if action.x is not None and action.y is not None:
            actual_x = (action.x / 1000) * self.SCREEN_WIDTH
            actual_y = (action.y / 1000) * self.SCREEN_HEIGHT

        match action.action:
            case "click_at":
                if actual_x is not None and actual_y is not None:
                    await self.page.mouse.click(actual_x, actual_y)

            case "type_text_at":
                if actual_x is not None and actual_y is not None:
                    await self.page.mouse.click(actual_x, actual_y)
                if action.text:
                    await self.page.keyboard.type(action.text)

            case "scroll_document":
                delta = 300 if action.direction == "down" else -300
                await self.page.mouse.wheel(0, delta)

            case "scroll_at":
                if actual_x is not None and actual_y is not None:
                    await self.page.mouse.move(actual_x, actual_y)
                delta = 200 if action.direction == "down" else -200
                await self.page.mouse.wheel(0, delta)

            case "navigate":
                if action.url:
                    await self.page.goto(action.url)

            case "key_combination":
                if action.keys:
                    await self.page.keyboard.press(action.keys)

            case "wait_5_seconds":
                await self.page.wait_for_timeout(5000)

            case "go_back":
                await self.page.go_back()

    def _extract_actions(self, response: Any) -> list[BrowserAction]:
        """Extract browser actions from model response.

        Args:
            response: Model response

        Returns:
            List of browser actions to execute
        """
        actions = []
        for part in response.candidates[0].content.parts:
            if hasattr(part, "function_call"):
                fc = part.function_call
                if fc.name in [
                    "click_at",
                    "type_text_at",
                    "scroll_document",
                    "scroll_at",
                    "navigate",
                    "key_combination",
                    "wait_5_seconds",
                    "go_back",
                ]:
                    actions.append(
                        BrowserAction(
                            action=fc.name,
                            **dict(fc.args),
                        )
                    )
        return actions

    def _has_recipe_submission(self, response: Any) -> bool:
        """Check if model submitted the recipe.

        Args:
            response: Model response

        Returns:
            True if recipe was submitted
        """
        return any(
            hasattr(part, "function_call") and part.function_call.name == "submit_recipe"
            for part in response.candidates[0].content.parts
        )

    def _extract_recipe_data(self, response: Any) -> dict:
        """Extract recipe data from submission function call.

        Args:
            response: Model response with recipe submission

        Returns:
            Recipe data dictionary

        Raises:
            ValueError: If no recipe submission found
        """
        for part in response.candidates[0].content.parts:
            if hasattr(part, "function_call") and part.function_call.name == "submit_recipe":
                return dict(part.function_call.args)
        raise ValueError("No recipe submission found")
