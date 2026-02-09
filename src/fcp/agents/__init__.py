"""Autonomous agents for FoodLog FCP.

This module provides autonomous agents that leverage Gemini 3's
advanced features for proactive food assistance:

- FoodDiscoveryAgent: Finds new restaurants and recipes
- MediaProcessingAgent: Auto-processes food photos
- ContentGeneratorAgent: Creates shareable content
- FreshnessAgent: Generates daily insights

Agents combine multiple Gemini 3 features:
- Function calling for structured actions
- Google Search grounding for real-time data
- Extended thinking for complex reasoning
- Code execution for calculations
"""

from fcp.agents.content_generator import ContentGeneratorAgent
from fcp.agents.discovery import FoodDiscoveryAgent
from fcp.agents.freshness import FreshnessAgent
from fcp.agents.media_processor import MediaProcessingAgent

__all__ = [
    "FoodDiscoveryAgent",
    "MediaProcessingAgent",
    "ContentGeneratorAgent",
    "FreshnessAgent",
]
