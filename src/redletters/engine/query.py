"""Scripture reference parsing and token retrieval."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass


@dataclass
class ScriptureRef:
    """Parsed scripture reference."""

    book: str
    chapter: int
    verse: int
    verse_end: int | None = None  # For ranges

    def __str__(self) -> str:
        if self.verse_end and self.verse_end != self.verse:
            return f"{self.book} {self.chapter}:{self.verse}-{self.verse_end}"
        return f"{self.book} {self.chapter}:{self.verse}"


# Book name normalization
BOOK_ALIASES = {
    "matt": "Matthew",
    "matthew": "Matthew",
    "mt": "Matthew",
    "mark": "Mark",
    "mk": "Mark",
    "luke": "Luke",
    "lk": "Luke",
    "john": "John",
    "jn": "John",
    "jhn": "John",
}


def normalize_book_name(name: str) -> str:
    """Normalize book name to canonical form."""
    key = name.lower().strip().replace(".", "")
    return BOOK_ALIASES.get(key, name.title())


def parse_reference(ref_string: str) -> ScriptureRef:
    """
    Parse a scripture reference string.

    Supported formats:
    - "Matthew 3:2"
    - "Matt 3:2"
    - "Mark 1:15-16"
    - "John 3:16"

    Args:
        ref_string: Reference string to parse

    Returns:
        ScriptureRef object

    Raises:
        ValueError: If reference cannot be parsed
    """
    # Pattern: Book Chapter:Verse(-VerseEnd)?
    pattern = r"^(\d?\s*[A-Za-z]+)\s*(\d+):(\d+)(?:-(\d+))?$"
    match = re.match(pattern, ref_string.strip())

    if not match:
        raise ValueError(f"Cannot parse reference: {ref_string}")

    book_raw, chapter_str, verse_str, verse_end_str = match.groups()

    book = normalize_book_name(book_raw)
    chapter = int(chapter_str)
    verse = int(verse_str)
    verse_end = int(verse_end_str) if verse_end_str else None

    return ScriptureRef(book=book, chapter=chapter, verse=verse, verse_end=verse_end)


def get_tokens_for_reference(
    conn: sqlite3.Connection, ref: ScriptureRef, red_letter_only: bool = False
) -> list[dict]:
    """
    Retrieve tokens for a scripture reference.

    Args:
        conn: Database connection
        ref: Parsed scripture reference
        red_letter_only: If True, only return tokens marked as red letter

    Returns:
        List of token dictionaries ordered by position
    """
    verse_end = ref.verse_end if ref.verse_end else ref.verse

    query = """
        SELECT id, book, chapter, verse, position, surface, lemma, morph, is_red_letter
        FROM tokens
        WHERE book = ? AND chapter = ? AND verse >= ? AND verse <= ?
    """
    params: list = [ref.book, ref.chapter, ref.verse, verse_end]

    if red_letter_only:
        query += " AND is_red_letter = 1"

    query += " ORDER BY verse, position"

    cursor = conn.execute(query, params)

    tokens = []
    for row in cursor:
        tokens.append(
            {
                "id": row["id"],
                "book": row["book"],
                "chapter": row["chapter"],
                "verse": row["verse"],
                "position": row["position"],
                "surface": row["surface"],
                "lemma": row["lemma"],
                "morph": row["morph"],
                "is_red_letter": bool(row["is_red_letter"]),
            }
        )

    return tokens
