# FCP Devpost Submission Checklist

**Competition:** Google Gemini 3 API Developer Competition
**Deadline:** February 9, 2026 at 5:00 PM PT
**Project:** Food Context Protocol (FCP) - AI-Powered Food Intelligence Platform

---

## ✅ Completed Preparation

### Codebase & Infrastructure
- [x] **100% Test Coverage** - 2,506 passing tests, 0 failures
- [x] **Legal Compliance** - Comprehensive disclaimers in LEGAL.md, updated README and API docs
- [x] **FoodLog Cleanup** - All legacy references removed, rebranded to FCP
- [x] **GitHub Organization** - 6 repositories under Food-Context-Protocol
  - [x] fcp (specification)
  - [x] fcp-gemini-server (reference implementation)
  - [x] fcp-cli (command-line tool)
  - [x] python-sdk (auto-generated)
  - [x] typescript-sdk (auto-generated)
  - [x] fcp-dev (landing page - private)
- [x] **Landing Page** - https://fcp.dev deployed to Cloudflare Pages
- [x] **Environment Variables** - All FOODLOG_* → FCP_*
- [x] **SDKs Regenerated** - Clean Fern-generated Python & TypeScript SDKs
- [x] **Documentation** - Comprehensive docs in all repos

### Gemini 3 Integration
- [x] **42 MCP Tools** - All using Gemini 3 Flash & Pro
- [x] **Feature Audit** - 15+ features documented in `docs/gemini-feature-audit.md`
- [x] **Tool Registry** - 5 tools migrated to new decorator-based system

---

## 🎯 Critical Path - Must Complete Before Submission

**Estimated Time: 6 hours**

### 1. Deploy to Google Cloud Run (2 hours)

**Status:** Not started
**Priority:** P0 - BLOCKING

**Steps:**
```bash
# 1. Authenticate with Google Cloud
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. Deploy to Cloud Run
gcloud run deploy fcp-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY,DATABASE_BACKEND=sqlite \
  --memory 1Gi \
  --timeout 60s

# 3. Get the URL (save this!)
gcloud run services describe fcp-api --region us-central1 --format 'value(status.url)'
```

**Success Criteria:**
- [ ] Service deployed and URL obtained
- [ ] `/health` endpoint returns 200
- [ ] `/mcp/v1/tools/list` returns 42+ tools
- [ ] Test 2-3 key tools via HTTP POST

**Reference:** See `docs/CLOUD_RUN_DEPLOYMENT_PLAN.md` for detailed guide

---

### 2. Configure DNS (30 minutes)

**Status:** Waiting for Cloud Run URL
**Priority:** P0 - BLOCKING

**Steps:**
1. Log into Cloudflare dashboard
2. Select domain: fcp.dev
3. Add DNS record:
   - Type: CNAME
   - Name: api
   - Target: [Cloud Run URL from step 1]
   - Proxy status: Proxied (orange cloud)
   - TTL: Auto
4. Wait 5-30 minutes for DNS propagation
5. Test: `curl https://api.fcp.dev/health`

**Success Criteria:**
- [ ] https://api.fcp.dev/health returns 200
- [ ] SSL certificate valid (Cloudflare auto-provisions)
- [ ] CORS headers present for cross-origin requests

---

### 3. Record Demo Video (2.5 hours)

**Status:** Script ready in `docs/video-script.md`
**Priority:** P1 - Required for submission

**Requirements:**
- Length: Under 3 minutes (2:45-2:55 ideal)
- Format: MP4, 1080p, 30fps
- Content: Live demo showing Gemini 3 features

**Filming Plan:**
1. **Intro** (15 sec) - FCP overview, GitHub link, live demo URL
2. **Live Demo** (2:15 min) - Show 4-5 key features:
   - Meal logging with image analysis
   - Recipe generation from pantry
   - Allergen detection
   - Nutritional insights
   - Business intelligence tools
3. **Outro** (15 sec) - Call to action, fcp.dev link

**Tools:**
- Screen recording: QuickTime (macOS) or OBS Studio
- Video editing: iMovie or DaVinci Resolve
- Voiceover: Built-in screen recording audio

**Success Criteria:**
- [ ] Video under 3 minutes
- [ ] Shows live api.fcp.dev demo
- [ ] Highlights Gemini 3 integration
- [ ] Clear audio and visuals
- [ ] Saved as MP4 file

**Reference:** See `docs/video-script.md` for detailed script

---

### 4. Upload to YouTube (30 minutes)

**Status:** Waiting for video
**Priority:** P1 - Required for submission

