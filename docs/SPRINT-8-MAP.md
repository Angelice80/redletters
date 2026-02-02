# Sprint 8 MAP: Evidence-Grade Translation at Scale

**Goal**: Transform the system from "John 1 demo + build variants" into scalable source packs, witness-aware variant support, and an upgradeable translation backend.

**Author**: BMad Orchestrator
**Date**: 2026-02-01
**Sprint**: 8

---

## Table of Contents

1. [Pack Spec v1.1 Schema](#1-pack-spec-v11-schema)
2. [YAML Catalog Additions](#2-yaml-catalog-additions)
3. [Database Changes](#3-database-changes)
4. [API Additions](#4-api-additions)
5. [TypeScript Type Additions](#5-typescript-type-additions)
6. [Implementation Order](#6-implementation-order)
7. [Test Plan](#7-test-plan)
8. [Acceptance Criteria](#8-acceptance-criteria)

---

## 1. Pack Spec v1.1 Schema

### 1.1 Manifest Schema (manifest.json)

```json
{
  "$schema": "https://redletters.io/schemas/pack-manifest-v1.1.json",
  "format_version": "1.1",

  "id": "westcott-hort-john",
  "name": "Westcott-Hort Greek NT (John)",
  "version": "1.0.0",

  "license": "Public Domain",
  "license_url": "https://example.com/license",

  "role": "comparative_layer",
  "siglum": "WH",
  "witness_type": "edition",
  "century_range": [19, 19],

  "coverage": ["John"],

  "provenance": {
    "source": "Westcott & Hort, The New Testament in the Original Greek (1881)",
    "digitized_from": "Public domain transcription",
    "notes": "Key variants marked where W-H differs from SBLGNT"
  },

  "index": {
    "generated_at": "2026-02-01T12:00:00Z",
    "total_verses": 51,
    "books": {
      "John": {
        "chapters": {
          "1": {"verse_count": 51, "first_verse": 1, "last_verse": 51}
        }
      }
    }
  }
}
```

### 1.2 Required Manifest Fields (v1.1)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `format_version` | string | **Yes** | Must be "1.1" |
| `id` | string | **Yes** | Unique pack identifier (slug format) |
| `name` | string | **Yes** | Human-readable name |
| `version` | string | **Yes** | SemVer version |
| `license` | string | **Yes** | License name |
| `siglum` | string | **Yes** | Apparatus siglum (e.g., "WH", "TR", "Byz") |
| `witness_type` | enum | **Yes** | One of: "edition", "manuscript", "papyrus", "version", "father" |
| `coverage` | string[] | **Yes** | List of book names covered |

### 1.3 Optional Manifest Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `license_url` | string | null | URL to license text |
| `role` | string | "comparative_layer" | Role in system |
| `century_range` | [int, int] | null | Century range [earliest, latest] |
| `provenance` | object | {} | Source provenance metadata |
| `index` | object | null | Pre-computed coverage index |
| `notes` | string | "" | Additional notes |

### 1.4 Witness Type Enum

```python
class WitnessType(str, Enum):
    EDITION = "edition"       # Critical editions (WH, NA28, UBS5)
    MANUSCRIPT = "manuscript" # Codices (א, B, A, D)
    PAPYRUS = "papyrus"       # Papyri (P66, P75)
    VERSION = "version"       # Ancient translations (Syriac, Latin)
    FATHER = "father"         # Church father quotations
```

### 1.5 TSV Data File Format

**Location**: `{pack_dir}/{Book}/chapter_{NN}.tsv`

**Headers** (required row):
```
verse_id	text	normalized	tokens
```

**Data rows**:
```
John.1.1	Ἐν ἀρχῇ ἦν ὁ λόγος...	εν αρχη ην ο λογος...	[optional JSON]
John.1.2	οὗτος ἦν ἐν ἀρχῇ...	ουτος ην εν αρχη...
```

**Field Definitions**:
| Column | Required | Description |
|--------|----------|-------------|
| `verse_id` | **Yes** | Format: `Book.Chapter.Verse` |
| `text` | **Yes** | Greek text with accents/punctuation |
| `normalized` | No | Lowercase, no accents (auto-generated if absent) |
| `tokens` | No | JSON array of token objects |

**Validation Rules**:
- Header row must be present (starts with `verse_id`)
- verse_id must match pattern: `[A-Za-z0-9]+\.\d+\.\d+`
- Chapter in verse_id must match filename chapter number
- Verses must be in ascending order within file
- No duplicate verse_ids within pack

### 1.6 Optional Witness Metadata File

**Location**: `{pack_dir}/witnesses.json`

```json
{
  "witnesses": [
    {
      "siglum": "WH",
      "full_name": "Westcott-Hort",
      "type": "edition",
      "century_range": [19, 19],
      "description": "Critical edition by B.F. Westcott and F.J.A. Hort (1881)",
      "attestation_notes": "Based primarily on codices א and B"
    }
  ],
  "relationships": [
    {
      "siglum": "WH",
      "based_on": ["א", "B"],
      "relationship_type": "derived_from"
    }
  ]
}
```

---

## 2. YAML Catalog Additions

### 2.1 New Fields for sources_catalog.yaml

```yaml
# Pack Spec v1.1 fields (backward compatible)
westcott-hort-john:
  name: "Westcott-Hort Greek NT (John)"
  # ... existing fields ...

  # NEW v1.1 fields
  format_version: "1.1"           # Pack spec version
  siglum: "WH"                    # Apparatus siglum (alias for witness_siglum)
  witness_type: "edition"         # Standardized type enum
  coverage:                       # Explicit book coverage list
    - "John"
  century_range: [19, 19]         # Replaces date_range for clarity

  # Index metadata (optional, generated by CLI)
  pack_index:
    total_verses: 51
    books:
      John:
        chapters: 2
        verses: 51
```

### 2.2 New Comparative Packs to Add

```yaml
# Pack 1: Tischendorf Mark 1 (different book, open license)
tischendorf-mark:
  name: "Tischendorf 8th Edition (Mark)"
  repo: ""
  commit: ""
  version: "1.0.0"
  license: "Public Domain"
  role: "comparative_layer"
  format: "pack"
  format_version: "1.1"
  pack_path: "data/packs/tischendorf-mark"
  siglum: "Tisch"
  witness_type: "edition"
  coverage:
    - "Mark"
  century_range: [19, 19]
  notes: |
    Tischendorf 8th critical edition (1869-1872).
    Public domain. Contains Mark chapter 1.
    Notable for heavy apparatus and early date.

# Pack 2: Byzantine/TR John 1 (same book, different tradition)
byzantine-john:
  name: "Byzantine Textform (John)"
  repo: ""
  commit: ""
  version: "1.0.0"
  license: "Public Domain"
  role: "comparative_layer"
  format: "pack"
  format_version: "1.1"
  pack_path: "data/packs/byzantine-john"
  siglum: "Byz"
  witness_type: "edition"
  coverage:
    - "John"
  century_range: [21, 21]
  notes: |
    Robinson-Pierpont Byzantine Textform (2018).
    Public domain. John chapter 1.
    Represents majority text tradition.
    Produces meaningful variants from SBLGNT.
```

---

## 3. Database Changes

### 3.1 Schema Additions

No new tables required. Existing schema supports witness tracking. Minor enhancements:

```sql
-- Add source_pack_id to track which pack contributed each witness
ALTER TABLE reading_witnesses
ADD COLUMN source_pack_id TEXT;

-- Add index for pack-based queries
CREATE INDEX IF NOT EXISTS idx_reading_witnesses_pack
ON reading_witnesses(source_pack_id);

-- Add pack_version for provenance
ALTER TABLE sources
ADD COLUMN pack_version TEXT;
ADD COLUMN format_version TEXT;
```

### 3.2 Migration Approach

**Strategy**: Additive-only schema changes (backward compatible)

```python
# In VariantStore.init_schema()
SCHEMA_MIGRATIONS = [
    # v1.1: Add source_pack_id column if missing
    """
    ALTER TABLE reading_witnesses
    ADD COLUMN source_pack_id TEXT
    """,
    # v1.1: Add pack metadata to sources
    """
    ALTER TABLE sources
    ADD COLUMN pack_version TEXT
    """,
    """
    ALTER TABLE sources
    ADD COLUMN format_version TEXT
    """,
]

def migrate_schema(self):
    for migration in SCHEMA_MIGRATIONS:
        try:
            self._conn.execute(migration)
        except sqlite3.OperationalError:
            pass  # Column already exists
    self._conn.commit()
```

### 3.3 Data Model Updates

**WitnessReading** additions:
```python
@dataclass
class WitnessReading:
    # ... existing fields ...
    source_pack_id: str | None = None  # NEW: Which pack contributed this reading
```

**VariantUnit** additions:
```python
@dataclass
class VariantUnit:
    # ... existing fields ...

    def get_witness_summary_by_type(self) -> dict[WitnessType, list[str]]:
        """Group witnesses by type for dossier display."""
        result: dict[WitnessType, list[str]] = {}
        for reading in self.readings:
            for witness, wtype in zip(reading.witnesses, reading.witness_types):
                result.setdefault(wtype, []).append(witness)
        return result

    def get_provenance_summary(self) -> list[str]:
        """Get list of source pack IDs that contributed readings."""
        packs = set()
        for reading in self.readings:
            if reading.source_pack_id:
                packs.add(reading.source_pack_id)
        return sorted(packs)
```

---

## 4. API Additions

### 4.1 Pack CLI Commands

```bash
# Validate pack against spec v1.1
redletters packs validate <path>
  --strict           # Fail on warnings
  --format-version   # Expected version (default: 1.1)

# Generate/update pack index
redletters packs index <path>
  --output-manifest  # Update manifest.json in place
  --dry-run          # Print index without writing

# List installed packs with status
redletters packs list
  --format json|table  # Output format
```

### 4.2 Dossier CLI Command

```bash
# Export variant dossier
redletters variants dossier "<ref>"
  --scope verse|passage|chapter|book  # Default: verse
  --session-id <id>                   # Include ack state
  --output <path>                     # Output file (default: stdout)
  --format json|yaml                  # Output format
```

### 4.3 New API Endpoints

#### GET /variants/dossier

**Request**:
```
GET /variants/dossier?reference=John.1.18&scope=verse&session_id=abc123
```

**Response**:
```json
{
  "reference": "John.1.18",
  "scope": "verse",
  "generated_at": "2026-02-01T12:00:00Z",

  "spine": {
    "source_id": "morphgnt-sblgnt",
    "text": "θεὸν οὐδεὶς ἑώρακεν πώποτε· μονογενὴς θεὸς...",
    "is_default": true
  },

  "variants": [
    {
      "ref": "John.1.18",
      "position": 0,
      "classification": "substitution",
      "significance": "major",
      "gating_requirement": "requires_acknowledgement",

      "reason": {
        "code": "theological_keyword",
        "summary": "Theological term change (Son/God)",
        "detail": "Spine has 'θεος' (God), alternate has 'υιος' (Son)"
      },

      "readings": [
        {
          "index": 0,
          "text": "μονογενὴς θεὸς",
          "is_spine": true,
          "witnesses": [
            {"siglum": "SBLGNT", "type": "edition", "century": 21}
          ],
          "witness_summary": {
            "editions": ["SBLGNT"],
            "papyri": [],
            "uncials": [],
            "minuscules": [],
            "versions": [],
            "fathers": []
          },
          "source_packs": ["morphgnt-sblgnt"]
        },
        {
          "index": 1,
          "text": "μονογενὴς υἱὸς",
          "is_spine": false,
          "witnesses": [
            {"siglum": "WH", "type": "edition", "century": 19}
          ],
          "witness_summary": {
            "editions": ["WH"],
            "papyri": [],
            "uncials": [],
            "minuscules": [],
            "versions": [],
            "fathers": []
          },
          "source_packs": ["westcott-hort-john"]
        }
      ],

      "acknowledgement": {
        "required": true,
        "acknowledged": false,
        "acknowledged_reading": null,
        "session_id": "abc123"
      }
    }
  ],

  "provenance": {
    "spine_source": "morphgnt-sblgnt",
    "comparative_packs": ["westcott-hort-john", "byzantine-john"],
    "build_timestamp": "2026-02-01T11:30:00Z"
  },

  "witness_density_note": "Reading 0 supported by modern critical edition only. Reading 1 supported by 19th century critical tradition."
}
```

#### GET /packs/status

**Response**:
```json
{
  "installed_packs": [
    {
      "id": "westcott-hort-john",
      "name": "Westcott-Hort Greek NT (John)",
      "format_version": "1.1",
      "siglum": "WH",
      "witness_type": "edition",
      "coverage": ["John"],
      "verse_count": 51,
      "index": {
        "John": {"1": 51}
      }
    }
  ],
  "total_packs": 1,
  "total_verses": 51
}
```

### 4.4 Pydantic Models (api/models.py)

```python
# === Dossier Models ===

class WitnessSummary(BaseModel):
    editions: list[str] = []
    papyri: list[str] = []
    uncials: list[str] = []
    minuscules: list[str] = []
    versions: list[str] = []
    fathers: list[str] = []


class WitnessInfo(BaseModel):
    siglum: str
    type: str
    century: int | None = None


class DossierReading(BaseModel):
    index: int
    text: str
    is_spine: bool
    witnesses: list[WitnessInfo]
    witness_summary: WitnessSummary
    source_packs: list[str]


class DossierReason(BaseModel):
    code: str
    summary: str
    detail: str | None = None


class DossierAcknowledgement(BaseModel):
    required: bool
    acknowledged: bool
    acknowledged_reading: int | None = None
    session_id: str | None = None


class DossierVariant(BaseModel):
    ref: str
    position: int
    classification: str
    significance: str
    gating_requirement: str
    reason: DossierReason
    readings: list[DossierReading]
    acknowledgement: DossierAcknowledgement


class DossierSpine(BaseModel):
    source_id: str
    text: str
    is_default: bool = True


class DossierProvenance(BaseModel):
    spine_source: str
    comparative_packs: list[str]
    build_timestamp: str


class DossierResponse(BaseModel):
    reference: str
    scope: str
    generated_at: str
    spine: DossierSpine
    variants: list[DossierVariant]
    provenance: DossierProvenance
    witness_density_note: str | None = None


# === Pack Status Models ===

class PackIndex(BaseModel):
    """Chapter -> verse count mapping."""
    pass  # Dynamic dict


class PackStatusItem(BaseModel):
    id: str
    name: str
    format_version: str
    siglum: str
    witness_type: str
    coverage: list[str]
    verse_count: int
    index: dict[str, dict[str, int]]  # Book -> Chapter -> count


class PacksStatusResponse(BaseModel):
    installed_packs: list[PackStatusItem]
    total_packs: int
    total_verses: int
```

---

## 5. TypeScript Type Additions

### 5.1 gui/src/api/types.ts Additions

```typescript
// === Dossier Types ===

export interface WitnessSummary {
  editions: string[];
  papyri: string[];
  uncials: string[];
  minuscules: string[];
  versions: string[];
  fathers: string[];
}

export interface WitnessInfo {
  siglum: string;
  type: string;
  century: number | null;
}

export interface DossierReading {
  index: number;
  text: string;
  is_spine: boolean;
  witnesses: WitnessInfo[];
  witness_summary: WitnessSummary;
  source_packs: string[];
}

export interface DossierReason {
  code: string;
  summary: string;
  detail: string | null;
}

export interface DossierAcknowledgement {
  required: boolean;
  acknowledged: boolean;
  acknowledged_reading: number | null;
  session_id: string | null;
}

export interface DossierVariant {
  ref: string;
  position: number;
  classification: string;
  significance: string;
  gating_requirement: string;
  reason: DossierReason;
  readings: DossierReading[];
  acknowledgement: DossierAcknowledgement;
}

export interface DossierSpine {
  source_id: string;
  text: string;
  is_default: boolean;
}

export interface DossierProvenance {
  spine_source: string;
  comparative_packs: string[];
  build_timestamp: string;
}

export interface DossierResponse {
  reference: string;
  scope: string;
  generated_at: string;
  spine: DossierSpine;
  variants: DossierVariant[];
  provenance: DossierProvenance;
  witness_density_note: string | null;
}

// === Pack Status Types ===

export interface PackStatusItem {
  id: string;
  name: string;
  format_version: string;
  siglum: string;
  witness_type: string;
  coverage: string[];
  verse_count: number;
  index: Record<string, Record<string, number>>;
}

export interface PacksStatusResponse {
  installed_packs: PackStatusItem[];
  total_packs: number;
  total_verses: number;
}

// === Witness Type Enum ===

export type WitnessTypeEnum =
  | "edition"
  | "manuscript"
  | "papyrus"
  | "version"
  | "father";
```

### 5.2 API Client Additions

```typescript
// In gui/src/api/client.ts

async getDossier(
  reference: string,
  scope: "verse" | "passage" | "chapter" | "book" = "verse",
  sessionId?: string
): Promise<DossierResponse> {
  const params = new URLSearchParams({ reference, scope });
  if (sessionId) params.set("session_id", sessionId);
  return this.request<DossierResponse>(`/variants/dossier?${params}`);
}

async getPacksStatus(): Promise<PacksStatusResponse> {
  return this.request<PacksStatusResponse>("/packs/status");
}
```

---

## 6. Implementation Order

### Phase 1: Pack Spec v1.1 Foundation (B1)

1. **Update PackManifest dataclass** in `pack_loader.py`:
   - Add `format_version`, `siglum`, `witness_type`, `coverage` fields
   - Add backward-compatible loading (default format_version="1.0")

2. **Create pack validator** `src/redletters/sources/pack_validator.py`:
   - Manifest schema validation
   - TSV header validation
   - verse_id format validation
   - Coverage continuity check

3. **Create pack indexer** `src/redletters/sources/pack_indexer.py`:
   - Generate book/chapter/verse counts
   - Optionally update manifest.json

4. **Add CLI commands** in `src/redletters/cli/packs.py`:
   - `validate` subcommand
   - `index` subcommand
   - `list` subcommand

5. **Update sources_catalog.yaml** with new fields

### Phase 2: New Packs (B2)

1. **Create Tischendorf Mark pack**:
   - `data/packs/tischendorf-mark/manifest.json`
   - `data/packs/tischendorf-mark/Mark/chapter_01.tsv`
   - Mark 1:1-45 (45 verses)

2. **Create Byzantine John pack**:
   - `data/packs/byzantine-john/manifest.json`
   - `data/packs/byzantine-john/John/chapter_01.tsv`
   - John 1:1-51 with Byzantine readings

3. **Add to sources_catalog.yaml**

4. **Test installer integration**

### Phase 3: Witness-Aware Enhancements (B3)

1. **Update VariantStore schema** with migration

2. **Update WitnessReading** with `source_pack_id`

3. **Update VariantBuilder.add_edition()** to track pack provenance

4. **Enhance reason classifier** with witness density notes

### Phase 4: Dossier Export (B4)

1. **Create dossier generator** `src/redletters/variants/dossier.py`

2. **Add CLI command** `redletters variants dossier`

3. **Add API endpoint** `GET /variants/dossier`

4. **Add Pydantic models** for dossier response

### Phase 5: GUI Dossier View (B5)

1. **Add TypeScript types** for dossier

2. **Add API client method** `getDossier()`

3. **Create DossierPanel component** in `gui/src/components/`

4. **Integrate into Gate screen** as expandable panel

---

## 7. Test Plan

### 7.1 Unit Tests

#### Pack Validation Tests (`tests/unit/test_pack_validator.py`)

```python
class TestPackValidator:
    def test_valid_manifest_v11(self):
        """Valid v1.1 manifest passes validation."""

    def test_missing_required_field(self):
        """Missing required field fails with clear error."""

    def test_invalid_witness_type(self):
        """Invalid witness_type enum fails validation."""

    def test_invalid_verse_id_format(self):
        """Malformed verse_id fails validation."""

    def test_tsv_missing_header(self):
        """TSV without header row fails validation."""

    def test_chapter_verse_mismatch(self):
        """Verse in wrong chapter file fails validation."""

    def test_duplicate_verse_id(self):
        """Duplicate verse_id fails validation."""

    def test_backward_compatible_v10(self):
        """v1.0 manifest without format_version passes with defaults."""
```

#### Pack Indexer Tests (`tests/unit/test_pack_indexer.py`)

```python
class TestPackIndexer:
    def test_index_single_chapter(self):
        """Index correctly counts verses in single chapter."""

    def test_index_multi_chapter(self):
        """Index correctly handles multiple chapters."""

    def test_index_updates_manifest(self):
        """Indexer can update manifest.json in place."""

    def test_index_dry_run(self):
        """Dry run returns index without modifying files."""
```

#### Witness Support Tests (`tests/unit/test_witness_support.py`)

```python
class TestWitnessSupport:
    def test_witness_stored_with_source_pack(self):
        """Witness reading includes source_pack_id."""

    def test_witness_retrieved_with_pack(self):
        """Retrieved reading has source_pack_id populated."""

    def test_witness_summary_by_type(self):
        """get_witness_summary_by_type groups correctly."""

    def test_provenance_summary(self):
        """get_provenance_summary returns unique pack list."""
```

### 7.2 Integration Tests

#### Pack Installation Tests (`tests/integration/test_pack_install.py`)

```python
class TestPackInstallation:
    def test_install_v11_pack(self):
        """v1.1 pack installs via existing installer."""

    def test_sources_screen_shows_coverage(self):
        """GUI Sources screen shows pack coverage/index."""

    def test_multiple_packs_coexist(self):
        """Multiple comparative packs can be installed."""
```

#### Variant Build Tests (`tests/integration/test_variant_build_sprint8.py`)

```python
class TestVariantBuildSprint8:
    def test_build_with_multiple_editions(self):
        """Variants built from multiple comparative packs."""

    def test_witness_density_in_variant(self):
        """Built variant includes witness provenance."""

    def test_idempotent_with_packs(self):
        """Re-building with same packs is idempotent."""
```

#### Dossier Tests (`tests/integration/test_dossier.py`)

```python
class TestDossierExport:
    def test_dossier_cli_verse(self):
        """CLI exports dossier for single verse."""

    def test_dossier_cli_chapter(self):
        """CLI exports dossier for chapter scope."""

    def test_dossier_api_endpoint(self):
        """API endpoint returns valid dossier response."""

    def test_dossier_includes_witness_summaries(self):
        """Dossier includes witness type summaries."""

    def test_dossier_includes_provenance(self):
        """Dossier includes source pack provenance."""

    def test_dossier_with_session_ack_state(self):
        """Dossier reflects acknowledgement state for session."""
```

#### GUI Compile Check

```bash
cd gui && npm run type-check && npm run build
```

### 7.3 Full Suite

```bash
# All tests must pass
pytest tests/ -q --tb=short

# Lint clean
ruff check src/ tests/
ruff format --check src/ tests/
```

---

## 8. Acceptance Criteria

### 8.1 Pack Spec v1.1 (B1)

- [ ] `redletters packs validate data/packs/westcott-hort-john` passes
- [ ] `redletters packs validate` fails on invalid manifest with clear error
- [ ] `redletters packs index data/packs/westcott-hort-john` generates index
- [ ] Existing WH John pack loads with backward compatibility

### 8.2 Coverage Expansion (B2)

- [ ] Tischendorf Mark pack installed via `redletters sources install tischendorf-mark`
- [ ] Byzantine John pack installed via `redletters sources install byzantine-john`
- [ ] GUI Sources screen shows all 3 comparative packs
- [ ] Each pack has ≥45 verses (Mark 1) or ≥51 verses (John 1)

### 8.3 Witness-Aware Variants (B3)

- [ ] Built variant includes witness sigla per reading
- [ ] witness_type is "edition" for edition packs
- [ ] Reason classifier notes "supported by [witness type]" when appropriate
- [ ] Schema supports future manuscript packs without changes

### 8.4 Dossier Export (B4)

- [ ] `redletters variants dossier "John.1.18"` outputs valid JSON
- [ ] `GET /variants/dossier?reference=John.1.18` returns 200 with dossier
- [ ] Dossier shows spine reading marked as default
- [ ] Dossier shows witness summaries per reading
- [ ] Dossier shows provenance (which packs contributed)
- [ ] Dossier reflects ack state when session_id provided

### 8.5 GUI Dossier View (B5)

- [ ] Gate screen has "View Dossier" button/panel
- [ ] Dossier panel shows witness summary
- [ ] Dossier panel shows reason + significance
- [ ] Dossier panel shows source pack provenance
- [ ] Dossier panel does NOT bypass gate (informational only)

### 8.6 Non-Negotiables

- [ ] ADR-007: SBLGNT remains canonical spine + default
- [ ] ADR-008: Variants surfaced side-by-side; significant/major require ack
- [ ] ADR-009: Readable/traceable claim gating unchanged
- [ ] ADR-010: Layered confidence shown and explainable
- [ ] redletters.* warnings treated as errors
- [ ] GUI/CLI/API from Sprints 5-7 continue to work
- [ ] Full test suite passes

### 8.7 Definition of Done

A clean setup can:
1. Install spine + 2 open-license comparative packs
2. Build variants for a chapter
3. Translate a passage and see a gate
4. Open a dossier that explains:
   - What differs
   - Who supports what (witnesses)
   - Why this matters (reason classification)
5. Acknowledge (single or multi) and proceed
6. All tests pass; ruff clean; receipt written

---

## Appendix: File Changes Summary

### New Files
- `src/redletters/sources/pack_validator.py`
- `src/redletters/sources/pack_indexer.py`
- `src/redletters/cli/packs.py`
- `src/redletters/variants/dossier.py`
- `data/packs/tischendorf-mark/manifest.json`
- `data/packs/tischendorf-mark/Mark/chapter_01.tsv`
- `data/packs/byzantine-john/manifest.json`
- `data/packs/byzantine-john/John/chapter_01.tsv`
- `gui/src/components/DossierPanel.tsx`
- `tests/unit/test_pack_validator.py`
- `tests/unit/test_pack_indexer.py`
- `tests/unit/test_witness_support.py`
- `tests/integration/test_dossier.py`

### Modified Files
- `src/redletters/sources/pack_loader.py` (v1.1 fields)
- `src/redletters/variants/models.py` (source_pack_id)
- `src/redletters/variants/store.py` (schema migration)
- `src/redletters/variants/builder.py` (witness tracking)
- `src/redletters/api/models.py` (dossier models)
- `src/redletters/api/routes.py` (dossier endpoint)
- `sources_catalog.yaml` (new packs + v1.1 fields)
- `gui/src/api/types.ts` (dossier types)
- `gui/src/api/client.ts` (dossier method)
- `gui/src/screens/Gate.tsx` (dossier panel)

---

*MAP complete. Ready for implementation.*
