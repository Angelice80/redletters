# Scholarly Tool v0.7.0 Runbook

**Definition of Done**: Pack Explainability + Citation Export for scholarly reproducibility.

**Target Scope**: Gospel of John (reuses v0.5-v0.6 infrastructure)

**Version**: 0.7.0 - Pack Explainability + Citation Export

---

## What's New in v0.7

### Core Changes
- **Sense Explainability**: `redletters senses explain|conflicts|list-packs`
- **Citation Export**: `redletters export citations` for CSL-JSON bibliography
- **Deterministic Audit Trail**: Inspect "why this sense was chosen" with pack precedence
- **Snapshot Integration**: `--include-citations` flag for reproducibility

### New Commands
- `redletters senses explain <lemma>` - Show sense resolution audit trail
- `redletters senses conflicts <lemma>` - Detect cross-pack disagreements
- `redletters senses list-packs` - Show installed sense packs with precedence
- `redletters export citations` - Export CSL-JSON bibliography of all packs

### Test Additions
- `tests/test_senses_normalize.py` - 15 tests for lemma normalization
- `tests/test_senses_explain.py` - 9 tests for explain functionality
- `tests/test_senses_conflicts.py` - 11 tests for conflict detection
- `tests/test_export_citations.py` - 12 tests for citation export

---

## Prerequisites

- Python 3.8+
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

## Step 3: Install Source Packs

```bash
# Install spine
redletters sources install morphgnt-sblgnt --accept-eula

# Install comparative packs
redletters sources install westcott-hort-john --accept-eula
redletters sources install byzantine-john --accept-eula
```

**Verify**:
```bash
redletters sources status
```

---

## Step 4: Install Sense Packs

For v0.7.0, sense packs provide lexical data with citation-grade metadata.

```bash
# Install sample sense pack (if available)
redletters sources install sample-senses --accept-eula
```

**Verify sense packs installed**:
```bash
redletters senses list-packs
```

**Expected output**:
```
Installed sense packs (precedence order):
  1. sample-senses@1.0.0
     Source: SampleLex - Sample Greek Lexicon
     License: CC0
```

---

## Step 5: Explain Sense Resolution

```bash
# Explain why a particular gloss was chosen for a lemma
redletters senses explain "logos"
```

**Expected output**:
```
Sense Resolution for "logos"
============================
Normalized: logos
Packs consulted: sample-senses

Matches found:
  sample-senses@1.0.0:
    - logos.1: "word" (weight: 0.90)
    - logos.2: "reason" (weight: 0.70)

Chosen: "word"
Reason: First match by precedence (pack: sample-senses, priority: 1)
```

**With JSON output**:
```bash
redletters senses explain "logos" --json
```

**Expected**: JSON object with `lemma_input`, `lemma_normalized`, `packs_consulted`, `matches`, `chosen`, `reason`.

---

## Step 6: Detect Cross-Pack Conflicts

```bash
# Check for disagreements across sense packs
redletters senses conflicts "logos"
```

**Expected output (no conflict)**:
```
Conflict Check for "logos"
==========================
Normalized: logos
Packs with matches: sample-senses

All entries:
  1. sample-senses@1.0.0: "word" (weight: 0.90)

Unique glosses: word
Conflict: NONE (Agreement on primary gloss)
```

**Expected output (with conflict)**:
```
Conflict Check for "logos"
==========================
Normalized: logos
Packs with matches: pack-a, pack-b

All entries:
  1. pack-a@1.0.0: "word" (weight: 0.90)
  2. pack-b@1.0.0: "reason" (weight: 0.85)

Unique glosses: word, reason
Conflict: YES - Primary glosses differ: "word" vs "reason"
```

**With JSON output**:
```bash
redletters senses conflicts "logos" --json
```

---

## Step 7: Export Citations (CSL-JSON)

```bash
# Create output directory
mkdir -p out

# Export bibliography in CSL-JSON format
redletters export citations --out out/citations.json
```

