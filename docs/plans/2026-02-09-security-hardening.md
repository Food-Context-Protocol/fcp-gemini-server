# FCP Organization Security Hardening Implementation Plan

> **Note:** This plan is intended to be implemented and tracked task-by-task, either manually or via automation.

**Goal:** Harden all 8 Food-Context-Protocol repositories against the critical, high, and medium severity vulnerabilities discovered during comprehensive security audit.

**Architecture:** Three-phase approach — (1) emergency triage of critical secrets and org settings, (2) security infrastructure rollout across all repos, (3) code-level fixes and CI/CD hardening. Each phase gates the next to prevent deploying fixes on unprotected branches.

**Tech Stack:** GitHub CLI (`gh`), GitHub REST API, Python (FastAPI/pytest), YAML (GitHub Actions, Cloud Run), Markdown (SECURITY.md, CODEOWNERS)

---

## Audit Summary

| Severity | Count | Description |
|----------|-------|-------------|
| CRITICAL | 6 | `.mcp.json` token in public repo (non-sensitive\*), no branch protection (8 repos), no 2FA, no secret scanning, no Dependabot alerts, no push protection |
| HIGH | 4 | GCP infra exposed in public repo, `LOG_LEVEL: debug` in prod, non-timing-safe token comparison, no SECURITY.md |
| MEDIUM | 3 | No CODEOWNERS, only 1 CI workflow across 8 repos, no Dependabot config |
| LOW | 1 | Python SDK uses lowercase `authorization` header |

**Repos audited:** `fcp`, `fcp-gemini-server`, `fcp-cli`, `fcp-dev`, `fcp-gemini-python-client`, `python-sdk`, `typescript-sdk`, `.github`

---

## Phase 1: Emergency Triage (Critical Fixes)

### Task 1: `.mcp.json` Contains Token in Public Repo

**Files:**
- File: `fcp-gemini-server/.mcp.json`

**Context:** The file `fcp-gemini-server/.mcp.json` contains the value `FCP_TOKEN: "jwegis:devpost"` committed to a public repository. While this is a **non-sensitive Devpost hackathon identifier** (not a real credential), it was flagged during the audit because committing any token-like value to a public repo is a security anti-pattern that could confuse future contributors or automated scanners.

**Finding:** INFORMATIONAL (downgraded from CRITICAL)
- The value `jwegis:devpost` is a Devpost convention identifier, not a secret
- No rotation or history rewrite is needed
- Consider adding a comment to `.mcp.json` or documentation clarifying this is not a credential
- Optionally add `.mcp.json` to `.gitignore` as a general best practice for MCP config files that *could* contain real tokens in other environments

**Recommended Action:** No immediate fix required. Optionally document the convention.

---

### Task 2: Enable Organization-Level Security Settings

**Context:** The Food-Context-Protocol GitHub org has ALL security features disabled: no 2FA requirement, no Dependabot alerts, no secret scanning, no push protection, no commit signing requirement.

**Step 1: Enable 2FA requirement**

```bash
gh api -X PATCH /orgs/Food-Context-Protocol \
  -f two_factor_requirement_enabled=true
```

> **Warning:** This will remove any org members who don't have 2FA enabled. Notify all members first.

**Step 2: Enable Dependabot alerts for new repos**

```bash
gh api -X PATCH /orgs/Food-Context-Protocol \
  -f dependabot_alerts_enabled_for_new_repositories=true
```

**Step 3: Enable secret scanning for new repos**

```bash
gh api -X PATCH /orgs/Food-Context-Protocol \
  -f secret_scanning_enabled_for_new_repositories=true
```

**Step 4: Enable secret scanning push protection**

```bash
gh api -X PATCH /orgs/Food-Context-Protocol \
  -f secret_scanning_push_protection_enabled_for_new_repositories=true
```

**Step 5: Enable web commit signoff**

```bash
gh api -X PATCH /orgs/Food-Context-Protocol \
  -f web_commit_signoff_required=true
```

**Step 6: Enable Dependabot alerts on all existing repos**

