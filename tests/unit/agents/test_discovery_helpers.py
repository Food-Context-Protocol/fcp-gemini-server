"""Tests for DiscoveryAgent helper methods."""

from fcp.agents.pydantic_agents.discovery import PydanticDiscoveryAgent


class TestNormalizeToList:
    """Tests for _normalize_to_list static method."""

    def test_list_passes_through(self):
        data = [{"name": "a"}, {"name": "b"}]
        assert PydanticDiscoveryAgent._normalize_to_list(data) == data

    def test_dict_with_recommendations_key(self):
        data = {"recommendations": [{"name": "a"}, {"name": "b"}]}
        assert len(PydanticDiscoveryAgent._normalize_to_list(data)) == 2

    def test_dict_with_restaurants_key(self):
        data = {"restaurants": [{"name": "x"}]}
        assert PydanticDiscoveryAgent._normalize_to_list(data) == [{"name": "x"}]

    def test_single_item_dict_with_name(self):
        data = {"name": "Solo Restaurant", "cuisine": "Italian"}
        result = PydanticDiscoveryAgent._normalize_to_list(data)
        assert result == [data]

    def test_single_item_dict_with_title(self):
        data = {"title": "Great Recipe"}
        result = PydanticDiscoveryAgent._normalize_to_list(data)
        assert result == [data]

    def test_unknown_dict_returns_empty(self):
        assert PydanticDiscoveryAgent._normalize_to_list({"foo": "bar"}) == []

    def test_non_dict_non_list_returns_empty(self):
        assert PydanticDiscoveryAgent._normalize_to_list("string") == []
        assert PydanticDiscoveryAgent._normalize_to_list(42) == []
        assert PydanticDiscoveryAgent._normalize_to_list(None) == []


class TestExtractListFromDict:
    """Tests for _extract_list_from_dict static method."""

    def test_each_known_key(self):
        for key in ["recommendations", "restaurants", "recipes", "seasonal_discoveries", "results", "items"]:
            data = {key: [{"name": "test"}]}
            result = PydanticDiscoveryAgent._extract_list_from_dict(data)
            assert result == [{"name": "test"}], f"Failed for key: {key}"

    def test_first_matching_key_wins(self):
        data = {"recommendations": [{"name": "a"}], "restaurants": [{"name": "b"}]}
        result = PydanticDiscoveryAgent._extract_list_from_dict(data)
        assert result == [{"name": "a"}]

    def test_skips_non_list_values(self):
        data = {"recommendations": "not a list", "restaurants": [{"name": "b"}]}
        result = PydanticDiscoveryAgent._extract_list_from_dict(data)
        assert result == [{"name": "b"}]

    def test_single_item_with_name(self):
        data = {"name": "Solo", "type": "restaurant"}
        result = PydanticDiscoveryAgent._extract_list_from_dict(data)
        assert result == [data]

    def test_single_item_with_title(self):
        data = {"title": "Recipe Title"}
        result = PydanticDiscoveryAgent._extract_list_from_dict(data)
        assert result == [data]

    def test_unknown_keys_returns_empty(self):
        data = {"unknown_key": [{"name": "test"}]}
        result = PydanticDiscoveryAgent._extract_list_from_dict(data)
        assert result == []
