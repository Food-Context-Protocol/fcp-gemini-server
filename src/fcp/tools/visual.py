"""Visual Kitchen tools for generating image prompts and food images."""

import base64
import logging
from typing import Any

from fcp.mcp.registry import tool
from fcp.services.gemini import gemini
from fcp.services.image_generation import AspectRatio, ImageGenerationService, Resolution

logger = logging.getLogger(__name__)

# Singleton instance of image generation service
_image_service: ImageGenerationService | None = None


def _get_image_service() -> ImageGenerationService:
    """Get or create the image generation service singleton."""
    global _image_service
    if _image_service is None:
        _image_service = ImageGenerationService()
    return _image_service


async def generate_food_image(
    dish_name: str,
    cuisine: str | None = None,
    style: str = "professional food photography",
    aspect_ratio: str = "4:3",
    resolution: str = "2K",
) -> dict[str, Any]:
    """
    Generate a photorealistic food image using Gemini 3 Pro Image.

    Args:
        dish_name: Name of the dish (e.g., "Tonkotsu Ramen")
        cuisine: Cuisine type for styling hints (e.g., "Japanese")
        style: Photography style description
        aspect_ratio: Output aspect ratio ("1:1", "4:3", "16:9", etc.)
        resolution: Output resolution ("1K", "2K", "4K")

    Returns:
        dict with:
        - image_base64: Base64-encoded image data
        - mime_type: Image MIME type (e.g., "image/png")
        - aspect_ratio: The aspect ratio used
        - resolution: The resolution used
        - dish_name: The dish that was generated
    """
    service = _get_image_service()

    # Map string to enum
    ar_map = {
        "1:1": AspectRatio.SQUARE,
        "2:3": AspectRatio.PORTRAIT,
        "4:5": AspectRatio.INSTAGRAM,
        "3:2": AspectRatio.LANDSCAPE,
        "4:3": AspectRatio.STANDARD,
        "16:9": AspectRatio.WIDE,
        "21:9": AspectRatio.ULTRA_WIDE,
        "9:16": AspectRatio.STORY,
    }
    res_map = {
        "1K": Resolution.STANDARD,
        "2K": Resolution.HIGH,
        "4K": Resolution.ULTRA,
    }

    ar_enum = ar_map.get(aspect_ratio, AspectRatio.STANDARD)
    res_enum = res_map.get(resolution, Resolution.HIGH)

    result = await service.generate_food_image(
        dish_name=dish_name,
        cuisine=cuisine,
        style=style,
        aspect_ratio=ar_enum,
        resolution=res_enum,
    )

    return {
        "image_base64": base64.b64encode(result.image_bytes).decode("utf-8"),
        "mime_type": result.mime_type,
        "aspect_ratio": result.aspect_ratio.value,
        "resolution": result.resolution.value,
        "dish_name": dish_name,
    }


@tool(
    name="dev.fcp.visual.generate_image_prompt",
    description="Generate a detailed image generation prompt for food concepts",
    category="visual",
)
async def generate_image_prompt_tool(
    subject: str,
    style: str = "photorealistic",
    context: str = "menu",
) -> dict[str, Any]:
    """MCP tool wrapper for generate_image_prompt."""
    prompt = await generate_image_prompt(subject, style, context)
    return {"prompt": prompt}


async def generate_image_prompt(
    subject: str,
    style: str = "photorealistic",
    context: str = "menu",
) -> str:
    """
    Generate a detailed image generation prompt for food concepts.

    Args:
        subject: The food item, dish, or concept (e.g., "Spicy Ramen").
        style: Desired art style (e.g., "photorealistic", "illustration", "chalkboard").
        context: Usage context (e.g., "menu", "social_media", "logo").

    Returns:
        A highly detailed prompt string optimized for image generation models.
    """

    system_instruction = """
    You are an expert art director for food photography and design.
    Your goal is to write the PERFECT image generation prompt for an AI image model (like Imagen 3 or Midjourney).

    1. Analyze the subject and style.
    2. Add sensory details (lighting, texture, steam, plating).
    3. Specify technical camera settings if photorealistic (macro, depth of field).
    4. Specify artistic medium if illustrative (watercolor, vector).
    5. Return ONLY the prompt text.
    """

    user_prompt = f"Subject: {subject}\nStyle: {style}\nContext: {context}\n\nWrite the prompt:"
    prompt = f"{system_instruction}\n\n{user_prompt}"

    try:
        # We use generate_content for raw text
        response = await gemini.generate_content(prompt)
        return response.strip()
    except Exception:
        logger.exception("Error generating image prompt")
        return f"A delicious {subject}, {style} style."
