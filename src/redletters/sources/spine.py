"""Spine provider interface for verse text retrieval.

The spine is the canonical base text (SBLGNT per ADR-007).
All verse IDs use the format: "Book.Chapter.Verse" (e.g., "John.1.18").

Sprint 3 additions:
- InstalledSpineProvider: Loads from installed source packs
- SpineMissingError: Raised when spine not installed with actionable message
- Support for OpenGNT as alternative open-license spine
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from redletters.sources.editions import MorphGNTLoader


class SpineMissingError(Exception):
    """Raised when required spine data is not installed.

    Provides actionable installation instructions.
    """

    def __init__(self, source_id: str, message: str | None = None):
        self.source_id = source_id
        if message is None:
            message = self._build_message(source_id)
        self.install_instructions = message
        super().__init__(message)

    def _build_message(self, source_id: str) -> str:
        """Build helpful error message with install instructions."""
        return (
            f"Spine data not installed: {source_id}\n\n"
            f"To install the required spine data, run:\n\n"
            f"  redletters sources install {source_id}\n\n"
            f"For EULA-licensed sources, add --accept-eula:\n\n"
            f"  redletters sources install {source_id} --accept-eula\n\n"
            f"Alternative open-license spine (OpenGNT):\n\n"
            f"  redletters sources install open-greek-nt\n"
        )


@dataclass
class VerseText:
    """Text of a single verse from an edition."""

    verse_id: str  # "Book.Chapter.Verse" format
    text: str  # Greek text (space-joined tokens)
    tokens: list[dict] = field(default_factory=list)  # Token-level data
    source_key: str = ""  # Source pack key
    word_count: int = 0


@runtime_checkable
class SpineProvider(Protocol):
    """Protocol for spine text providers.

    Implementations must provide verse text retrieval
    with the canonical "Book.Chapter.Verse" ID scheme.
    """

    def get_verse_text(self, verse_id: str) -> VerseText | None:
        """Get text for a single verse.

        Args:
            verse_id: Verse identifier in "Book.Chapter.Verse" format

        Returns:
            VerseText or None if verse not found
        """
        ...

    def get_verse_tokens(self, verse_id: str) -> list[dict]:
        """Get token-level data for a verse.

        Args:
            verse_id: Verse identifier

        Returns:
            List of token dictionaries with morphological data
        """
        ...

    def has_verse(self, verse_id: str) -> bool:
        """Check if verse exists in spine."""
        ...

    @property
    def source_key(self) -> str:
        """Get source pack key for provenance."""
        ...


class SBLGNTSpine(SpineProvider):
    """SBLGNT spine provider backed by MorphGNT data.

    Loads MorphGNT-format files and provides verse-level access.
    Verses are cached after first load for efficiency.

    Per ADR-007: This is the canonical spine. All positions
    and variant references are relative to SBLGNT.
    """

    def __init__(
        self,
        data_path: Path | str,
        source_key: str = "morphgnt-sblgnt",
    ):
        """Initialize spine provider.

        Args:
            data_path: Path to MorphGNT data directory or file
            source_key: Source pack key for provenance
        """
        self._data_path = Path(data_path)
        self._source_key = source_key
        self._loader = MorphGNTLoader()
        self._verses: dict[str, VerseText] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Lazy-load verse data on first access."""
        if self._loaded:
            return

        if self._data_path.is_file():
            self._load_file(self._data_path)
        elif self._data_path.is_dir():
            self._load_directory(self._data_path)
        else:
            # Try common variations
            candidates = [
                self._data_path,
                self._data_path.parent / "morphgnt-snapshot",
            ]
            for candidate in candidates:
                if candidate.exists():
                    if candidate.is_dir():
                        self._load_directory(candidate)
                    else:
                        self._load_file(candidate)
                    break

        self._loaded = True

    def _load_file(self, path: Path) -> None:
        """Load a single MorphGNT file."""
        tokens = self._loader.load_file(path)
        self._index_tokens(tokens)

    def _load_directory(self, path: Path) -> None:
        """Load all MorphGNT files in directory."""
        tokens = self._loader.load_directory(path)
        self._index_tokens(tokens)

    def _index_tokens(self, tokens: list[dict]) -> None:
        """Index tokens by verse ID."""
        # Group tokens by verse
        verse_tokens: dict[str, list[dict]] = {}
        for token in tokens:
            verse_id = self._normalize_verse_id(
                token.get("verse_id", token.get("ref", ""))
            )
            if verse_id:
                if verse_id not in verse_tokens:
                    verse_tokens[verse_id] = []
                verse_tokens[verse_id].append(token)

        # Build VerseText objects
        for verse_id, vtokens in verse_tokens.items():
            # Sort by position
            vtokens.sort(key=lambda t: t.get("position", 0))

            # Join surface text
            text = " ".join(t.get("surface_text", t.get("word", "")) for t in vtokens)

            self._verses[verse_id] = VerseText(
                verse_id=verse_id,
                text=text,
                tokens=vtokens,
                source_key=self._source_key,
                word_count=len(vtokens),
            )

    def _normalize_verse_id(self, raw_id: str) -> str:
        """Normalize verse ID to Book.Chapter.Verse format.

        Handles:
        - "John.1.18" (already correct)
        - "John.1.18.1" (strip token position)
        - "Matthew.3.2" -> "Matthew.3.2"
        """
        if not raw_id:
            return ""

        parts = raw_id.split(".")
        if len(parts) >= 3:
            # Take first 3 parts (Book.Chapter.Verse)
            return ".".join(parts[:3])
        return raw_id

    def get_verse_text(self, verse_id: str) -> VerseText | None:
        """Get text for a single verse."""
        self._ensure_loaded()
        normalized = self._normalize_verse_id(verse_id)
        return self._verses.get(normalized)

    def get_verse_tokens(self, verse_id: str) -> list[dict]:
        """Get token-level data for a verse."""
        verse = self.get_verse_text(verse_id)
        return verse.tokens if verse else []

    def has_verse(self, verse_id: str) -> bool:
        """Check if verse exists in spine."""
        self._ensure_loaded()
        normalized = self._normalize_verse_id(verse_id)
        return normalized in self._verses

    @property
    def source_key(self) -> str:
        """Get source pack key."""
        return self._source_key

    @property
    def verse_count(self) -> int:
        """Get total number of loaded verses."""
        self._ensure_loaded()
        return len(self._verses)

    def list_verses(self, book: str | None = None) -> list[str]:
        """List all loaded verse IDs, optionally filtered by book."""
        self._ensure_loaded()
        if book:
            return [
                vid for vid in sorted(self._verses.keys()) if vid.startswith(f"{book}.")
            ]
        return sorted(self._verses.keys())


