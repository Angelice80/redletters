"""SQLite connection management."""

import sqlite3
import unicodedata
from pathlib import Path


def normalize_greek(text: str) -> str:
    """
    Normalize Greek text to NFC form.

    This ensures consistent Unicode representation for lemma lookups,
    preventing mismatches between composed and decomposed forms.

    Args:
        text: Greek text (lemma, surface form, etc.)

    Returns:
        NFC-normalized text
    """
    return unicodedata.normalize("NFC", text)


def get_connection(db_path: Path) -> sqlite3.Connection:
    """
    Get a SQLite connection with row factory and WAL mode.

    WAL (Write-Ahead Logging) mode enables concurrent reads during writes,
    preventing data corruption under concurrent access.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Initialize database schema."""
    conn.executescript("""
        -- tokens: atomic Greek text units with morphological analysis
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            position INTEGER NOT NULL,
            surface TEXT NOT NULL,
            lemma TEXT NOT NULL,
            morph TEXT NOT NULL,
            is_red_letter BOOLEAN DEFAULT FALSE,
            UNIQUE(book, chapter, verse, position)
        );

        -- lexeme_senses: possible meanings for each lemma
        CREATE TABLE IF NOT EXISTS lexeme_senses (
            id INTEGER PRIMARY KEY,
            lemma TEXT NOT NULL,
            sense_id TEXT NOT NULL,
            gloss TEXT NOT NULL,
            definition TEXT,
            source TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            domain TEXT,
            UNIQUE(lemma, sense_id)
        );

        -- speech_spans: red-letter boundaries
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
            source TEXT
        );

        -- collocations: word pair frequencies
        CREATE TABLE IF NOT EXISTS collocations (
            id INTEGER PRIMARY KEY,
            lemma1 TEXT NOT NULL,
            lemma2 TEXT NOT NULL,
            frequency INTEGER DEFAULT 1,
            context_type TEXT,
            UNIQUE(lemma1, lemma2, context_type)
        );

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_tokens_ref ON tokens(book, chapter, verse);
        CREATE INDEX IF NOT EXISTS idx_tokens_lemma ON tokens(lemma);
        CREATE INDEX IF NOT EXISTS idx_senses_lemma ON lexeme_senses(lemma);
        CREATE INDEX IF NOT EXISTS idx_spans_ref ON speech_spans(book, chapter);
    """)
    conn.commit()
