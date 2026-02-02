# Sprint 7 MAP: Real Data + Bulk Build + Gate Hygiene

## Goal
Move from "demo fixtures" to "real NT coverage" by enabling:
1. Installation of real, open-license data packs
2. Bulk building of variants across books/chapters
3. Gate hygiene so users can batch-acknowledge

## ADR Invariants (DO NOT BREAK)
- ADR-007: SBLGNT is canonical spine + default reading
- ADR-008: Variants surfaced side-by-side; significant/major require explicit ack
- ADR-009: readable vs traceable claim gating unchanged
- ADR-010: layered confidence always shown and explainable

---

## B1: Real Open-License Data Pack

### Pack Format
```
data/packs/westcott-hort-john/
  ├── manifest.json          # Pack metadata
  ├── John/
  │   ├── chapter_01.tsv     # Verse-level text
  │   ├── chapter_02.tsv
  │   └── ...
```

**manifest.json schema:**
```json
{
  "pack_id": "westcott-hort-john",
  "name": "Westcott-Hort John",
  "version": "1.0.0",
  "license": "Public Domain",
  "role": "comparative_layer",
  "witness_siglum": "WH",
  "witness_type": "version",
  "date_range": [19, 19],
  "books": ["John"],
  "verse_count": 878,
  "format": "tsv"
}
```

**chapter_NN.tsv format:**
```
John.1.1	Ἐν ἀρχῇ ἦν ὁ λόγος...
John.1.2	οὗτος ἦν ἐν ἀρχῇ...
```

### Files to Create/Modify

| File | Action |
|------|--------|
| `sources_catalog.yaml` | Add `westcott-hort-john` pack entry |
| `src/redletters/sources/pack_loader.py` | **NEW** - PackLoader class |
| `src/redletters/sources/installer.py` | Extend for pack installation |
| `data/packs/westcott-hort-john/` | **NEW** - Real W-H John data |

---

## B2: Bulk Variant Build

### CLI Command
```bash
redletters variants build "John" --scope book
redletters variants build "John 1" --scope chapter
redletters variants build "John 1:1-18" --scope passage
```

### API Endpoint
```
POST /variants/build
{
  "reference": "John",
  "scope": "book",     // book | chapter | passage
  "source_id": "westcott-hort-john",  // optional, default all
  "force": false       // rebuild even if exists
}
```

### Files to Create/Modify

| File | Action |
|------|--------|
| `src/redletters/cli/variants.py` | **NEW** - CLI commands |
| `src/redletters/api/routes.py` | Add `POST /variants/build` |
| `src/redletters/api/models.py` | Add `VariantBuildRequest/Response` |
| `src/redletters/variants/builder.py` | Add `build_book`, `build_chapter` |

---

## B3: Gate Hygiene - Multi-Ack

### Schema Changes

**acknowledgements table (extend):**
```sql
ALTER TABLE acknowledgements ADD COLUMN scope TEXT DEFAULT 'verse';
-- scope: 'verse' | 'passage' | 'book'
```

### API Changes

**POST /acknowledge (extended):**
```json
{
  "session_id": "abc",
  "acks": [
    {"variant_ref": "John.1.18", "reading_index": 0},
    {"variant_ref": "John.1.19", "reading_index": 0}
  ],
  "scope": "passage"  // optional metadata
}
```

Backward compatible: single `variant_ref` + `reading_index` still works.

### Files to Create/Modify

| File | Action |
|------|--------|
| `src/redletters/api/models.py` | Add `AckItem`, extend `AcknowledgeRequestModel` |
| `src/redletters/api/routes.py` | Extend `/acknowledge` handler |
| `src/redletters/gates/state.py` | Add scope to schema, extend persist |
| `gui/src/api/types.ts` | Add multi-ack types |
| `gui/src/screens/Gate.tsx` | Add "Ack all for passage" button |

---

## B4: UX Signal - Reason Classifier

### Reason Classification Rules
```python
REASON_RULES = {
    "theological_keyword": ("major", "theological term change"),
    "article_particle": ("minor", "function word variation"),
    "word_order": ("minor", "word order difference"),
    "spelling": ("trivial", "spelling variation"),
    "default": ("significant", "lexical variation"),
}
```

### Schema Changes

**RequiredAck (extend):**
```python
@dataclass
class RequiredAck:
    verse_id: str
    variant_ref: str
    reading_index: int | None
    significance: str
    message: str
    reason: str  # NEW
    reason_detail: str | None  # NEW
```

### Files to Create/Modify

| File | Action |
|------|--------|
| `src/redletters/variants/builder.py` | Add `_classify_reason()` |
| `src/redletters/variants/models.py` | Add `reason`, `reason_detail` to VariantUnit |
| `src/redletters/pipeline/schemas.py` | Extend RequiredAck |
| `gui/src/api/types.ts` | Extend RequiredAck |
| `gui/src/screens/Gate.tsx` | Show reason in UI |

---

## Test Plan

| Test | Description |
|------|-------------|
| `test_pack_install` | Install W-H pack -> status OK |
| `test_bulk_build_chapter` | Build variants for John 1 -> variants exist |
| `test_bulk_build_idempotent` | Re-run build -> no duplicates |
| `test_translate_multi_gate` | Translate John 1:1-18 -> returns >=2 required_acks |
| `test_ack_list` | POST /acknowledge with list -> all persisted |
| `test_ack_scope` | Scope recorded correctly in DB |
| `test_gate_reason` | Gate response includes reason field |

---

## Definition of Done

On a clean environment:
1. Install spine + W-H John pack (CLI or GUI)
2. Build variants for John 1: `redletters variants build "John 1" --scope chapter`
3. Translate "John 1:1-18" -> gate appears with multiple variants
4. Click "Acknowledge all for passage" -> translation completes
5. Re-translate same passage -> no gate (already acked)
6. All tests pass: `pytest && ruff check && ruff format --check`
