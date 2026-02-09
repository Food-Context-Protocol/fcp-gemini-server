"""Food safety tools with Google Search grounding and automated recall matching."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from fcp.mcp.registry import tool
from fcp.services.fda import search_drug_food_interactions as fda_drug_interactions
from fcp.services.fda import search_food_recalls as fda_food_recalls
from fcp.services.firestore import firestore_client
from fcp.services.gemini import gemini

logger = logging.getLogger(__name__)

# =============================================================================
# Phrase Constants for Detection Logic
# =============================================================================
# These phrase lists are used by detection functions to classify text responses.
# Organized as module-level constants for maintainability and easy updates.

# Recall Detection Phrases
NO_RECALL_PHRASES: tuple[str, ...] = (
    "no active recall",
    "no current recall",
    "no recalls found",
    "no recent recall",
    "there are no recall",
    "not currently under recall",
    "no ongoing recall",
    "no food recall",
    "couldn't find any recall",
    "could not find any recall",
    "no known recall",
)

ACTIVE_RECALL_PHRASES: tuple[str, ...] = (
    "has been recalled",
    "is being recalled",
    "recall issued",
    "recall announced",
    "voluntary recall",
    "mandatory recall",
    "recalled due to",
    "recall in effect",
    "active recall",
    "current recall",
    "ongoing recall",
)

# Interaction Detection Phrases
NO_INTERACTION_PHRASES: tuple[str, ...] = (
    "no known interaction",
    "no significant interaction",
    "no documented interaction",
    "no reported interaction",
    "no clinical interaction",
    "no major interaction",
    "generally safe",
    "no adverse interaction",
    "unlikely to interact",
    "no evidence of interaction",
    "safe to consume",
    "no contraindication",
)

INTERACTION_PHRASES: tuple[str, ...] = (
    "may interact",
    "can interact",
    "should avoid",
    "avoid consuming",
    "contraindicated",
    "interaction between",
    "interacts with",
    "interfere with",
    "affect the absorption",
    "affect the efficacy",
    "increase the effect",
    "decrease the effect",
    "potentiate",
    "inhibit",
    "enhance the effect",
    "reduce the effect",
    "use caution when",
    "exercise caution",
    "warning: do not",
    "warning: avoid",
    "consult your doctor",
    "talk to your healthcare",
)

# Negation Patterns
# Used to detect when interaction/alert phrases are negated (e.g., "does not inhibit")
NEGATION_PATTERNS: tuple[str, ...] = (
    "does not ",
    "do not ",
    "doesn't ",
    "don't ",
    "did not ",
    "didn't ",
    "will not ",
    "won't ",
    "would not ",
    "wouldn't ",
    "cannot ",
    "can't ",
    "no evidence ",
    "no proof ",
    "unlikely to ",
    "not expected to ",
    "not known to ",
    "not likely to ",
    "is not known to ",
    "are not known to ",
)

# Allergen Alert Detection Phrases
NO_ALERT_PHRASES: tuple[str, ...] = (
    "no allergen alert",
    "no undeclared allergen",
    "no allergen warning",
    "no cross-contamination",
    "no known allergen",
    "no recent alert",
    "properly labeled",
    "correctly labeled",
    "no mislabeling",
    "safe for those with",
    "no issues found",
)

ALERT_PHRASES: tuple[str, ...] = (
    "undeclared",
    "mislabeled",
    "cross-contamination",
    "allergen alert",
    "allergen warning",
    "may contain",
    "traces of",
    "recall",
    "withdrawn",
    "do not consume",
    "allergic reaction",
    "anaphylaxis",
    "not declared on label",
    "missing from label",
)


# =============================================================================
# Field Normalization Functions
# =============================================================================
# These functions normalize structured fields from AI responses to ensure
# consistent types in the API response, even if the model returns unexpected types.


def _normalize_alert_type(value: Any) -> str | None:
    """Ensure alert_type is a short string or None."""
    if isinstance(value, str):
        value = value.strip()
        return value[:64] if value else None
    return None


def _normalize_alert_severity(value: Any) -> str | None:
    """Ensure alert_severity is one of the allowed values or None."""
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    allowed = {"critical", "warning", "info"}
    return value if value in allowed else None


def _normalize_affected_list(value: Any) -> list[str]:
    """Ensure affected_products/affected_medications is always a list of strings."""
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list | tuple):
        items = list(value)
    else:
        return []

    normalized = []
    for item in items:
        if not isinstance(item, str):
            item = str(item)
        item = item.strip()
        if not item:
            continue
        normalized.append(item[:200])
        if len(normalized) >= 50:
            break
    return normalized


def _normalize_recommended_action(value: Any) -> str | None:
    """Ensure recommended_action is a single string or None."""
    if isinstance(value, str):
        text = value
    elif isinstance(value, list | tuple):
        text = " ".join(str(v) for v in value)
    else:
        return None

    text = text.strip()
    return text[:500] if text else None


def _detect_active_recall(recall_info: str) -> bool:
    """
    Detect if the recall info indicates an active recall.

    Returns True if there appears to be an active recall,
    False if the response indicates no recalls or clear status.
    """
    text = recall_info.lower()

    # Check for phrases that indicate NO active recall
    for phrase in NO_RECALL_PHRASES:
        if phrase in text:
            return False

    # Must have "recall" to indicate a potential active recall
    if "recall" not in text:
        return False

    return next((True for phrase in ACTIVE_RECALL_PHRASES if phrase in text), True)


def _is_phrase_negated(text: str, phrase: str, match_pos: int) -> bool:
    """
    Check if a phrase match is preceded by a negation pattern.

    Args:
        text: The full text being analyzed (lowercase)
        phrase: The phrase that was matched
        match_pos: The position where the phrase was found

    Returns:
        True if the phrase is preceded by a negation pattern, False otherwise
    """
    # Look at the text before the match (up to 40 chars for context)
    # This window allows for patterns like "no evidence it will [phrase]"
    lookback_start = max(0, match_pos - 40)
    preceding_text = text[lookback_start:match_pos]

    return any(negation in preceding_text for negation in NEGATION_PATTERNS)


def _detect_interaction(interaction_info: str) -> bool:
    """
    Detect if the interaction info indicates a drug-food interaction.

    Checks for no-interaction phrases first, then interaction phrases.
    This ordering ensures explicit negations like "no evidence of interaction"
    take precedence over phrases like "interaction between" that may appear
    in the same text.

    Also handles negated phrases like "does not inhibit" by checking for
    negation patterns immediately preceding interaction keywords.

    Returns True if there appears to be a potential interaction,
    False if the response indicates no known interactions.
    """
    text = interaction_info.lower()

    # Check for phrases that indicate NO interaction - checked FIRST
    # This ensures "no evidence of interaction between X and Y" returns False
    for phrase in NO_INTERACTION_PHRASES:
        if phrase in text:
            return False

    # Check for phrases that indicate a potential interaction
    # Skip matches that are preceded by negation patterns
    for phrase in INTERACTION_PHRASES:
        pos = text.find(phrase)
        # Check if phrase is found and not negated
        if pos != -1 and not _is_phrase_negated(text, phrase, pos):
            return True

    # Default: no interaction detected
    # Log for monitoring ambiguous responses that couldn't be classified
    logger.debug(
        "Interaction detection defaulted to False (no matching phrases): %s",
        (f"{interaction_info[:100]}..." if len(interaction_info) > 100 else interaction_info),
    )
    return False


def _detect_allergen_alert(allergen_info: str) -> bool:
    """
    Detect if the allergen info indicates an active allergen alert.

    Checks for no-alert phrases first, then alert phrases.
    This ordering ensures explicit negations like "no allergen alert"
    take precedence over phrases like "alert" that may appear
    in the same text.

    Returns True if there appears to be an allergen warning or alert,
    False if the response indicates no allergen issues.
    """
    text = allergen_info.lower()

    # Check for phrases that indicate NO allergen alert - checked FIRST
    for phrase in NO_ALERT_PHRASES:
        if phrase in text:
            return False

    # Check for phrases that indicate an allergen alert
    for phrase in ALERT_PHRASES:
        if phrase in text:
            return True

    # Default: no alert detected
    # Log for monitoring ambiguous responses that couldn't be classified
    logger.debug(
        "Allergen detection defaulted to False (no matching phrases): %s",
        (f"{allergen_info[:100]}..." if len(allergen_info) > 100 else allergen_info),
    )
    return False


@tool(
    name="dev.fcp.safety.check_food_recalls",
    description="Check for FDA food recalls related to a food item",
    category="safety",
)
async def check_food_recalls(food_name: str) -> dict[str, Any]:
    """
    Check for FDA food recalls related to a food item.
    Uses Google Search grounding to find current recall information.

    Returns:
        dict with:
        - food_item: The food checked
        - recall_info: Text description of recall status
        - has_active_recall: Boolean indicating if there's an active recall
        - alert_type: "recall" | "contamination" | null
        - alert_severity: "critical" | "warning" | "info" | null
        - affected_products: List of affected product names/brands
        - recommended_action: What user should do
        - sources: List of sources used
        - checked_at: ISO timestamp
    """
    # 1. Query openFDA for real recall data
    fda_results = await fda_food_recalls(food_name)
    fda_recall_list = fda_results.get("results", [])

    # 2. Build context-enhanced prompt
    fda_context = ""
    if fda_recall_list:
        fda_context = f"\n\nReal FDA recall data for context:\n{json.dumps(fda_recall_list[:3], indent=2)}\n"

    prompt = f"""Search for any current FDA food recalls, safety alerts, or contamination
