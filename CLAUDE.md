# CLAUDE.md - FCP Gemini Server

This file provides context for AI assistants working on the Food Context Protocol (FCP) codebase.

## Project Overview

FCP (Food Context Protocol) is an AI-powered food intelligence server built for the **Google Gemini 3 API Developer Competition (February 2026)**. It exposes 40+ food-related tools via two interfaces:

- **MCP Server** (stdio) - For Claude Desktop, Gemini CLI, Cursor, and other MCP-compatible AI assistants
- **HTTP API** (FastAPI) - For Flutter apps, CLIs, and direct API consumers

The core AI backend is **Google Gemini 3** (`google-genai` SDK). The project uses `uv` for dependency management and `hatchling` as the build backend.

## Quick Reference

```bash
# Setup
uv sync --all-extras --dev        # Install all dependencies

# Run
make run                          # Run MCP server (default, stdio)
make run-http                     # Run HTTP server on :8080
make dev                          # HTTP server with hot-reload

# Test
make test                         # Run unit tests (excludes integration/)
make test-quick                   # Fast tests without coverage
make coverage                     # Tests with coverage report

# Lint, Format & Type Check
make lint                         # Lint with ruff
make format                       # Format with ruff
make typecheck                    # Type check with ty
make prek                         # Run all prek hooks (ruff + ty)
make check                        # All checks: format-check + lint + coverage
```

## Repository Structure

```
fcp-gemini-server/
├── src/fcp/                    # Main package (src layout)
│   ├── server.py               # MCP server entry point (stdio transport)
│   ├── server_sse.py           # MCP server with SSE transport (HTTP)
│   ├── api.py                  # FastAPI HTTP application
│   ├── config.py               # Static constants (_Config dataclass)
│   ├── settings.py             # Environment-based settings (pydantic-settings)
│   ├── mcp/                    # MCP protocol layer
│   │   ├── registry.py         # Tool registry with @tool decorator
│   │   ├── initialize.py       # Tool auto-discovery via imports
│   │   ├── container.py        # Dependency injection container
│   │   └── protocols.py        # Protocol interfaces (Database, AIService, HTTPClient)
│   ├── mcp_tool_dispatch.py    # Tool call dispatcher with permissions
│   ├── mcp_resources.py        # MCP resources and prompts
│   ├── tools/                  # MCP tool implementations (40+ tools)
│   │   ├── __init__.py         # Re-exports all tools
│   │   ├── crud.py             # Meal CRUD (add_meal, get_meals, etc.)
│   │   ├── analyze.py          # Image analysis with Gemini
│   │   ├── safety.py           # Food recalls, allergens, drug interactions
│   │   ├── search.py           # Semantic search
│   │   ├── profile.py          # Taste profile analysis
│   │   ├── inventory.py        # Pantry management
│   │   ├── discovery.py        # Location-based food discovery
│   │   ├── recipe_*.py         # Recipe extraction, generation, CRUD
│   │   ├── social.py           # Social media content generation
│   │   ├── video.py            # Video generation (Veo 3.1)
│   │   ├── voice.py            # Voice processing (Live API)
│   │   ├── research.py         # Deep research reports
│   │   ├── external/           # External API tools (Open Food Facts, USDA)
│   │   └── ...                 # 30+ more tool modules
│   ├── routes/                 # FastAPI route handlers (one file per domain)
│   │   ├── __init__.py         # Router exports
│   │   ├── meals.py, search.py, safety.py, profile.py, ...
│   │   └── schemas.py          # Pydantic request/response models
│   ├── services/               # Business logic and external clients
│   │   ├── gemini.py           # Gemini client facade (singleton)
│   │   ├── gemini_base.py      # Base client with connection pooling
│   │   ├── gemini_generation.py # Mixins: generation, grounding, thinking, etc.
│   │   ├── gemini_live.py      # Live API (voice/streaming)
│   │   ├── gemini_async_ops.py # Video, deep research, caching
│   │   ├── database.py         # SQLite backend (async, aiosqlite)
│   │   ├── firestore.py        # Firestore client (production)
│   │   ├── storage.py          # Storage abstraction
│   │   └── ...                 # Maps, FDA, browser automation, etc.
│   ├── agents/                 # Autonomous AI agents (pydantic-ai)
│   ├── auth/                   # Authentication (local token-based)
│   │   ├── local.py            # Token auth, demo mode
│   │   └── permissions.py      # UserRole enum, write access guards
│   ├── security/               # Security layer
│   │   ├── input_sanitizer.py  # Input sanitization
│   │   ├── rate_limit.py       # SlowAPI rate limiting
│   │   ├── mcp_rate_limit.py   # MCP-specific rate limiting
│   │   ├── url_validator.py    # Image URL validation
│   │   └── prompt_builder.py   # Safe prompt construction
│   ├── utils/                  # Shared utilities
│   │   ├── circuit_breaker.py  # Circuit breaker for external calls
│   │   ├── errors.py           # Standardized error handlers
│   │   ├── metrics.py          # Prometheus metrics
│   │   ├── audit.py            # Audit logging
│   │   └── background_tasks.py # Async task management
│   ├── observability/          # Tool execution observability
│   ├── scheduler/              # APScheduler background jobs
│   └── prompts/                # Prompt templates
├── tests/
│   ├── conftest.py             # Shared fixtures, autouse mocks
│   ├── constants.py            # Centralized test constants
│   ├── fakes/                  # Fake implementations for testing
│   ├── unit/                   # Unit tests (mirroring src/ structure)
│   └── integration/            # Integration tests (require API keys)
├── gemini-extension/           # Gemini CLI extension (TOML commands)
├── examples/                   # Example workflows
├── docs/                       # Documentation assets
├── scripts/                    # Utility scripts
├── static/                     # Static files
├── demo-video/                 # Demo video generation scripts
├── fern/                       # Fern SDK generation config
├── pyproject.toml              # Project config, dependencies, tool settings
├── Makefile                    # Development commands
├── Dockerfile.api              # HTTP API container (multi-stage, uv)
├── Dockerfile.mcp              # MCP SSE server container
├── cloudbuild.yaml             # Cloud Build for API deployment
├── cloudbuild-mcp.yaml         # Cloud Build for MCP deployment
├── service.yaml                # Cloud Run service config (API)
├── service-mcp.yaml            # Cloud Run service config (MCP)
└── .github/workflows/deploy.yml # GitHub Actions CD pipeline
```

