"""Pack indexer for generating coverage indices.

Sprint 8: B1 - Generates lightweight index for faster status display.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class ChapterIndex:
    """Index for a single chapter."""

    chapter_num: int
    verse_count: int
    first_verse: int
    last_verse: int

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "verse_count": self.verse_count,
            "first_verse": self.first_verse,
            "last_verse": self.last_verse,
        }


@dataclass
class BookIndex:
    """Index for a single book."""

    book_name: str
    chapters: dict[int, ChapterIndex] = field(default_factory=dict)

    @property
    def total_verses(self) -> int:
        """Total verses across all chapters."""
        return sum(ch.verse_count for ch in self.chapters.values())

    @property
    def chapter_count(self) -> int:
        """Number of chapters."""
        return len(self.chapters)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            str(ch_num): ch.to_dict() for ch_num, ch in sorted(self.chapters.items())
        }


@dataclass
class PackIndex:
    """Complete index for a pack."""

    generated_at: str
    total_verses: int
    books: dict[str, BookIndex] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for manifest embedding."""
        return {
            "generated_at": self.generated_at,
            "total_verses": self.total_verses,
            "books": {
                name: book.to_dict() for name, book in sorted(self.books.items())
            },
        }


class PackIndexer:
    """Generates index for a pack.

    Usage:
        indexer = PackIndexer(pack_path)
        index = indexer.generate()

        # Optionally update manifest
        indexer.update_manifest()
    """

    def __init__(self, pack_path: Path | str):
        """Initialize indexer.

        Args:
            pack_path: Path to pack directory
        """
        self._path = Path(pack_path)
        self._index: PackIndex | None = None

    def generate(self) -> PackIndex:
        """Generate index from pack data files.

        Returns:
            PackIndex with coverage information
        """
        books: dict[str, BookIndex] = {}
        total_verses = 0

        # Find all book directories
        for item in sorted(self._path.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                # Check if it contains chapter files
                chapter_files = list(item.glob("chapter_*.tsv"))
                if chapter_files:
                    book_index = self._index_book(item)
                    books[item.name] = book_index
                    total_verses += book_index.total_verses

        self._index = PackIndex(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_verses=total_verses,
            books=books,
        )

        return self._index

    def _index_book(self, book_path: Path) -> BookIndex:
        """Index a single book directory."""
        book_index = BookIndex(book_name=book_path.name)

        for chapter_file in sorted(book_path.glob("chapter_*.tsv")):
            # Extract chapter number
            match = re.match(r"chapter_(\d+)\.tsv", chapter_file.name)
            if not match:
                continue

            chapter_num = int(match.group(1))
            chapter_index = self._index_chapter(chapter_file)
            chapter_index.chapter_num = chapter_num
            book_index.chapters[chapter_num] = chapter_index

        return book_index

    def _index_chapter(self, chapter_file: Path) -> ChapterIndex:
        """Index a single chapter file."""
        verses: list[int] = []

        with open(chapter_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("verse_id"):
                    continue

                parts = line.split("\t", 1)
                if len(parts) < 2:
                    continue

                verse_id = parts[0]
                # Extract verse number from Book.Chapter.Verse
                id_parts = verse_id.split(".")
                if len(id_parts) >= 3:
                    try:
                        verse_num = int(id_parts[2])
                        verses.append(verse_num)
                    except ValueError:
                        pass

        if not verses:
            return ChapterIndex(
                chapter_num=0, verse_count=0, first_verse=0, last_verse=0
            )

        return ChapterIndex(
            chapter_num=0,  # Set by caller
            verse_count=len(verses),
            first_verse=min(verses),
            last_verse=max(verses),
        )

    def update_manifest(self, dry_run: bool = False) -> dict | None:
        """Update manifest.json with generated index.

        Args:
            dry_run: If True, return updated manifest without writing

        Returns:
            Updated manifest dict if dry_run, else None
        """
        if not self._index:
            self.generate()

        manifest_path = self._path / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"No manifest.json at {manifest_path}")

        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        # Update index field
        manifest["index"] = self._index.to_dict()

        # Update verse_count
        manifest["verse_count"] = self._index.total_verses

        # Update coverage from discovered books
        manifest["coverage"] = list(self._index.books.keys())

        if dry_run:
            return manifest

        # Write back
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            f.write("\n")

        return None

    def get_summary(self) -> dict:
        """Get a summary of the index.

        Returns:
            Summary dict with counts
        """
        if not self._index:
            self.generate()

        return {
            "total_verses": self._index.total_verses,
            "total_books": len(self._index.books),
            "books": {
                name: {
                    "chapters": book.chapter_count,
                    "verses": book.total_verses,
                }
                for name, book in self._index.books.items()
            },
        }


def index_pack(pack_path: Path | str, update_manifest: bool = False) -> PackIndex:
    """Convenience function to index a pack.

    Args:
        pack_path: Path to pack directory
        update_manifest: If True, update manifest.json

    Returns:
        PackIndex
    """
    indexer = PackIndexer(pack_path)
    index = indexer.generate()

    if update_manifest:
        indexer.update_manifest()

    return index
