# BMAD Receipt: Vertical Slice Implementation

**Date**: 2026-01-31
**Sprint**: Phase 2 - Real Data Integration
**Goal**: Make system FUNCTIONAL end-to-end

---

## DELIVER Summary

### What Was Implemented

A complete **vertical slice** orchestration pipeline allowing users to:
1. Request a passage
2. See SBLGNT text (spine, always marked default)
3. See variants side-by-side (never buried)
4. Be gated when required (significant/major variants, mode escalation)
5. Receive translation with full receipt-grade output

### Files Changed

```
src/redletters/pipeline/
├── __init__.py          # Module exports
├── schemas.py           # Response schemas (GateResponsePayload, TranslateResponse)
├── translator.py        # Translator Protocol + FakeTranslator
└── orchestrator.py      # translate_passage() + acknowledge_variant()

src/redletters/__main__.py   # Added CLI 'translate' command
src/redletters/api/routes.py # Added POST /translate and /acknowledge endpoints

tests/integration/
└── test_vertical_slice.py   # 18 integration tests
```

---

## BUILD: Implementation Details

### A) Orchestration Entrypoint

```python
translate_passage(
    conn: sqlite3.Connection,
    reference: str,                    # "John 1:18"
    mode: "readable" | "traceable",
    session_id: str,
    options: dict | None = None,
    translator: Translator | None = None,
) -> GateResponsePayload | TranslateResponse
```

**Pipeline Steps**:
1. Parse reference → verse keys
2. Fetch SBLGNT spine text (tokens table)
3. Fetch variants from VariantStore
4. Load acknowledgement state for session
5. If significant variant unacked → return `GateResponsePayload`
6. Run translator → get claims
7. Classify + enforce claims (ADR-009 rules)
8. Detect epistemic pressure language
9. If escalation required → return escalation gate
10. Compute layered confidence (ADR-010)
11. Return `TranslateResponse`

### B) Response Schemas

**GateResponsePayload** (when gate triggered):
- gate_id, gate_type, title, message, prompt
- options (acknowledge/cancel/escalate)
- variants_side_by_side (never buried)
- required_dependencies

**TranslateResponse** (when translation completes):
- reference, mode, sblgnt_text, translation_text
- variants[] (side-by-side display)
- claims[] (type, signals, warnings, dependencies, enforcement result)
- confidence (4 layers + composite + weakest + explanations)
- provenance (spine_source=SBLGNT, spine_marker=default, sources, witnesses)
- receipts (checks_run, gates_satisfied, enforcement_results, timestamp)

### C) CLI Command

```bash
# Basic translation
redletters translate "John 1:18"

# With mode and session
redletters translate "John 1:18" --mode traceable --session my-session

# Acknowledge variant and proceed
redletters translate "John 1:18" --ack "John.1.18:0"

# Output to JSON
redletters translate "John 1:18" --output result.json
```

**Exit Codes**:
- 0: Translation successful
- 1: Error (invalid ref, no tokens)
- 2: Gate required (variant/escalation)

### D) API Endpoints

```
POST /translate
  Request: { reference, mode, session_id, options }
  Response: GateResponsePayload | TranslateResponse

POST /acknowledge
  Request: { session_id, variant_ref, reading_index }
  Response: { success, session_id, variant_ref, reading_index }
```

### E) Translator Interface

```python
class Translator(Protocol):
    def translate(self, spine_text: str, context: TranslationContext) -> TranslationDraft

class FakeTranslator:
    # Scenarios: default, high_inference, epistemic_pressure, clean
    # Produces deterministic output for testing

class RealTranslator:
    # Stub for future LLM integration
```

---

## MEASURE: Test Evidence

### Commands Run

```bash
$ pytest tests/integration/test_vertical_slice.py -v
18 passed in 0.64s

$ pytest -q
415 passed, 409 warnings in 22.39s

$ ruff check src/redletters/pipeline/
All checks passed!
```

### Test Coverage

| Category | Tests | Status |
|----------|-------|--------|
| Gate Flow | 3 | ✓ |
| Acknowledgement Persistence | 2 | ✓ |
| Claim Enforcement | 4 | ✓ |
| Confidence Scoring | 2 | ✓ |
| Response Schema | 3 | ✓ |
| Receipt Audit | 2 | ✓ |
| Provenance Tracking | 2 | ✓ |
| **Total** | **18** | **All Pass** |

---

## ANALYZE: Design Validation

### Non-Negotiables Verified

