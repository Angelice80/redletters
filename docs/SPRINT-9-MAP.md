# SPRINT-9-MAP: Multi-Pack Aggregation + True Witness Support

**Sprint Goal**: Move from "one comparative pack at a time" to "many packs contribute to a single VariantUnit with explicit, deduped support sets per reading."

**Date**: 2026-02-01
**Status**: PLANNING

---

## 1. Current State Analysis

### What Exists (Sprint 8 Delivery)
- `source_pack_id` tracked at `WitnessReading` level
- Single-pack builds via `VariantBuilder.add_edition()` + `build_chapter()`
- Dossier exports with provenance (`comparative_packs[]`)
- Gate triggers based on `VariantUnit.significance`
- Pack Spec v1.1 with `siglum`, `witness_type`, `century_range`

### Gap Analysis for Multi-Pack World
| Current | Sprint 9 Target |
|---------|-----------------|
| One pack → one build pass | Multiple packs → single aggregated build |
| Witness sigla stored as strings in list | Structured support entries with type/century |
| No deduplication across packs | Dedupe by (siglum, reading_text) |
| Per-pack VariantUnits possible | Single merged VariantUnit per (ref, position) |
| Dossier shows `source_packs[]` flat | Dossier shows evidence class + counts by type |

---

## 2. Data Model Changes

### 2.1 New: `WitnessSupport` Structure

```python
@dataclass
class WitnessSupport:
    """Individual witness attestation for a reading."""
    witness_siglum: str           # "P66", "01", "WH", "Byz"
    witness_type: WitnessSupportType  # edition | manuscript | tradition | other
    century_range: tuple[int, int] | None  # (1, 2) = 1st-2nd century
    source_pack_id: str           # Provenance: which pack contributed this

@dataclass
class WitnessSupportType(str, Enum):
    EDITION = "edition"           # Critical editions (WH, NA28, SBLGNT)
    MANUSCRIPT = "manuscript"     # Specific MSS (P66, 01, 03)
    TRADITION = "tradition"       # Tradition aggregates (Byz, f1, f13)
    OTHER = "other"               # Fathers, versions, etc.
```

**Mapping from existing `WitnessType`**:
| Current WitnessType | New WitnessSupportType | Notes |
|---------------------|------------------------|-------|
| PAPYRUS | MANUSCRIPT | P66, P75, etc. |
| UNCIAL | MANUSCRIPT | 01 (Sinaiticus), 03 (Vaticanus) |
| MINUSCULE | MANUSCRIPT | Numbered MSS |
| VERSION | OTHER | Old Latin, Syriac, etc. |
| FATHER | OTHER | Church fathers |
| (new) | EDITION | WH, Tischendorf, NA28 |
| (new) | TRADITION | Byz, f1, f13 aggregates |

### 2.2 Enhanced `WitnessReading`

```python
@dataclass
class WitnessReading:
    surface_text: str
    normalized_text: str | None
    notes: str | None
    # EXISTING (Sprint 8)
    witnesses: list[str]              # Legacy: flat siglum list
    witness_types: list[WitnessType]  # Legacy: parallel types
    date_range: tuple[int, int] | None
    source_pack_id: str | None        # Single pack provenance

    # NEW (Sprint 9): Structured support set
    support_set: list[WitnessSupport] = field(default_factory=list)

    def get_support_by_type(self) -> dict[WitnessSupportType, list[WitnessSupport]]:
        """Group support entries by witness type."""
        ...

    def get_earliest_century(self) -> int | None:
        """Return earliest attested century from support set."""
        ...

    def get_source_packs(self) -> list[str]:
        """Unique source_pack_ids from support set."""
        ...
```

### 2.3 Database Schema Changes

**New table: `reading_support`** (replaces implicit witness storage)

```sql
CREATE TABLE reading_support (
    id INTEGER PRIMARY KEY,
    reading_id INTEGER NOT NULL REFERENCES witness_readings(id) ON DELETE CASCADE,
    witness_siglum TEXT NOT NULL,
    witness_type TEXT NOT NULL,  -- 'edition', 'manuscript', 'tradition', 'other'
    century_earliest INTEGER,
    century_latest INTEGER,
    source_pack_id TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    -- Dedupe: same witness can't support same reading twice from same pack
    UNIQUE(reading_id, witness_siglum, source_pack_id)
);

CREATE INDEX idx_reading_support_reading ON reading_support(reading_id);
CREATE INDEX idx_reading_support_siglum ON reading_support(witness_siglum);
CREATE INDEX idx_reading_support_type ON reading_support(witness_type);
```