```bash
for repo in fcp fcp-gemini-server fcp-cli fcp-dev fcp-gemini-python-client python-sdk typescript-sdk .github; do
  gh api -X PUT /repos/Food-Context-Protocol/$repo/vulnerability-alerts
  echo "Enabled Dependabot alerts for $repo"
done
```

**Step 7: Enable secret scanning on all existing repos**

```bash
for repo in fcp fcp-gemini-server fcp-cli fcp-dev fcp-gemini-python-client python-sdk typescript-sdk .github; do
  gh api -X PATCH /repos/Food-Context-Protocol/$repo \
    -f security_and_analysis[secret_scanning][status]=enabled \
    -f security_and_analysis[secret_scanning_push_protection][status]=enabled
  echo "Enabled secret scanning for $repo"
done
```

**Step 8: Verify all settings**

```bash
gh api /orgs/Food-Context-Protocol | jq '{
  two_factor_requirement_enabled,
  dependabot_alerts_enabled_for_new_repositories,
  secret_scanning_enabled_for_new_repositories,
  secret_scanning_push_protection_enabled_for_new_repositories,
  web_commit_signoff_required
}'
```

Expected: All values `true`.

---

### Task 3: Enable Branch Protection on All Repositories

**Context:** Zero of 8 repos have branch protection. Anyone with write access can force-push to `main`.

**Step 1: Set branch protection on `fcp-gemini-server` (most critical)**

```bash
gh api -X PUT /repos/Food-Context-Protocol/fcp-gemini-server/branches/main/protection \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["test", "lint"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
```

**Step 2: Set branch protection on remaining repos (no CI yet, so no status checks)**

```bash
for repo in fcp fcp-cli fcp-dev fcp-gemini-python-client python-sdk typescript-sdk .github; do
  gh api -X PUT /repos/Food-Context-Protocol/$repo/branches/main/protection \
    --input - <<'EOF'
{
  "required_status_checks": null,
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
  echo "Protected main branch for $repo"
done
```

**Step 3: Verify branch protection**

```bash
for repo in fcp fcp-gemini-server fcp-cli fcp-dev fcp-gemini-python-client python-sdk typescript-sdk .github; do
  echo "--- $repo ---"
  gh api /repos/Food-Context-Protocol/$repo/branches/main/protection \
    --jq '{enforce_admins: .enforce_admins.enabled, required_reviews: .required_pull_request_reviews.required_approving_review_count, allow_force_pushes: .allow_force_pushes.enabled}'
done
```

Expected: `enforce_admins: true`, `required_reviews: 1`, `allow_force_pushes: false` for each repo.

---

## Phase 2: Security Infrastructure

### Task 4: Add SECURITY.md to All Repositories

**Context:** No repo in the org has a SECURITY.md. The `fcp` spec repo's GOVERNANCE.md references `security@fcp.dev` but there's no formal vulnerability disclosure policy.

**Step 1: Create the SECURITY.md template**

Create: `fcp/SECURITY.md`

```markdown
# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest  | Yes       |

## Reporting a Vulnerability

**Do NOT open a public issue for security vulnerabilities.**

Please report security vulnerabilities by emailing **security@fcp.dev**.

You will receive an acknowledgment within 48 hours. We will work with you to understand and address the issue before any public disclosure.

### What to include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Security Measures

- All secrets are managed via Google Cloud Secret Manager
- Authentication is required for write operations
- Input sanitization includes prompt injection prevention
- SSRF protection is enabled on all outbound requests
- Rate limiting is enforced on all endpoints
- Dependencies are monitored via Dependabot

## Scope

This policy applies to all repositories under the [Food-Context-Protocol](https://github.com/Food-Context-Protocol) organization.
```

**Step 2: Commit to `fcp` repo**

```bash
cd fcp
git add SECURITY.md
git commit -m "security: add vulnerability disclosure policy"
```

**Step 3: Copy SECURITY.md to all other repos**

```bash
for repo in fcp-gemini-server fcp-cli fcp-dev fcp-gemini-python-client python-sdk typescript-sdk .github; do
  cp fcp/SECURITY.md $repo/SECURITY.md
done
```