warnings related to "{food_name}".
{fda_context}
Return a JSON object with these exact fields:
{{
    "recall_info": "Detailed description of recall status and any active recalls from the past 30 days, including contamination type, affected products, what consumers should do, and recall date. If no recalls, explain clearly.",
    "has_active_recall": true or false (boolean indicating if there is currently an active recall),
    "alert_type": "recall" or "contamination" or null (type of alert if active),
    "alert_severity": "critical" or "warning" or "info" or null (severity: critical for health hazards, warning for potential risk, info for advisories),
    "affected_products": ["list", "of", "affected", "product", "names"] or [] (specific brands/products affected),
    "recommended_action": "What consumers should do" or null (e.g., "Discard product", "Return for refund", "Check lot numbers")
}}

Be accurate with the boolean: set has_active_recall to true ONLY if there is a confirmed active recall in the past 30 days."""

    result = await gemini.generate_json_with_grounding(prompt)
    data = result["data"]

    # Handle case where Gemini returns a list instead of dict
    if isinstance(data, list):
        data = data[0] if data else {}

    # Log if boolean field is missing (helps distinguish "no" from malformed response)
    if "has_active_recall" not in data:
        logger.warning(
            "Gemini response missing 'has_active_recall' field for food: %s, defaulting to False",
            food_name,
        )

    return {
        "food_item": food_name,
        "recall_info": data.get("recall_info", ""),
        "has_active_recall": bool(data.get("has_active_recall", False)),
        "alert_type": _normalize_alert_type(data.get("alert_type")),
        "alert_severity": _normalize_alert_severity(data.get("alert_severity")),
        "affected_products": _normalize_affected_list(data.get("affected_products", [])),
        "recommended_action": _normalize_recommended_action(data.get("recommended_action")),
        "sources": result["sources"],
        "fda_data": fda_recall_list[:5],
        "checked_at": datetime.now(UTC).isoformat(),
    }


async def run_recall_radar(user_id: str) -> list[dict[str, Any]]:
    """
    Background job to scan user's recent meals against active recalls.
    """
    recent_logs = await firestore_client.get_user_logs(user_id, days=7)
    alert_triggered = []

    for log in recent_logs:
        dish_name = log.get("dish_name")
        if not dish_name:
            continue

        recall_data = await check_food_recalls(dish_name)
        # Use the structured has_active_recall field
        if recall_data.get("has_active_recall", False):
            alert_triggered.append(
                {
                    "log_id": log["id"],
                    "dish_name": dish_name,
                    "alert": recall_data["recall_info"],
                    "has_active_recall": True,
                }
            )

    return alert_triggered


@tool(
    name="dev.fcp.safety.check_allergen_alerts",
    description="Check for allergen-related safety alerts for a food item",
    category="safety",
)
async def check_allergen_alerts(food_name: str, allergens: list[str] | None = None) -> dict[str, Any]:
    """Check for allergen-related safety alerts for a food item.

    Args:
        food_name: Name of the food to check
        allergens: Optional list of specific allergens to check for

    Returns:
        dict with:
        - food_item: The food checked
        - allergens_checked: List of allergens checked
        - allergen_alerts: Text description of allergen status
        - has_alert: Boolean indicating if there's an active allergen alert
        - alert_type: "allergen" | null
        - alert_severity: "critical" | "warning" | "info" | null
        - affected_products: List of affected product names/brands
        - recommended_action: What user should do
        - sources: List of sources used
        - checked_at: ISO timestamp
    """
    if allergens:
        allergens_str = ", ".join(allergens)
        allergen_context = f" related to these allergens: {allergens_str}"
    else:
        allergen_context = ""

    prompt = f"""Search for any undeclared allergen warnings or cross-contamination risks for "{food_name}"{allergen_context}.
