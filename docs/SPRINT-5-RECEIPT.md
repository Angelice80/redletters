# Sprint 5 Receipt: Usable App Mode

**Date**: 2026-02-01
**Status**: Complete

## Overview

Sprint 5 makes redletters "daily-drivable" with a GUI for translation, gate handling with one-click acknowledgement, persistent sessions, and a deterministic FluentTranslator.

## Files Changed

### Backend (Python)

| File | Changes |
|------|---------|
| `src/redletters/api/routes.py` | Added `translator` parameter to /translate endpoint; passes session_id to responses |
| `src/redletters/pipeline/schemas.py` | Added `session_id` and `translator_type` fields to `TranslateResponse` and `GateResponsePayload`; updated `to_dict()` methods |
| `src/redletters/pipeline/translator.py` | Added `FluentTranslator` class with deterministic transform rules; added `BASIC_GLOSSES_NORMALIZED` for accent-insensitive lookup |
| `src/redletters/pipeline/__init__.py` | Exported `FluentTranslator`, `FluentTranslationDraft`, `get_translator` |
| `src/redletters/__main__.py` | Added "fluent" option to `--translator` flag; added GUI hint when variant gate triggers |

### Frontend (TypeScript/React)

| File | Changes |
|------|---------|
| `gui/src/api/types.ts` | Added comprehensive types: `TranslateRequest`, `TranslateResponse`, `GateResponse`, `ConfidenceResult`, `ClaimResult`, `VariantDisplay`, etc. |
| `gui/src/api/client.ts` | Added `translate()` and `acknowledge()` methods to `ApiClient` |
| `gui/src/store/index.ts` | Added `sessionId` to Settings with UUID generation and localStorage persistence |
| `gui/src/screens/Translate.tsx` | **NEW**: Main translation screen with reference input, mode/translator selectors, confidence bars, claims display |
| `gui/src/screens/Gate.tsx` | **NEW**: Side-by-side variant display with SBLGNT default highlighted, acknowledge button |
| `gui/src/App.tsx` | Added routes for `/translate` and `/gate`; added Translate link to navigation |

### Tests

| File | Tests | Status |
|------|-------|--------|
| `tests/test_fluent_translator.py` | 16 tests | All passing |
| `tests/integration/test_session_flow.py` | 15 tests | All passing |

## New Tests and What They Prove

### FluentTranslator Unit Tests (`tests/test_fluent_translator.py`)

1. **test_fluent_translator_produces_draft** - FluentTranslator returns FluentTranslationDraft with correct style
2. **test_article_dropping** - Articles dropped from beginning of translations (ARTICLE_DROP rule)
3. **test_postpositive_de_reordering** - δέ moved to sentence start as "But" (POSTPOSITIVE_DE rule)
4. **test_postpositive_gar_reordering** - γάρ moved to sentence start as "For" (POSTPOSITIVE_GAR rule)
5. **test_postpositive_oun_reordering** - οὖν moved to sentence start as "Therefore" (POSTPOSITIVE_OUN rule)
6. **test_transform_log_recorded** - All applied rules appear in transform_log with "RULE_NAME: applied" format
7. **test_bracket_removal** - BRACKET_CLEAN rule removes all [word] patterns
8. **test_readable_mode_no_type5_claims** - TYPE5+ claims blocked in readable mode (ADR-009)
9. **test_readable_mode_hypothesis_markers** - TYPE2-3 claims get hedging language ("likely", "probably")
10. **test_traceable_mode_allows_all_claims** - All claim types pass through in traceable mode
11. **test_deterministic_output** - Same input always produces identical output
12. **test_fluent_notes_include_transform_count** - Notes mention "transform" count
13. **test_fluent_translator_preserves_source_provenance** - License claims included
14. **test_fluent_translator_with_empty_tokens** - Handles empty token list gracefully
15. **test_fluent_translator_with_variants** - Includes canonical reading claims when variants present
16. **test_get_translator_returns_fluent** - Factory function returns correct type

### Session Flow Integration Tests (`tests/integration/test_session_flow.py`)

