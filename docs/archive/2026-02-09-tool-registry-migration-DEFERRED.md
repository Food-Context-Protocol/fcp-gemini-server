# Tool Registry Migration Plan (Phase 3)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate all 37 remaining legacy if/elif dispatch handlers in `mcp_tool_dispatch.py` to the `@tool()` registry pattern, then delete the legacy dispatch code.

**Architecture:** Each tool function gets a `@tool()` decorator. The existing registry dispatcher (lines 136-151) handles permission checks, user_id injection, and dependency resolution automatically. Functions that need pre-processing (log fetching, context injection) get thin wrapper functions. Since nothing has been released, return formats are standardized to raw function output (no dispatcher-level wrapping).

**Tech Stack:** Python 3.11+, `@tool()` decorator from `fcp.mcp.registry`, pytest + pytest-cov (100% branch coverage required)

---

## Summary of Changes

| Task | Action | Files |
|---|---|---|
| 1 | Enhance dispatcher for tools without user_id | `mcp_tool_dispatch.py`, `registry.py`, tests |
| 2 | Migrate 5 recipe tools | `tools/recipe_crud.py`, `mcp_tool_dispatch.py`, tests |
| 3 | Migrate 5 safety tools | `tools/safety.py`, `tools/taste_buddy.py`, `mcp_tool_dispatch.py`, tests |
| 4 | Migrate 4 inventory tools | `tools/inventory.py`, `mcp_tool_dispatch.py`, tests |
| 5 | Migrate 5 parsing/content tools | `tools/parser.py`, `tools/scaling.py`, `tools/standardize.py`, `tools/visual.py`, `mcp_tool_dispatch.py`, tests |
| 6 | Migrate 5 analytics tools | `tools/search.py`, `tools/suggest.py`, `tools/profile.py`, `tools/trends.py`, `mcp_tool_dispatch.py`, tests |
| 7 | Migrate 2 discovery + external tools | `tools/discovery.py`, `tools/external/open_food_facts.py`, `mcp_tool_dispatch.py`, tests |
| 8 | Migrate 4 business tools | `tools/civic.py`, `tools/cottage.py`, `tools/clinical.py`, `mcp_tool_dispatch.py`, tests |
| 9 | Migrate 3 connector + audio tools | `tools/connector.py`, `tools/voice.py`, `mcp_tool_dispatch.py`, tests |
| 10 | Migrate 2 publishing tools (pre-processing wrappers) | `tools/blog.py`, `tools/social.py`, `mcp_tool_dispatch.py`, tests |
| 11 | Migrate 2 special tools (agent + recipe extractor) | `tools/agents.py`, `tools/recipe_extractor.py`, `mcp_tool_dispatch.py`, tests |
| 12 | Clean up dispatch — remove all legacy code | `mcp_tool_dispatch.py`, `server.py` |
| 13 | Update integration tests | `tests/unit/api/test_server_mcp.py` |
| 14 | Final verification | Full suite |

---

## Architecture Decisions

### A. Return Value Standardization

**Decision:** Since nothing has been released, eliminate dispatcher-level result wrapping. Functions return their natural type; the registry serializes directly.

**Before (legacy):**
```python
# Dispatcher wraps:
result = await find_nearby_food(...)  # returns list
return _ok({"venues": result})         # wraps in dict
```

**After (registry):**
```python
@tool(name="dev.fcp.discovery.find_nearby_food", ...)
async def find_nearby_food(user_id: str, ...) -> list[dict]:
    ...  # returns list directly
# Registry does: return _ok(result)  # serializes list as-is
```

**7 tools affected** (currently wrapped by dispatcher):
- `find_nearby_food` → was `{venues: []}`, now `[]`
- `suggest_meal` → was `{suggestions: []}`, now `[]`
- `generate_image_prompt` → was `{prompt: str}`, now `str`
- `get_taste_profile` → was `{profile: {}}`, now `{}`
- `list_recipes` → was `{recipes: []}`, now `[]`
- `search_meals` → was `{results: []}`, now `[]`
- `get_recent_meals` → already unwrapped in registry

**Test impact:** Tests checking for `data["venues"]` etc. need updating to check raw format.

### B. Conditional user_id Injection

