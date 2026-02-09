"""Pydantic AI-based Media Processing Agent.

This agent processes food photos from camera roll, synced albums, or batch uploads
with type-safe models:
- Function calling for structured extraction
- Multimodal analysis for food detection
- Extended thinking for complex dishes
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from fcp.services.gemini import GeminiClient, gemini
from fcp.tools.function_definitions import MEDIA_PROCESSING_TOOLS

# ============================================================================
# Pydantic Models for Type-Safe Inputs
# ============================================================================


class PhotoBatchRequest(BaseModel):
    """Request parameters for batch photo processing."""

    image_urls: list[str] = Field(description="List of image URLs to process")
    auto_log: bool = Field(default=False, description="Whether to automatically create food logs")


class SinglePhotoRequest(BaseModel):
    """Request parameters for single photo processing."""

    image_url: str = Field(description="URL of the image to process")


class FilterImagesRequest(BaseModel):
    """Request parameters for filtering food images."""

    image_urls: list[str] = Field(description="List of image URLs to filter")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence to consider food")


class CreateEntriesRequest(BaseModel):
    """Request parameters for creating food log entries."""

    image_urls: list[str] = Field(description="List of food image URLs")
    default_venue: str | None = Field(default=None, description="Default venue for all entries")


class MealSequenceRequest(BaseModel):
    """Request parameters for meal sequence analysis."""

    image_urls: list[str] = Field(description="List of image URLs from the same meal")


# ============================================================================
# Pydantic Models for Type-Safe Outputs
# ============================================================================


class NutritionInfo(BaseModel):
    """Nutrition information for a dish."""

    calories: int | None = Field(default=None)
    protein_g: float | None = Field(default=None)
    carbs_g: float | None = Field(default=None)
    fat_g: float | None = Field(default=None)

    model_config = ConfigDict(extra="allow")


class VenueInfo(BaseModel):
    """Venue/restaurant information."""

    name: str | None = Field(default=None)
    type: str | None = Field(default=None)
    location_hint: str | None = Field(default=None)

    model_config = ConfigDict(extra="allow")


class Ingredient(BaseModel):
    """An ingredient detected in food."""

    name: str = Field(default="")
    quantity: str | None = Field(default=None)

    model_config = ConfigDict(extra="allow")


class PhotoAnalysis(BaseModel):
    """Analysis result for a single photo."""

    image_url: str
    is_food: bool = Field(default=False)
    confidence: float = Field(default=0.0)
    food_type: str | None = Field(default=None)
    dish_name: str | None = Field(default=None)
    cuisine: str | None = Field(default=None)
    cooking_method: str | None = Field(default=None)
    ingredients: list[Ingredient] = Field(default_factory=list)
    nutrition: NutritionInfo = Field(default_factory=NutritionInfo)
    venue: VenueInfo | None = Field(default=None)

    model_config = ConfigDict(extra="allow")


class PhotoBatchResult(BaseModel):
    """Result from batch photo processing."""

    total_processed: int
    food_detected: int
    non_food: int
    results: list[PhotoAnalysis]
    auto_logged: bool


class FilteredImage(BaseModel):
    """A filtered image with confidence."""

    url: str
    confidence: float


class FilterImagesResult(BaseModel):
    """Result from filtering food images."""

    food_images: list[FilteredImage]
    non_food_images: list[FilteredImage]
    food_count: int
    threshold_used: float


class FoodLogEntry(BaseModel):
    """A draft food log entry."""

    dish_name: str
    image_url: str
    cuisine: str | None = None
    ingredients: list[str] = Field(default_factory=list)
    nutrition: NutritionInfo = Field(default_factory=NutritionInfo)
    venue: str | None = None
    analysis_confidence: float = 0.0
    status: str = "draft"


class CourseInfo(BaseModel):
    """Information about a course in a meal."""

    dish_name: str | None = None
    image_url: str | None = None
    nutrition: NutritionInfo = Field(default_factory=NutritionInfo)


class MealSequenceResult(BaseModel):
    """Result from meal sequence analysis."""

    is_meal: bool
    message: str | None = None
    course_count: int = 0
    courses: list[CourseInfo] = Field(default_factory=list)
    total_nutrition: NutritionInfo = Field(default_factory=NutritionInfo)
    cuisines: list[str] = Field(default_factory=list)
    venue: VenueInfo | None = None


# ============================================================================
# Pydantic AI Media Processing Agent
# ============================================================================


class PydanticMediaProcessingAgent:
    """Type-safe media processing agent using Pydantic models.

    This agent wraps the Gemini API with function calling support and provides
    type-safe inputs and outputs via Pydantic models. It's designed to be a
    drop-in replacement for the original MediaProcessingAgent.

    Usage:
        agent = PydanticMediaProcessingAgent()

        # Using Pydantic models
        request = PhotoBatchRequest(
            image_urls=["https://example.com/food.jpg"],
            auto_log=True,
        )
        result = await agent.process_photo_batch_typed(request)

        # Or with raw dict (for backward compatibility)
        result = await agent.process_photo_batch(
            image_urls=["https://example.com/food.jpg"],
        )
    """

    def __init__(self, user_id: str | None = None, gemini: GeminiClient | None = None):
        self.user_id = user_id
        self._gemini = gemini

    def _gemini_client(self) -> GeminiClient:
        return self._gemini or gemini

    def _parse_function_calls(self, result: dict[str, Any], image_url: str) -> PhotoAnalysis:
        """Parse function calls into structured PhotoAnalysis."""
        analysis = PhotoAnalysis(
            image_url=image_url,
            is_food=False,
            confidence=0.0,
        )

        for call in result.get("function_calls", []):
            name = call.get("name", "")
            args = call.get("args", {})

            if name == "detect_food_in_image":
                analysis.is_food = args.get("is_food", False)
                analysis.confidence = args.get("confidence", 0.0)
                analysis.food_type = args.get("food_type")

            elif name == "identify_dish":
                analysis.dish_name = args.get("dish_name")
                analysis.cuisine = args.get("cuisine")
                analysis.cooking_method = args.get("cooking_method")

            elif name == "identify_ingredients":
                raw_ingredients = args.get("ingredients", [])
                analysis.ingredients = [
                    Ingredient(name=ing.get("name", ""), quantity=ing.get("quantity"))
                    if isinstance(ing, dict)
                    else Ingredient(name=str(ing))
                    for ing in raw_ingredients
                ]

            elif name == "extract_nutrition":
                analysis.nutrition = NutritionInfo(
                    calories=args.get("calories"),
                    protein_g=args.get("protein_g"),
                    carbs_g=args.get("carbs_g"),
                    fat_g=args.get("fat_g"),
                )

            elif name == "extract_venue_info":
                analysis.venue = self._parse_venue_info(args)

        return analysis

    @staticmethod
    def _parse_venue_info(args: dict[str, Any]) -> VenueInfo | None:
        """Parse venue info from function call args. Returns None if no venue_name."""
        venue_name = args.get("venue_name")
        if not venue_name:
            return None
        return VenueInfo(
            name=venue_name,
            type=args.get("venue_type"),
            location_hint=args.get("location_hint"),
        )

    # ========================================================================
    # Type-safe API using Pydantic models
    # ========================================================================

    async def process_single_photo_typed(self, request: SinglePhotoRequest) -> PhotoAnalysis:
        """Process a single photo with type-safe request/response."""
        prompt = """Analyze this image for food content.

