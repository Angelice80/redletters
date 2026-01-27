"""Parse MorphGNT SBLGNT TSV files into token records.

MorphGNT format (7 tab-separated columns):
1. Reference: BBCCVV format (book-chapter-verse encoded)
2. Part of Speech: Single or double-letter code
3. Parsing Code: 8-character grammatical breakdown
4. Text: Word with original punctuation
5. Word: Punctuation removed
6. Normalized: Standardized orthography
7. Lemma: Dictionary headword

Part of Speech codes:
  A-: Adjective, C-: Conjunction, D-: Adverb, I-: Interjection
  N-: Noun, P-: Preposition, RA: Definite article
  RD: Demonstrative pronoun, RI: Interrogative/indefinite pronoun
  RP: Personal pronoun, RR: Relative pronoun
  V-: Verb, X-: Particle

Parsing code positions (for verbs and nominals):
  1: Person (1, 2, 3, -)
  2: Tense (P=present, I=imperfect, F=future, A=aorist, X=perfect, Y=pluperfect, -)
  3: Voice (A=active, M=middle, P=passive, -)
  4: Mood (I=indicative, D=imperative, S=subjunctive, O=optative, N=infinitive, P=participle, -)
  5: Case (N=nominative, G=genitive, D=dative, A=accusative, V=vocative, -)
  6: Number (S=singular, P=plural, -)
  7: Gender (M=masculine, F=feminine, N=neuter, -)
  8: Degree (C=comparative, S=superlative, -)
"""

import unicodedata
from dataclasses import dataclass
from pathlib import Path

# Book number to name mapping (MorphGNT uses 2-digit book codes starting at 61)
BOOK_CODES = {
    "61": "Matthew",
    "62": "Mark",
    "63": "Luke",
    "64": "John",
    "65": "Acts",
    "66": "Romans",
    "67": "1Corinthians",
    "68": "2Corinthians",
    "69": "Galatians",
    "70": "Ephesians",
    "71": "Philippians",
    "72": "Colossians",
    "73": "1Thessalonians",
    "74": "2Thessalonians",
    "75": "1Timothy",
    "76": "2Timothy",
    "77": "Titus",
    "78": "Philemon",
    "79": "Hebrews",
    "80": "James",
    "81": "1Peter",
    "82": "2Peter",
    "83": "1John",
    "84": "2John",
    "85": "3John",
    "86": "Jude",
    "87": "Revelation",
}


@dataclass
class MorphGNTToken:
    """A single token from MorphGNT data."""

    ref: str  # "Matthew.3.2.1" format
    book: str
    chapter: int
    verse: int
    position: int
    surface_text: str  # with punctuation
    word: str  # stripped
    normalized: str
    lemma: str
    pos: str  # part of speech code
    parse_code: str  # raw 8-char morphology

    def to_db_tuple(self, source_id: int) -> tuple:
        """Convert to tuple for database insertion."""
        return (
            self.ref,
            self.surface_text,
            self.word,
            self.normalized,
            self.lemma,
            self.pos,
            self.parse_code,
            source_id,
        )


def normalize_greek(text: str) -> str:
    """Normalize Greek text to NFC form."""
    return unicodedata.normalize("NFC", text)


def parse_reference(ref_code: str) -> tuple[str, int, int]:
    """
    Parse MorphGNT reference code.

    Format: BBCCVV where BB=book, CC=chapter, VV=verse
    Example: "610302" -> ("Matthew", 3, 2)
    """
    book_code = ref_code[:2]
    chapter = int(ref_code[2:4])
    verse = int(ref_code[4:6])

    book = BOOK_CODES.get(book_code, f"Book{book_code}")
    return book, chapter, verse


