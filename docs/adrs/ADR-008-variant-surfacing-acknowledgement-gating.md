# ADR-008: Variant Surfacing & Acknowledgement Gating

**Status**: Accepted
**Date**: 2026-01-30
**Deciders**: Project maintainers
**Depends on**: ADR-007 (SBLGNT canonical spine)

## Context

Textual variants in the Greek New Testament represent real divergences in the manuscript tradition. Traditional translation workflows handle variants in three problematic ways:

1. **Footnote Graveyard**: Variants relegated to footnotes that 99% of readers ignore
2. **Silent Selection**: Translators choose a reading without surfacing the choice
3. **Apparatus Overload**: Full critical apparatus overwhelms non-specialists

For a forensic linguistics tool, none of these approaches is acceptable. The system must:

- Surface variants **at the point of dependency** (when a claim relies on the reading)
- Require **explicit acknowledgement** before allowing claims that depend on disputed text
- Support **side-by-side comparison** rather than primary/footnote hierarchy

## Decision

### Part 1: Variant Surfacing Model

Variants are represented as **VariantUnit** objects attached to token positions:

```python
class VariantUnit:
    ref: str                     # e.g., "John.1.18"
    position: int                # word position in verse
    readings: list[WitnessReading]
    sblgnt_reading_index: int    # which reading is SBLGNT default
    classification: VariantClassification  # SPELLING, WORD_ORDER, OMISSION, ADDITION, SUBSTITUTION
    significance: SignificanceLevel  # TRIVIAL, MINOR, SIGNIFICANT, MAJOR

class WitnessReading:
    surface_text: str
    witnesses: list[str]         # e.g., ["P66", "א", "B", "D"]
    date_range: tuple[int, int]  # earliest/latest witness century
    support_type: SupportType    # PAPYRI, UNCIAL, MINUSCULE, VERSION, FATHER
```

### Part 2: Acknowledgement Gating

When a user's workflow **depends on** a variant reading, the system triggers an **acknowledgement gate**:

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚠️  VARIANT DEPENDENCY DETECTED                                │
├─────────────────────────────────────────────────────────────────┤
│  Your interpretation depends on the reading at John 1:18        │
│                                                                 │
│  Reading A (SBLGNT): μονογενὴς θεός ("only-begotten God")      │
│    Witnesses: P66 P75 א B C* L                                  │
│                                                                 │
│  Reading B: ὁ μονογενὴς υἱός ("the only-begotten Son")         │
│    Witnesses: A C³ Θ Ψ f¹ f¹³ 33 Byz                            │
│                                                                 │
│  [  ] I acknowledge this variant affects my interpretation      │
│  [  ] Proceed with Reading A (SBLGNT default)                  │
│  [  ] Proceed with Reading B                                   │
│  [  ] View full apparatus                                       │
└─────────────────────────────────────────────────────────────────┘
```

### Gating Rules

| Trigger | Gate Required | Rationale |
|---------|---------------|-----------|
| Creating Type2+ claim on variant text | Yes | Interpretation depends on reading choice |
| Viewing readable mode | No | Default SBLGNT shown, variants available on-demand |
| Toggling to traceable mode | No | Variants automatically shown in traceable view |
| Exporting/sharing an interpretation | Yes | Recipients must know the textual basis |
| Querying a variant word's glosses | Soft warning | Glosses may differ by reading |

### Part 3: State Tracking

User acknowledgements are persisted per-session and optionally per-user:

```python
class AcknowledgementState:
    session_id: str
    acknowledged_variants: dict[str, VariantAck]  # ref -> ack record

class VariantAck:
    ref: str
    reading_chosen: int          # index of chosen reading
    timestamp: datetime
    context: str                 # what claim/action triggered the gate
