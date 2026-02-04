# Scholarly Tool v0.3 Runbook

**Definition of Done**: Fresh-environment reproducible workflow for Greek NT translation with comparative variants and evidence dossier.

**Target Scope**: Gospel of John (27 chapters, ~15,635 words)

**Version**: 0.3.0 - Comparative Variants + Evidence Dossier

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

## Step 5: Install Comparative Pack (Required for Variants)

```bash
redletters sources install westcott-hort-john --accept-eula
```

**Notes**:
- Provides textual variants for comparison against SBLGNT spine
- Currently covers John chapter 1 (51 verses)
- License: Public Domain (Westcott-Hort 1881)

**Verify**:
```bash
redletters sources status
```

**Expected**: Shows westcott-hort-john as "Installed".

---

## Step 6: Build Variants for John 1

```bash
redletters variants build "John 1" --scope chapter --all-installed
```

**Expected output**:
```
Building variants for John 1...
  Spine: morphgnt-sblgnt
  Comparative packs: westcott-hort-john

Processed 51 verses
Found X variation points
Variant data stored for John 1
```

**Verify variant data**:
```bash
redletters variants list "John 1" --json | head -20
```

**Expected**: Shows variants with spine_reading and alternative readings.

---

## Step 7: Generate Dossier for John 1:1

```bash
redletters variants dossier "John 1:1" --json
```

**Expected**: JSON output containing:
- `reference`: "John.1.1"
- `spine`: source_id "morphgnt-sblgnt" with Greek text
- `variants`: Array with classification, significance, readings
- `provenance`: spine_source, comparative_packs, build_timestamp
- Each reading has `evidence_class` (e.g., "edition-level evidence")
- Each reading has `support_summary.by_type` with counts

**Critical validation**: Output must NOT contain epistemic inflation phrases like:
- "more likely original"
- "preferred reading"
- "best text"
- "superior evidence"

---

## Step 8: Acknowledge a Gate (Standalone)

```bash
redletters gates acknowledge "John 1:1" --reason "Variant reviewed, prefer SBLGNT reading"
```

**Expected output**:
```
Gate acknowledged
  Reference: John.1.1
  Reading: 0
  Reason: Variant reviewed, prefer SBLGNT reading
  Session: cli-default
```

**Verify acknowledgement persisted**:
```bash
redletters gates list
```

**Expected**: Shows the acknowledged gate with timestamp.

---

## Step 9: Check Pending Gates

```bash
redletters gates pending "John 1"
```

**Expected**: Shows any TYPE3+ variants not yet acknowledged, or confirms all gates acknowledged.

---

## Step 10: Translate with Traceable Mode and Ledger

```bash
redletters translate "John 1:1" --translator traceable --mode traceable --ledger
```

**Expected**: Token-by-token breakdown with:
- Surface form (Greek)
- Lemma
- Morphology code
- Gloss (English)
- Four-layer confidence (T/G/L/I)
- Source attribution

**JSON output**:
```bash
redletters translate "John 1:1" --translator traceable --mode traceable --json
```

**Expected**: Valid JSON with `ledger` array containing `VerseLedger` objects.

---

## Step 11: Run Test Suite

```bash
# Full test suite
pytest tests/ -v

# Quick smoke test for new features
pytest tests/test_dossier_epistemic.py -v
pytest tests/test_traceable_ledger.py -v
```

**Expected**: 720+ tests passing (702 existing + 18+ new epistemic tests).

---

## Step 12: Lint Check

```bash
ruff check src/ tests/
```

**Expected**: "All checks passed!"

---

## Definition of Done Checklist

| Criterion | Command | Expected |
|-----------|---------|----------|
| Install succeeds | `pip install -e .` | No errors |
| Init creates DB | `redletters init` | DB file created |
| Spine installs | `redletters sources install morphgnt-sblgnt` | Pack in ~/.redletters/packs/ |
| Comparative installs | `redletters sources install westcott-hort-john` | Pack installed |
| Variants build | `redletters variants build "John 1" --scope chapter --all-installed` | Variant data stored |
| Dossier works | `redletters variants dossier "John 1:1" --json` | Valid JSON with evidence_class |
| Acknowledge standalone | `redletters gates acknowledge "John 1:1" -r "test"` | Gate recorded |
| Gates list works | `redletters gates list` | Shows acknowledged gates |
| Gates pending works | `redletters gates pending "John 1"` | Shows pending or confirms none |
| Traceable translate | `redletters translate "John 1:1" --translator traceable --mode traceable --ledger` | Token ledger displayed |
| JSON output valid | `redletters translate "John 1:1" ... --json \| python -m json.tool` | Valid JSON |
| Tests pass | `pytest tests/ -v` | 720+ green |
| Lint clean | `ruff check src/ tests/` | All checks passed |
| No epistemic inflation | `pytest tests/test_dossier_epistemic.py -v` | All 18+ tests pass |

---

## Non-Negotiables Validated

| Requirement | Validation |
|-------------|------------|
| SBLGNT canonical spine (ADR-007) | `spine.source_id` always "morphgnt-sblgnt" |
| Variants side-by-side (ADR-008) | Dossier shows all readings with support |
| TYPE5+ forbidden in readable mode (ADR-009) | Orchestrator enforces via `_filter_claims_for_mode()` |
| Layered confidence always visible (ADR-010) | Every token has T/G/L/I scores |
| Evidence class explicit (not collapsed) | `support_summary.by_type` with separate counts |
| No epistemic inflation | Epistemic test suite validates neutral language |
| Deterministic output (no ML) | All translation is rule-based/dictionary-lookup |
| No copyrighted data in repo | All packs downloaded at runtime |

---

## Known Limitations (v0.3)

1. **Lexicon Coverage**: BasicGlossProvider has ~90 common words (CC0). Full semantic ranges require Strongs or BDAG import.

2. **Comparative Pack Coverage**: westcott-hort-john covers John 1 only. Priority P1: Extend to all 21 chapters.

3. **Segment Alignment**: `translation_segments` in ledger is stubbed. Token-level alignment works.

4. **Commentary Plugins**: Plugin interface defined but no plugins bundled. Future sprint.

5. **No ML Components**: All translation is rule-based/dictionary-lookup. Deterministic by design (non-negotiable).

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

### "Gate blocked: TYPE5 variant requires acknowledgement"

```bash
redletters gates pending "John 1"
redletters gates acknowledge "<ref>" --reason "Reviewed variant, accepting SBLGNT reading"
```

### Database corruption

```bash
rm ~/.redletters/redletters.db
redletters init
```

---

## What's New in v0.3

### CLI Additions
- `redletters gates acknowledge <ref> --reason "<reason>"` - Standalone gate acknowledgement
- `redletters gates list` - List acknowledged gates for session
- `redletters gates pending <ref>` - Show unacknowledged TYPE3+ gates

### Test Additions
- `tests/test_dossier_epistemic.py` - 18+ tests validating neutral language in dossier output

### Non-Negotiable Enforcement
- Epistemic inflation prevention explicitly tested
- Evidence class labels validated as purely descriptive
- No hidden textual priority hierarchy

---

## Next Steps After v0.3

1. **Sprint 12**: Extend WH pack to full Gospel of John (21 chapters)
2. **Sprint 13**: Strongs lexicon integration via ChainedLexiconProvider
3. **Sprint 14**: Commentary plugin system with explicit provenance
4. **Sprint 15**: GUI variant comparison panel
5. **Sprint 16**: Export formats (OSIS, USFM, LaTeX)