class FixtureSpine(SpineProvider):
    """Simple spine provider backed by fixture data.

    Used for testing without full MorphGNT data.
    Loads from a simple JSON or TSV fixture file.
    """

    def __init__(
        self,
        fixture_path: Path | str,
        source_key: str = "fixture-spine",
    ):
        """Initialize fixture spine.

        Args:
            fixture_path: Path to fixture file (JSON or TSV)
            source_key: Source identifier
        """
        self._fixture_path = Path(fixture_path)
        self._source_key = source_key
        self._verses: dict[str, VerseText] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Load fixture data on first access."""
        if self._loaded:
            return

        if not self._fixture_path.exists():
            self._loaded = True
            return

        suffix = self._fixture_path.suffix.lower()
        if suffix == ".json":
            self._load_json()
        elif suffix in (".tsv", ".txt"):
            self._load_tsv()

        self._loaded = True

    def _load_json(self) -> None:
        """Load JSON fixture."""
        import json

        with open(self._fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for verse_id, verse_data in data.items():
            if isinstance(verse_data, str):
                text = verse_data
                tokens = []
            else:
                text = verse_data.get("text", "")
                tokens = verse_data.get("tokens", [])

            self._verses[verse_id] = VerseText(
                verse_id=verse_id,
                text=text,
                tokens=tokens,
                source_key=self._source_key,
                word_count=len(text.split()) if text else 0,
            )

    def _load_tsv(self) -> None:
        """Load TSV fixture (verse_id<TAB>text format)."""
        with open(self._fixture_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split("\t", 1)
                if len(parts) >= 2:
                    verse_id, text = parts[0], parts[1]
                    self._verses[verse_id] = VerseText(
                        verse_id=verse_id,
                        text=text,
                        tokens=[],
                        source_key=self._source_key,
                        word_count=len(text.split()) if text else 0,
                    )

    def get_verse_text(self, verse_id: str) -> VerseText | None:
        """Get text for a single verse."""
        self._ensure_loaded()
        return self._verses.get(verse_id)

    def get_verse_tokens(self, verse_id: str) -> list[dict]:
        """Get token-level data for a verse."""
        verse = self.get_verse_text(verse_id)
        return verse.tokens if verse else []

    def has_verse(self, verse_id: str) -> bool:
        """Check if verse exists."""
        self._ensure_loaded()
        return verse_id in self._verses

    @property
    def source_key(self) -> str:
        """Get source key."""
        return self._source_key

    def add_verse(
        self, verse_id: str, text: str, tokens: list[dict] | None = None
    ) -> None:
        """Add a verse programmatically (for tests)."""
        self._verses[verse_id] = VerseText(
            verse_id=verse_id,
            text=text,
            tokens=tokens or [],
            source_key=self._source_key,
            word_count=len(text.split()) if text else 0,
        )


class InstalledSpineProvider(SpineProvider):
    """Spine provider that loads from installed source packs.

    Uses the source installer's data root to find installed spine data.
    Raises SpineMissingError with actionable instructions if spine not installed.

    Per ADR-007: SBLGNT is the canonical spine, but requires installation.
    OpenGNT can be used as an open-license alternative if configured.
    """

    def __init__(
        self,
        source_id: str = "morphgnt-sblgnt",
        data_root: Path | str | None = None,
        require_installed: bool = True,
    ):
        """Initialize installed spine provider.

        Args:
            source_id: Source pack ID (default: morphgnt-sblgnt)
            data_root: Override data root path
            require_installed: If True, raise SpineMissingError if not installed
        """
        import os

        self._source_id = source_id
        self._require_installed = require_installed

        # Resolve data root
        if data_root:
            self._data_root = Path(data_root)
        else:
            env_root = os.environ.get("REDLETTERS_DATA_ROOT")
            if env_root:
                self._data_root = Path(env_root)
            else:
                self._data_root = Path.home() / ".redletters" / "data"

        self._install_path = self._data_root / source_id
        self._delegate: SBLGNTSpine | None = None
        self._loaded = False
        self._license: str = ""

    def _ensure_loaded(self) -> None:
        """Load spine data on first access."""
        if self._loaded:
            return

        # Check if installed
        if not self._install_path.exists():
            if self._require_installed:
                raise SpineMissingError(self._source_id)
            self._loaded = True
            return

        # Load using appropriate loader based on source type
        self._delegate = SBLGNTSpine(
            self._install_path,
            source_key=self._source_id,
        )

        # Try to get license from manifest
        manifest_path = self._data_root / "installed_sources.json"
        if manifest_path.exists():
            import json

            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            sources = manifest.get("sources", {})
            if self._source_id in sources:
                self._license = sources[self._source_id].get("license", "")

        self._loaded = True

    def get_verse_text(self, verse_id: str) -> VerseText | None:
        """Get text for a single verse."""
        self._ensure_loaded()
        if self._delegate is None:
            return None
        verse = self._delegate.get_verse_text(verse_id)
        if verse:
            # Add license info to provenance
            verse.source_key = (
                f"{self._source_id} ({self._license})"
                if self._license
                else self._source_id
            )
        return verse

    def get_verse_tokens(self, verse_id: str) -> list[dict]:
        """Get token-level data for a verse."""
        self._ensure_loaded()
        if self._delegate is None:
            return []
        return self._delegate.get_verse_tokens(verse_id)

    def has_verse(self, verse_id: str) -> bool:
        """Check if verse exists in spine."""
        self._ensure_loaded()
        if self._delegate is None:
            return False
        return self._delegate.has_verse(verse_id)

    @property
    def source_key(self) -> str:
        """Get source pack key."""
        return self._source_id

    @property
    def license(self) -> str:
        """Get source license."""
        self._ensure_loaded()
        return self._license

    @property
    def is_installed(self) -> bool:
        """Check if spine is installed."""
        return self._install_path.exists()

    @property
    def verse_count(self) -> int:
        """Get total number of loaded verses."""
        self._ensure_loaded()
        if self._delegate is None:
            return 0
        return self._delegate.verse_count


def get_installed_spine(
    source_id: str | None = None,
    data_root: Path | str | None = None,
    allow_alternative: bool = True,
) -> InstalledSpineProvider:
    """Get an installed spine provider.

    Tries to load the requested spine, with fallback to alternatives.

    Args:
        source_id: Preferred source ID (default: morphgnt-sblgnt)
        data_root: Override data root path
        allow_alternative: If True, try OpenGNT if primary not installed

    Returns:
        InstalledSpineProvider configured for available spine

    Raises:
        SpineMissingError: If no spine is installed and allow_alternative is False
    """
    import os

    # Resolve data root
    if data_root:
        resolved_root = Path(data_root)
    else:
        env_root = os.environ.get("REDLETTERS_DATA_ROOT")
        if env_root:
            resolved_root = Path(env_root)
        else:
            resolved_root = Path.home() / ".redletters" / "data"

    # Default to canonical spine
    if source_id is None:
        source_id = "morphgnt-sblgnt"

    # Try requested spine
    primary = InstalledSpineProvider(
        source_id=source_id,
        data_root=resolved_root,
        require_installed=False,
    )
    if primary.is_installed:
        return primary

    # Try alternative open-license spine
    if allow_alternative:
        alternative_ids = ["open-greek-nt", "opentext-gnt"]
        for alt_id in alternative_ids:
            alt = InstalledSpineProvider(
                source_id=alt_id,
                data_root=resolved_root,
                require_installed=False,
            )
            if alt.is_installed:
                return alt

    # No spine installed - raise with instructions
    raise SpineMissingError(source_id)
