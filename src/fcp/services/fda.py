"""openFDA API client for food recalls and drug interaction data."""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

FDA_API_KEY = os.environ.get("FDA_API_KEY", "")
FDA_BASE_URL = "https://api.fda.gov"
FDA_TIMEOUT = 10.0


def _build_params(params: dict[str, str]) -> dict[str, str]:
    """Add API key to params if configured."""
    if FDA_API_KEY:
        params["api_key"] = FDA_API_KEY
    return params


async def search_food_recalls(food_name: str, limit: int = 5) -> dict[str, Any]:
    """Search openFDA for food enforcement actions (recalls) related to a food item.

    Args:
        food_name: The food item to search for
        limit: Maximum number of results

    Returns:
        Dict with 'results' list and 'meta' info, or empty results on error
    """
    # Escape quotes in food_name to avoid breaking the query
    safe_name = food_name.replace('"', '\\"')
    # Use spaces for AND operator - httpx will URL-encode correctly
    search_query = f'reason_for_recall:"{safe_name}" AND status:"Ongoing"'
    params = _build_params(
        {
            "search": search_query,
            "limit": str(limit),
        }
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{FDA_BASE_URL}/food/enforcement.json",
                params=params,
                timeout=FDA_TIMEOUT,
            )
            if response.status_code == 404:
                return {"results": [], "meta": {"total": 0}}
            response.raise_for_status()
            data = response.json()
            return {
                "results": data.get("results", []),
                "meta": data.get("meta", {}).get("results", {"total": 0}),
            }
    except httpx.TimeoutException:
        logger.warning("FDA API timeout searching recalls for: %s", food_name)
        return {"results": [], "meta": {"total": 0}, "error": "timeout"}
    except httpx.HTTPStatusError as e:
        logger.warning("FDA API error %s searching recalls for: %s", e.response.status_code, food_name)
        return {"results": [], "meta": {"total": 0}, "error": str(e)}
    except Exception as e:
        logger.warning("FDA API unexpected error searching recalls: %s", e)
        return {"results": [], "meta": {"total": 0}, "error": str(e)}


async def search_drug_food_interactions(drug_name: str, limit: int = 3) -> dict[str, Any]:
    """Search openFDA drug labels for food interaction information.

    Args:
        drug_name: The drug/medication name to search for
        limit: Maximum number of label results

    Returns:
        Dict with 'interactions' list extracted from drug labels, or empty on error
    """
    search_query = f'openfda.generic_name:"{drug_name}"'
    params = _build_params(
        {
            "search": search_query,
            "limit": str(limit),
        }
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{FDA_BASE_URL}/drug/label.json",
                params=params,
                timeout=FDA_TIMEOUT,
            )
            if response.status_code == 404:
                return {"interactions": [], "drug_name": drug_name}
            response.raise_for_status()
            data = response.json()

            interactions = []
            for result in data.get("results", []):
                food_interactions = result.get("food_interaction", [])
                if food_interactions:
                    interactions.extend(food_interactions)

            return {
                "interactions": interactions,
                "drug_name": drug_name,
                "label_count": len(data.get("results", [])),
            }
    except httpx.TimeoutException:
        logger.warning("FDA API timeout searching drug interactions for: %s", drug_name)
        return {"interactions": [], "drug_name": drug_name, "error": "timeout"}
    except httpx.HTTPStatusError as e:
        logger.warning("FDA API error %s searching drug interactions for: %s", e.response.status_code, drug_name)
        return {"interactions": [], "drug_name": drug_name, "error": str(e)}
    except Exception as e:
        logger.warning("FDA API unexpected error searching drug interactions: %s", e)
        return {"interactions": [], "drug_name": drug_name, "error": str(e)}
