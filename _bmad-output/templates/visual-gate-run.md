# Visual Gate Run Procedure

This template defines the exact steps Claude follows when performing a Puppeteer MCP
visual gate run. Each step produces a screenshot and one or more DOM assertions.

## Lane Modes

- **SMOKE**: Steps 01-12 only. Quick feedback for dev.
- **RELEASE**: Steps 01-15 + fingerprint + manifest + golden compare.

## Prerequisites

1. GUI dev server running at `http://localhost:1420` (or `$VISUAL_GATE_URL`)
2. Backend engine running at port 47200 with source packs installed
3. Puppeteer MCP server connected (namespace: `mcp__puppeteer__`)

## Pre-Run Setup

```
# Clear any previous localStorage demo flags
# Key: gui/src/constants/storageKeys.ts → DEMO_NUDGE_DISMISSED_KEY
mcp__puppeteer__puppeteer_evaluate: localStorage.removeItem('redletters_demo_nudge_dismissed')
```

## SMOKE Steps (01-12)

### Step 01: Navigate to Explore
- **Tool**: `mcp__puppeteer__puppeteer_navigate` → `${base}/explore`
- **Screenshot**: `01-explore-load.png`
- **Assertions**: Page loads without console errors

### Step 02: Verify Demo Button
- **Tool**: `mcp__puppeteer__puppeteer_evaluate` → check `[data-testid="demo-btn"]` exists
- **Screenshot**: `02-demo-btn-visible.png`
- **Assertion**: `demo-btn` is visible

### Step 03: Click Demo
- **Tool**: `mcp__puppeteer__puppeteer_click` → `[data-testid="demo-btn"]`
- **Wait**: 3 seconds for translation to complete
- **Screenshot**: `03-demo-clicked.png`
- **Assertion**: Translation result appears

### Step 04: Verify Readable Result
- **Tool**: `mcp__puppeteer__puppeteer_evaluate` → check `[data-testid="explore-ready"]` visible
- **Screenshot**: `04-readable-result.png`
- **Assertions**:
  - `explore-ready` visible
  - `ref-input` contains reference text

### Step 05: Verify Ref Input
- **Tool**: `mcp__puppeteer__puppeteer_evaluate` → read `ref-input` value
- **Screenshot**: `05-ref-input-populated.png`
- **Assertion**: Input contains "John 3:16" or "Jn 3:16"

### Step 06: Switch to Traceable
- **Tool**: `mcp__puppeteer__puppeteer_click` → `[data-testid="view-traceable-btn"]`
- **Wait**: 1 second
- **Screenshot**: `06-traceable-view.png`
- **Assertion**: `view-traceable-btn` has active/selected styling

### Step 07: Open Receipts Tab
- **Tool**: `mcp__puppeteer__puppeteer_click` → `[data-testid="receipts-tab"]`
- **Wait**: 1 second
- **Screenshot**: `07-receipts-tab.png`
- **Assertion**: Receipts content is visible (ledger OR empty-state message)

### Step 08: Click Confidence Layer
- **Tool**: `mcp__puppeteer__puppeteer_click` → `[data-testid^="confidence-layer-"]` (first available)
- **Wait**: 500ms
- **Screenshot**: `08-confidence-layer-click.png`
- **Assertion**: A confidence layer is highlighted/selected

### Step 09: Verify Confidence Panel
- **Tool**: `mcp__puppeteer__puppeteer_evaluate` → check `confidence-detail-panel` visible
- **Screenshot**: `09-confidence-detail-panel.png`
- **Assertion**: `confidence-detail-panel` is visible in DOM

### Step 10: Open Compare Modal
- **Tool**: `mcp__puppeteer__puppeteer_click` → `[data-testid="compare-btn"]`
- **Wait**: 500ms
- **Screenshot**: `10-compare-modal-open.png`
- **Assertion**: `compare-modal` is visible

### Step 11: Verify Compare Modal Content
- **Tool**: `mcp__puppeteer__puppeteer_evaluate` → check `compare-run-btn` exists inside modal
- **Screenshot**: `11-compare-modal-content.png`
- **Assertion**: `compare-run-btn` is visible

### Step 12: Close Compare Modal
- **Tool**: `mcp__puppeteer__puppeteer_evaluate` → press Escape or click backdrop
- **Wait**: 500ms
- **Screenshot**: `12-compare-modal-closed.png`
- **Assertion**: `compare-modal` no longer visible

## RELEASE Steps (13-15) — Golden Compare

These steps are ONLY performed in RELEASE mode.

### Step 13: Re-open Compare Modal
- **Tool**: `mcp__puppeteer__puppeteer_click` → `[data-testid="compare-btn"]`
- **Wait**: 500ms
- **Screenshot**: `13-compare-reopen.png`
- **Assertion**: `compare-modal` is visible
- **Record**: `fingerprint.compareParams.compareA = { translator: <current>, mode: <current> }`

### Step 14: Select B Translator + Run Comparison
- **Tool**: `mcp__puppeteer__puppeteer_select` → `[data-testid="compare-translator-b"]` value="fluent"
- **Tool**: `mcp__puppeteer__puppeteer_click` → `[data-testid="compare-run-btn"]`
- **Wait**: 3 seconds for comparison to complete
- **Screenshot**: `14-compare-run.png`
- **Assertion**: Compare request completes without error
- **Record**: `fingerprint.compareParams.compareB = { translator: "fluent", mode: <selected> }`

### Step 15: Capture Compare Results
- **Tool**: `mcp__puppeteer__puppeteer_evaluate` → check `[data-testid="compare-results"]` visible
- **Screenshot**: `15-compare-results.png`
- **Assertion**: `compare-results` is visible with A and B panels

## Post-Run (SMOKE)

1. Collect all assertion results
2. Generate `report.json` and `report.md` using `visualGateReport.ts`
3. Save to `gui/_mcp_artifacts/latest/`
4. Copy to `gui/_mcp_artifacts/releases/<timestamp>_<sha>/`
5. Update `gui/_mcp_artifacts/index.json`

## Post-Run (RELEASE) — Additional Steps

After SMOKE post-run, also:

6. **Fingerprint**: Populate `report.fingerprint` with:
   - `gitCommit`, `baseUrl`, `requestParams`, `compareParams`
   - Fetch installed pack info from Sources API or evaluate from app state
   - Compute `packListHash` = SHA-256 of canonical JSON of sorted packs
7. **Manifest**: Generate `MANIFEST.json` and `MANIFEST.txt` using `visualGateManifest.ts`
   - Read every file in `releases/<slug>/` (reports + screenshots)
   - Compute SHA-256 hash for each file
   - Write `MANIFEST.json` and `MANIFEST.txt` to the release directory
8. **Recompute summary**: Call `computeSummary()` with `laneMode: "RELEASE"`, `fingerprint`, `hasManifest: true`
9. **Write final report**: Overwrite `report.json` and `report.md` with updated summary
