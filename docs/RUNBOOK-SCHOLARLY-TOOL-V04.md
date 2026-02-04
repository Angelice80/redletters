# Scholarly Tool v0.4 Runbook

**Definition of Done**: Fresh-environment reproducible workflow for Greek NT translation with multi-pack variant aggregation and gate stability.

**Target Scope**: Gospel of John (21 chapters, ~15,635 words)

**Version**: 0.4.0 - Multi-Pack Apparatus (John)

---

## What's New in v0.4

### Core Changes
- **Multi-pack aggregation**: 2+ comparative packs contribute to ONE merged VariantUnit per location
- **Structured support set**: Each reading has witness siglum, witness_type, century_range, source_pack_id
- **Gate stability**: ONE gate per merged VariantUnit (not per-pack); acknowledge once suppresses future gates
- **Idempotent rebuild**: Re-running variant build does not duplicate variants or support entries
- **Dossier provenance**: Lists all packs that contributed to readings

### Test Additions
- `tests/integration/test_v04_multipack_gates.py` - 8 tests validating gate stability with multiple packs

---

## Prerequisites

- Python 3.10+
- Git
- ~500MB disk space for source packs

---

## Step 1: Install from Source

```bash
# Clone and install
git clone <repo-url> greek2english
cd greek2english
pip install -e .

# Verify installation
redletters --version
```

**Expected**: Version number displayed, no import errors.

---

## Step 2: Initialize Database

```bash
redletters init
```

**Expected**: Creates `~/.redletters/redletters.db` with schema.

---

## Step 3: List Available Source Packs

```bash
redletters sources list
```

**Expected output**:
```
Available source packs:
  morphgnt-sblgnt     [spine]        MorphGNT SBLGNT - Canonical Greek spine
  strongs-greek       [lexicon]      Strong's Greek Dictionary
  westcott-hort-john  [comparative]  Westcott-Hort John (variant pack)
  byzantine-john      [comparative]  Byzantine Text John (variant pack)
  tischendorf-mark    [comparative]  Tischendorf Mark (variant pack)
```

---

## Step 4: Install MorphGNT SBLGNT Spine (Required)

```bash
redletters sources install morphgnt-sblgnt --accept-eula
```

**Notes**:
- Downloads MorphGNT SBLGNT files from GitHub
- License: CC BY-SA (requires attribution)
- The `--accept-eula` flag confirms license acceptance
- Installs to `~/.redletters/data/morphgnt-sblgnt/`

**Verify installation**:
```bash
redletters sources status
```

**Expected**: Shows morphgnt-sblgnt as "Installed".

---

## Step 5: Install Multiple Comparative Packs (Required for v0.4)

```bash
# Install first comparative pack
redletters sources install westcott-hort-john --accept-eula

# Install second comparative pack
redletters sources install byzantine-john --accept-eula
```

**Notes**:
- Westcott-Hort: Public Domain (1881 edition)
- Byzantine: Public Domain (Robinson-Pierpont)
- Both cover John chapter 1 (51 verses)

**Verify**:
```bash
redletters sources status
```

**Expected**: Shows both westcott-hort-john and byzantine-john as "Installed".

---

## Step 6: Build Variants with Multiple Packs

```bash
redletters variants build "John 1" --scope chapter --all-installed
```

**Expected output**:
```
Building variants for John 1...
  Spine: morphgnt-sblgnt
  Comparative packs: westcott-hort-john, byzantine-john

Processed 51 verses
Found X variation points (merged across packs)
Variant data stored for John 1
```

**Critical validation**: Variant count should NOT multiply with more packs. Each location has ONE merged VariantUnit.

---

## Step 7: Verify Merged VariantUnit (NOT Per-Pack)

```bash
redletters variants list "John 1:18" --json
```

**Expected**: Exactly ONE variant entry for John.1.18 (not two separate entries for WH and Byz).

**Validation criteria**:
- `variants` array has length 1 for this location
- The single variant has readings from BOTH packs merged
- Each reading's `support` array may have entries from multiple packs

---

## Step 8: Generate Dossier with Multi-Pack Provenance

```bash
redletters variants dossier "John 1:18" --json
```

**Expected**: JSON output containing:
- `reference`: "John.1.18"
- `spine`: source_id "morphgnt-sblgnt" with Greek text
- `variants`: Array with ONE merged variant
- `provenance`: Lists both "westcott-hort-john" and "byzantine-john"
- Each reading has `support_summary.by_type` with counts
- Each reading has `evidence_class` (e.g., "edition-level evidence")

**Critical validation - NO epistemic inflation**:
- Must NOT contain: "more likely original", "preferred reading", "best text", "superior evidence"
- Language must be purely descriptive

---

## Step 9: Verify Gate Stability (Critical v0.4 Test)

```bash
# Check pending gates
redletters gates pending "John 1"
```

**Expected**: Number of pending gates equals number of LOCATIONS with variants, NOT (packs × locations).

**Example**: If John 1:18 and John 1:28 have variants:
- With 1 pack: 2 pending gates
- With 2 packs: STILL 2 pending gates (not 4)

---

## Step 10: Acknowledge Gate Once

```bash
redletters gates acknowledge "John 1:18" --reason "Reviewed multi-pack variant, prefer SBLGNT reading"
```

**Expected output**:
```
Gate acknowledged
  Reference: John.1.18
  Reading: 0
  Reason: Reviewed multi-pack variant, prefer SBLGNT reading
  Session: cli-default
```

---

## Step 11: Verify Acknowledgement Suppresses Future Gates

