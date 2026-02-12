<div align="center">
  <img src="static/logos/fcp-logo.png" width="200" alt="FCP Logo"/>

  # FCP Gemini Server

  **Gemini 3-powered reference implementation of the [Food Context Protocol](https://github.com/Food-Context-Protocol/fcp)**

  [![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
  [![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
  [![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)]()

  [Protocol Spec](https://github.com/Food-Context-Protocol/fcp) ·
  [Try the API](https://fcp.dev) ·
  [Documentation](https://fcp.dev/docs)

</div>

---

## Overview

This is the **reference implementation** of the Food Context Protocol (FCP) in Python. It demonstrates how to implement FCP's 43 tools, dual transport (MCP + REST), and Gemini 3 integration.

For the **protocol specification**, see: [Food-Context-Protocol/fcp](https://github.com/Food-Context-Protocol/fcp)

> **Development Disclosure**: Development assisted by AI coding tools (Claude Code, GitHub Copilot, Cursor/Codex, Jules, Firebase Studio, Gemini API) for implementation. Core architecture, design, and functionality are original work.

> **⚠️ Legal Disclaimer**: FCP provides AI-generated food information **FOR INFORMATIONAL PURPOSES ONLY**. This is not medical, nutritional, or health advice. Do not rely on AI for allergen detection, food safety, or drug-food interactions without verification. See [LEGAL.md](LEGAL.md) for complete disclaimers.

## Features

- ✅ **43 MCP Tools** - Nutrition, recipes, safety, inventory, planning
- ✅ **Dual Transport** - MCP stdio + REST HTTP API
- ✅ **100% Test Coverage** - 2,981 passing tests
- ✅ **Gemini 3 Integration** - 15+ features (multimodal, grounding, thinking, Live API)
- ✅ **Type-Safe** - Pydantic schemas for all inputs/outputs
- ✅ **Auto-Generated SDKs** - Python + TypeScript via Fern

## Quick Start

### Prerequisites

- Python 3.11+
- Gemini API key (get from [ai.google.dev](https://ai.google.dev))

### Installation

```bash
# Clone repository
git clone https://github.com/Food-Context-Protocol/fcp-gemini-server.git
cd fcp-gemini-server

# Install dependencies
make install

# Configure
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Run

```bash
# HTTP Server (for web/mobile apps)
make dev-http
# Server runs on http://localhost:8080

# MCP Server (for Claude Desktop, CLI tools)
make run-mcp

# Run tests
make test
```

### Try It

```bash
# Health check
curl http://localhost:8080/health

# Analyze a meal photo
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c"
  }'

# Check food recalls
curl "http://localhost:8080/mcp/check_food_recalls?food_item=romaine+lettuce"

# List all MCP tools
curl http://localhost:8080/mcp/tools
```

## MCP Client Integrations

### Claude Desktop

See [CLAUDE.md](CLAUDE.md) for full setup instructions.

```json
{
  "mcpServers": {
    "fcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/fcp-gemini-server", "run", "python", "-m", "fcp.server"],
      "env": {
        "GEMINI_API_KEY": "your_key",
        "FCP_TOKEN": "your_token"
      }
    }
  }
}
```

### Gemini CLI Extension

Install the FCP extension for the Gemini CLI:

```bash
# Install extension
gemini extensions install ./gemini-extension

# Configure with your credentials
gemini extensions config fcp

# Use it
gemini
> /fcp:recent 5
> /fcp:search "that amazing ramen"
> /fcp:profile month
```

See [gemini-extension/README.md](gemini-extension/README.md) for all available commands.

## Architecture

```
┌─────────────┐
│   Clients   │  (CLI, Web, Mobile, Claude Desktop)
└──────┬──────┘
       │
       │  FCP Protocol (MCP stdio or REST HTTP)
       │
┌──────▼──────────────────────────────┐
│   FCP Server (This Repo)            │
│   - 43 Tool Implementations          │
│   - Pydantic Schema Validation      │
│   - Rate Limiting & Security        │
└──────┬──────────────────────────────┘
       │
       │  Google AI Python SDK
       │
┌──────▼──────────────────────────────┐
│   Gemini 3 Flash & Pro              │
│   - Multimodal Vision               │
│   - Function Calling                │
│   - Google Search Grounding         │
│   - Extended Thinking               │
│   - Code Execution                  │
│   - Live API                        │
└─────────────────────────────────────┘
```

## Project Structure

```
server/
├── src/fcp/
│   ├── tools/               # 43 MCP tool implementations
│   │   ├── nutrition/       # Meal analysis, logging
│   │   ├── recipes/         # Recipe search, scaling
│   │   ├── safety/          # Recall checks, allergens
│   │   ├── inventory/       # Pantry management
│   │   └── planning/        # Meal suggestions
│   ├── routes/              # REST API endpoints
│   │   └── schemas.py       # Pydantic response models
│   ├── services/            # External service clients
│   │   ├── gemini/          # Gemini 3 integration
│   │   ├── database.py      # SQLite persistence
│   │   └── fda.py           # OpenFDA integration
│   ├── security/            # Auth, rate limiting, validation
│   └── api.py               # FastAPI application
├── tests/                   # 100% branch coverage
│   ├── unit/                # Fast, hermetic tests
│   └── integration/         # E2E workflow tests
├── docs/                    # Implementation docs
└── Makefile                 # Common commands
```

## Gemini 3 Integration

### Multimodal Vision
```python
# Analyze food photo
from fcp.services.gemini import GeminiClient

client = GeminiClient()
result = await client.analyze_image(
    image_url="https://example.com/food.jpg",
    prompt="Extract nutrition information"
)
```

### Function Calling
```python
# Structured extraction with typed schemas
tools = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="log_meal",
            description="Log a meal with nutrition data",
            parameters=MealLogSchema
        )
    ])
]
```

### Google Search Grounding
```python
# Real-time FDA recall checks
response = await client.generate_content(
    prompt="Check if romaine lettuce has recalls",
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search_retrieval={})]
    )
)
```

## Available Commands

```bash
make install          # Install dependencies (uv sync)
make test             # Run tests with 100% coverage
make test-quick       # Run tests without coverage
make dev-http         # Start HTTP API with hot-reload
make run-mcp          # Start MCP stdio server
make lint             # Lint code with ruff
make format           # Format code with ruff
make typecheck        # Type check with mypy
make coverage         # Generate coverage report
make sdk              # Regenerate OpenAPI spec + SDKs
```

## Configuration

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key from [ai.google.dev](https://ai.google.dev) |

### Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_BACKEND` | Database backend (`sqlite` or `firestore`) | `sqlite` |
| `DEMO_MODE` | Enable demo mode (no auth required) | `false` |
| `DATABASE_URL` | SQLite database path (sqlite backend only) | `sqlite:///data/fcp.db` |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID (firestore backend only) | - |
| `LOG_LEVEL` | Logging level | `INFO` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit | `60` |

See `.env.example` for complete configuration options.

### Database Backend Selection

The server supports two database backends:

**SQLite (default)** - Best for local development:
```bash
# Uses local SQLite database at data/fcp.db
DATABASE_BACKEND=sqlite
make dev-http
```

**Cloud Firestore** - For production on Cloud Run:
```bash
# Install Firestore dependencies
uv sync --extra firestore

# Configure GCP project
export DATABASE_BACKEND=firestore
export GOOGLE_CLOUD_PROJECT=your-project-id

# For local testing, use service account credentials
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json

# Or use gcloud CLI default credentials
gcloud auth application-default login

# Start server
make dev-http
```

The backend is selected automatically based on the `DATABASE_BACKEND` environment variable. All 43 MCP tools work identically with either backend.

## Testing

```bash
# Run all tests with coverage (enforces 100%)
make test

# Run specific test file
pytest tests/unit/tools/test_nutrition.py -v

# Run core integration tests (backend-agnostic, sqlite)
RUN_INTEGRATION=1 DATABASE_BACKEND=sqlite pytest tests/integration/ -m "core and integration"

# Run external integration tests (USDA/FDA/maps/places), opt-in
RUN_INTEGRATION=1 RUN_EXTERNAL_INTEGRATION=1 DATABASE_BACKEND=sqlite pytest tests/integration/ -m "external and integration"

# Run full integration suite
RUN_INTEGRATION=1 RUN_EXTERNAL_INTEGRATION=1 DATABASE_BACKEND=sqlite pytest tests/integration/

# Watch mode during development
pytest-watch
```

## Deployment

See [docs/deployment-guide.md](docs/deployment-guide.md) for deployment to:
- Google Cloud Run
- Docker containers
- Kubernetes
- Local servers

Quick deploy to Cloud Run with Firestore:
```bash
gcloud run deploy fcp-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your-key,DATABASE_BACKEND=firestore,GOOGLE_CLOUD_PROJECT=your-project-id
```

**Note**: Cloud Run automatically uses Application Default Credentials, so no service account key is needed. Ensure the Cloud Run service account has Firestore permissions (`roles/datastore.user`).

## Contributing

We welcome contributions! See the main [CONTRIBUTING.md](https://github.com/Food-Context-Protocol/fcp/blob/main/CONTRIBUTING.md) for:
- Code of conduct
- Development workflow
- Testing requirements
- Pull request process

## Protocol Specification

This implementation follows the Food Context Protocol specification:

📖 **[View Specification](https://github.com/Food-Context-Protocol/fcp/blob/main/specification/FCP.md)**

## Related Repositories

- [fcp](https://github.com/Food-Context-Protocol/fcp) - Protocol specification
- [fcp-cli](https://github.com/Food-Context-Protocol/fcp-cli) - Command-line interface
- [python-sdk](https://github.com/Food-Context-Protocol/python-sdk) - Python SDK
- [typescript-sdk](https://github.com/Food-Context-Protocol/typescript-sdk) - TypeScript SDK

## License

Apache-2.0 - See [LICENSE](LICENSE) for software license and [LEGAL.md](LEGAL.md) for disclaimers

---

<div align="center">
  <strong>Reference Implementation | Food Context Protocol</strong><br/>
  Like Stripe for payments, FCP for food AI 🍽️
</div>
