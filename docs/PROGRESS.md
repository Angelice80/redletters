# Development Progress Log

## Project: Red Letters Source Reader
**Started**: 2026-01-26
**Current Version**: 0.17.0 (Contract-First GUI)

---

## Milestone: Contract-First GUI v0.17

**Date**: 2026-02-03
**Status**: ✓ Complete

### Summary

Made the GUI incapable of calling wrong endpoints by deriving endpoint paths from `/v1/capabilities` and centralizing base URL logic:
- ApiContract module provides single source of truth for endpoint paths
- All ApiClient methods use contract-derived paths instead of hardcoded strings
- ExportView now uses ApiClient.runScholarly() instead of raw fetch()
- Enhanced ApiErrorPanel shows resolved base URL, capability snapshot, and full diagnostics
- README.md updated to reflect current version, ports, and GUI documentation

### Key Additions (Sprint 17)

| Item | Description | Tests |
|------|-------------|-------|
| A1 | ApiContract module for centralized endpoint management | 33 |
| A2 | ApiClient refactored to use contract for all endpoints | 17 |
| A3 | ExportView uses ApiClient instead of raw fetch | - |
| A4 | ApiErrorPanel shows contract diagnostics (base URL, capabilities) | - |
| A5 | README.md updated (v0.17.0, port 47200, GUI docs) | - |
| A6 | contract.test.ts: Base URL, fallbacks, URL composition | 33 |
| A7 | client.test.ts: contractDiagnostics normalization | 17 |

### Test Results

- **GUI Tests**: 85 passing (contract.test.ts: 33, client.test.ts: 17, utils: 35)
- **Python Tests**: 1080 passing, 1 skipped
- **Coverage**: All new contract-first code has dedicated tests

### Non-Negotiables Validated

- SBLGNT canonical spine (ADR-007)
- Deterministic output (no ML)
- No copyrighted lexica in repo
- **NEW**: Endpoint paths derived from /v1/capabilities (contract-first)
- **NEW**: Single source of truth for API base URL and paths
- **NEW**: Error diagnostics include resolved base URL and capability snapshot
- **NEW**: No hardcoded endpoint strings in screen components

### Files Created

```
gui/src/api/contract.ts                 # ApiContract for endpoint resolution
gui/src/api/contract.test.ts            # 33 unit tests for ApiContract
```

### Files Modified

```
gui/src/api/client.ts                   # Uses ApiContract for all endpoints
gui/src/api/types.ts                    # Added contractDiagnostics to ApiErrorDetail
gui/src/screens/ExportView.tsx          # Uses client.runScholarly(), includes contract diags
gui/src/components/ApiErrorPanel.tsx    # Shows resolved base URL, capability snapshot
README.md                               # Updated version, port, GUI docs
docs/gui.md                             # Sprint 17 verification checklist
docs/PROGRESS.md                        # Add v0.17.0 milestone
```

### Verification Checklist

- [x] **No hardcoded endpoints**: grep confirms no raw "/translate", "/sources" strings in screens
- [x] **ApiContract provides fallbacks**: DEFAULT_ENDPOINTS used when capabilities unavailable
- [x] **Capabilities update contract**: setCapabilities() propagates to all endpoint methods
- [x] **Error panel shows contract state**: Base URL and capability version visible in diagnostics
- [x] **ExportView uses ApiClient**: raw fetch() replaced with client.runScholarly()
- [x] **GUI tests pass**: 85 tests including 33 contract tests and 17 client tests
- [x] **Python tests pass**: 1080 tests (backend compatibility verified)
- [x] **README accurate**: Version 0.17.0, port 47200, links to docs/gui.md

---

## Milestone: GUI Resilience + Bootstrap v0.16

**Date**: 2026-02-03
**Status**: ✓ Complete

### Summary

Made the GUI intuitive and resilient with actionable error diagnostics, bootstrap wizard, and unified API architecture:
- Unified Engine Spine and API routes into single application (no more 404s)
- API compatibility handshake via `/v1/capabilities` endpoint
- Bootstrap wizard for first-run onboarding (connect → install spine → test translation)
- Structured error panels with method+URL, status, response snippet, and suggested fixes
- Fixed VariantStore connection type bug in gates endpoint

### Key Additions (Sprint 16)

| Item | Description | Tests |
|------|-------------|-------|
| B18 | Unified API routes in Engine Spine app | - |
| B19 | Fixed VariantStore connection type (raw vs wrapper) | - |
| B11 | API capabilities endpoint `/v1/capabilities` | - |
| B12 | ApiErrorPanel component with structured diagnostics | - |
| B13 | BootstrapWizard component for first-run onboarding | - |
| B20 | Documentation updates (gui.md, PROGRESS.md) | - |

### Non-Negotiables Validated

- SBLGNT canonical spine (ADR-007)
- Deterministic output (no ML)
- No copyrighted lexica in repo
- **NEW**: GUI shows actionable diagnostics instead of generic errors
- **NEW**: First-run wizard guides users to working state
- **NEW**: API compatibility handshake enables version checking
- **NEW**: All translation/sources/variants endpoints accessible on engine port

### Files Created

```
gui/src/components/ApiErrorPanel.tsx     # Structured error display
gui/src/components/BootstrapWizard.tsx   # First-run onboarding wizard
```

### Files Modified

```
src/redletters/engine_spine/app.py       # Include API routes in engine app
src/redletters/engine_spine/routes.py    # Add /v1/capabilities endpoint, fix connection types
gui/src/App.tsx                          # Bootstrap wizard integration
gui/src/api/client.ts                    # Add getCapabilities method
gui/src/api/types.ts                     # Add ApiCapabilities, ApiErrorDetail types
gui/src/screens/Sources.tsx              # Integrate ApiErrorPanel
gui/src/screens/PassageWorkspace.tsx     # Integrate ApiErrorPanel
gui/src/screens/ExportView.tsx           # Integrate ApiErrorPanel
docs/gui.md                              # Document bootstrap wizard and error panels
docs/PROGRESS.md                         # Add v0.16.0 milestone
```

---

## Milestone: One Command Scholarly Run v0.13

**Date**: 2026-02-02
**Status**: ✓ Complete

### Summary

