# Runbook: Scholarly Tool v0.9.0 - Minority Metadata + Incentive Tags + Quote Friction

## Version: v0.9.0
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

### 3. Generate Dossier with New Fields

```bash
redletters dossier "John 1:1-18" --json > out/dossier.json
```

**Verify dossier contains:**
- Each reading has `confidence_bucket` (existing)
- Each reading has `consequence_summary` (existing)
- Each reading has `minority_metadata` with:
  - `attestation_strength`: "strong" | "moderate" | "weak" | null
  - `historical_uptake`: null (not derived)
  - `ideological_usage`: [] (not derived)
- Each reading has `incentive_tags`: list of strings (may be empty)
  - Possible tags: `brevity_preference_present`, `age_bias_risk`

```bash
cat out/dossier.json | jq '.variants[0].readings[0].minority_metadata'
cat out/dossier.json | jq '.variants[0].readings[0].incentive_tags'
```

### 4. Export Apparatus with New Fields

```bash
redletters export apparatus "John 1:1-18" --out out/apparatus.jsonl --force
```

**Verify apparatus includes:**
```bash
head -1 out/apparatus.jsonl | jq '.readings[0].minority_metadata'
head -1 out/apparatus.jsonl | jq '.readings[0].incentive_tags'
```

### 5. Quote Friction Test (Fails Without Acknowledgement)

```bash
# Should fail with pending gates
redletters quote "John 1:1" --out out/quote.json
# Exit code should be 1
# Output should mention pending gates
```

### 6. Quote with Force

```bash
redletters quote "John 1:1" --out out/quote_forced.json --force
```

**Verify output:**
```bash
cat out/quote_forced.json | jq '.gate_status'
# Should show:
# {
#   "gates_cleared": false,
#   "forced_responsibility": true,
#   "pending_gates": [...]
# }
```

### 7. Acknowledge Gates

```bash
redletters gates acknowledge "John 1:1-18" --all --reason "Reviewed"
```

### 8. Quote After Acknowledgement

```bash
redletters quote "John 1:1" --out out/quote_cleared.json
```

**Verify output:**
```bash
cat out/quote_cleared.json | jq '.gate_status'
# Should show:
# {
#   "gates_cleared": true,
#   "forced_responsibility": false
# }
```

### 9. Snapshot with Quote

```bash
redletters export snapshot \
  --out out/snapshot.json \
  --include-citations \
  --inputs out/apparatus.jsonl,out/quote_cleared.json
```

### 10. Verify Snapshot

```bash
redletters export verify \
  --snapshot out/snapshot.json \
  --inputs out/apparatus.jsonl,out/quote_cleared.json
```

### 11. Run Tests

```bash
pytest && ruff check && ruff format --check
```

All must pass.

---

## New CLI Commands

### `redletters quote`

Generate a citeable quote with gate friction enforcement.

```bash
redletters quote <reference> [OPTIONS]

Arguments:
  reference       Scripture reference (e.g., "John 1:1")

Options:
  --mode          Output mode: readable | traceable (default: readable)
  --out           Output file path (prints to stdout if not specified)
  --session-id    Session ID for gate checking (default: cli-default)
  --force         Generate quote even with pending gates
  --data-root     Override data root path
```

**Output format:**
```json
{
  "reference": "John 1:1",
  "reference_normalized": "John.1.1",
  "mode": "readable",
  "spine_text": "...",
  "provenance": {
    "packs_used": ["morphgnt-sblgnt", "..."],
    "session_id": "cli-default"
  },
  "gate_status": {
    "gates_cleared": true,
    "forced_responsibility": false
  },
  "confidence_summary": {
    "variants_in_scope": 2,
    "significance_breakdown": {"minor": 1, "significant": 1}
  },
  "generated_at": "2026-02-02T...",
  "schema_version": "1.0.0"
}
```

---

## New Fields

### MinorityMetadata (on readings)

```json
{
  "attestation_strength": "strong" | "moderate" | "weak" | null,
  "historical_uptake": null,
  "ideological_usage": []
}
```

Derivation rules for `attestation_strength`:
- `strong`: 3+ witnesses OR earliest_century <= 3
- `moderate`: 1-2 witnesses AND earliest_century in [4, 6]
- `weak`: 1 witness AND (no century OR century > 6)
- `null`: No support data

### Incentive Tags (on readings)

```json
{
  "incentive_tags": ["brevity_preference_present", "age_bias_risk"]
}
```

Derivation rules:
- `brevity_preference_present`: readings differ by >= 2 words
- `age_bias_risk`: earliest_century differs by >= 2 between readings

---

## Non-Negotiables

1. MinorityMetadata preserved for ALL readings
2. Incentive tags are neutral labels, not editorial commentary
3. historical_uptake and ideological_usage are NOT derived (pack-provided only)
4. Quote fails without acknowledgement unless --force
5. forced_responsibility=true marked in output when forced
6. Derivation is conservative and deterministic

---

## Troubleshooting

**Quote fails with "Database not found":**
```bash
redletters init
```

**Quote fails with pending gates:**
```bash
# Either acknowledge gates:
redletters gates acknowledge "John 1:1" --reason "Reviewed"

# Or use --force (marks forced_responsibility):
redletters quote "John 1:1" --force --out out/quote.json
```

**No minority_metadata in dossier:**
- Check that variants exist for the reference
- Check support_set has data (century_range, witness counts)
