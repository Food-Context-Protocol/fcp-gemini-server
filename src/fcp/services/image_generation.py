"""Image generation service using Nano Banana Pro (Gemini 3 Pro Image).

This service provides food photography generation capabilities using
Google's most advanced image generation model.
"""

from enum import StrEnum

from google import genai
from google.genai import types
from pydantic import BaseModel


class AspectRatio(StrEnum):
    """Supported aspect ratios for image generation."""

    SQUARE = "1:1"
    PORTRAIT = "2:3"
    INSTAGRAM = "4:5"  # Instagram-friendly portrait ratio
    LANDSCAPE = "3:2"
    STANDARD = "4:3"
    WIDE = "16:9"
    ULTRA_WIDE = "21:9"
    STORY = "9:16"


class Resolution(StrEnum):
    """Supported resolutions for image generation."""

    STANDARD = "1K"
    HIGH = "2K"
    ULTRA = "4K"


class GeneratedImage(BaseModel):
    """Result of image generation."""

    image_bytes: bytes
    mime_type: str
    aspect_ratio: AspectRatio
    resolution: Resolution
    thought_signature: str | None = None


class ImageGenerationService:
    """Service for generating food images using Nano Banana Pro.

    Uses the gemini-3-pro-image-preview model for:
    - Photorealistic food photography
    - Recipe cards with text overlay
    - Meal variations and alternatives
    """

    MODEL = "gemini-3-pro-image-preview"

    def __init__(self):
        """Initialize the image generation service."""
        self.client = genai.Client()

    async def generate_food_image(
        self,
        dish_name: str,
        cuisine: str | None = None,
        style: str = "professional food photography",
        aspect_ratio: AspectRatio = AspectRatio.STANDARD,
        resolution: Resolution = Resolution.HIGH,
    ) -> GeneratedImage:
        """Generate a photorealistic food image.

        Args:
            dish_name: Name of the dish (e.g., "Tonkotsu Ramen")
            cuisine: Cuisine type for styling hints
            style: Photography style description
            aspect_ratio: Output aspect ratio
            resolution: Output resolution (affects cost)

        Returns:
            GeneratedImage with bytes and metadata

        Raises:
            ValueError: If no image is generated in the response
        """
        prompt = self._build_food_prompt(dish_name, cuisine, style)

        # Handle both enum and string values for aspect_ratio
        ar_value = aspect_ratio.value if hasattr(aspect_ratio, "value") else str(aspect_ratio)

        response = await self.client.aio.models.generate_content(
            model=self.MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=ar_value,
                ),
            ),
        )

        # Extract image from response
        for part in response.candidates[0].content.parts:  # type: ignore[index]
            if part.inline_data:
                # thought_signature may be bytes, convert to base64 string if so
                thought_sig = getattr(part, "thought_signature", None)
                if isinstance(thought_sig, bytes):
                    import base64

                    thought_sig = base64.b64encode(thought_sig).decode("utf-8")
                return GeneratedImage(
                    image_bytes=part.inline_data.data,
                    mime_type=part.inline_data.mime_type,
                    aspect_ratio=aspect_ratio,
                    resolution=resolution,
                    thought_signature=thought_sig,
                )

        raise ValueError("No image generated in response")

    async def generate_recipe_card(
        self,
        recipe_name: str,
        ingredients: list[str],
        prep_time: str,
        cook_time: str,
        servings: int,
    ) -> GeneratedImage:
        """Generate a beautiful recipe card with text overlay.

        Args:
            recipe_name: Name of the recipe
            ingredients: List of ingredients
            prep_time: Preparation time string
            cook_time: Cooking time string
            servings: Number of servings

        Returns:
            GeneratedImage with the recipe card
        """
        prompt = f"""Create a professional recipe card image:

Recipe: {recipe_name}
Prep Time: {prep_time} | Cook Time: {cook_time} | Servings: {servings}

Ingredients:
{chr(10).join(f"- {ing}" for ing in ingredients[:8])}

Style: Modern minimalist recipe card with:
- Beautiful food photo as background (slightly blurred)
- Clean white text overlay with recipe details
- Elegant typography
- Warm, inviting colors
"""

        response = await self.client.aio.models.generate_content(
            model=self.MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_generation_config=types.ImageGenerationConfig(  # type: ignore[call-arg]
                    aspect_ratio="4:5",  # Instagram-friendly
                    resolution="2K",
                ),
            ),
        )

        for part in response.candidates[0].content.parts:  # type: ignore[index]
            if part.inline_data:
                return GeneratedImage(
                    image_bytes=part.inline_data.data,
                    mime_type=part.inline_data.mime_type,
                    aspect_ratio=AspectRatio.INSTAGRAM,  # Matches 4:5 request config
                    resolution=Resolution.HIGH,
                )

        raise ValueError("No recipe card generated")

    async def generate_meal_variation(
        self,
        original_image_url: str,
        variation: str,
    ) -> GeneratedImage:
        """Generate a variation of an existing meal photo.

        Args:
            original_image_url: URL of the original food image
            variation: Description of the variation (e.g., "Make this vegetarian")

        Returns:
            GeneratedImage with the variation
        """
        response = await self.client.aio.models.generate_content(
            model=self.MODEL,
            contents=[
                types.Part.from_uri(file_uri=original_image_url, mime_type="image/jpeg"),
                types.Part(
                    text=f"Generate a variation of this dish: {variation}. Maintain the same photography style and lighting."
                ),
            ],
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_generation_config=types.ImageGenerationConfig(  # type: ignore[call-arg]
                    aspect_ratio="4:3",
                    resolution="2K",
                ),
            ),
        )

        for part in response.candidates[0].content.parts:  # type: ignore[index]
            if part.inline_data:
                return GeneratedImage(
                    image_bytes=part.inline_data.data,
                    mime_type=part.inline_data.mime_type,
                    aspect_ratio=AspectRatio.STANDARD,
                    resolution=Resolution.HIGH,
                )

        raise ValueError("No variation generated")

    def _build_food_prompt(
        self,
        dish_name: str,
        cuisine: str | None,
        style: str,
    ) -> str:
        """Build an optimized prompt for food photography.

        Args:
            dish_name: Name of the dish
            cuisine: Optional cuisine type
            style: Photography style

        Returns:
            Optimized prompt string
        """
        cuisine_hint = f"authentic {cuisine} " if cuisine else ""

        return f"""Generate a stunning {style} image of {cuisine_hint}{dish_name}.

Photography specifications:
- Professional studio lighting with soft shadows
- Shallow depth of field focusing on the dish
- Steam/heat visible if applicable
- Garnishes and textures clearly visible
- Rich, appetizing colors
- Clean, minimal background
- Shot from 45-degree angle for optimal food presentation

Make the viewer hungry. Capture the essence and soul of this dish."""