Added single-command scholarly workflow orchestration for end-to-end reproducible runs:
- `run scholarly` CLI command orchestrates lockfile → gates → translate → export → snapshot → bundle → verify
- Deterministic run log with provenance (tool version, timestamps, file hashes, gate status)
- Gate enforcement: refuses to run with pending significant variants unless `--force`
- ScholarlyRunner reuses all existing primitives (no duplication)
- Run log schema with validation support
- Comprehensive integration tests

### Key Additions (Sprint 21)

| Item | Description | Tests |
|------|-------------|-------|
| M1 | ScholarlyRunner orchestration class | +4 |
| M2 | RunLog dataclasses (deterministic JSON) | +3 |
| M3 | CLI: `run scholarly` command | +2 |
| M4 | Validator: runlog artifact type | +3 |
| M5 | runlog-v1.0.0.schema.json | +1 |

**Total Tests**: 1080+ passing

### Non-Negotiables Validated

- SBLGNT canonical spine (ADR-007)
- Deterministic output (no ML)
- No copyrighted lexica in repo
- **NEW**: Single command produces complete scholarly bundle
- **NEW**: Run log is deterministic (sorted keys, stable hashes)
- **NEW**: Gate enforcement blocks unacknowledged variants unless --force
- **NEW**: forced_responsibility recorded when gates bypassed
- **NEW**: All existing primitives reused (no duplication)
- **NEW**: Run log validates against JSON Schema

### Files Created

```
src/redletters/run/__init__.py              # Run module exports
src/redletters/run/scholarly.py             # ScholarlyRunner, RunLog, RunLogCommand, etc.
docs/schemas/runlog-v1.0.0.schema.json      # Run log JSON Schema
tests/integration/test_scholarly_run.py     # 12 integration tests
```

### Files Modified

```
src/redletters/__main__.py                   # +run group with scholarly command
src/redletters/export/schema_versions.py     # +RUNLOG_SCHEMA_VERSION
src/redletters/export/validator.py           # +runlog artifact type support
docs/PROGRESS.md                             # Updated to v0.13.0
```

---

## Milestone: Deterministic Research Bundle v0.12

**Date**: 2026-02-02
**Status**: ✓ Complete

### Summary

Added deterministic research bundle packaging for shareable scholarly output:
- `bundle create` CLI to assemble reproducible bundles with lockfile, snapshot, and artifacts
- `bundle verify` CLI to validate bundle integrity via SHA-256 hashes
- `bundle inspect` CLI to view manifest details
- Tamper detection: any file modification causes verification to fail
- Optional schema inclusion and zip archive creation
- Content hash fingerprint for entire bundle

### Key Additions (Sprint 20)

| Item | Description | Tests |
|------|-------------|-------|
| M1 | Bundle manifest schema (bundle-v1.0.0.schema.json) | +2 |
| M2 | BundleCreator with deterministic packaging | +7 |
| M3 | BundleVerifier with tamper detection | +8 |
| M4 | CLI: bundle create/verify/inspect | +3 |
| M5 | Content hash for bundle fingerprinting | +2 |

**Total Tests**: 1068+ passing

### Non-Negotiables Validated

- SBLGNT canonical spine (ADR-007)
- Deterministic output (no ML)
- No copyrighted lexica in repo
- **NEW**: Bundle manifest is deterministic (sorted artifacts, canonical JSON)
- **NEW**: All artifacts have SHA-256 integrity verification
- **NEW**: Tamper detection works (modify file → verify fails)
- **NEW**: Optional schema files can be bundled
- **NEW**: Zip archive support for distribution

### Files Created

```
src/redletters/export/bundle.py              # Bundle creation and verification
docs/schemas/bundle-v1.0.0.schema.json       # Bundle manifest JSON Schema
tests/test_bundle.py                          # 22 bundle tests
```

### Files Modified

```
src/redletters/__main__.py                   # +bundle group with create/verify/inspect
src/redletters/export/__init__.py            # +BundleCreator, BundleVerifier exports
src/redletters/export/schema_versions.py     # +BUNDLE_SCHEMA_VERSION
docs/PROGRESS.md                             # Updated to v0.12.0
```

---

## Milestone: Pack Lockfile + Integrity Checks v0.11

**Date**: 2026-02-02
**Status**: ✓ Complete

### Summary

Added pack lockfile for reproducible scholarly environments:
- `packs lock` CLI to generate lockfile.json from installed state
- `packs sync` CLI to verify/sync environment against lockfile
- Lockfile includes content hashes for integrity verification
- Snapshot includes lockfile_hash for provenance chain
- JSON Schema for lockfile validation

### Key Additions (Sprint 19)

| Item | Description | Tests |
|------|-------------|-------|
| M1 | Lockfile generation (LockfileGenerator) | +5 |
| M2 | Lockfile sync and verification (LockfileSyncer) | +8 |
| M3 | CLI: packs lock/sync | +3 |
| M4 | Snapshot lockfile_hash field | +1 |
| M5 | lockfile-v1.0.0.schema.json | +1 |

**Total Tests**: 1046+ passing

### Files Created

```
src/redletters/sources/lockfile.py           # Lockfile generation and sync
docs/schemas/lockfile-v1.0.0.schema.json     # Lockfile JSON Schema
```

### Files Modified

```
src/redletters/__main__.py                   # +packs lock/sync commands
src/redletters/export/snapshot.py            # +lockfile_hash field
docs/schemas/snapshot-v1.0.0.schema.json     # +lockfile_hash property
```

---

## Milestone: Schema Contracts + Validation v0.10

**Date**: 2026-02-02
**Status**: ✓ Complete

### Summary

Added schema contracts and validation for stable, deterministic output:
- JSON Schema files for all public artifacts (apparatus, translation, quote, snapshot, citations, dossier)
- Centralized schema version constants in `schema_versions.py`
- CLI validator: `redletters validate output <path>` with auto-detect
- Snapshot now includes `schema_versions` mapping for all artifact types
- Dossier now includes `schema_version` field
- Quote command uses centralized version constant

### Key Additions (Sprint 18)

| Item | Description | Tests |
|------|-------------|-------|
| M1 | Centralized schema version constants | +5 |
| M2 | JSON Schema files (6 artifacts) | +7 |
| M3 | CLI validator (`validate output`) | +13 |
| M4 | Snapshot schema_versions field | +2 |
| M5 | Dossier schema_version field | +1 |
| M6 | v0.10 DoD runbook | - |

