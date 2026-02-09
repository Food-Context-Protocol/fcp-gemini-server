"""Tests for Agent orchestration tools."""

from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools.agents import delegate_to_food_agent


@pytest.mark.asyncio
async def test_delegate_to_food_agent_success():
    """Test successful agent delegation."""
    agent_name = "visual_agent"
    objective = "Create a logo for a sushi restaurant"

    mock_result = {
        "concept": "Minimalist red circle with black chopsticks",
        "style": "Modern Japanese",
    }

    with patch("fcp.tools.agents.gemini.generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_result

        result = await delegate_to_food_agent(agent_name, objective)

        assert result["agent"] == agent_name
        assert result["status"] == "completed"
        assert result["result"] == mock_result

        # Verify instructions were included in prompt
        args, _ = mock_gen.call_args
        assert "Art Director" in args[0]
        assert objective in args[0]