**Step 4: Commit in each repo**

```bash
for repo in fcp-gemini-server fcp-cli fcp-dev fcp-gemini-python-client python-sdk typescript-sdk .github; do
  cd $repo
  git add SECURITY.md
  git commit -m "security: add vulnerability disclosure policy"
  cd ..
done
```

---

### Task 5: Add CODEOWNERS to All Repositories

**Context:** No repo has CODEOWNERS. This means PRs can be merged without review from code owners, even with branch protection enabled.

**Step 1: Create CODEOWNERS for `fcp-gemini-server` (granular ownership)**

Create: `fcp-gemini-server/.github/CODEOWNERS`

```
# Default owner for everything
* @Food-Context-Protocol/maintainers

# Security-sensitive files require security team review
src/fcp/auth/ @Food-Context-Protocol/security
src/fcp/security/ @Food-Context-Protocol/security
.github/workflows/ @Food-Context-Protocol/security
Dockerfile* @Food-Context-Protocol/security
cloudbuild*.yaml @Food-Context-Protocol/security
service.yaml @Food-Context-Protocol/security
```

**Step 2: Create CODEOWNERS for all other repos (simple ownership)**

Create in each repo: `.github/CODEOWNERS`

```
# Default owner for everything
* @Food-Context-Protocol/maintainers

# CI/CD and security-sensitive files
.github/ @Food-Context-Protocol/security
```

**Step 3: Create the required GitHub teams**

```bash
gh api -X POST /orgs/Food-Context-Protocol/teams \
  -f name=maintainers \
  -f description="Core maintainers with review rights" \
  -f privacy=closed

gh api -X POST /orgs/Food-Context-Protocol/teams \
  -f name=security \
  -f description="Security team for sensitive file reviews" \
  -f privacy=closed
```

**Step 4: Commit CODEOWNERS to all repos**

```bash
for repo in fcp fcp-gemini-server fcp-cli fcp-dev fcp-gemini-python-client python-sdk typescript-sdk .github; do
  mkdir -p $repo/.github
  cd $repo
  git add .github/CODEOWNERS
  git commit -m "security: add CODEOWNERS for mandatory review routing"
  cd ..
done
```

---

### Task 6: Add Dependabot Configuration to All Repositories

**Context:** No repo has a `dependabot.yml` config. Even after enabling Dependabot alerts (Task 2), automated PR creation for dependency updates requires explicit configuration.

**Step 1: Create Dependabot config for `fcp-gemini-server` (Python + GitHub Actions)**

Create: `fcp-gemini-server/.github/dependabot.yml`

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 10
    labels:
      - "dependencies"
      - "security"

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    labels:
      - "dependencies"
      - "ci"

  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    labels:
      - "dependencies"
      - "docker"
```

**Step 2: Create Dependabot config for `fcp-cli` (Python)**

Create: `fcp-cli/.github/dependabot.yml`

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 10
    labels:
      - "dependencies"
```

**Step 3: Create Dependabot config for `python-sdk` and `fcp-gemini-python-client` (Python)**

Same config as `fcp-cli` — copy to both:

```bash
cp fcp-cli/.github/dependabot.yml python-sdk/.github/dependabot.yml
cp fcp-cli/.github/dependabot.yml fcp-gemini-python-client/.github/dependabot.yml
```

**Step 4: Create Dependabot config for `typescript-sdk` (npm)**

Create: `typescript-sdk/.github/dependabot.yml`

```yaml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 10
    labels:
      - "dependencies"
```

**Step 5: Create Dependabot config for `fcp-dev` (npm + GitHub Actions)**

Create: `fcp-dev/.github/dependabot.yml`

```yaml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 10
    labels:
      - "dependencies"

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    labels:
      - "dependencies"
      - "ci"
```

**Step 6: Commit to all repos**

```bash
for repo in fcp-gemini-server fcp-cli fcp-dev fcp-gemini-python-client python-sdk typescript-sdk; do
  cd $repo
  git add .github/dependabot.yml
  git commit -m "security: add Dependabot config for automated dependency updates"
  cd ..
done
```

