# BMAD Specification: Red Letters Source Reader

> **BMAD-Method**: Blueprint → Map → Assemble → Debug
> **Version**: 1.0.0
> **Date**: 2026-01-26
> **Status**: MVP Complete

---

## 1) BLUEPRINT

### Problem Statement

Build a transparent, multi-reading Greek New Testament tool that generates **3-5 plausible renderings** for Jesus' sayings with explicit interpretive receipts — no hidden theology.

### Goal Summary

- **Primary**: Generate 3-5 plausible English renderings for any Greek NT "red letter" (Jesus' speech) passage
- **Transparency**: Every rendering includes traceable "receipts" — lemma, morphology, sense selection rationale
- **No Hidden Theology**: Core engine is linguistically driven; theological commentary is plugin-only with clear provenance
- **Greek-First**: All processing starts from Greek witnesses; Syriac hooks are architected but not implemented in MVP
- **Simplicity + Depth**: Minimal dependencies, maximal transparency through modularity
- **Extensibility**: Plugin interfaces for sense providers, variant readings, and witness overlays
- **Reproducibility**: Deterministic ranking heuristic (no ML black boxes)
- **Self-Contained MVP**: Runs with hardcoded demo data (no external corpus licensing)

### Non-Negotiables

1. Do NOT output a single "authoritative" translation — always output 3-5 candidate renderings per unit
2. Every rendering must include traceable "receipts" section: lemma, morphology, key ambiguity points, and why a choice was made
3. Keep theology/sermonizing out of the core engine — commentary must be optional plugin layer with clear provenance
4. Assume Greek-first (extant witnesses are Greek) — provide hooks for Syriac witness overlay later
5. Build for simplicity first; preserve depth via transparency and modularity

### Inputs / Outputs

| Input | Output |
|-------|--------|
| Scripture reference (e.g., "Matthew 3:2") | JSON with 3-5 candidate renderings + receipts |
| Optional: rendering style filter | Filtered subset of renderings |
| Optional: token position range | Partial verse analysis |

### "Plausible Readings" — Operational Definition

A **plausible reading** is a rendering that:

1. **Morphologically valid**: Respects case, number, tense, voice, mood constraints
2. **Lexically attested**: Uses senses documented in standard lexica (with source citation)
3. **Syntactically coherent**: Word order produces parseable English
4. **Ranked by confidence**: Score = `(morph_fit × sense_weight × collocation_bonus) - uncommon_penalty`

**Ambiguity Handling**:
- When multiple senses have similar weights → include all in output with explicit "ambiguity_type" tag
- When morphology is ambiguous (e.g., middle/passive) → generate renderings for each parse
- Receipts must flag every decision point

### Acceptance Tests (MVP)

| Test ID | Criterion | Status |
|---------|-----------|--------|
| AT-01 | Query "Matthew 3:2" returns valid JSON with 3-5 renderings | ✓ Pass |
| AT-02 | Each rendering has complete receipts (lemma, morph, sense, rationale) | ✓ Pass |
| AT-03 | Renderings include: ultra-literal, natural, meaning-first, jewish-context | ✓ Pass |
| AT-04 | No rendering contains unmarked theological commentary | ✓ Pass |
| AT-05 | Ranking scores are deterministic (same input → same output) | ✓ Pass |
| AT-06 | System runs with zero external dependencies beyond Python stdlib + FastAPI | ✓ Pass |
| AT-07 | CLI command `python -m redletters query "Mark 1:15"` returns valid output | ✓ Pass |
| AT-08 | Plugin interface allows custom sense provider injection | ✓ Pass |

---

## 2) MAP

### Stack Selection

| Component | Choice | Justification |
|-----------|--------|---------------|
| Language | Python 3.11 | Type hints, pattern matching, broad NLP ecosystem |
| API Framework | FastAPI | Async, auto-docs, Pydantic validation |
| Database | SQLite | Zero-config, file-based, easy migration path |
| CLI | Click + Rich | Beautiful terminal output, minimal boilerplate |
| UI | CLI-first (API-ready) | Faster iteration, no JS build complexity |

### Database Schema

```sql
-- tokens: atomic Greek text units with morphological analysis
CREATE TABLE tokens (
    id INTEGER PRIMARY KEY,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    position INTEGER NOT NULL,
    surface TEXT NOT NULL,        -- Greek surface form (Unicode)
    lemma TEXT NOT NULL,          -- dictionary form
    morph TEXT NOT NULL,          -- morphology code (e.g., "V-PAI-3S")
    is_red_letter BOOLEAN DEFAULT FALSE,
    UNIQUE(book, chapter, verse, position)
);

-- lexeme_senses: possible meanings for each lemma
CREATE TABLE lexeme_senses (
    id INTEGER PRIMARY KEY,
    lemma TEXT NOT NULL,
    sense_id TEXT NOT NULL,       -- e.g., "metanoeo.1"
    gloss TEXT NOT NULL,          -- English gloss
    definition TEXT,              -- fuller definition
    source TEXT NOT NULL,         -- provenance: "BDAG", "LSJ", "Louw-Nida"
    weight REAL DEFAULT 1.0,      -- default frequency weight
    domain TEXT,                  -- semantic domain tag
    UNIQUE(lemma, sense_id)
);

-- speech_spans: red-letter boundaries
CREATE TABLE speech_spans (
    id INTEGER PRIMARY KEY,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse_start INTEGER NOT NULL,
    verse_end INTEGER NOT NULL,
    speaker TEXT DEFAULT 'Jesus',
    confidence REAL DEFAULT 1.0,
    source TEXT
);

-- collocations: word pair frequencies for context hints
CREATE TABLE collocations (
    id INTEGER PRIMARY KEY,
    lemma1 TEXT NOT NULL,
    lemma2 TEXT NOT NULL,
    frequency INTEGER DEFAULT 1,
    context_type TEXT,
    UNIQUE(lemma1, lemma2, context_type)
);
```

### Module Architecture

```
redletters/
├── __init__.py
├── __main__.py              # CLI entry point
├── config.py                # Settings, morphology mappings
│
├── ingest/                  # Data loading & normalization
│   ├── loader.py            # Load demo data into DB
│   ├── morphology.py        # Parse morphology codes
│   └── demo_data.py         # Hardcoded demo corpus
│
├── engine/                  # Core rendering logic
│   ├── query.py             # Reference parsing & token retrieval
│   ├── senses.py            # Sense lookup & disambiguation
│   ├── generator.py         # Candidate rendering generator
│   ├── ranker.py            # Deterministic ranking heuristic
│   └── receipts.py          # Receipt generation
│
├── api/                     # HTTP interface
│   ├── main.py              # FastAPI app
│   ├── routes.py            # Endpoints
│   └── models.py            # Pydantic schemas
│
├── plugins/                 # Extension interfaces
│   ├── base.py              # Abstract plugin classes
│   ├── sense_provider.py    # Sense provider interface
│   ├── variant_provider.py  # Variant readings (stub)
│   └── witness_overlay.py   # Syriac overlay (stub)
│
└── db/                      # Database utilities
    ├── connection.py        # SQLite connection
    └── schema.py            # Schema creation
```

### Plugin Interfaces

```python
# Sense Provider Interface
class SenseProvider(Protocol):
    def get_senses(self, lemma: str) -> list[LexemeSense]: ...
    def get_sense_weight(self, lemma: str, sense_id: str, context: TokenContext) -> float: ...
    @property
    def source_name(self) -> str: ...

# Variant Provider Interface (Future)
class VariantProvider(Protocol):
    def get_variants(self, book: str, chapter: int, verse: int) -> list[TextualVariant]: ...
    def get_variant_weight(self, variant_id: str) -> float: ...

# Witness Overlay Interface (Future)
class WitnessOverlay(Protocol):
    def get_parallel(self, book: str, chapter: int, verse: int) -> WitnessReading | None: ...
    @property
    def tradition_name(self) -> str: ...
```

---

## 3) ASSEMBLE

### Implementation Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Project scaffold (pyproject.toml, README, directories) | ✓ Complete |
| 2 | Database schema + demo data loader | ✓ Complete |
| 3 | Core engine (query → senses → generator → ranker) | ✓ Complete |
| 4 | CLI interface | ✓ Complete |
| 5 | FastAPI endpoints | ✓ Complete |
| 6 | Test suite | ✓ Complete (30 tests) |

### Rendering Styles Implemented

| Style | Description | Sense Domain Preferences |
|-------|-------------|-------------------------|
| `ultra-literal` | Word-for-word, Greek word order, hyphenated compounds | etymological, spatial, temporal |
| `natural` | Idiomatic English word order | general, cognitive, behavioral |
| `meaning-first` | Prioritizes semantic clarity over form | cognitive, relational, behavioral |
| `jewish-context` | Socio-historical Jewish framing | socio-religious, circumlocution, religious |

### Ranking Heuristic

```
score = (morph_fit × 0.40) + (sense_weight × 0.35) + (collocation_bonus × 0.15) - (uncommon_penalty × 0.10)
```

| Factor | Weight | Description |
|--------|--------|-------------|
| morph_fit | 0.40 | 1.0 if morphology respected, 0.8 if ambiguous |
| sense_weight | 0.35 | Lexicon-assigned frequency weight |
| collocation_bonus | 0.15 | Boost for common word pairings |
| uncommon_penalty | 0.10 | Penalty for low-frequency sense selections |

### Demo Data Coverage

- **Matthew 3:2** — "Repent, for the kingdom of heaven has drawn near" (7 tokens)
- **Matthew 4:17** — Same saying, different context (7 tokens)
- **Mark 1:15** — "The time is fulfilled..." (15 tokens)
- **Matthew 5:3** — First Beatitude (12 tokens)
- **Matthew 6:9-10** — Lord's Prayer opening (14 tokens)

---

## 4) DEBUG

### Top 10 Failure Modes & Mitigations

| # | Failure Mode | Impact | Mitigation | Status |
|---|--------------|--------|------------|--------|
| 1 | Lemma not in lexicon | Unknown words render as `[lemma]` | Fallback sense with "unknown" flag | ✓ Implemented |
| 2 | Morphology parse failure | Constraints not applied | Graceful degradation, flag as unparsed | ✓ Implemented |
| 3 | Reference format unrecognized | Query fails | Comprehensive regex + helpful error | ✓ Implemented |
| 4 | Database file missing | All queries fail | Check on startup, `init` command | ✓ Implemented |
| 5 | Token order corruption | Nonsensical output | Position-based ordering, validation | ✓ Implemented |
| 6 | Collocation data sparse | Weak contextual scoring | Fallback to base weights | ✓ Implemented |
| 7 | Style transformer malformed | Garbled output | Post-processing cleanup | ✓ Implemented |
| 8 | Score calculation overflow | NaN/Inf scores | Bounded arithmetic | ✓ Implemented |
| 9 | Unicode normalization mismatch | Lemma lookups fail | NFC normalization | ✓ Implemented |
| 10 | Concurrent DB writes | Data corruption | SQLite WAL mode | ✓ Implemented |

### Test Coverage

| Test File | Tests | Status |
|-----------|-------|--------|
| test_query.py | 8 | ✓ All passing |
| test_generator.py | 5 | ✓ All passing |
| test_ranker.py | 5 | ✓ All passing |
| test_receipts.py | 4 | ✓ All passing |
| test_connection.py | 8 | ✓ All passing |
| **Total** | **30** | **✓ All passing** |

### Example Output: Matthew 3:2

```json
{
  "reference": "Matthew 3:2",
  "greek_text": "μετανοεῖτε ἤγγικεν γὰρ ἡ βασιλεία τῶν οὐρανῶν",
  "renderings": [
    {
      "style": "ultra-literal",
      "text": "Change-your-minds! Has-drawn-near for the kingdom of-the heavens.",
      "score": 0.847,
      "receipts": [
        {
          "surface": "μετανοεῖτε",
          "lemma": "μετανοέω",
          "chosen_gloss": "Change-your-minds!",
          "sense_source": "LSJ",
          "rationale": "Selected 'think differently afterward' (weight=0.40); domain: etymological; style: preserving Greek form/order",
          "ambiguity_type": "lexical_polysemy",
          "alternate_glosses": ["change one's mind", "repent", "turn around"]
        }
      ]
    }
  ]
}
```

---

## Future Roadmap

### Phase 2: Real Data Integration
- [ ] SBLGNT/MorphGNT ingestion pipeline
- [ ] BDAG/Louw-Nida sense database import
- [ ] Full NT token coverage

### Phase 3: Variant Support
- [ ] Implement VariantProvider with NA28 apparatus
- [ ] Variant-aware rendering (show alternate readings)
- [ ] Manuscript witness confidence weighting

### Phase 4: Syriac Overlay
- [ ] Peshitta text database
- [ ] Syriac-Greek alignment
- [ ] Retroversion mappings

### Phase 5: UI
- [ ] React/Next.js frontend
- [ ] Side-by-side rendering comparison
- [ ] Interactive receipt exploration
