"""Media Processing Agent.

This agent autonomously processes food photos from camera roll,
synced albums, or batch uploads. It uses:
- Function calling for structured extraction
- Multimodal analysis for food detection
- Extended thinking for complex dishes
"""

from typing import Any

from fcp.services.gemini import GeminiClient, gemini
from fcp.tools.function_definitions import MEDIA_PROCESSING_TOOLS


class MediaProcessingAgent:
    """Agent that processes camera roll / synced photos for food."""

    def __init__(self, user_id: str | None = None, gemini: GeminiClient | None = None):
        self.user_id = user_id
        self._gemini = gemini

    def _gemini_client(self) -> GeminiClient:
        return self._gemini or gemini

    async def process_photo_batch(
        self,
        image_urls: list[str],
        auto_log: bool = False,
    ) -> dict[str, Any]:
        """
        Process a batch of photos to identify and analyze food.

        Args:
            image_urls: List of image URLs to process
            auto_log: Whether to automatically create food logs

        Returns:
            dict with processing results for each image
        """
        results = []

        for url in image_urls:
            result = await self.process_single_photo(url)
            results.append(result)

        # Summary statistics
        food_count = sum(bool(r.get("is_food", False)) for r in results)

        return {
            "total_processed": len(image_urls),
            "food_detected": food_count,
            "non_food": len(image_urls) - food_count,
            "results": results,
            "auto_logged": auto_log,
        }

    async def process_single_photo(self, image_url: str) -> dict[str, Any]:
        """
        Process a single photo to detect and analyze food.

        Args:
            image_url: URL of the image to process

        Returns:
            dict with analysis results
        """
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
            image_url=image_url,
        )

        # Parse function calls into structured result
        analysis = {
            "image_url": image_url,
            "is_food": False,
            "confidence": 0.0,
        }

        for call in result.get("function_calls", []):
            name = call["name"]
            args = call["args"]

            if name == "detect_food_in_image":
                analysis["is_food"] = args.get("is_food", False)
                analysis["confidence"] = args.get("confidence", 0.0)
                analysis["food_type"] = args.get("food_type")

            elif name == "identify_dish":
                analysis["dish_name"] = args.get("dish_name")
                analysis["cuisine"] = args.get("cuisine")
                analysis["cooking_method"] = args.get("cooking_method")

            elif name == "identify_ingredients":
                analysis["ingredients"] = args.get("ingredients", [])

            elif name == "extract_nutrition":
                analysis["nutrition"] = {
                    "calories": args.get("calories"),
                    "protein_g": args.get("protein_g"),
                    "carbs_g": args.get("carbs_g"),
                    "fat_g": args.get("fat_g"),
                }

            elif name == "extract_venue_info":
                if args.get("venue_name"):
                    analysis["venue"] = {
                        "name": args.get("venue_name"),
                        "type": args.get("venue_type"),
                        "location_hint": args.get("location_hint"),
                    }

        return analysis

    async def filter_food_images(
        self,
        image_urls: list[str],
        confidence_threshold: float = 0.7,
    ) -> dict[str, Any]:
        """
        Filter a batch of images to identify which contain food.

        Faster than full analysis - only checks if food is present.

        Args:
            image_urls: List of image URLs to filter
            confidence_threshold: Minimum confidence to consider food

        Returns:
            dict with food and non-food image lists
        """
        food_images = []
        non_food_images = []

        prompt = """Quickly determine if this image contains food.
Use detect_food_in_image to report your finding."""

        for url in image_urls:
            result = await self._gemini_client().generate_with_tools(
                prompt=prompt,
                tools=[MEDIA_PROCESSING_TOOLS[0]],  # detect_food_in_image only
                image_url=url,
            )

            # Check result
            is_food = False
            confidence = 0.0

            for call in result.get("function_calls", []):
                if call["name"] == "detect_food_in_image":
                    is_food = call["args"].get("is_food", False)
                    confidence = call["args"].get("confidence", 0.0)
                    break

            if is_food and confidence >= confidence_threshold:
                food_images.append({"url": url, "confidence": confidence})
            else:
                non_food_images.append({"url": url, "confidence": confidence})

        return {
            "food_images": food_images,
            "non_food_images": non_food_images,
            "food_count": len(food_images),
            "threshold_used": confidence_threshold,
        }

    async def filter_food_photos(
        self,
        image_urls: list[str],
        confidence_threshold: float = 0.7,
    ) -> dict[str, Any]:
        """Backward compatible alias for filter_food_images."""
        return await self.filter_food_images(
            image_urls=image_urls,
            confidence_threshold=confidence_threshold,
        )

    async def create_food_log_entries(
        self,
        image_urls: list[str],
        default_venue: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Process images and create food log entry drafts.

        Args:
            image_urls: List of food image URLs
            default_venue: Optional default venue for all entries

        Returns:
            list of food log entry drafts ready for saving
        """
        entries = []

        for url in image_urls:
            analysis = await self.process_single_photo(url)

            if analysis.get("is_food", False):
                entry = {
                    "dish_name": analysis.get("dish_name", "Unknown Dish"),
                    "image_url": url,
                    "cuisine": analysis.get("cuisine"),
                    "ingredients": [ing.get("name") for ing in analysis.get("ingredients", [])],
                    "nutrition": analysis.get("nutrition", {}),
                    "venue": analysis.get("venue", {}).get("name") or default_venue,
                    "analysis_confidence": analysis.get("confidence", 0.0),
                    "status": "draft",  # Needs user confirmation
                }
                entries.append(entry)

        return entries

    async def analyze_meal_sequence(
        self,
        image_urls: list[str],
    ) -> dict[str, Any]:
        """
        Analyze a sequence of photos as a complete meal.

        Useful when multiple photos capture different parts of a meal
        (appetizer, main, dessert, etc.).

        Args:
            image_urls: List of image URLs from the same meal

        Returns:
            dict with combined meal analysis
        """
        # Process each image
        courses = []
        for url in image_urls:
            analysis = await self.process_single_photo(url)
            if analysis.get("is_food", False):
                courses.append(analysis)

        if not courses:
            return {
                "is_meal": False,
                "message": "No food detected in images",
            }

        # Combine nutrition
        total_nutrition = {
            "calories": 0,
            "protein_g": 0,
            "carbs_g": 0,
            "fat_g": 0,
        }

        for course in courses:
            nutrition = course.get("nutrition", {})
            for key in total_nutrition:
                total_nutrition[key] += nutrition.get(key) or 0

        # Determine cuisines
        cuisines = list({c.get("cuisine") for c in courses if c.get("cuisine")})

        return {
            "is_meal": True,
            "course_count": len(courses),
            "courses": [
                {
                    "dish_name": c.get("dish_name"),
                    "image_url": c.get("image_url"),
                    "nutrition": c.get("nutrition"),
                }
                for c in courses
            ],
            "total_nutrition": total_nutrition,
            "cuisines": cuisines,
            "venue": courses[0].get("venue") if courses else None,
        }
