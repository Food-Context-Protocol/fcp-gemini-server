"""
Tests for portion analyzer service defensive parsing.

These tests verify that the portion analyzer handles malformed
Gemini responses gracefully without raising AttributeError.
"""

import os
from unittest.mock import patch

# Set dummy env var to avoid credential errors during import
os.environ.setdefault("GEMINI_API_KEY", "test-key")


class MockCodeExecutionResult:
    """Mock code execution result."""

    def __init__(self, output: str):
        self.output = output


class MockExecutableCode:
    """Mock executable code."""

    def __init__(self, code: str):
        self.code = code


class MockPart:
    """Mock response part."""

    def __init__(
        self,
        text: str | None = None,
        code_execution_result: MockCodeExecutionResult | None = None,
        executable_code: MockExecutableCode | None = None,
    ):
        self.text = text
        self.code_execution_result = code_execution_result
        self.executable_code = executable_code


class MockContent:
    """Mock content."""

    def __init__(self, parts: list[MockPart]):
        self.parts = parts


class MockCandidate:
    """Mock candidate."""

    def __init__(self, content: MockContent):
        self.content = content


class MockResponse:
    """Mock Gemini response."""

    def __init__(self, candidates: list[MockCandidate]):
        self.candidates = candidates


class TestPortionAnalyzerParsing:
    """Tests for _parse_response defensive handling."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock the genai.Client to avoid API key requirement
        with patch("fcp.services.portion_analyzer.genai.Client"):
            from fcp.services.portion_analyzer import PortionAnalyzerService

            self.service = PortionAnalyzerService()

    def test_parse_response_with_valid_dict(self):
        """Test parsing valid dict response."""
        from fcp.services.portion_analyzer import PortionAnalysisResult

        json_output = """{
            "portions": [
                {"item_name": "Rice", "estimated_volume_cups": 1.0, "estimated_weight_grams": 200, "bounding_box": [10, 20, 100, 100], "confidence": 0.9}
            ],
            "total_estimated_calories": 200,
            "reasoning": "Found rice on plate"
        }"""

        response = MockResponse(
            [MockCandidate(MockContent([MockPart(code_execution_result=MockCodeExecutionResult(json_output))]))]
        )

        result = self.service._parse_response(response)

        assert isinstance(result, PortionAnalysisResult)
        assert len(result.portions) == 1
        assert result.portions[0].item_name == "Rice"
        assert result.total_estimated_calories == 200

    def test_parse_response_with_list_instead_of_dict(self):
        """Test parsing when Gemini returns a list instead of dict.

        This was causing: AttributeError: 'list' object has no attribute 'get'
        """
        from fcp.services.portion_analyzer import PortionAnalysisResult

        # Gemini sometimes returns just a list of portions
        json_output = """[
            {"item_name": "Chicken", "estimated_volume_cups": 0.5, "estimated_weight_grams": 150, "bounding_box": [0, 0, 50, 50], "confidence": 0.8}
        ]"""

        response = MockResponse(
            [MockCandidate(MockContent([MockPart(code_execution_result=MockCodeExecutionResult(json_output))]))]
        )

        # Should not raise AttributeError
        result = self.service._parse_response(response)

        assert isinstance(result, PortionAnalysisResult)
        assert len(result.portions) == 1
        assert result.portions[0].item_name == "Chicken"

    def test_parse_response_with_list_non_dict_items(self):
        """Test parsing list output that isn't a list of dicts."""
        from fcp.services.portion_analyzer import PortionAnalysisResult

        json_output = """["oops", "not a dict"]"""

        response = MockResponse(
            [
                MockCandidate(
                    MockContent(
                        [
                            MockPart(code_execution_result=MockCodeExecutionResult(json_output)),
                            MockPart(text="Extra reasoning."),
                        ]
                    )
                )
            ]
        )

        result = self.service._parse_response(response)

        assert isinstance(result, PortionAnalysisResult)
        assert result.portions == []
        assert "Extra reasoning." in result.reasoning

    def test_parse_response_with_empty_list(self):
        """Test parsing empty list response."""
        from fcp.services.portion_analyzer import PortionAnalysisResult

        json_output = "[]"

        response = MockResponse(
            [MockCandidate(MockContent([MockPart(code_execution_result=MockCodeExecutionResult(json_output))]))]
        )

        result = self.service._parse_response(response)

        assert isinstance(result, PortionAnalysisResult)
        assert len(result.portions) == 0

    def test_parse_response_with_invalid_json(self):
        """Test parsing invalid JSON falls back gracefully."""
        from fcp.services.portion_analyzer import PortionAnalysisResult

        json_output = "not valid json {{"

        response = MockResponse(
            [MockCandidate(MockContent([MockPart(code_execution_result=MockCodeExecutionResult(json_output))]))]
        )

        result = self.service._parse_response(response)

        assert isinstance(result, PortionAnalysisResult)
        assert len(result.portions) == 0
        assert result.reasoning == json_output

    def test_parse_response_with_non_dict_portions(self):
        """Test parsing when portions contains non-dict items."""
        from fcp.services.portion_analyzer import PortionAnalysisResult

        json_output = """{
            "portions": ["invalid", 123, null, {"item_name": "Valid"}],
            "total_estimated_calories": 100
        }"""

        response = MockResponse(
            [MockCandidate(MockContent([MockPart(code_execution_result=MockCodeExecutionResult(json_output))]))]
        )

        result = self.service._parse_response(response)

        assert isinstance(result, PortionAnalysisResult)
        # Only the valid dict item should be parsed
        assert len(result.portions) == 1
        assert result.portions[0].item_name == "Valid"

    def test_parse_response_with_portions_as_string(self):
        """Test parsing when portions is a string instead of list."""
        from fcp.services.portion_analyzer import PortionAnalysisResult

        json_output = """{
            "portions": "not a list",
            "total_estimated_calories": 0
        }"""

        response = MockResponse(
            [MockCandidate(MockContent([MockPart(code_execution_result=MockCodeExecutionResult(json_output))]))]
        )

        result = self.service._parse_response(response)

        assert isinstance(result, PortionAnalysisResult)
        assert len(result.portions) == 0

    def test_parse_response_with_text_and_code(self):
        """Test parsing response with both text and code execution."""
        json_output = '{"portions": [], "total_estimated_calories": 500}'

        response = MockResponse(
            [
                MockCandidate(
                    MockContent(
                        [
                            MockPart(executable_code=MockExecutableCode("print('hello')")),
                            MockPart(code_execution_result=MockCodeExecutionResult(json_output)),
                            MockPart(text="Analysis complete."),
                        ]
                    )
                )
            ]
        )

        result = self.service._parse_response(response)

        assert result.analysis_code == "print('hello')"
        assert result.total_estimated_calories == 500
        assert "Analysis complete." in result.reasoning