**Decision:** Modify dispatcher to only inject `user_id` if the handler accepts it. This supports tools like `extract_recipe_from_media` that are stateless.

**Change in dispatcher:**
```python
# Before:
call_args = {"user_id": user.user_id, **arguments}

# After:
import inspect
sig = inspect.signature(tool_metadata.handler)
call_args = dict(arguments)
if "user_id" in sig.parameters:
    call_args["user_id"] = user.user_id
```

### C. Pre-Processing Wrappers

**Decision:** Tools that need data fetching before execution (generate_blog_post, generate_social_post, delegate_to_food_agent) get `@tool()`-decorated wrapper functions that accept MCP args (e.g., `log_id`) and fetch data internally. The original functions remain unchanged for route callers.

```python
# Original (called by routes with pre-fetched data):
async def generate_blog_post(log_data: dict, style: str) -> dict: ...

# MCP wrapper (called by registry with log_id):
@tool(name="dev.fcp.publishing.generate_blog_post", ...)
async def generate_blog_post_mcp(user_id: str, log_id: str, style: str = "lifestyle") -> dict:
    log = await get_meal(user_id, log_id)
    if not log:
        return {"error": "Log not found"}
    return await generate_blog_post(log_data=log, style=style)
```

### D. Validation in Functions

**Decision:** Move dispatcher-level validation (required field checks, type coercion) into the function body or rely on the auto-generated JSON schema's `required` fields. The schema already marks non-optional params as required.

---

## Task 1: Enhance Dispatcher for Optional user_id

**Files:**
- Modify: `src/fcp/mcp_tool_dispatch.py:136-151`
- Modify: `src/fcp/mcp/registry.py` (add `inject_user_id` field to ToolMetadata)
- Test: `tests/unit/mcp/test_mcp_tool_dispatch.py`

**Step 1: Write the failing test**

```python
# tests/unit/mcp/test_mcp_tool_dispatch.py
@pytest.mark.asyncio
async def test_registry_tool_without_user_id():
    """Registry tools without user_id param should not receive it."""
    from fcp.mcp.registry import tool, tool_registry

    @tool(name="dev.fcp.test.no_user_id", description="Test tool")
    async def no_user_id_tool(input_text: str) -> dict:
        return {"echo": input_text}

    try:
        user = AuthenticatedUser(user_id="user-1", role=UserRole.AUTHENTICATED)
        result = await dispatch_tool_call("dev.fcp.test.no_user_id", {"input_text": "hello"}, user)
        assert result.status == "success"
        data = json.loads(result.contents[0].text)
        assert data["echo"] == "hello"
    finally:
        tool_registry._tools.pop("dev.fcp.test.no_user_id", None)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/mcp/test_mcp_tool_dispatch.py::test_registry_tool_without_user_id -v`
Expected: FAIL (TypeError: unexpected keyword argument 'user_id')

**Step 3: Implement — modify dispatcher**

In `src/fcp/mcp_tool_dispatch.py`, change registry dispatch block (around line 140):

```python
import inspect

# ...inside dispatch_tool_call, after tool_metadata check:
if tool_metadata:
    if tool_metadata.requires_write:
        if error := _check_write_permission(user, name):
            return error

    call_args = dict(arguments)
    sig = inspect.signature(tool_metadata.handler)
    if "user_id" in sig.parameters:
        call_args["user_id"] = user.user_id

    dependencies = resolve_dependencies(tool_metadata.handler, container=None)
    call_args.update(dependencies)

    result = await tool_metadata.handler(**call_args)
    return _ok(result)
```

