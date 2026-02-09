# Tool Namespace Mapping

Converting from simple names to `dev.fcp.*` namespaced names following UCP pattern.

## Nutrition & Meals
- `get_recent_meals` → `dev.fcp.nutrition.get_recent_meals`
- `search_meals` → `dev.fcp.nutrition.search_meals`
- `add_meal` → `dev.fcp.nutrition.add_meal`
- `delete_meal` → `dev.fcp.nutrition.delete_meal`
- `log_meal_from_audio` → `dev.fcp.nutrition.log_meal_from_audio`

## Profile & Analytics
- `get_taste_profile` → `dev.fcp.profile.get_taste_profile`

## Planning
- `get_meal_suggestions` → `dev.fcp.planning.get_meal_suggestions`

## Recipes
- `list_recipes` → `dev.fcp.recipes.list`
- `get_recipe` → `dev.fcp.recipes.get`
- `save_recipe` → `dev.fcp.recipes.save`
- `favorite_recipe` → `dev.fcp.recipes.favorite`
- `archive_recipe` → `dev.fcp.recipes.archive`
- `delete_recipe` → `dev.fcp.recipes.delete`
- `standardize_recipe` → `dev.fcp.recipes.standardize`
- `scale_recipe` → `dev.fcp.recipes.scale`

## Safety
- `check_food_recalls` → `dev.fcp.safety.check_food_recalls`
- `check_allergen_alerts` → `dev.fcp.safety.check_allergen_alerts`
- `check_drug_food_interactions` → `dev.fcp.safety.check_drug_food_interactions`
- `get_restaurant_safety_info` → `dev.fcp.safety.get_restaurant_safety_info`
- `check_dietary_compatibility` → `dev.fcp.safety.check_dietary_compatibility`

## Inventory (Pantry)
- `add_to_pantry` → `dev.fcp.inventory.add_to_pantry`
- `get_pantry_suggestions` → `dev.fcp.inventory.get_pantry_suggestions`
- `check_pantry_expiry` → `dev.fcp.inventory.check_pantry_expiry`
- `update_pantry_item` → `dev.fcp.inventory.update_pantry_item`
- `delete_pantry_item` → `dev.fcp.inventory.delete_pantry_item`

## Discovery
- `find_nearby_food` → `dev.fcp.discovery.find_nearby_food`

## External Data
- `lookup_product` → `dev.fcp.external.lookup_product`

## Parsing
- `parse_menu` → `dev.fcp.parsing.parse_menu`
- `parse_receipt` → `dev.fcp.parsing.parse_receipt`

## Publishing & Social
- `generate_social_post` → `dev.fcp.publishing.generate_social_post`
- `generate_blog_post` → `dev.fcp.publishing.generate_blog_post`

## Visual
- `generate_image_prompt` → `dev.fcp.visual.generate_image_prompt`

## Agents
- `delegate_to_food_agent` → `dev.fcp.agents.delegate_to_food_agent`

## Business
- `donate_meal` → `dev.fcp.business.donate_meal`
- `generate_cottage_label` → `dev.fcp.business.generate_cottage_label`
- `plan_food_festival` → `dev.fcp.business.plan_food_festival`
- `detect_economic_gaps` → `dev.fcp.business.detect_economic_gaps`

## Clinical
- `generate_dietitian_report` → `dev.fcp.clinical.generate_dietitian_report`

## Connectors
- `sync_to_calendar` → `dev.fcp.connectors.sync_to_calendar`
- `save_to_drive` → `dev.fcp.connectors.save_to_drive`

## Trends
- `identify_emerging_trends` → `dev.fcp.trends.identify_emerging_trends`
- `get_flavor_pairings` → `dev.fcp.trends.get_flavor_pairings`
