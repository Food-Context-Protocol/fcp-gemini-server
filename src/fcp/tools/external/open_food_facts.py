"""Open Food Facts API client.

Provides access to the world's largest open food database for
nutrition facts, ingredients, Eco-Score, NOVA groups, and additives.
API docs: https://openfoodfacts.github.io/openfoodfacts-server/api/

No API key required - Open Food Facts is fully open.
"""

from typing import Any

import httpx

from fcp.mcp.registry import tool

OFF_API_BASE = "https://world.openfoodfacts.org"
OFF_API_URL = f"{OFF_API_BASE}/api/v2/product"
OFF_SEARCH_URL = f"{OFF_API_BASE}/cgi/search.pl"
DEFAULT_TIMEOUT = 10.0

# Limit returned fields from OFF search to reduce payload size and parsing time
OFF_SEARCH_FIELDS = ",".join(
    [
        "product_name",
        "brands",
        "code",
        "nutriments",
        "nova_group",
        "ecoscore_grade",
        "ecoscore_score",
        "nutriscore_grade",
        "additives_tags",
        "image_url",
    ]
)


@tool(
    name="dev.fcp.external.lookup_product",
    description="Look up product information from Open Food Facts",
    category="external",
)
async def lookup_product(barcode: str) -> dict[str, Any] | None:
    """
    Look up product information from Open Food Facts.

    Args:
        barcode: The product barcode string

    Returns:
        Dict with product data or None if not found
    """
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(url, timeout=10.0)
            if response.status_code != 200:
                return {"error": "Product not found or API error"}

            data = response.json()
            if data.get("status") == 0:
                return {"error": "Product not found or API error"}

            product = data.get("product", {})

            # Extract high-value metadata for FoodLog
            return {
                "name": product.get("product_name"),
                "dish_name": product.get("product_name"),
                "brand": product.get("brands"),
                "ingredients_text": product.get("ingredients_text"),
                "nutrition": product.get("nutriments", {}),
                "nova_group": product.get("nova_group"),
                "ecoscore_grade": product.get("ecoscore_grade"),
                "image_url": product.get("image_url"),
                "source": "open_food_facts",
            }
        except Exception as e:
            return {"error": str(e)}


async def search_by_name(
    query: str,
    page_size: int = 5,
) -> list[dict[str, Any]]:
    """Search Open Food Facts by product name.

    Args:
        query: Search term (product name, brand, etc.)
        page_size: Maximum results to return (default 5)

    Returns:
        List of product dicts with name, brand, nutrition, scores, etc.
        Empty list on error.
    """
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=DEFAULT_TIMEOUT,
        ) as client:
            response = await client.get(
                OFF_SEARCH_URL,
                params={
                    "search_terms": query,
                    "search_simple": 1,
                    "action": "process",
                    "json": 1,
                    "page_size": page_size,
                    "fields": OFF_SEARCH_FIELDS,
                },
            )
            if response.status_code != 200:
                return []

            data = response.json()
            products = data.get("products", [])

            return [
                {
                    "product_name": p.get("product_name"),
                    "brand": p.get("brands"),
                    "code": p.get("code"),
                    "nutrition": p.get("nutriments", {}),
                    "nova_group": p.get("nova_group"),
                    "ecoscore_grade": p.get("ecoscore_grade"),
                    "ecoscore_score": p.get("ecoscore_score"),
                    "nutriscore_grade": p.get("nutriscore_grade"),
                    "additives_tags": p.get("additives_tags", []),
                    "image_url": p.get("image_url"),
                }
                for p in products
                if p.get("product_name")
            ]
    except Exception:
        return []


def get_ecoscore(product: dict[str, Any]) -> dict[str, Any]:
    """Extract Eco-Score data from an OFF product.

    The Eco-Score rates environmental impact from A (best) to E (worst).

    Args:
        product: Product dict from lookup_product or search_by_name

    Returns:
        Dict with grade, score, and details.
    """
    # Coalesce null/falsy values to "unknown" for consistent client handling
    raw_grade = product.get("ecoscore_grade")
    grade = raw_grade if isinstance(raw_grade, str) and raw_grade else "unknown"
    return {
        "grade": grade,
        "score": product.get("ecoscore_score"),
    }


def get_nova_group(product: dict[str, Any]) -> int | None:
    """Extract NOVA processing group from an OFF product.

    NOVA classifies foods by processing level:
    - 1: Unprocessed or minimally processed
    - 2: Processed culinary ingredients
    - 3: Processed foods
    - 4: Ultra-processed foods

    Args:
        product: Product dict from lookup_product or search_by_name

    Returns:
        NOVA group (1-4) or None if not available.
    """
    nova = product.get("nova_group")
    if nova is not None:
        try:
            return int(nova)
        except (ValueError, TypeError):
            pass
    return None


def get_nutriscore(product: dict[str, Any]) -> str | None:
    """Extract Nutri-Score from an OFF product.

    Nutri-Score rates nutritional quality from A (best) to E (worst).

    Args:
        product: Product dict from lookup_product or search_by_name

    Returns:
        Nutri-Score grade (a-e) or None if not available.
    """
    grade = product.get("nutriscore_grade")
    return grade.lower() if grade and isinstance(grade, str) else None


def get_additives(product: dict[str, Any]) -> list[dict[str, str]]:
    """Extract additives from an OFF product.

    Args:
        product: Product dict from lookup_product or search_by_name

    Returns:
        List of additive dicts with code.
    """
    additives_tags = product.get("additives_tags", [])
    additives = []

    for tag in additives_tags:
        # Tags are like "en:e300", "fr:e621", or "en:e621-monosodium-glutamate"
        # Handle any locale prefix (2-letter code followed by colon)
        if isinstance(tag, str):
            # Remove locale prefix (e.g., "en:", "fr:", "de:")
            code = tag[3:].upper() if len(tag) > 3 and tag[2] == ":" else tag.upper()
            # Extract just the E-number if present (before any dash)
            if "-" in code:
                code = code.split("-")[0]
            additives.append({"code": code})

    return additives
