"""Portion analysis service using code execution with vision.

This service uses Gemini 3's ability to write and execute Python code
to analyze food images for accurate portion size estimation.
"""

from typing import Any

import logfire
from google import genai
from google.genai import types
from pydantic import BaseModel


class PortionMeasurement(BaseModel):
    """Measurement of a portion on a plate."""

    item_name: str
    estimated_volume_cups: float
    estimated_weight_grams: float
    bounding_box: tuple[int, int, int, int]  # x, y, width, height
    confidence: float


class PortionAnalysisResult(BaseModel):
    """Complete portion analysis of a meal image."""

    portions: list[PortionMeasurement]
    annotated_image_base64: str
    total_estimated_calories: int
    analysis_code: str  # The Python code that was executed
    reasoning: str


class PortionAnalyzerService:
    """Service for analyzing portion sizes using code execution with vision.

    Uses Gemini 3 Flash to write and execute Python code that:
    1. Identifies individual food items in the image
    2. Estimates their dimensions and volumes
    3. Calculates approximate weights and calories
    4. Generates an annotated image with measurements
    """

    MODEL = "gemini-3-flash-preview"

    def __init__(self):
        """Initialize the portion analyzer service."""
        self.client = genai.Client()

    async def analyze_portions(
        self,
        image_url: str,
        reference_object: str | None = None,
    ) -> PortionAnalysisResult:
        """Analyze portion sizes in a food image.

        Args:
            image_url: URL of the food image
            reference_object: Optional reference for scale (e.g., "standard fork")

        Returns:
            Detailed portion analysis with annotated image
        """
        with logfire.span("portion_analyzer.analyze", image_url=image_url):
            prompt = self._build_analysis_prompt(reference_object)

            response = await self.client.aio.models.generate_content(
                model=self.MODEL,
                contents=[
                    types.Part.from_uri(file_uri=image_url, mime_type="image/jpeg"),
                    types.Part(text=prompt),
                ],
                config=types.GenerateContentConfig(
                    tools=[types.Tool(code_execution=types.CodeExecution())],
                    thinking_config=types.ThinkingConfig(thinking_level="high"),
                ),
            )

            return self._parse_response(response)

    async def compare_portions(
        self,
        before_image_url: str,
        after_image_url: str,
    ) -> dict[str, Any]:
        """Compare portions between two images (e.g., before/after eating).

        Args:
            before_image_url: URL of the before image
            after_image_url: URL of the after image

        Returns:
            Comparison result with consumed calories
        """
        prompt = """Compare these two food images to estimate how much was eaten.

Image 1: Before eating
Image 2: After eating

Write Python code to:
1. Analyze both images
2. Identify what food items were consumed
3. Estimate the portion that was eaten
4. Calculate calories consumed

Return a JSON with:
{
    "consumed_items": [{"name": "...", "portion_eaten": 0.75, "estimated_calories": 300}],
    "total_calories_consumed": 450,
    "leftovers": [{"name": "...", "remaining_portion": 0.25}]
}
"""

        response = await self.client.aio.models.generate_content(
            model=self.MODEL,
            contents=[
                types.Part(text="Before eating:"),
                types.Part.from_uri(file_uri=before_image_url, mime_type="image/jpeg"),
                types.Part(text="After eating:"),
                types.Part.from_uri(file_uri=after_image_url, mime_type="image/jpeg"),
                types.Part(text=prompt),
            ],
            config=types.GenerateContentConfig(
                tools=[types.Tool(code_execution=types.CodeExecution())],
                thinking_config=types.ThinkingConfig(thinking_level="high"),
            ),
        )

        return self._parse_comparison_response(response)

    def _build_analysis_prompt(self, reference_object: str | None) -> str:
        """Build the prompt for portion analysis.

        Args:
            reference_object: Optional reference object in the image

        Returns:
            Analysis prompt string
        """
        reference_hint = ""
        if reference_object:
            reference_hint = f"\nUse the {reference_object} in the image as a size reference."

        return f"""Analyze this food image to estimate portion sizes.

Your task:
1. Identify each distinct food item on the plate
2. Estimate the volume and weight of each item
3. Create an annotated version of the image showing:
   - Bounding boxes around each food item
   - Labels with estimated portions
4. Calculate total estimated calories

{reference_hint}

Write Python code to:
1. Load and analyze the image
2. Use computer vision techniques to segment food items
3. Estimate dimensions and calculate volumes
4. Draw annotations on the image
5. Output the results as structured data

Use these standard portion references:
- 1 cup of vegetables = 25-50 calories
- 1 cup of rice/pasta = 200 calories
- 3 oz meat (deck of cards size) = 150-200 calories
- 1 tablespoon of oil/butter = 120 calories

Return a JSON object with:
{{
    "portions": [
        {{"item_name": "...", "estimated_volume_cups": 0.5, "estimated_weight_grams": 100, "bounding_box": [x, y, w, h], "confidence": 0.8}}
    ],
    "total_estimated_calories": 450,
    "reasoning": "..."
}}

Also save the annotated image as base64."""

    def _parse_response(self, response: Any) -> PortionAnalysisResult:
        """Parse the code execution response.

        Args:
            response: Model response

        Returns:
            Parsed PortionAnalysisResult
        """
        result: dict[str, Any] = {
            "portions": [],
            "annotated_image_base64": "",
            "total_estimated_calories": 0,
            "analysis_code": "",
            "reasoning": "",
        }

        for part in response.candidates[0].content.parts:
            # Extract executed code
            if hasattr(part, "executable_code") and part.executable_code:
                result["analysis_code"] = part.executable_code.code

            # Extract code output (should contain JSON result)
            if hasattr(part, "code_execution_result") and part.code_execution_result:
                output = part.code_execution_result.output
                # Parse JSON from output
                import json

                try:
                    data = json.loads(output)
                    # Only update if data is a dict (Gemini may return a list)
                    if isinstance(data, dict):
                        result |= data
                    elif isinstance(data, list) and data:
                        # If it's a list of portions, extract it
                        if all(isinstance(item, dict) for item in data):
                            result["portions"] = data
                except json.JSONDecodeError:
                    result["reasoning"] = output

            # Extract text reasoning
            if hasattr(part, "text") and part.text:
                result["reasoning"] += part.text

        # Convert portions to PortionMeasurement objects
        portions = []
        raw_portions = result.get("portions", [])
        # Ensure portions is a list (defensive against malformed responses)
        if not isinstance(raw_portions, list):
            raw_portions = []
        portions.extend(
            PortionMeasurement(
                item_name=p.get("item_name", "Unknown"),
                estimated_volume_cups=p.get("estimated_volume_cups", 0.0),
                estimated_weight_grams=p.get("estimated_weight_grams", 0.0),
                bounding_box=tuple(p.get("bounding_box", [0, 0, 0, 0])),
                confidence=p.get("confidence", 0.0),
            )
            for p in raw_portions
            if isinstance(p, dict)
        )
        return PortionAnalysisResult(
            portions=portions,
            annotated_image_base64=result.get("annotated_image_base64", ""),
            total_estimated_calories=result.get("total_estimated_calories", 0),
            analysis_code=result.get("analysis_code", ""),
            reasoning=result.get("reasoning", ""),
        )

    def _parse_comparison_response(self, response: Any) -> dict[str, Any]:
        """Parse the comparison response.

        Args:
            response: Model response

        Returns:
            Comparison result dictionary
        """
        import json

        default_result = {
            "consumed_items": [],
            "total_calories_consumed": 0,
            "leftovers": [],
        }

        for part in response.candidates[0].content.parts:
            if hasattr(part, "code_execution_result") and part.code_execution_result:
                try:
                    data = json.loads(part.code_execution_result.output)
                    # Only return if it's a dict with expected structure
                    if isinstance(data, dict):
                        return data
                    # If it's a list, try to use it as consumed_items
                    if isinstance(data, list):
                        return {**default_result, "consumed_items": data}
                except json.JSONDecodeError:
                    pass

        return default_result
