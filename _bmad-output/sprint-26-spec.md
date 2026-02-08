# Sprint 26 — Reproducible & Tamper-Evident Visual Gate

## Overview

Make the Release Gate reproducible and evidence packs tamper-evident. Three stories:
determinism fingerprint, SHA-256 manifest, and golden compare step.

## Report Schema Additions

### Fingerprint (in `GateReport`)

```typescript
interface Fingerprint {
  gitCommit: string;
  appVersion?: string;
  buildVersion?: string;
  baseUrl: string;
  requestParams: RequestParams;     // ref, translator, requestMode, viewMode
  compareParams?: CompareParams;    // compareA/B: { translator, mode }
  installedPacks: {
    count: number;
    packs: SourcePackInfo[];        // id, name, version per pack
    packListHash: string;           // SHA-256 of canonical JSON of sorted pack list
  };
  packInfoAvailable: boolean;
  packInfoUnavailableReason?: string;
}
```

### Lane Modes

```typescript
type LaneMode = "SMOKE" | "RELEASE";
```

- **SMOKE**: Steps 01-12, no fingerprint/manifest required.
- **RELEASE**: All steps + fingerprint + manifest + golden compare.

### MANIFEST Format

```json
{
  "createdAt": "2026-02-07T12:00:00Z",
  "gitCommit": "d767359",
  "baseUrl": "http://localhost:1420",
  "fingerprintHash": "<sha256 of canonical fingerprint JSON>",
  "files": [
    { "relativePath": "report.json", "bytes": 4521, "sha256": "<hex>" },
    { "relativePath": "screenshots/01-explore-load.png", "bytes": 123456, "sha256": "<hex>" }
  ]
}
```

## Gate Fail Rules (RELEASE mode)

In addition to existing SMOKE rules, RELEASE mode fails if:
1. `fingerprint` is missing from report
2. `fingerprint.packInfoAvailable` is false without a reason
3. `fingerprint.compareParams` is missing
4. MANIFEST.json is missing from release pack
5. `hasManifest` is false in summary

## Fingerprint Sources

- `gitCommit`: `git rev-parse --short HEAD`
- `baseUrl`: MCP navigate URL
- `requestParams`: Derived from lane steps (John 3:16, literal, readable, readable)
- `compareParams`: From golden compare steps (A=current, B=fluent/readable)
- `installedPacks`: From Sources API (`/sources/status`) or app state
- `packListHash`: SHA-256 of `canonicalJsonStable(sortedPacks)`

## MCP Compare Lane Step

New steps 13-15 in RELEASE mode:
- 13: Re-open compare modal
- 14: Select B translator=fluent, run comparison
- 15: Capture compare-results screenshot

## Files Changed

- `gui/src/utils/visualGateReport.ts` — Types + helpers extended
- `gui/src/utils/visualGateReport.test.ts` — 28 tests (was 8)
- `gui/src/utils/visualGateManifest.ts` — New: manifest types + builders
- `gui/src/utils/visualGateManifest.test.ts` — New: 8 tests
- `gui/docs/visual-gate.md` — Updated spec
- `_bmad-output/release-gate.md` — Updated checklist
- `_bmad-output/templates/visual-gate-run.md` — Updated procedure
