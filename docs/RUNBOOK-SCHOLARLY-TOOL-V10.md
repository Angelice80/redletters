# Runbook: Scholarly Tool v0.10.0 - Schema Contracts + Validation

## Version: v0.10.0
## Scope: Gospel of John only

---

## Definition of Done

Execute the following steps in a fresh environment. All must pass.

### Prerequisites

```bash
pip install -e .
redletters init
```

### 1. Install Sources

```bash
redletters sources install morphgnt-sblgnt --accept-eula
redletters sources install <comp_pack_1>
redletters sources install <comp_pack_2>
```

### 2. Build Variants

```bash
redletters variants build "John 1" --scope chapter --all-installed
```

### 3. Generate Exports with Schema Versions

```bash
# Create output directory
mkdir -p out

# Apparatus JSONL
redletters export apparatus "John 1:1-18" --out out/apparatus.jsonl --force

# Translation JSONL (requires traceable translation first)
redletters translate "John 1:1-5" --mode traceable --ledger > out/translation_ledger.json
# (Translation JSONL export from ledger data - via code)

# Quote JSON
redletters quote "John 1:1" --out out/quote.json --force

# Citations JSON
redletters export citations --out out/citations.json

# Snapshot JSON (includes schema_versions)
redletters export snapshot \
  --out out/snapshot.json \
  --include-citations \
  --inputs out/apparatus.jsonl,out/quote.json,out/citations.json
```

### 4. Verify Schema Versions in Outputs

```bash
# Each artifact should have schema_version field
head -1 out/apparatus.jsonl | jq '.schema_version'
# Expected: "1.0.0"

cat out/quote.json | jq '.schema_version'
# Expected: "1.0.0"

cat out/citations.json | jq '.schema_version'
# Expected: "1.0.0"

cat out/snapshot.json | jq '.schema_version'
# Expected: "1.0.0"

# Snapshot should include schema_versions mapping (NEW in v0.10)
cat out/snapshot.json | jq '.schema_versions'
# Expected: {"apparatus": "1.0.0", "translation": "1.0.0", ...}
```

### 5. Validate Outputs (NEW in v0.10)

```bash
# Validate each output file
redletters validate output out/apparatus.jsonl
# Expected: ✓ Valid apparatus

redletters validate output out/quote.json
# Expected: ✓ Valid quote

redletters validate output out/citations.json
# Expected: ✓ Valid citations

redletters validate output out/snapshot.json
# Expected: ✓ Valid snapshot

# Auto-detect artifact type
redletters validate output out/apparatus.jsonl --type auto
# Expected: ✓ Valid apparatus

# JSON output
redletters validate output out/quote.json --json
# Expected: {"valid": true, "artifact_type": "quote", ...}
```

### 6. Validate Tampered Output Fails

```bash
# Create tampered file (missing schema_version)
echo '{"reference":"John 1:1","mode":"readable"}' > out/tampered.json

redletters validate output out/tampered.json --type quote
# Expected: ✗ Invalid quote
# Errors: Missing required field: schema_version, gate_status, ...
```

### 7. List Schema Versions

```bash
redletters validate schemas
# Expected output:
#   Schema Versions
#   apparatus            1.0.0
#   citations            1.0.0
#   confidence_bucketing 1.0.0
#   dossier              1.0.0
#   quote                1.0.0
#   senses_conflicts     1.0.0
#   senses_explain       1.0.0
#   snapshot             1.0.0
#   translation          1.0.0
```

### 8. Dossier Includes Schema Version (NEW in v0.10)

```bash
redletters dossier "John 1:1-5" --json > out/dossier.json
cat out/dossier.json | jq '.schema_version'
# Expected: "1.0.0"

redletters validate output out/dossier.json
# Expected: ✓ Valid dossier
```

### 9. Run Tests

```bash
pytest && ruff check && ruff format --check
```

All must pass.

---

## New CLI Commands

### `redletters validate output`

Validate a generated output file against its schema contract.

```bash
redletters validate output <file_path> [OPTIONS]

Arguments:
  file_path       Path to the file to validate

Options:
  --type, -t      Artifact type: apparatus|translation|snapshot|citations|quote|dossier|auto
                  (default: auto - auto-detect from filename/content)
  --json          Output result as JSON
```

**Exit codes:**
- 0: Valid
- 1: Invalid or error

**Output (text mode):**
```
✓ Valid apparatus
  File: out/apparatus.jsonl
  Records: 5
  Schema: 1.0.0
```

**Output (JSON mode):**
```json
{
  "valid": true,
  "artifact_type": "apparatus",
  "file_path": "out/apparatus.jsonl",
  "errors": [],
  "warnings": [],
  "records_checked": 5,
  "schema_version_found": "1.0.0"
}
```

### `redletters validate schemas`

List all schema versions for all artifact types.

```bash
redletters validate schemas
```

---

## Schema Files

JSON Schema files are located in `docs/schemas/`:

| File | Artifact |
|------|----------|
| `apparatus-v1.0.0.schema.json` | Apparatus JSONL record |
| `translation-v1.0.0.schema.json` | Translation JSONL record |
| `quote-v1.0.0.schema.json` | Quote JSON output |
| `snapshot-v1.0.0.schema.json` | Reproducibility snapshot |
| `citations-v1.0.0.schema.json` | Citations export (CSL-JSON wrapper) |
| `dossier-v1.0.0.schema.json` | Variant dossier output |

---

## Versioning Policy

Schema versions follow semantic versioning:

- **Major bump (X.0.0)**: Breaking changes (field removal, type changes)
- **Minor bump (0.X.0)**: Additive optional fields
- **Patch bump (0.0.X)**: Documentation or clarification only

All schema versions are centralized in:
`src/redletters/export/schema_versions.py`

---

## New Fields

### Snapshot.schema_versions (v0.10.0)

```json
{
  "tool_version": "0.10.0",
  "schema_version": "1.0.0",
  "schema_versions": {
    "apparatus": "1.0.0",
    "translation": "1.0.0",
    "snapshot": "1.0.0",
    "citations": "1.0.0",
    "quote": "1.0.0",
    "dossier": "1.0.0",
    "senses_explain": "1.0.0",
    "senses_conflicts": "1.0.0",
    "confidence_bucketing": "1.0.0"
  },
  ...
}
```

### Dossier.schema_version (v0.10.0)

```json
{
  "reference": "John.1.1-5",
  "scope": "verse",
  "schema_version": "1.0.0",
  ...
}
```

---

## Non-Negotiables

1. Every public artifact has explicit `schema_version` field
2. JSON Schema files exist for all artifact types
3. CLI validator works offline (no network calls)
4. Validator fails on tampered/incomplete output
5. Snapshot includes `schema_versions` mapping
6. Version constants are centralized in one module
7. All validation is deterministic

---

## Troubleshooting

**Validation fails with "Could not auto-detect artifact type":**
```bash
# Use explicit --type flag
redletters validate output out/myfile.json --type quote
```

**Validation fails with schema version mismatch warning:**
```
Warnings:
  - Schema version mismatch: found=0.9.0, expected=1.0.0
```
This is a warning, not an error. The file was generated with an older schema version.

**Missing schema_version in output:**
```bash
# Re-generate the output with v0.10.0+ tool
redletters quote "John 1:1" --out out/quote.json --force
```