**Total Tests**: 1020+ passing

### Non-Negotiables Validated

- SBLGNT canonical spine (ADR-007)
- Deterministic output (no ML)
- No copyrighted lexica in repo
- **NEW**: Every public artifact has explicit schema_version
- **NEW**: JSON Schema files for all artifact types
- **NEW**: CLI validator works offline (no network calls)
- **NEW**: Validator fails on tampered/incomplete output
- **NEW**: Snapshot includes schema_versions mapping
- **NEW**: Version constants centralized in one module

### Files Created

```
src/redletters/export/schema_versions.py    # Centralized schema version constants
src/redletters/export/validator.py          # Output validation logic
docs/schemas/apparatus-v1.0.0.schema.json   # Apparatus JSON Schema
docs/schemas/translation-v1.0.0.schema.json # Translation JSON Schema
docs/schemas/quote-v1.0.0.schema.json       # Quote JSON Schema
docs/schemas/snapshot-v1.0.0.schema.json    # Snapshot JSON Schema
docs/schemas/citations-v1.0.0.schema.json   # Citations JSON Schema
docs/schemas/dossier-v1.0.0.schema.json     # Dossier JSON Schema
tests/test_schema_contracts.py              # 29 schema contract tests
docs/RUNBOOK-SCHOLARLY-TOOL-V10.md          # v0.10 DoD runbook
```

### Files Modified

```
src/redletters/export/__init__.py           # +imports from schema_versions.py
src/redletters/export/snapshot.py           # +schema_versions field, +tool version bump
src/redletters/export/citations.py          # Use centralized CITATIONS_SCHEMA_VERSION
src/redletters/variants/dossier.py          # +schema_version field on Dossier
src/redletters/__main__.py                  # +validate group, +validate output command
                                            # +QUOTE_SCHEMA_VERSION import for quote cmd
docs/PROGRESS.md                            # Updated to v0.10.0
```

---

## Milestone: Minority Metadata + Incentive Tags + Quote Friction v0.9

**Date**: 2026-02-02
**Status**: ✓ Complete

### Summary

Added minority/fringe reading preservation with metadata, incentive logic tags,
and quote friction for epistemic discipline:
- MinorityMetadata on readings (attestation_strength, historical_uptake, ideological_usage)
- Incentive tags (brevity_preference_present, age_bias_risk)
- `redletters quote` CLI command with gate friction
- Quote friction: fails without acknowledgement unless --force (marks forced_responsibility)
- Updated project goals documentation (docs/GOALS.md)

### Key Additions (Sprint 17)

| Item | Description | Tests |
|------|-------------|-------|
| M1 | MinorityMetadata dataclass and derivation | +12 |
| M2 | Incentive tags derivation | +11 |
| M3 | `redletters quote` CLI command | +7 |
| M4 | Quote friction enforcement | integrated |
| M5 | Project goals documentation | - |
| M6 | v0.9 DoD runbook | - |

**Total Tests**: 991+ passing

### Non-Negotiables Validated

- SBLGNT canonical spine (ADR-007)
- Deterministic output (no ML)
- No copyrighted lexica in repo
- **NEW**: MinorityMetadata preserved for all readings without false equivalence
- **NEW**: Incentive tags are neutral descriptive labels (no editorial commentary)
- **NEW**: Quote friction blocks unacknowledged variants unless --force
- **NEW**: forced_responsibility marked when quote is forced
- **NEW**: Derivation is conservative (historical_uptake/ideological_usage not inferred)

### Files Created

```
docs/GOALS.md                              # Project goals, non-goals, enforceable constraints
tests/test_minority_metadata.py            # 12 minority metadata tests
tests/test_incentive_tags.py               # 11 incentive tags tests
tests/test_quote_friction.py               # 7 quote friction tests
docs/RUNBOOK-SCHOLARLY-TOOL-V09.md         # v0.9 DoD runbook
```

### Files Modified

```
README.md                                  # +Philosophy additions, +link to GOALS.md
src/redletters/variants/dossier.py         # +MinorityMetadata, +derive_minority_metadata
                                           # +derive_incentive_tags, +incentive_tags on DossierReading
src/redletters/export/apparatus.py         # +minority_metadata, +incentive_tags in exports
src/redletters/__main__.py                 # +quote command
docs/PROGRESS.md                           # Updated to v0.9.0
```

---

## Milestone: Uncertainty Propagation + Export Friction v0.8

**Date**: 2026-02-02
**Status**: ✓ Complete

### Summary

Added uncertainty propagation and export friction for theological reversibility:
- Confidence bucketing (high/medium/low) with deterministic thresholds
- ConsequenceSummary describing variant impact (surface/gloss/omission)
- PackCoverage tracking absence as meaningful data
- Export friction requiring gate acknowledgement before export
- Claims analyzer for reversible theology workflow
- Composite confidence score in translation exports

### Key Additions (Sprint 16)

| Item | Description | Tests |
|------|-------------|-------|
| M1 | Confidence bucketing (bucket_confidence) | +18 |
| M2 | ConsequenceSummary for variants | +26 |
| M3 | PackCoverage (absence as data) | +9 |
| M4 | Export friction (PendingGatesError) | +14 |
| M5 | Claims analyzer CLI | +19 |
| M6 | Translation export with bucket | +threaded |
| M7 | Snapshot bucketing_version | +1 |

**Total Tests**: 942+ passing

### Non-Negotiables Validated

- SBLGNT canonical spine (ADR-007)
- Deterministic output (no ML)
- No copyrighted lexica in repo
- **NEW**: Confidence bucketing deterministic (high ≥ 0.8, medium ≥ 0.6, low < 0.6)
- **NEW**: Export friction blocks unacknowledged significant variants
- **NEW**: ConsequenceSummary neutral (affects_surface, affects_gloss, affects_omission)
- **NEW**: PackCoverage records absence as meaningful data
- **NEW**: Claims analyzer traces textual uncertainty through theology

### Files Created

