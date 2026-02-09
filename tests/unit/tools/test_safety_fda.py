"""Tests for FDA data branches in safety tools.

Covers lines where FDA API returns non-empty results, ensuring the
fda_context is built and passed into the Gemini prompt.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools import safety


@pytest.mark.asyncio
async def test_check_food_recalls_with_fda_results():
    """Cover line 346: fda_recall_list is truthy (FDA returned results)."""
    with (
        patch(
            "fcp.tools.safety.fda_food_recalls",
            new=AsyncMock(return_value={"results": [{"reason_for_recall": "contamination"}]}),
        ),
        patch(
            "fcp.tools.safety.gemini.generate_json_with_grounding",
            new=AsyncMock(
                return_value={
                    "data": {
                        "recall_info": "Contamination found.",
                        "has_active_recall": True,
                        "alert_type": "contamination",
                        "alert_severity": "critical",
                        "affected_products": ["Brand X"],
                        "recommended_action": "Discard product.",
                    },
                    "sources": [{"title": "FDA", "url": "https://fda.gov"}],
                }
            ),
        ),
    ):
        result = await safety.check_food_recalls("romaine lettuce")
        assert result["has_active_recall"] is True
        assert result["alert_type"] == "contamination"

        # Verify the FDA data was included in the prompt
        call_args = safety.gemini.generate_json_with_grounding.call_args[0][0]
        assert "contamination" in call_args
        assert "Real FDA recall data for context" in call_args


@pytest.mark.asyncio
async def test_check_drug_food_interactions_with_fda_results():
    """Cover lines 525 and 530: fda_result has interactions, fda_interactions_data is truthy."""
    with (
        patch(
            "fcp.tools.safety.fda_drug_interactions",
            new=AsyncMock(return_value={"interactions": ["Avoid grapefruit"], "drug_name": "atorvastatin"}),
        ),
        patch(
            "fcp.tools.safety.gemini.generate_json_with_grounding",
            new=AsyncMock(
                return_value={
                    "data": {
                        "interaction_info": "Grapefruit interacts with statins.",
                        "has_interaction": True,
                        "alert_severity": "critical",
                        "affected_medications": ["atorvastatin"],
                        "recommended_action": "Avoid grapefruit.",
                    },
                    "sources": [{"title": "NIH", "url": "https://nih.gov"}],
                }
            ),
        ),
    ):
        result = await safety.check_drug_food_interactions("grapefruit", ["atorvastatin"])
        assert result["has_interaction"] is True
        assert result["alert_severity"] == "critical"

        # Verify the FDA interaction data was included in the prompt
        call_args = safety.gemini.generate_json_with_grounding.call_args[0][0]
        assert "Real FDA drug label interaction data for context" in call_args
        assert "Avoid grapefruit" in call_args