Focus on FDA alerts, recalls, and mislabeling issues in the past 90 days.

Return a JSON object with these exact fields:
{{
    "allergen_alerts": "Detailed description of any allergen alerts, undeclared allergens, cross-contamination risks, or mislabeling issues. If none found, explain clearly.",
    "has_alert": true or false (boolean indicating if there is an active allergen alert or warning),
    "alert_type": "allergen" or null (always "allergen" if has_alert is true),
    "alert_severity": "critical" or "warning" or "info" or null (critical for anaphylaxis risk, warning for undeclared allergens, info for may-contain labels),
    "affected_products": ["list", "of", "affected", "product", "names"] or [] (specific brands/products with allergen issues),
    "recommended_action": "What consumers should do" or null (e.g., "Avoid if allergic to X", "Check ingredient labels", "Return product")
}}

Be accurate with the boolean: set has_alert to true ONLY if there is a confirmed allergen alert or undeclared allergen issue."""

    result = await gemini.generate_json_with_grounding(prompt)
    data = result["data"]

    # Handle case where Gemini returns a list instead of dict
    if isinstance(data, list):
        data = data[0] if data else {}

    # Log if boolean field is missing (helps distinguish "no" from malformed response)
    if "has_alert" not in data:
        logger.warning(
            "Gemini response missing 'has_alert' field for food: %s, defaulting to False",
            food_name,
        )

    return {
        "food_item": food_name,
        "allergens_checked": allergens,
        "allergen_alerts": data.get("allergen_alerts", ""),
        "has_alert": bool(data.get("has_alert", False)),
        "alert_type": _normalize_alert_type(data.get("alert_type")),
        "alert_severity": _normalize_alert_severity(data.get("alert_severity")),
        "affected_products": _normalize_affected_list(data.get("affected_products", [])),
        "recommended_action": _normalize_recommended_action(data.get("recommended_action")),
        "sources": result["sources"],
        "checked_at": datetime.now(UTC).isoformat(),
    }


@tool(
    name="dev.fcp.safety.get_restaurant_safety_info",
    description="Get safety and health inspection information for a restaurant",
    category="safety",
)
async def get_restaurant_safety_info(restaurant_name: str, location: str | None = None) -> dict[str, Any]:
    """Get safety and health inspection information for a restaurant."""
    location_str = f" in {location}" if location else ""
    prompt = (
        f"""Search for health inspection scores and food safety reputation for "{restaurant_name}"{location_str}."""
    )

    result = await gemini.generate_with_grounding(prompt)

    return {
        "restaurant": restaurant_name,
        "location": location,
        "safety_info": result["text"],
        "sources": result["sources"],
        "checked_at": datetime.now(UTC).isoformat(),
    }


@tool(
    name="dev.fcp.safety.check_drug_food_interactions",
    description="Check for interactions between a food and list of medications",
    category="safety",
)
async def check_drug_food_interactions(food_name: str, medications: list[str]) -> dict[str, Any]:
    """Check for interactions between a food and list of medications.

    Returns:
        dict with:
        - food: The food checked
        - medications: List of medications checked
        - interaction_info: Text description of interactions
        - has_interaction: Boolean indicating if there's a potential interaction
        - alert_severity: "critical" | "warning" | "info" | null
        - affected_medications: List of medications with interactions
        - recommended_action: What user should do
        - sources: List of sources used
        - checked_at: ISO timestamp
    """
    # 1. Query openFDA for real drug-food interaction data (in parallel)
    import asyncio

    fda_results = await asyncio.gather(*[fda_drug_interactions(med) for med in medications])
    fda_interactions_data: list[dict[str, Any]] = [result for result in fda_results if result.get("interactions")]

    # 2. Build context-enhanced prompt
    fda_context = ""
    if fda_interactions_data:
        fda_context = (
            f"\n\nReal FDA drug label interaction data for context:\n{json.dumps(fda_interactions_data, indent=2)}\n"
        )

    meds_str = ", ".join(medications)
    prompt = f"""Search for food-drug interactions between "{food_name}" and these medications: {meds_str}.
{fda_context}
Return a JSON object with these exact fields:
{{
    "interaction_info": "Detailed description of any known interactions between this food and the listed medications, including clinical significance and recommendations. If no interactions, explain clearly.",
    "has_interaction": true or false (boolean indicating if there is a clinically significant interaction),
    "alert_severity": "critical" or "warning" or "info" or null (critical for dangerous interactions, warning for moderate, info for minor),
    "affected_medications": ["list", "of", "affected", "medication", "names"] or [] (which medications from the list have interactions),
    "recommended_action": "What patient should do" or null (e.g., "Avoid grapefruit while taking X", "Take medication 2 hours apart from food", "Consult your doctor")
}}