```
src/redletters/analysis/__init__.py           # Claims analyzer module
src/redletters/analysis/claims_analyzer.py    # ClaimsAnalyzer, Claim, ClaimAnalysis
tests/test_confidence_bucketing.py            # 18 bucketing tests
tests/test_consequence_summary.py             # 26 consequence tests
tests/test_coverage_summary.py                # 9 coverage tests
tests/test_export_friction.py                 # 14 export friction tests
tests/test_claims_analyzer.py                 # 19 claims tests
docs/examples/claims.sample.json              # Sample claims input file
```

### Files Modified

```
src/redletters/confidence/scoring.py          # +bucket_confidence, +thresholds
src/redletters/confidence/__init__.py         # +exports for bucketing
src/redletters/variants/dossier.py            # +ConsequenceSummary, +PackCoverage
src/redletters/export/__init__.py             # +PendingGatesError, +PendingGate
src/redletters/export/apparatus.py            # +check_pending_gates, +raise_if_pending_gates
src/redletters/export/translation.py          # +composite, +bucket in confidence_summary
src/redletters/export/snapshot.py             # +confidence_bucketing_version
src/redletters/__main__.py                    # +claims group, +--force/--session-id flags
docs/PROGRESS.md                              # Updated to v0.8.0
```

---

## Milestone: Pack Explainability + Citation Export v0.7

**Date**: 2026-02-02
**Status**: ✓ Complete

### Summary

Added sense pack explainability and citation export for scholarly reproducibility:
- Sense resolution explainer showing "why this sense was chosen"
- Cross-pack conflict detection with deterministic audit trail
- CSL-JSON bibliography export of all installed packs
- Snapshot integration with `--include-citations` flag
- Greek lemma normalization for consistent lookups

### Key Additions (Sprint 15)

| Item | Description | Tests |
|------|-------------|-------|
| M1 | Greek lemma normalization (normalize_lemma) | +15 |
| M2 | Senses explain CLI (audit trail) | +9 |
| M3 | Senses conflicts CLI (disagreement detection) | +11 |
| M4 | Citations export (CSL-JSON) | +12 |
| M5 | Snapshot integration (--include-citations) | +2 |
| M6 | v0.7 DoD runbook | - |

**Total Tests**: 875+ passing

### Non-Negotiables Validated

- SBLGNT canonical spine (ADR-007)
- Deterministic output (no ML)
- No copyrighted lexica in repo
- **NEW**: Sense resolution audit trail (pack precedence visible)
- **NEW**: Cross-pack conflict detection (no hidden theology)
- **NEW**: Citation-grade bibliography export (CSL-JSON standard)
- **NEW**: Deterministic citations (same packs = identical hash)
- **NEW**: Citations included in snapshot verify workflow

### Files Created

```
src/redletters/senses/__init__.py          # normalize_lemma helper
src/redletters/senses/explain.py           # SenseExplainer, ExplainResult
src/redletters/senses/conflicts.py         # SenseConflictDetector, ConflictsResult
src/redletters/export/citations.py         # CitationsExporter, CitationEntry
tests/test_senses_normalize.py             # 15 normalization tests
tests/test_senses_explain.py               # 9 explain tests
tests/test_senses_conflicts.py             # 11 conflicts tests
tests/test_export_citations.py             # 12 citation export tests
docs/RUNBOOK-SCHOLARLY-TOOL-V07.md         # v0.7 DoD runbook
```

### Files Modified

```
src/redletters/__main__.py                 # +senses group, +export citations, +--include-citations
tests/integration/test_export_reproducibility.py  # +TestCitationsInSnapshot
docs/PROGRESS.md                           # Updated to v0.7.0
```

---

## Milestone: Sense Packs + Citation-Grade Provenance v0.6

**Date**: 2026-02-02
**Status**: ✓ Complete

### Summary

Added installable sense packs with citation-grade provenance for scholarly reproducibility:
- Sense pack manifest schema with citation fields (source_id, source_title, edition, publisher, year, license_url)
- SensePackLoader for loading TSV/JSON sense data with validation
- SensePackDB for persisting sense packs to SQLite with citation metadata
- SensePackProvider with ChainedSenseProvider fallback to BasicGlossProvider
- Citation-grade provenance threaded through receipts, ledger, and exports
- PackInfo in snapshots includes full bibliographic metadata
- Sample sense pack with 52 NT vocabulary entries

### Key Additions (Sprint 14)

| Item | Description | Tests |
|------|-------------|-------|
| M1 | Sense pack manifest schema (SensePackManifest) | +10 |
| M2 | Pack validation and loading (SensePackLoader) | +12 |
| M3 | Database operations (SensePackDB, install/uninstall) | +15 |
| M4 | Deterministic provider (SensePackProvider) | +18 |
| M5 | Citation-grade fields in receipts/exports | +8 |
| M6 | Snapshot PackInfo with citation metadata | - |
| M7 | Sample sense pack (sample-senses) | - |

**Total Tests**: 830+ passing

### Non-Negotiables Validated

- SBLGNT canonical spine (ADR-007)
- Deterministic output (no ML)
- No copyrighted lexica in repo
- **NEW**: Citation-grade provenance (source_id, source_title, edition, publisher, year)
- **NEW**: Sense packs are installable, not embedded
- **NEW**: License acceptance gating for non-CC0/PD licenses
- **NEW**: Deterministic sense precedence (priority-ordered packs)
- **NEW**: All gloss lookups traceable to sense pack source

### Files Created

```
src/redletters/sources/sense_pack.py        # SensePackManifest, SenseEntry, SensePackLoader
src/redletters/sources/sense_db.py          # SensePackDB, InstalledSensePack, schema
src/redletters/lexicon/sense_pack_provider.py # SensePackProvider, ChainedSenseProvider
tests/test_sense_pack.py                     # 22 pack loading tests
tests/test_sense_db.py                       # 15 DB operation tests
tests/test_sense_pack_provider.py            # 18 provider tests
data/packs/sample-senses/manifest.json       # Sample sense pack manifest
data/packs/sample-senses/senses.tsv          # 52 NT vocabulary entries
```

### Files Modified

```
src/redletters/sources/catalog.py           # +SENSE_PACK role
src/redletters/sources/installer.py         # +install_sense_pack, +get_sense_pack_status
src/redletters/engine/receipts.py           # +sense pack source formatting
src/redletters/pipeline/schemas.py          # +SensePackProvenance, +sense_packs_used
src/redletters/ledger/schemas.py            # +SensePackCitation, +sense_packs_used
src/redletters/export/snapshot.py           # +citation fields in PackInfo
src/redletters/export/translation.py        # +sense_packs_used in provenance
docs/PROGRESS.md                            # Updated to v0.6.0
```

