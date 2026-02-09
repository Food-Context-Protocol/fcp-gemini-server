"""Tests for utils/json_extractor.py."""

from typing import Any, cast

from fcp.utils.json_extractor import (
    _extract_balanced_json,
    extract_json,
    extract_json_with_key,
)


class TestExtractJson:
    """Tests for extract_json function."""

    def test_pure_json_response(self) -> None:
        text = '{"dish_name": "Ramen", "cuisine": "Japanese"}'
        result = extract_json(text)
        assert result == {"dish_name": "Ramen", "cuisine": "Japanese"}

    def test_json_in_markdown_code_block(self) -> None:
        text = """Here is the analysis:
```json
{"dish_name": "Pasta", "rating": 5}
```
Hope this helps!"""
        result = extract_json(text)
        assert result == {"dish_name": "Pasta", "rating": 5}

    def test_json_in_generic_code_block(self) -> None:
        text = """The result is:
```
{"name": "Pizza"}
```"""
        result = extract_json(text)
        assert result == {"name": "Pizza"}

    def test_json_array_response(self) -> None:
        text = '[{"name": "A"}, {"name": "B"}]'
        result = extract_json(text)
        assert result == [{"name": "A"}, {"name": "B"}]

    def test_json_embedded_in_prose(self) -> None:
        text = 'Based on my analysis, the data is: {"result": true, "count": 42} which indicates success.'
        result = extract_json(text)
        assert result == {"result": True, "count": 42}

    def test_returns_none_for_empty_string(self) -> None:
        result = extract_json("")
        assert result is None

    def test_returns_none_for_none_input(self) -> None:
        result = extract_json(None)
        assert result is None

    def test_returns_none_for_non_string(self) -> None:
        result = extract_json(cast(Any, 12345))
        assert result is None

    def test_returns_none_for_invalid_json(self) -> None:
        result = extract_json("This is not JSON at all")
        assert result is None

    def test_handles_nested_objects(self) -> None:
        text = '{"outer": {"inner": {"deep": "value"}}}'
        result = extract_json(text)
        assert result == {"outer": {"inner": {"deep": "value"}}}

    def test_handles_json_with_escaped_characters(self) -> None:
        text = '{"message": "Hello \\"World\\""}'
        result = extract_json(text)
        assert result == {"message": 'Hello "World"'}

    def test_case_insensitive_json_tag(self) -> None:
        text = """Result:
```JSON
{"data": "value"}
```"""
        result = extract_json(text)
        assert result == {"data": "value"}

    def test_invalid_json_in_code_block_returns_none(self) -> None:
        text = """```json
{invalid json here}
```
No valid JSON after this"""
        result = extract_json(text)
        assert result is None

    def test_invalid_json_in_generic_code_block_falls_through(self) -> None:
        text = """```
not json
```
Later: {"actual": "json"}"""
        result = extract_json(text)
        assert result == {"actual": "json"}

    def test_extracts_array_with_objects(self) -> None:
        text = '[{"name": "Item1"}, {"name": "Item2"}]'
        result = extract_json(text)
        assert result == [{"name": "Item1"}, {"name": "Item2"}]

    def test_balanced_extraction_handles_strings_with_braces(self) -> None:
        text = '{"message": "Use {braces} here", "count": 1}'
        result = extract_json(text)
        assert result == {"message": "Use {braces} here", "count": 1}

    def test_first_valid_json_returned(self) -> None:
        text = '{"first": 1} and {"second": 2}'
        result = extract_json(text)
        assert result == {"first": 1}


class TestExtractBalancedJson:
    """Tests for _extract_balanced_json function."""

    def test_extracts_balanced_object(self) -> None:
        text = 'prefix {"key": "value"} suffix'
        result = _extract_balanced_json(text, "{", "}")
        assert result == '{"key": "value"}'

    def test_extracts_balanced_array(self) -> None:
        text = "data: [1, 2, 3] end"
        result = _extract_balanced_json(text, "[", "]")
        assert result == "[1, 2, 3]"

    def test_handles_nested_braces(self) -> None:
        text = '{"outer": {"inner": "value"}}'
        result = _extract_balanced_json(text, "{", "}")
        assert result == '{"outer": {"inner": "value"}}'

    def test_handles_escaped_quotes(self) -> None:
        text = '{"msg": "say \\"hi\\""}'
        result = _extract_balanced_json(text, "{", "}")
        assert result == '{"msg": "say \\"hi\\""}'

    def test_handles_backslash_escape(self) -> None:
        text = '{"path": "C:\\\\Users"}'
        result = _extract_balanced_json(text, "{", "}")
        assert result == '{"path": "C:\\\\Users"}'

    def test_returns_none_when_not_found(self) -> None:
        text = "no json here"
        result = _extract_balanced_json(text, "{", "}")
        assert result is None

    def test_returns_none_for_unbalanced(self) -> None:
        text = '{"unclosed": "object"'
        result = _extract_balanced_json(text, "{", "}")
        assert result is None

    def test_handles_braces_in_strings(self) -> None:
        text = '{"text": "a{b}c", "num": 1}'
        result = _extract_balanced_json(text, "{", "}")
        assert result is not None
        assert '"num": 1' in result