Be accurate with the boolean: set has_interaction to true ONLY if there is a documented clinically significant interaction."""

    result = await gemini.generate_json_with_grounding(prompt)
    data = result["data"]

    # Handle case where Gemini returns a list instead of dict
    if isinstance(data, list):
        data = data[0] if data else {}

    # Log if boolean field is missing (helps distinguish "no" from malformed response)
    if "has_interaction" not in data:
        logger.warning(
            "Gemini response missing 'has_interaction' field for food: %s, defaulting to False",
            food_name,
        )

    return {
        "food": food_name,
        "medications": medications,
        "interaction_info": data.get("interaction_info", ""),
        "has_interaction": bool(data.get("has_interaction", False)),
        "alert_severity": _normalize_alert_severity(data.get("alert_severity")),
        "affected_medications": _normalize_affected_list(data.get("affected_medications", [])),
        "recommended_action": _normalize_recommended_action(data.get("recommended_action")),
        "sources": result["sources"],
        "fda_data": fda_interactions_data,
        "checked_at": datetime.now(UTC).isoformat(),
    }


async def get_seasonal_food_safety(location: str) -> dict[str, Any]:
    """Get seasonal food safety advisories and tips for a location."""
    prompt = f"Search for current seasonal food safety outbreaks, tips, and produce alerts for {location}."
    result = await gemini.generate_with_grounding(prompt)
    return {
        "location": location,
        "safety_tips": result["text"],
        "sources": result["sources"],
        "checked_at": datetime.now(UTC).isoformat(),
    }


async def verify_nutrition_claim(claim: str, food_name: str) -> dict[str, Any]:
    """Verify a nutrition or health claim about a food."""
    prompt = (
        f"""Fact-check this claim: "{claim}" about "{food_name}". Search scientific sources and FDA/USDA guidance."""
    )

    result = await gemini.generate_with_grounding(prompt)

    return {
        "food": food_name,
        "claim": claim,
        "verification": result["text"],
        "sources": result["sources"],
        "checked_at": datetime.now(UTC).isoformat(),
    }
