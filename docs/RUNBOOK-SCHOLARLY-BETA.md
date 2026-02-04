# Scholarly Beta Runbook

**Definition of Done**: Fresh-environment reproducible workflow for Greek NT translation with full provenance.

**Target Scope**: Gospel of John (27 chapters, ~15,635 words)

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
  westcott-hort-john  [comparative]  Westcott-Hort John 1 (variant pack)
```

---

## Step 4: Install MorphGNT SBLGNT Spine (Required)

```bash
redletters sources install morphgnt-sblgnt --accept-eula
```

**Notes**:
- This downloads the MorphGNT SBLGNT files from GitHub
- License: CC BY-SA (requires attribution)
- The `--accept-eula` flag confirms license acceptance
- Installs to `~/.redletters/data/morphgnt-sblgnt/`

**Verify installation**:
```bash
redletters sources status
```

**Expected**: Shows morphgnt-sblgnt as "✓ Installed".

---

## Step 5: Install Comparative Pack (Optional but Recommended)

```bash
redletters sources install westcott-hort-john --accept-eula
```

**Notes**:
- Provides textual variants for comparison
- Currently covers John chapter 1 only (P1: extend to full Gospel)
- License: Public Domain

**Verify**:
```bash
redletters sources status
```

**Expected**: Shows westcott-hort-john as "✓ Installed".

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
redletters variants show "John 1:1"
```

**Expected**: Shows SBLGNT spine text with any WH variants marked.

---

## Step 7: Translate with Traceable Mode

### 7a: Basic Translation (Human Output)

```bash
redletters translate "John 1:1" --translator traceable --mode traceable
```

**Expected**: Greek text + English translation with provenance.

### 7b: Full Ledger Output

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

### 7c: JSON Output (Machine-Readable)

```bash
redletters translate "John 1:1" --translator traceable --mode traceable --json
```

**Expected**: Full JSON with `ledger` array containing `VerseLedger` objects.

---

## Step 8: Gate System (Significance Acknowledgements)

When variants exceed significance thresholds, gates require explicit acknowledgement.

```bash
# Show pending gates
redletters gates pending "John 1"

# Acknowledge a gate
redletters gates ack <gate-id> --reason "Variant reviewed, prefer SBLGNT reading"
```

**Gate Types**:
- `TYPE1`: Minor orthographic (auto-passed)
- `TYPE2`: Grammatical (may require ack)
- `TYPE3`: Lexical (requires ack)
- `TYPE4`: Semantic (requires ack)
- `TYPE5+`: Major theological (blocked in readable mode, requires explicit ack in traceable mode)

---

## Step 9: Generate Dossier

```bash
redletters dossier "John 1" --output john1-dossier.json
```

**Expected**: Comprehensive JSON with:
- All verses with translations
- Variant apparatus per verse
- Gate acknowledgement status
- Evidence class summaries
- Full provenance chain

---

## Step 10: Run Test Suite

```bash
# Full test suite
pytest tests/ -v

# Quick smoke test
pytest tests/test_traceable_ledger.py -v
```

**Expected**: 702+ tests passing (664 existing + 38 Sprint 10).

---

## Step 11: Lint Check

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
| Variants build | `redletters variants build "John 1" --scope chapter --all-installed` | Variant data stored |
| Traceable translate works | `redletters translate "John 1:1" --translator traceable --mode traceable --ledger` | Token ledger displayed |
| JSON output valid | `redletters translate "John 1:1" ... --json \| python -m json.tool` | Valid JSON |
| Tests pass | `pytest tests/ -v` | 700+ green |
| Lint clean | `ruff check src/ tests/` | All checks passed |

---

## Known Limitations (Scholarly Beta)

1. **Lexicon Coverage**: BasicGlossProvider has ~90 common words (CC0). Full semantic ranges require Strongs or BDAG import.

2. **Comparative Pack Coverage**: westcott-hort-john currently covers John 1 only. Priority P1: Extend to all 21 chapters.

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
redletters gates ack <gate-id> --reason "Reviewed variant, accepting SBLGNT reading"
```

### Database corruption

```bash
rm ~/.redletters/redletters.db
redletters init
```

---

## Next Steps After Scholarly Beta

1. **Sprint 11**: Extend WH pack to full Gospel of John (21 chapters)
2. **Sprint 12**: Strongs lexicon integration via ChainedLexiconProvider
3. **Sprint 13**: Commentary plugin system with explicit provenance
4. **Sprint 14**: GUI variant comparison panel
5. **Sprint 15**: Export formats (OSIS, USFM, LaTeX)
