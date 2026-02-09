# FCP Demo Guide

This guide walks through a short, repeatable demo of the Food Context Protocol.

## Prerequisites

1. Set environment variables:
   ```bash
   export GEMINI_API_KEY=your-key-here
   export GOOGLE_MAPS_API_KEY=your-key-here  # Optional
   ```

2. Install dependencies:
   ```bash
   make install
   ```

## Demo 1: Food Image Analysis

Analyze a food image to extract structured data.

```bash
# Start the server
make run-http

# In another terminal, analyze an image
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Sushi_bento.jpg/1280px-Sushi_bento.jpg"}'
```

Example output:
```json
{
  "dish_name": "Sushi Bento",
  "cuisine": "Japanese",
  "ingredients": [
    {"name": "salmon", "amount": "2 pieces"},
    {"name": "tuna", "amount": "2 pieces"},
    {"name": "rice", "amount": "1 cup"}
  ],
  "nutrition": {
    "calories": 450,
    "protein_g": 28,
    "carbs_g": 52,
    "fat_g": 12
  },
  "confidence": 0.92
}
```

## Demo 2: Food Safety Check

Check for active food recalls using real-time grounding.

```bash
curl "http://localhost:8080/safety/recalls?food_name=romaine%20lettuce"
```

## Demo 3: CLI Usage

```bash
# Add a meal
uv run foodlog add "Pad Thai" --venue "Thai Kitchen" --notes "Extra spicy"

# Search meals
uv run foodlog search "spicy noodles"

# Get taste profile
uv run foodlog profile

# Get suggestions
uv run foodlog suggest "quick healthy lunch"
```

## Demo 4: MCP Integration

For Claude Desktop or Gemini CLI integration:

1. Configure your MCP client to connect to the FCP server
2. The server exposes tools like `analyze_meal`, `search_meals`, `check_food_recalls`

## Gemini Features Demonstrated

| Feature | Demo |
|---------|------|
| Multimodal | Image analysis endpoint |
| Grounding | Food safety recalls |
| Function Calling | Structured extraction |
| Extended Thinking | Complex dish analysis |

## Troubleshooting

- `GEMINI_API_KEY not set`: export the variable before running.
- `Import errors`: run `make install`.
- `Connection refused`: ensure `make run-http` is running.