**Migration strategy**:
1. Create new `reading_support` table
2. Migrate existing `reading_witnesses` data → `reading_support`
3. Retain `reading_witnesses` for backward compatibility (deprecated)
4. New code writes to `reading_support`; reads from both

---

## 3. Aggregation Algorithm

### 3.1 Multi-Pack Build Flow

```
Input: SBLGNT spine + [pack_1, pack_2, ..., pack_n]

For each verse_id in scope:
    1. Load SBLGNT tokens for verse
    2. For each comparative pack:
        a. Load pack tokens for verse
        b. Align tokens (existing diff algorithm)
        c. Collect raw differences as PackReading{text, siglum, type, century, pack_id}

    3. Normalize all readings (same normalizer everywhere)

    4. Group by (position, normalized_text):
        - Identical normalized texts → merge support sets
        - Different texts → separate readings

    5. Deduplicate support within each reading:
        - Key: (siglum, witness_type)
        - If same witness appears from multiple packs:
          → Keep all entries (different provenance)
          → BUT: Mark as "same_witness_multiple_packs" for UI warning

    6. Upsert to VariantStore:
        - If VariantUnit exists for (ref, position):
          → Merge new readings into existing
          → Add new support entries (skip duplicates via UNIQUE constraint)
        - If new:
          → Create fresh VariantUnit

    7. Re-classify significance (may change with more witnesses)
```

### 3.2 Normalization Rules

```python
def normalize_for_aggregation(text: str) -> str:
    """Canonical normalization for reading comparison."""
    # 1. Remove combining diacriticals (breathing, accents)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')

    # 2. Lowercase
    text = text.lower()

    # 3. Collapse whitespace
    text = ' '.join(text.split())

    # 4. Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)

    return text
```

### 3.3 Deduplication Rules

**Rule 1: Same siglum, same pack → ERROR** (should never happen)
**Rule 2: Same siglum, different packs → KEEP BOTH** (different provenance)
**Rule 3: Same siglum, same type, same century → FLAG** (potential double-count)

```python
def dedupe_support_set(supports: list[WitnessSupport]) -> tuple[list[WitnessSupport], list[str]]:
    """Dedupe support entries, return (deduped_list, warnings)."""
    seen: dict[tuple[str, str], WitnessSupport] = {}  # (siglum, type) -> first entry
    warnings = []
    result = []

    for s in supports:
        key = (s.witness_siglum, s.witness_type)
        if key in seen:
            # Same witness type/siglum from different pack
            existing = seen[key]
            if existing.source_pack_id != s.source_pack_id:
                # Different packs → keep both for provenance, but warn
                warnings.append(
                    f"Witness {s.witness_siglum} appears in multiple packs: "
                    f"{existing.source_pack_id}, {s.source_pack_id}"
                )
                result.append(s)
            # Same pack → skip (dedupe)
        else:
            seen[key] = s
            result.append(s)

    return result, warnings
```

### 3.4 Idempotency Guarantees

```python
def build_with_idempotency(verse_id: str, packs: list[Pack]) -> BuildResult:
    """Idempotent build: running twice produces same result."""

    # Strategy: Delete + Rebuild for clean state
    # OR: Upsert with conflict resolution

    # Chosen approach: UPSERT with support_set merge
    existing = store.get_variant(ref, position)
    if existing:
        # Merge readings by normalized_text
        for new_reading in computed_readings:
            matched = find_reading_by_normalized(existing.readings, new_reading.normalized_text)
            if matched:
                # Add support entries (UNIQUE constraint handles dupes)
                for support in new_reading.support_set:
                    store.add_support_if_not_exists(matched.id, support)
            else:
                # New reading text → add to unit
                store.add_reading(existing.id, new_reading)
    else:
        store.save_variant(new_unit)
```

---

## 4. Dossier Upgrade

### 4.1 New Dossier Fields