| Requirement | Implementation | Evidence |
|-------------|----------------|----------|
| SBLGNT is spine | `provenance.spine_source = "SBLGNT"`, `spine_marker = "default"` | TranslateResponse always includes |
| Variants surfaced side-by-side | `variants_side_by_side` in both Gate and Translate responses | Never in footnotes |
| Significant variants require ack | `GateResponsePayload` returned until acknowledged | test_significant_variant_triggers_gate |
| Readable mode restrictions | TYPE0-1 allowed, TYPE2-3 with markers, TYPE4 preview, TYPE5-7 forbidden | test_readable_mode_blocks_type5_plus |
| Traceable mode requires deps | Enforcement checks dependencies via `_check_dependencies()` | test_traceable_mode_allows_all_types |
| Confidence is layered | 4 layers (textual/grammatical/lexical/interpretive) | test_confidence_is_layered |
| Epistemic pressure detected | `EpistemicPressureDetector` runs on all claims | test_epistemic_pressure_detected |
| No test dodges | All 18 integration tests pass with real logic | pytest output |

### Gate Flow Determinism

```
Request 1 (no ack) → GateResponsePayload (gate_type=variant)
                     ↓
User acknowledges via --ack or /acknowledge
                     ↓
Request 2 (same session) → TranslateResponse (gates_satisfied includes ref)
```

### Readable vs Traceable Behavior

| Claim Type | Readable | Traceable |
|------------|----------|-----------|
| TYPE0 Descriptive | ✓ Allowed | ✓ Allowed |
| TYPE1 Lexical Range | ✓ Allowed (ranges only) | ✓ Allowed |
| TYPE2 Grammatical | ✓ With hypothesis markers | ✓ With grammar dep |
| TYPE3 Contextual | ✓ With hypothesis markers | ✓ With context dep |
| TYPE4 Theological | ✓ Preview (tradition attr) | ✓ With tradition dep |
| TYPE5 Moral | ✗ Escalation gate | ✓ With hermeneutic dep |
| TYPE6 Metaphysical | ✗ Escalation gate | ✓ With tradition dep |
| TYPE7 Harmonized | ✗ Escalation gate | ✓ With cross-ref dep |

---

## Example Outputs

### GateResponse (Variant)

```json
{
  "response_type": "gate",
  "gate_id": "variant_John.1.18_...",
  "gate_type": "variant",
  "title": "Variant Acknowledgement Required",
  "message": "A major variant exists at John.1.18",
  "options": [
    {"id": "reading_0", "label": "μονογενὴς θεός [SBLGNT]", "is_default": true},
    {"id": "reading_1", "label": "ὁ μονογενὴς υἱός", "is_default": false}
  ],
  "variants_side_by_side": [{
    "ref": "John.1.18",
    "sblgnt_reading": "μονογενὴς θεός",
    "sblgnt_witnesses": "B, P66, P75, א",
    "alternate_readings": [{"surface_text": "ὁ μονογενὴς υἱός", "witnesses": "A, C, D"}],
    "significance": "major",
    "requires_acknowledgement": true,
    "acknowledged": false
  }]
}
```

### TranslateResponse

```json
{
  "response_type": "translation",
  "reference": "John 1:18",
  "mode": "readable",
  "sblgnt_text": "θεὸν οὐδεὶς ἑώρακεν πώποτε",
  "translation_text": "[θεός] [οὐδείς] [ὁράω] [πώποτε]",
  "variants": [...],
  "claims": [
    {"content": "The word 'θεὸν' is a noun.", "claim_type": 0, "enforcement_allowed": true}
  ],
  "confidence": {
    "composite": 0.71,
    "weakest_layer": "textual",
    "layers": {
      "textual": {"score": 0.45, "rationale": "Variant exists; Papyri support"},
      "grammatical": {"score": 0.8},
      "lexical": {"score": 0.7},
      "interpretive": {"score": 1.0}
    }
  },
  "provenance": {"spine_source": "SBLGNT", "spine_marker": "default"},
  "receipts": {"checks_run": [...], "gates_satisfied": ["John.1.18"]}
}
```

---

## Definition of Done Checklist

- [x] CLI works (`redletters translate "John 1:18"`)
- [x] GUI path works minimally (POST /translate, POST /acknowledge)
- [x] Gates enforced (variant acknowledgement, mode escalation)
- [x] Variants surfaced side-by-side (never footnote-buried)
- [x] Confidence layered output present (4 layers + composite + weakest)
- [x] All tests pass (415 passed)
- [x] Linting passes (ruff check clean)

---

## Next Steps

1. **Real Translator**: Implement `RealTranslator` with LLM integration
2. **GUI Integration**: Wire `JobDetail.tsx` to call `/translate` endpoint
3. **Variant Data**: Load real NA28 apparatus into VariantStore
4. **Performance**: Add caching for acknowledgement state
5. **Export**: Add PDF/DOCX export with full receipts

---

**BMAD Status**: ✓ DELIVERED

*Vertical slice is functional. User can request passage → see variants → acknowledge → receive receipt-grade translation.*
