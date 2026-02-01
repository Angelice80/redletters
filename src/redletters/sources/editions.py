"""Edition loader implementations.

Provides loaders for different Greek text edition formats:
- MorphGNTLoader: MorphGNT space-separated format
- FixtureLoader: Simple JSON/TSV fixtures for testing
"""

from __future__ import annotations

import json
import unicodedata
from abc import ABC, abstractmethod
from pathlib import Path


# Book code mappings (shared with morphgnt_parser)
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
    # Legacy 61-based numbering
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


class EditionLoader(ABC):
    """Abstract base class for edition loaders."""

    @abstractmethod
    def load_file(self, path: Path) -> list[dict]:
        """Load tokens from a single file.

        Args:
            path: Path to edition file

        Returns:
            List of token dictionaries with at minimum:
            - verse_id: "Book.Chapter.Verse" format
            - surface_text: Greek text
            - position: Token position in verse (1-based)
        """
        ...

    @abstractmethod
    def load_directory(self, path: Path) -> list[dict]:
        """Load tokens from a directory of files.

        Args:
            path: Path to directory

        Returns:
            Combined list of token dictionaries
        """
        ...


class MorphGNTLoader(EditionLoader):
    """Loader for MorphGNT format files.

    MorphGNT format (7 space-separated columns):
    1. Reference: BBCCVV format (book-chapter-verse encoded)
    2. Part of Speech: Single or double-letter code
    3. Parsing Code: 8-character grammatical breakdown
    4. Text: Word with original punctuation
    5. Word: Punctuation removed
    6. Normalized: Standardized orthography
    7. Lemma: Dictionary headword
    """

    def load_file(self, path: Path) -> list[dict]:
        """Load tokens from a MorphGNT file."""
        tokens = []
        position_tracker: dict[str, int] = {}

        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                token = self._parse_line(line, position_tracker, line_num)
                if token:
                    tokens.append(token)

        return tokens

    def load_directory(self, path: Path) -> list[dict]:
        """Load tokens from all MorphGNT files in directory."""
        tokens = []

        # Find MorphGNT files
        patterns = ["*-morphgnt.txt", "*-morphgnt.tsv", "*.txt"]
        files = []

        for pattern in patterns:
            found = sorted(path.glob(pattern))
            if found:
                # Filter to only morphgnt-like files
                files = [
                    f
                    for f in found
                    if "morphgnt" in f.name.lower()
                    or f.name.startswith(
                        (
                            "61-",
                            "62-",
                            "63-",
                            "64-",
                            "65-",
                            "66-",
                            "67-",
                            "68-",
                            "69-",
                            "70-",
                            "71-",
                            "72-",
                            "73-",
                            "74-",
                            "75-",
                            "76-",
                            "77-",
                            "78-",
                            "79-",
                            "80-",
                            "81-",
                            "82-",
                            "83-",
                            "84-",
                            "85-",
                            "86-",
                            "87-",
                            "01-",
                            "02-",
                            "03-",
                            "04-",
                            "05-",
                            "06-",
                            "07-",
                            "08-",
                            "09-",
                            "10-",
                            "11-",
                            "12-",
                            "13-",
                            "14-",
                            "15-",
                            "16-",
                            "17-",
                            "18-",
                            "19-",
                            "20-",
                            "21-",
                            "22-",
                            "23-",
                            "24-",
                            "25-",
                            "26-",
                            "27-",
                        )
                    )
                ]
                if files:
                    break

        for file_path in files:
            tokens.extend(self.load_file(file_path))

        return tokens

    def _parse_line(
        self, line: str, position_tracker: dict[str, int], line_num: int
    ) -> dict | None:
        """Parse a single MorphGNT line."""
        # Split on spaces (MorphGNT uses space separator)
        parts = line.split(" ")
        if len(parts) != 7:
            # Try tab separator
            parts = line.split("\t")
            if len(parts) != 7:
                return None

        ref_code, pos, parse_code, surface_text, word, normalized, lemma = parts

        # Parse reference: BBCCVV
        if len(ref_code) != 6:
            return None

        book_code = ref_code[:2]
        try:
            chapter = int(ref_code[2:4])
            verse = int(ref_code[4:6])
        except ValueError:
            return None

        book = BOOK_CODES.get(book_code, f"Book{book_code}")

        # Build verse ID
        verse_id = f"{book}.{chapter}.{verse}"

        # Track position within verse
        if verse_id not in position_tracker:
            position_tracker[verse_id] = 0
        position_tracker[verse_id] += 1
        position = position_tracker[verse_id]

        # Normalize Greek text
        surface_text = unicodedata.normalize("NFC", surface_text)
        word = unicodedata.normalize("NFC", word)
        normalized = unicodedata.normalize("NFC", normalized)
        lemma = unicodedata.normalize("NFC", lemma)

        return {
            "verse_id": verse_id,
            "ref": f"{verse_id}.{position}",
            "position": position,
            "surface_text": surface_text,
            "word": word,
            "normalized": normalized,
            "lemma": lemma,
            "pos": pos,
            "parse_code": parse_code,
            "source_ref": ref_code,
            "book": book,
            "chapter": chapter,
            "verse": verse,
        }