```python
@dataclass
class DossierReading:
    index: int
    text: str
    is_spine: bool
    # EXISTING
    witnesses: list[WitnessInfo]
    witness_summary: WitnessSummary
    source_packs: list[str]

    # NEW (Sprint 9)
    support_summary: SupportSummary
    evidence_class: str  # "edition-level" | "manuscript-level" | "tradition aggregate" | "mixed"

@dataclass
class SupportSummary:
    """Counts and details by witness type."""
    total_count: int
    by_type: dict[str, TypeSummary]  # "edition" -> TypeSummary
    earliest_century: int | None
    provenance_packs: list[str]

@dataclass
class TypeSummary:
    count: int
    sigla: list[str]  # Collapsed in GUI, expandable
    century_range: tuple[int, int] | None
```

### 4.2 Evidence Class Labels

```python
def determine_evidence_class(support_summary: SupportSummary) -> str:
    """Determine evidence class label for a reading."""
    types_present = set(support_summary.by_type.keys())

    if types_present == {"edition"}:
        return "edition-level evidence"
    elif types_present == {"manuscript"}:
        return "manuscript-level evidence"
    elif types_present == {"tradition"}:
        return "tradition aggregate"
    elif "manuscript" in types_present:
        return "manuscript-level evidence"  # Prioritize manuscript if present
    else:
        return "mixed evidence"
```

### 4.3 No Epistemic Inflation Rule

**CRITICAL**: The dossier MUST NOT make claims like:
- "This reading is more likely original because..."
- "Earlier manuscripts suggest..."
- "The weight of evidence supports..."

**ALLOWED**:
- "Earliest attestation: 2nd century"
- "Supported by 3 manuscripts, 2 editions"
- "Evidence class: manuscript-level"

---

## 5. Gate Hygiene

### 5.1 Gate Trigger on Merged Unit

```python
def detect_variant_gates(verse_id: str) -> list[Gate]:
    """Detect gates based on merged VariantUnit, not per-pack."""

    # Get the SINGLE merged VariantUnit for this verse/position
    variants = store.get_variants_for_verse(verse_id)

    gates = []
    for v in variants:
        if v.requires_acknowledgement:
            # Create ONE gate per VariantUnit
            gates.append(Gate.for_variant(
                variant_ref=f"{v.ref}:{v.position}",
                readings=v.readings,  # Merged readings with full support
                sblgnt_index=v.sblgnt_reading_index,
            ))

    return gates
```

### 5.2 Acknowledgement Deduplication

```python
def get_required_acks(verse_id: str) -> list[str]:
    """Return unique variant refs requiring acknowledgement."""
    variants = store.get_significant_variants_for_verse(verse_id)

    # Each VariantUnit needs ONE ack, regardless of how many packs contributed
    return [f"{v.ref}:{v.position}" for v in variants if v.requires_acknowledgement]
```

---

## 6. CLI + API Surface

### 6.1 CLI: `redletters variants build`

```bash
# Existing (unchanged)
redletters variants build "John.1" --scope chapter

# New: --all-installed flag (default behavior)
redletters variants build "John.1" --scope chapter --all-installed

# Explicit pack selection (future)
redletters variants build "John.1" --scope chapter --packs westcott-hort-john,byzantine-john
```

**Implementation**:
```python
@app.command("build")
def build_variants(
    reference: str,
    scope: str = "chapter",
    all_installed: bool = True,  # New: default True
    packs: list[str] | None = None,  # Future: explicit selection
):
    """Build variants using installed comparative packs."""
    if all_installed:
        packs = catalog.get_installed_comparative_packs()

    builder = VariantBuilder(spine, store)
    for pack in packs:
        builder.add_edition_from_pack(pack)

    result = builder.build_scope(reference, scope)
    ...
```

### 6.2 API: `POST /variants/build`

```python
class VariantBuildRequest(BaseModel):
    reference: str
    scope: str = "verse"
    source_id: int | None = None
    force: bool = False
    # NEW (Sprint 9)
    include_all_installed_sources: bool = True  # Default: use all packs
    source_pack_ids: list[str] | None = None    # Future: explicit selection
```

**Backward compatibility**: If neither new field is set, use existing single-pack behavior.

---

## 7. Test Plan

### 7.1 Unit Tests

