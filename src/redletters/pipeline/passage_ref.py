"""Passage reference parsing for human-readable scripture references.

This module provides robust parsing of human scripture references into
canonical verse_ids for the pipeline.

Supported formats:
- Single verse: "John 1:18", "Jn 1:18"
- Hyphen range: "John 1:18-19"
- En-dash range: "John 1:18–19"
- Comma list: "John 1:18,19"
- Combined: "John 1:18-19,21" (range + comma)

Output: Ordered list of canonical verse_ids like ["John.1.18", "John.1.19"]

Error messages are actionable and specific.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# ============================================================================
# Book Name Normalization
# ============================================================================

# Canonical book names (27 NT books in order)
NT_BOOKS = [
    "Matthew",
    "Mark",
    "Luke",
    "John",
    "Acts",
    "Romans",
    "1Corinthians",
    "2Corinthians",
    "Galatians",
    "Ephesians",
    "Philippians",
    "Colossians",
    "1Thessalonians",
    "2Thessalonians",
    "1Timothy",
    "2Timothy",
    "Titus",
    "Philemon",
    "Hebrews",
    "James",
    "1Peter",
    "2Peter",
    "1John",
    "2John",
    "3John",
    "Jude",
    "Revelation",
]

# Comprehensive alias mapping (lowercase key -> canonical name)
# Covers common abbreviations from various traditions
BOOK_ALIASES: dict[str, str] = {
    # Matthew
    "matthew": "Matthew",
    "matt": "Matthew",
    "mat": "Matthew",
    "mt": "Matthew",
    # Mark
    "mark": "Mark",
    "mk": "Mark",
    "mr": "Mark",
    # Luke
    "luke": "Luke",
    "lk": "Luke",
    "luk": "Luke",
    # John (Gospel)
    "john": "John",
    "jn": "John",
    "jhn": "John",
    "joh": "John",
    # Acts
    "acts": "Acts",
    "ac": "Acts",
    "act": "Acts",
    # Romans
    "romans": "Romans",
    "rom": "Romans",
    "rm": "Romans",
    "ro": "Romans",
    # 1 Corinthians
    "1corinthians": "1Corinthians",
    "1cor": "1Corinthians",
    "1co": "1Corinthians",
    "icor": "1Corinthians",
    "i cor": "1Corinthians",
    "1 corinthians": "1Corinthians",
    "1 cor": "1Corinthians",
    # 2 Corinthians
    "2corinthians": "2Corinthians",
    "2cor": "2Corinthians",
    "2co": "2Corinthians",
    "iicor": "2Corinthians",
    "ii cor": "2Corinthians",
    "2 corinthians": "2Corinthians",
    "2 cor": "2Corinthians",
    # Galatians
    "galatians": "Galatians",
    "gal": "Galatians",
    "ga": "Galatians",
    # Ephesians
    "ephesians": "Ephesians",
    "eph": "Ephesians",
    "ep": "Ephesians",
    # Philippians
    "philippians": "Philippians",
    "phil": "Philippians",
    "php": "Philippians",
    "pp": "Philippians",
    # Colossians
    "colossians": "Colossians",
    "col": "Colossians",
    "co": "Colossians",
    # 1 Thessalonians
    "1thessalonians": "1Thessalonians",
    "1thess": "1Thessalonians",
    "1th": "1Thessalonians",
    "1 thessalonians": "1Thessalonians",
    "1 thess": "1Thessalonians",
    "i thess": "1Thessalonians",
    # 2 Thessalonians
    "2thessalonians": "2Thessalonians",
    "2thess": "2Thessalonians",
    "2th": "2Thessalonians",
    "2 thessalonians": "2Thessalonians",
    "2 thess": "2Thessalonians",
    "ii thess": "2Thessalonians",
    # 1 Timothy
    "1timothy": "1Timothy",
    "1tim": "1Timothy",
    "1ti": "1Timothy",
    "1 timothy": "1Timothy",
    "1 tim": "1Timothy",
    "i tim": "1Timothy",
    # 2 Timothy
    "2timothy": "2Timothy",
    "2tim": "2Timothy",
    "2ti": "2Timothy",
    "2 timothy": "2Timothy",
    "2 tim": "2Timothy",
    "ii tim": "2Timothy",
    # Titus
    "titus": "Titus",
    "tit": "Titus",
    "ti": "Titus",
    # Philemon
    "philemon": "Philemon",
    "phlm": "Philemon",
    "phm": "Philemon",
    "philem": "Philemon",
    # Hebrews
    "hebrews": "Hebrews",
    "heb": "Hebrews",
    "he": "Hebrews",
    # James
    "james": "James",
    "jas": "James",
    "jm": "James",
    "jam": "James",
    # 1 Peter
    "1peter": "1Peter",
    "1pet": "1Peter",
    "1pe": "1Peter",
    "1pt": "1Peter",
    "1 peter": "1Peter",
    "1 pet": "1Peter",
    "i pet": "1Peter",
    # 2 Peter
    "2peter": "2Peter",
    "2pet": "2Peter",
    "2pe": "2Peter",
    "2pt": "2Peter",
    "2 peter": "2Peter",
    "2 pet": "2Peter",
    "ii pet": "2Peter",
    # 1 John (Epistle)
    "1john": "1John",
    "1jn": "1John",
    "1jhn": "1John",
    "1 john": "1John",
    "1 jn": "1John",
    "i jn": "1John",
    "i john": "1John",
    # 2 John
    "2john": "2John",
    "2jn": "2John",
    "2jhn": "2John",
    "2 john": "2John",
    "2 jn": "2John",
    "ii jn": "2John",
    "ii john": "2John",
    # 3 John
    "3john": "3John",
    "3jn": "3John",
    "3jhn": "3John",
    "3 john": "3John",
    "3 jn": "3John",
    "iii jn": "3John",
    "iii john": "3John",
    # Jude
    "jude": "Jude",
    "jud": "Jude",
    "jd": "Jude",
    # Revelation
    "revelation": "Revelation",
    "rev": "Revelation",
    "re": "Revelation",
    "rv": "Revelation",
    "apocalypse": "Revelation",
    "apoc": "Revelation",
}


@dataclass
class ParsedPassageRef:
    """Result of parsing a passage reference."""

    book: str
    chapter: int
    verse_ids: list[str]  # Canonical verse_ids in order
    input_ref: str  # Original input string
    normalized_ref: str  # Canonical form like "John 1:18-19"

    def __str__(self) -> str:
        return self.normalized_ref


class PassageRefError(ValueError):
    """Error parsing a passage reference with actionable message."""

    pass


def normalize_book_name(name: str) -> str:
    """Normalize a book name to canonical form.

    Args:
        name: Book name or abbreviation (e.g., "John", "Jn", "1 Cor")

    Returns:
        Canonical book name (e.g., "John", "1Corinthians")

    Raises:
        PassageRefError: If book name is not recognized
    """
    # Clean up the input
    cleaned = name.strip().replace(".", "")

    # Try direct lookup (lowercase)
    key = cleaned.lower()
    if key in BOOK_ALIASES:
        return BOOK_ALIASES[key]

    # Try with spaces removed
    key_no_space = key.replace(" ", "")
    if key_no_space in BOOK_ALIASES:
        return BOOK_ALIASES[key_no_space]

    # Try title case for canonical names
    title_cased = cleaned.title()
    if title_cased in NT_BOOKS:
        return title_cased

    # Not found - provide helpful error
    # Find close matches for suggestion
    suggestions = _find_similar_books(cleaned)
    suggestion_text = ""
    if suggestions:
        suggestion_text = f" Did you mean: {', '.join(suggestions)}?"

    raise PassageRefError(
        f"Unknown book abbreviation: '{name}'.{suggestion_text} "
        f"Supported books: Matthew, Mark, Luke, John, Acts, Romans, etc."
    )


def _find_similar_books(query: str) -> list[str]:
    """Find books with names similar to the query."""
    query_lower = query.lower()
    suggestions = []

    for book in NT_BOOKS:
        book_lower = book.lower()
        # Check if query is a prefix
        if book_lower.startswith(query_lower) or query_lower.startswith(book_lower[:3]):
            suggestions.append(book)
            if len(suggestions) >= 3:
                break

    return suggestions


def parse_verse_spec(spec: str) -> list[int]:
    """Parse a verse specification into a list of verse numbers.

    Args:
        spec: Verse spec like "18", "18-19", "18,19", "18-19,21"

    Returns:
        Ordered list of verse numbers

    Raises:
        PassageRefError: If spec is malformed
    """
    verses: set[int] = set()

    # Normalize dashes (en-dash → hyphen)
    spec = spec.replace("–", "-").replace("—", "-")

    # Split by comma first
    parts = [p.strip() for p in spec.split(",") if p.strip()]

    if not parts:
        raise PassageRefError(f"Missing verse number in specification: '{spec}'")

    for part in parts:
        if "-" in part:
            # Range like "18-19"
            range_parts = part.split("-")
            if len(range_parts) != 2:
                raise PassageRefError(
                    f"Invalid verse range: '{part}'. Expected format like '18-19'."
                )

            try:
                start = int(range_parts[0].strip())
                end = int(range_parts[1].strip())
            except ValueError:
                raise PassageRefError(
                    f"Invalid verse numbers in range: '{part}'. "
                    "Verses must be integers."
                )

            if start > end:
                raise PassageRefError(
                    f"Invalid verse range: '{part}'. "
                    f"Start verse ({start}) cannot be greater than end verse ({end})."
                )

            if start < 1:
                raise PassageRefError(
                    f"Invalid verse number: {start}. Verses start at 1."
                )

            # Add all verses in range
            for v in range(start, end + 1):
                verses.add(v)
        else:
            # Single verse
            try:
                v = int(part.strip())
            except ValueError:
                raise PassageRefError(
                    f"Invalid verse number: '{part}'. Verses must be integers."
                )

            if v < 1:
                raise PassageRefError(f"Invalid verse number: {v}. Verses start at 1.")

            verses.add(v)

    return sorted(verses)


def parse_passage_ref(ref_string: str) -> ParsedPassageRef:
    """Parse a human-readable passage reference.

    Args:
        ref_string: Reference string like "John 1:18", "Jn 1:18-19", "Matt 3:2,4"

    Returns:
        ParsedPassageRef with book, chapter, verse_ids, and normalized form

    Raises:
        PassageRefError: With actionable error message if parsing fails

    Examples:
        >>> parse_passage_ref("John 1:18")
        ParsedPassageRef(book='John', chapter=1, verse_ids=['John.1.18'], ...)

        >>> parse_passage_ref("Jn 1:18-19")
        ParsedPassageRef(book='John', chapter=1, verse_ids=['John.1.18', 'John.1.19'], ...)

        >>> parse_passage_ref("1 Cor 1:1,3")
        ParsedPassageRef(book='1Corinthians', chapter=1, verse_ids=['1Corinthians.1.1', '1Corinthians.1.3'], ...)
    """
    original = ref_string
    ref_string = ref_string.strip()

    if not ref_string:
        raise PassageRefError("Empty reference string provided.")

    # Pattern: Book Chapter:Verse(s)
    # Book can be: "John", "1 John", "1John", "1 Cor", etc.
    # Verse(s) can be: "18", "18-19", "18,19", "18-19,21"

    # Normalize dashes in verse part for pattern matching
    normalized = ref_string.replace("–", "-").replace("—", "-")

    # Main pattern: captures book (with optional number prefix), chapter, verses
    # Book: optional digit + optional space + letters (+ optional more parts)
    # Chapter: digits
    # Verses: digits with optional ranges and commas
    pattern = r"^(\d?\s*[A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(\d+):(.+)$"
    match = re.match(pattern, normalized)

    if not match:
        # Try to give helpful error
        if ":" not in ref_string:
            raise PassageRefError(
                f"Invalid reference format: '{ref_string}'. "
                "Expected format: 'Book Chapter:Verse' (e.g., 'John 1:18')."
            )
        raise PassageRefError(
            f"Cannot parse reference: '{ref_string}'. "
            "Expected format: 'Book Chapter:Verse' (e.g., 'John 1:18', 'Matt 3:2-4')."
        )

    book_raw, chapter_str, verse_spec = match.groups()

    # Normalize book name
    book = normalize_book_name(book_raw)

    # Parse chapter
    try:
        chapter = int(chapter_str)
    except ValueError:
        raise PassageRefError(
            f"Invalid chapter number: '{chapter_str}'. Chapters must be integers."
        )

    if chapter < 1:
        raise PassageRefError(
            f"Invalid chapter number: {chapter}. Chapters start at 1."
        )

    # Parse verses
    verses = parse_verse_spec(verse_spec)

    # Build verse_ids
    verse_ids = [f"{book}.{chapter}.{v}" for v in verses]

    # Build normalized reference string
    if len(verses) == 1:
        normalized_ref = f"{book} {chapter}:{verses[0]}"
    elif verses == list(range(verses[0], verses[-1] + 1)):
        # Contiguous range
        normalized_ref = f"{book} {chapter}:{verses[0]}-{verses[-1]}"
    else:
        # Non-contiguous - show individual verses
        normalized_ref = f"{book} {chapter}:{','.join(str(v) for v in verses)}"

    return ParsedPassageRef(
        book=book,
        chapter=chapter,
        verse_ids=verse_ids,
        input_ref=original,
        normalized_ref=normalized_ref,
    )


def expand_verse_ids(ref_string: str) -> list[str]:
    """Convenience function: parse reference and return just verse_ids.

    Args:
        ref_string: Human-readable reference

    Returns:
        List of canonical verse_ids in order

    Raises:
        PassageRefError: If parsing fails
    """
    parsed = parse_passage_ref(ref_string)
    return parsed.verse_ids


def is_verse_id_format(ref_string: str) -> bool:
    """Check if a string is already in verse_id format (Book.Chapter.Verse).

    Args:
        ref_string: String to check

    Returns:
        True if string matches verse_id format, False otherwise
    """
    pattern = r"^[A-Za-z0-9]+\.\d+\.\d+$"
    return bool(re.match(pattern, ref_string.strip()))


def normalize_reference(ref_string: str) -> tuple[str, list[str]]:
    """Normalize a reference to canonical form and verse_ids.

    Handles both human references ("John 1:18") and verse_ids ("John.1.18").

    Args:
        ref_string: Either human reference or verse_id

    Returns:
        Tuple of (normalized_reference, verse_ids)

    Raises:
        PassageRefError: If parsing fails
    """
    ref_string = ref_string.strip()

    if is_verse_id_format(ref_string):
        # Already a verse_id - validate and normalize
        parts = ref_string.split(".")
        if len(parts) != 3:
            raise PassageRefError(
                f"Invalid verse_id format: '{ref_string}'. "
                "Expected: 'Book.Chapter.Verse'."
            )

        book_raw, chapter_str, verse_str = parts

        # Normalize book (handles "john" → "John")
        book = normalize_book_name(book_raw)

        try:
            chapter = int(chapter_str)
            verse = int(verse_str)
        except ValueError:
            raise PassageRefError(
                f"Invalid verse_id: '{ref_string}'. Chapter and verse must be integers."
            )

        verse_id = f"{book}.{chapter}.{verse}"
        normalized = f"{book} {chapter}:{verse}"
        return (normalized, [verse_id])

    # Human reference - parse it
    parsed = parse_passage_ref(ref_string)
    return (parsed.normalized_ref, parsed.verse_ids)