class TestComparisonResponseParsing:
    """Tests for _parse_comparison_response defensive handling."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock the genai.Client to avoid API key requirement
        with patch("fcp.services.portion_analyzer.genai.Client"):
            from fcp.services.portion_analyzer import PortionAnalyzerService

            self.service = PortionAnalyzerService()

    def test_parse_comparison_with_valid_dict(self):
        """Test parsing valid comparison response."""
        json_output = """{
            "consumed_items": [{"name": "Pizza", "portion_eaten": 0.75, "estimated_calories": 300}],
            "total_calories_consumed": 300,
            "leftovers": [{"name": "Salad", "remaining_portion": 1.0}]
        }"""

        response = MockResponse(
            [MockCandidate(MockContent([MockPart(code_execution_result=MockCodeExecutionResult(json_output))]))]
        )

        result = self.service._parse_comparison_response(response)

        assert result["total_calories_consumed"] == 300
        assert len(result["consumed_items"]) == 1

    def test_parse_comparison_with_list(self):
        """Test parsing when comparison returns a list.

        Should use list as consumed_items.
        """
        json_output = """[{"name": "Burger", "portion_eaten": 1.0, "estimated_calories": 500}]"""

        response = MockResponse(
            [MockCandidate(MockContent([MockPart(code_execution_result=MockCodeExecutionResult(json_output))]))]
        )

        result = self.service._parse_comparison_response(response)

        assert len(result["consumed_items"]) == 1
        assert result["consumed_items"][0]["name"] == "Burger"
        assert result["total_calories_consumed"] == 0  # Default
        assert result["leftovers"] == []  # Default

    def test_parse_comparison_with_invalid_json(self):
        """Test parsing invalid JSON returns default."""
        json_output = "invalid json"

        response = MockResponse(
            [MockCandidate(MockContent([MockPart(code_execution_result=MockCodeExecutionResult(json_output))]))]
        )

        result = self.service._parse_comparison_response(response)

        assert result == {
            "consumed_items": [],
            "total_calories_consumed": 0,
            "leftovers": [],
        }

    def test_parse_comparison_with_non_list_or_dict(self):
        """Test parsing comparison response with JSON that isn't list or dict."""
        json_output = '"just a string"'

        response = MockResponse(
            [MockCandidate(MockContent([MockPart(code_execution_result=MockCodeExecutionResult(json_output))]))]
        )

        result = self.service._parse_comparison_response(response)

        assert result == {
            "consumed_items": [],
            "total_calories_consumed": 0,
            "leftovers": [],
        }

    def test_parse_comparison_with_no_code_execution(self):
        """Test parsing response without code execution result."""
        response = MockResponse([MockCandidate(MockContent([MockPart(text="No code was executed")]))])

        result = self.service._parse_comparison_response(response)

        assert result == {
            "consumed_items": [],
            "total_calories_consumed": 0,
            "leftovers": [],
        }
