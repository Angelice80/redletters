# Scholarly Tool v0.5.0 Runbook

**Definition of Done**: Fresh-environment reproducible workflow for Greek NT translation with reproducible scholar exports.

**Target Scope**: Gospel of John (reuses v0.4 infrastructure)

**Version**: 0.5.0 - Reproducible Scholar Exports

---

## What's New in v0.5

### Core Changes
- **Export CLI group**: `redletters export apparatus|translation|snapshot|verify`
- **Stable identifiers**: Deterministic IDs for variant units, readings, and tokens
- **Canonical JSON**: Reproducible serialization for hash verification
- **JSONL exports**: Apparatus and translation datasets in line-delimited JSON
- **Snapshot verification**: Record and verify export state for reproducibility

### New Commands
- `redletters export apparatus` - Export variant apparatus to JSONL
- `redletters export translation` - Export token ledger to JSONL
- `redletters export snapshot` - Generate reproducibility metadata
- `redletters export verify` - Verify exports against snapshot

### Test Additions
- `tests/test_export_ids.py` - 24 tests for ID generation and hashing
- `tests/integration/test_export_reproducibility.py` - 14 tests for export reproducibility

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

## Step 3: Install MorphGNT SBLGNT Spine

```bash
redletters sources install morphgnt-sblgnt --accept-eula
```

**Notes**:
- Downloads MorphGNT SBLGNT files from GitHub
- License: CC BY-SA (requires attribution)

**Verify**:
```bash
redletters sources status
```

**Expected**: Shows morphgnt-sblgnt as "Installed".

---

## Step 4: Install Comparative Packs

```bash
# Install first comparative pack
redletters sources install westcott-hort-john --accept-eula

# Install second comparative pack
redletters sources install byzantine-john --accept-eula
```

**Verify**:
```bash
redletters sources status
```

---

## Step 5: Build Variants

```bash
redletters variants build "John 1" --scope chapter --all-installed
```

**Expected**:
```
Building variants for John 1...
  Spine: morphgnt-sblgnt
  Comparative packs: westcott-hort-john, byzantine-john

Processed 51 verses
Found X variation points (merged across packs)
```

---

## Step 6: Run Traceable Translation

```bash
# Create output directory
mkdir -p out

# Run traceable translation with ledger output
redletters translate "John 1:1-18" \
  --translator traceable \
  --mode traceable \
  --ledger \
  --json > out/translate.json
```

**Expected**: JSON output with token-level ledger, confidence scores, and provenance.

---

## Step 7: Generate Dossier

```bash
redletters variants dossier "John 1:1-18" --json > out/dossier.json
```

**Expected**: JSON dossier with variants, readings, support, and provenance.

---

## Step 8: Export Apparatus Dataset

```bash
redletters export apparatus "John 1:1-18" \
  --format jsonl \
  --out out/apparatus.jsonl
```

**Expected output**:
```
✓ Apparatus exported
  Reference: John 1:1-18
  Rows: X
  Output: out/apparatus.jsonl
  Schema: 1.0.0
```

**Validate**:
```bash
# Check JSONL format
head -1 out/apparatus.jsonl | python -m json.tool

# Verify stable IDs
grep -o '"variant_unit_id":"[^"]*"' out/apparatus.jsonl | head -3
```

**Expected**: Each line is valid JSON with `variant_unit_id` like "John.1.18:3".

---

## Step 9: Export Translation Dataset

```bash
redletters export translation "John 1:1-18" \
  --format jsonl \
  --out out/translation.jsonl
```

**Expected output**:
```
✓ Translation exported
  Reference: John 1:1-18
  Rows: 18
  Output: out/translation.jsonl
  Schema: 1.0.0
```

**Validate**:
```bash
# Check JSONL format
head -1 out/translation.jsonl | python -m json.tool

# Verify token IDs
grep -o '"token_id":"[^"]*"' out/translation.jsonl | head -5
```

**Expected**: Each line contains verse with tokens having IDs like "John.1.1:0".

