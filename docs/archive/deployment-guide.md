# Public Demo Deployment Guide

**Deploy FoodLog to Cloud Run for Hackathon Judges**

Devpost requires: "Public Project Link: A URL to your working product or interactive demo. Should be publicly accessible and **not require a login or paywall**."

This guide gets you a public demo URL in 20 minutes.

---

## Overview

**Goal:** Deploy FoodLog HTTP API to Google Cloud Run with:
- ✅ Public URL (no authentication required for judges)
- ✅ Demo mode (judges can try features without creating account)
- ✅ HTTPS (secure, fast, global CDN)
- ✅ Auto-scaling (handles traffic spikes from judge testing)

**Cost:** Free tier covers hackathon traffic (~$0)

---

## Prerequisites

1. **Google Cloud Account** (free tier)
   - Sign up: https://cloud.google.com/free
   - $300 free credit for 90 days

2. **gcloud CLI** installed
   ```bash
   # macOS
   brew install google-cloud-sdk

   # Linux
   curl https://sdk.cloud.google.com | bash

   # Windows
   # Download from https://cloud.google.com/sdk/docs/install
   ```

3. **Gemini API Key**
   - Get from: https://aistudio.google.com/app/apikey
   - Already have in `.env`

---

## Step 1: Prepare for Deployment (5 min)

### 1.1: Create Dockerfile

Create `Dockerfile` in project root:

```dockerfile
# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install uv
RUN pip install uv

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source code
COPY src/ ./src/
COPY spec/ ./spec/

# Create data directory
RUN mkdir -p data

# Expose port (Cloud Run uses PORT env var)
EXPOSE 8080

# Run HTTP server
CMD ["uv", "run", "uvicorn", "fcp.api:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 1.2: Create .dockerignore

Create `.dockerignore`:

```
.venv/
__pycache__/
*.pyc
.git/
.env
tests/
docs/
*.md
.github/
.ruff_cache/
.mypy_cache/
.pytest_cache/
node_modules/
```

### 1.3: Enable Demo Mode

Update `src/fcp/auth/permissions.py`:

```python
# Demo mode: Allow public access for judges
DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() == "true"

# In Cloud Run, always use demo mode for public access
if os.environ.get("K_SERVICE"):  # Cloud Run environment
    DEMO_MODE = True
```

This automatically enables demo mode when deployed to Cloud Run.

### 1.4: Test Locally with Docker

```bash
# Build image
docker build -t foodlog-api .

# Run locally
docker run -p 8080:8080 \
  -e GEMINI_API_KEY=your-key-here \
  -e DEMO_MODE=true \
  foodlog-api

# Test
curl http://localhost:8080/health
```

---

## Step 2: Deploy to Cloud Run (10 min)

### 2.1: Authenticate

```bash
# Login to Google Cloud
gcloud auth login

# Set project (create if needed)
gcloud projects create foodlog-demo --name="FoodLog Demo"
gcloud config set project foodlog-demo

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 2.2: Deploy with gcloud

```bash
# Deploy to Cloud Run (builds and deploys in one command)
gcloud run deploy foodlog-api \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your-gemini-api-key,DEMO_MODE=true \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0

# This will:
# 1. Build Docker image using Cloud Build
# 2. Push to Container Registry
# 3. Deploy to Cloud Run
# 4. Return public URL
```

**Output:**
```
Service [foodlog-api] revision [foodlog-api-00001-abc] has been deployed.
Service URL: https://foodlog-api-xyz123.a.run.app
```

**Your Public Demo URL:** `https://foodlog-api-xyz123.a.run.app`

### 2.3: Verify Deployment

```bash
# Test health endpoint
curl https://foodlog-api-xyz123.a.run.app/health

# Test analyze endpoint
curl -X POST https://foodlog-api-xyz123.a.run.app/analyze \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://example.com/food.jpg"}'
```

---

## Step 3: Configure for Judge Access (5 min)

### 3.1: Add CORS (Allow Browser Access)