**Steps:**
1. Go to youtube.com/upload
2. Upload MP4 file
3. Configure:
   - **Title:** "FCP - AI-Powered Food Intelligence | Gemini 3 API Competition"
   - **Description:**
     ```
     Food Context Protocol (FCP) - An open protocol for food intelligence powered by Google's Gemini 3 API.

     Live Demo: https://api.fcp.dev
     GitHub: https://github.com/Food-Context-Protocol
     Landing Page: https://fcp.dev

     Built for the Google Gemini 3 API Developer Competition (February 2026)

     Features 42+ MCP tools for meal logging, recipe generation, allergen detection,
     nutritional insights, and business intelligence - all powered by Gemini 3 Flash & Pro.
     ```
   - **Visibility:** Unlisted
   - **Thumbnail:** Custom (use FCP logo + "Gemini 3" badge)
4. Copy video URL

**Success Criteria:**
- [ ] Video uploaded and processing complete
- [ ] Unlisted visibility set
- [ ] Description includes all links
- [ ] Custom thumbnail uploaded
- [ ] Video URL copied for Devpost submission

---

### 5. Make Repositories Public (15 minutes)

**Status:** Ready to execute
**Priority:** P1 - Do at submission time

⚠️ **IMPORTANT:** Do this IMMEDIATELY BEFORE Devpost submission to avoid early discovery

**Steps:**
1. Navigate to each repo settings:
   - https://github.com/Food-Context-Protocol/fcp/settings
   - https://github.com/Food-Context-Protocol/fcp-gemini-server/settings
   - https://github.com/Food-Context-Protocol/fcp-cli/settings
   - https://github.com/Food-Context-Protocol/python-sdk/settings
   - https://github.com/Food-Context-Protocol/typescript-sdk/settings

2. For each repo:
   - Scroll to "Danger Zone"
   - Click "Change visibility"
   - Select "Make public"
   - Confirm by typing repository name

3. Verify no secrets in git history:
   ```bash
   # Run in each repo
   git log --all --full-history --source --grep="API_KEY\|SECRET\|PASSWORD\|TOKEN"
   git log --all --full-history --source -S "firebase" -S "credentials" --pickaxe-regex
   ```

**Success Criteria:**
- [ ] All 5 repos public
- [ ] No secrets found in git history
- [ ] README badges show public repo status
- [ ] All repos accessible without GitHub login

---

### 6. Submit to Devpost (1 hour)

**Status:** Ready to execute
**Priority:** P0 - Final step

**Submission URL:** https://googlegemini3.devpost.com

**Required Fields:**

| Field | Value |
|-------|-------|
| **Project Name** | Food Context Protocol (FCP) |
| **Tagline** | AI-powered food intelligence platform with 42+ Gemini 3 tools |
| **Category** | Gemini 3 API |
| **Built With** | Python, FastAPI, Gemini 3 Flash, Gemini 3 Pro, MCP, SQLite |
| **Try it out** | https://api.fcp.dev |
| **Source Code** | https://github.com/Food-Context-Protocol |
| **Video URL** | [YouTube URL from step 4] |

**200-Word Description:**

Use the competition-optimized description from `docs/gemini-feature-audit.md`:

```
Food Context Protocol (FCP) is an open protocol for food intelligence powered by Google's Gemini 3 API. FCP provides a standardized interface for meal logging, recipe generation, nutritional analysis, and food safety - accessible through 42+ MCP tools.

Gemini 3 Integration:
• Flash (Rapid Analysis): Real-time meal parsing, recipe scaling, allergen detection, pantry management
• Pro (Deep Intelligence): Multi-modal recipe extraction from images/PDFs, dietary compatibility analysis, personalized nutrition insights
• Flash-Thinking: Complex meal planning with constraint satisfaction

Key Features (15+):
1. Multi-modal Recipe Extraction - Extract recipes from images, PDFs, videos
2. Allergen & Drug Interaction Detection - Real-time safety alerts
3. Pantry Intelligence - Automated inventory tracking with expiry warnings
4. Personalized Nutrition - AI-powered meal suggestions based on history
5. Business Intelligence - Economic gap detection, food waste analysis
6. Restaurant Safety - Real-time health inspection data
7. Cottage Food Labeling - Compliant label generation
8. Multi-language Support - Recipe translation across 100+ languages

Built with: Python, FastAPI, Gemini 3 Flash/Pro, MCP Protocol, SQLite
Open Source: Apache 2.0
Live Demo: https://api.fcp.dev
```