---

## Step 10: Generate Reproducibility Snapshot

```bash
redletters export snapshot \
  --out out/snapshot.json \
  --inputs out/apparatus.jsonl,out/translation.jsonl
```

**Expected output**:
```
✓ Snapshot created
  Tool version: 0.5.0
  Schema version: 1.0.0
  Git commit: abc123... (or "(not in git repo)")
  Packs: 3
    - morphgnt-sblgnt (v1.0, CC BY-SA)
    - westcott-hort-john (v1.0, Public Domain)
    - byzantine-john (v1.0, Public Domain)
  Export hashes: 2
    - apparatus.jsonl: abc123def456...
    - translation.jsonl: def456abc789...
  Output: out/snapshot.json
```

**Validate snapshot contents**:
```bash
python -c "import json; print(json.dumps(json.load(open('out/snapshot.json')), indent=2))"
```

**Expected**: JSON with tool_version, schema_version, packs, export_hashes.

---

## Step 11: Verify Exports Against Snapshot

```bash
redletters export verify \
  --snapshot out/snapshot.json \
  --inputs out/apparatus.jsonl,out/translation.jsonl
```

**Expected output**:
```
✓ Verification passed

File hashes:
  ✓ apparatus.jsonl
      Expected: abc123def456789...
      Actual:   abc123def456789...
  ✓ translation.jsonl
      Expected: def456abc789012...
      Actual:   def456abc789012...
```

**Exit code**: 0 (success)

---

## Step 12: Verify Deterministic Exports

```bash
# Export again to different files
redletters export apparatus "John 1:1-18" --out out/apparatus2.jsonl
redletters export translation "John 1:1-18" --out out/translation2.jsonl

# Compare hashes
sha256sum out/apparatus.jsonl out/apparatus2.jsonl
sha256sum out/translation.jsonl out/translation2.jsonl
```

**Expected**: Identical hashes for same reference.

---

## Step 13: Run Full Test Suite

```bash
# Full test suite
pytest tests/ -v

# Specific v0.5 tests
pytest tests/test_export_ids.py tests/integration/test_export_reproducibility.py -v

# Lint check
ruff check src/ tests/
ruff format --check src/ tests/
```

**Expected**: 771+ tests passing, lint clean.

---

## Definition of Done Checklist

| Criterion | Command | Expected |
|-----------|---------|----------|
| Install succeeds | `pip install -e .` | No errors |
| Init creates DB | `redletters init` | DB file created |
| Spine installs | `redletters sources install morphgnt-sblgnt` | Pack installed |
| WH pack installs | `redletters sources install westcott-hort-john` | Pack installed |
| Byz pack installs | `redletters sources install byzantine-john` | Pack installed |
| Variants build | `redletters variants build "John 1"` | Variants created |
| Translate works | `redletters translate "John 1:1-18" --translator traceable --mode traceable --json` | JSON output |
| Dossier works | `redletters variants dossier "John 1:1-18" --json` | JSON dossier |
| **Export apparatus** | `redletters export apparatus "John 1:1-18" --out x.jsonl` | JSONL file |
| **Export translation** | `redletters export translation "John 1:1-18" --out x.jsonl` | JSONL file |
| **Export snapshot** | `redletters export snapshot --out snapshot.json` | JSON snapshot |
| **Verify passes** | `redletters export verify --snapshot x.json --inputs ...` | Exit code 0 |
| **Deterministic exports** | Export twice, compare hashes | Identical hashes |
| Tests pass | `pytest tests/ -v` | 771+ green |
| Lint clean | `ruff check src/ tests/` | No errors |

---

## Non-Negotiables Validated

| Requirement | Validation |
|-------------|------------|
| SBLGNT canonical spine (ADR-007) | Exports include `spine_source_id: morphgnt-sblgnt` |
| Variants side-by-side (ADR-008) | Apparatus export contains all readings |
| Deterministic output (no ML) | Same reference → identical hash |
| No copyrighted data in repo | All packs downloaded at runtime |
| Reproducibility | Snapshot verify passes for unchanged exports |
| Stable identifiers | variant_unit_id, reading_id, token_id are deterministic |
| Explicit provenance | Every export row includes `provenance_packs` and `schema_version` |

