"""
Tests for audio processing tools.

These tests verify that the audio tools properly:
- Analyze voice transcripts to extract meal data
- Handle error conditions gracefully
- Normalize confidence values correctly
"""

from unittest.mock import AsyncMock, patch

import pytest

from fcp.tools.audio import (
    _normalize_confidence,
    analyze_voice_transcript,
    extract_voice_correction,
)


class TestNormalizeConfidence:
    """Tests for _normalize_confidence helper function."""

    def test_valid_float(self):
        """Test valid float value."""
        assert _normalize_confidence(0.8) == 0.8

    def test_valid_int(self):
        """Test valid integer value."""
        assert _normalize_confidence(1) == 1.0

    def test_string_number(self):
        """Test string that can be converted to float."""
        assert _normalize_confidence("0.7") == 0.7

    def test_clamps_high_value(self):
        """Test that values > 1.0 are clamped to 1.0."""
        assert _normalize_confidence(1.5) == 1.0

    def test_clamps_low_value(self):
        """Test that values < 0.0 are clamped to 0.0."""
        assert _normalize_confidence(-0.5) == 0.0

    def test_none_returns_zero(self):
        """Test that None returns 0.0."""
        assert _normalize_confidence(None) == 0.0

    def test_invalid_string_returns_zero(self):
        """Test that invalid string returns 0.0."""
        assert _normalize_confidence("not a number") == 0.0


class TestAnalyzeVoiceTranscript:
    """Tests for analyze_voice_transcript function."""

    @pytest.mark.asyncio
    async def test_successful_analysis(self):
        """Test successful transcript analysis."""
        mock_response = {
            "dish_name": "Salmon with vegetables",
            "description": "Grilled salmon with roasted vegetables",
            "venue": "Home Kitchen",
            "ingredients": ["salmon", "broccoli", "carrots"],
            "meal_type": "dinner",
            "nutrition_estimate": {"calories": 450, "protein_g": 35},
            "confidence": 0.9,
        }

        with patch("fcp.tools.audio.gemini") as mock_gemini:
            mock_gemini.generate_json = AsyncMock(return_value=mock_response)

            result = await analyze_voice_transcript("I had grilled salmon with veggies for dinner")

            assert result["dish_name"] == "Salmon with vegetables"
            assert result["confidence"] == 0.9
            assert result["error"] is None
            assert "salmon" in result["ingredients"]

    @pytest.mark.asyncio
    async def test_no_dish_identified(self):
        """Test when no dish can be identified from transcript."""
        mock_response = {
            "dish_name": None,
            "description": None,
            "confidence": 0,
            "error": "Could not identify a meal",
        }

        with patch("fcp.tools.audio.gemini") as mock_gemini:
            mock_gemini.generate_json = AsyncMock(return_value=mock_response)

            result = await analyze_voice_transcript("random sounds")

            assert result["dish_name"] is None
            assert result["confidence"] == 0.0
            assert "Could not identify a meal" in result["error"]

    @pytest.mark.asyncio
    async def test_gemini_error(self):
        """Test handling of Gemini API errors."""
        with patch("fcp.tools.audio.gemini") as mock_gemini:
            mock_gemini.generate_json = AsyncMock(side_effect=Exception("API error"))

            result = await analyze_voice_transcript("I ate pizza")

            assert result["dish_name"] is None
            assert result["confidence"] == 0.0
            assert "Error analyzing voice transcript" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_optional_fields(self):
        """Test handling of missing optional fields in response."""
        mock_response = {
            "dish_name": "Pizza",
            "confidence": 0.8,
            # Missing: description, venue, ingredients, meal_type, nutrition_estimate
        }

        with patch("fcp.tools.audio.gemini") as mock_gemini:
            mock_gemini.generate_json = AsyncMock(return_value=mock_response)

            result = await analyze_voice_transcript("I had pizza")

            assert result["dish_name"] == "Pizza"
            assert result["ingredients"] == []
            assert result["venue"] is None
            assert result["error"] is None


class TestExtractVoiceCorrection:
    """Tests for extract_voice_correction function."""

    @pytest.mark.asyncio
    async def test_successful_correction(self):
        """Test successful extraction of voice correction."""
        mock_response = {
            "field": "dish_name",
            "new_value": "Margherita Pizza",
            "confidence": 0.95,
        }

        with patch("fcp.tools.audio.gemini") as mock_gemini:
            mock_gemini.generate_json = AsyncMock(return_value=mock_response)

            result = await extract_voice_correction("Actually, it was a Margherita Pizza, not pepperoni")

            assert result["field"] == "dish_name"
            assert result["new_value"] == "Margherita Pizza"
            assert result["confidence"] == 0.95
            assert result["error"] is None

    @pytest.mark.asyncio
    async def test_unclear_correction(self):
        """Test when correction intent is unclear."""
        mock_response = {
            "field": None,
            "new_value": None,
            "confidence": 0,
        }

        with patch("fcp.tools.audio.gemini") as mock_gemini:
            mock_gemini.generate_json = AsyncMock(return_value=mock_response)

            result = await extract_voice_correction("what's the weather like")

            assert result["field"] is None
            assert result["new_value"] is None
            assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_gemini_error(self):
        """Test handling of Gemini API errors."""
        with patch("fcp.tools.audio.gemini") as mock_gemini:
            mock_gemini.generate_json = AsyncMock(side_effect=Exception("API error"))

            result = await extract_voice_correction("Change the name to salad")

            assert result["field"] is None
            assert result["confidence"] == 0.0
            assert "Error extracting voice correction" in result["error"]
