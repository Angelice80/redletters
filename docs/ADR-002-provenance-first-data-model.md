# ADR-002: Provenance-First Data Model for Real Data Integration

**Status**: Accepted
**Date**: 2026-01-27
**Context**: Phase 2 - Real Data Integration

---

## Context

Phase 2 requires ingesting real Greek NT data from external sources:
- **MorphGNT SBLGNT** (text + morphology)
- **UBS Dictionary** (Louw-Nida derived sense inventory)
- **Strong's Greek Dictionary** (sense inventory)

The project's Epistemic Constitution demands:
1. No hidden theology through dependency injection
2. Every interpretive choice must be traceable
3. Dependencies are authorities — they must be explicit

## Decision

### 1. Sources Table as Provenance Backbone

Every piece of external data links to a `sources` record:

```sql
CREATE TABLE sources (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,      -- e.g., "MorphGNT-SBLGNT"
    version TEXT NOT NULL,          -- e.g., "6.12"
    license TEXT NOT NULL,          -- e.g., "CC-BY-SA-3.0"
    url TEXT NOT NULL,              -- canonical download URL
    retrieved_at TEXT NOT NULL,     -- ISO 8601 timestamp
    sha256 TEXT,                    -- hash of downloaded artifact
    notes TEXT                      -- any caveats or constraints
);
```

### 2. No Bundled Data

Data is **fetched at install time**, not committed to the repository.

**Rationale**:
- Avoids license composition issues (CC BY + CC BY-SA mixing)
- Forces users to accept licenses explicitly
- Prevents "stealth theology" via frozen snapshots
- Keeps repo clean and auditable

### 3. Tokens with Source Tracking

```sql
CREATE TABLE tokens (
    id INTEGER PRIMARY KEY,
    ref TEXT NOT NULL,              -- "Matt.3.2.1" (book.chapter.verse.position)
    surface_text TEXT NOT NULL,     -- with punctuation
    word TEXT NOT NULL,             -- stripped
    normalized TEXT NOT NULL,       -- normalized form
    lemma TEXT NOT NULL,
    pos TEXT NOT NULL,              -- part of speech code
    parse_code TEXT NOT NULL,       -- raw 8-char morphology
    source_id INTEGER NOT NULL REFERENCES sources(id),
    UNIQUE(ref, source_id)
);
```

### 4. Senses as Constraint Inventory (Not Truth)

Lexicon entries are **candidate partitions of usage**, not authoritative meanings:

```sql
CREATE TABLE lexicon_entries (
    id INTEGER PRIMARY KEY,
    lemma TEXT NOT NULL,
    sense_id TEXT NOT NULL,         -- e.g., "metanoeo.1"
    gloss TEXT NOT NULL,            -- short translation
    definition TEXT,                -- fuller explanation
    domain TEXT,                    -- semantic domain (if available)
    source_id INTEGER NOT NULL REFERENCES sources(id),
    UNIQUE(lemma, sense_id, source_id)
);
```

**Critical**: These are inventory items, not meanings. The system should treat them as:
- "Here are the buckets this source uses"
- "Here is how often this lemma appears in contexts resembling bucket X"
- "Here's what would have to be true to privilege bucket X here"

### 5. Constraints as First-Class Objects

Constraints influence ranking without collapsing meaning:

```sql
CREATE TABLE constraints (
    id INTEGER PRIMARY KEY,
    constraint_type TEXT NOT NULL,  -- morphology|syntax|collocation|lexicon-sense|witness
    target_ref TEXT,                -- which token(s) this applies to
    target_lemma TEXT,              -- which lemma(s) this applies to
    payload TEXT NOT NULL,          -- JSON blob with constraint details
    source_id INTEGER NOT NULL REFERENCES sources(id),
    confidence REAL DEFAULT 1.0
);
```

### 6. License Provenance Command

`redletters licenses` prints:
- Every source name, license, version
- SHA256 hashes
- Retrieval timestamps
- Any propagation requirements (e.g., BY-SA obligations)

---

## License Inventory (Current)

| Source | License | Share-Alike? | Attribution Required? |
|--------|---------|--------------|----------------------|
| SBLGNT text | CC BY 4.0 | No | Yes |
| MorphGNT morphology | CC BY-SA 3.0 | Yes | Yes |
| UBS Dictionary | CC BY-SA 4.0 | Yes | Yes |
| Strong's Greek | CC0 | No | No (but courteous) |

**Implication**: If distributing a compiled database mixing these sources, the artifact may need to be released under CC BY-SA terms due to share-alike propagation.

**Mitigation**: Don't bundle. Fetch at install. Generate NOTICE automatically.

---

## Consequences

### Positive
- Complete audit trail for every piece of data
- No hidden theology via frozen lexicon choices
- License obligations explicit and manageable
- Aligns with Epistemic Constitution

### Negative
- Requires network access on first run
- Slightly more complex ingestion pipeline
- Users must understand provenance model

### Neutral
- Demo data remains for offline testing
- Migration path from current schema needed

---

## Implementation Notes

1. **Schema version tracking**: Add a `schema_version` table
2. **Migration strategy**: Keep demo data loader, add real data loader
3. **CLI commands**:
   - `redletters data fetch` — download sources
   - `redletters data load` — parse and load
   - `redletters licenses` — show provenance report