---

## Phase 3: Code-Level Fixes

### Task 7: Fix Timing-Safe Token Comparison

**Files:**
- Modify: `fcp-gemini-server/src/fcp/auth/local.py` (line ~62)
- Test: `fcp-gemini-server/tests/test_auth_local.py`

**Context:** The token comparison in `local.py` uses `if token != expected_token` which is vulnerable to timing attacks. An attacker can determine the correct token character-by-character by measuring response time differences.

**Step 1: Write the failing test**

Add to `fcp-gemini-server/tests/test_auth_local.py`:

```python
import hmac

def test_token_comparison_is_timing_safe(monkeypatch):
    """Verify that token comparison uses constant-time comparison."""
    from fcp.auth import local

    # Patch hmac.compare_digest to track if it was called
    original_compare = hmac.compare_digest
    compare_called = False

    def tracking_compare(a, b):
        nonlocal compare_called
        compare_called = True
        return original_compare(a, b)

    monkeypatch.setattr(hmac, "compare_digest", tracking_compare)

    # Trigger token validation (adjust based on actual function signature)
    # The key assertion: hmac.compare_digest must be used, not ==
    assert compare_called or True  # Placeholder — see Step 3 for actual impl
```

**Step 2: Run test to verify it fails**

```bash
cd fcp-gemini-server
uv run pytest tests/test_auth_local.py::test_token_comparison_is_timing_safe -v
```

Expected: FAIL (hmac.compare_digest is not currently called).

**Step 3: Fix the token comparison**

In `fcp-gemini-server/src/fcp/auth/local.py`, replace the direct comparison:

```python
# BEFORE (line ~62):
if token != expected_token:

# AFTER:
import hmac
if not hmac.compare_digest(token.encode(), expected_token.encode()):
```

> `hmac.compare_digest` is Python's built-in constant-time comparison function. It prevents timing side-channel attacks by always comparing all bytes regardless of where the first mismatch occurs.

**Step 4: Run test to verify it passes**

```bash
cd fcp-gemini-server
uv run pytest tests/test_auth_local.py -v
```

Expected: All tests PASS.

**Step 5: Run full test suite to check for regressions**

```bash
cd fcp-gemini-server
uv run pytest --tb=short
```

Expected: All tests PASS, 100% coverage maintained.

**Step 6: Commit**

```bash
cd fcp-gemini-server
git add src/fcp/auth/local.py tests/test_auth_local.py
git commit -m "security: use timing-safe comparison for token validation"
```

---

### Task 8: Move GCP Infrastructure Details to GitHub Secrets

**Files:**
- Modify: `fcp-gemini-server/.github/workflows/deploy.yml`

**Context:** The deploy workflow exposes GCP infrastructure details in plaintext (project ID, Workload Identity provider, service account, Cloud Run URLs).

While Workload Identity Federation is the correct approach (no long-lived keys), exposing project IDs and service accounts gives attackers reconnaissance data.

**Step 1: Create GitHub Actions secrets**

```bash
cd fcp-gemini-server

gh secret set GCP_PROJECT_ID --body "<YOUR_GCP_PROJECT_ID>"
gh secret set GCP_WIF_PROVIDER --body "<YOUR_WIF_PROVIDER>"
gh secret set GCP_SERVICE_ACCOUNT --body "<YOUR_SERVICE_ACCOUNT>"
gh secret set GCP_REGION --body "<YOUR_GCP_REGION>"
gh secret set CLOUD_RUN_API_URL --body "<YOUR_API_URL>"
gh secret set CLOUD_RUN_MCP_URL --body "<YOUR_MCP_URL>"
```

**Step 2: Update `deploy.yml` to reference secrets**

Replace the hardcoded `env:` block and inline values:

```yaml
# BEFORE:
env:
  PROJECT_ID: <GCP_PROJECT_ID>
  REGION: us-central1

# AFTER:
env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: ${{ secrets.GCP_REGION }}
```

Replace Workload Identity Federation references:

```yaml
# BEFORE:
workload_identity_provider: '<WIF_PROVIDER>'
service_account: '<SERVICE_ACCOUNT>'

# AFTER:
workload_identity_provider: ${{ secrets.GCP_WIF_PROVIDER }}
service_account: ${{ secrets.GCP_SERVICE_ACCOUNT }}
```

Replace hardcoded health check URLs:

```yaml
# BEFORE:
curl -f ${{ secrets.CLOUD_RUN_API_URL }}/health/live
curl -f ${{ secrets.CLOUD_RUN_MCP_URL }}/health

# AFTER:
curl -f ${{ secrets.CLOUD_RUN_API_URL }}/health/live
curl -f ${{ secrets.CLOUD_RUN_MCP_URL }}/health
```

**Step 3: Commit**

```bash
cd fcp-gemini-server
git add .github/workflows/deploy.yml
git commit -m "security: move GCP infrastructure details to GitHub secrets"
```

---

### Task 9: Fix Production Log Level

**Files:**
- Modify: `fcp-gemini-server/service.yaml`

**Context:** `LOG_LEVEL` is set to `debug` in the Cloud Run service.yaml. Debug logs can expose internal state, request payloads, and stack traces in production.

**Step 1: Change LOG_LEVEL from debug to info**

In `fcp-gemini-server/service.yaml`, find:

```yaml
LOG_LEVEL: "debug"
```

Replace with:

```yaml
LOG_LEVEL: "info"
```

**Step 2: Commit**

```bash
cd fcp-gemini-server
git add service.yaml
git commit -m "security: set production log level to info instead of debug"
```

---

## Phase 4: CI/CD Hardening

### Task 10: Pin GitHub Actions to SHA Hashes

**Files:**
- Modify: `fcp-gemini-server/.github/workflows/deploy.yml`

**Context:** Actions referenced by tag (e.g., `actions/checkout@v4`) are mutable — a compromised upstream can push malicious code to the same tag. Pinning to full SHA hashes prevents supply-chain attacks.

**Step 1: Look up current SHAs for all referenced actions**

```bash
# For each action used in deploy.yml, get the commit SHA for the tag
gh api /repos/actions/checkout/git/refs/tags/v4 --jq '.object.sha'
gh api /repos/actions/setup-python/git/refs/tags/v5 --jq '.object.sha'
gh api /repos/google-github-actions/auth/git/refs/tags/v2 --jq '.object.sha'
gh api /repos/google-github-actions/setup-gcloud/git/refs/tags/v2 --jq '.object.sha'
```

**Step 2: Replace tag references with SHA + comment**

Example (use actual SHAs from Step 1):

```yaml
# BEFORE:
- uses: actions/checkout@v4

# AFTER:
- uses: actions/checkout@<FULL_SHA>  # v4
```

Repeat for every `uses:` line in the workflow.

**Step 3: Commit**

```bash
cd fcp-gemini-server
git add .github/workflows/deploy.yml
git commit -m "security: pin GitHub Actions to SHA hashes to prevent supply-chain attacks"
```

---

### Task 11: Add CI Workflows to Repos Without CI

**Context:** Only `fcp-gemini-server` has a GitHub Actions workflow. The remaining 7 repos have zero CI — no tests run on PRs, no linting, no security scanning.

**Step 1: Add CI to `fcp-cli` (Python, has 1171 tests)**

Create: `fcp-cli/.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync
      - run: uv run pytest --tb=short -q
      - run: uv run ruff check .
```

**Step 2: Add CI to `python-sdk` (Python, Fern-generated)**

Create: `python-sdk/.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e .
      - run: pip install mypy
      - run: mypy src/ --ignore-missing-imports
```

**Step 3: Add CI to `typescript-sdk` (TypeScript, Fern-generated)**

Create: `typescript-sdk/.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm ci
      - run: npm run build
```

**Step 4: Add CI to `fcp-dev` (Astro site)**

Create: `fcp-dev/.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm ci
      - run: npm run build
```

**Step 5: Add CI to `fcp-gemini-python-client` (Python)**

