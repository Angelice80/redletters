# Sprint 26 Plan — Reproducible & Tamper-Evident Visual Gate

## Sprint Goal
Make the visual gate reproducible (fingerprint) and tamper-evident (MANIFEST).

## Stories

### S26.0 — Determinism Fingerprint in Gate Report
**Points**: 3
**Files**: `visualGateReport.ts`, `visualGateReport.test.ts`
**Types added**: `SourcePackInfo`, `RequestParams`, `CompareParams`, `Fingerprint`, `LaneMode`
**Functions added**: `canonicalJsonStable()`, `computePackListHash()`
**Gate logic**: RELEASE mode requires fingerprint + compareParams + packInfoAvailable
**Tests**: 28 (up from 8)

### S26.1 — Release MANIFEST with SHA256 Hashes
**Points**: 3
**Files**: `visualGateManifest.ts` (new), `visualGateManifest.test.ts` (new)
**Types**: `ManifestFileEntry`, `Manifest`, `ManifestFsReader`, `HashFn`
**Functions**: `buildManifest()`, `renderManifestText()`, `verifyManifest()`
**Pattern**: Dependency-injected fs + crypto (no @types/node needed)
**Tests**: 8

### S26.2 — Golden Compare Step + Diff Screenshot Capture
**Points**: 2
**Files**: All doc files + visualGateReport.ts (compareParams in Fingerprint)
**Lane update**: Steps 13-15 added for RELEASE mode
**Gate logic**: RELEASE mode requires compareParams in fingerprint
**Existing testids verified**: `compare-modal`, `compare-translator-b`, `compare-mode-b`, `compare-run-btn`, `compare-results`

## Velocity
- 8 points / 3 stories
- Total tests: 327 (up from 299)
- TypeScript errors: 0
