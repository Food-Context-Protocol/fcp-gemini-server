# Coverage Analysis - What's Excluded and Why

**Current Coverage:** 94.90% (with exclusions)
**Target:** 100% (test everything possible)

---

## Currently Excluded Files

### ✅ Correctly Excluded (No Action Needed)

#### 1. `src/fcp/mcp/protocols.py` - Protocol Interfaces
**Why Excluded:** Pure interface definitions using `Protocol` - no executable code
```python
@runtime_checkable
class Database(Protocol):
    async def get_user_logs(...) -> list[dict[str, Any]]:
        ...  # Just interface definition
```
**Action:** Keep excluded ✅

#### 2. `src/fcp/client/*` - Generated SDK Code
**Why Excluded:** Auto-generated client SDK code (Fern)
**Action:** Keep excluded ✅

---

### ❌ Should Be Tested (Fix Required)

#### 3. `src/fcp/services/gemini_generation.py` (~150 lines)
**Current State:** Excluded with comment "needs mocking"
**Why It Can Be Tested:**
- Uses dependency injection (`self._require_client()`)
- All methods can be mocked with proper fixtures

**Solution:**
```python
# tests/unit/services/test_gemini_generation.py
@pytest.fixture
def mock_gemini_client():
    mock = AsyncMock()
    mock.aio.models.generate_content.return_value = MockResponse(text="result")
    return mock

async def test_generate_content(mock_gemini_client):
    mixin = GeminiGenerationMixin()
    mixin._require_client = lambda: mock_gemini_client
    result = await mixin.generate_content("test prompt")
    assert result == "result"
```

**Priority:** HIGH - Core functionality
**Effort:** 2-3 hours
**Coverage Gain:** ~150 lines

---

#### 4. `src/fcp/services/gemini_helpers.py` (~100 lines)
**Current State:** Excluded
**Why It Can Be Tested:**
- Pure utility functions (`_log_token_usage`, `_parse_json_response`, `gemini_retry`)
- No external dependencies

**Solution:**
```python
def test_parse_json_response():
    response = MockResponse(text='{"key": "value"}')
    result = _parse_json_response(response)
    assert result == {"key": "value"}

def test_log_token_usage(caplog):
    response = MockResponse(usage_metadata={"input_tokens": 10})
    _log_token_usage(response, "test_operation")
    assert "input_tokens=10" in caplog.text
```

**Priority:** MEDIUM - Utility functions
**Effort:** 1-2 hours
**Coverage Gain:** ~100 lines

---

#### 5. `src/fcp/scheduler/jobs.py` (~200 lines)
**Current State:** Excluded
**Why It Can Be Tested:**
- Uses APScheduler (mockable)
- Firestore operations (already have mocks)

**Solution:**
```python
@pytest.fixture
def mock_scheduler():
    return AsyncMock(spec=AsyncIOScheduler)

def test_start_scheduler(mock_scheduler, monkeypatch):
    monkeypatch.setattr("fcp.scheduler.jobs.AsyncIOScheduler", lambda: mock_scheduler)
    scheduler = start_scheduler()
    mock_scheduler.start.assert_called_once()

async def test_get_active_users(mock_firestore):
    users = await get_active_users()
    mock_firestore.get_active_users.assert_called_once_with(days=7)
```

**Priority:** LOW - Optional scheduler feature
**Effort:** 2-3 hours
**Coverage Gain:** ~200 lines

---

#### 6. `src/fcp/services/cloud_storage_backend.py` (~150 lines)
**Current State:** Excluded - "Production-only GCS code requiring google-cloud-storage"
**Why It Can Be Tested:**
- Same pattern as firestore_backend.py
- Mock google-cloud-storage client

