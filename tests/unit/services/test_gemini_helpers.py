"""Tests for gemini_helpers.py utility functions."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from fcp.services.gemini_helpers import (
    _extract_grounding_sources,
    _extract_thinking_content,
    _get_thinking_budget,
    _log_token_usage,
    _parse_json_response,
)


class TestGetThinkingBudget:
    """Tests for _get_thinking_budget function."""

    def test_minimal_level(self):
        """Test MINIMAL thinking level returns correct budget."""
        assert _get_thinking_budget("minimal") == 1024

    def test_low_level(self):
        """Test LOW thinking level returns correct budget."""
        assert _get_thinking_budget("low") == 4096

    def test_medium_level(self):
        """Test MEDIUM thinking level returns correct budget."""
        assert _get_thinking_budget("medium") == 16384

    def test_high_level(self):
        """Test HIGH thinking level returns correct budget."""
        assert _get_thinking_budget("high") == 32768

    def test_case_insensitive(self):
        """Test thinking level is case-insensitive."""
        assert _get_thinking_budget("MINIMAL") == 1024
        assert _get_thinking_budget("LoW") == 4096
        assert _get_thinking_budget("MeDiUm") == 16384

    def test_unknown_level_returns_default(self):
        """Test unknown thinking level returns default (medium)."""
        assert _get_thinking_budget("unknown") == 16384
        assert _get_thinking_budget("") == 16384
        assert _get_thinking_budget("invalid") == 16384


class TestExtractThinkingContent:
    """Tests for _extract_thinking_content function."""

    def test_no_candidates(self):
        """Test response with no candidates returns None."""
        response = MagicMock(spec=[])  # No candidates attribute
        assert _extract_thinking_content(response) is None

    def test_empty_candidates(self):
        """Test response with empty candidates returns None."""
        response = MagicMock(candidates=[])
        assert _extract_thinking_content(response) is None

    def test_candidate_no_content(self):
        """Test candidate without content returns None."""
        candidate = MagicMock(spec=[])  # No content attribute
        response = MagicMock(candidates=[candidate])
        assert _extract_thinking_content(response) is None

    def test_content_no_parts(self):
        """Test content without parts returns None."""
        content = MagicMock(spec=[])  # No parts attribute
        candidate = MagicMock(content=content)
        response = MagicMock(candidates=[candidate])
        assert _extract_thinking_content(response) is None

    def test_part_without_thought_flag(self):
        """Test parts without thought flag returns None."""
        part = MagicMock(thought=False, text="regular text")
        content = MagicMock(parts=[part])
        candidate = MagicMock(content=content)
        response = MagicMock(candidates=[candidate])
        assert _extract_thinking_content(response) is None

    def test_single_thinking_part(self):
        """Test extraction of single thinking part."""
        part = MagicMock(thought=True, text="This is my reasoning")
        content = MagicMock(parts=[part])
        candidate = MagicMock(content=content)
        response = MagicMock(candidates=[candidate])

        result = _extract_thinking_content(response)
        assert result == "This is my reasoning"

    def test_multiple_thinking_parts(self):
        """Test concatenation of multiple thinking parts."""
        part1 = MagicMock(thought=True, text="First thought")
        part2 = MagicMock(thought=False, text="Regular text")
        part3 = MagicMock(thought=True, text="Second thought")

        content = MagicMock(parts=[part1, part2, part3])
        candidate = MagicMock(content=content)
        response = MagicMock(candidates=[candidate])

        result = _extract_thinking_content(response)
        assert result == "First thought\nSecond thought"

    def test_multiple_candidates_with_thinking(self):
        """Test extraction from multiple candidates."""
        part1 = MagicMock(thought=True, text="Candidate 1 thinking")
        content1 = MagicMock(parts=[part1])
        candidate1 = MagicMock(content=content1)

        part2 = MagicMock(thought=True, text="Candidate 2 thinking")
        content2 = MagicMock(parts=[part2])
        candidate2 = MagicMock(content=content2)

        response = MagicMock(candidates=[candidate1, candidate2])

        result = _extract_thinking_content(response)
        assert result == "Candidate 1 thinking\nCandidate 2 thinking"

    def test_thinking_part_without_text(self):
        """Test thinking part without text is skipped."""
        part1 = MagicMock(thought=True, spec=["thought"])  # No text attribute
        part2 = MagicMock(thought=True, text="Valid thought")

        content = MagicMock(parts=[part1, part2])
        candidate = MagicMock(content=content)
        response = MagicMock(candidates=[candidate])

        result = _extract_thinking_content(response)
        assert result == "Valid thought"


class TestParseJsonResponse:
    """Tests for _parse_json_response function."""

    def test_empty_string_raises_error(self):
        """Test empty string raises ValueError."""
        with pytest.raises(ValueError, match="Empty response"):
            _parse_json_response("")

    def test_none_raises_error(self):
        """Test None raises ValueError."""
        with pytest.raises(ValueError, match="Empty response"):
            _parse_json_response(None)

    def test_whitespace_only_raises_error(self):
        """Test whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="Empty response"):
            _parse_json_response("   \n\t  ")

    def test_valid_dict_json(self):
        """Test parsing valid JSON dict."""
        text = '{"key": "value", "number": 42}'
        result = _parse_json_response(text)
        assert result == {"key": "value", "number": 42}

    def test_valid_list_json(self):
        """Test parsing valid JSON list."""
        text = '[1, 2, 3, "four"]'
        result = _parse_json_response(text)
        assert result == [1, 2, 3, "four"]

    def test_json_with_whitespace(self):
        """Test JSON with leading/trailing whitespace."""
        text = '  \n  {"key": "value"}  \t  '
        result = _parse_json_response(text)
        assert result == {"key": "value"}

    def test_json_with_bom(self):
        """Test JSON with BOM character."""
        text = '\ufeff{"key": "value"}'
        result = _parse_json_response(text)
        assert result == {"key": "value"}

    def test_markdown_wrapped_json(self):
        """Test JSON wrapped in markdown code blocks."""
        text = '```json\n{"key": "value"}\n```'
        result = _parse_json_response(text)
        assert result == {"key": "value"}

    def test_invalid_json_raises_error(self):
        """Test invalid JSON raises ValueError."""
        with pytest.raises(ValueError, match="Failed to parse JSON"):
            _parse_json_response("not json at all")

    def test_truncated_json_raises_error(self):
        """Test truncated JSON raises ValueError."""
        with pytest.raises(ValueError, match="Failed to parse JSON"):
            _parse_json_response('{"key": "value"')

    def test_logs_warning_on_failure(self, caplog):
        """Test that parsing failure logs a warning."""
        with caplog.at_level(logging.WARNING):
            with pytest.raises(ValueError):
                _parse_json_response("invalid json")

        assert "Failed to parse JSON" in caplog.text
        assert "length=" in caplog.text