Update `src/fcp/api.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(...)

# Enable CORS for judge browser testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Public demo, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Redeploy:
```bash
gcloud run deploy foodlog-api --source .
```

### 3.2: Create Landing Page

Create `static/index.html` for judges to land on:

```html
<!DOCTYPE html>
<html>
<head>
    <title>FoodLog - Gemini 3 Hackathon Demo</title>
    <style>
        body {
            font-family: system-ui, -apple-system, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .card {
            background: white;
            color: #333;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 { color: #667eea; }
        .btn {
            display: inline-block;
            padding: 12px 24px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            margin: 10px 10px 10px 0;
        }
        .btn:hover { background: #764ba2; }
        code {
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>🍽️ FoodLog - AI-Powered Food Intelligence</h1>
        <p><strong>Gemini 3 Hackathon Demo</strong></p>

        <h2>Quick Start (No Login Required!)</h2>

        <h3>📸 Analyze a Meal Photo</h3>
        <pre><code>curl -X POST https://foodlog-api-xyz123.a.run.app/analyze \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c"}'</code></pre>

        <h3>🔍 Check Food Safety</h3>
        <pre><code>curl "https://foodlog-api-xyz123.a.run.app/mcp/check_food_recalls?food_item=romaine+lettuce"</code></pre>

        <h3>🎤 Voice Meal Logging</h3>
        <pre><code>curl -X POST https://foodlog-api-xyz123.a.run.app/voice/transcribe \
  -F "audio=@meal.mp3"</code></pre>

        <h2>Features (15+ Gemini 3 Capabilities)</h2>
        <ul>
            <li>✅ Multimodal image analysis</li>
            <li>✅ Function calling (40+ MCP tools)</li>
            <li>✅ Google Search grounding</li>
            <li>✅ Extended thinking</li>
            <li>✅ Code execution</li>
            <li>✅ Gemini Live API</li>
            <li>✅ Video processing</li>
            <li>✅ Context caching</li>
        </ul>

        <div style="margin-top: 30px;">
            <a href="/docs" class="btn">📖 API Docs</a>
            <a href="/health" class="btn">💚 Health Check</a>
            <a href="https://github.com/humboldt-tech/foodlog-devpost" class="btn">💻 GitHub</a>
        </div>

        <p style="margin-top: 30px; font-size: 14px; color: #666;">
            <strong>For Judges:</strong> This demo is publicly accessible. No authentication required.
            All endpoints support demo mode with sample data.
        </p>
    </div>
</body>
</html>
```

Update `src/fcp/api.py` to serve static files:

```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")
```

### 3.3: Update README with Demo URL

Update your `README.md`:

```markdown
## Live Demo (Hackathon Submission)

**🚀 Try it now:** https://foodlog-api-xyz123.a.run.app

**No login required!** The demo is publicly accessible for judges.

### Quick Test

```bash
# Analyze a meal photo
curl -X POST https://foodlog-api-xyz123.a.run.app/analyze \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c"}'

# Check food safety
curl https://foodlog-api-xyz123.a.run.app/mcp/check_food_recalls?food_item=romaine+lettuce
```
```

---

## Step 4: Monitor & Optimize (Ongoing)

### 4.1: View Logs

```bash
# Real-time logs
gcloud run logs tail foodlog-api --region us-central1

# Recent errors
gcloud run logs read foodlog-api --limit 50 --region us-central1
```

### 4.2: Check Metrics

```bash
# Open Cloud Run console
gcloud run services describe foodlog-api --region us-central1
```

Visit: https://console.cloud.google.com/run

**Monitor:**
- Request count (judge traffic)
- Error rate (should be 0%)
- Response time (aim for <2s)
- Memory usage

### 4.3: Increase Limits (If Needed)

If judges are testing heavily:

```bash
gcloud run deploy foodlog-api \
  --max-instances 50 \
  --concurrency 100
```

---

## Troubleshooting

### Issue: "Service Unavailable"

**Cause:** Container crashed or startup timeout

**Fix:**
```bash
# Check logs
gcloud run logs tail foodlog-api

# Common issues:
# - Missing GEMINI_API_KEY
# - Port not matching Cloud Run's PORT env var
# - Startup timeout (increase --timeout)
```

### Issue: "Forbidden"

**Cause:** Authentication required

**Fix:**
```bash
# Ensure --allow-unauthenticated
gcloud run deploy foodlog-api --allow-unauthenticated
```

### Issue: "Out of Memory"

**Cause:** 1Gi not enough for Gemini models

**Fix:**
```bash
gcloud run deploy foodlog-api --memory 2Gi
```

### Issue: Slow Cold Starts

**Cause:** No minimum instances

**Fix:**
```bash
# Keep 1 instance warm for judges
gcloud run deploy foodlog-api --min-instances 1
```

**Cost:** ~$5-10/month for 1 warm instance during hackathon

---

## Cost Estimate

**Cloud Run Pricing:**
- **Free tier:** 2 million requests/month, 360,000 GB-seconds
- **Your usage (2 days of judge testing):**
  - ~1,000 requests (judges testing)
  - ~50 GB-seconds
  - **Cost: $0** (within free tier)

**Gemini API:**
- Flash: $0.075 / 1M input tokens
- Estimate: 100 requests × 1000 tokens = 100K tokens
- **Cost: ~$0.01**

**Total: Essentially free for hackathon**

---

## Alternative: AI Studio Apps (Even Faster!)

**If you want an even quicker demo:**

1. Visit https://aistudio.google.com/
2. Click "Create" → "App"
3. Upload your Gemini prompts
4. Get instant public URL
5. **Time: 5 minutes**

**Pros:**
- Fastest option
- No deployment needed
- Built-in UI

**Cons:**
- Less customization
- Doesn't show full backend
- Can't demo MCP tools

**Recommendation:** Use Cloud Run for full demo, AI Studio for quick prototype

---

## Final Checklist

Before submitting to Devpost:

- [ ] Public URL works: `https://foodlog-api-xyz123.a.run.app`
- [ ] No login required (demo mode enabled)
- [ ] Landing page explains what to do
- [ ] Health endpoint returns 200
- [ ] At least 3 features testable via curl
- [ ] Logs show no errors
- [ ] README updated with demo URL
- [ ] Video shows the public URL
- [ ] Devpost submission includes URL

---

## Next Steps

1. ✅ Deploy to Cloud Run (use this guide)
2. ✅ Test public URL
3. ✅ Update README with demo link
4. ✅ Proceed to video script (`docs/video-script.md`)

---

## Your Devpost Submission

**Public Project Link:**
```
https://foodlog-api-xyz123.a.run.app
```

**Public Code Repository:**
```
https://github.com/humboldt-tech/foodlog-devpost
```

**Instructions for Judges:**
```
Visit https://foodlog-api-xyz123.a.run.app for interactive examples.
No authentication required - all endpoints support demo mode.
```

Done! ✅
