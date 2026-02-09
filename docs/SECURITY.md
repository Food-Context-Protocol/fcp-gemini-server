# Security & API Key Management

This guide covers secure handling of API keys and credentials in the FCP Gemini Server project.

---

## 🔐 API Keys Used in FCP

The FCP server requires several API keys for full functionality:

| Key | Required | Purpose | Get Key From |
|-----|----------|---------|--------------|
| `GEMINI_API_KEY` | ✅ Yes | Gemini AI models | [Google AI Studio](https://aistudio.google.com) |
| `GOOGLE_MAPS_API_KEY` | ⚠️ Optional | Location search, nearby restaurants | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |
| `FCP_TOKEN` | ⚠️ Optional | Authentication for write operations | User-defined |
| `GOOGLE_APPLICATION_CREDENTIALS` | ⚠️ Optional | Firebase/Firestore access | [Firebase Console](https://console.firebase.google.com) |

---

## ✅ Secure Setup

### 1. Use Environment Variables

**Always store API keys in `.env` files**, never in code:

```bash
# .env (this file is gitignored)
GEMINI_API_KEY=AIza...your_key_here
GOOGLE_MAPS_API_KEY=AIza...your_key_here
FCP_TOKEN=your_secure_token_here
GOOGLE_APPLICATION_CREDENTIALS=/path/to/firebase-credentials.json
```

### 2. Verify `.gitignore`

Ensure these files are **never committed**:

```gitignore
# Already in .gitignore
.env
.env.*
*.key
*-credentials.json
```

### 3. Load Environment Variables

The project uses `python-dotenv` to automatically load `.env`:

```python
from dotenv import load_dotenv
load_dotenv()  # Loads .env file
```

---

## 🛡️ API Key Restrictions

### Google Maps API Key

**Restrict your Google Maps API key to prevent abuse:**

1. Go to [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
2. Click your API key
3. **Set Application Restrictions:**
   - **HTTP referrers** (for web apps): `https://yourdomain.com/*`
   - **IP addresses** (for servers): Your server's IP
   - **None** (for development only)

4. **Set API Restrictions** (enable only what you need):
   - ✅ Places API (New)
   - ✅ Geocoding API
   - ✅ Maps JavaScript API (if using web frontend)
   - ❌ Disable all other APIs

5. **Save** changes

### Gemini API Key

**Restrict your Gemini API key:**

1. Go to [Google AI Studio → API Keys](https://aistudio.google.com/apikey)
2. Click your API key settings
3. **Set restrictions if available:**
   - IP address restrictions
   - Usage quotas/limits

4. **Monitor usage** regularly in the console

---

## 🚨 What to Do If a Key is Exposed

If you accidentally commit or share an API key:

### Immediate Actions

1. **Revoke/Delete the exposed key immediately**
   - Google Cloud Console → Credentials → Delete key
   - Google AI Studio → API Keys → Delete key

2. **Generate a new key**
   - Create a replacement key with proper restrictions

3. **Update your `.env` file**
   ```bash
   # Replace old key with new one
   GEMINI_API_KEY=new_key_here
   ```

4. **Restart your server**
   ```bash
   make run-mcp  # or make dev-http
   ```

### Long-term Actions

5. **Scan git history** (if key was committed):
   ```bash
   # Remove key from git history (use with caution)
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all
   ```

6. **Force push** (if working on a private repo):
   ```bash
   git push origin --force --all
   ```

7. **Review access logs** in Google Cloud Console to check for unauthorized usage

---

## 🔒 Production Deployment

### Cloud Run / Google Cloud

Use **Secret Manager** instead of environment variables:

```bash
# Store secret in Secret Manager
gcloud secrets create gemini-api-key --data-file=-
# Paste your key and press Ctrl+D

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding gemini-api-key \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"

# Reference in Cloud Run
gcloud run deploy fcp-api \
  --set-secrets=GEMINI_API_KEY=gemini-api-key:latest
```

### Docker

Use Docker secrets or environment files:

```bash
# Create secrets file (never commit this)
echo "GEMINI_API_KEY=your_key" > .secrets

# Run with secrets
docker run --env-file .secrets fcp-server
```

### Kubernetes

Use Kubernetes Secrets:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: fcp-secrets
type: Opaque
stringData:
  gemini-api-key: "your_key_here"
---
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: fcp-server
        env:
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: fcp-secrets
              key: gemini-api-key
```

---

## 📋 Security Checklist

Before deploying or sharing code:

- [ ] All API keys are in `.env` (not in code)
- [ ] `.env` is in `.gitignore`
- [ ] API keys have usage restrictions enabled
- [ ] API keys have API-level restrictions (only needed APIs)
- [ ] Git history has no exposed keys (`git log -p | grep -i "api"`)
- [ ] Production uses Secret Manager (not plain env vars)
- [ ] Usage monitoring/alerts are configured
- [ ] Team members know how to handle keys securely

---

## 🧪 Development vs Production Keys

### Development
- Use **separate API keys** for development
- Set loose restrictions for localhost
- Use `.env.development`

### Production
- Use **dedicated production keys**
- Set strict IP/domain restrictions
- Use Secret Manager or vault services
- Enable usage alerts and quotas

---

## 📚 Additional Resources

- [Google Cloud Security Best Practices](https://cloud.google.com/security/best-practices)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)

---

## 🆘 Questions?

If you're unsure about any security practices, please ask in the team channel or consult the security documentation before proceeding.

**Remember:** It's always better to ask than to expose credentials!

---

## Security Audit (February 2026)

### Findings Addressed

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | SSE server bypassed auth in tool execution | CRITICAL | Fixed - uses `FCP_TOKEN` env auth |
| 2 | Tool arguments logged at INFO (PII exposure) | CRITICAL | Fixed - args moved to DEBUG level |
| 3 | CORS credentials with unvalidated origins | HIGH | Fixed - wildcard blocked with credentials |
| 4 | SSE server missing security headers | HIGH | Fixed - X-Content-Type-Options, X-Frame-Options |
| 5 | Error messages leaked internal details | MEDIUM | Fixed - generic messages to clients |

### Accepted Risks (Competition Scope)

| Issue | Severity | Rationale |
|-------|----------|-----------|
| SQL column names from dict keys | HIGH | Column names are server-controlled, not user input. All values use `?` placeholders. |
| Token-as-user-id when FCP_TOKEN unset | HIGH | Design choice for local dev. Production always sets FCP_TOKEN via Secret Manager. |
| Rate limit bypass via token rotation | HIGH | Requires Redis/JWT. Acceptable for demo with low traffic. |
| Prompt injection regex-based detection | MEDIUM | Defense-in-depth; Gemini's built-in safety filters provide additional layer. |

### Security Architecture

- **Authentication**: Bearer token matched against `FCP_TOKEN` env var. Valid token -> admin user. Invalid/missing -> read-only demo user.
- **Authorization**: `UserRole.DEMO` restricts to read-only tools. `UserRole.AUTHENTICATED` has full access.
- **Secrets**: All API keys stored in Google Secret Manager, injected as env vars by Cloud Run.
- **Input Sanitization**: `src/fcp/security/input_sanitizer.py` - prompt injection patterns, Unicode normalization, zero-width character removal.
- **SSRF Prevention**: `src/fcp/security/url_validator.py` - private IP blocking, scheme validation, domain whitelist.
- **Rate Limiting**: Per-user/IP bucket with per-endpoint limits via slowapi.
- **Logging**: Sensitive data (tool arguments, message content) at DEBUG only. INFO logs tool names and events only.
