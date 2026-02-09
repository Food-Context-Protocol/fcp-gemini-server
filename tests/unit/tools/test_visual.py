"""Tests for Visual Kitchen tools."""

from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools.visual import generate_image_prompt


@pytest.mark.asyncio
async def test_generate_image_prompt_success():
    """Test successful prompt generation."""
    subject = "Spicy Ramen"
    expected_prompt = "A detailed, cinematic shot of spicy ramen..."

    with patch("fcp.tools.visual.gemini.generate_content", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = expected_prompt

        result = await generate_image_prompt(subject)

        assert result == expected_prompt
        args, _ = mock_generate.call_args
        assert subject in args[0]