**Solution:**
```python
@pytest.fixture
def mock_gcs_client():
    mock = AsyncMock()
    mock.bucket.return_value.blob.return_value.upload_from_string = AsyncMock()
    return mock

async def test_upload_image(mock_gcs_client, monkeypatch):
    backend = CloudStorageBackend()
    monkeypatch.setattr(backend, "_client", mock_gcs_client)
    await backend.upload_image(user_id="u1", image_data=b"data")
    mock_gcs_client.bucket().blob().upload_from_string.assert_called_once()
```

**Priority:** MEDIUM - Production storage
**Effort:** 2-3 hours
**Coverage Gain:** ~150 lines

---

#### 7. `src/fcp/services/firestore_backend.py` (812 lines)
**Current State:** Excluded - "Pre-existing 90 test failures - needs fixture refactor"
**Root Cause:** Tests exist but fail due to missing `google-cloud-firestore` dependency
**Why It Can Be Tested:**
- Install optional dependency: `uv sync --extra firestore`
- OR: Fix mock fixtures to properly simulate Firestore async queries

**Solution A (Recommended):** Fix mock fixtures
```python
class MockAsyncQuery:
    def __init__(self, docs):
        self._docs = docs
        self._filters = []

    def where(self, field, op, value):
        # Actually filter the docs
        filtered = [d for d in self._docs if d.get(field) == value]
        return MockAsyncQuery(filtered)

    async def stream(self):
        for doc in self._docs:
            yield doc
```

**Solution B:** Install firestore and test against real local emulator
```bash
gcloud emulators firestore start
export FIRESTORE_EMULATOR_HOST=localhost:8080
pytest tests/unit/services/test_firestore_backend.py
```

**Priority:** HIGH - Core production backend
**Effort:** 4-6 hours (fixture refactor)
**Coverage Gain:** ~812 lines

---

## Dependency Injection Assessment

### Current DI Pattern: ✅ Good Foundation

**Tools use dependency injection:**
```python
@tool(dependencies={"db"})
async def add_meal(user_id: str, dish_name: str, db: Database | None = None):
    db = db or firestore_client  # Fallback for non-DI calls
    await db.create_log(user_id, data)
```

**Problems:**
1. **Fallback pattern breaks pure DI** - `db or firestore_client` creates tight coupling
2. **Not consistently applied** - Some tools use DI, some don't
3. **Global singletons** - `firestore_client`, `gemini_client` are global

---

### Improved DI Pattern (Recommendation)

#### Option A: Pure Constructor Injection (Strict)
```python
class MealTools:
    def __init__(self, db: Database):
        self._db = db

    async def add_meal(self, user_id: str, dish_name: str):
        await self._db.create_log(user_id, data)

# In production:
meal_tools = MealTools(db=firestore_client)

# In tests:
meal_tools = MealTools(db=mock_db)
```

**Pros:** Testable, explicit dependencies, no globals
**Cons:** Breaks current `@tool()` decorator pattern

---

#### Option B: Improve Current Fallback Pattern (Pragmatic)
```python
@tool(dependencies={"db"})
async def add_meal(user_id: str, dish_name: str, db: Database | None = None):
    if db is None:
        raise ValueError("Database dependency required")
    await db.create_log(user_id, data)

# Container provides db automatically via DI
# Tests must explicitly provide mock
```

**Pros:** Keeps `@tool()` pattern, forces explicit DI in tests
**Cons:** Runtime error instead of type error

---

#### Option C: Factory Pattern (Current + Type-Safe)
```python
from fcp.mcp.container import get_dependency

@tool(dependencies={"db"})
async def add_meal(user_id: str, dish_name: str, db: Database | None = None):
    db = db or get_dependency(Database)  # Type-safe lookup
    await db.create_log(user_id, data)
```

**Pros:** Keeps current pattern, type-safe, testable
**Cons:** Still uses fallback (but cleaner)

---

## Action Plan to Reach 100% Coverage

### Phase 1: Low-Hanging Fruit (4-6 hours)

