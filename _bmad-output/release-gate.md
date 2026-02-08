# Release Gate Checklist

A human can verify release readiness in 60 seconds using this checklist.

## Required Commands

Run these from the repo root. All must pass (exit code 0).

| # | Command | What it checks |
|---|---------|----------------|
| 1 | `cd gui && npx vitest run` | 327+ unit tests pass |
| 2 | `cd gui && npx tsc --noEmit` | Zero TypeScript errors |
| 3 | `cd gui && npx vitest run && npx tsc --noEmit` | Combined (or `npm run verify`) |

## Lane Modes

| Mode | When | What |
|------|------|------|
| **SMOKE** | Dev iteration | Steps 01-12, 8+ screenshots, 6+ assertions |
| **RELEASE** | Before release | All SMOKE + fingerprint + manifest + golden compare (steps 13-15) |

## Required MCP Visual Lane

Before release, a Puppeteer MCP run must be performed by Claude. The procedure
is defined in `_bmad-output/templates/visual-gate-run.md`.

### SMOKE Steps (12 steps, 8 mandatory screenshots)

1. Navigate to Explore
2. Verify demo button visible
3. Click demo (John 3:16)
4. Verify readable result (3-column layout)
5. Verify ref-input populated
6. Switch to Traceable view
7. Open Receipts tab
8. Click confidence layer
9. Verify confidence detail panel
10. Open Compare modal
11. Verify Compare modal content
12. Close Compare modal

### RELEASE Additional Steps (Golden Compare)

13. Re-open Compare modal
14. Select B translator (fluent) + click Run Comparison
15. Capture compare results (side-by-side)

### Minimum Assertions (6 mandatory, 15+ typical)

- [ ] `explore-ready` visible
- [ ] `ref-input` contains expected reference
- [ ] `view-traceable-btn` active after switch
- [ ] `receipts-tab` content visible
- [ ] `confidence-detail-panel` visible after click
- [ ] `compare-modal` visible after click

## Where to Find Artifacts

| Artifact | Path |
|----------|------|
| Latest report (human) | `gui/_mcp_artifacts/latest/report.md` |
| Latest report (machine) | `gui/_mcp_artifacts/latest/report.json` |
| Release evidence pack | `gui/_mcp_artifacts/releases/<timestamp>_<sha>/` |
| Release MANIFEST | `gui/_mcp_artifacts/releases/<timestamp>_<sha>/MANIFEST.json` |
| Run index | `gui/_mcp_artifacts/index.json` |
| Visual gate spec | `gui/docs/visual-gate.md` |
| Selector contract | `gui/docs/visual-gate-selectors.md` |
| Run procedure template | `_bmad-output/templates/visual-gate-run.md` |

## Fail Conditions

The release gate **FAILS** if ANY of these are true:

1. **vitest fails**: Any test failure or test count < 327
2. **tsc fails**: Any TypeScript error
3. **No MCP report**: `gui/_mcp_artifacts/latest/report.json` missing or stale (>24h)
4. **Gate result != PASS**: `report.json` summary.gate is not "PASS"
5. **Missing assertions**: Fewer than 6 assertions in report
6. **Too few screenshots**: `summary.totalScreenshots` < 8
7. **Failed assertion**: Any assertion with `pass: false`
8. **Stale commit**: Report gitCommit does not match current `HEAD`
9. **Screenshot files missing**: `summary.missingScreenshotsCount` > 0
10. **Screenshot paths unverified**: `screenshotPaths` array is empty or absent
11. **Missing fingerprint** (RELEASE): `summary.hasFingerprint` is false
12. **Missing manifest** (RELEASE): `summary.hasManifest` is false
13. **Missing compare** (RELEASE): `fingerprint.compareParams` is absent
14. **Pack info unavailable** (RELEASE): `fingerprint.packInfoAvailable` is false without `packInfoUnavailableReason`
15. **No MANIFEST.json** (RELEASE): `releases/<slug>/MANIFEST.json` missing

## Pass Condition

The release gate **PASSES** when ALL of these are true:

- [ ] `npx vitest run` — 327+ tests, 0 failures
- [ ] `npx tsc --noEmit` — 0 errors
- [ ] `report.json` exists in `gui/_mcp_artifacts/latest/`
- [ ] `report.json` summary.gate === "PASS"
- [ ] `report.json` summary.passedAssertions >= 6
- [ ] `report.json` summary.totalSteps >= 8
- [ ] `report.json` summary.totalScreenshots >= 8
- [ ] `report.json` summary.missingScreenshotsCount === 0
- [ ] `report.json` screenshotPaths[] all exist on disk
- [ ] `report.json` gitCommit matches current HEAD
- [ ] Release evidence pack copied to `gui/_mcp_artifacts/releases/`
- [ ] (RELEASE) `report.json` summary.hasFingerprint === true
- [ ] (RELEASE) `report.json` summary.hasManifest === true
- [ ] (RELEASE) `report.json` fingerprint.compareParams present
- [ ] (RELEASE) `MANIFEST.json` in release pack with valid SHA-256 hashes

## Pre-Release: Reset Demo State

If the demo nudge has been dismissed during testing, reset it before a clean run:

```javascript
// In browser console or via puppeteer_evaluate:
// Key defined in gui/src/constants/storageKeys.ts → DEMO_NUDGE_DISMISSED_KEY
localStorage.removeItem('redletters_demo_nudge_dismissed');
```

## Quick Verify (Copy-Paste)

```bash
# 1. Automated checks
cd gui && npx vitest run && npx tsc --noEmit

# 2. Check latest report (includes screenshot + fingerprint + manifest verification)
cat gui/_mcp_artifacts/latest/report.json | python3 -c "
import json, sys, os
r = json.load(sys.stdin)
s = r['summary']
mode = r.get('laneMode', 'SMOKE')
print(f\"Gate: {s['gate']} | Mode: {mode} | Steps: {s['passedSteps']}/{s['totalSteps']} | Assertions: {s['passedAssertions']}/{s['totalAssertions']} | Screenshots: {s['totalScreenshots']} ({s['missingScreenshotsCount']} missing) | Commit: {r['gitCommit']}\")
print(f\"Fingerprint: {'present' if s.get('hasFingerprint') else 'missing'} | Manifest: {'present' if s.get('hasManifest') else 'missing'}\")
# Verify screenshot files exist
missing = [p for p in r.get('screenshotPaths', []) if not os.path.exists(p)]
if missing:
    print(f'FAIL: {len(missing)} screenshot(s) missing on disk: {missing}')
else:
    print(f'OK: all {len(r.get(\"screenshotPaths\", []))} screenshots verified on disk')
if mode == 'RELEASE':
    fp = r.get('fingerprint', {})
    print(f\"Pack Info: {'available' if fp.get('packInfoAvailable') else 'unavailable'} | Packs: {fp.get('installedPacks', {}).get('count', 0)} | Compare: {'yes' if fp.get('compareParams') else 'no'}\")
"

# 3. Check commit matches
echo "HEAD: $(git rev-parse --short HEAD)"
```
