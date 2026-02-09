"""Coverage tests for PortionAnalyzerService parsing branches."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fcp.services.portion_analyzer import PortionAnalyzerService


def _response_with_parts(parts):
    return SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=parts))])


def test_parse_response_handles_list_portions():
    with patch("fcp.services.portion_analyzer.genai.Client", return_value=MagicMock()):
        service = PortionAnalyzerService()

    part = SimpleNamespace(code_execution_result=SimpleNamespace(output=json.dumps([{"item_name": "Apple"}])))
    response = _response_with_parts([part])

    result = service._parse_response(response)
    assert result.portions[0].item_name == "Apple"


def test_parse_response_handles_non_list_portions():
    with patch("fcp.services.portion_analyzer.genai.Client", return_value=MagicMock()):
        service = PortionAnalyzerService()

    payload = {"portions": "oops"}
    part = SimpleNamespace(code_execution_result=SimpleNamespace(output=json.dumps(payload)))
    response = _response_with_parts([part])

    result = service._parse_response(response)
    assert result.portions == []


def test_parse_response_handles_empty_list_payload():
    with patch("fcp.services.portion_analyzer.genai.Client", return_value=MagicMock()):
        service = PortionAnalyzerService()

    part = SimpleNamespace(code_execution_result=SimpleNamespace(output=json.dumps([])))
    response = _response_with_parts([part])

    result = service._parse_response(response)
    assert result.portions == []


def test_parse_response_handles_list_with_non_dict_items():
    with patch("fcp.services.portion_analyzer.genai.Client", return_value=MagicMock()):
        service = PortionAnalyzerService()

    part = SimpleNamespace(code_execution_result=SimpleNamespace(output=json.dumps(["oops"])))
    response = _response_with_parts([part])

    result = service._parse_response(response)
    assert result.portions == []


def test_parse_comparison_response_list_consumed_items():
    with patch("fcp.services.portion_analyzer.genai.Client", return_value=MagicMock()):
        service = PortionAnalyzerService()

    part = SimpleNamespace(code_execution_result=SimpleNamespace(output=json.dumps([{"name": "Soup"}])))
    response = _response_with_parts([part])

    result = service._parse_comparison_response(response)
    assert result["consumed_items"][0]["name"] == "Soup"


def test_parse_comparison_response_non_list_non_dict_payload():
    with patch("fcp.services.portion_analyzer.genai.Client", return_value=MagicMock()):
        service = PortionAnalyzerService()

    part = SimpleNamespace(code_execution_result=SimpleNamespace(output=json.dumps("oops")))
    response = _response_with_parts([part])

    result = service._parse_comparison_response(response)
    assert result["consumed_items"] == []
