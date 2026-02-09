"""Dependency injection container for FCP tools.

Provides a lightweight DI system for managing tool dependencies
and enabling easy testing with mocks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fcp.mcp.protocols import AIService, Database, HTTPClient


@dataclass
class DependencyContainer:
    """Container for managing tool dependencies.

    This container holds references to all services that tools depend on.
    During testing, you can override these with mocks.

    Example:
        # Production
        container = DependencyContainer(
            database=firestore_client,
            ai_service=gemini,
            http_client=httpx.AsyncClient(),
        )

        # Testing
        mock_db = AsyncMock(spec=Database)
        container = DependencyContainer(
            database=mock_db,
            ai_service=AsyncMock(spec=AIService),
            http_client=AsyncMock(spec=HTTPClient),
        )
    """

    database: Database
    ai_service: AIService
    http_client: HTTPClient

    def override_database(self, mock_db: Database) -> None:
        """Override database for testing.

        Args:
            mock_db: Mock database implementation
        """
        self.database = mock_db

    def override_ai_service(self, mock_ai: AIService) -> None:
        """Override AI service for testing.

        Args:
            mock_ai: Mock AI service implementation
        """
        self.ai_service = mock_ai

    def override_http_client(self, mock_http: HTTPClient) -> None:
        """Override HTTP client for testing.

        Args:
            mock_http: Mock HTTP client implementation
        """
        self.http_client = mock_http


class Depends:
    """Dependency marker for FastAPI-style dependency injection.

    This class marks a parameter as a dependency that should be injected
    by the dispatcher, rather than coming from MCP arguments.

    Example:
        async def add_meal(
            user_id: str,
            dish_name: str,
            db: Database = Depends(get_database),  # ← Injected
        ):
            ...
    """

    def __init__(self, provider: Any):
        """Initialize dependency marker.

        Args:
            provider: Function that provides the dependency
        """
        self.provider = provider


# Dependency providers
def get_database(container: DependencyContainer | None = None) -> Database:
    """Provide database dependency.

    Args:
        container: Optional container for testing

    Returns:
        Database instance (real or mock)
    """
    if container is not None:
        return container.database

    # Production: import and return real firestore client
    from typing import cast

    from fcp.services.firestore import firestore_client

    # Cast to protocol type - firestore_client implements Database protocol
    return cast(Database, firestore_client)


def get_ai_service(container: DependencyContainer | None = None) -> AIService:
    """Provide AI service dependency.

    Args:
        container: Optional container for testing

    Returns:
        AI service instance (real or mock)
    """
    if container is not None:
        return container.ai_service

    # Production: import and return real gemini client
    from typing import cast

    from fcp.services.gemini import gemini

    # Cast to protocol type - gemini implements AIService protocol
    return cast(AIService, gemini)


def get_http_client(container: DependencyContainer | None = None) -> HTTPClient:
    """Provide HTTP client dependency.

    Args:
        container: Optional container for testing

    Returns:
        HTTP client instance (real or mock)
    """
    if container is not None:
        return container.http_client

    # Production: create and return real HTTP client
    import httpx

    return httpx.AsyncClient(timeout=30.0)


# Helper to resolve dependencies from function signature
def resolve_dependencies(
    func: Any,
    container: DependencyContainer | None = None,
) -> dict[str, Any]:
    """Resolve dependencies for a function.

    Inspects the function's default values to find Depends() markers
    and resolves them using the provider functions.

    Args:
        func: Function to resolve dependencies for
        container: Optional container for testing

    Returns:
        Dict mapping parameter names to resolved dependency instances
    """
    from inspect import signature

    sig = signature(func)
    resolved = {}

    for param_name, param in sig.parameters.items():
        # Check if parameter has Depends() as default
        if isinstance(param.default, Depends):
            provider = param.default.provider
            resolved[param_name] = provider(container)

    return resolved
