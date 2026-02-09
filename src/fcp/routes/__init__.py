"""FCP Server Route Modules.

This package contains route handlers organized by domain:
- meals: CRUD operations for food logs
- search: Semantic search across food logs
- safety: Food safety, recalls, allergens, drug interactions
- profile: User taste profiles, lifetime analysis
- analyze: Food image analysis (basic, streaming, v2, thinking)
- analytics: Nutrition stats, patterns, trends
- agents: Autonomous agents, discovery, content generation
- inventory: Pantry management and recipe suggestions
- discovery: Location-based food discovery
- recipes: Recipe processing and extraction
- social: Social media content generation
- publishing: Content generation, drafts, and CMS publishing
- connectors: External service integrations (Calendar, Drive)
- external: External API integrations (Open Food Facts)
- scheduler: Background scheduler management
- research: Deep research reports (Interactions API)
- video: AI video generation (Veo 3.1)
- voice: Real-time voice processing (Live API)
- misc: Various specialized endpoints (enrich, suggest, visual, audio, etc.)

Usage:
    from fcp.routes import (meals_router, search_router, safety_router, profile_router,
                        analyze_router, analytics_router, agents_router, inventory_router,
                        discovery_router)
    app.include_router(meals_router, prefix="", tags=["meals"])
    app.include_router(search_router, prefix="", tags=["search"])
    app.include_router(safety_router, prefix="/safety", tags=["safety"])
    app.include_router(profile_router, prefix="", tags=["profile"])
    app.include_router(analyze_router, prefix="", tags=["analyze"])
    app.include_router(analytics_router, prefix="", tags=["analytics"])
    app.include_router(agents_router, prefix="", tags=["agents"])
    app.include_router(inventory_router, prefix="", tags=["inventory"])
    app.include_router(discovery_router, prefix="", tags=["discovery"])
    app.include_router(recipes_router, prefix="", tags=["recipes"])
    app.include_router(social_router, prefix="", tags=["social"])
    app.include_router(connectors_router, prefix="", tags=["connectors"])
    app.include_router(external_router, prefix="", tags=["external"])
    app.include_router(scheduler_router, prefix="", tags=["scheduler"])
    app.include_router(misc_router, prefix="", tags=["misc"])
"""

from fcp.routes.agents import router as agents_router
from fcp.routes.analytics import router as analytics_router
from fcp.routes.analyze import router as analyze_router
from fcp.routes.connectors import router as connectors_router
from fcp.routes.discovery import router as discovery_router
from fcp.routes.external import router as external_router
from fcp.routes.health import router as health_router
from fcp.routes.inventory import router as inventory_router
from fcp.routes.knowledge import router as knowledge_router
from fcp.routes.meals import router as meals_router
from fcp.routes.misc import router as misc_router
from fcp.routes.parser import router as parser_router
from fcp.routes.profile import router as profile_router
from fcp.routes.publishing import router as publishing_router
from fcp.routes.recipes import router as recipes_router
from fcp.routes.research import router as research_router
from fcp.routes.safety import router as safety_router
from fcp.routes.scheduler import router as scheduler_router
from fcp.routes.search import router as search_router
from fcp.routes.social import router as social_router
from fcp.routes.video import router as video_router
from fcp.routes.voice import router as voice_router

__all__ = [
    "agents_router",
    "analyze_router",
    "analytics_router",
    "connectors_router",
    "discovery_router",
    "external_router",
    "health_router",
    "inventory_router",
    "knowledge_router",
    "meals_router",
    "misc_router",
    "parser_router",
    "profile_router",
    "publishing_router",
    "recipes_router",
    "research_router",
    "safety_router",
    "scheduler_router",
    "search_router",
    "social_router",
    "video_router",
    "voice_router",
]