class TestExtractGroundingSources:
    """Tests for _extract_grounding_sources function."""

    def test_no_candidates(self):
        """Test response with no candidates returns empty list."""
        response = MagicMock(candidates=[])
        assert _extract_grounding_sources(response) == []

    def test_candidate_no_grounding_metadata(self):
        """Test candidate without grounding_metadata returns empty list."""
        candidate = MagicMock(grounding_metadata=None)
        response = MagicMock(candidates=[candidate])
        assert _extract_grounding_sources(response) == []

    def test_metadata_no_grounding_chunks(self):
        """Test metadata without grounding_chunks returns empty list."""
        metadata = MagicMock(spec=[])  # No grounding_chunks attribute
        candidate = MagicMock(grounding_metadata=metadata)
        response = MagicMock(candidates=[candidate])
        assert _extract_grounding_sources(response) == []

    def test_empty_grounding_chunks(self):
        """Test empty grounding_chunks returns empty list."""
        metadata = MagicMock(grounding_chunks=[])
        candidate = MagicMock(grounding_metadata=metadata)
        response = MagicMock(candidates=[candidate])
        assert _extract_grounding_sources(response) == []

    def test_single_grounding_source(self):
        """Test extraction of single grounding source."""
        web = MagicMock(uri="https://example.com", title="Example")
        chunk = MagicMock(web=web)
        metadata = MagicMock(grounding_chunks=[chunk])
        candidate = MagicMock(grounding_metadata=metadata)
        response = MagicMock(candidates=[candidate])

        result = _extract_grounding_sources(response)
        assert result == [{"uri": "https://example.com", "title": "Example"}]

    def test_multiple_grounding_sources(self):
        """Test extraction of multiple grounding sources."""
        web1 = MagicMock(uri="https://example1.com", title="Example 1")
        web2 = MagicMock(uri="https://example2.com", title="Example 2")
        chunk1 = MagicMock(web=web1)
        chunk2 = MagicMock(web=web2)

        metadata = MagicMock(grounding_chunks=[chunk1, chunk2])
        candidate = MagicMock(grounding_metadata=metadata)
        response = MagicMock(candidates=[candidate])

        result = _extract_grounding_sources(response)
        assert len(result) == 2
        assert {"uri": "https://example1.com", "title": "Example 1"} in result
        assert {"uri": "https://example2.com", "title": "Example 2"} in result

    def test_chunk_without_web_attribute(self):
        """Test chunk without web attribute is skipped."""
        chunk1 = MagicMock(spec=[])  # No web attribute
        web2 = MagicMock(uri="https://example.com", title="Example")
        chunk2 = MagicMock(web=web2)

        metadata = MagicMock(grounding_chunks=[chunk1, chunk2])
        candidate = MagicMock(grounding_metadata=metadata)
        response = MagicMock(candidates=[candidate])

        result = _extract_grounding_sources(response)
        assert result == [{"uri": "https://example.com", "title": "Example"}]

    def test_chunk_with_none_web(self):
        """Test chunk with None web is skipped."""
        chunk1 = MagicMock(web=None)
        web2 = MagicMock(uri="https://example.com", title="Example")
        chunk2 = MagicMock(web=web2)

        metadata = MagicMock(grounding_chunks=[chunk1, chunk2])
        candidate = MagicMock(grounding_metadata=metadata)
        response = MagicMock(candidates=[candidate])

        result = _extract_grounding_sources(response)
        assert result == [{"uri": "https://example.com", "title": "Example"}]