First, determine if this image contains food using detect_food_in_image.

If it IS food:
1. Use identify_dish to identify the dish
2. Use identify_ingredients to list ingredients
3. Use extract_nutrition to estimate nutrition
4. Use extract_venue_info if any venue/restaurant info is visible

If it's NOT food, just report that with detect_food_in_image.

Be thorough but efficient."""

        result = await self._gemini_client().generate_with_tools(
            prompt=prompt,
            tools=MEDIA_PROCESSING_TOOLS,
            image_url=request.image_url,
        )

        return self._parse_function_calls(result, request.image_url)

    async def process_photo_batch_typed(self, request: PhotoBatchRequest) -> PhotoBatchResult:
        """Process a batch of photos with type-safe request/response."""
        results = []

        for url in request.image_urls:
            single_request = SinglePhotoRequest(image_url=url)
            result = await self.process_single_photo_typed(single_request)
            results.append(result)

        food_count = sum(bool(r.is_food) for r in results)

        return PhotoBatchResult(
            total_processed=len(request.image_urls),
            food_detected=food_count,
            non_food=len(request.image_urls) - food_count,
            results=results,
            auto_logged=request.auto_log,
        )

    async def filter_food_images_typed(self, request: FilterImagesRequest) -> FilterImagesResult:
        """Filter images to identify food with type-safe request/response."""
        food_images = []
        non_food_images = []

        prompt = """Quickly determine if this image contains food.
