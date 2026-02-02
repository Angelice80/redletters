# Sprint 7 Receipt: Real Data + Bulk Build + Gate Hygiene

**Sprint Duration**: 2026-02-01
**Status**: COMPLETE

## Objectives Delivered

### B1: Real Data Pack (Westcott-Hort John)
- Created `data/packs/westcott-hort-john/` data pack structure
- Pack manifest with witness_siglum "WH", Public Domain license
- John chapter 1 with 51 verses including key variant at John 1:18 (υἱός vs θεός)
- New `PackLoader` class for loading pack data from TSV files
- New `PackSpineAdapter` to bridge packs to SpineProvider interface
- Updated `sources_catalog.yaml` with pack configuration

### B2: Bulk Variant Build
- Added `VariantBuilder.build_chapter(book, chapter)` method
- Added `VariantBuilder.build_book(book)` method
- Added `VariantBuilder.build_range(start, end)` / `build_passage()` methods
- New `/variants/build` API endpoint with scope parameter (book/chapter/passage)
- `VariantBuildRequest` and `VariantBuildResponse` Pydantic models

### B3: Multi-Ack Support
- New `/acknowledge/multi` API endpoint for batch acknowledgements
- Supports both single ack (backward compatible) and array of acks
- Records scope metadata (verse/passage/book) for audit trail
- `AcknowledgeMultiRequest` and `AcknowledgeMultiResponse` types
- GUI "Acknowledge All" button in Gate screen

### B4: Reason Classification
- `VariantReason` dataclass with code, summary, detail fields
- `_classify_reason()` method in VariantBuilder
- Theological keyword detection (God, Christ, Jesus, Lord, Spirit, Son, Father, etc.)
- Article/particle detection
- Word order detection
- Reason fields persisted in variant_units table
- Reason display in GUI Gate screen

## Files Changed

### New Files
- `src/redletters/sources/pack_loader.py` - Pack loading and parsing
- `data/packs/westcott-hort-john/manifest.json` - W-H pack manifest
- `data/packs/westcott-hort-john/John/chapter_01.tsv` - John 1 verses
- `tests/integration/test_sprint7_variants.py` - Sprint 7 integration tests
- `docs/SPRINT-7-MAP.md` - Sprint planning document

### Modified Files
- `src/redletters/sources/catalog.py` - Added pack fields to SourcePack
- `src/redletters/sources/installer.py` - Local pack installation support
- `src/redletters/sources/spine.py` - Added PackSpineAdapter class
- `src/redletters/variants/builder.py` - Bulk build and reason classification
- `src/redletters/variants/models.py` - Added reason fields to VariantUnit
- `src/redletters/variants/store.py` - Reason field persistence
- `src/redletters/api/models.py` - Sprint 7 request/response models
- `src/redletters/api/routes.py` - /variants/build and /acknowledge/multi endpoints
- `sources_catalog.yaml` - westcott-hort-john pack entry
- `gui/src/api/types.ts` - Sprint 7 TypeScript types
- `gui/src/api/client.ts` - acknowledgeMulti() method
- `gui/src/screens/Gate.tsx` - Multi-ack button and reason display

## ADR Confirmations

| ADR | Requirement | Status |
|-----|-------------|--------|
| ADR-007 | SBLGNT canonical spine | CONFIRMED - All comparative editions compared against SBLGNT spine |
| ADR-008 | Variants side-by-side with ack | CONFIRMED - Gate screen shows variants inline, never buried in footnotes |
| ADR-009 | Readable/traceable gating | CONFIRMED - Mode-based enforcement preserved in all endpoints |
| ADR-010 | Layered confidence | CONFIRMED - Confidence scoring unchanged, works with new variants |

## Test Coverage

```
tests/integration/test_sprint7_variants.py - 13 tests
  TestPackLoader - 4 tests (B1)
  TestPackSpineAdapter - 2 tests (B1)
  TestBulkVariantBuild - 3 tests (B2)
  TestReasonClassification - 1 test (B4)
  TestMultiAck - 2 tests (B3)
  TestVariantStore - 1 test (B4)

Full test suite: 606 tests passing
```

## Quality Gates

- [x] All unit tests pass
- [x] All integration tests pass
- [x] ruff check passes
- [x] ruff format passes
- [x] ADR requirements confirmed
- [x] TypeScript types in sync with Python models

## Database Schema Changes

Added to `variant_units` table:
```sql
reason_code TEXT DEFAULT '',
reason_summary TEXT DEFAULT '',
reason_detail TEXT
```

## API Additions

### POST /variants/build
Build variants for a reference with scope control.

**Request**:
```json
{
  "reference": "John 1",
  "scope": "chapter",
  "source_id": "westcott-hort-john",
  "force": false
}
```

**Response**:
```json
{
  "success": true,
  "reference": "John 1",
  "scope": "chapter",
  "verses_processed": 51,
  "variants_created": 5,
  "variants_updated": 0,
  "variants_unchanged": 46,
  "errors": [],
  "message": "Built variants for John 1: 5 created, 0 updated, 46 unchanged"
}
```

### POST /acknowledge/multi
Batch acknowledge variants.

**Request**:
```json
{
  "session_id": "user-123",
  "acks": [
    {"variant_ref": "John.1.18", "reading_index": 0},
    {"variant_ref": "John.1.34", "reading_index": 0}
  ],
  "scope": "passage"
}
```

**Response**:
```json
{
  "success": true,
  "session_id": "user-123",
  "acknowledged": ["John.1.18", "John.1.34"],
  "count": 2,
  "scope": "passage",
  "errors": []
}
```

## Notes

1. Pack format uses TSV for verse data (simple, diffable, easy to verify)
2. Theological keyword detection supports Greek term variations (nominative, genitive, accusative)
3. Reason classification returns the first detected reason type (theological keywords have priority)
4. Multi-ack preserves individual acknowledgement semantics while enabling batch operations
