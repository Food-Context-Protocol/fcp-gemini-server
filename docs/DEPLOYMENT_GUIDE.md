# FCP Deployment Guide (Google Cloud Run)

This guide documents the process for deploying the Food Context Protocol (FCP) services to Google Cloud Run.

## Architecture
- **fcp-api**: The main REST API providing food intelligence features.
- **fcp-mcp**: The MCP SSE server providing remote access for AI assistants (e.g., Claude Desktop).
- **Database**: Google Cloud Firestore (Native Mode).
- **Storage**: Google Cloud Storage bucket for user-uploaded food images.
- **Secrets**: Google Secret Manager for API keys.

---

## 1. Manual Deployment (CLI)

### Prerequisites
- Google Cloud SDK installed and authenticated.
- Billing enabled for the project.
- Project ID: `YOUR_PROJECT_ID`

### Initial Infrastructure Setup
One-time setup for the project:

```bash
# Enable required APIs
gcloud services enable
    secretmanager.googleapis.com
    cloudbuild.googleapis.com
    run.googleapis.com
    artifactregistry.googleapis.com
    firestore.googleapis.com
    storage.googleapis.com

# Initialize Firestore
gcloud firestore databases create --location=us-central1

# Create Storage Bucket
gcloud storage buckets create gs://fcp-uploads-YOUR_PROJECT_ID --location=us-central1
```

### Secrets Management
Create the following secrets in Secret Manager:
- `gemini-api-key`: Your Google AI Studio key.
- `usda-api-key`: API key from api.nal.usda.gov.
- `fda-api-key`: API key from api.fda.gov.
- `google-maps-api-key`: Google Maps Places API key.
- `astro-api-key`: Astro scheduling API key.
- `astro-endpoint`: Astro scheduling endpoint URL.
- `fcp-token`: Authentication token in `user_id:token` format (e.g., `jwegis:devpost`).

```bash
# Example: Creating a secret
gcloud secrets create gemini-api-key --replication-policy="automatic"
echo -n "YOUR_KEY" | gcloud secrets versions add gemini-api-key --data-file=-
```

### Deployment Commands
Run these from the project root:

```bash
# Deploy REST API
gcloud builds submit --config cloudbuild.yaml

# Deploy MCP SSE Server
gcloud builds submit --config cloudbuild-mcp.yaml
```

---

## 2. GitHub Actions Automation

We use GitHub Actions to automatically redeploy services when code is pushed to the `main` branch.

### Prerequisites for Automation
1.  **Workload Identity Federation**: Follow [Google's guide](https://github.com/google-github-actions/auth#workload-identity-federation) to set up a pool and provider for GitHub.
2.  **Service Account**: Create a service account (e.g., `github-deployer`) with these roles:
    - Cloud Build Editor
    - Cloud Run Admin
    - Service Account User
    - Storage Admin (for build artifacts)

### Workflow Configuration
The workflow is defined in `.github/workflows/deploy.yml`. It handles:
1.  Authentication with GCP.
2.  Building and pushing Docker images.
3.  Deploying to Cloud Run using `service.yaml` / `service-mcp.yaml`.

---

## 3. Custom Domains
The services are mapped to:
- `api.fcp.dev` -> `fcp-api`
- `mcp.fcp.dev` -> `fcp-mcp`

**DNS Configuration**: Both use a CNAME record pointing to `ghs.googlehosted.com` in Cloudflare.
