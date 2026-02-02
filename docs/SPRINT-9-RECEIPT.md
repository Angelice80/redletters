# Sprint 9 Receipt: Multi-Pack Aggregation + Real Witness Support Semantics

**Sprint Goal**: Multi-pack aggregation + real witness support semantics. Move from single-pack variant building to multiple packs contributing to a single VariantUnit with explicit, deduplicated support sets per reading.

**Completion Date**: 2026-02-01
**Status**: Complete

---

## Deliverables Summary

| Backlog Item | Status | Evidence |
|--------------|--------|----------|
| B1: True Witness Support Model | DONE | `WitnessSupportType`, `WitnessSupport`, `reading_support` table |
| B2: Multi-Pack Variant Aggregation | DONE | `normalize_for_aggregation()`, merge mode in builder |
| B3: Dossier Upgrade | DONE | `SupportSummary`, `determine_evidence_class()` |
| B4: Gate Hygiene | DONE | Gates work with merged VariantUnit, no duplicate acks |
| B5: CLI --all-installed + API | DONE | CLI flag, `include_all_installed_sources` param |

---

## B1: True Witness Support Model

### Data Model

```python
class WitnessSupportType(str, Enum):
    """Type classification for witness attestation."""
    EDITION = "edition"       # Critical edition (e.g., WH, NA28)
    MANUSCRIPT = "manuscript" # Greek manuscript (e.g., P66, Sinaiticus)
    TRADITION = "tradition"   # Textual tradition (e.g., Byzantine)
    OTHER = "other"           # Everything else

@dataclass
class WitnessSupport:
    """Structured witness attestation with provenance."""
    witness_siglum: str                           # e.g., "WH", "P66", "Byz"
    witness_type: WitnessSupportType              # Type classification
    source_pack_id: str                           # Pack that provided this
    century_range: tuple[int, int] | None = None  # [earliest, latest] if known
```

### Database Schema Addition

```sql
CREATE TABLE IF NOT EXISTS reading_support (
    id INTEGER PRIMARY KEY,
    reading_id INTEGER NOT NULL REFERENCES witness_readings(id) ON DELETE CASCADE,
    witness_siglum TEXT NOT NULL,
    witness_type TEXT NOT NULL,
    century_earliest INTEGER,
    century_latest INTEGER,
    source_pack_id TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(reading_id, witness_siglum, source_pack_id)
);
CREATE INDEX IF NOT EXISTS idx_reading_support_reading ON reading_support(reading_id);
```

### Helper Methods on WitnessReading

- `get_support_by_type(witness_type: WitnessSupportType) -> list[WitnessSupport]`
- `get_source_packs() -> list[str]`

---

## B2: Multi-Pack Variant Aggregation

### Reading Normalization

The `normalize_for_aggregation()` function ensures identical readings from different packs are grouped together:

```python
def normalize_for_aggregation(text: str) -> str:
    """Normalize Greek text for reading comparison."""
    # NFD decomposition
    text = unicodedata.normalize("NFD", text)
    # Remove combining marks (accents)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # Lowercase
    text = text.lower()
    # Collapse whitespace
    text = " ".join(text.split())
    # Remove punctuation
    text = re.sub(r"[^\w\s]", "", text)
    return text
```

### Aggregation Algorithm

1. Load spine reading for verse
2. For each installed comparative pack:
   - Get reading at verse position
   - Normalize for comparison
   - If different from spine: check for existing reading with same normalized form
   - If found: add support to existing reading (deduplicated)
   - If not found: create new reading with support
3. Merge mode ensures idempotency - rebuilding with same packs produces same result

### Builder Changes

- `build_verse(verse_id, merge_mode=True)` - Default merge mode for aggregation
- `_merge_into_existing(variant_id, edition_key, spine, reading_text, supports)` - Merges new supports into existing readings
- Support deduplication via `UNIQUE(reading_id, witness_siglum, source_pack_id)` constraint

---

## B3: Dossier Upgrade

### Support Summary Model

