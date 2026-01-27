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

Parsing code positions (8 characters):
  1: Person (1, 2, 3, -)
  2: Tense (P=present, I=imperfect, F=future, A=aorist, X=perfect, Y=pluperfect, -)
  3: Voice (A=active, M=middle, P=passive, -)
  4: Mood (I=indicative, D=imperative, S=subjunctive, O=optative, N=infinitive, P=participle, -)
  5: Case (N=nominative, G=genitive, D=dative, A=accusative, V=vocative, -)
  6: Number (S=singular, P=plural, -)
  7: Gender (M=masculine, F=feminine, N=neuter, -)
  8: Degree (C=comparative, S=superlative, -)

IMPORTANT: Parse code field semantics depend on POS:
- Verbs (non-participle): use person/tense/voice/mood/number, case/gender must be '-'
- Participles (V- with mood=P): use tense/voice + case/number/gender
- Nominals (N-, A-, RA, RD, RI, RP, RR): use case/number/gender, verb fields must be '-'
- Indeclinables (C-, D-, P-, I-, X-): all parse fields should be '-'
"""

import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

# Book number to name mapping (MorphGNT uses 2-digit book codes starting at 01)
# Note: Some MorphGNT sources use 61-based numbering (61=Matthew)
# We support both conventions.
BOOK_CODES = {
    # Standard MorphGNT numbering (01-27)
    "01": "Matthew",
    "02": "Mark",
    "03": "Luke",
    "04": "John",
    "05": "Acts",
    "06": "Romans",
    "07": "1Corinthians",
    "08": "2Corinthians",
    "09": "Galatians",
    "10": "Ephesians",
    "11": "Philippians",
    "12": "Colossians",
    "13": "1Thessalonians",
    "14": "2Thessalonians",
    "15": "1Timothy",
    "16": "2Timothy",
    "17": "Titus",
    "18": "Philemon",
    "19": "Hebrews",
    "20": "James",
    "21": "1Peter",
    "22": "2Peter",
    "23": "1John",
    "24": "2John",
    "25": "3John",
    "26": "Jude",
    "27": "Revelation",
    # Legacy 61-based numbering (for backwards compatibility)
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

# POS categories for decode gating
VERBAL_POS = {"V-"}  # Verbs
NOMINAL_POS = {
    "N-",
    "A-",
    "RA",
    "RD",
    "RI",
    "RP",
    "RR",
}  # Nouns, adjectives, articles, pronouns
INDECLINABLE_POS = {
    "C-",
    "D-",
    "P-",
    "I-",
    "X-",
}  # Conjunctions, adverbs, prepositions, etc.


class MorphGNTParseError(Exception):
    """Raised when MorphGNT data fails structural validation."""

    def __init__(
        self, message: str, line_number: int | None = None, raw_line: str | None = None
    ):
        self.line_number = line_number
        self.raw_line = raw_line
        full_message = message
        if line_number is not None:
            full_message = f"Line {line_number}: {message}"
        if raw_line is not None:
            full_message = f"{full_message}\n  Raw: {repr(raw_line)}"
        super().__init__(full_message)


class DelimiterAmbiguityError(MorphGNTParseError):
    """Raised when delimiter detection is ambiguous (both tabs and multi-space)."""

    def __init__(self, line_number: int, raw_line: str):
        super().__init__(
            "Ambiguous delimiter: line contains both tabs and multi-space separators",
            line_number=line_number,
            raw_line=raw_line,
        )


@dataclass
class ParseReport:
    """Receipt for a parse operation with detected delimiter.

    Constitutional constraint: all heuristics must be surfaced.
    """

    tokens: list["MorphGNTToken"] = field(default_factory=list)
    delimiter_detected: str = ""  # "TAB" | "SPACE" | ""
    files_parsed: list[str] = field(default_factory=list)
    total_lines: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class ParseCodeDecoded:
    """Decoded parse code with POS-gated field population."""

    raw: str
    # Verbal fields (populated for verbs)
    person: str | None = None
    tense: str | None = None
    voice: str | None = None
    mood: str | None = None
    # Nominal fields (populated for nominals and participles)
    case: str | None = None
    number: str | None = None
    gender: str | None = None
    # Degree (populated for adjectives/adverbs with comparison)
    degree: str | None = None
    # Validation
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class MorphGNTToken:
    """A single token from MorphGNT data."""

    ref: str  # "Matthew.3.2.1" format (friendly reference)
    source_ref: str  # "010302" (raw MorphGNT reference for reverse mapping)
    token_index: int  # Explicit position within verse (1-based)
    book: str
    chapter: int
    verse: int
    position: int  # Same as token_index, kept for API compatibility
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
    Example: "010302" -> ("Matthew", 3, 2)
    """
    if len(ref_code) != 6:
        raise MorphGNTParseError(f"Invalid reference code length: {repr(ref_code)}")

    book_code = ref_code[:2]
    try:
        chapter = int(ref_code[2:4])
        verse = int(ref_code[4:6])
    except ValueError as e:
        raise MorphGNTParseError(
            f"Invalid chapter/verse in reference: {repr(ref_code)}"
        ) from e

    book = BOOK_CODES.get(book_code, f"Book{book_code}")
    return book, chapter, verse


