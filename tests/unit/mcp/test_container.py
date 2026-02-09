"""Unit tests for dependency injection container."""

from unittest.mock import AsyncMock, Mock

import pytest

from fcp.mcp.container import (
    DependencyContainer,
    Depends,
    get_ai_service,
    get_database,
    get_http_client,
    resolve_dependencies,
)
from fcp.mcp.protocols import AIService, Database, HTTPClient


class TestDependencyContainer:
    """Test DependencyContainer class."""

    def test_create_container(self):
        """Test creating a dependency container."""
        mock_db = Mock(spec=Database)
        mock_ai = Mock(spec=AIService)
        mock_http = Mock(spec=HTTPClient)

        container = DependencyContainer(
            database=mock_db,
            ai_service=mock_ai,
            http_client=mock_http,
        )

        assert container.database == mock_db
        assert container.ai_service == mock_ai
        assert container.http_client == mock_http

    def test_override_database(self):
        """Test overriding database dependency."""
        original_db = Mock(spec=Database)
        new_db = Mock(spec=Database)

        container = DependencyContainer(
            database=original_db,
            ai_service=Mock(spec=AIService),
            http_client=Mock(spec=HTTPClient),
        )

        container.override_database(new_db)
        assert container.database == new_db

    def test_override_ai_service(self):
        """Test overriding AI service dependency."""
        original_ai = Mock(spec=AIService)
        new_ai = Mock(spec=AIService)

        container = DependencyContainer(
            database=Mock(spec=Database),
            ai_service=original_ai,
            http_client=Mock(spec=HTTPClient),
        )

        container.override_ai_service(new_ai)
        assert container.ai_service == new_ai

    def test_override_http_client(self):
        """Test overriding HTTP client dependency."""
        original_http = Mock(spec=HTTPClient)
        new_http = Mock(spec=HTTPClient)

        container = DependencyContainer(
            database=Mock(spec=Database),
            ai_service=Mock(spec=AIService),
            http_client=original_http,
        )

        container.override_http_client(new_http)
        assert container.http_client == new_http


class TestDepends:
    """Test Depends dependency marker."""

    def test_create_depends(self):
        """Test creating a Depends marker."""

        def provider():
            return "value"

        depends = Depends(provider)
        assert depends.provider == provider

    def test_depends_stores_provider_function(self):
        """Test that Depends stores the provider function."""

        def my_provider():
            return Mock(spec=Database)

        marker = Depends(my_provider)
        assert callable(marker.provider)
        assert marker.provider == my_provider


class TestDependencyProviders:
    """Test dependency provider functions."""

    def test_get_database_with_container(self):
        """Test get_database with container returns mock."""
        mock_db = Mock(spec=Database)
        container = DependencyContainer(
            database=mock_db,
            ai_service=Mock(spec=AIService),
            http_client=Mock(spec=HTTPClient),
        )

        result = get_database(container)
        assert result == mock_db

    def test_get_database_without_container(self):
        """Test get_database without container returns real client."""
        # This will import the real firestore_client
        result = get_database(None)
        assert result is not None
        # We can't easily test the type without circular imports,
        # but we can verify it's not None

    def test_get_ai_service_with_container(self):
        """Test get_ai_service with container returns mock."""
        mock_ai = Mock(spec=AIService)
        container = DependencyContainer(
            database=Mock(spec=Database),
            ai_service=mock_ai,
            http_client=Mock(spec=HTTPClient),
        )

        result = get_ai_service(container)
        assert result == mock_ai

    def test_get_ai_service_without_container(self):
        """Test get_ai_service without container returns real client."""
        result = get_ai_service(None)
        assert result is not None

    def test_get_http_client_with_container(self):
        """Test get_http_client with container returns mock."""
        mock_http = Mock(spec=HTTPClient)
        container = DependencyContainer(
            database=Mock(spec=Database),
            ai_service=Mock(spec=AIService),
            http_client=mock_http,
        )

        result = get_http_client(container)
        assert result == mock_http

    def test_get_http_client_without_container(self):
        """Test get_http_client without container returns real client."""
        result = get_http_client(None)
        assert result is not None
        # Should be an httpx.AsyncClient
        assert hasattr(result, "get")
        assert hasattr(result, "post")