## Architecture

### Dual Server Architecture

The project runs as two independent servers:

1. **MCP Server** (`server.py`) - Communicates over stdio using the MCP protocol. Used by AI assistants (Claude Desktop, Gemini CLI). Default mode when running `fcp-server` CLI.
2. **HTTP API** (`api.py`) - FastAPI application on port 8080. Used by Flutter app and direct API consumers. Includes Swagger docs at `/docs`.

Both servers share the same tool implementations (`src/fcp/tools/`) and service layer (`src/fcp/services/`).

A third server mode, **MCP SSE** (`server_sse.py`), exposes MCP tools over HTTP/SSE for remote access (deployed at `mcp.fcp.dev`).

### Tool Registration System

Tools are registered via the `@tool` decorator from `fcp.mcp.registry`:

```python
from fcp.mcp.registry import tool

@tool(
    name="dev.fcp.nutrition.add_meal",
    requires_write=True,
    description="Log a meal to nutrition history",
    category="nutrition",
    dependencies={"db"},
)
async def add_meal(user_id: str, dish_name: str, db: Database = Depends(get_database)):
    ...
```

Key conventions:
- Tool names use reverse-DNS: `dev.fcp.<category>.<action>`
- Tools are async functions
- `user_id` parameter is auto-injected by the dispatcher
- Dependencies use `Depends()` markers (similar to FastAPI)
- `requires_write=True` blocks demo users
- JSON schemas are auto-generated from function signatures

### Dependency Injection