def decode_parse_code(parse_code: str, pos: str) -> ParseCodeDecoded:
    """
    Decode the 8-character parse code with POS-gated field population.

    Only populates fields that are semantically valid for the given POS.
    Flags errors when unexpected fields are populated.

    Args:
        parse_code: 8-character morphological code
        pos: Part of speech code (e.g., "V-", "N-", "P-")

    Returns:
        ParseCodeDecoded with appropriate fields populated and any validation errors
    """
    result = ParseCodeDecoded(raw=parse_code)

    if len(parse_code) != 8:
        result.errors.append(
            f"Invalid parse code length: {len(parse_code)}, expected 8"
        )
        return result

    # Position mappings
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

    # Extract raw values
    p0, p1, p2, p3, p4, p5, p6, p7 = parse_code

    # Decode each position
    person_val = person_map.get(p0)
    tense_val = tense_map.get(p1)
    voice_val = voice_map.get(p2)
    mood_val = mood_map.get(p3)
    case_val = case_map.get(p4)
    number_val = number_map.get(p5)
    gender_val = gender_map.get(p6)
    degree_val = degree_map.get(p7)

    # Flag unknown codes
    if p0 not in person_map:
        result.warnings.append(f"Unknown person code: {p0}")
    if p1 not in tense_map:
        result.warnings.append(f"Unknown tense code: {p1}")
    if p2 not in voice_map:
        result.warnings.append(f"Unknown voice code: {p2}")
    if p3 not in mood_map:
        result.warnings.append(f"Unknown mood code: {p3}")
    if p4 not in case_map:
        result.warnings.append(f"Unknown case code: {p4}")
    if p5 not in number_map:
        result.warnings.append(f"Unknown number code: {p5}")
    if p6 not in gender_map:
        result.warnings.append(f"Unknown gender code: {p6}")
    if p7 not in degree_map:
        result.warnings.append(f"Unknown degree code: {p7}")

    # Determine if this is a participle
    is_participle = pos in VERBAL_POS and mood_val == "participle"

    # POS-gated population
    if pos in VERBAL_POS:
        # Verbs: always populate tense/voice/mood
        result.tense = tense_val
        result.voice = voice_val
        result.mood = mood_val

        if is_participle:
            # Participles: have case/number/gender instead of person
            result.case = case_val
            result.number = number_val
            result.gender = gender_val
            # Participles should NOT have person
            if person_val is not None:
                result.errors.append(f"Participle has person field populated: {p0}")
        else:
            # Finite verbs: have person/number, but NOT case/gender
            result.person = person_val
            result.number = number_val  # Verbs can have number
            # Check for invalid nominal fields on non-participle verbs
            if case_val is not None:
                result.errors.append(
                    f"Non-participle verb has case field populated: {p4}"
                )
            if gender_val is not None:
                result.errors.append(
                    f"Non-participle verb has gender field populated: {p6}"
                )

    elif pos in NOMINAL_POS:
        # Nominals: populate case/number/gender
        result.case = case_val
        result.number = number_val
        result.gender = gender_val
        result.degree = degree_val  # Adjectives can have degree

        # Check for invalid verbal fields
        if person_val is not None:
            result.errors.append(f"Nominal has person field populated: {p0}")
        if tense_val is not None:
            result.errors.append(f"Nominal has tense field populated: {p1}")
        if voice_val is not None:
            result.errors.append(f"Nominal has voice field populated: {p2}")
        if mood_val is not None:
            result.errors.append(f"Nominal has mood field populated: {p3}")

    elif pos in INDECLINABLE_POS:
        # Indeclinables: all fields should be empty
        result.degree = degree_val  # Adverbs can have degree

        # Check that all other fields are empty
        if person_val is not None:
            result.errors.append(f"Indeclinable has person field populated: {p0}")
        if tense_val is not None:
            result.errors.append(f"Indeclinable has tense field populated: {p1}")
        if voice_val is not None:
            result.errors.append(f"Indeclinable has voice field populated: {p2}")
        if mood_val is not None:
            result.errors.append(f"Indeclinable has mood field populated: {p3}")
        if case_val is not None:
            result.errors.append(f"Indeclinable has case field populated: {p4}")
        if number_val is not None:
            result.errors.append(f"Indeclinable has number field populated: {p5}")
        if gender_val is not None:
            result.errors.append(f"Indeclinable has gender field populated: {p6}")

    else:
        # Unknown POS - populate all fields but warn
        result.warnings.append(f"Unknown POS: {pos}, populating all fields")
        result.person = person_val
        result.tense = tense_val
        result.voice = voice_val
        result.mood = mood_val
        result.case = case_val
        result.number = number_val
        result.gender = gender_val
        result.degree = degree_val

    return result


