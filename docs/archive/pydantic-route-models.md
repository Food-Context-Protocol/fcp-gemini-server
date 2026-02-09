# Pydantic Route Models

## Purpose
Every MCP route should expose a Pydantic request and response schema so that we have strong typing, validated inputs, and predictable outputs. The centralized `src/fcp/routes/schemas.py` file houses the shared response models (`NearbyFoodResponse`, `ImageAnalysisResponse`, `MealListResponse`, etc.) that are reused across multiple routers.

## Guidelines
- **Response contracts**: Annotate each route with `response_model=` and return the corresponding Pydantic object rather than bare dictionaries. This keeps upstream clients, API docs, and coverage aligned.
- **Schema updates**: When adding new endpoints or changing payloads, update `schemas.py` first and add any new unit tests under `tests/unit/routes/test_routes_schemas.py` so coverage continues to enforce the contract.
- **Error handling**: The schema should reflect the successful shape only; raise `HTTPException` for failure cases so the response modeling remains simple.
- **Coverage**: Every route change triggers `uv run pytest tests/unit/ --maxfail=1 -q --ignore=tests/integration/` with 100% coverage, so make sure new models are fully exercised by the unit tests.

## Current coverage
| Module | Response Model |
| --- | --- |
| `/discovery/nearby` | `NearbyFoodResponse` |
| `/analyze` family | `ImageAnalysisResponse` |
| `/meals` CRUD | `MealListResponse`, `MealDetailResponse`, `ActionResponse` |
| `/health` probes | `StatusResponse`, `ReadinessResponse`, `DependencyHealthResponse` |
| `/search` | `SearchResponse` |
| `/publish` (generation/drafts/publishing) | `DraftCreationResponse`, `DraftListResponse`, `DraftDetailResponse`, `ActionResponse`, `PublishActionResponse`, `PublishedListResponse`, `AnalyticsResponse` |

Follow this pattern for every future route so documentation, coverage enforcement, and the runtime experience stay consistent.
