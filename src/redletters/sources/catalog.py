"""Source catalog loading and validation.

Loads sources_catalog.yaml with backward-compatible schema extension.
New fields are optional; existing keys remain valid.

Design assumptions (documented here as ADR-style notes):
- sources_catalog.yaml lives at repo root (REDLETTERS_CATALOG_PATH env override)
- All sources require: name, license, role
- role must be one of: canonical_spine, lexicon_*, comparative_layer, witness_anchor, variant_collation
- Only one source may have role=canonical_spine (SBLGNT per ADR-007)
- format field defaults to "morphgnt" for SBLGNT, "json" otherwise
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import yaml


class SourceRole(Enum):
    """Valid source roles per ADR-007."""

    CANONICAL_SPINE = "canonical_spine"
    LEXICON_PRIMARY = "lexicon_primary"
    LEXICON_SECONDARY = "lexicon_secondary"
    LEXICON_SEMANTIC_DOMAINS = "lexicon_semantic_domains"
    COMPARATIVE_LAYER = "comparative_layer"
    WITNESS_ANCHOR = "witness_anchor"
    VARIANT_COLLATION = "variant_collation"
    SENSE_PACK = "sense_pack"  # v0.6.0: Installable lexicon/gloss packs


class CatalogValidationError(Exception):
    """Raised when catalog validation fails."""

    def __init__(self, message: str, source_key: str | None = None):
        self.source_key = source_key
        full_message = f"[{source_key}] {message}" if source_key else message
        super().__init__(full_message)


@dataclass
class SourcePack:
    """A single source entry from the catalog.

    Required fields:
        key: Unique identifier (e.g., "morphgnt-sblgnt")
        name: Human-readable name
        license: License identifier (SPDX or explicit string)
        role: Source role (canonical_spine, comparative_layer, etc.)

    Optional fields (backward-compatible additions):
        repo: GitHub repository URL
        commit: Full 40-char SHA for pinned version
        git_tag: Release tag
        version: Version string
        license_url: Link to full license text
        files: List of file paths within the source
        notes: Additional documentation
        format: Data format (morphgnt, json, tsv, xml)
        root_path: Override local path (relative to data root)
        verse_id_scheme: Verse ID format (default: "Book.Chapter.Verse")
        provenance: Additional provenance metadata
    """

    key: str
    name: str
    license: str
    role: SourceRole

    # Optional fields
    repo: str = ""
    commit: str = ""
    git_tag: str = ""
    version: str = ""
    license_url: str = ""
    files: list[str] = field(default_factory=list)
    notes: str = ""
    format: str = ""  # morphgnt, json, tsv, xml, pack
    root_path: str = ""  # Override local path
    verse_id_scheme: str = "Book.Chapter.Verse"
    provenance: dict = field(default_factory=dict)

    # Pack-specific fields (Sprint 7)
    pack_path: str = ""  # Local pack path relative to project root
    witness_siglum: str = ""  # Witness siglum for apparatus (e.g., "WH")
    witness_type: str = ""  # papyrus, uncial, minuscule, version, father
    date_range: tuple[int, int] | None = None  # Century range

    @property
    def is_spine(self) -> bool:
        """True if this is the canonical spine source."""
        return self.role == SourceRole.CANONICAL_SPINE

    @property
    def is_comparative(self) -> bool:
        """True if this is a comparative edition for variant generation."""
        return self.role == SourceRole.COMPARATIVE_LAYER

    @property
    def is_pack(self) -> bool:
        """True if this is a local data pack (Sprint 7)."""
        return self.format == "pack" or bool(self.pack_path)

    @property
    def has_pinned_commit(self) -> bool:
        """True if commit is a full 40-char SHA."""
        return len(self.commit) == 40 and all(
            c in "0123456789abcdef" for c in self.commit.lower()
        )

    @classmethod
    def from_dict(cls, key: str, data: dict) -> "SourcePack":
        """Create SourcePack from catalog entry dict."""
        # Required fields
        name = data.get("name", "")
        license_ = data.get("license", "")
        role_str = data.get("role", "")

        if not name:
            raise CatalogValidationError("Missing required field: name", key)
        if not license_:
            raise CatalogValidationError("Missing required field: license", key)
        if not role_str:
            raise CatalogValidationError("Missing required field: role", key)

        # Validate role
        try:
            role = SourceRole(role_str)
        except ValueError:
            valid_roles = [r.value for r in SourceRole]
            raise CatalogValidationError(
                f"Invalid role '{role_str}'. Must be one of: {valid_roles}",
                key,
            )

        # Parse date_range (list to tuple)
        date_range = data.get("date_range")
        if date_range and isinstance(date_range, list) and len(date_range) == 2:
            date_range = (date_range[0], date_range[1])
        else:
            date_range = None

        # Optional fields with defaults
        return cls(
            key=key,
            name=name,
            license=license_,
            role=role,
            repo=data.get("repo", ""),
            commit=data.get("commit", ""),
            git_tag=data.get("git_tag", ""),
            version=data.get("version", ""),
            license_url=data.get("license_url", ""),
            files=data.get("files", []),
            notes=data.get("notes", ""),
            format=data.get("format", ""),
            root_path=data.get("root_path", ""),
            verse_id_scheme=data.get("verse_id_scheme", "Book.Chapter.Verse"),
            provenance=data.get("provenance", {}),
            # Pack-specific fields (Sprint 7)
            pack_path=data.get("pack_path", ""),
            witness_siglum=data.get("witness_siglum", ""),
            witness_type=data.get("witness_type", ""),
            date_range=date_range,
        )

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "key": self.key,
            "name": self.name,
            "license": self.license,
            "role": self.role.value,
            "repo": self.repo,
            "commit": self.commit,
            "git_tag": self.git_tag,
            "version": self.version,
            "license_url": self.license_url,
            "files": self.files,
            "notes": self.notes,
            "format": self.format,
            "root_path": self.root_path,
            "verse_id_scheme": self.verse_id_scheme,
            "provenance": self.provenance,
            "is_spine": self.is_spine,
            "is_comparative": self.is_comparative,
            "has_pinned_commit": self.has_pinned_commit,
        }


@dataclass
class SourceCatalog:
    """Container for all source packs with validation.

    Enforces:
    - Exactly one canonical_spine source (SBLGNT per ADR-007)
    - All sources have required fields
    - Role values are valid
    """

    sources: dict[str, SourcePack] = field(default_factory=dict)
    path: Path | None = None

    @property
    def spine(self) -> SourcePack | None:
        """Get the canonical spine source (should be SBLGNT)."""
        for source in self.sources.values():
            if source.is_spine:
                return source
        return None

    @property
    def comparative_editions(self) -> list[SourcePack]:
        """Get all comparative edition sources."""
        return [s for s in self.sources.values() if s.is_comparative]

    def get(self, key: str) -> SourcePack | None:
        """Get source by key."""
        return self.sources.get(key)

    def validate(self) -> list[str]:
        """Validate catalog and return list of warnings."""
        warnings = []

        # Check for spine
        spine_sources = [s for s in self.sources.values() if s.is_spine]
        if len(spine_sources) == 0:
            warnings.append(
                "No canonical_spine source defined (ADR-007 requires SBLGNT)"
            )
        elif len(spine_sources) > 1:
            keys = [s.key for s in spine_sources]
            warnings.append(
                f"Multiple canonical_spine sources: {keys}. Only one allowed per ADR-007."
            )

        # Check for pinned commits on spine
        if spine_sources and not spine_sources[0].has_pinned_commit:
            warnings.append(
                f"Spine source '{spine_sources[0].key}' lacks pinned commit. "
                "Full 40-char SHA required for reproducibility."
            )

        # Check comparative editions have licenses
        for source in self.comparative_editions:
            if not source.license:
                warnings.append(
                    f"Comparative edition '{source.key}' missing license field"
                )

        return warnings

    @classmethod
    def load(cls, path: Path | str | None = None) -> "SourceCatalog":
        """Load catalog from YAML file.

        Args:
            path: Path to sources_catalog.yaml. If None, uses:
                  1. REDLETTERS_CATALOG_PATH env var
                  2. sources_catalog.yaml in repo root

        Returns:
            Loaded and validated SourceCatalog

        Raises:
            CatalogValidationError: If catalog is invalid
            FileNotFoundError: If catalog file not found
        """
        if path is None:
            path = os.environ.get("REDLETTERS_CATALOG_PATH")
            if path:
                path = Path(path)
            else:
                # Find repo root by looking for sources_catalog.yaml
                path = _find_catalog_path()

        if isinstance(path, str):
            path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Catalog not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)

        if not isinstance(raw_data, dict):
            raise CatalogValidationError("Catalog must be a YAML mapping")

        sources = {}
        for key, value in raw_data.items():
            # Skip comment-only keys and special keys
            if key.startswith("_") or not isinstance(value, dict):
                continue

            # Skip sources without required structure
            if "name" not in value:
                continue

            try:
                sources[key] = SourcePack.from_dict(key, value)
            except CatalogValidationError:
                raise

        catalog = cls(sources=sources, path=path)

        # Validate and surface warnings (but don't fail)
        warnings = catalog.validate()
        if warnings:
            # Store warnings for inspection but don't raise
            catalog._warnings = warnings

        return catalog


def _find_catalog_path() -> Path:
    """Find sources_catalog.yaml by walking up from current directory."""
    # Start from package location
    current = Path(__file__).resolve().parent

    # Walk up looking for sources_catalog.yaml
    for _ in range(10):  # Max depth
        candidate = current / "sources_catalog.yaml"
        if candidate.exists():
            return candidate

        # Also check parent
        parent_candidate = current.parent / "sources_catalog.yaml"
        if parent_candidate.exists():
            return parent_candidate

        # Try repo root markers
        if (current / ".git").exists() or (current / "pyproject.toml").exists():
            candidate = current / "sources_catalog.yaml"
            if candidate.exists():
                return candidate
            # Return expected path even if not found
            return candidate

        current = current.parent

    # Default to cwd
    return Path.cwd() / "sources_catalog.yaml"
