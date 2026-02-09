# FCP HACKATHON READY - CONSOLIDATED ACTION ITEMS

Generated: $(date)

## 🔴 CRITICAL - DO NOW (< 1 hour)

### Fix Extension Documentation
**File**: `../fcp-gemini-extension/GEMINI.md`
- [ ] Line 39: Change `log_meal` → `log_meal_from_audio`
- [ ] Line 65-70: Remove `get_food_stats` section (tool doesn't exist)

### Update Test Count
**File**: `README.md` line 34
- [ ] Change "2,861" to actual count from latest `pytest tests/unit -q`

### Clean Up Dated Review Docs
**Move to archive**:
```bash
mv docs/CODE_REVIEW_2026-02-09.md docs/archive/
mv docs/CODE_AND_DOC_REVIEW_2026-02-09.md docs/archive/
mv docs/coverage-report-2026-02-09.md docs/archive/
mv docs/plans/2026-02-09-*.md docs/archive/plans/
```

## 🟡 HIGH PRIORITY - Before Submission

### Verify Links in README
- [ ] Test: https://fcp.dev (landing page)
- [ ] Test: https://api.fcp.dev (will exist after deployment)
- [ ] Test: Protocol spec link
- [ ] Update "Try the API" if URL changes

### SUBMISSION.md Cleanup
**Current**: 683 lines mixing pre/post hackathon
**Fix**: Split into two files
- [ ] Keep lines 1-310 (pre-submission) as SUBMISSION.md
- [ ] Move lines 311-683 (post-submission roadmap) to docs/ROADMAP.md

### Verify .env.example Exists
```bash
# Check if exists
ls -la .env.example

# If missing, create minimal version
cat > .env.example << 'ENVEOF'
# Required
GEMINI_API_KEY=your_key_here

# Optional
DATABASE_BACKEND=sqlite
LOG_LEVEL=INFO
ENVEOF
```

## 🟢 NICE TO HAVE - If Time Permits

### Add Missing CONTRIBUTING.md
Create `.github/CONTRIBUTING.md` with basic dev setup

### Clean Up demo-video Directory
- [ ] Verify all generated files are .gitignored
- [ ] Check if timeline_final.mp4 should be in repo (2.2 MB)

### Verify All Tool Names Match
Run consistency check:
```bash
python scripts/verify_tool_names.py  # if exists
# Or manual: Check GEMINI.md vs registry
```

## ❌ DO NOT DO (Post-Hackathon)

- Don't touch technical-debt docs (keep for later)
- Don't implement FoodLoop/FoodFeed features
- Don't add CI/CD workflows beyond what exists
- Don't refactor registry for remaining 38 tools
- Don't add GEMINI.md/AGENTS.md to server repo (extension only)

## 📋 FINAL CHECKLIST BEFORE SUBMISSION

- [ ] Extension GEMINI.md tool names fixed
- [ ] README test count accurate
- [ ] Dated docs moved to archive
- [ ] .env.example exists
- [ ] All links in README work
- [ ] SUBMISSION.md split (roadmap separated)
- [ ] Git status clean (`git status`)
- [ ] All changes committed and pushed

---

**Total Time**: ~30-45 minutes
**Deadline**: February 9, 2026 5:00 PM PT
