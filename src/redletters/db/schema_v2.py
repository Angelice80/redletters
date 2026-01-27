"""Schema v2: Provenance-first data model.

This schema implements ADR-002, adding:
- sources table as provenance backbone
- source_id foreign keys on all data tables
- constraints table for first-class constraint objects
- lexicon_entries replacing lexeme_senses (inventory, not truth)
"""

SCHEMA_VERSION = 2

SCHEMA_SQL = """
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- sources: provenance backbone (anti-smuggling)
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    version TEXT NOT NULL,
    license TEXT NOT NULL,
    url TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    sha256 TEXT,
    notes TEXT
);

-- tokens: atomic Greek text units with full morphological analysis
CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY,
    ref TEXT NOT NULL,
    surface_text TEXT NOT NULL,
    word TEXT NOT NULL,
    normalized TEXT NOT NULL,
    lemma TEXT NOT NULL,
    pos TEXT NOT NULL,
    parse_code TEXT NOT NULL,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    UNIQUE(ref, source_id)
);

-- lexicon_entries: sense inventory (NOT authoritative meanings)
-- These are candidate partitions of usage, not definitions
CREATE TABLE IF NOT EXISTS lexicon_entries (
    id INTEGER PRIMARY KEY,
    lemma TEXT NOT NULL,
    sense_id TEXT NOT NULL,
    gloss TEXT NOT NULL,
    definition TEXT,
    domain TEXT,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    UNIQUE(lemma, sense_id, source_id)
);

-- constraints: first-class constraint objects that influence ranking
CREATE TABLE IF NOT EXISTS constraints (
    id INTEGER PRIMARY KEY,
    constraint_type TEXT NOT NULL,
    target_ref TEXT,
    target_lemma TEXT,
    payload TEXT NOT NULL,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    confidence REAL DEFAULT 1.0
);

-- speech_spans: red-letter boundaries with provenance
CREATE TABLE IF NOT EXISTS speech_spans (
    id INTEGER PRIMARY KEY,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse_start INTEGER NOT NULL,
    verse_end INTEGER NOT NULL,
    position_start INTEGER,
    position_end INTEGER,
    speaker TEXT DEFAULT 'Jesus',
    confidence REAL DEFAULT 1.0,
    source_id INTEGER REFERENCES sources(id)
);

-- collocations: word pair frequencies with provenance
CREATE TABLE IF NOT EXISTS collocations (
    id INTEGER PRIMARY KEY,
    lemma1 TEXT NOT NULL,
    lemma2 TEXT NOT NULL,
    frequency INTEGER DEFAULT 1,
    context_type TEXT,
    source_id INTEGER REFERENCES sources(id),
    UNIQUE(lemma1, lemma2, context_type, source_id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tokens_ref ON tokens(ref);
CREATE INDEX IF NOT EXISTS idx_tokens_lemma ON tokens(lemma);
CREATE INDEX IF NOT EXISTS idx_tokens_source ON tokens(source_id);
CREATE INDEX IF NOT EXISTS idx_lexicon_lemma ON lexicon_entries(lemma);
CREATE INDEX IF NOT EXISTS idx_lexicon_source ON lexicon_entries(source_id);
CREATE INDEX IF NOT EXISTS idx_constraints_type ON constraints(constraint_type);
CREATE INDEX IF NOT EXISTS idx_constraints_lemma ON constraints(target_lemma);
CREATE INDEX IF NOT EXISTS idx_spans_ref ON speech_spans(book, chapter);
"""


def init_schema_v2(conn) -> None:
    """Initialize v2 schema with provenance tracking."""
    conn.executescript(SCHEMA_SQL)
    conn.execute(
        "INSERT OR REPLACE INTO schema_meta (key, value) VALUES (?, ?)",
        ("version", str(SCHEMA_VERSION)),
    )
    conn.commit()


def get_schema_version(conn) -> int | None:
    """Get current schema version, or None if not initialized."""
    try:
        cursor = conn.execute("SELECT value FROM schema_meta WHERE key = 'version'")
        row = cursor.fetchone()
        return int(row[0]) if row else None
    except Exception:
        return None


def register_source(
    conn,
    name: str,
    version: str,
    license_: str,
    url: str,
    retrieved_at: str,
    sha256: str | None = None,
    notes: str | None = None,
) -> int:
    """
    Register a data source and return its ID.

    This is the provenance entry point - all data must trace to a source.
    """
    cursor = conn.execute(
        """
        INSERT INTO sources (name, version, license, url, retrieved_at, sha256, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            version = excluded.version,
            license = excluded.license,
            url = excluded.url,
            retrieved_at = excluded.retrieved_at,
            sha256 = excluded.sha256,
            notes = excluded.notes
        RETURNING id
        """,
        (name, version, license_, url, retrieved_at, sha256, notes),
    )
    return cursor.fetchone()[0]


def get_source_id(conn, name: str) -> int | None:
    """Get source ID by name, or None if not found."""
    cursor = conn.execute("SELECT id FROM sources WHERE name = ?", (name,))
    row = cursor.fetchone()
    return row[0] if row else None


def list_sources(conn) -> list[dict]:
    """List all registered sources with their metadata."""
    cursor = conn.execute(
        """
        SELECT id, name, version, license, url, retrieved_at, sha256, notes
        FROM sources
        ORDER BY name
        """
    )
    return [
        {
            "id": row[0],
            "name": row[1],
            "version": row[2],
            "license": row[3],
            "url": row[4],
            "retrieved_at": row[5],
            "sha256": row[6],
            "notes": row[7],
        }
        for row in cursor
    ]
