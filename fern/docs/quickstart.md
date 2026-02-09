# Quick Start

Get started with FCP in minutes.

## Installation

### Python

```bash
pip install fcp-python
```

### TypeScript

```bash
npm install @fcp/sdk
```

## Authentication

Get your API key from the [FCP Dashboard](https://fcp.dev/dashboard) (coming soon) or use the demo key for testing:

```python
from fcp import FoodContextClient

client = FoodContextClient(
    api_key="your-api-key",
    base_url="https://api.fcp.dev"
)
```

## Basic Usage

### Log a Meal

```python
# Add a meal
meal = await client.nutrition.add_meal(
    dish_name="Grilled Salmon",
    venue="Home Kitchen",
    rating=5
)

print(f"Logged meal: {meal.id}")
```

### Search Meals

```python
# Search your meal history
results = await client.nutrition.search_meals(
    query="spicy noodles",
    limit=10
)

for meal in results:
    print(f"{meal.dish_name} at {meal.venue}")
```

### Get Recipe

```python
# Fetch a recipe
recipe = await client.recipes.get(recipe_id="r-123")
print(f"{recipe.name}: {recipe.servings} servings")
```

### Check Food Recalls

```python
# Check for FDA recalls
recalls = await client.safety.check_food_recalls(
    food_name="peanut butter"
)

if recalls:
    print(f"⚠️ Found {len(recalls)} recalls")
```

## MCP Integration

Use FCP with Claude Desktop or other MCP-aware tools:

```json
{
  "mcpServers": {
    "fcp": {
      "url": "https://mcp.fcp.dev",
      "apiKey": "your-api-key"
    }
  }
}
```

## REST API

Use the REST API directly with curl:

```bash
curl https://api.fcp.dev/v1/nutrition/recent \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json"
```

## Next Steps

- Explore all [40+ tools](#api-reference) in the API Reference
- Check out [example workflows](https://github.com/Food-Context-Protocol/fcp-gemini-server/tree/main/examples)
- Read the [protocol specification](https://github.com/Food-Context-Protocol/fcp)