class TestResolveDependencies:
    """Test resolve_dependencies helper."""

    def test_resolve_no_dependencies(self):
        """Test resolving function with no dependencies."""

        async def handler(name: str, age: int):
            pass

        resolved = resolve_dependencies(handler, None)
        assert resolved == {}

    def test_resolve_single_dependency(self):
        """Test resolving function with one dependency."""
        mock_db = Mock(spec=Database)
        container = DependencyContainer(
            database=mock_db,
            ai_service=Mock(spec=AIService),
            http_client=Mock(spec=HTTPClient),
        )

        async def handler(name: str, db=Depends(get_database)):
            pass

        resolved = resolve_dependencies(handler, container)
        assert "db" in resolved
        assert resolved["db"] == mock_db

    def test_resolve_multiple_dependencies(self):
        """Test resolving function with multiple dependencies."""
        mock_db = Mock(spec=Database)
        mock_ai = Mock(spec=AIService)
        container = DependencyContainer(
            database=mock_db,
            ai_service=mock_ai,
            http_client=Mock(spec=HTTPClient),
        )

        async def handler(
            name: str,
            db=Depends(get_database),
            ai=Depends(get_ai_service),
        ):
            pass

        resolved = resolve_dependencies(handler, container)
        assert "db" in resolved
        assert "ai" in resolved
        assert resolved["db"] == mock_db
        assert resolved["ai"] == mock_ai

    def test_resolve_mixed_parameters(self):
        """Test resolving function with both dependencies and regular params."""
        mock_db = Mock(spec=Database)
        container = DependencyContainer(
            database=mock_db,
            ai_service=Mock(spec=AIService),
            http_client=Mock(spec=HTTPClient),
        )

        async def handler(
            name: str,
            age: int = 25,
            active: bool = True,
            db=Depends(get_database),
        ):
            pass

        resolved = resolve_dependencies(handler, container)

        # Only dependency should be resolved
        assert len(resolved) == 1
        assert "db" in resolved
        assert resolved["db"] == mock_db


class TestDependencyInjectionPattern:
    """Test end-to-end dependency injection pattern."""

    @pytest.mark.asyncio
    async def test_inject_mock_database(self):
        """Test injecting mock database into a function."""
        # Setup mock
        mock_db = AsyncMock(spec=Database)
        mock_db.create_log.return_value = "log_123"

        container = DependencyContainer(
            database=mock_db,
            ai_service=AsyncMock(spec=AIService),
            http_client=AsyncMock(spec=HTTPClient),
        )

        # Function with DI
        async def add_meal(user_id: str, dish_name: str, db=Depends(get_database)):
            log_id = await db.create_log(user_id, {"dish_name": dish_name})
            return {"success": True, "log_id": log_id}

        # Resolve and inject dependencies
        deps = resolve_dependencies(add_meal, container)
        result = await add_meal(user_id="user_456", dish_name="Test", **deps)

        # Assertions
        assert result == {"success": True, "log_id": "log_123"}
        mock_db.create_log.assert_called_once_with("user_456", {"dish_name": "Test"})

    @pytest.mark.asyncio
    async def test_inject_mock_ai_service(self):
        """Test injecting mock AI service into a function."""
        # Setup mock
        mock_ai = AsyncMock(spec=AIService)
        mock_ai.generate_json.return_value = {"result": "generated"}

        container = DependencyContainer(
            database=AsyncMock(spec=Database),
            ai_service=mock_ai,
            http_client=AsyncMock(spec=HTTPClient),
        )

        # Function with DI
        async def analyze(prompt: str, ai=Depends(get_ai_service)):
            result = await ai.generate_json(prompt)
            return result

        # Resolve and inject
        deps = resolve_dependencies(analyze, container)
        result = await analyze(prompt="Test prompt", **deps)

        # Assertions
        assert result == {"result": "generated"}
        mock_ai.generate_json.assert_called_once_with("Test prompt")

    @pytest.mark.asyncio
    async def test_inject_multiple_dependencies(self):
        """Test injecting multiple dependencies into a function."""
        # Setup mocks
        mock_db = AsyncMock(spec=Database)
        mock_db.get_pantry.return_value = [{"name": "Tomato"}]

        mock_ai = AsyncMock(spec=AIService)
        mock_ai.generate_json.return_value = {"suggestions": ["Pasta"]}

        container = DependencyContainer(
            database=mock_db,
            ai_service=mock_ai,
            http_client=AsyncMock(spec=HTTPClient),
        )

        # Function with multiple dependencies
        async def suggest_recipe(
            user_id: str,
            db=Depends(get_database),
            ai=Depends(get_ai_service),
        ):
            pantry = await db.get_pantry(user_id)
            suggestions = await ai.generate_json(f"Suggest recipes for {pantry}")
            return suggestions

        # Resolve and inject
        deps = resolve_dependencies(suggest_recipe, container)
        result = await suggest_recipe(user_id="user_789", **deps)

        # Assertions
        assert result == {"suggestions": ["Pasta"]}
        mock_db.get_pantry.assert_called_once_with("user_789")
        mock_ai.generate_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_container_overrides(self):
        """Test that test container can override dependencies."""
        # Original container
        original_db = AsyncMock(spec=Database)
        original_db.get_log.return_value = {"id": "original"}

        container = DependencyContainer(
            database=original_db,
            ai_service=AsyncMock(spec=AIService),
            http_client=AsyncMock(spec=HTTPClient),
        )

        # Override for testing
        test_db = AsyncMock(spec=Database)
        test_db.get_log.return_value = {"id": "test"}
        container.override_database(test_db)

        # Function
        async def get_meal(log_id: str, db=Depends(get_database)):
            return await db.get_log("user", log_id)

        # Execute with overridden dependency
        deps = resolve_dependencies(get_meal, container)
        result = await get_meal(log_id="log_123", **deps)

        # Should use test database, not original
        assert result == {"id": "test"}
        test_db.get_log.assert_called_once()
        original_db.get_log.assert_not_called()