class FixtureLoader(EditionLoader):
    """Loader for simple fixture files (JSON or TSV).

    JSON format:
    {
        "John.1.18": {
            "text": "Θεὸν οὐδεὶς ἑώρακεν πώποτε...",
            "tokens": [...]  // optional
        }
    }

    TSV format:
    verse_id<TAB>text
    """

    def load_file(self, path: Path) -> list[dict]:
        """Load tokens from a fixture file."""
        suffix = path.suffix.lower()

        if suffix == ".json":
            return self._load_json(path)
        elif suffix in (".tsv", ".txt"):
            return self._load_tsv(path)
        else:
            return []

    def load_directory(self, path: Path) -> list[dict]:
        """Load from all fixture files in directory."""
        tokens = []

        for pattern in ["*.json", "*.tsv"]:
            for file_path in sorted(path.glob(pattern)):
                tokens.extend(self.load_file(file_path))

        return tokens

    def _load_json(self, path: Path) -> list[dict]:
        """Load JSON fixture."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        tokens = []
        for verse_id, verse_data in data.items():
            if isinstance(verse_data, str):
                # Simple format: {"John.1.18": "Greek text..."}
                text = verse_data
                verse_tokens = []
            else:
                text = verse_data.get("text", "")
                verse_tokens = verse_data.get("tokens", [])

            if verse_tokens:
                # Use explicit tokens
                for i, tok in enumerate(verse_tokens, start=1):
                    tok["verse_id"] = verse_id
                    tok["position"] = tok.get("position", i)
                    tokens.append(tok)
            elif text:
                # Split text into tokens
                words = text.split()
                for i, word in enumerate(words, start=1):
                    tokens.append(
                        {
                            "verse_id": verse_id,
                            "ref": f"{verse_id}.{i}",
                            "position": i,
                            "surface_text": word,
                            "word": word.strip(".,;:"),
                            "normalized": unicodedata.normalize(
                                "NFC", word.strip(".,;:")
                            ),
                            "lemma": "",
                            "pos": "",
                            "parse_code": "",
                        }
                    )

        return tokens

    def _load_tsv(self, path: Path) -> list[dict]:
        """Load TSV fixture."""
        tokens = []

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split("\t", 1)
                if len(parts) >= 2:
                    verse_id, text = parts[0], parts[1]
                    words = text.split()
                    for i, word in enumerate(words, start=1):
                        tokens.append(
                            {
                                "verse_id": verse_id,
                                "ref": f"{verse_id}.{i}",
                                "position": i,
                                "surface_text": word,
                                "word": word.strip(".,;:"),
                                "normalized": unicodedata.normalize(
                                    "NFC", word.strip(".,;:")
                                ),
                                "lemma": "",
                                "pos": "",
                                "parse_code": "",
                            }
                        )

        return tokens