---

## Milestone: Reproducible Scholar Exports v0.5

**Date**: 2026-02-02
**Status**: ✓ Complete

### Summary

Added stable export layer for scholarly reproducibility:
- Export CLI group: `export apparatus|translation|snapshot|verify`
- Stable deterministic IDs for variant units, readings, and tokens
- Canonical JSON serialization for reproducible hashing
- JSONL export of apparatus and translation datasets
- Snapshot generation with pack metadata and export hashes
- Verification against snapshot for reproducibility validation

### Key Additions (Sprint 13)

| Item | Description | Tests |
|------|-------------|-------|
| M1 | Stable ID helpers (verse_id, variant_unit_id, reading_id, token_id) | +10 |
| M2 | Canonical JSON serialization + content hashing | +8 |
| M3 | Apparatus JSONL export | +4 |
| M4 | Translation JSONL export | +2 |
| M5 | Snapshot generation with pack metadata | +4 |
| M6 | Snapshot verification | +6 |
| M7 | End-to-end reproducibility tests | +4 |
| M8 | v0.5 DoD runbook | - |

**Total Tests**: 771+ passing

### Non-Negotiables Validated

- SBLGNT canonical spine (ADR-007)
- Deterministic output (no ML)
- No copyrighted data in repo
- **NEW**: Stable identifiers for variant_unit_id, reading_id, token_id
- **NEW**: Export twice → identical hashes (reproducibility)
- **NEW**: Explicit provenance in every export row
- **NEW**: Schema version in exports for forward compatibility

### Files Created

```
src/redletters/export/__init__.py          # Export module with lazy loading
src/redletters/export/identifiers.py       # Stable ID generation + canonical JSON
src/redletters/export/apparatus.py         # Apparatus JSONL exporter
src/redletters/export/translation.py       # Translation JSONL exporter
src/redletters/export/snapshot.py          # Snapshot generation + verification
tests/test_export_ids.py                   # NEW: 24 ID/hash tests
tests/integration/test_export_reproducibility.py  # NEW: 14 reproducibility tests
docs/RUNBOOK-SCHOLARLY-TOOL-V05.md         # NEW: v0.5 DoD runbook
```

### Files Modified

```
src/redletters/__main__.py                 # +320 lines: export CLI group
docs/PROGRESS.md                           # Updated to v0.5.0
```

---

## Milestone: Multi-Pack Apparatus v0.4

**Date**: 2026-02-02
**Status**: ✓ Complete

### Summary

Extended Scholarly Tool with multi-pack variant aggregation and gate stability:
- 2+ comparative packs contribute to ONE merged VariantUnit per location
- Structured support set with witness siglum, witness_type, century_range, source_pack_id
- Gate count stable: ONE gate per merged VariantUnit (not per-pack)
- Acknowledge once suppresses future gates for that VariantUnit
- Idempotent rebuild prevents duplicate variants/support entries
- Dossier lists all packs that contributed to readings

### Key Additions (Sprint 12)

| Item | Description | Tests |
|------|-------------|-------|
| M1 | Multi-pack variant aggregation | +3 |
| M2 | Gate count stability | +2 |
| M3 | Acknowledgement suppression | +1 |
| M4 | Dossier provenance (all packs) | +1 |
| M5 | Idempotent rebuild validation | +1 |
| M6 | PackLoader v1.1 compat fixes | - |
| M7 | v0.4 DoD runbook | - |

**Total Tests**: 733+ passing

### Non-Negotiables Validated

- SBLGNT canonical spine (ADR-007)
- Variants side-by-side (ADR-008)
- TYPE5+ forbidden in readable mode (ADR-009)
- Layered confidence always visible (ADR-010)
- Evidence class explicit (no collapsed scores)
- Deterministic output (no ML)
- No copyrighted data in repo
- No epistemic inflation (explicit test coverage)
- **NEW**: ONE gate per merged VariantUnit (not per-pack)
- **NEW**: Acknowledge once suppresses future gates
- **NEW**: Idempotent rebuild (UNIQUE constraints)

### Files Modified/Created

```
src/redletters/sources/pack_loader.py      # Fixed: effective_coverage, header skip, 3-col TSV
tests/integration/test_v04_multipack_gates.py  # NEW: 8 gate stability tests
docs/RUNBOOK-SCHOLARLY-TOOL-V04.md         # NEW: v0.4 DoD runbook
docs/PROGRESS.md                           # Updated to v0.4.0
```

---

## Milestone: Scholarly Tool v0.3

**Date**: 2026-02-01
**Status**: ✓ Complete

### Summary

Extended Scholarly Beta with comparative variants workflow and epistemic discipline:
- Standalone `gates acknowledge` CLI command for audit-trail acknowledgements
- `gates list` and `gates pending` commands for gate management
- Explicit epistemic inflation prevention test suite (18+ tests)
- DoD runbook for fresh-environment reproducibility

### Key Additions (Sprint 11)

| Item | Description | Tests |
|------|-------------|-------|
| M1 | `gates acknowledge` CLI subcommand | +6 |
| M2 | `gates list` CLI subcommand | +3 |
| M3 | `gates pending` CLI subcommand | +3 |
| M4 | Epistemic inflation prevention tests | +18 |
| M5 | v0.3 DoD runbook | - |

**Total Tests**: 720+ passing

### Non-Negotiables Validated

- ✅ SBLGNT canonical spine (ADR-007)
- ✅ Variants side-by-side (ADR-008)
- ✅ TYPE5+ forbidden in readable mode (ADR-009)
- ✅ Layered confidence always visible (ADR-010)
- ✅ Evidence class explicit (no collapsed scores)
- ✅ Deterministic output (no ML)
- ✅ No copyrighted data in repo
- ✅ **NEW**: No epistemic inflation (explicit test coverage)

### Files Modified/Created

