"""Enrich food log entries with AI analysis and scientific data."""

import os
from typing import Any

import httpx

from fcp.prompts import PROMPTS
from fcp.services.firestore import firestore_client
from fcp.services.gemini import gemini
from fcp.services.storage import is_storage_configured, storage_client
from fcp.utils.errors import tool_error

USDA_API_KEY = os.environ.get("USDA_API_KEY", "DEMO_KEY")


async def get_usda_nutrition(dish_name: str) -> dict[str, Any]:
    """Fetch micronutrients from USDA FoodData Central."""
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?query={dish_name}&pageSize=1&api_key={USDA_API_KEY}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                if data.get("foods"):
                    food = data["foods"][0]
                    # Map standard nutrients to FoodLog schema
                    nutrients = {n["nutrientName"]: n["value"] for n in food.get("foodNutrients", [])}
                    return {
                        "magnesium": nutrients.get("Magnesium, Mg"),
                        "iron": nutrients.get("Iron, Fe"),
                        "vitamin_d": nutrients.get("Vitamin D (D2 + D3)"),
                        "calcium": nutrients.get("Calcium, Ca"),
                        "fdc_id": food.get("fdcId"),
                    }
    except Exception:
        pass
    return {}


async def enrich_entry(
    user_id: str,
    log_id: str,
) -> dict[str, Any]:
    """
    Enrich a food log entry with AI-generated metadata and scientific hydration.
    """
    # Fetch the log entry
    log = await firestore_client.get_log(user_id, log_id)
    if not log:
        return {"success": False, "error": "Log not found"}

    # Get image URL
    image_path = log.get("image_path")
    if not image_path:
        return {"success": False, "error": "No image to analyze"}

    if not is_storage_configured():
        return {
            "success": False,
            "error": "Storage not configured. Cannot retrieve stored images.",
        }

    image_url = storage_client.get_public_url(image_path)

    # Build enrichment prompt
    prompt = PROMPTS["enrich_entry"].format(
        notes=log.get("notes", ""),
        venue=log.get("venue_name", ""),
    )

    try:
        # 1. Primary AI Vision Analysis
        result = await gemini.generate_json(prompt, image_url=image_url)

        # 2. Secondary Scientific Hydration (USDA)
        dish_name = str(result.get("dish_name") or log.get("dish_name") or "")
        micronutrients = await get_usda_nutrition(dish_name)

        # Prepare update data
        update_data = {
            "processing_status": "enriched",
            "dish_name": dish_name,
            "ingredients": result.get("ingredients", []),
            "nutrition": {**result.get("nutrition", {}), "micronutrients": micronutrients},
            "dietary_tags": result.get("dietary_tags", []),
            "allergens": result.get("allergens", []),
            "cuisine": result.get("cuisine"),
        }

        # Add inferred context if present
        if inferred := result.get("inferred_context"):
            if inferred.get("occasion"):
                update_data["occasion"] = inferred["occasion"]
            if inferred.get("notes_summary"):
                update_data["ai_notes"] = inferred["notes_summary"]

        # 3. Semantic Mapping (FoodOn)
        if foodon := result.get("foodon"):
            update_data["foodon"] = foodon

        # Update the log
        await firestore_client.update_log(user_id, log_id, update_data)

        return {
            "success": True,
            "log_id": log_id,
            "enrichment": update_data,
        }

    except Exception as e:
        # Mark as failed
        await firestore_client.update_log(
            user_id,
            log_id,
            {
                "processing_status": "failed",
                "processing_error": "An error occurred during enrichment processing",
            },
        )
        return {**tool_error(e, "enriching food log entry"), "success": False}