def parse_line(line: str, position_tracker: dict) -> MorphGNTToken | None:
    """
    Parse a single line from MorphGNT TSV.

    Args:
        line: Tab-separated line
        position_tracker: Dict tracking position within each verse

    Returns:
        MorphGNTToken or None if line is invalid
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    parts = line.split("\t")
    if len(parts) != 7:
        return None

    ref_code, pos, parse_code, surface_text, word, normalized, lemma = parts

    # Parse reference
    book, chapter, verse = parse_reference(ref_code)

    # Track position within verse
    verse_key = f"{book}.{chapter}.{verse}"
    if verse_key not in position_tracker:
        position_tracker[verse_key] = 0
    position_tracker[verse_key] += 1
    position = position_tracker[verse_key]

    # Build canonical reference
    ref = f"{book}.{chapter}.{verse}.{position}"

    # Normalize Greek text
    surface_text = normalize_greek(surface_text)
    word = normalize_greek(word)
    normalized = normalize_greek(normalized)
    lemma = normalize_greek(lemma)

    return MorphGNTToken(
        ref=ref,
        book=book,
        chapter=chapter,
        verse=verse,
        position=position,
        surface_text=surface_text,
        word=word,
        normalized=normalized,
        lemma=lemma,
        pos=pos,
        parse_code=parse_code,
    )


def parse_file(file_path: Path) -> list[MorphGNTToken]:
    """Parse a single MorphGNT TSV file."""
    tokens = []
    position_tracker: dict[str, int] = {}

    with open(file_path, encoding="utf-8") as f:
        for line in f:
            token = parse_line(line, position_tracker)
            if token:
                tokens.append(token)

    return tokens


def parse_directory(morphgnt_dir: Path) -> list[MorphGNTToken]:
    """
    Parse all MorphGNT TSV files in a directory.

    Expects files named like: 61-Mt-morphgnt.txt, 62-Mk-morphgnt.txt, etc.
    """
    all_tokens = []

    # Find all morphgnt files
    pattern = "*-morphgnt.txt"
    files = sorted(morphgnt_dir.glob(pattern))

    if not files:
        # Try looking in subdirectory (GitHub archive structure)
        for subdir in morphgnt_dir.iterdir():
            if subdir.is_dir():
                files = sorted(subdir.glob(pattern))
                if files:
                    break

    for file_path in files:
        print(f"  Parsing {file_path.name}...")
        tokens = parse_file(file_path)
        all_tokens.extend(tokens)
        print(f"    {len(tokens)} tokens")

    return all_tokens


def get_unique_lemmas(tokens: list[MorphGNTToken]) -> set[str]:
    """Extract unique lemmas from token list."""
    return {t.lemma for t in tokens}


def get_verse_tokens(
    tokens: list[MorphGNTToken], book: str, chapter: int, verse: int
) -> list[MorphGNTToken]:
    """Filter tokens for a specific verse."""
    return [
        t
        for t in tokens
        if t.book == book and t.chapter == chapter and t.verse == verse
    ]


def format_parse_code(parse_code: str) -> dict:
    """
    Decode the 8-character parse code into human-readable fields.

    Returns dict with keys: person, tense, voice, mood, case, number, gender, degree
    """
    if len(parse_code) != 8:
        return {"raw": parse_code, "error": "invalid length"}

    person_map = {"1": "1st", "2": "2nd", "3": "3rd", "-": None}
    tense_map = {
        "P": "present",
        "I": "imperfect",
        "F": "future",
        "A": "aorist",
        "X": "perfect",
        "Y": "pluperfect",
        "-": None,
    }
    voice_map = {"A": "active", "M": "middle", "P": "passive", "-": None}
    mood_map = {
        "I": "indicative",
        "D": "imperative",
        "S": "subjunctive",
        "O": "optative",
        "N": "infinitive",
        "P": "participle",
        "-": None,
    }
    case_map = {
        "N": "nominative",
        "G": "genitive",
        "D": "dative",
        "A": "accusative",
        "V": "vocative",
        "-": None,
    }
    number_map = {"S": "singular", "P": "plural", "-": None}
    gender_map = {"M": "masculine", "F": "feminine", "N": "neuter", "-": None}
    degree_map = {"C": "comparative", "S": "superlative", "-": None}

    return {
        "person": person_map.get(parse_code[0], parse_code[0]),
        "tense": tense_map.get(parse_code[1], parse_code[1]),
        "voice": voice_map.get(parse_code[2], parse_code[2]),
        "mood": mood_map.get(parse_code[3], parse_code[3]),
        "case": case_map.get(parse_code[4], parse_code[4]),
        "number": number_map.get(parse_code[5], parse_code[5]),
        "gender": gender_map.get(parse_code[6], parse_code[6]),
        "degree": degree_map.get(parse_code[7], parse_code[7]),
        "raw": parse_code,
    }