```
src/redletters/__main__.py          # +180 lines: gates group with acknowledge/list/pending
tests/test_dossier_epistemic.py     # NEW: 18+ epistemic inflation tests
docs/RUNBOOK-SCHOLARLY-TOOL-V03.md  # NEW: v0.3 DoD runbook
docs/PROGRESS.md                    # Updated to v0.3.0
```

---

## Milestone: Scholarly Beta

**Date**: 2026-02-01
**Status**: ✓ Complete

### Summary

Extended MVP to a fully functional scholarly tool with provenance-first architecture:
- Full MorphGNT SBLGNT spine support with token-level morphology
- Multi-pack variant system with side-by-side comparison
- Traceable Ledger Mode with T/G/L/I confidence layers
- Gate system for significant variant acknowledgement
- Deterministic, receipt-grade translation output

### Key Additions (Sprints 1-10)

| Sprint | Feature | Tests |
|--------|---------|-------|
| 1 | Provenance-first data model | ~50 |
| 2 | GUI foundations | ~40 |
| 3 | FluentTranslator | ~30 |
| 4 | Claims taxonomy + enforcement | ~60 |
| 5 | Confidence scoring | ~40 |
| 6 | Source management + catalog | ~80 |
| 7 | Variant builder + gates | ~100 |
| 8 | Dossier + evidence class | ~80 |
| 9 | Multi-pack aggregation | ~100 |
| 10 | Traceable Ledger Mode | 38 |

**Total Tests**: 702 passing

### Non-Negotiables Validated

- ✅ SBLGNT canonical spine (ADR-007)
- ✅ Variants side-by-side (ADR-008)
- ✅ TYPE5+ forbidden in readable mode (ADR-009)
- ✅ Layered confidence always visible (ADR-010)
- ✅ Evidence class explicit (no collapsed scores)
- ✅ Deterministic output (no ML)
- ✅ No copyrighted data in repo

### Files Added

```
src/redletters/ledger/              # Token-level ledger module
src/redletters/lexicon/             # Lexicon provider interface
src/redletters/pipeline/traceable_translator.py
src/redletters/sources/             # Source pack management
src/redletters/variants/            # Variant building and storage
gui/src/components/LedgerPanel.tsx  # GUI ledger display
docs/RUNBOOK-SCHOLARLY-BETA.md      # DoD runbook
```

---

## Milestone: MVP Complete

**Date**: 2026-01-26
**Status**: ✓ Complete

### Summary

Built a fully functional multi-reading Greek NT tool using the BMAD methodology (Blueprint → Map → Assemble → Debug). The system generates 3-5 candidate English renderings for Greek text with full interpretive receipts.

---

## Development Timeline

### Phase 1: BMAD Specification
**Duration**: Initial session
**Status**: ✓ Complete

- [x] Defined problem statement and non-negotiables
- [x] Established acceptance tests (8 criteria)
- [x] Defined "plausible reading" operationally
- [x] Specified input/output contracts

### Phase 2: Architecture Design
**Duration**: Initial session
**Status**: ✓ Complete

- [x] Selected stack (Python 3.11 + FastAPI + SQLite)
- [x] Designed database schema (4 tables)
- [x] Defined module boundaries (ingest, engine, api, plugins)
- [x] Specified plugin interfaces (SenseProvider, VariantProvider, WitnessOverlay)

### Phase 3: Implementation
**Duration**: Initial session
**Status**: ✓ Complete

#### Files Created (29 Python files)

**Core Package** (`src/redletters/`):
- [x] `__init__.py` — Package init
- [x] `__main__.py` — CLI entry point (Click + Rich)
- [x] `config.py` — Settings and morphology mappings

**Database** (`src/redletters/db/`):
- [x] `__init__.py`
- [x] `connection.py` — SQLite connection management

**Ingest** (`src/redletters/ingest/`):
- [x] `__init__.py`
- [x] `demo_data.py` — Hardcoded demo corpus (55 tokens, 58 senses)
- [x] `loader.py` — Data loading functions
- [x] `morphology.py` — Morphology code parser

**Engine** (`src/redletters/engine/`):
- [x] `__init__.py`
- [x] `query.py` — Reference parsing and token retrieval
- [x] `senses.py` — Lexeme sense lookup and disambiguation
- [x] `generator.py` — Candidate rendering generator (4 styles)
- [x] `ranker.py` — Deterministic ranking heuristic
- [x] `receipts.py` — Receipt generation utilities

**API** (`src/redletters/api/`):
- [x] `__init__.py`
- [x] `main.py` — FastAPI application
- [x] `routes.py` — API endpoints
- [x] `models.py` — Pydantic schemas

**Plugins** (`src/redletters/plugins/`):
- [x] `__init__.py`
- [x] `base.py` — Protocol definitions
- [x] `sense_provider.py` — Database and composite providers
- [x] `variant_provider.py` — Stub for future variants
- [x] `witness_overlay.py` — Stub for future Syriac support

**Tests** (`tests/`):
- [x] `__init__.py`
- [x] `test_query.py` — Reference parsing tests (8 tests)
- [x] `test_generator.py` — Candidate generation tests (5 tests)
- [x] `test_ranker.py` — Ranking tests (5 tests)
- [x] `test_receipts.py` — Receipt validation tests (4 tests)

**Configuration**:
- [x] `pyproject.toml` — Project metadata and dependencies
- [x] `README.md` — User documentation

### Phase 4: Testing & Verification
**Duration**: Initial session
**Status**: ✓ Complete

- [x] All 22 unit tests passing
- [x] CLI `init` command works
- [x] CLI `query` command produces output
- [x] JSON export works correctly
- [x] Demo data covers 5 passages

---

## Test Results

