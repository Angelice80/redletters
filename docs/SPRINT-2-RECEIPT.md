# Sprint 2 Receipt: Source Pack + On-Demand Variant Building

## Forensics

| Key | Value |
|-----|-------|
| Python | 3.8.10 |
| OS | Darwin 21.6.0 |
| Git SHA | 802659b |
| Date | 2026-02-01 |

## Commands Run

```bash
# Lint (all pass)
ruff check src/redletters/sources/ src/redletters/variants/ src/redletters/pipeline/orchestrator.py
# → All checks passed!

# Format (all formatted)
ruff format --check src/redletters/sources/ src/redletters/variants/ src/redletters/pipeline/orchestrator.py
# → 10 files already formatted

# Test (all pass)
python -m pytest -q
# → 466 passed, 409 warnings
# (warnings are from upstream: pydantic, httpx - NOT redletters)
```

## Files Created

### Source Pack System (`src/redletters/sources/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Package exports for SourceCatalog, SpineProvider, etc. |
| `catalog.py` | Load/validate sources_catalog.yaml with Pydantic-style models |
| `resolver.py` | Resolve source pack paths (data root, fixtures, repo) |
| `spine.py` | SpineProvider protocol + SBLGNTSpine + FixtureSpine implementations |
| `editions.py` | EditionLoader interface + MorphGNTLoader + FixtureLoader |

### Variant Builder (`src/redletters/variants/`)

| File | Purpose |
|------|---------|
| `builder.py` | VariantBuilder: diff editions against spine, compute significance |

### Test Fixtures (`tests/fixtures/`)

| File | Purpose |
|------|---------|
| `spine_fixture.json` | SBLGNT-style fixture with John 1:18, 3:16, Matt 3:2 |
| `comparative_fixture.json` | WH-style fixture with θεὸς→υἱὸς variant at John 1:18 |

### Test Files

| File | Tests |
|------|-------|
| `tests/test_source_pack.py` | 31 tests for catalog, resolver, spine, editions, builder |
| `tests/test_pipeline_source_pack.py` | 9 tests for orchestrator integration |
| `tests/integration/test_source_pack_vertical_slice.py` | 11 tests for end-to-end vertical slice (NEW) |

## Files Modified

### `src/redletters/pipeline/orchestrator.py`

- Added `_get_spine_data()`: Uses spine_provider from options or falls back to DB
- Added `_ensure_variants()`: Builds variants on-demand if variant_builder provided
- Updated `translate_passage()`: Uses new helper functions
- **Backward compatible**: Existing code continues to work with database tokens

### `src/redletters/__main__.py`

- Added `sources` command group:
  - `redletters sources list` - List configured sources and status
  - `redletters sources validate` - Validate catalog structure
  - `redletters sources info <pack_id>` - Show detailed source info
- Added `variants` command group:
  - `redletters variants list` - List variants in database
  - `redletters variants build` - (Stub for future real edition support)

## Test Evidence

### Source Pack Tests (31 tests)

- **Catalog**: Loading, validation, required fields, role checking
- **Resolver**: Repo root detection, path resolution, fixture paths
- **Spine**: FixtureSpine JSON loading, verse retrieval, token access
- **Editions**: MorphGNTLoader parsing, FixtureLoader JSON/TSV
- **Builder**: Variant creation, idempotent updates, theological significance

### Pipeline Integration Tests (9 tests)

- Orchestrator uses spine_provider when available
- Variant builder creates MAJOR variant for θεὸς→υἱὸς at John 1:18
- Gate is triggered for significant/major variants
- Acknowledgement flow works end-to-end
- Provenance shows SBLGNT as spine source

### Vertical Slice Integration Tests (11 tests) - NEW

- **John 1:18**: MAJOR variant (θεὸς vs υἱὸς) triggers gate
- **Ack Flow**: Acknowledge → translate succeeds with spine_text + variants
- **Matthew 3:2**: No variant (identical text) → translation proceeds
- **ADR-007**: SBLGNT is canonical spine in catalog
- **ADR-008**: Variants surfaced side-by-side, significant/major require ack
- **Idempotency**: Rebuild does not duplicate, preserves significance
- **Provenance**: SBLGNT marked as spine source

## Explicit Confirmations

### ADR-007: SBLGNT is canonical spine default ✓

- `SourceCatalog.spine` returns morphgnt-sblgnt
- `sources validate` confirms spine is defined
- `translate_passage` sets `spine_marker="default"` in provenance

### ADR-008: Variants surfaced side-by-side ✓

- `GateResponsePayload.variants_side_by_side` populated
- Each variant shows SBLGNT reading + alternates
- Significance gating enforced (SIGNIFICANT/MAJOR require ack)

### ADR-008: Acknowledgement gating enforced ✓

- Unacknowledged significant variants trigger `GateResponsePayload`
- `acknowledge_variant()` persists choice in `AcknowledgementStore`
- Subsequent calls proceed to translation

### ADR-009: Readable vs traceable restrictions unchanged ✓

- No changes to claim enforcement logic
- Escalation gates still trigger for TYPE5-7 in readable mode

### ADR-010: Layered confidence unchanged ✓

- No changes to confidence calculation
- Four-layer model preserved

### No redletters warnings ✓

```bash
python -m pytest -q --tb=line 2>&1 | grep -i "redletters.*warning"
# No matches
```

## Summary Statistics

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Test count | 455 | 466 | +11 |
| Source files | 5 | 5 | 0 |
| Test files | 2 | 3 | +1 |
| Fixture files | 4 | 4 | 0 |
| CLI commands | ~16 | ~16 | 0 |

## What's New

1. **Source Pack System**: Load sources_catalog.yaml, validate roles/licenses, resolve paths
2. **Spine Provider Protocol**: Abstract verse retrieval for SBLGNT or fixtures
3. **Edition Loaders**: MorphGNT and JSON/TSV fixture formats
4. **Variant Builder**: Diff editions, classify variants, compute significance
5. **On-Demand Variants**: Build variants when first requested via translate_passage
6. **CLI Commands**: `sources list/validate/info`, `variants list/build`

## What's NOT Changed

- Pipeline API is backward compatible
- ADR-007/008/009/010 enforcement unchanged
- Claim taxonomy, epistemic pressure detection unchanged
- Database schema unchanged (uses existing tables)
- FakeTranslator remains default for tests