```bash
# Check pending gates again
redletters gates pending "John 1"
```

**Expected**: John.1.18 is NO LONGER in pending list (was suppressed by acknowledgement).

**Critical validation**: Adding a third pack and rebuilding should NOT re-create the gate for John.1.18.

---

## Step 12: Test Idempotent Rebuild

```bash
# Rebuild variants (should not duplicate)
redletters variants build "John 1" --scope chapter --all-installed

# Check variant count
redletters variants list "John 1:18" --json | python -c "import sys, json; v=json.load(sys.stdin); print(f'Variant count: {len(v.get(\"variants\", []))}')"
```

**Expected**: Variant count is still 1 (not 2 after rebuild).

---

## Step 13: Run Full Test Suite

```bash
# Full test suite
pytest tests/ -v

# Specific v0.4 tests
pytest tests/integration/test_v04_multipack_gates.py -v
```

**Expected**: 733+ tests passing (725 existing + 8 new v0.4 gate stability tests).

---

## Definition of Done Checklist

| Criterion | Command | Expected |
|-----------|---------|----------|
| Install succeeds | `pip install -e .` | No errors |
| Init creates DB | `redletters init` | DB file created |
| Spine installs | `redletters sources install morphgnt-sblgnt` | Pack installed |
| WH pack installs | `redletters sources install westcott-hort-john` | Pack installed |
| Byz pack installs | `redletters sources install byzantine-john` | Pack installed |
| Multi-pack build | `redletters variants build "John 1" --all-installed` | Variants merged |
| ONE variant per location | `redletters variants list "John 1:18" --json` | Array length = 1 |
| Dossier shows provenance | `redletters variants dossier "John 1:18" --json` | Both packs listed |
| Gate count stable | `redletters gates pending "John 1"` | Count = locations, not packs×locations |
| Acknowledge once works | `redletters gates acknowledge "John 1:18" -r "test"` | Gate recorded |
| Ack suppresses gate | `redletters gates pending "John 1"` | John.1.18 not in list |
| Idempotent rebuild | Re-run build, check variant count | Still 1 variant |
| Tests pass | `pytest tests/ -v` | 733+ green |
| Lint clean | `ruff check src/ tests/` | All checks passed |
| No epistemic inflation | Check dossier output | No value judgments |

---

## Non-Negotiables Validated

| Requirement | Validation |
|-------------|------------|
| SBLGNT canonical spine (ADR-007) | `spine.source_id` always "morphgnt-sblgnt" |
| Variants side-by-side (ADR-008) | Dossier shows all readings with support |
| TYPE5+ forbidden in readable mode (ADR-009) | Orchestrator enforces via `_filter_claims_for_mode()` |
| Layered confidence always visible (ADR-010) | Every token has T/G/L/I scores |
| Evidence class explicit (not collapsed) | `support_summary.by_type` with separate counts |
| No epistemic inflation | Descriptive language only |
| Deterministic output (no ML) | All translation is rule-based/dictionary-lookup |
| No copyrighted data in repo | All packs downloaded at runtime |
| **NEW: ONE gate per merged VariantUnit** | Gate count = locations, not packs×locations |
| **NEW: Ack once suppresses future gates** | Re-build does not re-create acknowledged gates |
| **NEW: Idempotent rebuild** | UNIQUE constraints prevent duplicate support entries |

---

## Known Limitations (v0.4)

1. **Comparative Pack Coverage**: westcott-hort-john and byzantine-john cover John 1 only. Full John coverage is future work.

2. **Lexicon Coverage**: BasicGlossProvider has ~90 common words (CC0). Full semantic ranges require Strongs or BDAG import.

3. **Segment Alignment**: `translation_segments` in ledger is stubbed. Token-level alignment works.

4. **Commentary Plugins**: Plugin interface defined but no plugins bundled.

5. **Pack Conflict Resolution**: When two packs have different readings for the same witness, currently last-write-wins. Future: explicit conflict UI.

---

## Architecture References

| ADR | Title | Status |
|-----|-------|--------|
| ADR-002 | Provenance-First Data Model | Implemented |
| ADR-007 | SBLGNT Canonical Spine | Implemented |
| ADR-008 | Variants Side-by-Side | Implemented |
| ADR-009 | TYPE5+ Forbidden in Readable Mode | Implemented |
| ADR-010 | Layered Confidence Always Visible | Implemented |

---

## Troubleshooting

### "SpineMissingError: No spine pack installed"

```bash
redletters sources install morphgnt-sblgnt
```

### "Pack not found in catalog"

```bash
redletters sources list  # Check available packs
```

### "Gate count multiplied after adding pack"

This indicates a bug. Check:
1. Variants are being merged by normalized text, not duplicated
2. `reading_support` table has UNIQUE constraint on (reading_id, witness_siglum, source_pack_id)

```bash
# Debug: Check variant count per location
redletters variants list "John 1:18" --json | python -m json.tool
```

### "Acknowledged gate reappeared after rebuild"

Check that acknowledgement store is persisting correctly:
```bash
redletters gates list
```

### Database corruption

```bash
rm ~/.redletters/redletters.db
redletters init
```

---

## Next Steps After v0.4

1. **Sprint 13**: Extend WH and Byz packs to full Gospel of John (21 chapters)
2. **Sprint 14**: Strongs lexicon integration via ChainedLexiconProvider
3. **Sprint 15**: Commentary plugin system with explicit provenance
4. **Sprint 16**: GUI variant comparison panel with multi-pack display
5. **Sprint 17**: Export formats (OSIS, USFM, LaTeX)