`fcp.mcp.container` provides a lightweight DI system:
- `Depends(provider_fn)` marks parameters for injection
- `resolve_dependencies()` inspects function signatures and resolves `Depends()` defaults
- Providers: `get_database()`, `get_ai_service()`, `get_http_client()`
- For testing, pass a `DependencyContainer` with mocks

### Configuration

Two-layer config system:
- `settings.py` - Environment variables via `pydantic-settings` (loads `.env` file)
- `config.py` - Static constants in a frozen `_Config` dataclass

Key env vars (see `.env.example`):
- `GEMINI_API_KEY` (required) - Must start with `AIza`
- `DATABASE_BACKEND` - `sqlite` (default) or `firestore`
- `FCP_TOKEN` - Auth token for write access
- `ENVIRONMENT` - `development`, `production`, or `test`

### Authentication & Permissions

- `UserRole.DEMO` - Read-only access (no token or invalid token)
- `UserRole.AUTHENTICATED` - Full access (valid `FCP_TOKEN`)
- HTTP endpoints use `Depends(require_write_access)` for write operations
- MCP tools use `requires_write=True` in the `@tool` decorator

### Database

- **Development**: SQLite via `aiosqlite` (stored in `data/fcp.db`)
- **Production**: Cloud Firestore (via `google-cloud-firestore`)
- Tables: `food_logs`, `pantry`, `recipes`, `drafts`, `published`, `notifications`, `users`, `receipts`
- JSON fields are transparently serialized/deserialized

### Gemini Client

`GeminiClient` is a mixin-based singleton (`services/gemini.py`):
- `GeminiBase` - Connection pooling, shared httpx client
- `GeminiGenerationMixin` - Text/JSON generation
- `GeminiGroundingMixin` - Google Search grounding
- `GeminiThinkingMixin` - Extended thinking with budget control
- `GeminiImageMixin` - Image generation (Imagen)
- `GeminiMediaMixin` - Multimodal analysis
- `GeminiVideoMixin` - Video generation (Veo 3.1)
- `GeminiLiveMixin` - Real-time voice (Live API)
- `GeminiCodeExecutionMixin` - Code execution sandbox
- `GeminiCacheMixin` - Context caching
- `GeminiDeepResearchMixin` - Deep research reports

Access via `get_gemini_client()` singleton or `get_gemini()` FastAPI dependency.

## Development Workflow

### Testing

```bash
make test          # Unit tests only (recommended for dev)
make test-quick    # Fast, no coverage
make coverage      # With coverage report (100% target)
```

- Framework: `pytest` with `pytest-asyncio` (auto mode)
- All tests must have a size marker: `small`, `medium`, or `large`
- Unit tests auto-assign `small`; integration tests auto-assign `large`
- HTTP requests are blocked in unit tests via `respx` (autouse `block_httpx_network` fixture)
- Test timeout: 10 seconds per test
- Coverage target: **100%** (with exclusions in `pyproject.toml`)
- Hypothesis profiles: `ci` (500 examples), `dev` (100), `quick` (10), `debug` (10, verbose)

Test environment automatically sets:
- `ENVIRONMENT=test`
- `GEMINI_API_KEY=AIzaTest...` (placeholder)
- `ENABLE_METRICS=false`
- `ENABLE_TELEMETRY=false`

### Linting, Formatting & Type Checking

```bash
make lint          # ruff check src/ tests/
make lint-fix      # ruff check --fix src/ tests/
make format        # ruff format src/ tests/
make format-check  # ruff format --check (CI-friendly)
make typecheck     # uv run ty check src/ tests/
make prek          # prek run --all-files (runs ruff + ty together)
```

