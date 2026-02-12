"""Knowledge graph enrichment combining OFF and USDA data.

Provides comprehensive food knowledge by combining data from:
- USDA FoodData Central (detailed micronutrients)
- Open Food Facts (sustainability scores, additives)
- AI-powered related food suggestions
"""

import asyncio
import re
from datetime import UTC, datetime
from typing import Any

from fcp.mcp.registry import tool
from fcp.services.firestore import get_firestore_client
from fcp.services.gemini import gemini
from fcp.tools.external import open_food_facts as off
from fcp.tools.external import usda


def _make_safe_doc_id(name: str) -> str:
    """Create a safe Firestore document ID from a food name.

    Firestore document IDs cannot contain '/', and we want deterministic,
    collision-resistant IDs. This sanitizes the name by replacing unsafe
    characters with underscores and limiting length.
    """
    # Lowercase and replace spaces/unsafe chars with underscores
    safe_id = re.sub(r"[^a-z0-9]", "_", name.lower())
    # Collapse multiple underscores
    safe_id = re.sub(r"_+", "_", safe_id).strip("_")
    # Limit length to 50 chars
    return safe_id[:50] if safe_id else "unknown"


async def enrich_with_knowledge_graph(
    user_id: str,
    log_id: str,
    include_sustainability: bool = True,
    include_micronutrients: bool = True,
) -> dict[str, Any]:
    """Enrich a food log with comprehensive knowledge graph data.

    Combines data from USDA FoodData Central and Open Food Facts
    to provide detailed nutrition and sustainability information.

    Args:
        user_id: User ID
        log_id: Food log ID to enrich
        include_sustainability: Include OFF Eco-Score, NOVA, etc.
        include_micronutrients: Include USDA detailed nutrients

    Returns:
        {
            "success": bool,
            "knowledge_graph": {
                "usda_data": {...},
                "off_data": {...},
                "related_foods": [...],
                "enriched_at": str
            }
        }
    """
    db = get_firestore_client()

    # Get the food log
    log = await db.get_log(user_id, log_id)
    if not log:
        return {"success": False, "error": "Log not found"}

    dish_name = log.get("dish_name", "")
    if not dish_name:
        return {"success": False, "error": "Log has no dish name"}

    # Build knowledge graph
    knowledge_graph: dict[str, Any] = {}

    # Get USDA data if requested
    if include_micronutrients:
        usda_data = await _get_usda_data(dish_name)
        if usda_data:
            knowledge_graph["usda_data"] = usda_data

    # Get OFF data if requested
    if include_sustainability:
        off_data = await _get_off_data(dish_name)
        if off_data:
            knowledge_graph["off_data"] = off_data

    # Get related foods using AI
    related_foods = await _get_related_foods(dish_name)
    if related_foods:
        knowledge_graph["related_foods"] = related_foods

    knowledge_graph["enriched_at"] = datetime.now(UTC).isoformat()

    # Update the food log with knowledge graph
    await db.update_log(user_id, log_id, {"knowledge_graph": knowledge_graph})

    # Cache the knowledge for future lookups
    await _cache_knowledge(user_id, dish_name, knowledge_graph)

    return {"success": True, "knowledge_graph": knowledge_graph}


async def _get_usda_data(dish_name: str) -> dict[str, Any] | None:
    """Get USDA nutrition data for a dish."""
    results = await usda.search_foods(dish_name, page_size=1)
    if not results:
        return None

    best_match = results[0]
    fdc_id = best_match.get("fdcId")
    if not fdc_id:
        return None

    details = await usda.get_food_details(fdc_id)
    if not details:
        return None

    return {
        "fdc_id": fdc_id,
        "description": best_match.get("description"),
        "data_type": best_match.get("dataType"),
        "micronutrients": usda.extract_micronutrients(details),
    }


async def _get_off_data(dish_name: str) -> dict[str, Any] | None:
    """Get Open Food Facts sustainability data for a dish."""
    results = await off.search_by_name(dish_name, page_size=1)
    if not results:
        return None

    product = results[0]
    return {
        "ecoscore": off.get_ecoscore(product),
        "nova_group": off.get_nova_group(product),
        "nutriscore": off.get_nutriscore(product),
        "additives": off.get_additives(product),
    }


