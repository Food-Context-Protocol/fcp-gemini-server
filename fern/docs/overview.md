# Food Context Protocol

FCP is an open protocol that enables AI assistants to understand, track, and interact with food data across any application.

## What is FCP?

The Food Context Protocol (FCP) provides a standardized way for AI models to access food intelligence through 40+ tools organized into six core domains:

- **Nutrition** - Meal logging, dietary analysis, taste profiles
- **Recipes** - Recipe management, extraction, scaling
- **Safety** - FDA recalls, allergen alerts, freshness predictions
- **Inventory** - Pantry tracking, expiry monitoring, shopping lists
- **Discovery** - Restaurant search, product lookup, trend analysis
- **Planning** - Meal suggestions, event planning, content generation

## Architecture

FCP is built on the Model Context Protocol (MCP), providing dual transport support:

- **MCP Protocol** (`mcp.fcp.dev`) - For AI assistants like Claude and ChatGPT
- **REST API** (`api.fcp.dev`) - For traditional HTTP integrations

## Powered by Gemini 3

FCP leverages 15+ Gemini 3 features including:
- Multimodal understanding (images, audio, video, PDFs)
- Grounding and real-time search
- Thinking mode for complex reasoning
- Live API for voice interactions
- Function calling and tool integration

## Get Started

Install the SDK:

```bash
# Python
uv add fcp-python

# TypeScript
npm install @fcp/sdk
```

Example usage:

```python
from fcp import FoodContextClient

client = FoodContextClient(api_key="your-key")
meals = await client.nutrition.get_recent_meals(limit=5)
```

## Next Steps

- Browse the [API Reference](#api-reference) for all available tools
- Check out [Quick Start](#quick-start) for integration examples
- Join the community on [GitHub](https://github.com/Food-Context-Protocol)
