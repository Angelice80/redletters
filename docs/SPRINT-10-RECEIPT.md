# Sprint 10 Receipt: Traceable Ledger Mode

**Status:** COMPLETE
**Date:** 2026-02-01
**Sprint Goal:** Token-level evidence "receipt-grade" translation ledger with UI/CLI wiring

---

## Non-Negotiables Validated

| ADR | Requirement | Status |
|-----|-------------|--------|
| ADR-007 | SBLGNT canonical spine | ✅ Ledger provenance always shows `spine_source_id: "sblgnt"` |
| ADR-008 | Variants side-by-side | ✅ Preserved in traceable mode, no changes |
| ADR-009 | TYPE5+ forbidden in readable mode | ✅ `_filter_claims_for_mode()` enforces |
| ADR-010 | Layered confidence always visible | ✅ Every token has T/G/L/I scores |

**Evidence class explicit (not collapsed):**
✅ `EvidenceClassSummary` has separate counts: `manuscript_count`, `edition_count`, `tradition_count`, `other_count`
✅ No `support_score` or `total_support` fields exist

---

## Build Items Completed

### B1: TraceableLedger Data Model ✅
**Files:**
- `src/redletters/ledger/__init__.py` - Module exports
- `src/redletters/ledger/schemas.py` - Core dataclasses

**Types Created:**
- `TokenConfidence` - Four-layer confidence (textual, grammatical, lexical, interpretive)
- `TokenLedger` - Token-level entry with surface, lemma, morph, gloss, source, notes
- `SegmentLedger` - Translation segment mapping Greek→English phrases
- `EvidenceClassSummary` - Explicit counts per witness type
- `LedgerProvenance` - Spine ID + comparative sources + evidence summary
- `VerseLedger` - Per-verse container for tokens and provenance

### B2: LexiconProvider Interface ✅
**Files:**
- `src/redletters/lexicon/__init__.py` - Module exports
- `src/redletters/lexicon/provider.py` - Protocol and implementation

**Components:**
- `LexiconProvider` - Protocol for gloss lookup with source_id and license_info
- `BasicGlossProvider` - CC0/Public Domain basic glosses (~90 words)
- `GlossResult` - Result with gloss, source, confidence, alternatives
- `ChainedLexiconProvider` - Multi-source fallback chain
- `normalize_greek()` - Accent-stripping utility for dictionary lookup
- Semantic range data for theological terms (λόγος, πίστις, σάρξ, etc.)

### B3: TraceableTranslator ✅
**File:** `src/redletters/pipeline/traceable_translator.py`

**Features:**
- Wraps `FluentTranslator` for English output
- Builds token-level ledger in traceable mode only
- Four-layer confidence scoring per token
- Variant-aware textual confidence
- Parse-aware grammatical confidence
- Semantic range detection for interpretive confidence
- Claims filtered by mode (TYPE5+ excluded in readable)

**Integration:**
- Added to translator factory (`get_translator(translator_type="traceable")`)
- Updated `src/redletters/pipeline/translator.py` factory function
- Updated `src/redletters/pipeline/schemas.py` with `ledger` field

### B4: GUI Ledger Panel ✅
**Files:**
- `gui/src/components/LedgerPanel.tsx` - New component
- `gui/src/screens/Translate.tsx` - Integration
- `gui/src/api/types.ts` - TypeScript types

**Components:**
- `LedgerPanel` - Collapsible panel for verse ledger
- `TokenTable` - Token grid (surface, lemma, morph, gloss, confidence)
- `MiniConfidenceBars` - T/G/L/I confidence visualization
- `ProvenanceBadges` - Spine + comparative pack badges
- `LedgerList` - Multi-verse ledger container

**UI Features:**
- Greek font styling for surface/lemma columns
- Color-coded confidence bars (green ≥0.8, amber ≥0.6, red <0.6)
- Evidence class display (MSS/Ed/Trad counts)
- Traceable translator option in dropdown

### B5: CLI Traceable Output ✅
**File:** `src/redletters/__main__.py`