**Expected output**:
```
Citations exported
  Format: csljson
  Entries: 4
  Schema: 1.0.0
  Hash: abc123def456...
  Output: out/citations.json
```

**Validate CSL-JSON format**:
```bash
python -c "import json; data=json.load(open('out/citations.json')); print(f'Entries: {len(data)}'); print(json.dumps(data[0], indent=2))"
```

**Expected**: Array of CSL-JSON entries with `id`, `type`, `title`, and optional fields like `edition`, `publisher`, `issued`.

---

## Step 8: Export Citations (Full Format)

```bash
redletters export citations --format full --out out/citations_full.json
```

**Expected**: JSON with metadata wrapper including `schema_version`, `export_timestamp`, `entries`, `content_hash`.

---

## Step 9: Generate Snapshot with Citations

```bash
# Generate snapshot that includes citations export
redletters export snapshot \
  --out out/snapshot.json \
  --include-citations \
  --inputs out/apparatus.jsonl,out/translation.jsonl
```

**Expected output**:
```
Citations exported
  Entries: 4
  Hash: abc123def456...

Snapshot created
  Tool version: 0.5.0
  Schema version: 1.0.0
  Git commit: abc123...
  Packs: 4
    - morphgnt-sblgnt (v1.0, CC BY-SA)
    - westcott-hort-john (v1.0, Public Domain)
    - byzantine-john (v1.0, Public Domain)
    - sample-senses (v1.0.0, CC0)
  Export hashes: 3
    - apparatus.jsonl: abc123...
    - translation.jsonl: def456...
    - citations.json: ghi789...
  Output: out/snapshot.json
```

---

## Step 10: Verify Exports (Including Citations)

```bash
redletters export verify \
  --snapshot out/snapshot.json \
  --inputs out/apparatus.jsonl,out/translation.jsonl,out/citations.json
```

**Expected output**:
```
Verification passed

File hashes:
  apparatus.jsonl
      Expected: abc123...
      Actual:   abc123...
  translation.jsonl
      Expected: def456...
      Actual:   def456...
  citations.json
      Expected: ghi789...
      Actual:   ghi789...
```

---

## Step 11: Verify Deterministic Citations

```bash
# Export twice
redletters export citations --out out/citations1.json
redletters export citations --out out/citations2.json

# Compare hashes
sha256sum out/citations1.json out/citations2.json
```

**Expected**: Identical hashes (deterministic output).

---

## Step 12: Run Full Test Suite

```bash
# Full test suite
pytest tests/ -v

# Specific v0.7 tests
pytest tests/test_senses_*.py tests/test_export_citations.py -v

# Integration tests
pytest tests/integration/test_export_reproducibility.py::TestCitationsInSnapshot -v

# Lint check
ruff check src/ tests/
ruff format --check src/ tests/
```

**Expected**: 875+ tests passing, lint clean.

---

## Definition of Done Checklist

| Criterion | Command | Expected |
|-----------|---------|----------|
| Install succeeds | `pip install -e .` | No errors |
| Init creates DB | `redletters init` | DB file created |
| Source packs install | `redletters sources install ...` | Packs installed |
| **List sense packs** | `redletters senses list-packs` | Shows precedence order |
| **Explain works** | `redletters senses explain "logos"` | Shows audit trail |
| **Explain JSON** | `redletters senses explain "logos" --json` | Valid JSON |
| **Conflicts works** | `redletters senses conflicts "logos"` | Shows conflict status |
| **Conflicts JSON** | `redletters senses conflicts "logos" --json` | Valid JSON |
| **Export citations** | `redletters export citations --out x.json` | CSL-JSON file |
| **Export citations full** | `redletters export citations --format full --out x.json` | Full JSON |
| **Snapshot with citations** | `redletters export snapshot --include-citations` | Includes hash |
| **Verify citations** | `redletters export verify --inputs citations.json` | Hash matches |
| **Deterministic citations** | Export twice, compare hashes | Identical |
| Tests pass | `pytest tests/ -v` | 875+ green |
| Lint clean | `ruff check src/ tests/` | No errors |

