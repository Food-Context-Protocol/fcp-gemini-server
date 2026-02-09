"""Analyze Routes.

Food image analysis endpoints:
- POST /analyze - Basic image analysis
- POST /analyze/stream - Streaming analysis for real-time UI
- POST /analyze/v2 - Function calling version
- POST /analyze/thinking - Extended thinking for complex dishes
"""

from fastapi import Depends, Query, Request
from fastapi.responses import StreamingResponse

from fcp.auth import AuthenticatedUser, require_write_access
from fcp.prompts import PROMPTS
from fcp.routes import schemas as route_schemas
from fcp.routes.router import APIRouter
from fcp.security.rate_limit import RATE_LIMIT_ANALYZE, limiter
from fcp.services.gemini import GeminiClient, get_gemini
from fcp.tools import analyze_meal
from fcp.tools.analyze import (
    analyze_meal_v2,
    analyze_meal_with_agentic_vision,
    analyze_meal_with_thinking,
)

AnalyzeRequest = route_schemas.ImageURLRequest
ImageAnalysisResponse = route_schemas.ImageAnalysisResponse

router = APIRouter()


# --- Routes ---


@router.post("/analyze", response_model=ImageAnalysisResponse)
@limiter.limit(RATE_LIMIT_ANALYZE)
async def analyze_image(
    request: Request,
    analyze_request: AnalyzeRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> ImageAnalysisResponse:
    """Analyze a food image (without creating a log entry). Requires authentication."""
    result = await analyze_meal(analyze_request.image_url)
    return ImageAnalysisResponse(analysis=result, method="basic")


@router.post("/analyze/stream")
@limiter.limit(RATE_LIMIT_ANALYZE)
async def analyze_image_stream(
    request: Request,
    analyze_request: AnalyzeRequest,
    user: AuthenticatedUser = Depends(require_write_access),
    gemini: GeminiClient = Depends(get_gemini),
):
    """
    Stream food image analysis for real-time UI updates. Requires authentication.

    Returns Server-Sent Events (SSE) with analysis chunks as they're generated.
    Perfect for showing AI "thinking" in the Flutter app.

    Usage (Flutter):
        final client = http.Client();
        final request = http.Request('POST', Uri.parse('$baseUrl/analyze/stream'));
        final response = await client.send(request);
        await for (final chunk in response.stream.transform(utf8.decoder)) {
            setState(() { _analysisText += chunk; });
        }
    """

    async def generate():
        prompt = PROMPTS.get("analyze_meal", "Analyze this food image and describe it in detail.")
        async for chunk in gemini.generate_content_stream(prompt, image_url=analyze_request.image_url):
            # SSE format: "data: <content>\n\n"
            # Escape newlines in chunk to maintain SSE protocol
            escaped_chunk = chunk.replace("\n", "\\n")
            yield f"data: {escaped_chunk}\n\n"
        # Send done event to signal completion
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/analyze/v2", response_model=ImageAnalysisResponse)
@limiter.limit(RATE_LIMIT_ANALYZE)
async def analyze_image_v2(
    request: Request,
    analyze_request: AnalyzeRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> ImageAnalysisResponse:
    """
    Analyze a food image using Gemini 3 function calling. Requires authentication.

    Returns structured data extracted via tool calls:
    - Dish identification
    - Ingredients
    - Nutrition estimates
    - Allergens
    - Dietary tags
    """
    result = await analyze_meal_v2(analyze_request.image_url)
    return ImageAnalysisResponse(
        analysis=result,
        version="v2",
        method="function_calling",
    )


@router.post("/analyze/thinking", response_model=ImageAnalysisResponse)
@limiter.limit(RATE_LIMIT_ANALYZE)
async def analyze_image_with_thinking(
    request: Request,
    analyze_request: AnalyzeRequest,
    thinking_level: str = Query(default="high", pattern=r"^(minimal|low|medium|high)$"),
    user: AuthenticatedUser = Depends(require_write_access),
) -> ImageAnalysisResponse:
    """
    Analyze a complex food image using extended thinking. Requires authentication.

    Use for:
    - Multi-component dishes
    - Fusion cuisine
    - Unusual presentations
    - When standard analysis is uncertain
    """
    result = await analyze_meal_with_thinking(
        analyze_request.image_url,
        thinking_level=thinking_level,
    )
    return ImageAnalysisResponse(
        analysis=result,
        method="thinking",
        thinking_level=thinking_level,
    )


@router.post("/analyze/agentic-vision", response_model=ImageAnalysisResponse)
@limiter.limit(RATE_LIMIT_ANALYZE)
async def analyze_image_with_agentic_vision(
    request: Request,
    analyze_request: AnalyzeRequest,
    user: AuthenticatedUser = Depends(require_write_access),
) -> ImageAnalysisResponse:
    """
    Analyze food image using Agentic Vision (code execution). Requires authentication.

    Uses Gemini's code execution to actively investigate images:
    - Zooms into areas of interest
    - Counts discrete items
    - Calculates portion estimates

    Best for complex dishes or when standard analysis needs improvement.
    May take longer but provides higher accuracy for difficult images.
    """
    result = await analyze_meal_with_agentic_vision(analyze_request.image_url)
    return ImageAnalysisResponse(
        analysis=result,
        method="agentic_vision",
    )
