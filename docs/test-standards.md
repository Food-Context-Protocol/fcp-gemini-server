# Test Standards

This repo follows Google-style test hygiene: small, deterministic, and hermetic by default.

## Defaults
- Unit tests are the default (`pytest` runs unit tests only).
- Network is blocked for HTTPX by default via `respx` mocks.
- Coverage is enforced at 100% for `src/`.
- Timeouts are enforced to prevent hangs.
- Every test must be tagged with a size marker (`small`, `medium`, or `large`).

## Markers
- `small`: default unit tests (fast, hermetic).
- `medium`: heavier unit tests or property-based tests.
- `large`: integration/e2e tests.
- `integration`: requires external services or emulators.
- `core`: backend-agnostic integration checks (sqlite-friendly).
- `gemini`: tests that require Gemini capabilities.
- `external`: tests that touch external providers (USDA/FDA/maps/places).

## Running Integration Tests
Run explicitly with markers:
```bash
RUN_INTEGRATION=1 DATABASE_BACKEND=sqlite uv run pytest tests/integration/ -m "core and integration"
```
Or use:
```bash
make test-integration-core
```

## Size Enforcement
Tests are auto-tagged by path and enforced at collection time:
- `tests/unit/` -> `small`
- `tests/unit/cli/property_based/` -> `medium`
- `tests/integration/` -> `large` + `integration`
- `tests/` (tests not under `unit/` or `integration/`) -> `small`

## Running Without Coverage
For speed during local iteration:
```bash
make test-quick
```