Add `import inspect` at top of file.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/mcp/test_mcp_tool_dispatch.py::test_registry_tool_without_user_id -v`
Expected: PASS

**Step 5: Run full suite and commit**

```bash
pytest tests/unit -q
git add src/fcp/mcp_tool_dispatch.py tests/unit/mcp/test_mcp_tool_dispatch.py
git commit -m "feat: conditional user_id injection in registry dispatch"
```

---

## Task 2: Migrate 5 Recipe Tools

**Files:**
- Modify: `src/fcp/tools/recipe_crud.py` (add `@tool()` to 5 functions)
- Modify: `src/fcp/mcp_tool_dispatch.py` (delete 5 handlers)
- Test: `tests/unit/mcp/test_mcp_tool_dispatch.py`

**Tools to migrate:**

| Tool Name | Function | Write? | Special Logic |
|---|---|---|---|
| `dev.fcp.recipes.save` | `save_recipe` | YES | name/ingredients required validation |
| `dev.fcp.recipes.list` | `list_recipes` | NO | wraps result in `{recipes: []}` |
| `dev.fcp.recipes.archive` | `archive_recipe` | YES | recipe_id required |
| `dev.fcp.recipes.favorite` | `favorite_recipe` | YES | recipe_id required, bool coercion |
| `dev.fcp.recipes.delete` | `delete_recipe` | YES | recipe_id required |

**Step 1: Add @tool() decorators to recipe_crud.py**

Read `src/fcp/tools/recipe_crud.py` first to see current signatures. Add decorators following the pattern from `get_recipe` (already decorated). For each function:

```python
@tool(
    name="dev.fcp.recipes.save",
    description="Save a new recipe",
    category="recipes",
    requires_write=True,
    dependencies={"db"},
)
async def save_recipe(user_id: str, name: str, ingredients: list[str], ..., db: Database | None = None) -> dict:
```

**Important:** Ensure each function has `user_id: str` as first param and `db: Database | None = None` as dependency. Some may already have this. If a function takes `recipe_id` as required, it should NOT have a default value (the schema will mark it required).

**Step 2: Delete 5 legacy handlers from mcp_tool_dispatch.py**

Remove the `if name == "dev.fcp.recipes.archive"` through `if name == "dev.fcp.recipes.save"` blocks (including `.delete`, `.favorite`, `.list`).

Also remove unused imports: `archive_recipe`, `delete_recipe`, `favorite_recipe`, `list_recipes`, `save_recipe` from the import block.

**Step 3: Write tests for new registry paths**

For each tool, add a test that calls through `dispatch_tool_call` (which will now hit the registry). Mock the `db` dependency or the underlying Firestore calls.

**Step 4: Run and verify**

```bash
pytest tests/unit -q
pytest tests/unit --cov=src/fcp --cov-report=term-missing --cov-branch --no-cov-on-fail -q 2>&1 | grep -v "100%"
```

**Step 5: Commit**

```bash
git add src/fcp/tools/recipe_crud.py src/fcp/mcp_tool_dispatch.py tests/
git commit -m "feat: migrate 5 recipe tools to registry"
```

---

## Task 3: Migrate 5 Safety Tools

**Files:**
- Modify: `src/fcp/tools/safety.py` (add `@tool()` to 4 functions)
- Modify: `src/fcp/tools/taste_buddy.py` (add `@tool()` to 1 function)
- Modify: `src/fcp/mcp_tool_dispatch.py` (delete 5 handlers)
- Test: `tests/unit/mcp/test_mcp_tool_dispatch.py`

**Tools to migrate:**

| Tool Name | Function | File | Notes |
|---|---|---|---|
| `dev.fcp.safety.check_allergen_alerts` | `check_allergen_alerts` | safety.py | No user_id needed |
| `dev.fcp.safety.check_drug_food_interactions` | `check_drug_food_interactions` | safety.py | No user_id needed |
| `dev.fcp.safety.check_food_recalls` | `check_food_recalls` | safety.py | No user_id needed |
| `dev.fcp.safety.get_restaurant_safety_info` | `get_restaurant_safety_info` | safety.py | No user_id needed |
| `dev.fcp.safety.check_dietary_compatibility` | `check_dietary_compatibility` | taste_buddy.py | No user_id needed |

**Key:** These tools do NOT take `user_id`. Relies on Task 1's conditional injection.

**Pattern:**
```python
@tool(
    name="dev.fcp.safety.check_allergen_alerts",
    description="Check food for allergen alerts",
    category="safety",
)
async def check_allergen_alerts(food_name: str, allergens: list[str] | None = None) -> dict:
    ...