Use detect_food_in_image to report your finding."""

        for url in request.image_urls:
            result = await self._gemini_client().generate_with_tools(
                prompt=prompt,
                tools=[MEDIA_PROCESSING_TOOLS[0]],
                image_url=url,
            )

            is_food = False
            confidence = 0.0

            for call in result.get("function_calls", []):
                if call.get("name") == "detect_food_in_image":
                    is_food = call.get("args", {}).get("is_food", False)
                    confidence = call.get("args", {}).get("confidence", 0.0)
                    break

            filtered_image = FilteredImage(url=url, confidence=confidence)
            if is_food and confidence >= request.confidence_threshold:
                food_images.append(filtered_image)
            else:
                non_food_images.append(filtered_image)

        return FilterImagesResult(
            food_images=food_images,
            non_food_images=non_food_images,
            food_count=len(food_images),
            threshold_used=request.confidence_threshold,
        )

    async def filter_food_photos_typed(self, request: "FilterImagesRequest") -> "FilterImagesResult":
        """Backward compatible alias for filter_food_images_typed."""
        return await self.filter_food_images_typed(request)

    async def create_food_log_entries_typed(self, request: CreateEntriesRequest) -> list[FoodLogEntry]:
        """Create food log entry drafts with type-safe request/response."""
        entries = []

        for url in request.image_urls:
            single_request = SinglePhotoRequest(image_url=url)
            analysis = await self.process_single_photo_typed(single_request)

            if analysis.is_food:
                entry = FoodLogEntry(
                    dish_name=analysis.dish_name or "Unknown Dish",
                    image_url=url,
                    cuisine=analysis.cuisine,
                    ingredients=[ing.name for ing in analysis.ingredients],
                    nutrition=analysis.nutrition,
                    venue=analysis.venue.name if analysis.venue else request.default_venue,
                    analysis_confidence=analysis.confidence,
                    status="draft",
                )
                entries.append(entry)

        return entries

    async def analyze_meal_sequence_typed(self, request: MealSequenceRequest) -> MealSequenceResult:
        """Analyze a sequence of photos as a complete meal with type-safe request/response."""
        courses = []

        for url in request.image_urls:
            single_request = SinglePhotoRequest(image_url=url)
            analysis = await self.process_single_photo_typed(single_request)
            if analysis.is_food:
                courses.append(analysis)

        if not courses:
            return MealSequenceResult(
                is_meal=False,
                message="No food detected in images",
            )

        total_nutrition = NutritionInfo(
            calories=0,
            protein_g=0.0,
            carbs_g=0.0,
            fat_g=0.0,
        )

        for course in courses:
            nutrition = course.nutrition
            total_nutrition.calories = (total_nutrition.calories or 0) + (nutrition.calories or 0)
            total_nutrition.protein_g = (total_nutrition.protein_g or 0) + (nutrition.protein_g or 0)
            total_nutrition.carbs_g = (total_nutrition.carbs_g or 0) + (nutrition.carbs_g or 0)
            total_nutrition.fat_g = (total_nutrition.fat_g or 0) + (nutrition.fat_g or 0)

        cuisines = list({c.cuisine for c in courses if c.cuisine})

        course_infos = [
            CourseInfo(
                dish_name=c.dish_name,
                image_url=c.image_url,
                nutrition=c.nutrition,
            )
            for c in courses
        ]

        return MealSequenceResult(
            is_meal=True,
            course_count=len(courses),
            courses=course_infos,
            total_nutrition=total_nutrition,
            cuisines=cuisines,
            venue=courses[0].venue if courses else None,
        )

    # ========================================================================
    # Backward-compatible API (dict inputs, dict outputs)
    # ========================================================================

    def _photo_analysis_to_dict(self, result: PhotoAnalysis) -> dict[str, Any]:
        """Convert PhotoAnalysis to legacy dict format.

        This is used by backward-compatible methods to avoid duplicating
        the conversion logic.
        """
        output: dict[str, Any] = {
            "image_url": result.image_url,
            "is_food": result.is_food,
            "confidence": result.confidence,
        }

        if result.food_type:
            output["food_type"] = result.food_type
        if result.dish_name:
            output["dish_name"] = result.dish_name
        if result.cuisine:
            output["cuisine"] = result.cuisine
        if result.cooking_method:
            output["cooking_method"] = result.cooking_method
        if result.ingredients:
            output["ingredients"] = [
                {"name": ing.name, "quantity": ing.quantity} if ing.quantity else {"name": ing.name}
                for ing in result.ingredients
            ]
        if result.nutrition.calories is not None:
            output["nutrition"] = {
                "calories": result.nutrition.calories,
                "protein_g": result.nutrition.protein_g,
                "carbs_g": result.nutrition.carbs_g,
                "fat_g": result.nutrition.fat_g,
            }
        if result.venue:
            output["venue"] = {
                "name": result.venue.name,
                "type": result.venue.type,
                "location_hint": result.venue.location_hint,
            }

        return output

    async def process_single_photo(self, image_url: str) -> dict[str, Any]:
        """Process a single photo with dict interface (backward compatible)."""
        request = SinglePhotoRequest(image_url=image_url)
        result = await self.process_single_photo_typed(request)
        return self._photo_analysis_to_dict(result)

    async def process_photo_batch(
        self,
        image_urls: list[str],
        auto_log: bool = False,
    ) -> dict[str, Any]:
        """Process a batch of photos with dict interface (backward compatible)."""
        request = PhotoBatchRequest(image_urls=image_urls, auto_log=auto_log)
        result = await self.process_photo_batch_typed(request)

        return {
            "total_processed": result.total_processed,
            "food_detected": result.food_detected,
            "non_food": result.non_food,
            "results": [self._photo_analysis_to_dict(r) for r in result.results],
            "auto_logged": result.auto_logged,
        }

    async def filter_food_images(
        self,
        image_urls: list[str],
        confidence_threshold: float = 0.7,
    ) -> dict[str, Any]:
        """Filter images to identify food with dict interface (backward compatible)."""
        request = FilterImagesRequest(image_urls=image_urls, confidence_threshold=confidence_threshold)
        result = await self.filter_food_images_typed(request)

        return {
            "food_images": [{"url": img.url, "confidence": img.confidence} for img in result.food_images],
            "non_food_images": [{"url": img.url, "confidence": img.confidence} for img in result.non_food_images],
            "food_count": result.food_count,
            "threshold_used": result.threshold_used,
        }

    async def filter_food_photos(
        self,
        image_urls: list[str],
        confidence_threshold: float = 0.7,
    ) -> dict[str, Any]:
        """Backward compatible alias for filter_food_images."""
        return await self.filter_food_images(image_urls=image_urls, confidence_threshold=confidence_threshold)

    async def create_food_log_entries(
        self,
        image_urls: list[str],
        default_venue: str | None = None,
    ) -> list[dict[str, Any]]:
        """Create food log entry drafts with dict interface (backward compatible)."""
        request = CreateEntriesRequest(image_urls=image_urls, default_venue=default_venue)
        results = await self.create_food_log_entries_typed(request)

        return [
            {
                "dish_name": entry.dish_name,
                "image_url": entry.image_url,
                "cuisine": entry.cuisine,
                "ingredients": entry.ingredients,
                "nutrition": entry.nutrition.model_dump(),
                "venue": entry.venue,
                "analysis_confidence": entry.analysis_confidence,
                "status": entry.status,
            }
            for entry in results
        ]

    async def analyze_meal_sequence(
        self,
        image_urls: list[str],
    ) -> dict[str, Any]:
        """Analyze a sequence of photos as a complete meal with dict interface (backward compatible)."""
        request = MealSequenceRequest(image_urls=image_urls)
        result = await self.analyze_meal_sequence_typed(request)

        if not result.is_meal:
            return {
                "is_meal": False,
                "message": result.message,
            }

        return {
            "is_meal": True,
            "course_count": result.course_count,
            "courses": [
                {
                    "dish_name": c.dish_name,
                    "image_url": c.image_url,
                    "nutrition": c.nutrition.model_dump(),
                }
                for c in result.courses
            ],
            "total_nutrition": result.total_nutrition.model_dump(),
            "cuisines": result.cuisines,
            "venue": result.venue.model_dump() if result.venue else None,
        }


# Backward compatible type aliases.
FilterPhotosRequest = FilterImagesRequest
FilterPhotosResult = FilterImagesResult