```
======================== 22 passed in 0.40s ========================

tests/test_generator.py::TestCandidateGenerator::test_generates_all_styles PASSED
tests/test_generator.py::TestCandidateGenerator::test_all_candidates_have_text PASSED
tests/test_generator.py::TestCandidateGenerator::test_token_renderings_match_input PASSED
tests/test_generator.py::TestCandidateGenerator::test_renderings_have_senses PASSED
tests/test_generator.py::TestCandidateGenerator::test_deterministic_output PASSED
tests/test_query.py::TestParseReference::test_simple_reference PASSED
tests/test_query.py::TestParseReference::test_abbreviated_book PASSED
tests/test_query.py::TestParseReference::test_verse_range PASSED
tests/test_query.py::TestParseReference::test_invalid_format_raises PASSED
tests/test_query.py::TestParseReference::test_whitespace_handling PASSED
tests/test_query.py::TestNormalizeBookName::test_lowercase_conversion PASSED
tests/test_query.py::TestNormalizeBookName::test_aliases PASSED
tests/test_query.py::TestNormalizeBookName::test_unknown_book_titlecased PASSED
tests/test_ranker.py::TestRenderingRanker::test_returns_sorted_by_score PASSED
tests/test_ranker.py::TestRenderingRanker::test_includes_score_breakdown PASSED
tests/test_ranker.py::TestRenderingRanker::test_includes_receipts PASSED
tests/test_ranker.py::TestRenderingRanker::test_receipts_completeness PASSED
tests/test_ranker.py::TestRenderingRanker::test_deterministic_ranking PASSED
tests/test_receipts.py::TestReceiptValidation::test_complete_receipt_passes PASSED
tests/test_receipts.py::TestReceiptValidation::test_incomplete_receipt_fails PASSED
tests/test_receipts.py::TestReceiptFormatting::test_bibtex_style_format PASSED
tests/test_receipts.py::TestReceiptFormatting::test_summary_format PASSED
```

---

## Demo Data Statistics

| Category | Count |
|----------|-------|
| Tokens | 55 |
| Lexeme Senses | 58 |
| Speech Spans | 5 |
| Collocations | 8 |
| Unique Lemmas | ~25 |

**Passages Covered**:
1. Matthew 3:2 (7 tokens) — John's proclamation
2. Matthew 4:17 (7 tokens) — Jesus' proclamation
3. Mark 1:15 (15 tokens) — Extended proclamation
4. Matthew 5:3 (12 tokens) — First Beatitude
5. Matthew 6:9-10 (14 tokens) — Lord's Prayer opening

---

## Known Limitations (MVP)

1. **Demo data only** — Not representative of full NT
2. **No real lexicon** — Simplified senses for demo
3. **Basic transformers** — Style transformers need refinement
4. **No variants** — Textual criticism support stubbed
5. **No Syriac** — Witness overlay stubbed
6. **Single-threaded** — No concurrent query optimization

---

## Next Steps

### Immediate (Post-MVP)
- [ ] Add more demo passages (Sermon on the Mount, parables)
- [ ] Refine style transformers for better English
- [ ] Add verse range support to CLI
- [ ] Improve error messages

### Short-term
- [ ] Integrate SBLGNT/MorphGNT data
- [ ] Import real lexicon data (BDAG subset or open alternative)
- [ ] Add API authentication for production use
- [ ] Build simple web UI

### Long-term
- [ ] Implement VariantProvider with NA28 data
- [ ] Implement SyriacOverlay with Peshitta
- [ ] Add user annotation/notes system
- [ ] Performance optimization for full NT

---

## Changelog

### v0.17.0 (2026-02-03) - Contract-First GUI
- ApiContract module: single source of truth for endpoint paths
- All ApiClient methods use contract-derived paths (not hardcoded strings)
- ExportView uses `client.runScholarly()` instead of raw `fetch()`
- ApiErrorPanel shows resolved base URL and capability snapshot in diagnostics
- "Copy Full Diagnostics" includes contract state (baseUrl, capabilities, resolved endpoints)
- contractDiagnostics field added to ApiErrorDetail type
- README.md updated: version 0.17.0, port 47200, GUI documentation section
- docs/gui.md Sprint 17 verification checklist

### v0.16.0 (2026-02-03) - GUI Resilience + Bootstrap
- Unified Engine Spine and API routes into single FastAPI application
- `/v1/capabilities` endpoint for GUI↔backend compatibility handshake
- BootstrapWizard component for first-run onboarding flow
- ApiErrorPanel component with structured error diagnostics (method+URL, status, suggested fix)
- Fixed VariantStore connection type bug (was passing EngineDatabase wrapper, now passes raw Connection)
- ApiCapabilities and ApiErrorDetail TypeScript types
- Sources, PassageWorkspace, and ExportView screens use ApiErrorPanel
- Documentation: bootstrap wizard, error panels, capabilities endpoint

### v0.13.0 (2026-02-02) - One Command Scholarly Run
- `run scholarly` CLI command for end-to-end scholarly workflow orchestration
- ScholarlyRunner class orchestrates: lockfile → gate check → translation → export → snapshot → bundle → verify
- Deterministic run log (RunLog) with provenance: tool version, timestamps, file hashes, gate status
- Gate enforcement: refuses to proceed with pending significant variants unless `--force`
- forced_responsibility recorded in run log when gates bypassed
- RunLogCommand, RunLogFile, RunLogValidation, RunLogGates, RunLogPacksSummary dataclasses
- Run log content hash for integrity verification
- `--mode` flag: traceable (default) or readable
- `--include-schemas` flag to bundle JSON schema files
- `--zip` flag to create distributable archive
- Validator extended with runlog artifact type support
- Run log schema: docs/schemas/runlog-v1.0.0.schema.json
- RUNLOG_SCHEMA_VERSION constant in schema_versions.py
- All existing primitives reused (LockfileGenerator, SnapshotGenerator, BundleCreator, etc.)
- 1080+ passing tests

### v0.12.0 (2026-02-02) - Deterministic Research Bundle
- `bundle create` CLI to assemble reproducible bundles (lockfile + snapshot + artifacts)
- `bundle verify` CLI to validate bundle integrity via SHA-256 hashes
- `bundle inspect` CLI to view manifest details
- Bundle manifest with deterministic serialization (sorted artifacts, canonical JSON)
- Content hash fingerprint for entire bundle (concatenated artifact hashes)
- Optional `--include-schemas` to bundle JSON schema files
- Optional `--zip` to create distributable archive
- Tamper detection: any file modification causes verification to fail
- Bundle schema: docs/schemas/bundle-v1.0.0.schema.json
- 1068+ passing tests

### v0.11.0 (2026-02-02) - Pack Lockfile + Integrity Checks
- `packs lock` CLI to generate lockfile.json from installed state
- `packs sync` CLI to verify/sync environment against lockfile
- Lockfile includes content hashes for pack integrity verification
- Snapshot includes lockfile_hash for provenance chain
- Lockfile schema: docs/schemas/lockfile-v1.0.0.schema.json
- --force flag on sync to accept hash mismatches with audit trail
- 1046+ passing tests