```

Follow same steps as Task 2: add decorators → delete handlers → test → commit.

---

## Task 4: Migrate 4 Inventory Tools

**Files:**
- Modify: `src/fcp/tools/inventory.py`
- Modify: `src/fcp/mcp_tool_dispatch.py`

**Tools:**

| Tool Name | Function | Write? | Notes |
|---|---|---|---|
| `dev.fcp.inventory.check_pantry_expiry` | `check_pantry_expiry` | NO | user_id only |
| `dev.fcp.inventory.delete_pantry_item` | `delete_pantry_item` | YES | item_id required |
| `dev.fcp.inventory.update_pantry_item` | `update_pantry_item` | YES | Complex field filtering — move into function |
| `dev.fcp.inventory.get_pantry_suggestions` | `suggest_recipe_from_pantry` | NO | |

**Special: update_pantry_item** — The dispatcher currently filters fields. Move this logic into the function:

```python
@tool(name="dev.fcp.inventory.update_pantry_item", requires_write=True, category="inventory")
async def update_pantry_item(
    user_id: str,
    item_id: str,
    name: str | None = None,
    quantity: int | None = None,
    unit: str | None = None,
    expiration_date: str | None = None,
) -> dict:
    updates = {k: v for k, v in {"name": name, "quantity": quantity, "unit": unit, "expiration_date": expiration_date}.items() if v is not None}
    if not updates:
        return {"error": "No valid updates provided"}
    ...
```

Follow same steps: decorators → delete handlers → test → commit.

---

## Task 5: Migrate 5 Parsing/Content Tools

**Tools:**

| Tool Name | Function | File |
|---|---|---|
| `dev.fcp.parsing.parse_menu` | `parse_menu` | parser.py |
| `dev.fcp.parsing.parse_receipt` | `parse_receipt` | parser.py |
| `dev.fcp.recipes.scale` | `scale_recipe` | scaling.py |
| `dev.fcp.recipes.standardize` | `standardize_recipe` | standardize.py |
| `dev.fcp.visual.generate_image_prompt` | `generate_image_prompt` | visual.py |

All simple, no special logic. `parse_menu` and `parse_receipt` have no `user_id`. `generate_image_prompt` has no `user_id`. Relies on Task 1.

Follow same steps: decorators → delete handlers → test → commit.

---

## Task 6: Migrate 5 Analytics Tools

**Tools:**

| Tool Name | Function | File | Notes |
|---|---|---|---|
| `dev.fcp.nutrition.search_meals` | `search_meals` | search.py | user_id positional |
| `dev.fcp.planning.get_meal_suggestions` | `suggest_meal` | suggest.py | Complex pre-processing (fetches profile + recent logs internally) |
| `dev.fcp.profile.get_taste_profile` | `get_taste_profile` | profile.py | user_id positional |
| `dev.fcp.trends.get_flavor_pairings` | `get_flavor_pairings` | trends.py | subject required (raises ValueError) |
| `dev.fcp.trends.identify_emerging_trends` | `identify_emerging_trends` | trends.py | |

`suggest_meal` already does its own pre-processing (fetches taste profile, recent logs). The dispatcher just passes args through. Simple migration.

`get_flavor_pairings` raises ValueError if subject is missing — this will become a 500 error without the dispatcher's early return. Move validation into function or let the schema's `required` handle it (subject has no default → it's required in schema → MCP rejects the call before dispatch).

Follow same steps: decorators → delete handlers → test → commit.

---

## Task 7: Migrate 2 Discovery + External Tools

**Tools:**

| Tool Name | Function | File | Notes |
|---|---|---|---|
| `dev.fcp.discovery.find_nearby_food` | `find_nearby_food` | discovery.py | Complex validation: (lat+lon) OR location |
| `dev.fcp.external.lookup_product` | `lookup_product` | external/open_food_facts.py | No user_id |

**Special: find_nearby_food** — Move validation into function body:

```python
@tool(name="dev.fcp.discovery.find_nearby_food", category="discovery")
async def find_nearby_food(
    latitude: float | None = None,
    longitude: float | None = None,
    radius: float = 2000.0,
    food_type: str = "restaurant",
    location: str | None = None,
) -> list[dict]:
    if not ((latitude is not None and longitude is not None) or location):
        raise ValueError("Either (latitude, longitude) or location must be provided")
    ...
