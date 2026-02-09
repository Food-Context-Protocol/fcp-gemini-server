# FCP Server Makefile (Food Context Protocol)

# ============================================
# Variables
# ============================================
# Load .env file for commands (handles quoted values)
LOAD_ENV := set -a && [ -f .env ] && . ./.env && set +a;

# ============================================
# Self-documentation
# ============================================
.PHONY: help
help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================
# Default
# ============================================
.DEFAULT_GOAL := help

# ============================================
# Setup
# ============================================
install: ## Install all dependencies
	uv sync --all-extras --dev

# ============================================
# Testing
# ============================================
test: ## Run all tests (unit only, no emulator needed)
	uv run pytest tests/ -v --ignore=tests/integration/

test-unit: test ## Alias for test

coverage: ## Run tests with coverage (unit only)
	uv run pytest tests/ --ignore=tests/integration/ -x --tb=short --cov-report=html:htmlcov --cov-report=xml:coverage.xml

test-coverage: coverage ## Alias for coverage

test-quick: ## Run tests without coverage for speed
	uv run pytest tests/ --ignore=tests/integration/ -x -q --no-cov

# ============================================
# Integration Tests
# ============================================
test-integration: ## Run integration tests (requires API keys)
	uv run pytest tests/integration/ -v -m "integration"

test-all: ## Run all tests (unit + integration)
	uv run pytest tests/ -v -m "not integration or integration"

# ============================================
# Linting & Formatting
# ============================================
lint: ## Lint code with ruff
	uv run ruff check src/ tests/

lint-fix: ## Auto-fix lint errors with ruff
	uv run ruff check --fix src/ tests/

format: ## Format code with ruff
	uv run ruff format src/ tests/

format-check: ## Check code formatting without modifying files
	uv run ruff format --check src/ tests/

typecheck: ## Type check with ty
	uv run ty check src/ tests/

prek: ## Run prek hooks (ruff + ty)
	prek run --all-files

check: format-check lint coverage ## Run all checks (format, lint, coverage)

# ============================================
# Running (with logging to logs/)
# ============================================
LOGS_DIR := logs
$(LOGS_DIR):
	mkdir -p $(LOGS_DIR)

run: ## Run both MCP and HTTP servers
	$(LOAD_ENV) uv run python -m fcp.server

run-mcp: $(LOGS_DIR) ## Run MCP server only (logs to logs/mcp.log)
	$(LOAD_ENV) uv run python -m fcp.server --mcp 2>&1 | tee $(LOGS_DIR)/mcp.log

run-http: $(LOGS_DIR) ## Run HTTP server only (logs to logs/http.log)
	$(LOAD_ENV) uv run python -m fcp.server --http 2>&1 | tee $(LOGS_DIR)/http.log

# ============================================
# Development (with hot-reload and logging)
# ============================================
dev: dev-http ## Alias for dev-http

dev-http: $(LOGS_DIR) ## Run HTTP API with hot-reload (logs to logs/dev-http.log)
	$(LOAD_ENV) uv run uvicorn fcp.api:app --reload --reload-dir src --host 0.0.0.0 --port 8080 2>&1 | tee $(LOGS_DIR)/dev-http.log

dev-mcp: $(LOGS_DIR) ## Run MCP server with hot-reload (logs to logs/dev-mcp.log)
	$(LOAD_ENV) uv run watchfiles "python -m fcp.server --mcp" src/ 2>&1 | tee $(LOGS_DIR)/dev-mcp.log

# ============================================
# Demo
# ============================================
demo: ## Run demo workflow
	@echo "Running FCP Demo..."
	uv run python examples/workflows/photo_to_social.py

# ============================================
# CLI Shortcuts
# ============================================
cli-recent: ## Show recent meals
	uv run foodlog recent --limit 5

cli-search: ## Search meals for "spicy food"
	uv run foodlog search "spicy food"

cli-profile: ## Show user profile
	uv run foodlog profile

# ============================================
# OpenAPI & SDK Generation
# ============================================
openapi: ## Export OpenAPI spec to openapi.json
	$(LOAD_ENV) uv run python -c "import json; from fcp.api import app; print(json.dumps(app.openapi(), indent=2))" > openapi.json
	@echo "OpenAPI spec exported to openapi.json"

sdk: openapi ## Generate Python & TypeScript SDKs from OpenAPI spec
	cd fern && fern generate --group local
	@echo "SDKs generated in src/fcp/client (Python) and sdks/typescript"

fern-generate: sdk ## Alias for sdk (deprecated)

# ============================================
# Docker
# ============================================
docker-build: ## Build the Docker image
	docker build -t fcp-server .

docker-run: ## Run the Docker container
	docker run -p 8080:8080 --env-file .env fcp-server

# ============================================
# Cleaning
# ============================================
clean: ## Remove temporary files
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -f coverage.xml
	find . -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
