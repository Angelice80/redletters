"""Data pack loader for comparative editions.

Handles loading of verse-level data packs in the standard pack format:
  pack_dir/
    manifest.json
    Book/
      chapter_NN.tsv

TSV format: verse_id<TAB>greek_text
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PackManifest:
    """Manifest data for a pack.

    Pack Spec v1.1 fields (Sprint 8):
    - format_version: "1.1" for new packs
    - siglum: Apparatus siglum (preferred over witness_siglum)
    - witness_type: edition|manuscript|papyrus|version|father
    - coverage: List of book names (preferred over books)
    - century_range: [earliest, latest] (preferred over date_range)
    """

    pack_id: str
    name: str
    version: str
    license: str
    role: str
    witness_siglum: str
    witness_type: str
    date_range: tuple[int, int] | None
    books: list[str]
    verse_count: int
    format: str
    # v1.1 fields
    format_version: str = "1.0"
    siglum: str = ""
    coverage: list[str] | None = None
    century_range: tuple[int, int] | None = None
    license_url: str | None = None
    provenance: dict | None = None
    index: dict | None = None
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "PackManifest":
        """Create from dictionary."""
        date_range = data.get("date_range")
        if date_range and isinstance(date_range, list):
            date_range = tuple(date_range)

        century_range = data.get("century_range")
        if century_range and isinstance(century_range, list):
            century_range = tuple(century_range)

        # v1.1: siglum preferred over witness_siglum
        siglum = data.get("siglum", data.get("witness_siglum", ""))

        # v1.1: coverage preferred over books
        coverage = data.get("coverage")
        books = data.get("books", [])
        if coverage is None:
            coverage = books

        # v1.1: century_range preferred over date_range
        effective_century = century_range or date_range

        return cls(
            pack_id=data.get("pack_id", data.get("id", "")),
            name=data["name"],
            version=data.get("version", "1.0.0"),
            license=data["license"],
            role=data.get("role", "comparative_layer"),
            witness_siglum=siglum,  # Keep for backward compat
            witness_type=data.get("witness_type", "version"),
            date_range=date_range,
            books=books,
            verse_count=data.get("verse_count", 0),
            format=data.get("format", "tsv"),
            # v1.1 fields
            format_version=data.get("format_version", "1.0"),
            siglum=siglum,
            coverage=coverage,
            century_range=effective_century,
            license_url=data.get("license_url"),
            provenance=data.get("provenance"),
            index=data.get("index"),
            notes=data.get("notes", ""),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            "format_version": self.format_version,
            "id": self.pack_id,
            "name": self.name,
            "version": self.version,
            "license": self.license,
            "role": self.role,
            "siglum": self.siglum or self.witness_siglum,
            "witness_type": self.witness_type,
            "coverage": self.coverage or self.books,
        }
        # Optional fields
        if self.century_range:
            result["century_range"] = list(self.century_range)
        if self.license_url:
            result["license_url"] = self.license_url
        if self.provenance:
            result["provenance"] = self.provenance
        if self.index:
            result["index"] = self.index
        if self.notes:
            result["notes"] = self.notes
        # Legacy fields for backward compat
        if self.date_range:
            result["date_range"] = list(self.date_range)
        if self.books:
            result["books"] = self.books
        result["verse_count"] = self.verse_count
        result["format"] = self.format
        # Keep pack_id for legacy
        result["pack_id"] = self.pack_id
        return result

    @property
    def effective_siglum(self) -> str:
        """Get effective siglum (v1.1 siglum or legacy witness_siglum)."""
        return self.siglum or self.witness_siglum

    @property
    def effective_coverage(self) -> list[str]:
        """Get effective coverage (v1.1 coverage or legacy books)."""
        return self.coverage or self.books or []

    @property
    def effective_century_range(self) -> tuple[int, int] | None:
        """Get effective century range (v1.1 or legacy date_range)."""
        return self.century_range or self.date_range


@dataclass
class VerseText:
    """Text for a single verse."""

    verse_id: str
    text: str
    normalized_text: str | None = None

    def __post_init__(self):
        if self.normalized_text is None:
            self.normalized_text = self._normalize(self.text)

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize Greek text for comparison."""
        import re

        text = unicodedata.normalize("NFC", text)
        text = re.sub(r"[^\w\s]", "", text)
        text = " ".join(text.split())
        return text.lower()


class PackLoader:
    """Loader for comparative edition data packs."""

    def __init__(self, pack_path: Path):
        """Initialize with pack directory path.

        Args:
            pack_path: Path to pack directory containing manifest.json
        """
        self._path = Path(pack_path)
        self._manifest: PackManifest | None = None
        self._verses: dict[str, VerseText] = {}
        self._loaded = False

    @property
    def path(self) -> Path:
        """Pack directory path."""
        return self._path

    @property
    def manifest(self) -> PackManifest | None:
        """Pack manifest (None if not loaded)."""
        return self._manifest

    @property
    def is_loaded(self) -> bool:
        """True if pack data is loaded."""
        return self._loaded

    def load(self) -> bool:
        """Load pack manifest and verse data.

        Returns:
            True if loaded successfully
        """
        manifest_path = self._path / "manifest.json"
        if not manifest_path.exists():
            return False

        # Load manifest
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        self._manifest = PackManifest.from_dict(manifest_data)

        # Load verse data from each book
        for book in self._manifest.books:
            self._load_book(book)

        self._loaded = True
        return True

    def _load_book(self, book: str) -> None:
        """Load verse data for a book."""
        book_path = self._path / book
        if not book_path.exists():
            return

        # Load chapter files
        for chapter_file in sorted(book_path.glob("chapter_*.tsv")):
            self._load_chapter_file(chapter_file)

    def _load_chapter_file(self, path: Path) -> None:
        """Load a chapter TSV file."""
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split("\t", 1)
                if len(parts) == 2:
                    verse_id, text = parts
                    text = unicodedata.normalize("NFC", text)
                    self._verses[verse_id] = VerseText(
                        verse_id=verse_id,
                        text=text,
                    )

    def get_verse(self, verse_id: str) -> VerseText | None:
        """Get verse text by ID.

        Args:
            verse_id: Verse ID in "Book.Chapter.Verse" format

        Returns:
            VerseText or None if not found
        """
        if not self._loaded:
            self.load()
        return self._verses.get(verse_id)

    def get_verses_for_book(self, book: str) -> list[VerseText]:
        """Get all verses for a book.

        Args:
            book: Book name (e.g., "John")

        Returns:
            List of VerseText objects
        """
        if not self._loaded:
            self.load()

        return [v for v in self._verses.values() if v.verse_id.startswith(f"{book}.")]

    def get_verses_for_chapter(self, book: str, chapter: int) -> list[VerseText]:
        """Get all verses for a chapter.

        Args:
            book: Book name
            chapter: Chapter number

        Returns:
            List of VerseText objects
        """
        if not self._loaded:
            self.load()

        prefix = f"{book}.{chapter}."
        return [v for v in self._verses.values() if v.verse_id.startswith(prefix)]

    def has_verse(self, verse_id: str) -> bool:
        """Check if verse exists in pack."""
        if not self._loaded:
            self.load()
        return verse_id in self._verses

    def verse_ids(self) -> list[str]:
        """Get all verse IDs in pack."""
        if not self._loaded:
            self.load()
        return list(self._verses.keys())

    def __len__(self) -> int:
        """Number of verses in pack."""
        if not self._loaded:
            self.load()
        return len(self._verses)