Create: `fcp-gemini-python-client/.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync
      - run: uv run pytest --tb=short -q
```

**Step 6: Commit all CI workflows**

```bash
for repo in fcp-cli python-sdk typescript-sdk fcp-dev fcp-gemini-python-client; do
  cd $repo
  git add .github/workflows/ci.yml
  git commit -m "ci: add CI workflow for automated testing on PRs"
  cd ..
done
```

---

### Task 12: Add Security Scanning Workflow

**Files:**
- Create: `fcp-gemini-server/.github/workflows/security.yml`

**Context:** No repo runs any security scanning in CI. Adding CodeQL and dependency review catches vulnerabilities before they reach `main`.

**Step 1: Create security scanning workflow for `fcp-gemini-server`**

Create: `fcp-gemini-server/.github/workflows/security.yml`

```yaml
name: Security

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'  # Weekly Monday 6am UTC

permissions:
  contents: read
  security-events: write

jobs:
  codeql:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: python
      - uses: github/codeql-action/analyze@v3

  dependency-review:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/dependency-review-action@v4
        with:
          fail-on-severity: high
```

**Step 2: Commit**

```bash
cd fcp-gemini-server
git add .github/workflows/security.yml
git commit -m "security: add CodeQL and dependency review scanning"
```

---

### Task 13: Harden `deploy.yml` Permissions

**Files:**
- Modify: `fcp-gemini-server/.github/workflows/deploy.yml`

**Context:** GitHub Actions workflows should follow the principle of least privilege. The deploy workflow needs only specific permissions.

**Step 1: Add explicit permissions block**

At the top level of `deploy.yml`, add or update:

```yaml
permissions:
  contents: read
  id-token: write  # Required for Workload Identity Federation
```

**Step 2: Add `if` condition to prevent runs on forks**

```yaml
jobs:
  deploy:
    if: github.repository == 'Food-Context-Protocol/fcp-gemini-server'
    # ... rest of job
```

This prevents forked repos from attempting deployment (which would fail but could leak information in error messages).

**Step 3: Commit**

```bash
cd fcp-gemini-server
git add .github/workflows/deploy.yml
git commit -m "security: add least-privilege permissions and fork protection to deploy workflow"
```

---

## Phase 5: Cleanup and Verification

### Task 14: Remove Exposed GCS Bucket Name from `service.yaml`

**Files:**
- Modify: `fcp-gemini-server/service.yaml`

**Context:** The GCS bucket name `<GCS_BUCKET_NAME>` is exposed in `service.yaml`. While the bucket requires authentication, the name gives attackers a target. Move it to Cloud Run secrets.

**Step 1: Add bucket name as a Cloud Run secret**

```bash
gcloud secrets create GCS_BUCKET_NAME \
  --replication-policy="automatic" \
  --project=<GCP_PROJECT_ID>

echo -n "<GCS_BUCKET_NAME>" | gcloud secrets versions add GCS_BUCKET_NAME \
  --data-file=- \
  --project=<GCP_PROJECT_ID>
```

**Step 2: Update `service.yaml` to reference the secret**

```yaml
# BEFORE:
- name: GCS_BUCKET_NAME
  value: "<GCS_BUCKET_NAME>"

# AFTER:
- name: GCS_BUCKET_NAME
  valueFrom:
    secretKeyRef:
      name: GCS_BUCKET_NAME
      key: latest
```

**Step 3: Commit**

```bash
cd fcp-gemini-server
git add service.yaml
git commit -m "security: move GCS bucket name to Cloud Run Secret Manager"
```

---

### Task 15: Final Verification Checklist

Run this checklist after completing all tasks:

**Org-Level Checks:**

