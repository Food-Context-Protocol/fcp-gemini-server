"""Semantic search across food logs.

Security:
- Input sanitization to prevent prompt injection
- Query length limits
"""

import json
from typing import Any

from fcp.mcp.registry import tool
from fcp.prompts import PROMPTS
from fcp.security import sanitize_search_query
from fcp.security.input_sanitizer import escape_for_prompt
from fcp.services.firestore import firestore_client
from fcp.services.gemini import gemini


@tool(
    name="dev.fcp.nutrition.search_meals",
    description="Semantic search across food journal",
    category="nutrition",
)
async def search_meals_tool(
    user_id: str,
    query: str,
    limit: int = 10,
) -> dict[str, Any]:
    """MCP tool wrapper for search_meals."""
    results = await search_meals(user_id, query, limit)
    return {"results": results}


async def search_meals(
    user_id: str,
    query: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Semantic search using Gemini to find matching food logs.

    Args:
        user_id: The user's ID
        query: Natural language search query (e.g., "that spicy ramen")
        limit: Maximum results to return

    Returns:
        List of matching food logs with relevance scores
    """
    # Sanitize query to prevent prompt injection
    safe_query = sanitize_search_query(query)

    if not safe_query:
        return []

    # Fetch user's logs
    logs = await firestore_client.get_user_logs(user_id, limit=100)

    if not logs:
        return []

    # Prepare logs for the prompt (simplified for context length)
    logs_summary = json.dumps(
        [
            {
                "id": log["id"],
                "dish_name": log.get("dish_name", ""),
                "venue": log.get("venue_name", ""),
                "cuisine": log.get("cuisine", ""),
                "notes": log.get("notes", ""),
                "date": log.get("created_at", ""),
                "ingredients": log.get("ingredients", [])[:5],
            }
            for log in logs
        ],
        indent=2,
    )

    # Build prompt with escaped query
    escaped_query = escape_for_prompt(safe_query)
    prompt = PROMPTS["search_meals"].format(logs=logs_summary, query=escaped_query)

    try:
        result = await gemini.generate_json(prompt)
        matches = result.get("matches", [])

        # Enrich matches with full log data
        log_by_id = {log["id"]: log for log in logs}
        enriched = []

        for match in matches[:limit]:
            log_id = match.get("id")
            if log_id and log_id in log_by_id:
                log = log_by_id[log_id]
                enriched.append(
                    {
                        **log,
                        "relevance_score": match.get("relevance", 0.5),
                        "match_reason": match.get("reason", ""),
                    }
                )

        return enriched

    except Exception:
        # Fallback to simple keyword search
        return _keyword_search(logs, safe_query, limit)


def _keyword_search(
    logs: list[dict],
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Simple keyword fallback when Gemini fails."""
    query_lower = query.lower()
    query_words = query_lower.split()

    results = []
    for log in logs:
        searchable = " ".join(
            [
                str(log.get("dish_name", "")),
                str(log.get("venue_name", "")),
                str(log.get("cuisine", "")),
                str(log.get("notes", "")),
                " ".join(log.get("ingredients", [])),
            ]
        ).lower()

        if any(word in searchable for word in query_words):
            results.append(
                {
                    **log,
                    "relevance_score": 0.5,
                    "match_reason": "keyword match",
                }
            )

        if len(results) >= limit:
            break

    return results
