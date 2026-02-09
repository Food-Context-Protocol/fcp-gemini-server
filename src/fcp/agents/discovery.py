"""Food Discovery Agent.

This agent autonomously discovers new food experiences based on
the user's taste profile and preferences. It uses:
- Google Search grounding for real-time restaurant/recipe discovery
- Extended thinking for matching preferences
- JSON mode + Grounding for structured results
"""

import logging
from typing import Any

from fcp.security import (
    build_discovery_prompt,
    build_recipe_discovery_prompt,
    build_restaurant_discovery_prompt,
    build_seasonal_discovery_prompt,
)
from fcp.services.gemini import GeminiClient, gemini

logger = logging.getLogger(__name__)


class FoodDiscoveryAgent:
    """Autonomous agent that discovers new food experiences."""

    def __init__(self, user_id: str, gemini: GeminiClient | None = None):
        self.user_id = user_id
        self._gemini = gemini

    def _gemini_client(self) -> GeminiClient:
        return self._gemini or gemini

    def _extract_recommendations(self, data: Any) -> list[dict[str, Any]]:
        """Robustly extract recommendations and flatten nested details.

        Handles:
        1. {'recommendations': [...]}
        2. [...] (top-level list)
        """
        raw_list = []
        if isinstance(data, list):
            raw_list = data
        elif isinstance(data, dict):
            for key in ["recommendations", "restaurants", "recipes", "seasonal_discoveries", "results", "items"]:
                if key in data and isinstance(data[key], list):
                    raw_list = data[key]
                    break
            if not raw_list and ("name" in data or "title" in data):
                raw_list = [data]

        flattened = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue

            # Flatten 'details' if it exists
            details = item.get("details", {})
            if isinstance(details, dict) and details:
                # Merge details into top-level.
                # Use details to override top-level for specific known fields if they exist there
                merged = {**item, **details}
                flattened.append(merged)
            else:
                flattened.append(item)

        logger.debug("Extracted %d recommendations", len(flattened))
        if flattened:
            logger.debug("First recommendation keys: %s", list(flattened[0].keys()))

        return flattened

    async def run_discovery(
        self,
        taste_profile: dict,
        location: str | None = None,
        discovery_type: str = "all",
        count: int = 5,
    ) -> dict[str, Any]:
        prompt = build_discovery_prompt(
            taste_profile=taste_profile,
            location=location,
            discovery_type=discovery_type,
            count=count,
        )

        result = await self._gemini_client().generate_json_with_grounding(prompt)

        if not isinstance(result, dict):
            return {
                "user_id": self.user_id,
                "discovery_type": discovery_type,
                "location": location,
                "recommendations": [],
                "sources": [],
            }

        data = result.get("data")
        recommendations = self._extract_recommendations(data)

        return {
            "user_id": self.user_id,
            "discovery_type": discovery_type,
            "location": location,
            "recommendations": recommendations,
            "sources": result.get("sources", []),
        }

    async def discover_restaurants(
        self,
        taste_profile: dict,
        location: str,
        occasion: str | None = None,
    ) -> dict[str, Any]:
        prompt = build_restaurant_discovery_prompt(
            taste_profile=taste_profile,
            location=location,
            occasion=occasion,
        )

        result = await self._gemini_client().generate_json_with_grounding(prompt)

        if not isinstance(result, dict):
            return {"user_id": self.user_id, "restaurants": [], "sources": []}

        data = result.get("data")
        recommendations = self._extract_recommendations(data)

        return {
            "user_id": self.user_id,
            "location": location,
            "occasion": occasion,
            "restaurants": recommendations,
            "sources": result.get("sources", []),
        }

    async def discover_recipes(
        self,
        taste_profile: dict,
        available_ingredients: list[str] | None = None,
        dietary_restrictions: list[str] | None = None,
    ) -> dict[str, Any]:
        prompt = build_recipe_discovery_prompt(
            taste_profile=taste_profile,
            available_ingredients=available_ingredients,
            dietary_restrictions=dietary_restrictions,
        )

        result = await self._gemini_client().generate_json_with_grounding(prompt)

        if not isinstance(result, dict):
            return {"user_id": self.user_id, "recipes": [], "sources": []}

        data = result.get("data")
        recommendations = self._extract_recommendations(data)

        return {
            "user_id": self.user_id,
            "recipes": recommendations,
            "sources": result.get("sources", []),
        }

    async def discover_seasonal(
        self,
        taste_profile: dict,
        location: str,
        current_month: int,
    ) -> dict[str, Any]:
        month_names = [
            "",
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        month_name = month_names[current_month]

        prompt = build_seasonal_discovery_prompt(
            taste_profile=taste_profile,
            location=location,
            month_name=month_name,
        )

        result = await self._gemini_client().generate_json_with_grounding(prompt)

        if not isinstance(result, dict):
            return {"user_id": self.user_id, "seasonal_discoveries": [], "sources": []}

        data = result.get("data")
        recommendations = self._extract_recommendations(data)

        return {
            "user_id": self.user_id,
            "location": location,
            "month": month_name,
            "seasonal_discoveries": recommendations,
            "sources": result.get("sources", []),
        }

    def _get_type_focus(self, discovery_type: str) -> str:
        type_map = {
            "restaurant": "restaurant",
            "recipe": "recipe",
            "ingredient": "ingredient",
            "all": "restaurant, recipe, and ingredient",
        }
        return type_map.get(discovery_type, "food")