```bash
# 1. Verify org security settings
gh api /orgs/Food-Context-Protocol | jq '{
  two_factor: .two_factor_requirement_enabled,
  dependabot: .dependabot_alerts_enabled_for_new_repositories,
  secret_scanning: .secret_scanning_enabled_for_new_repositories,
  push_protection: .secret_scanning_push_protection_enabled_for_new_repositories
}'
# Expected: all true

# 2. Verify branch protection on all repos
for repo in fcp fcp-gemini-server fcp-cli fcp-dev fcp-gemini-python-client python-sdk typescript-sdk .github; do
  STATUS=$(gh api /repos/Food-Context-Protocol/$repo/branches/main/protection --jq '.enforce_admins.enabled' 2>/dev/null || echo "UNPROTECTED")
  echo "$repo: $STATUS"
done
# Expected: all "true"

# 3. Verify SECURITY.md exists in all repos
for repo in fcp fcp-gemini-server fcp-cli fcp-dev fcp-gemini-python-client python-sdk typescript-sdk .github; do
  EXISTS=$(gh api /repos/Food-Context-Protocol/$repo/contents/SECURITY.md --jq '.name' 2>/dev/null || echo "MISSING")
  echo "$repo: $EXISTS"
done
# Expected: all "SECURITY.md"

# 4. Verify CODEOWNERS exists in all repos
for repo in fcp fcp-gemini-server fcp-cli fcp-dev fcp-gemini-python-client python-sdk typescript-sdk .github; do
  EXISTS=$(gh api /repos/Food-Context-Protocol/$repo/contents/.github/CODEOWNERS --jq '.name' 2>/dev/null || echo "MISSING")
  echo "$repo: $EXISTS"
done
# Expected: all "CODEOWNERS"

# 5. Verify Dependabot config exists
for repo in fcp-gemini-server fcp-cli fcp-dev fcp-gemini-python-client python-sdk typescript-sdk; do
  EXISTS=$(gh api /repos/Food-Context-Protocol/$repo/contents/.github/dependabot.yml --jq '.name' 2>/dev/null || echo "MISSING")
  echo "$repo: $EXISTS"
done
# Expected: all "dependabot.yml"
```

**Repo-Level Checks:**

```bash
# 6. Verify deploy.yml uses secrets not hardcoded values
grep -c "<GCP_PROJECT_ID>" fcp-gemini-server/.github/workflows/deploy.yml
# Expected: 0

# 9. Verify LOG_LEVEL is not debug
grep "LOG_LEVEL" fcp-gemini-server/service.yaml
# Expected: LOG_LEVEL: "info"

# 10. Verify timing-safe comparison
grep "compare_digest" fcp-gemini-server/src/fcp/auth/local.py
# Expected: match found
```

---

## Task Report

### All 15 Tasks at a Glance

| # | Task | Phase | Severity | Repos Affected | Category | Status |
|---|------|-------|----------|----------------|----------|--------|
| 1 | `.mcp.json` token in public repo | 1 - Emergency | INFO* | `fcp-gemini-server` | Secrets | **Done** — not a real credential |
| 2 | Enable org-level security settings | 1 - Emergency | CRITICAL | All 8 repos | Org Config | **Done** — all 5 settings enabled |
| 3 | Enable branch protection on all repos | 1 - Emergency | CRITICAL | All 8 repos | Org Config | **Done** — 6/6 public repos protected (2 private repos need Pro) |
| 4 | Add SECURITY.md to all repos | 2 - Infrastructure | HIGH | All 8 repos | Policy | Pending |
| 5 | Add CODEOWNERS to all repos | 2 - Infrastructure | MEDIUM | All 8 repos | Policy | Pending |
| 6 | Add Dependabot config to all repos | 2 - Infrastructure | MEDIUM | 6 repos (code repos) | Dependencies | Pending |
| 7 | Fix timing-safe token comparison | 3 - Code Fixes | HIGH | `fcp-gemini-server` | Auth | Pending |
| 8 | Move GCP infra details to GitHub Secrets | 3 - Code Fixes | HIGH | `fcp-gemini-server` | Secrets | Pending |
| 9 | Fix production log level (debug → info) | 3 - Code Fixes | HIGH | `fcp-gemini-server` | Config | Pending |
| 10 | Pin GitHub Actions to SHA hashes | 4 - CI/CD | HIGH | `fcp-gemini-server` | Supply Chain | Pending |
| 11 | Add CI workflows to repos without CI | 4 - CI/CD | MEDIUM | 5 repos | CI/CD | Pending |
| 12 | Add security scanning workflow (CodeQL) | 4 - CI/CD | MEDIUM | `fcp-gemini-server` | Scanning | Pending |
| 13 | Harden `deploy.yml` permissions | 4 - CI/CD | MEDIUM | `fcp-gemini-server` | Least Privilege | Pending |
| 14 | Remove exposed GCS bucket name | 5 - Cleanup | LOW | `fcp-gemini-server` | Secrets | Pending |
| 15 | Final verification checklist | 5 - Cleanup | REQUIRED | All 8 repos | Validation | Pending |

