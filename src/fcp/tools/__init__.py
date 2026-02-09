"""FCP Tools - Core functionality exposed via MCP and HTTP."""

from .agents import delegate_to_food_agent, delegate_to_food_agent_tool
from .analyze import (
    analyze_meal,
    analyze_meal_from_bytes,
    analyze_meal_with_agentic_vision,
    analyze_meal_with_thinking,
)
from .astro import AstroBridge, get_astro_bridge
from .audio import analyze_voice_transcript, extract_voice_correction, log_meal_from_audio
from .blog import generate_blog_post, generate_blog_post_tool
from .civic import detect_economic_gaps, plan_food_festival
from .clinical import generate_dietitian_report
from .connector import save_to_drive, sync_to_calendar
from .cottage import generate_cottage_label
from .crud import (
    add_meal,
    delete_meal,
    donate_meal,
    get_meal,
    get_meals,
    get_meals_by_ids,
    get_recent_meals_tool,
    update_meal,
)
from .discovery import find_nearby_food, find_nearby_food_tool
from .enrich import enrich_entry
from .flavor import get_flavor_pairings
from .inventory import (
    add_to_pantry,
    check_pantry_expiry,
    delete_pantry_item,
    suggest_recipe_from_pantry,
    update_pantry_item,
)
from .knowledge_graph import (
    compare_foods,
    enrich_with_knowledge_graph,
    get_cached_knowledge,
    search_knowledge,
)
from .parser import parse_menu, parse_receipt
from .profile import get_taste_profile, get_taste_profile_tool
from .recipe_crud import (
    archive_recipe,
    delete_recipe,
    favorite_recipe,
    get_recipe,
    list_recipes,
    list_recipes_tool,
    save_recipe,
    update_recipe,
)
from .recipe_extractor import extract_recipe_from_media
from .recipe_generator import generate_recipe
from .research import generate_research_report
from .safety import (
    check_allergen_alerts,
    check_drug_food_interactions,
    check_food_recalls,
    get_restaurant_safety_info,
    get_seasonal_food_safety,
    run_recall_radar,
    verify_nutrition_claim,
)
from .scaling import scale_recipe
from .search import search_meals, search_meals_tool
from .social import generate_social_post, generate_social_post_tool
from .standardize import standardize_recipe
from .suggest import get_meal_suggestions_tool, suggest_meal
from .taste_buddy import check_dietary_compatibility
from .trends import identify_emerging_trends
from .video import generate_cooking_clip, generate_recipe_video
from .visual import generate_food_image, generate_image_prompt, generate_image_prompt_tool
from .voice import process_voice_meal_log, voice_food_query

__all__ = [
    "AstroBridge",
    "analyze_meal",
    "analyze_meal_from_bytes",
    "analyze_meal_with_agentic_vision",
    "analyze_meal_with_thinking",
    "check_allergen_alerts",
    "check_drug_food_interactions",
    "check_food_recalls",
    "get_restaurant_safety_info",
    "get_seasonal_food_safety",
    "run_recall_radar",
    "verify_nutrition_claim",
    "search_meals",
    "enrich_entry",
    "get_taste_profile",
    "suggest_meal",
    "standardize_recipe",
    "generate_image_prompt",
    "generate_social_post",
    "find_nearby_food",
    "find_nearby_food_tool",
    "log_meal_from_audio",
    "analyze_voice_transcript",
    "extract_voice_correction",
    "suggest_recipe_from_pantry",
    "check_pantry_expiry",
    "add_to_pantry",
    "update_pantry_item",
    "delete_pantry_item",
    "delegate_to_food_agent",
    "delegate_to_food_agent_tool",
    "generate_cottage_label",
    "generate_dietitian_report",
    "plan_food_festival",
    "detect_economic_gaps",
    "scale_recipe",
    "parse_menu",
    "parse_receipt",
    "check_dietary_compatibility",
    "generate_blog_post",
    "generate_blog_post_tool",
    "extract_recipe_from_media",
    "generate_recipe",
    "list_recipes",
    "list_recipes_tool",
    "get_recipe",
    "save_recipe",
    "update_recipe",
    "favorite_recipe",
    "archive_recipe",
    "delete_recipe",
    "get_flavor_pairings",
    "sync_to_calendar",
    "save_to_drive",
    "identify_emerging_trends",
    "enrich_with_knowledge_graph",
    "search_knowledge",
    "compare_foods",
    "get_astro_bridge",
    "get_cached_knowledge",
    "get_meals",
    "get_recent_meals_tool",
    "get_meals_by_ids",
    "get_meal",
    "add_meal",
    "update_meal",
    "delete_meal",
    "donate_meal",
    "generate_cooking_clip",
    "generate_food_image",
    "generate_recipe_video",
    "generate_research_report",
    "process_voice_meal_log",
    "voice_food_query",
    "search_meals",
    "search_meals_tool",
    "get_taste_profile_tool",
    "get_meal_suggestions_tool",
    "generate_social_post_tool",
    "generate_image_prompt_tool",
]