| Test | What It Proves |
|------|----------------|
| `test_support_set_dedupe_same_pack` | Same siglum from same pack → single entry |
| `test_support_set_dedupe_diff_packs` | Same siglum from different packs → both kept |
| `test_normalize_for_aggregation` | Normalization consistent (accents, case, whitespace) |
| `test_reading_grouping_by_normalized` | Identical normalized texts → merged |
| `test_evidence_class_edition_only` | Edition-only support → "edition-level evidence" |
| `test_evidence_class_manuscript` | Manuscript support → "manuscript-level evidence" |
| `test_evidence_class_mixed` | Mixed support → appropriate label |
| `test_dossier_no_epistemic_claims` | Dossier JSON has no editorial language |

### 7.2 Integration Tests

| Test | What It Proves |
|------|----------------|
| `test_multipack_build_creates_merged_unit` | 2 packs → 1 VariantUnit per position |
| `test_multipack_idempotent_rebuild` | Build twice → same row counts |
| `test_dossier_shows_support_counts` | Dossier JSON has `support_summary.by_type` |
| `test_dossier_shows_evidence_class` | Dossier JSON has `evidence_class` field |
| `test_gate_not_duplicated_multipack` | 2 packs same variant → 1 gate |
| `test_ack_list_not_exploded` | Multi-pack → same ack count as single |
| `test_cli_all_installed_flag` | `--all-installed` uses all comparative packs |
| `test_api_include_all_installed` | API flag triggers multi-pack build |

### 7.3 Full Suite Requirements

- All existing Sprint 5-8 tests must pass
- `redletters.*` warnings → errors
- `ruff check` clean
- Coverage ≥80% on new code

---

## 8. Implementation Order

### Phase 1: Data Model + Schema (Safest First)
1. Add `WitnessSupport` and `WitnessSupportType` to `models.py`
2. Create migration for `reading_support` table
3. Update `VariantStore` to read/write support sets
4. Unit tests for new model methods

### Phase 2: Aggregation Builder
1. Add `normalize_for_aggregation()` function
2. Implement `dedupe_support_set()` with warnings
3. Update `VariantBuilder` to accept multiple packs
4. Implement merge logic with idempotency
5. Unit + integration tests for aggregation

### Phase 3: Dossier + API/CLI
1. Add `SupportSummary`, `evidence_class` to dossier models
2. Update `DossierGenerator` to compute new fields
3. Add `--all-installed` CLI flag
4. Add `include_all_installed_sources` API field
5. Integration tests for dossier output

### Phase 4: GUI + Gate Hygiene
1. Update `DossierPanel.tsx` to show support counts
2. Add evidence class badges
3. Verify gate deduplication works
4. Manual testing via runbook

---

## 9. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Migration breaks existing data | Create new table, don't alter existing |
| Performance with many packs | Index on `reading_id`, batch inserts |
| Normalization inconsistency | Single `normalize_for_aggregation()` used everywhere |
| GUI complexity | Collapsed/expandable sigla list |
| Breaking existing CLI/API | Default flags maintain backward compat |

---

## 10. ADR Compliance Checklist

| ADR | Requirement | Sprint 9 Impact |
|-----|-------------|-----------------|
| ADR-007 | SBLGNT canonical | Unchanged: SBLGNT always `sblgnt_reading_index=0` |
| ADR-008 | Side-by-side variants | Unchanged: merged readings still shown side-by-side |
| ADR-008 | Acknowledgement gating | Enhanced: gates based on merged unit, no duplicates |
| ADR-009 | Readable vs traceable | Unchanged: gating logic same |
| ADR-010 | Layered confidence | Unchanged: confidence displayed |

---

## 11. Definition of Done

With 2+ comparative packs installed:

1. **Build**: `redletters variants build "John.1.18" --all-installed`
   - Creates single VariantUnit per position
   - Readings have merged support sets
   - No duplicate support entries

2. **Dossier**: `GET /variants/dossier?reference=John.1.18`
   - Shows `support_summary.by_type` with counts
   - Shows `evidence_class` label per reading
   - Lists sigla (collapsed/expandable)
   - No epistemic inflation language

3. **Gate**: Navigate to variant in GUI
   - One gate per VariantUnit (not per-pack)
   - Acknowledge once, variant resolved

4. **Tests**: Full suite green, ruff clean

---

**MAP Status**: COMPLETE - Ready for implementation
