"""Pydantic AI-based Food Discovery Agent.

This agent provides the same functionality as the original FoodDiscoveryAgent
but with type-safe Pydantic models for inputs and outputs.

Note: Uses the existing Gemini client with grounding support, then validates
outputs through Pydantic models. Full Pydantic AI agent pattern can be adopted
once pydantic-ai adds native grounding support for Gemini.
"""

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from fcp.security import (
    build_discovery_prompt,
    build_recipe_discovery_prompt,
    build_restaurant_discovery_prompt,
    build_seasonal_discovery_prompt,
)
from fcp.services.gemini import GeminiClient, gemini

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models for Type-Safe Inputs
# ============================================================================


class TasteProfile(BaseModel):
    """User's taste preferences for personalized recommendations."""

    top_cuisines: list[str] = Field(default_factory=list, description="Preferred cuisine types")
    spice_preference: str = Field(default="medium", description="Spice level: low, medium, or high")
    dietary_restrictions: list[str] = Field(default_factory=list, description="Dietary restrictions")
    favorite_dishes: list[str] = Field(default_factory=list, description="User's favorite dishes")
    disliked_ingredients: list[str] = Field(default_factory=list, description="Ingredients to avoid")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for prompt building."""
        return self.model_dump(exclude_none=True)


class DiscoveryRequest(BaseModel):
    """Request parameters for general food discovery."""

    taste_profile: TasteProfile
    location: str | None = Field(default=None, description="Geographic location for recommendations")
    discovery_type: str = Field(default="all", description="Type: restaurant, recipe, ingredient, or all")
    count: int = Field(default=5, ge=1, le=20, description="Number of recommendations")


class RestaurantDiscoveryRequest(BaseModel):
    """Request parameters for restaurant discovery."""

    taste_profile: TasteProfile
    location: str = Field(description="Geographic location (required for restaurants)")
    occasion: str | None = Field(default=None, description="e.g., date night, family dinner")


class RecipeDiscoveryRequest(BaseModel):
    """Request parameters for recipe discovery."""

    taste_profile: TasteProfile
    available_ingredients: list[str] | None = Field(default=None, description="Ingredients on hand")
    dietary_restrictions: list[str] | None = Field(default=None, description="Dietary constraints")


class SeasonalDiscoveryRequest(BaseModel):
    """Request parameters for seasonal food discovery."""

    taste_profile: TasteProfile
    location: str = Field(description="Geographic location for seasonal context")
    current_month: int = Field(ge=1, le=12, description="Month number (1-12)")


# ============================================================================
# Pydantic Models for Type-Safe Outputs
# ============================================================================


class GroundingSource(BaseModel):
    """Source information from Google Search grounding."""

    uri: str = Field(description="URL of the source")
    title: str = Field(default="", description="Title of the source")


class Recommendation(BaseModel):
    """A single food recommendation with details."""

    name: str = Field(description="Name of the restaurant, recipe, or item")
    reason: str = Field(default="", description="Why this matches the user's preferences")
    match_score: float = Field(default=0.0, ge=0, le=1, description="How well it matches (0-1)")
    cuisine: str = Field(default="", description="Cuisine type")
    price_range: str = Field(default="", description="Price indicator (e.g., $$)")
    address: str = Field(default="", description="Location address (for restaurants)")
    highlights: list[str] = Field(default_factory=list, description="Key features or highlights")

    model_config = ConfigDict(extra="allow")  # Allow additional fields from API response


class DiscoveryResult(BaseModel):
    """Result from a food discovery operation."""

    user_id: str = Field(description="User identifier")
    discovery_type: str = Field(default="all", description="Type of discovery performed")
    location: str | None = Field(default=None, description="Location context")
    recommendations: list[Recommendation] = Field(default_factory=list, description="List of recommendations")
    sources: list[GroundingSource] = Field(default_factory=list, description="Grounding sources")


class RestaurantResult(BaseModel):
    """Result from restaurant discovery."""

    user_id: str
    location: str
    occasion: str | None = None
    restaurants: list[Recommendation] = Field(default_factory=list)
    sources: list[GroundingSource] = Field(default_factory=list)


class RecipeResult(BaseModel):
    """Result from recipe discovery."""

    user_id: str
    recipes: list[Recommendation] = Field(default_factory=list)
    sources: list[GroundingSource] = Field(default_factory=list)


class SeasonalResult(BaseModel):
    """Result from seasonal discovery."""

    user_id: str
    location: str
    month: str
    seasonal_discoveries: list[Recommendation] = Field(default_factory=list)
    sources: list[GroundingSource] = Field(default_factory=list)


# ============================================================================
# Pydantic AI Discovery Agent
# ============================================================================


class PydanticDiscoveryAgent:
    """Type-safe food discovery agent using Pydantic models.

    This agent wraps the Gemini API with grounding support and provides
    type-safe inputs and outputs via Pydantic models. It's designed to
    be a drop-in replacement for the original FoodDiscoveryAgent with
    better type safety and validation.

    Usage:
        agent = PydanticDiscoveryAgent(user_id="user123")

        # Using Pydantic models
        request = DiscoveryRequest(
            taste_profile=TasteProfile(top_cuisines=["Italian", "Japanese"]),
            location="San Francisco",
            discovery_type="restaurant",
            count=5,
        )
        result = await agent.discover(request)

        # Or with raw dict (for backward compatibility)
        result = await agent.run_discovery(
            taste_profile={"top_cuisines": ["Italian"]},
            location="San Francisco",
        )
    """

    MONTH_NAMES = [
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

    def __init__(self, user_id: str, gemini: GeminiClient | None = None):
        self.user_id = user_id
        self._gemini = gemini

    def _gemini_client(self) -> GeminiClient:
        return self._gemini or gemini

    def _extract_recommendations(self, data: Any) -> list[dict[str, Any]]:
        """Robustly extract recommendations and flatten nested details."""
        raw_list = self._normalize_to_list(data)

        flattened = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue

            details = item.get("details", {})
            if isinstance(details, dict) and details:
                merged = {**item, **details}
                flattened.append(merged)
            else:
                flattened.append(item)

        return flattened

    @staticmethod
    def _normalize_to_list(data: Any) -> list[Any]:
        """Normalize a Gemini response (list or dict) into a flat list of items."""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return PydanticDiscoveryAgent._extract_list_from_dict(data)
        return []

    @staticmethod
    def _extract_list_from_dict(data: dict[str, Any]) -> list[Any]:
        """Extract a recommendation list from a dict response with known keys."""
        known_keys = ["recommendations", "restaurants", "recipes", "seasonal_discoveries", "results", "items"]
        for key in known_keys:
            if key in data and isinstance(data[key], list):
                return data[key]
        if "name" in data or "title" in data:
            return [data]
        return []

    def _parse_recommendations(self, raw_list: list[dict[str, Any]]) -> list[Recommendation]:
        """Parse raw recommendation dicts into validated Pydantic models."""
        recommendations = []
        for item in raw_list:
            try:
                # Map common field variations
                normalized = {
                    "name": item.get("name") or item.get("title") or item.get("dish_name", ""),
                    "reason": item.get("reason") or item.get("why") or item.get("description", ""),
                    "match_score": float(item.get("match_score", 0) or item.get("score", 0) or 0),
                    "cuisine": item.get("cuisine") or item.get("cuisine_type", ""),
                    "price_range": item.get("price_range") or item.get("price", ""),
                    "address": item.get("address") or item.get("location", ""),
                    "highlights": item.get("highlights") or item.get("features", []),
                }
                # Include any extra fields
                for k, v in item.items():
                    if k not in normalized and k != "details":
                        normalized[k] = v

                recommendations.append(Recommendation(**normalized))
            except Exception as e:
                logger.warning("Failed to parse recommendation: %s - %s", item, e)
                # Still include with minimal data
                recommendations.append(Recommendation(name=str(item.get("name", "Unknown"))))

        return recommendations

    def _parse_sources(self, sources: list[dict[str, Any]] | None) -> list[GroundingSource]:
        """Parse grounding sources into Pydantic models."""
        if not sources:
            return []
        return [GroundingSource(uri=s.get("uri", ""), title=s.get("title", "")) for s in sources if s.get("uri")]

    # ========================================================================
    # Type-safe API using Pydantic models
    # ========================================================================

    async def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        """Run discovery with type-safe request/response."""
        prompt = build_discovery_prompt(
            taste_profile=request.taste_profile.to_dict(),
            location=request.location,
            discovery_type=request.discovery_type,
            count=request.count,
        )

        result = await self._gemini_client().generate_json_with_grounding(prompt)

        if not isinstance(result, dict):
            return DiscoveryResult(
                user_id=self.user_id,
                discovery_type=request.discovery_type,
                location=request.location,
            )

        raw_recs = self._extract_recommendations(result.get("data"))
        recommendations = self._parse_recommendations(raw_recs)
        sources = self._parse_sources(result.get("sources"))

        return DiscoveryResult(
            user_id=self.user_id,
            discovery_type=request.discovery_type,
            location=request.location,
            recommendations=recommendations,
            sources=sources,
        )

    async def discover_restaurants_typed(self, request: RestaurantDiscoveryRequest) -> RestaurantResult:
        """Discover restaurants with type-safe request/response."""
        prompt = build_restaurant_discovery_prompt(
            taste_profile=request.taste_profile.to_dict(),
            location=request.location,
            occasion=request.occasion,
        )

        result = await self._gemini_client().generate_json_with_grounding(prompt)

        if not isinstance(result, dict):
            return RestaurantResult(user_id=self.user_id, location=request.location)

        raw_recs = self._extract_recommendations(result.get("data"))
        recommendations = self._parse_recommendations(raw_recs)
        sources = self._parse_sources(result.get("sources"))

        return RestaurantResult(
            user_id=self.user_id,
            location=request.location,
            occasion=request.occasion,
            restaurants=recommendations,
            sources=sources,
        )

    async def discover_recipes_typed(self, request: RecipeDiscoveryRequest) -> RecipeResult:
        """Discover recipes with type-safe request/response."""
        prompt = build_recipe_discovery_prompt(
            taste_profile=request.taste_profile.to_dict(),
            available_ingredients=request.available_ingredients,
            dietary_restrictions=request.dietary_restrictions,
        )

        result = await self._gemini_client().generate_json_with_grounding(prompt)

        if not isinstance(result, dict):
            return RecipeResult(user_id=self.user_id)

        raw_recs = self._extract_recommendations(result.get("data"))
        recommendations = self._parse_recommendations(raw_recs)
        sources = self._parse_sources(result.get("sources"))

        return RecipeResult(
            user_id=self.user_id,
            recipes=recommendations,
            sources=sources,
        )

    async def discover_seasonal_typed(self, request: SeasonalDiscoveryRequest) -> SeasonalResult:
        """Discover seasonal foods with type-safe request/response."""
        month_name = self.MONTH_NAMES[request.current_month]

        prompt = build_seasonal_discovery_prompt(
            taste_profile=request.taste_profile.to_dict(),
            location=request.location,
            month_name=month_name,
        )

        result = await self._gemini_client().generate_json_with_grounding(prompt)

        if not isinstance(result, dict):
            return SeasonalResult(user_id=self.user_id, location=request.location, month=month_name)

        raw_recs = self._extract_recommendations(result.get("data"))
        recommendations = self._parse_recommendations(raw_recs)
        sources = self._parse_sources(result.get("sources"))

        return SeasonalResult(
            user_id=self.user_id,
            location=request.location,
            month=month_name,
            seasonal_discoveries=recommendations,
            sources=sources,
        )

    # ========================================================================
    # Backward-compatible API (dict inputs, dict outputs)
    # ========================================================================

    async def run_discovery(
        self,
        taste_profile: dict,
        location: str | None = None,
        discovery_type: str = "all",
        count: int = 5,
    ) -> dict[str, Any]:
        """Run discovery with dict interface (backward compatible)."""
        request = DiscoveryRequest(
            taste_profile=TasteProfile(**taste_profile) if taste_profile else TasteProfile(),
            location=location,
            discovery_type=discovery_type,
            count=count,
        )
        result = await self.discover(request)
        return result.model_dump()

    async def discover_restaurants(
        self,
        taste_profile: dict,
        location: str,
        occasion: str | None = None,
    ) -> dict[str, Any]:
        """Discover restaurants with dict interface (backward compatible)."""
        request = RestaurantDiscoveryRequest(
            taste_profile=TasteProfile(**taste_profile) if taste_profile else TasteProfile(),
            location=location,
            occasion=occasion,
        )
        result = await self.discover_restaurants_typed(request)
        return result.model_dump()

    async def discover_recipes(
        self,
        taste_profile: dict,
        available_ingredients: list[str] | None = None,
        dietary_restrictions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Discover recipes with dict interface (backward compatible)."""
        request = RecipeDiscoveryRequest(
            taste_profile=TasteProfile(**taste_profile) if taste_profile else TasteProfile(),
            available_ingredients=available_ingredients,
            dietary_restrictions=dietary_restrictions,
        )
        result = await self.discover_recipes_typed(request)
        return result.model_dump()

    async def discover_seasonal(
        self,
        taste_profile: dict,
        location: str,
        current_month: int,
    ) -> dict[str, Any]:
        """Discover seasonal foods with dict interface (backward compatible)."""
        request = SeasonalDiscoveryRequest(
            taste_profile=TasteProfile(**taste_profile) if taste_profile else TasteProfile(),
            location=location,
            current_month=current_month,
        )
        result = await self.discover_seasonal_typed(request)
        return result.model_dump()