### v0.10.0 (2026-02-02) - Schema Contracts + Validation
- JSON Schema files for all public artifacts (apparatus, translation, quote, snapshot, citations, dossier)
- Centralized schema version constants in `src/redletters/export/schema_versions.py`
- CLI validator: `redletters validate output <path>` with --type and --json options
- Auto-detect artifact type from filename/content
- Validator fails on tampered/incomplete output (deterministic error messages)
- Snapshot includes `schema_versions` mapping for all artifact types
- Dossier includes `schema_version` field
- Quote command uses centralized QUOTE_SCHEMA_VERSION constant
- DoD runbook: docs/RUNBOOK-SCHOLARLY-TOOL-V10.md
- 1020+ passing tests

### v0.9.0 (2026-02-02) - Minority Metadata + Incentive Tags + Quote Friction
- MinorityMetadata on readings: attestation_strength (strong/moderate/weak/None)
- historical_uptake and ideological_usage fields (pack-provided, not derived)
- Incentive tags: brevity_preference_present, age_bias_risk (neutral labels)
- `redletters quote` CLI command for citeable output with gate friction
- Quote friction: fails with PendingGatesError unless gates cleared or --force
- forced_responsibility=true in output when quote is forced past pending gates
- Project goals documentation: docs/GOALS.md
- DoD runbook: docs/RUNBOOK-SCHOLARLY-TOOL-V09.md
- 991+ passing tests

### v0.8.0 (2026-02-02) - Uncertainty Propagation + Export Friction
- Confidence bucketing: high (≥0.8) / medium (≥0.6) / low (<0.6)
- ConsequenceSummary: affects_surface, affects_gloss, affects_omission_addition
- PackCoverage: records absence as meaningful data in dossier
- Export friction: PendingGatesError blocks exports until gates acknowledged
- Claims analyzer: `claims analyze` CLI for reversible theology
- Translation exports include composite confidence score and bucket
- Snapshot includes confidence_bucketing_version for reproducibility
- `--force` flag on exports to bypass gate checks
- `--session-id` flag on exports for acknowledgement tracking
- Sample claims file: docs/examples/claims.sample.json
- 942+ passing tests

### v0.7.0 (2026-02-02) - Pack Explainability + Citation Export
- Sense resolution explainer: `senses explain <lemma>` shows audit trail
- Cross-pack conflict detection: `senses conflicts <lemma>` detects disagreements
- Sense pack listing: `senses list-packs` shows precedence order
- Citation export: `export citations` for CSL-JSON bibliography
- Greek lemma normalization for consistent cross-pack lookups
- Snapshot integration: `--include-citations` flag auto-generates citations
- Deterministic: same packs = identical citations hash
- 875+ passing tests
- DoD runbook: docs/RUNBOOK-SCHOLARLY-TOOL-V07.md

### v0.6.0 (2026-02-02) - Sense Packs + Citation-Grade Provenance
- Installable sense packs with citation-grade metadata
- SensePackManifest schema: source_id, source_title, edition, publisher, year, license_url
- SensePackLoader for TSV/JSON sense data validation and loading
- SensePackDB for SQLite persistence with citation metadata
- SensePackProvider with ChainedSenseProvider fallback
- Citation-grade provenance in receipts, ledger, and exports
- PackInfo snapshots include full bibliographic metadata
- Sample sense pack with 52 NT vocabulary entries
- License acceptance gating for non-CC0/PD packs
- 830+ passing tests

### v0.5.0 (2026-02-02) - Reproducible Scholar Exports
- Export CLI group: `export apparatus|translation|snapshot|verify`
- Stable identifiers: verse_id, variant_unit_id, reading_id, token_id
- Canonical JSON serialization for deterministic hashing
- Apparatus JSONL export with readings, support, and provenance
- Translation JSONL export with token ledger and confidence
- Snapshot generation with pack metadata and export hashes
- Snapshot verification for reproducibility validation
- DoD runbook: docs/RUNBOOK-SCHOLARLY-TOOL-V05.md
- 771+ passing tests

### v0.4.0 (2026-02-02) - Multi-Pack Apparatus
- Multi-pack variant aggregation: 2+ packs merge to ONE VariantUnit per location
- Structured support set with witness siglum, witness_type, century_range, source_pack_id
- Gate count stability: ONE gate per merged VariantUnit (not packs × locations)
- Acknowledge once suppresses future gates for that VariantUnit
- Idempotent rebuild: UNIQUE constraints prevent duplicate support entries
- Dossier provenance lists all contributing packs
- PackLoader fixes for Pack Spec v1.1 compatibility
- DoD runbook: docs/RUNBOOK-SCHOLARLY-TOOL-V04.md
- 733+ passing tests

### v0.3.0 (2026-02-01) - Scholarly Tool
- Standalone `gates acknowledge` CLI for audit-trail acknowledgements
- `gates list` CLI to view acknowledged gates by session
- `gates pending` CLI to show unacknowledged TYPE3+ variants
- Epistemic inflation prevention test suite (18+ tests)
- DoD runbook: docs/RUNBOOK-SCHOLARLY-TOOL-V03.md
- 720+ passing tests

### v0.2.0 (2026-02-01) - Scholarly Beta
- Full MorphGNT SBLGNT spine with token-level morphology
- Source pack system with catalog and EULA support
- Multi-pack variant builder with aggregation rules
- Gate system for significant variant acknowledgement
- Traceable Ledger Mode with T/G/L/I confidence layers
- LexiconProvider interface with BasicGlossProvider (~90 CC0 words)
- Evidence class explicit (manuscript/edition/tradition counts)
- CLI: `sources`, `variants`, `translate --traceable --ledger`
- GUI: LedgerPanel with confidence visualization
- 702 passing tests
- DoD runbook: docs/RUNBOOK-SCHOLARLY-BETA.md

### v0.1.0 (2026-01-26)
- Initial MVP release
- 4 rendering styles (ultra-literal, natural, meaning-first, jewish-context)
- Full receipt system with lexical citations
- CLI with query and list-spans commands
- FastAPI endpoints for programmatic access
- 22 passing tests
- Demo data for 5 passages