async def _get_related_foods(dish_name: str) -> list[str]:
    """Get related foods using AI."""
    try:
        result = await gemini.generate_json(
            f"List 5 foods that are nutritionally similar to '{dish_name}'. "
            f'Return JSON: {{"related_foods": ["food1", "food2", "food3", "food4", "food5"]}}'
        )
        return result.get("related_foods", [])
    except Exception:
        return []


async def _cache_knowledge(
    user_id: str,
    food_name: str,
    knowledge_graph: dict[str, Any],
) -> None:
    """Cache knowledge graph data for future lookups."""
    db = get_firestore_client()
    cache_ref = db.db.collection("users").document(user_id).collection("knowledge_cache")
    doc_id = _make_safe_doc_id(food_name)
    cache_ref.document(doc_id).set(
        {
            "food_name": food_name,
            **knowledge_graph,
        }
    )


async def get_cached_knowledge(
    user_id: str,
    food_name: str,
) -> dict[str, Any] | None:
    """Get cached knowledge graph data if available.

    Args:
        user_id: User ID
        food_name: Name of food to look up

    Returns:
        Cached knowledge data or None if not cached.
    """
    db = get_firestore_client()
    cache_ref = db.db.collection("users").document(user_id).collection("knowledge_cache")
    doc_id = _make_safe_doc_id(food_name)
    doc = cache_ref.document(doc_id).get()
    return doc.to_dict() if doc.exists else None


async def search_knowledge(
    query: str,
) -> dict[str, Any]:
    """Search across USDA and OFF databases.

    Args:
        query: Search term

    Returns:
        {
            "usda": [...],
            "off": [...],
            "combined_count": int
        }
    """
    # Search both databases in parallel
    usda_results, off_results = await asyncio.gather(
        usda.search_foods(query, page_size=3),
        off.search_by_name(query, page_size=3),
    )

    return {
        "usda": [
            {
                "fdc_id": r.get("fdcId"),
                "description": r.get("description"),
                "data_type": r.get("dataType"),
            }
            for r in usda_results
        ],
        "off": [
            {
                "product_name": r.get("product_name"),
                "brand": r.get("brand"),
                "ecoscore": r.get("ecoscore_grade"),
                "nutriscore": r.get("nutriscore_grade"),
            }
            for r in off_results
        ],
        "combined_count": len(usda_results) + len(off_results),
    }


@tool(
    name="dev.fcp.knowledge.search",
    description="Search food knowledge across USDA and Open Food Facts",
    category="knowledge",
)
async def search_knowledge_tool(query: str) -> dict[str, Any]:
    """MCP wrapper for knowledge search."""
    return await search_knowledge(query)


async def compare_foods(
    food1: str,
    food2: str,
) -> dict[str, Any]:
    """Compare nutrition between two foods.

    Args:
        food1: First food name
        food2: Second food name

    Returns:
        {
            "success": bool,
            "food1": str,
            "food2": str,
            "comparison": {
                "nutrient_name": {
                    "food1": value,
                    "food2": value,
                    "difference": value
                }
            }
        }
    """
    # Check if USDA API is configured
    if not usda._get_api_key():
        return {
            "success": False,
            "error": "USDA API key not configured",
            "error_code": "SERVICE_UNAVAILABLE",
        }

    # Get USDA data for both foods in parallel
    data1, data2 = await asyncio.gather(
        usda.get_food_by_name(food1),
        usda.get_food_by_name(food2),
    )

    if not data1:
        return {"success": False, "error": f"'{food1}' not found in USDA database"}
    if not data2:
        return {"success": False, "error": f"'{food2}' not found in USDA database"}

    nutrients1 = usda.extract_micronutrients(data1)
    nutrients2 = usda.extract_micronutrients(data2)

    # Find common nutrients and compare
    # Use None for missing nutrients to distinguish from actual zero values
    all_nutrients = set(nutrients1.keys()) | set(nutrients2.keys())
    comparison: dict[str, dict[str, float | None]] = {}

    for nutrient in sorted(all_nutrients):
        val1 = nutrients1.get(nutrient)
        val2 = nutrients2.get(nutrient)
        # Only calculate difference if both values are present
        diff = round(val1 - val2, 2) if val1 is not None and val2 is not None else None
        comparison[nutrient] = {
            "food1": val1,
            "food2": val2,
            "difference": diff,
        }

    return {
        "success": True,
        "food1": food1,
        "food2": food2,
        "comparison": comparison,
    }
