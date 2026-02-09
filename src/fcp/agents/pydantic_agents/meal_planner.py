"""Multi-turn meal planning agent using Thought Signatures.

This agent maintains conversation state across multiple interactions,
allowing users to iteratively refine their meal plans.
"""

from typing import Any

import logfire
from pydantic import BaseModel, Field

from fcp.services.conversation_state import ConversationState


class MealPlanDay(BaseModel):
    """A single day in the meal plan."""

    date: str
    breakfast: str | None = None
    lunch: str | None = None
    dinner: str | None = None
    snacks: list[str] = Field(default_factory=list)
    estimated_calories: int | None = None
    notes: str | None = None


class MealPlan(BaseModel):
    """Complete meal plan with multiple days."""

    days: list[MealPlanDay]
    shopping_list: list[str] = Field(default_factory=list)
    dietary_notes: str | None = None
    total_estimated_cost: float | None = None


class MealPlannerAgent:
    """Multi-turn meal planning agent using Thought Signatures.

    This agent maintains conversation state across multiple interactions,
    allowing users to iteratively refine their meal plan.

    Example session:
        1. User: "Plan my meals for next week"
        2. Agent: [generates initial plan]
        3. User: "Make Tuesday vegetarian"
        4. Agent: [modifies Tuesday, remembers full context]
        5. User: "Add more protein to all lunches"
        6. Agent: [adjusts all lunches with full plan awareness]
    """

    MODEL = "gemini-3-flash-preview"

    def __init__(self, user_id: str):
        """Initialize the meal planner agent.

        Args:
            user_id: The user's ID
        """
        self.user_id = user_id
        self.conversation = ConversationState()
        self.current_plan: MealPlan | None = None

    async def start_planning(
        self,
        days: int = 7,
        dietary_preferences: list[str] | None = None,
        budget: str | None = None,
        taste_profile: dict[str, Any] | None = None,
    ) -> MealPlan:
        """Start a new meal planning session.

        Args:
            days: Number of days to plan
            dietary_preferences: List of dietary preferences
            budget: Budget description
            taste_profile: User's taste profile from history

        Returns:
            Initial meal plan
        """
        with logfire.span("meal_planner.start", days=days):
            prompt = self._build_initial_prompt(days, dietary_preferences, budget, taste_profile)

            self.conversation.add_user_message(prompt)

            response = await self._generate_with_tools()

            self.conversation.add_model_response(response)

            # Execute any function calls (e.g., fetch pantry items)
            if self._has_function_calls(response):
                results = await self._execute_function_calls(response)
                self.conversation.add_function_responses(results)
                response = await self._generate_with_tools()
                self.conversation.add_model_response(response)

            # Parse the final meal plan
            self.current_plan = self._extract_meal_plan(response)

            return self.current_plan

    async def refine_plan(self, instruction: str) -> MealPlan:
        """Refine the current meal plan with a new instruction.

        The thought signature ensures the model remembers all previous
        decisions and can make coherent modifications.

        Args:
            instruction: Refinement instruction (e.g., "Make Tuesday vegetarian")

        Returns:
            Updated meal plan
        """
        with logfire.span("meal_planner.refine", instruction=instruction):
            self.conversation.add_user_message(instruction)

            response = await self._generate_with_tools()

            self.conversation.add_model_response(response)

            # Execute function calls if needed
            if self._has_function_calls(response):
                results = await self._execute_function_calls(response)
                self.conversation.add_function_responses(results)
                response = await self._generate_with_tools()
                self.conversation.add_model_response(response)

            self.current_plan = self._extract_meal_plan(response)

            return self.current_plan

    async def generate_shopping_list(self) -> list[str]:
        """Generate a consolidated shopping list from the current plan.

        Returns:
            List of items to purchase
        """
        with logfire.span("meal_planner.shopping_list"):
            self.conversation.add_user_message(
                "Generate a consolidated shopping list for this meal plan. "
                "Group items by category (produce, dairy, meat, pantry, etc.) "
                "and include quantities."
            )

            response = await self._generate_with_tools()
            self.conversation.add_model_response(response)

            # May call pantry check function
            if self._has_function_calls(response):
                results = await self._execute_function_calls(response)
                self.conversation.add_function_responses(results)
                response = await self._generate_with_tools()
                self.conversation.add_model_response(response)

            return self._extract_shopping_list(response)

    async def _generate_with_tools(self) -> Any:
        """Generate with function calling tools.

        Returns:
            Model response
        """
        from google import genai
        from google.genai import types

        client = genai.Client()

        tools = [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="get_pantry_items",
                        description="Get user's current pantry items to avoid duplicate purchases",
                        parameters=types.Schema(
                            type="object",
                            properties={},
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="get_food_history",
                        description="Get user's recent food logs to avoid repetition",
                        parameters=types.Schema(
                            type="object",
                            properties={
                                "days": types.Schema(type="integer", description="Number of days to look back"),
                            },
                        ),
                    ),
                    types.FunctionDeclaration(
                        name="check_recipe_exists",
                        description="Check if user has a saved recipe for a dish",
                        parameters=types.Schema(
                            type="object",
                            properties={
                                "dish_name": types.Schema(type="string"),
                            },
                            required=["dish_name"],
                        ),
                    ),
                ]
            )
        ]

        return await client.aio.models.generate_content(
            model=self.MODEL,
            contents=self.conversation.to_contents(),
            config=types.GenerateContentConfig(
                tools=tools,
                thinking_config=types.ThinkingConfig(thinking_level="high"),
            ),
        )

    def _build_initial_prompt(
        self,
        days: int,
        dietary_preferences: list[str] | None,
        budget: str | None,
        taste_profile: dict[str, Any] | None,
    ) -> str:
        """Build the initial planning prompt.

        Args:
            days: Number of days to plan
            dietary_preferences: Dietary preferences
            budget: Budget description
            taste_profile: User's taste profile

        Returns:
            Initial prompt string
        """
        prompt = f"Create a {days}-day meal plan for me.\n\n"

        if dietary_preferences:
            prompt += f"Dietary preferences: {', '.join(dietary_preferences)}\n"

        if budget:
            prompt += f"Budget: {budget}\n"

        if taste_profile:
            prompt += f"Taste profile: {taste_profile}\n"

        prompt += """
Please create a balanced, varied meal plan with:
- Breakfast, lunch, dinner, and optional snacks for each day
- Estimated calories per day
- A consolidated shopping list
- Brief notes on prep suggestions

First, check my pantry and recent food history to personalize the plan.
"""

        return prompt

    def _has_function_calls(self, response: Any) -> bool:
        """Check if response contains function calls.

        Args:
            response: Model response

        Returns:
            True if function calls are present
        """
        return any(
            hasattr(part, "function_call") and part.function_call for part in response.candidates[0].content.parts
        )

    async def _execute_function_calls(self, response: Any) -> list[dict[str, Any]]:
        """Execute function calls and return results.

        Args:
            response: Model response with function calls

        Returns:
            List of function results
        """
        results = []

        for part in response.candidates[0].content.parts:
            if hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                name = fc.name
                args = dict(fc.args) if fc.args else {}

                # Execute the function
                result = await self._call_function(name, args)
                results.append({"name": name, "result": result})

        return results

    async def _call_function(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Call a function by name.

        Args:
            name: Function name
            args: Function arguments

        Returns:
            Function result
        """
        match name:
            case "get_pantry_items":
                # In real implementation, this would query Firestore
                return {"items": [], "message": "Pantry check complete"}

            case "get_food_history":
                days = args.get("days", 7)
                # In real implementation, this would query food logs
                return {"logs": [], "days_checked": days}

            case "check_recipe_exists":
                dish_name = args.get("dish_name", "")
                # In real implementation, this would check recipes
                return {"exists": False, "dish_name": dish_name}

        return {"error": f"Unknown function: {name}"}

    def _extract_meal_plan(self, response: Any) -> MealPlan:
        """Extract meal plan from model response.

        Args:
            response: Model response

        Returns:
            Parsed MealPlan
        """
        import json

        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                # Try to parse JSON from the response
                try:
                    # Find JSON in the text
                    text = part.text
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start >= 0 and end > start:
                        data = json.loads(text[start:end])
                        if "days" in data:
                            days = [MealPlanDay(**d) for d in data["days"]]
                            return MealPlan(
                                days=days,
                                shopping_list=data.get("shopping_list", []),
                                dietary_notes=data.get("dietary_notes"),
                                total_estimated_cost=data.get("total_estimated_cost"),
                            )
                except json.JSONDecodeError:
                    # Continue searching for valid JSON in other response parts
                    # If no valid JSON is found, we fall through to return empty plan
                    pass

        # Return empty plan if parsing fails
        return MealPlan(days=[])

    def _extract_shopping_list(self, response: Any) -> list[str]:
        """Extract shopping list from model response.

        Args:
            response: Model response

        Returns:
            List of shopping items
        """
        import json

        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                try:
                    # Try to parse JSON
                    text = part.text
                    start = text.find("[")
                    end = text.rfind("]") + 1
                    if start >= 0 and end > start:
                        return json.loads(text[start:end])
                except json.JSONDecodeError:
                    # Fall back to line-by-line parsing
                    items = []
                    for line in part.text.split("\n"):
                        line = line.strip()
                        if line.startswith("- ") or line.startswith("* "):
                            items.append(line[2:])
                        elif line and not line.startswith("#"):
                            items.append(line)
                    return items

        return []