class TestLogTokenUsage:
    """Tests for _log_token_usage function."""

    def test_no_usage_metadata(self, caplog):
        """Test response without usage_metadata logs warning."""
        response = MagicMock(spec=[])  # No usage_metadata attribute

        with caplog.at_level(logging.WARNING):
            result = _log_token_usage(response, "test_method")

        assert "No usage metadata" in caplog.text
        assert result == {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
        }

    def test_valid_usage_metadata(self, caplog):
        """Test extraction of valid usage metadata."""
        metadata = MagicMock(prompt_token_count=100, candidates_token_count=50)
        response = MagicMock(usage_metadata=metadata)

        with caplog.at_level(logging.INFO):
            result = _log_token_usage(response, "generate_content")

        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 50
        assert result["total_tokens"] == 150
        assert result["cost_usd"] > 0  # Cost calculated

        assert "Gemini API usage [generate_content]" in caplog.text
        assert "input=100" in caplog.text
        assert "output=50" in caplog.text

    def test_zero_tokens(self):
        """Test handling of zero tokens."""
        metadata = MagicMock(prompt_token_count=0, candidates_token_count=0)
        response = MagicMock(usage_metadata=metadata)

        result = _log_token_usage(response, "test_method")

        assert result["input_tokens"] == 0
        assert result["output_tokens"] == 0
        assert result["cost_usd"] == 0.0

    def test_float_token_counts_converted_to_int(self):
        """Test that float token counts are converted to integers."""
        metadata = MagicMock(prompt_token_count=100.5, candidates_token_count=50.7)
        response = MagicMock(usage_metadata=metadata)

        result = _log_token_usage(response, "test_method")

        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 50
        assert isinstance(result["input_tokens"], int)
        assert isinstance(result["output_tokens"], int)

    def test_missing_token_count_attributes(self):
        """Test handling of missing token count attributes."""
        metadata = MagicMock(spec=[])  # No token count attributes
        response = MagicMock(usage_metadata=metadata)

        result = _log_token_usage(response, "test_method")

        assert result["input_tokens"] == 0
        assert result["output_tokens"] == 0

    @patch("fcp.services.gemini_helpers.record_gemini_usage")
    def test_records_prometheus_metrics(self, mock_record):
        """Test that Prometheus metrics are recorded."""
        metadata = MagicMock(prompt_token_count=100, candidates_token_count=50)
        response = MagicMock(usage_metadata=metadata)

        _log_token_usage(response, "test_method", latency_seconds=1.5, success=True)

        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args[1]
        assert call_kwargs["method"] == "test_method"
        assert call_kwargs["input_tokens"] == 100
        assert call_kwargs["output_tokens"] == 50
        assert call_kwargs["latency_seconds"] == 1.5
        assert call_kwargs["success"] is True

    @patch("fcp.services.gemini_helpers.record_gemini_usage")
    def test_records_metrics_on_failure(self, mock_record):
        """Test that metrics are recorded even without usage metadata."""
        response = MagicMock(spec=[])  # No usage_metadata

        _log_token_usage(response, "test_method", success=False)

        mock_record.assert_called_once()
        call_kwargs = mock_record.call_args[1]
        assert call_kwargs["success"] is False
        assert call_kwargs["input_tokens"] == 0

    def test_cost_calculation(self):
        """Test accurate cost calculation."""
        metadata = MagicMock(prompt_token_count=1000, candidates_token_count=500)
        response = MagicMock(usage_metadata=metadata)

        result = _log_token_usage(response, "test_method")

        # Cost should be: (1000 * input_rate) + (500 * output_rate)
        # Exact values depend on COST_PER_INPUT_TOKEN and COST_PER_OUTPUT_TOKEN
        assert isinstance(result["cost_usd"], float)
        assert result["cost_usd"] >= 0
        assert len(str(result["cost_usd"]).split(".")[-1]) <= 6  # Rounded to 6 decimals


class TestRetryDecorator:
    """Tests for gemini_retry decorator creation."""

    def test_retry_decorator_created(self):
        """Test that retry decorator is created successfully."""
        from fcp.services.gemini_helpers import gemini_retry

        # Should be a retry decorator instance
        assert gemini_retry is not None
        assert callable(gemini_retry)

    def test_retry_decorator_applies(self):
        """Test that retry decorator can be applied to a function."""
        from fcp.services.gemini_helpers import gemini_retry

        @gemini_retry
        async def test_func():
            return "success"

        # Function should still be callable
        assert callable(test_func)
