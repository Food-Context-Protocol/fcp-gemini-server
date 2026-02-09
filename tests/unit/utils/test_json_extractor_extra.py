"""Extra coverage for JSON extractor."""

from fcp.utils.json_extractor import extract_json


def test_extract_json_array_after_object_branch():
    # Object appears before array, but object is invalid so array branch should succeed.
    text = "prefix {bad json} suffix [1, 2, 3]"
    result = extract_json(text)
    assert result == [1, 2, 3]


def test_extract_json_array_after_object_decode_error():
    text = '{"a": 1} [not-json]'
    result = extract_json(text)
    assert result == {"a": 1}


def test_extract_json_invalid_array_after_invalid_object():
    text = "prefix {bad} suffix [not-json]"
    result = extract_json(text)
    assert result is None


def test_extract_json_array_before_object_valid():
    text = '[1, 2] trailing {"a": 1}'
    result = extract_json(text)
    assert result == [1, 2]


def test_extract_json_array_before_object_invalid_then_object():
    text = '[not-json] prefix {"ok": true}'
    result = extract_json(text)
    assert result == {"ok": True}


def test_extract_json_array_after_invalid_object():
    text = "{bad} trailing [1, 2, 3]"
    result = extract_json(text)
    assert result == [1, 2, 3]


def test_extract_json_unbalanced_array_before_object_falls_back_to_object():
    text = '[1, 2 {"ok": true}'
    result = extract_json(text)
    assert result == {"ok": True}


def test_extract_json_unbalanced_array_after_invalid_object_returns_none():
    text = "{bad} trailing [1, 2"
    result = extract_json(text)
    assert result is None