---

## Non-Negotiables Validated

| Requirement | Validation |
|-------------|------------|
| Deterministic output | Same packs = identical citations hash |
| Explicit provenance | Every citation includes source_id, title, license |
| Pack precedence | explain shows consultation order |
| No hidden theology | Conflicts detection exposes disagreements |
| Reproducibility | Citations included in snapshot verify |
| CSL-JSON standard | Valid format for Zotero/Mendeley import |
| Citation-grade metadata | edition, publisher, year, license_url included |

---

## Schema Reference

### Senses Explain (JSON)
```json
{
  "lemma_input": "logos",
  "lemma_normalized": "logos",
  "packs_consulted": ["sample-senses"],
  "matches": [
    {
      "pack_id": "sample-senses",
      "pack_ref": "sample-senses@1.0.0",
      "source_id": "SampleLex",
      "source_title": "Sample Greek Lexicon",
      "sense_id": "logos.1",
      "gloss": "word",
      "weight": 0.90,
      "edition": "",
      "publisher": "",
      "year": null,
      "license": "CC0"
    }
  ],
  "chosen": {
    "pack_id": "sample-senses",
    "gloss": "word",
    "weight": 0.90
  },
  "reason": "First match by precedence",
  "schema_version": "1.0.0"
}
```

### Senses Conflicts (JSON)
```json
{
  "lemma_input": "logos",
  "lemma_normalized": "logos",
  "packs_checked": ["pack-a", "pack-b"],
  "packs_with_matches": ["pack-a", "pack-b"],
  "entries": [
    {
      "pack_id": "pack-a",
      "pack_ref": "pack-a@1.0.0",
      "source_id": "LexA",
      "source_title": "Lexicon A",
      "gloss": "word",
      "weight": 0.90
    },
    {
      "pack_id": "pack-b",
      "pack_ref": "pack-b@1.0.0",
      "source_id": "LexB",
      "source_title": "Lexicon B",
      "gloss": "reason",
      "weight": 0.85
    }
  ],
  "unique_glosses": ["word", "reason"],
  "has_conflict": true,
  "conflict_summary": "CONFLICT: Primary glosses differ: \"word\" vs \"reason\"",
  "schema_version": "1.0.0"
}
```

### Citations Export (CSL-JSON)
```json
[
  {
    "id": "sample-senses",
    "type": "book",
    "title": "Sample Greek Lexicon",
    "edition": "1st",
    "publisher": "Sample Publisher",
    "issued": {"date-parts": [[2020]]},
    "note": "License: CC0",
    "x-license": "CC0",
    "x-license-url": "https://creativecommons.org/publicdomain/zero/1.0/",
    "version": "1.0.0",
    "x-pack-role": "sense_pack"
  }
]
```

### Citations Export (Full Format)
```json
{
  "schema_version": "1.0.0",
  "export_timestamp": "2026-02-02T12:00:00Z",
  "entries": [...],
  "entries_count": 4,
  "content_hash": "abc123def456..."
}
```

---

## Troubleshooting

### "No sense packs installed"
Install sense packs first:
```bash
redletters sources install sample-senses --accept-eula
```

### "No matches found" for explain/conflicts
The lemma may not exist in installed sense packs. Check with:
```bash
redletters senses list-packs
```

### Citations export returns empty
Check that packs are installed:
```bash
redletters sources status
```

### Normalization issues
Greek lemmas are normalized (accents stripped, lowercased). Both "logos" and "logos" should match.

---

## Next Steps After v0.7

1. **Sense pack builder**: CLI to create sense packs from lexicon files
2. **Priority management**: CLI to adjust sense pack precedence
3. **BibTeX export**: Alternative citation format for LaTeX users
4. **Web API**: REST endpoints for explain/conflicts/citations