| File | Lines | Priority | Effort | Action |
|------|-------|----------|--------|--------|
| gemini_helpers.py | 100 | MEDIUM | 1-2h | Add unit tests with mocked responses |
| gemini_generation.py | 150 | HIGH | 2-3h | Add tests with AsyncMock Gemini client |
| cloud_storage_backend.py | 150 | MEDIUM | 2-3h | Add tests with mocked GCS client |

**Estimated Coverage Gain:** ~400 lines (+4-5%)

---

### Phase 2: Firestore Backend Fix (4-6 hours)

**Approach:** Fix mock fixtures instead of installing dependency
```python
# Create proper async query mocks
class AsyncQueryBuilder:
    def __init__(self, collection_data):
        self._data = collection_data
        self._where_clauses = []
        self._order_by_clause = None
        self._limit_value = None

    def where(self, field, op, value):
        self._where_clauses.append((field, op, value))
        return self

    def order_by(self, field, direction="ASCENDING"):
        self._order_by_clause = (field, direction)
        return self

    def limit(self, n):
        self._limit_value = n
        return self

    async def stream(self):
        # Apply filters, ordering, limit
        filtered = self._apply_filters(self._data)
        if self._order_by_clause:
            filtered = self._apply_ordering(filtered)
        if self._limit_value:
            filtered = filtered[:self._limit_value]

        for doc in filtered:
            yield doc
```

**Estimated Coverage Gain:** ~812 lines (+9%)

---

### Phase 3: Scheduler (Optional, 2-3 hours)

**Only if scheduler is production-critical**
- Mock APScheduler
- Test job registration and execution
- Verify cron triggers

**Estimated Coverage Gain:** ~200 lines (+2%)

---

## Total Potential Coverage

| Current | After Phase 1 | After Phase 2 | After Phase 3 |
|---------|---------------|---------------|---------------|
| 94.90% | ~99% | ~99.5% | ~100% |
| 8,200 tested | +400 lines | +812 lines | +200 lines |

**Total Untested:** ~1,400 lines
**Testable:** ~1,200 lines (86%)
**Legitimately Excluded:** ~200 lines (protocols + client SDK)

---

## Recommendation

**Immediate:** Execute Phase 1 (gemini helpers + generation + cloud storage)
- High value, low effort
- Tests core functionality
- Gain ~4-5% coverage

**Next Sprint:** Fix firestore backend mocks (Phase 2)
- Highest coverage gain
- Unblocks 90 existing tests
- Critical production code

**Defer:** Scheduler tests (Phase 3)
- Low priority if scheduler is optional
- Can wait until scheduler becomes critical

---

## Dependency Injection Improvements

**Recommended Approach:** Option C (Factory Pattern)
1. Keep current `@tool()` decorator pattern
2. Replace `db or firestore_client` with `db or get_dependency(Database)`
3. Make `get_dependency()` mockable in tests
4. Maintain backward compatibility

**Implementation:**
```python
# fcp/mcp/container.py
_test_overrides: dict[type, Any] = {}

def get_dependency(protocol: type[T]) -> T:
    """Get dependency from container (mockable in tests)."""
    if protocol in _test_overrides:
        return _test_overrides[protocol]

    if protocol == Database:
        return firestore_client
    raise ValueError(f"Unknown dependency: {protocol}")

def set_test_override(protocol: type, implementation: Any):
    """Override dependency for testing."""
    _test_overrides[protocol] = implementation

def clear_test_overrides():
    """Clear all test overrides."""
    _test_overrides.clear()
```

**Usage in tests:**
```python
@pytest.fixture
def mock_db():
    mock = AsyncMock(spec=Database)
    set_test_override(Database, mock)
    yield mock
    clear_test_overrides()
```

---

**Next Steps:**
1. ✅ Create this analysis document (done)
2. ⏭️ Implement Phase 1 tests (gemini helpers)
3. ⏭️ Refactor firestore mock fixtures
4. ⏭️ Consider DI factory pattern improvement