1. **test_translate_response_has_session_id_field** - TranslateResponse includes session_id
2. **test_gate_response_has_session_id_field** - GateResponsePayload includes session_id
3. **test_translate_response_to_dict_includes_session_id** - to_dict() serializes session_id
4. **test_gate_response_to_dict_includes_session_id** - to_dict() serializes session_id
5. **test_full_translate_response_serialization** - Complete response with all fields serializes correctly
6. **test_gate_response_structure** - Gate response has options, variants_side_by_side, required_acks
7. **test_get_fake_translator** - get_translator("fake") returns FakeTranslator
8. **test_get_literal_translator** - get_translator("literal") returns LiteralTranslator
9. **test_get_fluent_translator** - get_translator("fluent") returns FluentTranslator
10. **test_translator_produces_output** - All translator types produce valid output
11. **test_fluent_transforms_applied** - FluentTranslator applies transforms and logs them
12. **test_fluent_readable_mode_filters_claims** - TYPE5+ claims filtered in readable mode
13. **test_fluent_includes_provenance** - FluentTranslator includes CC-BY-SA license
14. **test_literal_produces_bracketed_output** - LiteralTranslator outputs [bracketed] glosses
15. **test_literal_known_word_glosses** - LiteralTranslator glosses known words (θεός→God, λόγος→word)

## ADR Compliance Confirmations

| ADR | Requirement | Status |
|-----|-------------|--------|
| ADR-007 | SBLGNT remains canonical spine | ✓ SBLGNT reading always index 0 and highlighted as default |
| ADR-008 | Variants displayed side-by-side, gate before translation | ✓ Gate screen shows side-by-side with witnesses |
| ADR-009 | FluentTranslator enforces TYPE0-4 in readable mode | ✓ TYPE5+ blocked, TYPE2-3 get hedging markers |
| ADR-010 | Confidence layers always shown (collapsible but not hidden) | ✓ Confidence bars always rendered, expandable details |

## UX Confirmations

- [x] **Gate screen**: Shows side-by-side variants with SBLGNT highlighted as default
- [x] **One-click acknowledge**: "Acknowledge & Continue" button acknowledges and auto-retries translation
- [x] **Session persistence**: session_id generated via UUID, persisted to localStorage
- [x] **Translator selection**: Dropdown to choose fake/literal/fluent translator
- [x] **Mode selection**: Radio buttons for readable/traceable mode
- [x] **Confidence display**: Visual bars with expandable layer breakdown
- [x] **Claims display**: Expandable section showing all claims
- [x] **Variants display**: Expandable section showing variant info

## Quality Checks

```bash
$ ruff check .
All checks passed!

$ ruff format --check .
108 files already formatted

$ python -m pytest -q
593 passed, 409 warnings in 22.53s
```

## Key Implementation Notes

### FluentTranslator Transform Rules

```python
FLUENT_RULES = [
    ("POSTPOSITIVE_DE", r"(\[[^\]]+\]) \[but\]", r"But \1"),
    ("POSTPOSITIVE_GAR", r"(\[[^\]]+\]) \[for\]", r"For \1"),
    ("POSTPOSITIVE_OUN", r"(\[[^\]]+\]) \[therefore\]", r"Therefore \1"),
    ("ARTICLE_DROP_LEADING", r"^\[the\] ", ""),
    ("GENITIVE_POSSESSIVE", r"\[of\] \[the\] (\[[^\]]+\])", r"\1's"),
    ("BRACKET_CLEAN", r"\[([^\]]+)\]", r"\1"),
]
```

### Session ID Generation

Frontend generates UUID using `crypto.randomUUID()` with fallback for older browsers. Session ID persists across page reloads via Zustand persist middleware.

### Accent-Insensitive Greek Lookup

BASIC_GLOSSES dictionary now has a normalized companion (`BASIC_GLOSSES_NORMALIZED`) that strips diacritical marks for lookup, enabling `θεός` to match whether input has accents or not.

## CLI Example

```bash
$ python -m redletters translate "John 1:1" --translator fluent --mode readable
```

When a variant gate triggers:
```
Gate triggered: Variant acknowledgement required at John.1.18
Tip: Use GUI for easiest acknowledgement flow
```

## GUI Usage

1. Start API: `python -m redletters serve`
2. Start GUI: `cd gui && npm run tauri dev`
3. Navigate to Translate screen
4. Enter reference (e.g., "John 1:18")
5. Select Fluent translator and Readable mode
6. Click Translate
7. If variant gate appears, review variants and click "Acknowledge & Continue"
8. View translation with confidence breakdown and claims
