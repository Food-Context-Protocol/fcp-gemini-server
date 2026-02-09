# Cloud Run Deployment Plan for fcp-gemini-server

**Status**: Planning
**Priority**: P0 - Blocking deployment
**Deadline**: Before February 9, 2026 (Hackathon submission)

---

## Critical Issues

### 1. 🚨 SQLite Database Won't Work (P0)

**Problem**: Cloud Run containers are ephemeral. SQLite database stored in `data/fcp.db` will be lost on every container restart.

**Options**:

**A. Switch to Cloud Firestore (RECOMMENDED)**
- ✅ Native GCP service
- ✅ Free tier covers hackathon usage
- ✅ Auto-scales with traffic
- ✅ All class names already use "Firestore*" prefix
- ⏱️ Estimated: 2-3 hours implementation
- **Implementation**:
  1. Add `firebase-admin` to dependencies
  2. Replace SQLite calls in `firestore.py` with actual Firestore SDK
  3. Update `database.py` to use Firestore client
  4. Test with Firebase emulator locally
  5. Deploy with `GOOGLE_APPLICATION_CREDENTIALS` env var

**B. Cloud SQL (PostgreSQL)**
- ✅ Persistent, traditional SQL database
- ❌ Costs $10-20/month minimum
- ❌ Requires schema migration from SQLite
- ⏱️ Estimated: 4-5 hours implementation

**C. Keep SQLite for Demo Only**
- ✅ Zero changes needed
- ❌ Data resets on every container restart
- ❌ Not suitable for persistent demo
- Add banner: "Demo mode - data is ephemeral"

**Decision**: **Option A (Cloud Firestore)** for hackathon demo.

---

### 2. 🚨 Local File Storage Won't Persist (P0)

**Problem**: User uploads stored in `data/uploads/` directory will be lost on container restart.

**Options**:

**A. Cloud Storage (RECOMMENDED)**
- ✅ Already have `local_storage.py` abstraction
- ✅ Easy to add Cloud Storage backend
- ⏱️ Estimated: 1 hour implementation
- **Implementation**:
  1. Add `google-cloud-storage` dependency
  2. Create `CloudStorageClient` class matching `local_storage.py` interface
  3. Use `STORAGE_BACKEND` env var to switch between local/cloud
  4. Create GCS bucket: `fcp-uploads-{project-id}`

**B. Store in Firestore as Base64**
- ❌ Not recommended for large files
- ❌ 1MB document size limit in Firestore

**Decision**: **Option A (Cloud Storage)** with environment-based switching.

---

### 3. ⚠️ Missing Cloud Run Configuration (P1)

**Problem**: No Cloud Run deployment configuration exists.

**Required Files**:

**`cloudbuild.yaml`** (Google Cloud Build):
```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/fcp-gemini-server:$COMMIT_SHA', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/fcp-gemini-server:$COMMIT_SHA']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'fcp-gemini-server'
      - '--image=gcr.io/$PROJECT_ID/fcp-gemini-server:$COMMIT_SHA'
      - '--region=us-central1'
      - '--platform=managed'
      - '--allow-unauthenticated'
images:
  - 'gcr.io/$PROJECT_ID/fcp-gemini-server:$COMMIT_SHA'
```

**`service.yaml`** (Cloud Run Service Config):
```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: fcp-gemini-server
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: '10'
        run.googleapis.com/cpu-throttling: 'false'
    spec:
      containerConcurrency: 80
      timeoutSeconds: 300
      containers:
      - image: gcr.io/PROJECT_ID/fcp-gemini-server:latest
        ports:
        - name: http1
          containerPort: 8080
        env:
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: gemini-api-key
              key: latest
        - name: GOOGLE_APPLICATION_CREDENTIALS
          value: /secrets/firestore-sa.json
        - name: FCP_DATA_DIR
          value: /tmp/data
        - name: ENVIRONMENT
          value: production
        resources:
          limits:
            cpu: '2'
            memory: 2Gi
        volumeMounts:
        - name: firestore-credentials
          mountPath: /secrets
          readOnly: true
      volumes:
      - name: firestore-credentials
        secret:
          secretName: firestore-service-account
```

**Update `Dockerfile`**:
```dockerfile
# Add healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Use port from environment
ENV PORT=8080
EXPOSE ${PORT}

# Run with proper user
USER nobody
CMD ["uvicorn", "fcp.api:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

### 4. ⚠️ Health Check Endpoint (P1)

**Problem**: Cloud Run requires health checks, current `/health` may not be suitable.

**Requirements**:
- Fast response (<1s)
- Doesn't depend on external services
- Returns 200 OK when ready

**Implementation**:
```python
@app.get("/health/liveness")
async def liveness():
    """Cloud Run liveness probe - just check if app is running."""
    return {"status": "ok"}

