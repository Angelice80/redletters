# Visual Gate Specification

The Visual Gate is a repeatable set of Puppeteer MCP checks that must pass before
any release of the Red Letters GUI. Each check produces durable on-disk evidence.

## Lane Modes

| Mode | Purpose | Requirements |
|------|---------|-------------|
| **SMOKE** | Quick dev feedback | 8+ screenshots, 6+ assertions, all pass |
| **RELEASE** | Full release gate | All SMOKE + fingerprint + manifest + compare |

## Base URL

| Variable | Default | Description |
|----------|---------|-------------|
| `VISUAL_GATE_URL` | `http://localhost:1420` | GUI dev server |

The Explore route is `${VISUAL_GATE_URL}/explore`.

## Required Checks (Explore Smoke Lane)

Each check is a discrete step that produces a screenshot and one or more DOM assertions.

| Step | Action | Selector | Assertion |
|------|--------|----------|-----------|
| 01 | Navigate to Explore | — | Page loads without error |
| 02 | Verify Explore ready state | `[data-testid="demo-btn"]` | Demo button visible |
| 03 | Click Demo button | `[data-testid="demo-btn"]` | Demo loads John 3:16 |
| 04 | Verify Readable result | `[data-testid="explore-ready"]` | 3-column layout visible |
| 05 | Verify ref-input populated | `[data-testid="ref-input"]` | Contains "John 3:16" or similar |
| 06 | Switch to Traceable view | `[data-testid="view-traceable-btn"]` | Traceable button active |
| 07 | Open Receipts tab | `[data-testid="receipts-tab"]` | Tab content visible |
| 08 | Click confidence layer | `[data-testid^="confidence-layer-"]` | Layer highlights |
| 09 | Verify confidence panel | `[data-testid="confidence-detail-panel"]` | Panel visible |
| 10 | Open Compare modal | `[data-testid="compare-btn"]` | Modal visible |
| 11 | Verify Compare modal | `[data-testid="compare-modal"]` | Modal contains run button |
| 12 | Close Compare modal | Escape key or backdrop | Modal dismissed |

## Additional RELEASE Steps (Golden Compare)

These steps are **required in RELEASE mode only**:

| Step | Action | Selector | Assertion |
|------|--------|----------|-----------|
| 13 | Re-open Compare modal | `[data-testid="compare-btn"]` | Modal visible |
| 14 | Select B translator + run | `[data-testid="compare-translator-b"]`, `[data-testid="compare-run-btn"]` | Results appear |
| 15 | Capture compare results | `[data-testid="compare-results"]` | Side-by-side visible |

## Fingerprint (RELEASE mode)

In RELEASE mode, `report.json` must include a `fingerprint` object with:

| Field | Description |
|-------|-------------|
| `gitCommit` | Short SHA of current HEAD |
| `appVersion` | App version if discoverable |
| `baseUrl` | MCP base URL used |
| `requestParams` | `ref`, `translator`, `requestMode`, `viewMode` used in lane |
| `compareParams` | `compareA` and `compareB` translator + mode |
| `installedPacks.count` | Number of installed source packs |
| `installedPacks.packs[]` | `{id, name, version}` for each |
| `installedPacks.packListHash` | SHA-256 of canonical JSON of sorted pack list |
| `packInfoAvailable` | Whether pack data was retrieved |
| `packInfoUnavailableReason` | Explanation if not available |

The gate **FAILS** if fingerprint is missing or `packInfoAvailable=false` without a reason.

## MANIFEST (RELEASE mode)

Each `releases/<slug>/` directory must include:

- `MANIFEST.json` — machine-readable with `{createdAt, gitCommit, baseUrl, fingerprintHash, files[{relativePath, bytes, sha256}]}`
- `MANIFEST.txt` — human-readable with SHA256 + size + path per line

The gate **FAILS** if MANIFEST is missing from a RELEASE pack.

## Screenshot Naming Convention

Format: `{step_number:02d}-{kebab-case-description}.png`

Examples:
- `01-explore-load.png`
- `02-demo-btn-visible.png`
- `03-demo-clicked.png`
- `04-readable-result.png`
- `05-ref-input-populated.png`
- `06-traceable-view.png`
- `07-receipts-tab.png`
- `08-confidence-layer-click.png`
- `09-confidence-detail-panel.png`
- `10-compare-modal-open.png`
- `11-compare-modal-content.png`
- `12-compare-modal-closed.png`
- `13-compare-reopen.png` (RELEASE only)
- `14-compare-run.png` (RELEASE only)
- `15-compare-results.png` (RELEASE only)

## Assertion Format

Each assertion is recorded in `report.json` as:

```json
{
  "step": 4,
  "name": "readable-result-visible",
  "selector": "[data-testid=\"explore-ready\"]",
  "expected": "visible",
  "actual": "visible",
  "pass": true,
  "screenshot": "04-readable-result.png"
}
```

An assertion **passes** when:
- `expected === actual` for visibility checks
- Element exists in DOM for existence checks
- Element text matches expected pattern for content checks

A step **fails** when any assertion in that step fails.

The gate **fails** when any step fails.

## Minimum Requirements Per Run

### SMOKE mode
- At least **8 screenshots** (steps 01-04 + 06-09 are mandatory)
- At least **6 DOM assertions** must pass

### RELEASE mode
- At least **8 screenshots** (typically 15 with compare steps)
- At least **6 DOM assertions** must pass
- `fingerprint` object present and valid
- `compareParams` present in fingerprint
- `MANIFEST.json` present in release directory
- `packInfoAvailable=true` OR explicit `packInfoUnavailableReason`

## Artifact Storage

See `gui/_mcp_artifacts/README.md` for layout details.

- **latest/**: Always overwritten. Contains the most recent run's results.
- **releases/**: Immutable evidence packs keyed by `YYYY-MM-DD_HHMM_shortsha`.
- **index.json**: Array of all run metadata entries.