---

## Export Schema Reference

### Apparatus Row (JSONL line)
```json
{
  "variant_unit_id": "John.1.18:3",
  "verse_id": "John.1.18",
  "position": 3,
  "classification": "substitution",
  "significance": "significant",
  "gate_requirement": "requires_acknowledgement",
  "sblgnt_reading_index": 0,
  "readings": [
    {
      "reading_id": "John.1.18:3#abc123def456",
      "index": 0,
      "surface_text": "μονογενὴς θεός",
      "normalized_text": "μονογενης θεος",
      "is_sblgnt": true,
      "witness_summary": "SBLGNT, P66, P75, B",
      "support_entries": [
        {
          "witness_siglum": "SBLGNT",
          "witness_type": "edition",
          "century_range": [19, 21],
          "source_pack_id": "morphgnt-sblgnt"
        }
      ],
      "source_packs": ["morphgnt-sblgnt", "westcott-hort-john"]
    }
  ],
  "provenance_packs": ["westcott-hort-john", "byzantine-john"],
  "reason_code": "lexical",
  "reason_summary": "Theologically significant word choice",
  "schema_version": "1.0.0"
}
```

### Translation Row (JSONL line)
```json
{
  "verse_id": "John.1.18",
  "normalized_ref": "John 1:18",
  "spine_text": "θεὸν οὐδεὶς ἑώρακεν πώποτε...",
  "tokens": [
    {
      "token_id": "John.1.18:0",
      "position": 0,
      "surface": "θεόν",
      "normalized": "θεον",
      "lemma": "θεός",
      "morph": "N-ASM",
      "gloss": "God",
      "gloss_source": "basic_glosses",
      "confidence": {
        "textual": 0.9,
        "grammatical": 0.9,
        "lexical": 0.9,
        "interpretive": 0.9
      },
      "notes": []
    }
  ],
  "renderings": [],
  "confidence_summary": {
    "textual": 0.9,
    "grammatical": 0.9,
    "lexical": 0.9,
    "interpretive": 0.9
  },
  "provenance": {
    "spine_source_id": "morphgnt-sblgnt",
    "comparative_sources_used": ["westcott-hort-john"],
    "evidence_class_summary": {}
  },
  "schema_version": "1.0.0"
}
```

### Snapshot
```json
{
  "tool_version": "0.5.0",
  "schema_version": "1.0.0",
  "git_commit": "abc123...",
  "timestamp": "2026-02-02T12:00:00Z",
  "packs": [
    {
      "pack_id": "morphgnt-sblgnt",
      "version": "1.0",
      "license": "CC BY-SA",
      "pack_hash": "abc123...",
      "install_path": "~/.redletters/data/morphgnt-sblgnt"
    }
  ],
  "export_hashes": {
    "apparatus.jsonl": "sha256hex...",
    "translation.jsonl": "sha256hex..."
  }
}
```

---

## Troubleshooting

### "No spine data installed"
```bash
redletters sources install morphgnt-sblgnt --accept-eula
```

### "Gate required" during export translation
The translation exporter handles gates automatically. If you see this warning, the export continues with available data.

### Hash mismatch during verify
If verification fails:
1. Check if export files were modified
2. Re-export with same reference
3. Regenerate snapshot
4. Verify pack versions match

### Export produces empty file
Check that variants exist:
```bash
redletters variants list "John.1.18" --json
```
If empty, build variants first:
```bash
redletters variants build "John 1" --scope chapter
```

---

## Next Steps After v0.5

1. **TSV export format**: Add optional TSV output for spreadsheet compatibility
2. **Extended coverage**: Full John chapters, Synoptic parallels
3. **Citation format**: BibTeX-compatible export metadata
4. **Diff tool**: Compare exports between versions/runs
