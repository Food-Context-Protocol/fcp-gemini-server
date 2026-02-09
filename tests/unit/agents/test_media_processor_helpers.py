"""Tests for MediaProcessorAgent helper methods."""

from fcp.agents.pydantic_agents.media_processor import PydanticMediaProcessingAgent


class TestParseVenueInfo:
    """Tests for _parse_venue_info static method."""

    def test_returns_venue_when_name_present(self):
        result = PydanticMediaProcessingAgent._parse_venue_info(
            {
                "venue_name": "Cafe Roma",
                "venue_type": "restaurant",
                "location_hint": "downtown",
            }
        )
        assert result is not None
        assert result.name == "Cafe Roma"
        assert result.type == "restaurant"
        assert result.location_hint == "downtown"

    def test_returns_none_when_no_name(self):
        result = PydanticMediaProcessingAgent._parse_venue_info({})
        assert result is None

    def test_returns_none_when_name_empty(self):
        result = PydanticMediaProcessingAgent._parse_venue_info({"venue_name": ""})
        assert result is None

    def test_partial_venue_info(self):
        result = PydanticMediaProcessingAgent._parse_venue_info(
            {
                "venue_name": "Joe's Diner",
            }
        )
        assert result is not None
        assert result.name == "Joe's Diner"
        assert result.type is None
        assert result.location_hint is None