```

Note: No `user_id` param needed — relies on Task 1.

Follow same steps: decorators → delete handlers → test → commit.

---

## Task 8: Migrate 4 Business Tools

**Tools:**

| Tool Name | Function | File |
|---|---|---|
| `dev.fcp.business.detect_economic_gaps` | `detect_economic_gaps` | civic.py |
| `dev.fcp.business.plan_food_festival` | `plan_food_festival` | civic.py |
| `dev.fcp.business.generate_cottage_label` | `generate_cottage_label` | cottage.py |
| `dev.fcp.clinical.generate_dietitian_report` | `generate_dietitian_report` | clinical.py |

No user_id on detect_economic_gaps, plan_food_festival, generate_cottage_label. `generate_dietitian_report` has user_id.

Follow same steps: decorators → delete handlers → test → commit.

---

## Task 9: Migrate 3 Connector + Audio Tools

**Tools:**

| Tool Name | Function | File | Write? |
|---|---|---|---|
| `dev.fcp.connectors.sync_to_calendar` | `sync_to_calendar` | connector.py | YES |
| `dev.fcp.connectors.save_to_drive` | `save_to_drive` | connector.py | YES |
| `dev.fcp.nutrition.log_meal_from_audio` | `log_meal_from_audio` | voice.py | YES |

`sync_to_calendar` and `save_to_drive` have dispatcher validation (required fields). Move into function or let schema enforce (required params without defaults).

Follow same steps: decorators → delete handlers → test → commit.

---

## Task 10: Migrate 2 Publishing Tools (Pre-Processing Wrappers)

**Files:**
- Modify: `src/fcp/tools/blog.py` (or where `generate_blog_post` lives)
- Modify: `src/fcp/tools/social.py` (or where `generate_social_post` lives)
- Modify: `src/fcp/mcp_tool_dispatch.py`

**Tools:**

| Tool Name | Function | Notes |
|---|---|---|
| `dev.fcp.publishing.generate_blog_post` | `generate_blog_post` | Dispatcher fetches log by log_id |
| `dev.fcp.publishing.generate_social_post` | `generate_social_post` | Dispatcher fetches log by log_id |

**Pattern:** Create `@tool()`-decorated wrapper in the same file:

```python
# Existing function (routes call with pre-fetched data):
async def generate_blog_post(log_data: dict, style: str = "lifestyle") -> dict:
    ...

# MCP tool wrapper (registry calls with log_id):
@tool(
    name="dev.fcp.publishing.generate_blog_post",
    description="Generate a blog post from a food log",
    category="publishing",
)
async def generate_blog_post_tool(user_id: str, log_id: str, style: str = "lifestyle") -> dict:
    from fcp.tools import get_meal
    log = await get_meal(user_id, log_id)
    if not log:
        return {"error": "Log not found"}
    return await generate_blog_post(log_data=log, style=style)
```

Same pattern for `generate_social_post_tool` (also maps `tone` arg to `style` param).

Follow same steps: add wrappers → delete handlers → test → commit.

---

## Task 11: Migrate 2 Special Tools

### 11a. delegate_to_food_agent (Pre-Processing Wrapper)

**File:** `src/fcp/tools/agents.py`

Dispatcher fetches user preferences before calling. Create wrapper:

```python
@tool(
    name="dev.fcp.agents.delegate_to_food_agent",
    description="Delegate a task to a specialized food agent",
    category="agents",
)
async def delegate_to_food_agent_tool(user_id: str, agent_name: str, objective: str) -> dict:
    from fcp.services.firestore import firestore_client
    context = await firestore_client.get_user_preferences(user_id)
    return await delegate_to_food_agent(
        agent_name=agent_name, objective=objective, user_context=context
    )
```

### 11b. extract_recipe_from_media (No user_id, Non-Standard Name)

**File:** `src/fcp/tools/recipe_extractor.py`

**Current name:** `"extract_recipe_from_media"` (no `dev.fcp.` prefix)

**Decision:** Rename to `"dev.fcp.media.extract_recipe"` for consistency. Since nothing is released, there's no backward compat concern.

```python
@tool(
    name="dev.fcp.media.extract_recipe",
    description="Extract a recipe from an image or video",
    category="media",
)
async def extract_recipe_from_media(
    image_url: str | None = None,
    media_url: str | None = None,
    additional_notes: str | None = None,
) -> dict:
    ...
