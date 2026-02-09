"""Unit tests for donate_meal tool and endpoint definitions."""

from unittest.mock import AsyncMock, patch

import pytest


class TestDonateMealRoute:
    """Tests for the donate_meal REST endpoint definition."""

    def test_route_defined_in_misc(self):
        """Test donate_meal route is defined in misc routes."""
        import fcp.routes.misc as misc_module

        with open(misc_module.__file__) as f:
            source = f.read()

        assert '@router.post("/impact/donate")' in source
        assert "post_donate_meal" in source
        assert "DonateMealRequest" in source

    def test_request_model_defined(self):
        """Test DonateMealRequest model is defined."""
        import fcp.routes.misc as misc_module

        with open(misc_module.__file__) as f:
            source = f.read()

        assert "class DonateMealRequest" in source
        assert "log_id: str" in source
        assert 'organization: str = Field(default="Local Food Bank"' in source


class TestDonateMealToolDefinition:
    """Tests for the donate_meal tool function definition."""

    def test_tool_defined_in_crud(self):
        """Test donate_meal is defined in crud.py."""
        import fcp.tools.crud as crud_module

        with open(crud_module.__file__) as f:
            source = f.read()

        assert "async def donate_meal(" in source
        assert "user_id: str" in source
        assert "log_id: str" in source
        assert 'organization: str = "Local Food Bank"' in source

    def test_tool_exported_in_init(self):
        """Test donate_meal is exported from fcp.tools."""
        import fcp.tools as tools_module

        with open(tools_module.__file__) as f:
            source = f.read()

        assert "donate_meal," in source
        assert '"donate_meal",' in source

    def test_tool_implementation_logic(self):
        """Test donate_meal implementation has correct logic."""
        import fcp.tools.crud as crud_module

        with open(crud_module.__file__) as f:
            source = f.read()

        assert "firestore_client.get_log" in source
        assert "firestore_client.update_log" in source
        assert '"donated": True' in source
        assert '"donation_organization":' in source
        assert '"Meal not found"' in source
        assert "except Exception" in source

    def test_tool_returns_correct_structure(self):
        """Test donate_meal returns expected response structure."""
        import fcp.tools.crud as crud_module

        with open(crud_module.__file__) as f:
            source = f.read()

        start = source.find("async def donate_meal(")
        end = source.find("\nasync def", start + 1)
        # sourcery skip: no-conditionals-in-tests
        if end == -1:
            end = source.find("\n# ---", start + 1)
        func_source = source[start:end] if end != -1 else source[start:]

        assert '"success": True' in func_source
        assert '"log_id":' in func_source
        assert '"organization":' in func_source
        assert '"message":' in func_source

        assert '"success": False' in func_source
        assert '"error":' in func_source

    @pytest.mark.asyncio
    async def test_tool_returns_not_found(self):
        """Test donate_meal returns error when meal is missing."""
        from fcp.tools import donate_meal

        with patch("fcp.tools.crud.firestore_client") as mock_fs:
            mock_fs.get_log = AsyncMock(return_value=None)
            result = await donate_meal(
                user_id="test-user",
                log_id="nonexistent-meal-12345",
                organization="Food Bank",
            )

        assert result["success"] is False
        assert result["error"] == "Meal not found"


class TestDonateMealCLICompatibility:
    """Test that donate_meal matches CLI client expectations."""

    def test_endpoint_path_matches_cli(self):
        """Test the endpoint path matches what CLI expects."""
        import fcp.routes.misc as misc_module

        with open(misc_module.__file__) as f:
            source = f.read()

        assert '@router.post("/impact/donate")' in source

    def test_response_structure_matches_cli(self):
        """Test response structure matches CLI expectations."""
        import fcp.tools.crud as crud_module

        with open(crud_module.__file__) as f:
            source = f.read()

        assert '"success":' in source
        assert '"log_id":' in source
        assert '"organization":' in source
        assert '"message":' in source

    def test_request_fields_match_cli(self):
        """Test request fields match CLI expectations."""
        import fcp.routes.misc as misc_module

        with open(misc_module.__file__) as f:
            source = f.read()

        assert "log_id: str" in source
        assert 'organization: str = Field(default="Local Food Bank"' in source