**Submission Checklist:**
- [ ] All required fields filled
- [ ] Description under 200 words
- [ ] Video uploaded and URL added
- [ ] GitHub link works (repos are public)
- [ ] Demo URL works (api.fcp.dev)
- [ ] Screenshots uploaded (4-6 images)
- [ ] Team members added (if applicable)
- [ ] Submission saved as draft
- [ ] Final review completed
- [ ] **SUBMIT** before 5:00 PM PT

---

## 📊 Current Repository Status

| Repository | Status | Tests | Coverage |
|------------|--------|-------|----------|
| fcp-gemini-server | ✅ Ready | 2,506 passing | 100% |
| fcp-cli | ✅ Ready | N/A | N/A |
| fcp | ✅ Ready | N/A | Specification |
| python-sdk | ✅ Ready | Auto-generated | N/A |
| typescript-sdk | ✅ Ready | Auto-generated | N/A |

---

## 🚨 Pre-Submission Verification

**Run these checks before submitting:**

```bash
# 1. Test local server
make test
make run-http
curl http://localhost:8080/health

# 2. Test Cloud Run deployment
curl https://api.fcp.dev/health
curl https://api.fcp.dev/mcp/v1/tools/list | jq '.tools | length'

# 3. Verify GitHub repos are public
curl https://api.github.com/repos/Food-Context-Protocol/fcp
curl https://api.github.com/repos/Food-Context-Protocol/fcp-gemini-server

# 4. Check landing page
curl -I https://fcp.dev

# 5. Verify video is unlisted and accessible
# Open YouTube URL in incognito window
```

**Expected Results:**
- ✅ All tests pass
- ✅ Local server returns 200
- ✅ Cloud Run returns 200 with 42+ tools
- ✅ GitHub API returns public repo data
- ✅ Landing page returns 200
- ✅ Video plays without login

---

## 📝 Post-Submission Roadmap

**Complete after Devpost submission to build production-ready protocol**

### Phase 1: Repository Cleanup & Documentation (1 week)

#### Git Repository Hygiene
- [ ] **Clean git histories** - Remove accidentally committed secrets/files
  - Review all repos for sensitive data in history
  - Use `git filter-repo` or BFG Repo-Cleaner if needed
  - Verify with `git log --all --full-history --source -S "API_KEY"`

- [ ] **Squash histories** - Clean up commit history
  - Squash "WIP", "fix typo", "formatting" commits
  - Keep meaningful commits with clear messages
  - Rebase feature branches before merging
  - Document in `.github/CONTRIBUTING.md`

#### Core Documentation Files
- [ ] **Create GEMINI.md** - Gemini integration guide
  - Document all 42 tools using Gemini 3
  - Flash vs Pro usage patterns
  - Prompt engineering best practices
  - Token optimization strategies
  - Error handling and rate limits
  - Example code snippets

- [ ] **Create AGENTS.md** - Agent development guide
  - MCP agent architecture overview
  - Tool registry and decorator system
  - Dependency injection patterns
  - Testing strategies for agents
  - Creating custom agents
  - Agent orchestration patterns

- [ ] **Create CLAUDE.md** - Claude-specific guidance
  - How to use FCP with Claude Desktop
  - MCP server configuration
  - Tool usage examples
  - Best practices for Claude integration
  - Troubleshooting common issues

#### Documentation Infrastructure
- [ ] **Set up docs.fcp.dev** - Dedicated documentation site
  - Framework: Docusaurus, VitePress, or Astro
  - Sections:
    - Getting Started
    - API Reference (auto-generated from OpenAPI)
    - MCP Tools Catalog
    - Integration Guides (Claude, Gemini, Custom)
    - Architecture Docs
    - Contributing Guide
  - Deploy to Cloudflare Pages or Vercel
  - Custom domain: docs.fcp.dev

- [ ] **Set up mcp.fcp.dev** - MCP server demo/playground
  - Interactive MCP server for testing tools
  - Real-time tool execution playground
  - WebSocket or SSE connection demo
  - Tool response visualization
  - Example requests/responses for all 42+ tools
  - Claude Desktop integration instructions
  - Deploy to Cloud Run with public endpoint
  - Custom domain: mcp.fcp.dev

- [ ] **Update fcp.dev landing page** - Enhance after submission
  - Replace placeholder content with full feature showcase
  - Add live demo links (api.fcp.dev, mcp.fcp.dev, docs.fcp.dev)
  - Add Devpost badge and competition results
  - Add "Built with Gemini 3" hero section
  - Add screenshots/GIFs of key features
  - Add community links (GitHub, Discord/Slack)
  - Add getting started CTA
  - Add testimonials/use cases (once available)
  - Optimize for SEO (meta tags, Open Graph)

