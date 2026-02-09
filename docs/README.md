# FCP Documentation

Comprehensive documentation for the Food Context Protocol reference implementation.

---

## 📁 Documentation Structure

### Essential Docs (Start Here)

- **[CLOUD_RUN_DEPLOYMENT_PLAN.md](CLOUD_RUN_DEPLOYMENT_PLAN.md)** - Deploy to Google Cloud Run for hackathon
- **[SETUP.md](SETUP.md)** - Local development setup instructions
- **[video-script.md](video-script.md)** - Demo video script and filming guide
- **[gemini-feature-audit.md](gemini-feature-audit.md)** - Gemini 3 features and submission description
- **[test-standards.md](test-standards.md)** - Testing conventions and best practices
- **[DEMO.md](DEMO.md)** - Demo walkthroughs

### Plans Directory

- **[plans/2026-02-09-achieve-100-percent-coverage.md](plans/2026-02-09-achieve-100-percent-coverage.md)** - Test coverage implementation plan (✅ Complete - 100% achieved)

### Technical Debt

**Location:** `technical-debt/`

Post-submission refactoring plans:

- **[TOOL_REGISTRY_PLAN.md](technical-debt/TOOL_REGISTRY_PLAN.md)** - High-level registry refactoring overview
- **[TOOL_REGISTRY_DETAILED_PLAN.md](technical-debt/TOOL_REGISTRY_DETAILED_PLAN.md)** - Detailed implementation roadmap (5/43 tools migrated)
- **[authentication-architecture.md](technical-debt/authentication-architecture.md)** - Production auth system design
- **[auth-comparison.md](technical-debt/auth-comparison.md)** - Auth implementation alternatives
- **[auth-quickstart.md](technical-debt/auth-quickstart.md)** - Auth setup guide

### Archive

**Location:** `archive/`

Historical documentation preserved for reference:

- **[CLEANUP_SUMMARY.md](archive/CLEANUP_SUMMARY.md)** - FoodLog → FCP rebranding history
- **[TOOL_NAMESPACE_MAPPING.md](archive/TOOL_NAMESPACE_MAPPING.md)** - Tool namespace migration record
- **[deployment-guide.md](archive/deployment-guide.md)** - Original deployment guide (superseded)
- **[DEPLOYMENT_CHECKLIST.md](archive/DEPLOYMENT_CHECKLIST.md)** - Local deployment steps (superseded)
- **[screenshot-capture-guide.md](archive/screenshot-capture-guide.md)** - Screenshot workflow for demo
- **[video-storyboard.md](archive/video-storyboard.md)** - Original 24-shot storyboard
- **[hackathon-audit-prompt.md](archive/hackathon-audit-prompt.md)** - Internal audit prompt
- **[preview-code-review.md](archive/preview-code-review.md)** - Draft code review
- **[preview-tool-guide.md](archive/preview-tool-guide.md)** - Draft tool guide
- **[pydantic-route-models.md](archive/pydantic-route-models.md)** - Technical notes on Pydantic models

---

## 🎯 Quick Navigation

### For Hackathon Submission
1. Read **[SUBMISSION.md](../SUBMISSION.md)** (root directory) - Main submission checklist
2. Deploy using [CLOUD_RUN_DEPLOYMENT_PLAN.md](CLOUD_RUN_DEPLOYMENT_PLAN.md)
3. Record video following [video-script.md](video-script.md)
4. Use description from [gemini-feature-audit.md](gemini-feature-audit.md)

### For Development
1. Setup: [SETUP.md](SETUP.md)
2. Testing: [test-standards.md](test-standards.md)
3. Coverage: [plans/2026-02-09-achieve-100-percent-coverage.md](plans/2026-02-09-achieve-100-percent-coverage.md)

### For Post-Submission Work
1. Registry refactoring: [technical-debt/TOOL_REGISTRY_PLAN.md](technical-debt/TOOL_REGISTRY_PLAN.md)
2. Authentication: [technical-debt/authentication-architecture.md](technical-debt/authentication-architecture.md)

---

## 📊 Current Status

| Area | Status | Notes |
|------|--------|-------|
| **Tests** | ✅ 100% coverage | 2,506 passing tests |
| **Deployment** | ⏳ Pending | Ready for Cloud Run |
| **Registry** | 🚧 12% complete | 5/43 tools migrated |
| **Auth** | 📋 Planned | Demo mode active |
| **Video** | 📝 Script ready | Ready to film |

---

**Last Updated:** 2026-02-09
**Maintained By:** Food Context Protocol Contributors