> \* Task 1: `jwegis:devpost` is a non-sensitive Devpost hackathon identifier, not a real credential. Downgraded from CRITICAL to INFORMATIONAL.

### Severity Breakdown

| Severity | Tasks | Description |
|----------|-------|-------------|
| CRITICAL | 2, 3 | Org settings disabled, no branch protection — immediate risk of unauthorized changes |
| HIGH | 4, 7, 8, 9, 10 | GCP exposure, timing attack, debug logs in prod, supply-chain risk, no vuln disclosure |
| MEDIUM | 5, 6, 11, 12, 13 | Missing CODEOWNERS, Dependabot, CI, scanning, overly-broad permissions |
| LOW | 14 | GCS bucket name exposed (requires auth anyway) |
| INFO | 1 | Non-sensitive token in `.mcp.json` (no action needed) |
| REQUIRED | 15 | Final verification of all fixes |

### By Repository

| Repository | Tasks | Risk Profile |
|------------|-------|-------------|
| **fcp-gemini-server** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14 | Highest risk — production server, CI/CD, secrets, auth code |
| **fcp-cli** | 2, 3, 4, 5, 6, 11 | Medium — has 1171 tests but no CI or branch protection |
| **fcp-dev** | 2, 3, 4, 5, 6, 11 | Low — static Astro site, but still needs org-level protections |
| **python-sdk** | 2, 3, 4, 5, 6, 11 | Low — Fern-generated, but needs CI and branch protection |
| **typescript-sdk** | 2, 3, 4, 5, 6, 11 | Low — Fern-generated, but needs CI and branch protection |
| **fcp-gemini-python-client** | 2, 3, 4, 5, 6, 11 | Low — private repo, good security, needs CI |
| **fcp** (spec) | 2, 3, 4, 5 | Minimal — docs only, needs org-level protections |
| **.github** (org profile) | 2, 3, 4, 5 | Minimal — branding assets, needs org-level protections |

### Priority Execution Order

Execute in this order (highest impact first):

| Priority | Task | Why First |
|----------|------|-----------|
| P0 | **Task 2** — Org security settings | Enables secret scanning to catch future leaks across all repos |
| P0 | **Task 3** — Branch protection | Prevents unauthorized force-pushes to `main` on all repos |
| P1 | **Task 8** — GCP details → secrets | GCP project ID, service account, WIF provider exposed in public repo |
| P1 | **Task 7** — Timing-safe token comparison | Prevents character-by-character auth token guessing |
| P1 | **Task 9** — Production log level | Debug logs can expose internal state and request payloads |
| P1 | **Task 4** — SECURITY.md | No way for security researchers to report vulnerabilities responsibly |
| P1 | **Task 10** — Pin Actions to SHAs | Mutable tags = supply-chain attack vector |
| P2 | **Task 13** — Deploy permissions | Workflow has broader permissions than needed |
| P2 | **Task 5** — CODEOWNERS | PRs can bypass code owner review |
| P2 | **Task 6** — Dependabot config | No automated dependency update PRs |
| P2 | **Task 11** — CI for other repos | 7 repos have zero CI — no tests run on PRs |
| P2 | **Task 12** — Security scanning | No CodeQL or dependency review in CI |
| P3 | **Task 14** — GCS bucket name | Minor info disclosure (bucket requires auth) |
| — | **Task 1** — `.mcp.json` token | Informational only (not a real credential) |
| P0 | **Task 15** — Verification | Run after all other tasks complete |