```

## Consequences

### Positive

1. **No Hidden Choices**: Users cannot unknowingly build interpretations on disputed text
2. **Side-by-Side Default**: Variants presented as alternatives, not primary/footnote
3. **Audit Trail**: Acknowledgements recorded for traceability
4. **Graduated Disclosure**: Readable mode is clean; traceable mode shows everything

### Negative

1. **User Friction**: Gates interrupt workflow (intentionally)
2. **Complexity**: Requires variant database and UI components
3. **Incomplete Data**: Not all variants have manuscript witness data in open sources

### Mitigations

- **Friction by Design**: The interruption is the feature; it prevents unearned certainty
- **Progressive Loading**: Variant data loaded on-demand, not upfront
- **Open Sources**: Use CNTTS-style collation data and open apparatus where available

## Data Sources for Variants

| Source | License | Coverage | Notes |
|--------|---------|----------|-------|
| NA28 Apparatus | Restricted | ~5000 variation units | Cannot redistribute; manual entry only |
| SBLGNT Apparatus | CC-BY | ~540 places SBLGNT differs from NA28 | Available in SBLGNT edition |
| CNTTS Collations | Academic | Full NT | Requires institutional access |
| Open Greek NT Project | MIT | Partial | Community-driven collations |
| INTF NTVMR | Academic | Growing | Online, API available |

For MVP: Manually curate significant variants (~100 high-impact units) from open sources.

## Implementation

### Database Schema Addition

```sql
CREATE TABLE variant_units (
    id INTEGER PRIMARY KEY,
    ref TEXT NOT NULL,              -- e.g., "John.1.18"
    position INTEGER NOT NULL,
    classification TEXT NOT NULL,   -- SPELLING, WORD_ORDER, etc.
    significance TEXT NOT NULL,     -- TRIVIAL, MINOR, SIGNIFICANT, MAJOR
    sblgnt_reading_index INTEGER DEFAULT 0,
    source_id INTEGER REFERENCES sources(id),
    notes TEXT,
    UNIQUE(ref, position)
);

CREATE TABLE witness_readings (
    id INTEGER PRIMARY KEY,
    variant_unit_id INTEGER REFERENCES variant_units(id),
    reading_index INTEGER NOT NULL,
    surface_text TEXT NOT NULL,
    normalized_text TEXT,
    source_id INTEGER REFERENCES sources(id)
);

CREATE TABLE reading_witnesses (
    id INTEGER PRIMARY KEY,
    reading_id INTEGER REFERENCES witness_readings(id),
    witness_siglum TEXT NOT NULL,   -- e.g., "P66", "א", "B"
    witness_type TEXT NOT NULL,     -- PAPYRUS, UNCIAL, MINUSCULE, VERSION, FATHER
    century_earliest INTEGER,
    century_latest INTEGER,
    source_id INTEGER REFERENCES sources(id)
);

CREATE TABLE acknowledgements (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    variant_unit_id INTEGER REFERENCES variant_units(id),
    reading_chosen INTEGER NOT NULL,
    context TEXT,                   -- what triggered the gate
    timestamp TEXT NOT NULL,
    UNIQUE(session_id, variant_unit_id)
);
```

### UI Integration Points

1. **Readable View**: Token highlighting for words with significant variants
2. **Traceable View**: Inline variant panel with witness table
3. **Gate Modal**: Blocking dialog when creating claims on variant text
4. **Export Warning**: Summary of variant dependencies in exported content

## Alternatives Considered

### Alternative 1: Footnote-Style Variants

**Rejected because**: Replicates the traditional model that hides variants. Users can and do ignore footnotes.

### Alternative 2: Always Show All Variants

**Rejected because**: Information overload. Most variants are trivial (spelling, movable nu). Graduated disclosure is more usable.

### Alternative 3: Let Users Disable Gates

**Rejected because**: Undermines traceability. If interpretations can be built without acknowledging variants, the audit trail is incomplete. Power users can work in "research mode" but acknowledgements are still logged.

## References

- Metzger, Bruce M. *A Textual Commentary on the Greek New Testament*. 2nd ed. United Bible Societies, 1994.
- Wasserman, Tommy, and Peter J. Gurry. *A New Approach to Textual Criticism: An Introduction to the Coherence-Based Genealogical Method*. SBL Press, 2017.
- [INTF New Testament Virtual Manuscript Room](https://ntvmr.uni-muenster.de/)
