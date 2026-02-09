"""Coverage tests for recipe extractor helpers."""

from fcp.tools.recipe_extractor import _ensure_list, _parse_int


def test_parse_int_invalid():
    assert _parse_int("not-int") is None


def test_ensure_list_none():
    assert _ensure_list(None) == []