- [ ] **Review FCP specification** - Polish the protocol spec
  - Review `fcp` repo specification for completeness
  - Ensure all 42 tools are documented
  - Add data model schemas (JSON Schema)
  - Document versioning strategy
  - Add extension mechanism documentation
  - Professional formatting and diagrams
  - Review by domain experts

---

### Phase 2: Future Features Planning (2-3 weeks)

#### FoodLoop - Community Recipe Sharing
- [ ] **Design FoodLoop architecture**
  - User-generated recipe sharing platform
  - Social features: likes, comments, follows
  - Recipe collections and meal plans
  - Integration with FCP tools
  - Privacy controls and moderation

- [ ] **FoodLoop MVP scope**
  - Core features: share, discover, save recipes
  - Authentication and user profiles
  - Recipe rating system
  - Search and filtering
  - Mobile-responsive web interface

- [ ] **FoodLoop technical spec**
  - Database schema for social features
  - API endpoints for community features
  - Caching strategy for popular content
  - CDN for recipe images
  - Moderation tools and workflows

#### FoodFeed - Personalized Nutrition Insights
- [ ] **Design FoodFeed architecture**
  - Personalized daily nutrition feed
  - AI-powered meal suggestions
  - Trend analysis and insights
  - Weekly/monthly reports
  - Integration with wearables (future)

- [ ] **FoodFeed MVP scope**
  - Daily digest of user's nutrition
  - Personalized recommendations
  - Goal tracking (calorie, protein, etc.)
  - Historical trends and charts
  - Email/push notifications

- [ ] **FoodFeed technical spec**
  - Background job architecture
  - Data aggregation pipelines
  - Notification system
  - Real-time vs batch processing
  - A/B testing framework for recommendations

#### Diet Management - Dietary Restrictions & Goals
- [ ] **Design Diet feature architecture**
  - Flexible dietary profiles (vegan, keto, etc.)
  - Custom nutrition goals
  - Meal planning with constraints
  - Shopping list generation
  - Meal prep scheduling

- [ ] **Diet MVP scope**
  - Dietary preference profiles
  - Goal setting and tracking
  - Constraint-based meal suggestions
  - Weekly meal plans
  - Progress reports

- [ ] **Diet technical spec**
  - Constraint satisfaction algorithms
  - Recipe compatibility scoring
  - Nutrition optimization engine
  - Integration with existing tools
  - Personalization ML models

---

### Phase 3: CI/CD & Development Workflow (1 week)

#### GitHub Actions Workflows
- [ ] **Review existing workflows**
  - Audit all `.github/workflows/*.yml` files
  - Remove unused/duplicate workflows
  - Document workflow purposes
  - Optimize for speed and cost

- [ ] **Standard CI workflow** - `.github/workflows/ci.yml`
  ```yaml
  name: CI
  on: [push, pull_request]
  jobs:
    test:
      - Run linting (ruff)
      - Run type checking (mypy)
      - Run tests (pytest)
      - Upload coverage (codecov)
    build:
      - Build Docker image
      - Push to registry (on main)
  ```

- [ ] **Linting workflow**
  - Use `ruff` for Python linting
  - Use `prettier` for JSON/YAML/Markdown
  - Fail on errors, warn on style issues
  - Auto-fix on pre-commit when possible

- [ ] **Type checking workflow**
  - Run `mypy` with strict mode
  - Check all Python source files
  - Fail on type errors
  - Allow gradual typing with `# type: ignore` comments

- [ ] **Test & Coverage workflow**
  - Run full test suite with `pytest`
  - Generate coverage report
  - Enforce minimum coverage (current: 100%)
  - Upload to Codecov or Coveralls
  - Fail if coverage drops below threshold
  - Matrix testing: Python 3.11, 3.12, 3.13

- [ ] **Deployment workflow** - `.github/workflows/deploy.yml`
  - Trigger on tag push (e.g., `v1.0.0`)
  - Build and push Docker image
  - Deploy to Cloud Run
  - Run smoke tests on production
  - Rollback on failure

- [ ] **Documentation workflow** - `.github/workflows/docs.yml`
  - Build documentation site
  - Deploy to docs.fcp.dev
  - Check for broken links
  - Generate API docs from OpenAPI spec

#### Development Process Documentation
- [ ] **Create .github/CONTRIBUTING.md**
  - Development setup guide
  - Branch naming conventions
  - Commit message format
  - PR checklist and review process
  - Code style guidelines

- [ ] **Create .github/PULL_REQUEST_TEMPLATE.md**
  - PR description template
  - Checklist: tests, docs, changelog
  - Related issues

