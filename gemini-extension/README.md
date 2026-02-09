# FCP Extension for Gemini CLI

AI-powered food journaling with taste profiles, meal discovery, and nutrition analytics.

## Features

- **Food Journal Access**: View and search your meal history
- **Taste Profile Analysis**: Understand your cuisine preferences and eating patterns
- **AI Meal Suggestions**: Get personalized recommendations based on your history
- **Natural Language Search**: Find meals with queries like "that spicy Thai from last week"
- **Quick Logging**: Log new meals directly from the CLI

## Installation

### From GitHub

```bash
gemini extensions install https://github.com/yourusername/fcp-gemini-server
```

### For Development

```bash
# Clone the repo
git clone https://github.com/yourusername/fcp-gemini-server
cd fcp-gemini-server

# Link the extension for development
gemini extensions link ./gemini-extension
```

## Configuration

During installation, you'll be prompted for:

1. **FCP Token**: Your authentication token (format: `user_id:token`)
2. **Gemini API Key**: Your Google Gemini API key for AI features
3. **Firebase Credentials**: Path to your Google Application Credentials JSON

You can update settings later:

```bash
gemini extensions config fcp
```

## Commands

| Command | Description |
|---------|-------------|
| `/fcp:recent [count]` | Show recent meals (default: 5) |
| `/fcp:search <query>` | Search food journal with natural language |
| `/fcp:profile [period]` | Analyze taste preferences |
| `/fcp:suggest [context]` | Get personalized meal suggestions |
| `/fcp:log <meal>` | Log a new meal |
| `/fcp:discover [context]` | Discover new food experiences |
| `/fcp:stats` | Show food journal statistics |

## Example Usage

```
> /fcp:recent 3
Shows your last 3 meals with details

> /fcp:search that amazing ramen
Finds meals matching "that amazing ramen"

> /fcp:profile month
Analyzes your eating patterns from the past month

> /fcp:suggest date night
Recommends meals perfect for a date night

> /fcp:log Pad Thai at Bangkok Garden - extra spicy!
Logs a new meal entry

> /fcp:discover trying something new
Suggests cuisines and dishes you haven't tried
```

## MCP Tools Available

The extension exposes these tools that Gemini can use:

- `get_recent_meals` - Retrieve food log entries
- `search_meals` - Semantic search across journal
- `get_taste_profile` - Analyze eating patterns
- `get_meal_suggestions` - AI-powered recommendations
- `add_meal` - Log new meals
- `donate_meal` - Pledge meals for donation

## Requirements

- Python 3.11+
- FCP Server dependencies (see `pyproject.toml`)
- Firebase project with Firestore
- Gemini API key

## Architecture

```
Gemini CLI
    ↓
FCP Gemini Extension (MCP Client)
    ↓
FCP Server (MCP Server)
    ↓
┌─────────────────────────────────┐
│  Gemini 3 Flash API             │
│  • Function Calling             │
│  • Google Search Grounding      │
│  • Extended Thinking            │
│  • Code Execution               │
│  • 1M Token Context             │
└─────────────────────────────────┘
    ↓
Firebase (Firestore + Storage)
```

## License

Apache 2.0