```python
@dataclass
class TypeSummary:
    """Support count for a specific witness type."""
    count: int
    sigla: list[str]

@dataclass
class SupportSummary:
    """Summary of all support for a reading."""
    total: int
    by_type: dict[str, TypeSummary]  # keyed by WitnessSupportType value
    source_packs: list[str]
```

### Evidence Class Labels

The `determine_evidence_class()` function provides informational labels without epistemic inflation:

```python
def determine_evidence_class(support_summary: SupportSummary) -> str:
    """Determine evidence class label for a reading's support set."""
    types_present = set(support_summary.by_type.keys())

    if types_present == {"edition"}:
        return "edition-level evidence"
    elif types_present == {"manuscript"}:
        return "manuscript-level evidence"
    elif types_present == {"tradition"}:
        return "tradition-level evidence"
    elif "manuscript" in types_present and "edition" in types_present:
        return "multi-source evidence (manuscript + edition)"
    elif "tradition" in types_present and len(types_present) > 1:
        return "multi-source evidence (tradition + other)"
    elif types_present == {"other"}:
        return "other evidence"
    elif len(types_present) > 1:
        return "multi-source evidence"
    else:
        return "unclassified evidence"
```

### DossierReading Enhancements

- `support_summary: SupportSummary` - Counts by witness type
- `evidence_class: str` - Informational label (no epistemic claims)

---

## B4: Gate Hygiene

### No Changes to Gating Logic

Gates continue to work exactly as before:
- Significance-based gating (SIGNIFICANT/MAJOR require acknowledgement)
- Session-scoped acknowledgements
- No duplicate acks possible due to existing UNIQUE constraints

### Merged VariantUnit Behavior

- Gates apply to the merged VariantUnit, not individual pack contributions
- A reading with support from 3 packs requires ONE acknowledgement, not three
- Existing `get_variants_for_verse()` returns merged variants

---

## B5: CLI --all-installed + API Parameter

### CLI Changes

```bash
# Build with all installed comparative packs (default)
redletters variants build John.1 --all-installed

# Build with specific packs only
redletters variants build John.1 --pack westcott-hort-john --pack byzantine-john

# Scope options
redletters variants build John --scope book --all-installed
redletters variants build John.1 --scope chapter --all-installed
redletters variants build John.1.18 --scope passage --all-installed
```

### API Changes

`VariantBuildRequest` model updated:

```python
class VariantBuildRequest(BaseModel):
    reference: str
    scope: str = "passage"
    source_id: str | None = None  # Legacy single-pack
    force: bool = False
    include_all_installed_sources: bool = True  # Default: use all packs
    source_pack_ids: list[str] | None = None    # Override with specific packs
```

---

## Test Coverage

### Test File

`tests/integration/test_sprint9_multipack.py` - 26 tests

### Test Classes

1. **TestWitnessSupportType** (2 tests)
   - Enum values
   - String conversion

2. **TestWitnessSupport** (2 tests)
   - Dataclass creation
   - None century range

3. **TestNormalization** (5 tests)
   - Accent removal
   - Case normalization
   - Whitespace collapse
   - Punctuation removal
   - Full normalization

4. **TestWitnessTypeMapping** (4 tests)
   - Edition mapping
   - Manuscript mapping
   - Unknown type defaults to OTHER
   - Case insensitivity

5. **TestSupportDedupe** (2 tests)
   - Identical support deduplication
   - Different packs preserved

6. **TestEvidenceClass** (4 tests)
   - Edition-only evidence
   - Manuscript-only evidence
   - Multi-source evidence
   - Empty support summary

7. **TestMultiPackAggregation** (4 tests)
   - Multiple packs contribute to single variant
   - Reading normalization groups identical texts
   - Support sets merged correctly
   - Rebuild idempotency

8. **TestDossierWithSupportSummary** (3 tests)
   - Support summary in dossier readings
   - Evidence class labeling
   - Source pack provenance

### Test Results

```
26 passed, 0 failed
```

### Full Suite

```
664 passed, 0 failed (24.83s)
```

---