class TestExtractJsonWithKey:
    """Tests for extract_json_with_key function."""

    def test_extracts_json_with_required_key(self) -> None:
        text = '{"recommendations": [{"name": "Item"}], "extra": "data"}'
        result = extract_json_with_key(text, "recommendations")
        assert result is not None
        assert "recommendations" in result
        assert result["recommendations"] == [{"name": "Item"}]

    def test_returns_none_when_key_missing(self) -> None:
        text = '{"other": "data"}'
        result = extract_json_with_key(text, "recommendations")
        assert result is None

    def test_returns_none_for_empty_string(self) -> None:
        result = extract_json_with_key("", "key")
        assert result is None

    def test_returns_none_for_none_input(self) -> None:
        result = extract_json_with_key(None, "key")
        assert result is None

    def test_returns_none_for_non_string(self) -> None:
        result = extract_json_with_key(cast(Any, 12345), "key")
        assert result is None

    def test_returns_none_for_array_without_key(self) -> None:
        text = '[{"other_key": "Item"}]'
        result = extract_json_with_key(text, "name")
        assert result is None

    def test_finds_key_in_embedded_json(self) -> None:
        text = 'Here is the response: {"results": [1, 2, 3]} done.'
        result = extract_json_with_key(text, "results")
        assert result is not None
        assert result["results"] == [1, 2, 3]

    def test_escapes_regex_special_chars_in_key(self) -> None:
        text = '{"key.with.dots": "value"}'
        result = extract_json_with_key(text, "key.with.dots")
        assert result is not None
        assert result["key.with.dots"] == "value"

    def test_fallback_search_when_extraction_fails(self) -> None:
        text = 'prefix {"target_key": 123} suffix'
        result = extract_json_with_key(text, "target_key")
        assert result is not None
        assert result["target_key"] == 123

    def test_fallback_search_handles_invalid_json(self) -> None:
        text = 'The {"target_key": not valid json}'
        result = extract_json_with_key(text, "target_key")
        assert result is None

    def test_fallback_pattern_finds_key_when_extract_json_returns_wrong_type(self) -> None:
        text = '[1, 2, 3] but also {"my_key": "found_it"}'
        result = extract_json_with_key(text, "my_key")
        assert result is not None
        assert result["my_key"] == "found_it"

    def test_fallback_pattern_with_matched_json_missing_key(self) -> None:
        text = 'some {"other": "value"} text'
        result = extract_json_with_key(text, "nonexistent")
        assert result is None

    def test_fallback_succeeds_when_extract_json_returns_array(self) -> None:
        from unittest.mock import patch

        text = '{"target_key": "found_value"}'

        with patch("fcp.utils.json_extractor.extract_json", return_value=[1, 2, 3]):
            result = extract_json_with_key(text, "target_key")
            assert result is not None
            assert result["target_key"] == "found_value"

    def test_fallback_returns_none_when_regex_matches_but_key_not_in_parsed(self) -> None:
        from unittest.mock import patch

        text = '{"message": "target"}'

        with patch("fcp.utils.json_extractor.extract_json", return_value=None):
            result = extract_json_with_key(text, "target")
            assert result is None


class TestExtractJsonArrayDecodeError:
    """Tests for JSON array decode error handling."""

    def test_array_extraction_with_invalid_json_array(self) -> None:
        text = "data [not: valid, json: here] more"
        result = extract_json(text)
        assert result is None

    def test_array_extraction_decode_error_falls_through(self) -> None:
        text = 'prefix [invalid,json] suffix {"valid": "json"}'
        result = extract_json(text)
        assert result == {"valid": "json"}

    def test_array_with_unquoted_strings(self) -> None:
        text = "result: [abc, def] end"
        result = extract_json(text)
        assert result is None


def test_extract_json_array_before_object_branch():
    text = '[1, 2] trailing {"a": 1}'
    result = extract_json(text)
    assert result == [1, 2]


def test_extract_json_array_after_object_branch():
    text = '{"a": 1} trailing [1, 2]'
    result = extract_json(text)
    assert result == {"a": 1}