- **Ruff** (`ruff`): Linter and formatter. Line length 120, target Python 3.11, rules: E, F, I, N, W, UP. Ignores E501 (handled by formatter). Excludes `src/fcp/client`.
- **ty** (`ty`): Type checker (configured in `pyproject.toml` under `[tool.ty]`). Run via `make typecheck` or as part of `make prek`. Several rules are set to `"ignore"` for dynamic `google-genai` types and Pydantic patterns: `unresolved-attribute`, `invalid-argument-type`, `unused-ignore-comment`, `unresolved-import`, `missing-argument`, `unknown-argument`, `possibly-missing-attribute`, `not-iterable`. Excludes `src/fcp/client`.
- **prek**: Runs all configured hooks (ruff + ty) across all files in one command. Use `make prek` for a quick full check before committing.

### Pre-commit Hooks

Configured in `.pre-commit-config.yaml`:
- **Pre-commit stage**: YAML check, trailing whitespace, end-of-file fixer, `make format`, `make lint typecheck`
- **Pre-push stage**: `make coverage` (runs full test suite with coverage)

Additionally, `prek` provides a standalone way to run ruff + ty without git hooks: `make prek`.

### Docker & Deployment

Two Docker images (multi-stage builds with `uv`):
- `Dockerfile.api` - HTTP API server (runs `uvicorn fcp.api:app`)
- `Dockerfile.mcp` - MCP SSE server (runs `uvicorn fcp.server_sse:app`)

Deployed to **Google Cloud Run** via:
- `cloudbuild.yaml` / `cloudbuild-mcp.yaml` - Cloud Build configs (run tests, build, push, deploy)
- `service.yaml` / `service-mcp.yaml` - Cloud Run service definitions
- `.github/workflows/deploy.yml` - GitHub Actions triggers Cloud Build on push to `main`

## Key Conventions

### Code Style
- Python 3.11+ (uses `X | None` union syntax, not `Optional[X]`)
- Async-first: all tool handlers and DB operations are async
- Line length: 120 characters
- `ruff` for both linting and formatting
- `# noqa: S608` on dynamic SQL (parameterized queries are safe)

### Adding a New Tool
1. Create or edit a file in `src/fcp/tools/`
2. Use the `@tool` decorator with a `dev.fcp.<category>.<name>` name
3. Add the import in `src/fcp/tools/__init__.py`
4. If it needs an HTTP endpoint, add a route in `src/fcp/routes/`
5. Write tests in `tests/unit/tools/`

### Adding a New Route
1. Create a new file in `src/fcp/routes/` with an `APIRouter`
2. Export it from `src/fcp/routes/__init__.py`
3. Include it in `src/fcp/api.py` via `app.include_router()`
4. Write tests in `tests/unit/routes/`

### Testing Patterns
- Mock Gemini via `mock_gemini_client` or `mock_gemini_v2` fixtures from `conftest.py`
- Mock DB via `mock_firestore_client` fixture
- Use `AsyncMock` for async service mocks
- `respx` blocks all unmocked HTTP in unit tests
- Centralized test constants in `tests/constants.py`
- Circuit breakers, rate limiters, and HTTP clients are auto-reset between tests

### Security Considerations
- All user input is sanitized via `input_sanitizer.py`
- Image URLs are validated via `url_validator.py`
- Prompts are built safely via `prompt_builder.py` (prevents injection)
- Rate limiting on both HTTP (SlowAPI) and MCP layers
- CORS restricted to known domains in production
- Security headers middleware (CSP, HSTS, X-Frame-Options)
- Non-root user in Docker containers

## Environment Setup

1. Copy `.env.example` to `.env`
2. Set `GEMINI_API_KEY` (required, get from https://aistudio.google.com/apikey)
3. Optionally set `GOOGLE_MAPS_API_KEY`, `USDA_API_KEY`, `FDA_API_KEY`
4. Run `uv sync --all-extras --dev` to install dependencies

## Connecting as MCP Server

### Local (stdio)
```json
{
  "mcpServers": {
    "fcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/fcp-gemini-server", "run", "python", "-m", "fcp.server"],
      "env": { "GEMINI_API_KEY": "your_key", "FCP_TOKEN": "optional_write_token" }
    }
  }
}
```

### Remote (SSE)
```json
{
  "mcpServers": {
    "fcp-remote": { "url": "https://mcp.fcp.dev/sse" }
  }
}
```