**New Options:**
- `--translator traceable` - Use traceable translator
- `--ledger` - Show token ledger in human output
- `--json` - Output full JSON (includes ledger automatically)

**Output Features:**
- Token table with Rich formatting
- Confidence display as T/G/L/I ratios
- Provenance (spine + comparative sources)
- Evidence class counts

---

## Test Coverage

### New Test File: `tests/test_traceable_ledger.py`

**38 tests covering:**
- `TokenConfidence` creation and serialization
- `TokenLedger` with full data, notes, null lemma
- `SegmentLedger` creation
- `EvidenceClassSummary` explicit counts (no collapsed fields)
- `LedgerProvenance` with/without comparative sources
- `VerseLedger` complete structure
- `normalize_greek()` accent stripping
- `LexiconProvider` protocol compliance
- `BasicGlossProvider` lookup (common words, articles, prepositions)
- `GlossResult` creation
- `TraceableTranslator` initialization and translation
- Translator factory integration
- ADR-010 compliance (layered confidence always present)

**Full suite:** 702 tests passing (664 existing + 38 new)

---

## Files Modified/Created

### New Files
```
src/redletters/ledger/__init__.py
src/redletters/ledger/schemas.py
src/redletters/lexicon/__init__.py
src/redletters/lexicon/provider.py
src/redletters/pipeline/traceable_translator.py
gui/src/components/LedgerPanel.tsx
tests/test_traceable_ledger.py
docs/SPRINT-10-MAP.md
docs/SPRINT-10-RECEIPT.md
```

### Modified Files
```
src/redletters/pipeline/schemas.py      # Added ledger field to TranslateResponse
src/redletters/pipeline/translator.py   # Added traceable to factory
src/redletters/__main__.py              # CLI --ledger, --json, traceable translator
gui/src/api/types.ts                    # TypeScript ledger types
gui/src/screens/Translate.tsx           # LedgerPanel integration
```

---

## Usage Examples

### CLI
```bash
# Human output with ledger table
redletters translate "John 1:18" --translator traceable --mode traceable --ledger

# JSON output (includes ledger automatically)
redletters translate "John 1:18" --translator traceable --mode traceable --json
```

### API Response (traceable mode)
```json
{
  "response_type": "translation",
  "reference": "John 1:18",
  "translation_text": "No one has ever seen God...",
  "ledger": [
    {
      "verse_id": "John.1.18",
      "normalized_ref": "John 1:18",
      "tokens": [
        {
          "position": 0,
          "surface": "Θεὸν",
          "normalized": "Θεον",
          "lemma": "θεός",
          "morph": "N-ASM",
          "gloss": "God",
          "gloss_source": "basic_glosses",
          "notes": [],
          "confidence": {
            "textual": 0.9,
            "grammatical": 0.9,
            "lexical": 0.8,
            "interpretive": 0.85,
            "explanations": {...}
          }
        }
      ],
      "provenance": {
        "spine_source_id": "sblgnt",
        "comparative_sources_used": [],
        "evidence_class_summary": {
          "manuscript_count": 0,
          "edition_count": 1,
          "tradition_count": 0,
          "other_count": 0
        }
      }
    }
  ]
}
```

---

## Definition of Done

| Criterion | Status |
|-----------|--------|
| All BUILD items complete | ✅ |
| Full test suite passes (702 tests) | ✅ |
| Non-negotiables validated | ✅ |
| Evidence class explicit, not collapsed | ✅ |
| Backward compatibility preserved | ✅ |
| CLI examples work as documented | ✅ |
| GUI shows ledger in traceable mode | ✅ |

---

## Notes

- The `BasicGlossProvider` is intentionally minimal (~90 words) for CC0/Public Domain compliance
- Future sprints may add additional lexicon providers (e.g., Strongs, BDAG) via `ChainedLexiconProvider`
- Segment-level alignment (`translation_segments`) is stubbed but not fully implemented yet
- The translator always uses "sblgnt" as spine_source_id per ADR-007, even when source_id differs