## Non-Negotiables Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| ADR-007: SBLGNT canonical spine | PASSED | Spine always position 0, sblgnt_reading_index = 0 |
| ADR-008: Variants side-by-side | PASSED | All readings with support sets shown together |
| ADR-009: Claim gating | PASSED | Gating unchanged, works on merged VariantUnit |
| ADR-010: Layered confidence | PASSED | Confidence scoring infrastructure unchanged |
| Full test suite | PASSED | 664/664 tests passing |

---

## Files Changed

### New Files

- `tests/integration/test_sprint9_multipack.py` - 26 Sprint 9 tests
- `docs/SPRINT-9-MAP.md` - Sprint 9 planning document
- `docs/SPRINT-9-RECEIPT.md` - This document

### Modified Files

- `src/redletters/variants/models.py`
  - `WitnessSupportType` enum
  - `WitnessSupport` dataclass
  - `WitnessReading.support_set` field
  - Helper methods: `get_support_by_type()`, `get_source_packs()`

- `src/redletters/variants/store.py`
  - `reading_support` table schema
  - `_save_support()`, `add_support_to_reading()` methods
  - `_load_support_set()` for retrieval
  - `get_reading_id_by_normalized()`, `get_variant_id()`, `add_reading_to_variant()` for aggregation

- `src/redletters/variants/builder.py`
  - `normalize_for_aggregation()` function
  - `map_witness_type_to_support_type()` function
  - `dedupe_support_set()` function
  - `build_verse()` merge_mode parameter
  - `_merge_into_existing()` method

- `src/redletters/variants/dossier.py`
  - `TypeSummary`, `SupportSummary` dataclasses
  - `determine_evidence_class()` function
  - `DossierReading.support_summary` and `evidence_class` fields
  - `_build_support_summary()` method

- `src/redletters/__main__.py`
  - `variants_build` command rewritten
  - `--all-installed` flag (default True)
  - `--pack` option for specific pack selection

- `src/redletters/api/models.py`
  - `VariantBuildRequest.include_all_installed_sources` field
  - `VariantBuildRequest.source_pack_ids` field

- `src/redletters/api/routes.py`
  - `/variants/build` endpoint updated for multi-pack
  - Fixed forward reference issue

- `tests/test_source_pack.py`
  - `test_idempotent_rebuild` updated for merge mode behavior

- `tests/integration/test_source_pack_vertical_slice.py`
  - `test_rebuild_does_not_duplicate` updated for merge mode behavior

---

## Acceptance Criteria Checklist

- [x] WitnessSupportType enum with 4 types
- [x] WitnessSupport dataclass with provenance
- [x] reading_support table with UNIQUE constraint
- [x] normalize_for_aggregation() handles Greek text
- [x] Multi-pack aggregation merges identical readings
- [x] Support sets deduplicated across packs
- [x] Rebuild is idempotent (same result on re-run)
- [x] SupportSummary with counts by witness type
- [x] Evidence class labels without epistemic inflation
- [x] CLI --all-installed flag
- [x] API include_all_installed_sources parameter
- [x] Gates work with merged VariantUnit
- [x] No duplicate acknowledgements possible
- [x] All tests passing (664/664)

---

## Known Limitations

1. **Normalization aggressiveness**: Current normalization removes all accents and punctuation. Very similar but semantically distinct readings (e.g., different word order) would still be separate.

2. **Century range**: Currently stored but not used in evidence class determination. Future enhancement could weight by manuscript age.

3. **Support summary caching**: Support summaries are computed on-demand for dossiers. For very large variant sets, pre-computation might improve performance.

---

## Sprint 10 Recommendations

1. **Manuscript packs**: Add real manuscript readings (P66, P75, Sinaiticus, Vaticanus) to demonstrate manuscript-level evidence
2. **Evidence weighting**: Use century_range to weight witness quality in evidence class
3. **Performance optimization**: Pre-compute support summaries for frequently accessed variants
4. **Export formats**: Add PDF/HTML export with full support documentation for scholarly citation
5. **Translation backend**: Integrate LLM for fluent translation with variant awareness
