# Gemini 3 Implementation Guide (FCP)

The Food Context Protocol (FCP) leverages 15+ features of the Google Gemini 3 API to provide professional-grade food intelligence.

---

## 🚀 Getting Started (uv)

We use `uv` for lightning-fast, reproducible dependency management. **Do not use pip directly.**

### Installation
```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies and create virtual environment
uv sync

# Run the server locally
uv run python -m fcp.server
```

---

## 🧠 Gemini 3 Feature Integration

FCP is built to showcase the full breadth of Gemini 3 capabilities:

| Feature | Usage in FCP | Implementation |
|---------|--------------|----------------|
| **Multimodal (Vision)** | Nutrition breakdown from meal photos. | `GeminiImageMixin` |
| **Function Calling** | 43 structured MCP tools with typed schemas. | `GeminiToolingMixin` |
| **Google Search Grounding** | Real-time FDA recall alerts with citations. | `GeminiGroundingMixin` |
| **Extended Thinking** | Complex recipe reconstruction and reasoning. | `GeminiThinkingMixin` |
| **Code Execution** | Deterministic recipe scaling and calculations. | `GeminiCodeExecutionMixin` |
| **Gemini Live API** | Conversational real-time meal logging. | `GeminiLiveMixin` |
| **Context Caching** | Caching user diet/allergies for 3x speedup. | `GeminiCacheMixin` |
| **Video Processing** | Extracting recipes from cooking tutorials. | `GeminiVideoMixin` |
| **Deep Research** | Comprehensive nutrition reports. | `GeminiDeepResearchMixin` |

---

## 🛠 Model Context Protocol (MCP) Tools

FCP exposes **43 tools** via the Model Context Protocol. All tools use Gemini 3 for intent parsing and structured data extraction.

### Core Tool Categories:
1.  **Nutrition (`dev.fcp.nutrition.*`)**: `add_meal`, `get_meals`, `get_taste_profile`, `suggest_meal`.
2.  **Safety (`dev.fcp.safety.*`)**: `check_food_recalls`, `check_allergen_alerts`, `get_restaurant_safety_info`.
3.  **Recipes (`dev.fcp.recipes.*`)**: `extract_recipe_from_media`, `scale_recipe`, `save_recipe`, `list_recipes`.
4.  **Inventory (`dev.fcp.inventory.*`)**: `add_to_pantry`, `check_pantry_expiry`, `suggest_recipe_from_pantry`.
5.  **Analytics (`dev.fcp.analytics.*`)**: `identify_emerging_trends`, `detect_economic_gaps`.

---

## 🔑 Authentication

Gemini 3 requires an API key from Google AI Studio.

1.  Get your key at [aistudio.google.com](https://aistudio.google.com/).
2.  Set it in your environment:
    ```bash
    export GEMINI_API_KEY="AIza..."
    ```

---

## ☁️ Cloud Run Deployment

Deployment is automated via Google Cloud Build.

```bash
# Deploy using uv-optimized Dockerfile
gcloud builds submit --config cloudbuild.yaml
```

The container uses **Firestore** for persistence and **Cloud Storage** for image blobs, switching automatically when `ENVIRONMENT=production`.

---

## 📊 Observability

We use **Logfire** for deep tracing of Gemini 3 calls, including:
- Token usage and cost tracking.
- Latency monitoring per feature.
- Full trace of agentic tool calls.

---

Built for the **Google Gemini 3 API Developer Competition (February 2026)**.
