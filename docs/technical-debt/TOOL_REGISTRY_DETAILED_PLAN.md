# Tool Registry Refactoring - Comprehensive Plan
**Date:** February 8, 2026
**Status:** Planning Phase
**Estimated Effort:** 12-16 hours over 2-3 weeks

---

## Table of Contents
1. [Current State Analysis](#current-state-analysis)
2. [Research & Best Practices](#research--best-practices)
3. [Proposed Architecture](#proposed-architecture)
4. [Dependency Injection Strategy](#dependency-injection-strategy)
5. [Testing Strategy](#testing-strategy)
6. [Implementation Roadmap](#implementation-roadmap)
7. [Tool Catalog & Migration Plan](#tool-catalog--migration-plan)

---

## Current State Analysis

### Problem Statement
`src/fcp/mcp_tool_dispatch.py` contains **626 lines** with **43 if/elif blocks**, making it:
- ❌ Hard to maintain
- ❌ Difficult to test (tight coupling)
- ❌ Not extensible
- ❌ Repetitive permission checks
- ❌ No tool discovery mechanism

### Tool Dependencies Analysis

**Current pattern** (from `src/fcp/tools/`):
```python
# Direct singleton imports = hard to test
from fcp.services.firestore import firestore_client
from fcp.services.gemini import gemini

async def add_meal(user_id: str, dish_name: str, ...):
    # Tightly coupled to globals
    await firestore_client.create_log(user_id, data)
    result = await gemini.generate_json(prompt)
```

**Common dependencies across tools:**
1. **firestore_client** - Used by ~35/43 tools (database operations)
2. **gemini** - Used by ~20/43 tools (AI generation)
3. **httpx.AsyncClient** - Used by ~5/43 tools (external APIs)
4. **logger** - Used by all tools (logging)

**Testing pain points:**
- ❌ Can't mock firestore_client without monkeypatching
- ❌ Can't test tools without real Gemini API
- ❌ Integration tests require full database setup
- ❌ No isolation between test runs

---

## Research & Best Practices

### Key Insights from Industry

Based on research from [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/), [Python DI Guide](https://www.datacamp.com/tutorial/python-dependency-injection), and [Dependency Injector](https://python-dependency-injector.ets-labs.org/):

**✅ Dependency Injection Benefits:**
1. **Testability** - Swap real implementations with mocks using `container.override()`
2. **Modularity** - Components are loosely coupled
3. **Maintainability** - Dependencies are explicit, not hidden
4. **Flexibility** - Easy to change implementations

**✅ Registry Pattern Benefits:**
1. **Auto-discovery** - Tools register themselves
2. **Centralized metadata** - Name, permissions, schema in one place
3. **Runtime inspection** - List all available tools
4. **Type safety** - Validate arguments against schemas

### FastAPI Integration Pattern

From [Mastering DI in FastAPI](https://medium.com/@azizmarzouki/mastering-dependency-injection-in-fastapi-clean-scalable-and-testable-apis-5f78099c3362):

```python
# Dependencies can be injected at the decorator level
@router.post("/endpoint", dependencies=[Depends(auth_guard)])
async def handler():
    ...

# Or as function parameters
async def handler(db: Database = Depends(get_db)):
    ...
```

**Best practices:**
- Program to interfaces, not implementations
- Favor composition over inheritance
- Keep dependencies small and focused
- Use containers for complex dependency graphs

---

## Proposed Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────┐
│                  Tool Registry                       │
│  - Decorator-based registration                     │
│  - Metadata storage (name, permissions, schema)     │
│  - Tool discovery & validation                      │
└────────────────┬────────────────────────────────────┘
                 │
                 ├── Dependency Container
                 │   - firestore_client provider
                 │   - gemini provider
                 │   - httpx client provider
                 │   - logger provider
                 │
                 ├── Tool Handlers (43 tools)
                 │   - Decorated with @tool
                 │   - Dependencies injected via parameters
                 │   - Pure functions (testable)
                 │
                 └── Dispatcher
                     - Registry lookup
                     - Permission checks
                     - Dependency resolution
                     - Error handling
```

### Core Classes

#### 1. Tool Registry (`src/fcp/mcp/registry.py`)

```python
from dataclasses import dataclass, field
from typing import Callable, Any
from inspect import signature

@dataclass
class ToolMetadata:
    """Metadata for a registered tool."""
    name: str
    handler: Callable
    requires_write: bool = False
    requires_admin: bool = False
    description: str = ""
    category: str = "general"

    # Dependency injection
    dependencies: dict[str, type] = field(default_factory=dict)

    # Auto-generated schema from function signature
    schema: dict[str, Any] | None = None

    def __post_init__(self):
        if self.schema is None:
            self.schema = self._infer_schema()

    def _infer_schema(self) -> dict[str, Any]:
        """Infer JSON schema from function signature."""
        sig = signature(self.handler)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            # Skip DI parameters (Container, Database, etc.)
            if param_name in self.dependencies:
                continue

            # Map Python types to JSON schema types
            param_type = param.annotation
            if param_type == str:
                properties[param_name] = {"type": "string"}
            elif param_type == int:
                properties[param_name] = {"type": "integer"}
            elif param_type == bool:
                properties[param_name] = {"type": "boolean"}
            # ... more type mappings

            if param.default == param.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }


class ToolRegistry:
    """Central registry for all FCP tools."""

    def __init__(self):
        self._tools: dict[str, ToolMetadata] = {}

    def register(self, metadata: ToolMetadata) -> None:
        """Register a tool."""
        if metadata.name in self._tools:
            raise ValueError(f"Tool {metadata.name} already registered")
        self._tools[metadata.name] = metadata

    def get(self, name: str) -> ToolMetadata | None:
        """Get tool metadata by name."""
        return self._tools.get(name)

    def list_tools(
        self,
        category: str | None = None,
        requires_write: bool | None = None,
    ) -> list[ToolMetadata]:
        """List all registered tools with optional filters."""
        tools = list(self._tools.values())

        if category:
            tools = [t for t in tools if t.category == category]
        if requires_write is not None:
            tools = [t for t in tools if t.requires_write == requires_write]

        return tools

    def get_mcp_tool_list(self) -> list[dict[str, Any]]:
        """Generate MCP-compatible tool list for clients."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.schema,
            }
            for t in self._tools.values()
        ]


# Global registry instance
tool_registry = ToolRegistry()


def tool(
    name: str,
    *,
    requires_write: bool = False,
    requires_admin: bool = False,
    description: str = "",
    category: str = "general",
):
    """
    Decorator to register a tool with the registry.

    Usage:
        @tool(
            name="dev.fcp.nutrition.add_meal",
            requires_write=True,
            description="Log a meal to nutrition history",
            category="nutrition",
        )
        async def add_meal(
            user_id: str,
            dish_name: str,
            db: FirestoreClient = Depends(get_firestore),
        ):
            await db.create_log(user_id, {...})
    """
    def decorator(func: Callable) -> Callable:
        # Extract dependency parameters
        sig = signature(func)
        dependencies = {
            name: param.annotation
            for name, param in sig.parameters.items()
            if hasattr(param.default, "__class__") and
               param.default.__class__.__name__ == "Depends"
        }

        metadata = ToolMetadata(
            name=name,
            handler=func,
            requires_write=requires_write,
            requires_admin=requires_admin,
            description=description,
            category=category,
            dependencies=dependencies,
        )
        tool_registry.register(metadata)
        return func
    return decorator
```

#### 2. Dependency Container (`src/fcp/mcp/container.py`)

```python
from dataclasses import dataclass
from typing import Protocol


# Define interfaces (program to interfaces, not implementations)
class Database(Protocol):
    """Database interface for tool dependencies."""
    async def get_user_logs(self, user_id: str, **kwargs): ...
    async def create_log(self, user_id: str, data: dict): ...
    async def get_pantry(self, user_id: str): ...
    # ... other methods


class AIService(Protocol):
    """AI service interface for tool dependencies."""
    async def generate_json(self, prompt: str): ...
    async def generate_content(self, prompt: str): ...
    async def analyze_image(self, image_url: str, prompt: str): ...


@dataclass
class DependencyContainer:
    """Container for managing tool dependencies."""

    database: Database
    ai_service: AIService
    http_client: Any  # httpx.AsyncClient
    logger: Any  # logging.Logger

    def override_database(self, mock_db: Database) -> None:
        """Override database for testing."""
        self.database = mock_db

    def override_ai_service(self, mock_ai: AIService) -> None:
        """Override AI service for testing."""
        self.ai_service = mock_ai


# FastAPI-style dependency providers
def get_database(container: DependencyContainer = None):
    """Dependency provider for database."""
    if container is None:
        # Production: use real firestore_client
        from fcp.services.firestore import firestore_client
        return firestore_client
    return container.database


def get_ai_service(container: DependencyContainer = None):
    """Dependency provider for AI service."""
    if container is None:
        # Production: use real gemini
        from fcp.services.gemini import gemini
        return gemini
    return container.ai_service


class Depends:
    """FastAPI-style dependency marker."""
    def __init__(self, provider: Callable):
        self.provider = provider
```

#### 3. Updated Dispatcher (`src/fcp/mcp_tool_dispatch.py`)

```python
async def dispatch_tool_call(
    name: str,
    arguments: dict[str, Any],
    user: AuthenticatedUser,
    container: DependencyContainer | None = None,
) -> ToolExecutionResult:
    """
    Execute an MCP tool with dependency injection.

    Args:
        name: Tool name (e.g., "dev.fcp.nutrition.add_meal")
        arguments: Tool arguments from MCP client
        user: Authenticated user context
        container: Optional DI container (for testing)
    """
    # 1. Lookup tool in registry
    metadata = tool_registry.get(name)
    if not metadata:
        return _error(f"Unknown tool: {name}")

    # 2. Check permissions
    if metadata.requires_write and not user.can_write:
        return _error("write_permission_denied")
    if metadata.requires_admin and not user.is_admin:
        return _error("admin_permission_denied")

    # 3. Resolve dependencies
    resolved_deps = {}
    for dep_name, dep_type in metadata.dependencies.items():
        if dep_name == "db":
            resolved_deps["db"] = get_database(container)
        elif dep_name == "ai":
            resolved_deps["ai"] = get_ai_service(container)
        # ... other dependency types

    # 4. Inject user_id as first parameter
    if "user_id" in signature(metadata.handler).parameters:
        arguments = {"user_id": user.user_id, **arguments}

    # 5. Execute handler with dependencies
    try:
        result = await metadata.handler(**arguments, **resolved_deps)
        return _ok(result)
    except TypeError as e:
        logger.error(f"Invalid arguments for {name}: {e}")
        return _error(f"Invalid arguments: {e}")
    except Exception as e:
        logger.exception(f"Tool {name} failed")
        return _error(str(e))
```

---

## Dependency Injection Strategy

### Migration Pattern

**Before (tightly coupled):**
```python
# src/fcp/tools/crud.py
from fcp.services.firestore import firestore_client

async def add_meal(user_id: str, dish_name: str, ...):
    log_id = await firestore_client.create_log(user_id, data)
    return {"success": True, "log_id": log_id}
```

**After (dependency injection):**
```python
# src/fcp/tools/crud.py
from fcp.mcp.registry import tool
from fcp.mcp.container import Depends, get_database, Database

@tool(
    name="dev.fcp.nutrition.add_meal",
    requires_write=True,
    description="Log a meal to nutrition history",
    category="nutrition",
)
async def add_meal(
    user_id: str,
    dish_name: str,
    venue: str | None = None,
    notes: str | None = None,
    db: Database = Depends(get_database),  # ← Injected dependency
):
    """Add a new meal and trigger pantry deduction."""
    data = {
        "dish_name": dish_name,
        "venue_name": venue,
        "notes": notes,
        "processing_status": "pending",
    }
    log_id = await db.create_log(user_id, data)
    return {"success": True, "log_id": log_id}
```

### Dependency Categories

| Dependency | Usage | Testing Strategy |
|------------|-------|------------------|
| **firestore_client** (Database) | 35/43 tools | Mock with `AsyncMock` |
| **gemini** (AIService) | 20/43 tools | Mock with predefined responses |
| **httpx.AsyncClient** | 5/43 tools | Mock with `respx` library |
| **logger** | All tools | Real logger in tests (capture output) |

---

## Testing Strategy

### Unit Testing with DI

**Example: Testing `add_meal` tool**

```python
# tests/unit/tools/test_crud.py
import pytest
from unittest.mock import AsyncMock
from fcp.tools.crud import add_meal
from fcp.mcp.container import DependencyContainer

@pytest.fixture
def mock_container():
    """Create a container with mocked dependencies."""
    mock_db = AsyncMock()
    mock_db.create_log.return_value = "log_123"

    return DependencyContainer(
        database=mock_db,
        ai_service=AsyncMock(),
        http_client=AsyncMock(),
        logger=AsyncMock(),
    )

@pytest.mark.asyncio
async def test_add_meal_success(mock_container):
    """Test add_meal creates a log successfully."""
    # Arrange
    user_id = "user_456"
    dish_name = "Spaghetti Carbonara"

    # Act - inject mocked database
    result = await add_meal(
        user_id=user_id,
        dish_name=dish_name,
        venue="Test Restaurant",
        db=mock_container.database,  # ← Inject mock
    )

    # Assert
    assert result["success"] is True
    assert result["log_id"] == "log_123"

    # Verify database interaction
    mock_container.database.create_log.assert_called_once()
    call_args = mock_container.database.create_log.call_args
    assert call_args[0][0] == user_id  # user_id
    assert call_args[0][1]["dish_name"] == dish_name  # data


@pytest.mark.asyncio
async def test_add_meal_database_error(mock_container):
    """Test add_meal handles database errors."""
    # Arrange
    mock_container.database.create_log.side_effect = Exception("DB connection failed")

    # Act & Assert
    with pytest.raises(Exception, match="DB connection failed"):
        await add_meal(
            user_id="user_456",
            dish_name="Test Dish",
            db=mock_container.database,
        )
```

### Integration Testing

**Example: Testing dispatcher with real registry**

```python
# tests/integration/test_dispatcher.py
import pytest
from fcp.mcp_tool_dispatch import dispatch_tool_call
from fcp.mcp.registry import tool_registry
from fcp.mcp.container import DependencyContainer
from fcp.auth.permissions import AuthenticatedUser

@pytest.fixture
def test_container():
    """Create test container with mocks."""
    return DependencyContainer(
        database=AsyncMock(),
        ai_service=AsyncMock(),
        http_client=AsyncMock(),
        logger=AsyncMock(),
    )

@pytest.mark.asyncio
async def test_dispatch_add_meal(test_container):
    """Test dispatching add_meal tool."""
    # Arrange
    user = AuthenticatedUser(user_id="user_123", can_write=True)

    test_container.database.create_log.return_value = "log_456"

    # Act
    result = await dispatch_tool_call(
        name="dev.fcp.nutrition.add_meal",
        arguments={"dish_name": "Test Meal", "venue": "Test Venue"},
        user=user,
        container=test_container,  # ← Inject test container
    )

    # Assert
    assert result.status == "success"
    assert "log_456" in result.contents[0].text


@pytest.mark.asyncio
async def test_dispatch_permission_denied(test_container):
    """Test dispatcher enforces write permissions."""
    # Arrange
    user = AuthenticatedUser(user_id="user_123", can_write=False)

    # Act
    result = await dispatch_tool_call(
        name="dev.fcp.nutrition.add_meal",  # requires_write=True
        arguments={"dish_name": "Test"},
        user=user,
        container=test_container,
    )

    # Assert
    assert result.status == "error"
    assert "write_permission_denied" in result.error_message
```

### Test Coverage Strategy

**Coverage goals:**
- ✅ **Unit tests:** Each tool handler - 100% coverage
- ✅ **Integration tests:** Dispatcher + registry - 100% coverage
- ✅ **E2E tests:** Full MCP flow with real services - smoke tests only

**Test organization:**
```
tests/
├── unit/
│   ├── mcp/
│   │   ├── test_registry.py      # Registry & decorator
│   │   └── test_container.py     # DI container
│   └── tools/
│       ├── test_crud.py           # CRUD tools
│       ├── test_inventory.py     # Inventory tools
│       ├── test_recipes.py       # Recipe tools
│       └── ...                   # All 43 tools
├── integration/
│   ├── test_dispatcher.py         # Dispatcher with mocks
│   └── test_tool_execution.py    # End-to-end tool flows
└── fixtures/
    ├── mock_firestore.py          # Shared mock database
    └── mock_gemini.py             # Shared mock AI service
```

---

## Implementation Roadmap

### Phase 1: Infrastructure (Week 1, 4-6 hours)

**Goals:**
- [ ] Create registry and decorator system
- [ ] Create DI container and protocols
- [ ] Write comprehensive unit tests
- [ ] Document patterns and examples

**Files to create:**
1. `src/fcp/mcp/registry.py` (~200 lines)
2. `src/fcp/mcp/container.py` (~150 lines)
3. `src/fcp/mcp/protocols.py` (~100 lines) - Database, AIService interfaces
4. `tests/unit/mcp/test_registry.py` (~300 lines)
5. `tests/unit/mcp/test_container.py` (~200 lines)

**Acceptance criteria:**
- ✅ Registry can register and lookup tools
- ✅ Decorator auto-generates schemas
- ✅ Container can override dependencies
- ✅ 100% test coverage on registry & container

### Phase 2: Proof of Concept (Week 1-2, 3-4 hours)

**Goals:**
- [ ] Migrate 5 simple tools to new pattern
- [ ] Update dispatcher to check registry first
- [ ] Maintain backward compatibility
- [ ] Validate testing approach works

**Tools to migrate (nutrition category):**
1. ✅ `dev.fcp.nutrition.add_meal` - Simple CRUD
2. ✅ `dev.fcp.nutrition.delete_meal` - Simple CRUD
3. ✅ `dev.fcp.nutrition.get_recent_meals` - Read-only
4. ✅ `dev.fcp.inventory.add_to_pantry` - CRUD with AI
5. ✅ `dev.fcp.recipes.get` - Simple read

**Acceptance criteria:**
- ✅ All 5 tools have @tool decorators
- ✅ All 5 tools work via dispatcher
- ✅ All 5 tools have unit tests with mocks
- ✅ Legacy if/elif blocks still work (fallback)

### Phase 3: Bulk Migration (Week 2-3, 6-8 hours)

**Goals:**
- [ ] Migrate remaining 38 tools in batches
- [ ] Group by category for efficient migration
- [ ] Write unit tests for each tool
- [ ] Verify integration tests pass

**Migration order (by category):**
1. **Recipes** (8 tools) - Similar patterns
2. **Inventory** (4 tools) - Shared logic
3. **Safety** (5 tools) - External API calls
4. **Parsing** (2 tools) - Heavy AI usage
5. **Publishing** (2 tools) - Content generation
6. **Discovery** (1 tool) - Location services
7. **Business** (4 tools) - Complex workflows
8. **Agents** (1 tool) - Meta-tool
9. **Others** (11 tools) - Miscellaneous

**Acceptance criteria:**
- ✅ All 43 tools migrated and decorated
- ✅ All tools have unit tests (100% coverage)
- ✅ Integration tests pass
- ✅ No regression in functionality

### Phase 4: Dispatcher Cleanup (Week 3, 2 hours)

**Goals:**
- [ ] Remove all legacy if/elif blocks
- [ ] Simplify dispatcher to ~100 lines
- [ ] Add schema validation
- [ ] Update integration tests

**Acceptance criteria:**
- ✅ Dispatcher only uses registry
- ✅ No if/elif blocks remain
- ✅ Schema validation works
- ✅ All tests pass

### Phase 5: Features & Polish (Week 3, 2-3 hours)

**Goals:**
- [ ] Auto-generate MCP tool list from registry
- [ ] Add tool categorization/filtering
- [ ] Document DI patterns for developers
- [ ] Performance benchmarks

**New capabilities:**
```python
# Auto-list tools for MCP clients
tools = tool_registry.get_mcp_tool_list()

# Filter tools by category
nutrition_tools = tool_registry.list_tools(category="nutrition")

# Filter by permissions
write_tools = tool_registry.list_tools(requires_write=True)
```

**Acceptance criteria:**
- ✅ MCP clients get auto-generated tool list
- ✅ Developer docs updated
- ✅ Performance tests show no regression
- ✅ All tests green

---

## Tool Catalog & Migration Plan

### Complete Tool List (43 tools)

| # | Tool Name | Category | Requires Write | Dependencies | Complexity | Est. Time |
|---|-----------|----------|----------------|--------------|------------|-----------|
| 1 | dev.fcp.nutrition.add_meal | nutrition | Yes | DB | Low | 30min |
| 2 | dev.fcp.nutrition.delete_meal | nutrition | Yes | DB | Low | 20min |
| 3 | dev.fcp.nutrition.get_recent_meals | nutrition | No | DB | Low | 20min |
| 4 | dev.fcp.nutrition.search_meals | nutrition | No | DB | Low | 20min |
| 5 | dev.fcp.nutrition.log_meal_from_audio | nutrition | Yes | DB, AI | Medium | 40min |
| 6 | dev.fcp.inventory.add_to_pantry | inventory | Yes | DB | Low | 30min |
| 7 | dev.fcp.inventory.delete_pantry_item | inventory | Yes | DB | Low | 20min |
| 8 | dev.fcp.inventory.update_pantry_item | inventory | Yes | DB | Low | 20min |
| 9 | dev.fcp.inventory.check_pantry_expiry | inventory | No | DB, AI | Medium | 40min |
| 10 | dev.fcp.inventory.get_pantry_suggestions | inventory | No | DB, AI | Medium | 40min |
| 11 | dev.fcp.recipes.get | recipes | No | DB | Low | 20min |
| 12 | dev.fcp.recipes.list | recipes | No | DB | Low | 20min |
| 13 | dev.fcp.recipes.save | recipes | Yes | DB | Low | 30min |
| 14 | dev.fcp.recipes.delete | recipes | Yes | DB | Low | 20min |
| 15 | dev.fcp.recipes.archive | recipes | Yes | DB | Low | 20min |
| 16 | dev.fcp.recipes.favorite | recipes | Yes | DB | Low | 20min |
| 17 | dev.fcp.recipes.scale | recipes | No | AI | Low | 30min |
| 18 | dev.fcp.recipes.standardize | recipes | No | AI | Medium | 40min |
| 19 | extract_recipe_from_media | recipes | No | AI | High | 60min |
| 20 | dev.fcp.safety.check_allergen_alerts | safety | No | HTTP | Medium | 40min |
| 21 | dev.fcp.safety.check_food_recalls | safety | No | HTTP | Medium | 40min |
| 22 | dev.fcp.safety.check_dietary_compatibility | safety | No | AI | Medium | 40min |
| 23 | dev.fcp.safety.check_drug_food_interactions | safety | No | AI | Medium | 40min |
| 24 | dev.fcp.safety.get_restaurant_safety_info | safety | No | HTTP | Medium | 40min |
| 25 | dev.fcp.parsing.parse_menu | parsing | No | AI | High | 60min |
| 26 | dev.fcp.parsing.parse_receipt | parsing | No | AI | High | 60min |
| 27 | dev.fcp.publishing.generate_blog_post | publishing | No | AI | Medium | 40min |
| 28 | dev.fcp.publishing.generate_social_post | publishing | No | AI | Medium | 40min |
| 29 | dev.fcp.discovery.find_nearby_food | discovery | No | HTTP | Medium | 40min |
| 30 | dev.fcp.business.detect_economic_gaps | business | No | DB, AI | High | 60min |
| 31 | dev.fcp.business.donate_meal | business | Yes | DB | Medium | 40min |
| 32 | dev.fcp.business.generate_cottage_label | business | No | AI | Medium | 40min |
| 33 | dev.fcp.business.plan_food_festival | business | No | AI | High | 60min |
| 34 | dev.fcp.clinical.generate_dietitian_report | clinical | No | DB, AI | High | 60min |
| 35 | dev.fcp.connectors.save_to_drive | connectors | Yes | HTTP | Medium | 40min |
| 36 | dev.fcp.connectors.sync_to_calendar | connectors | Yes | HTTP | Medium | 40min |
| 37 | dev.fcp.agents.delegate_to_food_agent | agents | No | AI | High | 60min |
| 38 | dev.fcp.external.lookup_product | external | No | HTTP | Medium | 40min |
| 39 | dev.fcp.planning.get_meal_suggestions | planning | No | DB, AI | Medium | 40min |
| 40 | dev.fcp.profile.get_taste_profile | profile | No | DB | Low | 20min |
| 41 | dev.fcp.trends.get_flavor_pairings | trends | No | AI | Medium | 40min |
| 42 | dev.fcp.trends.identify_emerging_trends | trends | No | DB, AI | High | 60min |
| 43 | dev.fcp.visual.generate_image_prompt | visual | No | AI | Medium | 40min |

**Total migration time:** ~27 hours (including tests)

### Migration Batches

**Batch 1 - PoC (5 tools, 2.5 hours):**
- Tools: 1, 2, 3, 6, 11
- Goal: Validate pattern works

**Batch 2 - Nutrition (2 tools, 1.5 hours):**
- Tools: 4, 5

**Batch 3 - Inventory (3 tools, 2 hours):**
- Tools: 7, 8, 9, 10

**Batch 4 - Recipes (7 tools, 4 hours):**
- Tools: 12, 13, 14, 15, 16, 17, 18, 19

**Batch 5 - Safety (5 tools, 3.5 hours):**
- Tools: 20, 21, 22, 23, 24

**Batch 6 - Parsing (2 tools, 2 hours):**
- Tools: 25, 26

**Batch 7 - Publishing (2 tools, 1.5 hours):**
- Tools: 27, 28

**Batch 8 - Remaining (17 tools, 10 hours):**
- Tools: 29-43

---

## Success Metrics

**Code Quality:**
- ✅ Dispatcher reduced from 626 to ~100 lines (-84%)
- ✅ 100% test coverage on all tools
- ✅ 100% test coverage on registry/container
- ✅ All tools have explicit dependency injection

**Testing:**
- ✅ Unit tests run without database/AI services
- ✅ Integration tests use mocked dependencies
- ✅ Test suite runs in <10 seconds (unit + integration)
- ✅ No flaky tests due to external dependencies

**Maintainability:**
- ✅ New tools can be added without touching dispatcher
- ✅ Tool metadata centralized in decorator
- ✅ Dependencies explicit and mockable
- ✅ Developer docs for adding new tools

**Performance:**
- ✅ Registry lookup: O(1) via dict
- ✅ No measurable latency regression
- ✅ Memory usage: <1MB for registry

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing functionality | High | Gradual migration with fallback, comprehensive tests |
| Import order issues with decorators | Medium | Use lazy registration at module import |
| Performance overhead from DI | Low | Benchmark shows O(1) dict lookup |
| Developer learning curve | Medium | Comprehensive docs and examples |
| Test coverage gaps | Medium | Require tests for each migrated tool |
| Circular dependencies | Low | Use protocols and lazy imports |

---

## References

- [FastAPI Dependencies Tutorial](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [Python Dependency Injection Guide - DataCamp](https://www.datacamp.com/tutorial/python-dependency-injection)
- [Dependency Injector Framework](https://python-dependency-injector.ets-labs.org/)
- [Mastering DI in FastAPI - Medium](https://medium.com/@azizmarzouki/mastering-dependency-injection-in-fastapi-clean-scalable-and-testable-apis-5f78099c3362)
- [Python DI Best Practices - TestDriven.io](https://testdriven.io/blog/python-dependency-injection/)

---

## Next Steps

1. **Review this plan** with team
2. **Phase 1:** Build registry infrastructure (Week 1)
3. **Phase 2:** Migrate PoC tools (Week 1-2)
4. **Phase 3:** Bulk migration (Week 2-3)
5. **Phase 4-5:** Cleanup and features (Week 3)

**Total timeline:** 2-3 weeks
**Total effort:** 12-16 hours