- [ ] **Create .github/ISSUE_TEMPLATE/**
  - Bug report template
  - Feature request template
  - Documentation improvement template

---

### Phase 4: Technical Debt (2-3 weeks)

- [ ] **Registry refactoring** - Migrate 38 remaining tools
  - See `docs/technical-debt/TOOL_REGISTRY_DETAILED_PLAN.md`
  - Estimated: ~24 hours
  - Reduces dispatcher from 626 to ~100 lines

- [ ] **Review 123 skipped tests**
  - Categorize: Not implemented, Not applicable, Future feature
  - Implement missing functionality or remove test
  - Document decisions in test file comments

- [ ] **Fix interface mismatches**
  - Database protocol: `save_recipe` vs `create_recipe`
  - Align protocol definitions with implementations
  - Update all call sites

- [ ] **Remove duplicate functions**
  - `add_to_pantry` in both crud.py and inventory.py
  - Consolidate to single implementation
  - Update all imports

- [ ] **Production authentication**
  - Implement OAuth 2.1 flow
  - JWT token management
  - Rate limiting
  - User isolation
  - See `docs/technical-debt/authentication-architecture.md`

---

### Phase 5: Community & Marketing (Ongoing)

- [ ] **Tweet Announcement**
  - Share GitHub repo
  - Tag @googledevs @GoogleAI
  - Use #GeminiAPI #GenAI #FCP

- [ ] **Update README Badges**
  - Add "Devpost Submission" badge
  - Add "Built with Gemini 3" badge
  - Add CI status badge
  - Add coverage badge
  - Add license badge

- [ ] **Create GitHub Release**
  - Tag: v1.0.0-hackathon
  - Release notes with Devpost link
  - Changelog of features

- [ ] **Blog Post / Dev.to Article**
  - "Building FCP: An Open Protocol for Food Intelligence"
  - Technical deep-dive
  - Lessons learned
  - Community call-to-action

- [ ] **Submit to Product Hunt**
  - Once docs.fcp.dev is ready
  - Prepare screenshots and demo
  - Community launch

- [ ] **Create Demo Videos**
  - Individual feature tutorials
  - Integration guides
  - Developer onboarding

---

### Success Metrics

**Phase 1 Complete:**
- ✅ All repos have clean histories
- ✅ GEMINI.md, AGENTS.md, CLAUDE.md published
- ✅ docs.fcp.dev live with full documentation
- ✅ FCP specification is professional-grade

**Phase 2 Complete:**
- ✅ Technical specs for FoodLoop, FoodFeed, Diet features
- ✅ Roadmap published and prioritized
- ✅ Community feedback collected

**Phase 3 Complete:**
- ✅ All CI/CD workflows passing on main
- ✅ 100% test coverage maintained
- ✅ < 10 minute CI pipeline
- ✅ Automated deployments working

**Phase 4 Complete:**
- ✅ Registry refactoring done (43/43 tools migrated)
- ✅ All skipped tests resolved
- ✅ Zero TODO/FIXME in production code
- ✅ Production auth implemented

**Phase 5 Complete:**
- ✅ 100+ GitHub stars
- ✅ 5+ external contributors
- ✅ Featured in developer community
- ✅ First production users onboarded

---

## 📞 Emergency Contacts & Resources

**If Something Goes Wrong:**

| Issue | Solution |
|-------|----------|
| Cloud Run deployment fails | See `docs/CLOUD_RUN_DEPLOYMENT_PLAN.md` troubleshooting section |
| DNS not propagating | Use direct Cloud Run URL for submission, fix DNS later |
| Video too large | Compress with HandBrake (1080p, H.264, 5000 kbps) |
| Tests failing | Check `pytest --maxfail=1 -v` for first failure |
| Out of time | Submit with current status, note limitations in description |

**Key Links:**
- Competition: https://googlegemini3.devpost.com
- Cloud Run Console: https://console.cloud.google.com/run
- Cloudflare Dashboard: https://dash.cloudflare.com
- Gemini API: https://aistudio.google.com/app/apikey

---

## ✨ Success Definition

**Submission is successful when:**
- ✅ Devpost submission completed before 5:00 PM PT on Feb 9, 2026
- ✅ Video under 3 minutes, shows live demo
- ✅ Public demo URL (api.fcp.dev) is accessible
- ✅ All 5 GitHub repos are public
- ✅ 200-word description highlights Gemini 3 integration
- ✅ Screenshots show key features

**Good luck! 🚀**

---

**Last Updated:** 2026-02-09
**Status:** Ready for deployment phase
**Next Step:** Execute "1. Deploy to Google Cloud Run"