```

No `user_id` param — relies on Task 1's conditional injection.

### 11c. donate_meal

**File:** `src/fcp/tools/civic.py` (or wherever `donate_meal` lives)

```python
@tool(
    name="dev.fcp.business.donate_meal",
    description="Donate a meal to a food bank",
    category="business",
    requires_write=True,
)
async def donate_meal(log_id: str, organization: str = "Local Food Bank") -> dict:
    ...
```

Note: No `user_id` needed (function doesn't use it). Check current signature.

Follow same steps: add decorators/wrappers → delete handlers → test → commit.

---

## Task 12: Clean Up Dispatch File

**File:** `src/fcp/mcp_tool_dispatch.py`

After all tools are migrated, the entire legacy if/elif block (lines ~150-593) should be empty. Remove:

1. All remaining `if name ==` blocks (should be 0 if Tasks 2-11 complete)
2. The `_call()` helper function
3. The `_call_sync()` helper function
4. The `_resolve_handler()` helper function
5. All unused imports from `fcp.tools import (...)` block
6. The `from fcp.tools.external.open_food_facts import lookup_product` import
7. The `from fcp.tools.safety import (...)` import block

**Also clean up `src/fcp/server.py`:**
- Remove the legacy `get_recent_meals` handler (lines ~179-191) that duplicates the registry version
- Remove unused re-exports in the `from fcp.tools import (...)` block

**Keep:**
- `_ok()` helper (still used by registry path)
- `_error()` helper (still used)
- `_check_write_permission()` (still used by registry path)
- `dispatch_tool_call()` function (now just the registry path + unknown tool fallback)

The dispatch function should reduce to roughly:

```python
async def dispatch_tool_call(name, arguments, user):
    try:
        tool_metadata = tool_registry.get(name)
        if tool_metadata:
            # Permission check, arg injection, call handler
            ...
            return _ok(result)

        return _error(f"Unknown tool: {name}")
    except Exception as e:
        return _error(str(e))
```

**Step: Run tests, fix any import errors, commit.**

```bash
pytest tests/unit -q
git add src/fcp/mcp_tool_dispatch.py src/fcp/server.py
git commit -m "refactor: remove all legacy dispatch handlers"
```

---

## Task 13: Update Integration Tests

**File:** `tests/unit/api/test_server_mcp.py`

The 15 previously-unskipped tests call tools through `server.call_tool()` → `dispatch_tool_call()`. After migration:

1. Tools now go through registry path (not legacy)
2. Return format may differ (no wrapper dicts)
3. Patch targets change from `fcp.server.<func>` to `fcp.tools.<module>.<func>` or mock the `db` dependency

**For each test:**
1. Update patch targets to match new code paths
2. Update assertions for return format changes (no `{venues: ...}` wrappers)
3. Verify all 89 tests in file still pass

```bash
pytest tests/unit/api/test_server_mcp.py -v --no-header -q
```

---

## Task 14: Final Verification

```bash
# Full test suite with coverage
pytest tests/unit --cov=src/fcp --cov-report=term-missing --cov-branch -q

# Verify 100% coverage
# Verify 0 legacy handlers remain
grep -c "if name == " src/fcp/mcp_tool_dispatch.py  # Expected: 0

# Verify all tools registered
python -c "from fcp.mcp.registry import tool_registry; print(f'{len(tool_registry.list_tools())} tools registered')"

# Check file size reduction
wc -l src/fcp/mcp_tool_dispatch.py  # Should be ~50 lines (was ~600+)
```

Expected: 100% coverage, 0 legacy handlers, ~42 tools registered, dispatch file reduced by ~550 lines.

---

## Migration Checklist Per Tool

For every tool migration, verify:

- [ ] `@tool()` decorator with correct `name`, `description`, `category`, `requires_write`
- [ ] Function has `user_id: str` if it needs it (omit if stateless)
- [ ] Function has `db: Database | None = None` if it uses Firestore (add to `dependencies={"db"}`)
- [ ] Required params have no default value (schema marks them required)
- [ ] Optional params have default values (`None`, `""`, `[]`, etc.)
- [ ] Dispatcher validation moved into function body (if any)
- [ ] Legacy handler deleted from `mcp_tool_dispatch.py`
- [ ] Unused import removed from `mcp_tool_dispatch.py`
- [ ] Tests pass: `pytest tests/unit -q`
- [ ] Coverage maintained: no new uncovered lines