@app.get("/health/readiness")
async def readiness():
    """Cloud Run readiness probe - check if ready to serve traffic."""
    # Quick check of critical dependencies
    checks = {
        "gemini": gemini_service.is_available(),
        "database": await database.is_connected(),
    }
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    return Response(
        content=json.dumps({"status": "ready" if all_healthy else "not_ready", "checks": checks}),
        status_code=status_code,
    )
```

---

### 5. ⚠️ Environment Variables & Secrets (P1)

**Problem**: Need to manage secrets securely in Cloud Run.

**Required Secrets** (Google Secret Manager):
1. `gemini-api-key` - Gemini API key
2. `firestore-service-account` - Firebase credentials JSON
3. `fcp-auth-token` - FCP_TOKEN for admin access

**Configuration** (Environment Variables):
- `ENVIRONMENT=production`
- `FCP_DATA_DIR=/tmp/data`
- `STORAGE_BACKEND=cloud`
- `GCS_BUCKET=fcp-uploads-{project-id}`

---

### 6. ⚠️ CORS Configuration (P2)

**Problem**: Current CORS origins hardcoded to `fcp.dev` domains.

**Update** `src/fcp/api.py`:
```python
_PRODUCTION_CORS_ORIGINS = [
    "https://fcp.dev",
    "https://app.fcp.dev",
    "https://www.fcp.dev",
    "https://api.fcp.dev",  # Allow API subdomain
]
```

---

## Implementation Checklist

### Phase 1: Storage Backend (2-3 hours)
- [ ] Implement Cloud Firestore backend (replace SQLite)
- [ ] Implement Cloud Storage backend (replace local files)
- [ ] Test with Firebase emulator locally
- [ ] Update tests to work with Firestore

### Phase 2: Cloud Run Configuration (1 hour)
- [ ] Create `cloudbuild.yaml`
- [ ] Create `service.yaml`
- [ ] Update `Dockerfile` with healthchecks
- [ ] Add liveness/readiness endpoints

### Phase 3: Secrets & Environment (30 min)
- [ ] Create secrets in Google Secret Manager
- [ ] Configure environment variables
- [ ] Test deployment with secrets

### Phase 4: DNS & Testing (1 hour)
- [ ] Deploy to Cloud Run
- [ ] Configure `api.fcp.dev` DNS to Cloud Run URL
- [ ] Test all critical endpoints
- [ ] Monitor logs for errors

---

## Deployment Steps

```bash
# 1. Set project
gcloud config set project YOUR_PROJECT_ID

# 2. Create secrets
gcloud secrets create gemini-api-key --data-file=- <<< "$GEMINI_API_KEY"
gcloud secrets create firestore-service-account --data-file=firestore-sa.json

# 3. Build and deploy
gcloud builds submit --config cloudbuild.yaml

# 4. Verify
curl https://fcp-gemini-server-HASH-uc.a.run.app/health/liveness

# 5. Map custom domain
gcloud run services update fcp-gemini-server \
  --platform managed \
  --region us-central1 \
  --add-custom-domain api.fcp.dev
```

---

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Storage Backend | 2-3 hours | None |
| Cloud Run Config | 1 hour | Storage Backend |
| Secrets Setup | 30 min | None |
| Deploy & Test | 1 hour | All above |
| **Total** | **4.5-5.5 hours** | |

**Target Completion**: February 8, 2026 (1 day before deadline)

---

## Rollback Plan

If Cloud Run deployment fails:
1. Keep SQLite for local demo only
2. Deploy to VM with persistent disk instead
3. Document as "local development server" in Devpost submission
4. Use ngrok or similar for public URL

---

## Post-Deployment Monitoring

**Key Metrics**:
- Response latency (target: <2s p95)
- Error rate (target: <1%)
- Cold start time (target: <10s)
- Cost per request

**Monitoring**:
```bash
# View logs
gcloud run services logs read fcp-gemini-server --region us-central1 --limit 50

# Check metrics
gcloud run services describe fcp-gemini-server --region us-central1 --format='value(status)'
```

---

## Notes

- Cloud Run free tier: 2 million requests/month, 360,000 GB-seconds
- For hackathon, this should be more than sufficient
- Consider switching to VM with persistent disk if demo needs are higher
