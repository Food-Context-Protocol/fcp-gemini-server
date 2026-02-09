"""Shared request/response schemas for route modules.

This module contains Pydantic models that are used across multiple route modules.
Keeping them here avoids circular imports between route modules.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator

from fcp.security.url_validator import ImageURLError, validate_image_url


class ImageURLRequest(BaseModel):
    """Request model for endpoints that accept an image URL."""

    image_url: str = Field(..., min_length=1, max_length=2000)

    @field_validator("image_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        try:
            return validate_image_url(v)
        except (ImageURLError, Exception) as e:
            raise ValueError(str(e)) from e


class AnyResponse(RootModel[Any]):
    """Permissive response model used as a default for route responses."""


class Coordinates(BaseModel):
    """Latitude/longitude pair used across multiple responses."""

    latitude: float
    longitude: float


class NearbyFoodResponse(BaseModel):
    """Response returned by the discovery/nearby endpoint."""

    venues: list[dict[str, Any]]
    resolved_location: str | None = None
    coordinates: Coordinates | None = None
    error: str | None = None
    message: str | None = None


class ImageAnalysisResponse(BaseModel):
    """Structured response used by `/analyze` endpoints."""

    analysis: dict[str, Any]
    version: str | None = None
    method: str | None = None
    thinking_level: str | None = None


class MealLog(BaseModel):
    """Common structure for a food log entry returned by the meals routes."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    log_id: str | None = Field(default=None, alias="id")
    dish_name: str | None = None
    venue_name: str | None = None
    notes: str | None = None
    rating: int | None = None
    tags: list[str] | None = None
    public: bool | None = None
    processing_status: str | None = None
    image_path: str | None = None
    image_url: str | None = None
    analysis: dict[str, Any] | None = Field(default=None)
    nutrition: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None


class MealListResponse(BaseModel):
    """Response for listing meals."""

    meals: list[MealLog]
    count: int


class MealDetailResponse(BaseModel):
    """Response for fetching a single meal."""

    meal: MealLog


class ActionResponse(BaseModel):
    """Generic response for create/update/delete operations."""

    success: bool
    log_id: str | None = None
    dish_name: str | None = None
    updated_fields: list[str] | None = None
    analysis: dict[str, Any] | None = None
    image_url: str | None = None
    storage_note: str | None = None
    message: str | None = None
    error: str | None = None

    model_config = ConfigDict(extra="allow")

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        data = super().model_dump(*args, **kwargs)
        if data.get("storage_note") is None:
            data.pop("storage_note", None)
        return data


class DraftCreationResponse(BaseModel):
    """Response returned by draft generation."""

    draft_id: str
    content_type: str

    model_config = ConfigDict(extra="allow")


class DraftListResponse(BaseModel):
    """Response for listing drafts."""

    drafts: list[dict[str, Any]]
    count: int


class DraftDetailResponse(BaseModel):
    """Detailed draft payload."""

    draft_id: str
    content: dict[str, Any] | None = None
    status: str | None = None
    content_type: str | None = None
    source_log_ids: list[str] | None = None
    publish_results: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class PublishActionResponse(ActionResponse):
    """Response for publishing operations that includes external metadata."""

    results: dict[str, Any] | None = None
    external_urls: dict[str, str] | None = None
    published_id: str | None = None


class PublishedListResponse(BaseModel):
    """Response for listing published content."""

    published: list[dict[str, Any]]
    count: int


class AnalyticsResponse(ActionResponse):
    """Response payload for analytics endpoint."""

    analytics: dict[str, Any] | None = None


class SearchResponse(BaseModel):
    """Response returned by the search endpoint."""

    results: list[dict[str, Any]]
    query: str


class StatusResponse(BaseModel):
    """Basic status payload shared by health endpoints."""

    status: str


class ReadinessResponse(StatusResponse):
    """Readiness endpoint response with component checks."""

    checks: dict[str, bool]


class DependencyHealthResponse(StatusResponse):
    """Dependency health response with detailed checks."""

    checks: dict[str, Any]
    request_id: str
