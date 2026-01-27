# ADR-001: Core Architecture for Red Letters Source Reader

**Status**: Accepted
**Date**: 2026-01-26
**Decision Makers**: Initial development team

---

## Context

We need to build a Greek New Testament reading tool that:
1. Generates multiple plausible English renderings (not a single "authoritative" translation)
2. Provides transparent "receipts" for every translation choice
3. Avoids embedding theological bias in the core engine
4. Remains extensible for future data sources (variants, Syriac witnesses)

## Decision Drivers

- **Transparency**: Users must understand WHY each rendering was chosen
- **Reproducibility**: Same input must produce same output (no ML randomness)
- **Simplicity**: MVP must run without external licensed data
- **Extensibility**: Architecture must support future plugins without core rewrites
- **Academic credibility**: Receipts must cite lexical sources (BDAG, LSJ, Louw-Nida)

---

## Decisions Made

### Decision 1: Multi-Rendering Output (Not Single Translation)

**Choice**: Always output 3-5 candidate renderings per passage

**Rationale**:
- Single translations hide interpretive decisions
- Multiple readings expose ambiguity inherent in translation
- Users can compare approaches and make informed choices

**Alternatives Considered**:
- Single "best" translation with footnotes — rejected (hides primary ambiguity)
- User-selected single style — rejected (loses comparative value)

---

### Decision 2: Deterministic Ranking Heuristic

**Choice**: Use weighted formula instead of ML model

```
score = (morph_fit × 0.40) + (sense_weight × 0.35) + (collocation × 0.15) - (uncommon_penalty × 0.10)
```

**Rationale**:
- Fully explainable — users can understand why rankings differ
- Reproducible — same input always produces same output
- No training data required — works with demo corpus
- Weights are tunable without retraining

**Alternatives Considered**:
- Neural translation model — rejected (black box, requires training data)
- Pure lexicon frequency — rejected (ignores context)
- User voting/feedback — rejected (introduces bias, requires users)

---

### Decision 3: SQLite for Data Storage

**Choice**: SQLite with file-based storage

**Rationale**:
- Zero configuration — no database server required
- Single file — easy backup and distribution
- Sufficient performance for demo corpus (< 100K tokens)
- Easy migration path to PostgreSQL if needed

**Alternatives Considered**:
- PostgreSQL — rejected (overkill for MVP, deployment complexity)
- In-memory only — rejected (no persistence between sessions)
- JSON files — rejected (slower queries, no indexing)

---

### Decision 4: Plugin Architecture for Extensibility

**Choice**: Protocol-based plugin interfaces for sense providers, variants, witnesses

**Rationale**:
- Core engine remains stable while data sources change
- Different lexica can be swapped without code changes
- Future Syriac support doesn't require core rewrites
- Testing with mock providers is straightforward

**Plugin Interfaces**:
```python
class SenseProvider(Protocol):
    def get_senses(self, lemma: str) -> list[LexemeSense]: ...

class VariantProvider(Protocol):
    def get_variants(self, book: str, chapter: int, verse: int) -> list[TextualVariant]: ...

class WitnessOverlay(Protocol):
    def get_parallel(self, book: str, chapter: int, verse: int) -> WitnessReading | None: ...
```

**Alternatives Considered**:
- Hardcoded data sources — rejected (not extensible)
- Configuration-based switching — rejected (less flexible than plugins)
- Microservices — rejected (overkill for MVP)

---

### Decision 5: Four Rendering Styles

**Choice**: Implement four distinct rendering philosophies

| Style | Philosophy |
|-------|------------|
| `ultra-literal` | Preserve Greek form, word order, morphology markers |
| `natural` | Idiomatic English with minimal interpretation |
| `meaning-first` | Prioritize semantic clarity over form |
| `jewish-context` | Socio-historical framing (avoid anachronistic theology) |

**Rationale**:
- Covers major translation philosophy spectrum
- Each serves different user needs (study vs. reading vs. historical)
- Jewish-context addresses the "hidden theology" concern directly

**Alternatives Considered**:
- Single configurable style — rejected (loses comparative value)
- More styles (10+) — rejected (diminishing returns, complexity)
- User-defined styles — rejected (too complex for MVP)

---

### Decision 6: Receipts as First-Class Output

**Choice**: Every token rendering includes full interpretive receipt

**Receipt Structure**:
```json
{
  "surface": "μετανοεῖτε",
  "lemma": "μετανοέω",
  "morph": {"force": "command", "aspect": "ongoing"},
  "chosen_sense_id": "metanoeo.1",
  "chosen_gloss": "change one's mind",
  "sense_source": "BDAG",
  "sense_weight": 0.8,
  "rationale": "Selected based on cognitive domain preference...",
  "ambiguity_type": "lexical_polysemy",
  "alternate_glosses": ["repent", "turn around"]
}
```

**Rationale**:
- Core differentiator from existing translation tools
- Enables academic citation and verification
- Makes bias visible and challengeable
- Supports future UI features (receipt exploration)

**Alternatives Considered**:
- Footnotes only — rejected (not machine-readable)
- Separate receipt API — rejected (splits related data)
- Optional receipts — rejected (undermines transparency goal)

---

### Decision 7: CLI-First with API-Ready Architecture

**Choice**: Build CLI first, expose same logic via FastAPI

**Rationale**:
- Faster iteration without frontend complexity
- API enables future web UI without rewrites
- CLI useful for scripting and batch processing
- Rich library provides beautiful terminal output

**Alternatives Considered**:
- Web-first — rejected (slower iteration, more dependencies)
- API-only — rejected (harder to test interactively)
- Desktop app — rejected (distribution complexity)

---

## Consequences

### Positive
- Transparent, explainable translation system
- Easy to extend with new data sources
- Runs standalone without external services
- Academic credibility through source citations

### Negative
- Multiple renderings may confuse casual users
- SQLite limits concurrent write access
- Demo data is not representative of full NT
- Plugin system adds abstraction overhead

### Risks
- Real lexicon data may have licensing restrictions
- Ranking weights may need tuning with real data
- Performance untested at full NT scale

---

## Related Documents

- [BMAD-SPEC.md](./BMAD-SPEC.md) — Full project specification
- [PROGRESS.md](./PROGRESS.md) — Development log
- [API.md](./API.md) — API reference