def detect_delimiter(line: str, line_number: int | None = None) -> str:
    """Detect delimiter in a MorphGNT line.

    Constitutional constraint: guessing must be either provably safe or explicitly surfaced.
    This function surfaces the detection and fails on ambiguity.

    Args:
        line: Raw line content
        line_number: Line number for error reporting

    Returns:
        "TAB" or "SPACE"

    Raises:
        DelimiterAmbiguityError: If both tabs and multi-space found
    """
    has_tabs = "\t" in line
    # Check for multiple consecutive spaces (not just single space which is within words)
    has_multi_space = (
        "  " in line or line.count(" ") >= 6
    )  # 7 columns = at least 6 spaces

    if has_tabs and has_multi_space:
        # Ambiguous - could parse differently with different delimiters
        raise DelimiterAmbiguityError(line_number or 0, line)

    if has_tabs:
        return "TAB"
    return "SPACE"


def parse_line(
    line: str, position_tracker: dict, line_number: int | None = None
) -> tuple[MorphGNTToken | None, str]:
    """
    Parse a single line from MorphGNT data.

    Supports both tab-separated (TSV) and space-separated formats.
    The official MorphGNT repository uses space-separated format.

    Args:
        line: Tab or space-separated line
        position_tracker: Dict tracking position within each verse
        line_number: Line number for error reporting

    Returns:
        Tuple of (MorphGNTToken or None if line is blank/comment, detected delimiter)

    Raises:
        MorphGNTParseError: If line has wrong number of columns
        DelimiterAmbiguityError: If delimiter detection is ambiguous
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None, ""

    # Detect delimiter - fails on ambiguity
    delimiter = detect_delimiter(line, line_number)

    # Split based on detected delimiter
    if delimiter == "TAB":
        parts = line.split("\t")
    else:
        parts = line.split(" ")

    if len(parts) != 7:
        raise MorphGNTParseError(
            f"Expected 7 columns, got {len(parts)}: {parts}",
            line_number=line_number,
            raw_line=line,
        )

    ref_code, pos, parse_code, surface_text, word, normalized, lemma = parts

    # Validate parse_code length
    if len(parse_code) != 8:
        raise MorphGNTParseError(
            f"Parse code must be 8 characters, got {len(parse_code)}: {repr(parse_code)}",
            line_number=line_number,
            raw_line=line,
        )

    # Parse reference
    try:
        book, chapter, verse = parse_reference(ref_code)
    except MorphGNTParseError as e:
        e.line_number = line_number
        e.raw_line = line
        raise

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

    return (
        MorphGNTToken(
            ref=ref,
            source_ref=ref_code,
            token_index=position,
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
        ),
        delimiter,
    )


def parse_file(
    file_path: Path, *, return_delimiter: bool = False
) -> list[MorphGNTToken] | tuple[list[MorphGNTToken], str]:
    """Parse a single MorphGNT TSV file.

    Args:
        file_path: Path to the MorphGNT TSV file
        return_delimiter: If True, return (tokens, delimiter) tuple.
                         If False (default), return just tokens list.
                         Prefer parse_file_with_delimiter() for delimiter access.

    Returns:
        If return_delimiter=False: list of MorphGNTToken
        If return_delimiter=True: tuple of (list of tokens, detected delimiter)

    Raises:
        MorphGNTParseError: If delimiter is inconsistent across lines

    See Also:
        parse_file_with_delimiter: Cleaner API when delimiter info is needed.
    """
    tokens = []
    position_tracker: dict[str, int] = {}
    file_delimiter: str | None = None

    with open(file_path, encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            token, delimiter = parse_line(
                line, position_tracker, line_number=line_number
            )
            if token:
                tokens.append(token)
                # Track delimiter consistency
                if delimiter:
                    if file_delimiter is None:
                        file_delimiter = delimiter
                    elif file_delimiter != delimiter:
                        raise MorphGNTParseError(
                            f"Inconsistent delimiter: expected {file_delimiter}, got {delimiter}",
                            line_number=line_number,
                            raw_line=line.strip(),
                        )

    if return_delimiter:
        return tokens, file_delimiter or "SPACE"
    return tokens


def parse_file_with_delimiter(file_path: Path) -> tuple[list[MorphGNTToken], str]:
    """Parse a MorphGNT file and return tokens with delimiter info.

    This is the receipt-grade variant that includes delimiter provenance.
    Use this when you need to track/verify the source format.

    Args:
        file_path: Path to the MorphGNT TSV file

    Returns:
        Tuple of (list of MorphGNTToken, detected delimiter "TAB" or "SPACE")
    """
    result = parse_file(file_path, return_delimiter=True)
    # Type narrowing for mypy - we know return_delimiter=True returns tuple
    assert isinstance(result, tuple)
    return result


def parse_directory(morphgnt_dir: Path) -> list[MorphGNTToken]:
    """
    Parse all MorphGNT TSV files in a directory.

    Expects files named like: 61-Mt-morphgnt.txt, 62-Mk-morphgnt.txt, etc.

    Note: For full provenance tracking, use parse_directory_with_report() instead.
    """
    report = parse_directory_with_report(morphgnt_dir)
    return report.tokens


def parse_directory_with_report(morphgnt_dir: Path) -> ParseReport:
    """
    Parse all MorphGNT TSV files in a directory with full provenance report.

    Expects files named like: 61-Mt-morphgnt.txt, 62-Mk-morphgnt.txt, etc.

    Returns:
        ParseReport with tokens, detected delimiter, and file list.
        Raises if delimiter is inconsistent across files.
    """
    report = ParseReport()
    directory_delimiter: str | None = None

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
        tokens, delimiter = parse_file_with_delimiter(file_path)
        report.tokens.extend(tokens)
        report.files_parsed.append(file_path.name)
        report.total_lines += len(tokens)
        print(f"    {len(tokens)} tokens (delimiter={delimiter})")

        # Track delimiter consistency across files
        if directory_delimiter is None:
            directory_delimiter = delimiter
        elif directory_delimiter != delimiter:
            report.warnings.append(
                f"Inconsistent delimiter in {file_path.name}: "
                f"expected {directory_delimiter}, got {delimiter}"
            )

    report.delimiter_detected = directory_delimiter or ""
    return report


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


# Legacy function for backwards compatibility
def format_parse_code(parse_code: str) -> dict:
    """
    DEPRECATED: Use decode_parse_code() instead for POS-gated decoding.

    Decode the 8-character parse code into human-readable fields.
    WARNING: This function does NOT check POS and may return semantically
    invalid field combinations.
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
        "_deprecated": "Use decode_parse_code() for POS-gated decoding",
    }
