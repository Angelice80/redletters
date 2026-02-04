"""Sense pack schema and validation for v0.6.0.

Sense packs provide lexicon/gloss data with citation-grade provenance.

Manifest required fields:
  - pack_id: Unique identifier (lowercase slug)
  - name: Human-readable name
  - version: Semantic version
  - role: Must be "sense_pack"
  - license: SPDX identifier or explicit string
  - source_id: Stable citation key for bibliographic reference
  - source_title: Full bibliographic title

Optional fields:
  - edition: Edition string
  - publisher: Publisher name
  - year: Publication year
  - license_url: Link to license text
  - source_url: Link to original source
  - notes: Additional documentation

Data format (senses.tsv or senses.json):
  - lemma: Greek lemma (required)
  - sense_id: Unique sense identifier (required)
  - gloss: English gloss (required)
  - definition: Fuller definition (optional)
  - domain: Semantic domain (optional)
  - weight: Default weight 0.0-1.0 (optional, default 1.0)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


# Required fields for sense pack manifest
REQUIRED_SENSE_PACK_FIELDS = {
    "name",
    "license",
    "source_id",
    "source_title",
}

# Sense data required fields
REQUIRED_SENSE_FIELDS = {"lemma", "sense_id", "gloss"}

# Valid role for sense packs
SENSE_PACK_ROLE = "sense_pack"


@dataclass
class SensePackManifest:
    """Manifest for a sense pack with citation-grade provenance.

    Provides full bibliographic metadata for scholarly citation.
    """

    pack_id: str
    name: str
    version: str
    license: str
    source_id: str
    source_title: str

    # Optional citation fields
    edition: str = ""
    publisher: str = ""
    year: int | None = None
    license_url: str = ""
    source_url: str = ""
    notes: str = ""

    # Pack metadata
    format_version: str = "1.0"
    role: str = SENSE_PACK_ROLE
    sense_count: int = 0
    data_file: str = "senses.tsv"

    @classmethod
    def from_dict(cls, data: dict) -> "SensePackManifest":
        """Create from manifest dictionary."""
        pack_id = data.get("pack_id", data.get("id", ""))

        return cls(
            pack_id=pack_id,
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            license=data.get("license", ""),
            source_id=data.get("source_id", ""),
            source_title=data.get("source_title", ""),
            edition=data.get("edition", ""),
            publisher=data.get("publisher", ""),
            year=data.get("year"),
            license_url=data.get("license_url", ""),
            source_url=data.get("source_url", ""),
            notes=data.get("notes", ""),
            format_version=data.get("format_version", "1.0"),
            role=data.get("role", SENSE_PACK_ROLE),
            sense_count=data.get("sense_count", 0),
            data_file=data.get("data_file", "senses.tsv"),
        )

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        result = {
            "format_version": self.format_version,
            "pack_id": self.pack_id,
            "name": self.name,
            "version": self.version,
            "role": self.role,
            "license": self.license,
            "source_id": self.source_id,
            "source_title": self.source_title,
        }

        # Optional fields
        if self.edition:
            result["edition"] = self.edition
        if self.publisher:
            result["publisher"] = self.publisher
        if self.year:
            result["year"] = self.year
        if self.license_url:
            result["license_url"] = self.license_url
        if self.source_url:
            result["source_url"] = self.source_url
        if self.notes:
            result["notes"] = self.notes
        if self.sense_count:
            result["sense_count"] = self.sense_count
        if self.data_file:
            result["data_file"] = self.data_file

        return result

    @property
    def requires_license_acceptance(self) -> bool:
        """Check if license requires explicit acceptance.

        Public domain (CC0, PD) does not require acceptance.
        """
        license_lower = self.license.lower()
        return not any(
            pd in license_lower for pd in ["public domain", "cc0", "pd", "unlicense"]
        )

    def citation_dict(self) -> dict:
        """Return citation-grade provenance dictionary.

        Suitable for inclusion in receipts and exports.
        """
        result = {
            "source_id": self.source_id,
            "source_title": self.source_title,
            "license": self.license,
        }
        if self.edition:
            result["edition"] = self.edition
        if self.publisher:
            result["publisher"] = self.publisher
        if self.year:
            result["year"] = self.year
        if self.license_url:
            result["license_url"] = self.license_url
        if self.source_url:
            result["source_url"] = self.source_url
        return result


@dataclass
class SenseEntry:
    """A single sense entry from a sense pack."""

    lemma: str
    sense_id: str
    gloss: str
    definition: str = ""
    domain: str = ""
    weight: float = 1.0

    # Provenance (populated from pack manifest)
    source_id: str = ""

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "lemma": self.lemma,
            "sense_id": self.sense_id,
            "gloss": self.gloss,
            "definition": self.definition,
            "domain": self.domain,
            "weight": self.weight,
            "source_id": self.source_id,
        }


@dataclass
class SensePackValidationError:
    """A validation error for sense packs."""

    path: str
    message: str
    severity: str = "error"


@dataclass
class SensePackValidationResult:
    """Result of sense pack validation."""

    valid: bool = True
    errors: list[SensePackValidationError] = field(default_factory=list)
    warnings: list[SensePackValidationError] = field(default_factory=list)
    manifest: SensePackManifest | None = None
    sense_count: int = 0

    def add_error(self, path: str, message: str) -> None:
        """Add an error."""
        self.errors.append(SensePackValidationError(path, message, "error"))
        self.valid = False

    def add_warning(self, path: str, message: str) -> None:
        """Add a warning."""
        self.warnings.append(SensePackValidationError(path, message, "warning"))


class SensePackValidator:
    """Validates sense packs.

    Usage:
        validator = SensePackValidator(pack_path)
        result = validator.validate()

        if not result.valid:
            for err in result.errors:
                print(f"ERROR: {err.path}: {err.message}")
    """

    def __init__(self, pack_path: Path | str, strict: bool = False):
        """Initialize validator.

        Args:
            pack_path: Path to sense pack directory
            strict: If True, treat warnings as errors
        """
        self._path = Path(pack_path)
        self._strict = strict
        self._manifest_data: dict | None = None

    def validate(self) -> SensePackValidationResult:
        """Run full validation.

        Returns:
            SensePackValidationResult with errors and warnings
        """
        result = SensePackValidationResult()

        # Check pack directory exists
        if not self._path.exists():
            result.add_error(str(self._path), "Sense pack directory does not exist")
            return result

        if not self._path.is_dir():
            result.add_error(str(self._path), "Sense pack path is not a directory")
            return result

        # Validate manifest
        manifest_result = self._validate_manifest()
        if manifest_result.errors:
            result.errors.extend(manifest_result.errors)
            result.valid = False
        result.warnings.extend(manifest_result.warnings)
        result.manifest = manifest_result.manifest

        if not result.valid:
            return result

        # Validate sense data file
        data_result = self._validate_sense_data(result.manifest)
        if data_result.errors:
            result.errors.extend(data_result.errors)
            result.valid = False
        result.warnings.extend(data_result.warnings)
        result.sense_count = data_result.sense_count

        # In strict mode, warnings become errors
        if self._strict:
            for warning in result.warnings:
                result.add_error(warning.path, f"[strict] {warning.message}")

        return result

    def _validate_manifest(self) -> SensePackValidationResult:
        """Validate manifest.json."""
        result = SensePackValidationResult()
        manifest_path = self._path / "manifest.json"

        if not manifest_path.exists():
            result.add_error(str(manifest_path), "manifest.json not found")
            return result

        try:
            with open(manifest_path, encoding="utf-8") as f:
                self._manifest_data = json.load(f)
        except json.JSONDecodeError as e:
            result.add_error(str(manifest_path), f"Invalid JSON: {e}")
            return result

        # Check role is sense_pack
        role = self._manifest_data.get("role", "")
        if role != SENSE_PACK_ROLE:
            result.add_error(
                str(manifest_path),
                f"Invalid role '{role}'. Sense packs must have role: '{SENSE_PACK_ROLE}'",
            )
            return result

        # Check required fields
        for field_name in REQUIRED_SENSE_PACK_FIELDS:
            if (
                field_name not in self._manifest_data
                or not self._manifest_data[field_name]
            ):
                result.add_error(
                    str(manifest_path), f"Missing required field: {field_name}"
                )

        # Validate pack_id format
        pack_id = self._manifest_data.get("pack_id", self._manifest_data.get("id", ""))
        if not pack_id:
            result.add_error(str(manifest_path), "Missing pack_id (or id)")
        elif not re.match(r"^[a-z0-9-]+$", pack_id):
            result.add_warning(
                str(manifest_path),
                f"pack_id '{pack_id}' should be lowercase slug format",
            )

        # Validate source_id format (citation key)
        source_id = self._manifest_data.get("source_id", "")
        if source_id and not re.match(r"^[a-zA-Z0-9_-]+$", source_id):
            result.add_warning(
                str(manifest_path),
                f"source_id '{source_id}' should be alphanumeric citation key",
            )

        # Create manifest object if valid
        if result.valid:
            result.manifest = SensePackManifest.from_dict(self._manifest_data)

        return result

    def _validate_sense_data(
        self, manifest: SensePackManifest | None
    ) -> SensePackValidationResult:
        """Validate sense data file."""
        result = SensePackValidationResult()

        if manifest is None:
            return result

        data_file = manifest.data_file
        data_path = self._path / data_file

        if not data_path.exists():
            result.add_error(str(data_path), f"Sense data file not found: {data_file}")
            return result

        # Determine format from extension
        if data_file.endswith(".tsv"):
            result = self._validate_tsv_senses(data_path, manifest.source_id)
        elif data_file.endswith(".json"):
            result = self._validate_json_senses(data_path, manifest.source_id)
        else:
            result.add_error(
                str(data_path),
                f"Unsupported sense data format: {data_file}. Use .tsv or .json",
            )

        return result

    def _validate_tsv_senses(
        self, path: Path, source_id: str
    ) -> SensePackValidationResult:
        """Validate TSV sense data file."""
        result = SensePackValidationResult()

        try:
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            result.add_error(str(path), f"Cannot read file: {e}")
            return result

        if not lines:
            result.add_error(str(path), "File is empty")
            return result

        # Check header
        header = lines[0].strip().split("\t")
        header_lower = [h.lower() for h in header]

        # Verify required columns exist
        for req_field in REQUIRED_SENSE_FIELDS:
            if req_field not in header_lower:
                result.add_error(str(path), f"Missing required column: {req_field}")

        if not result.valid:
            return result

        # Map column indices
        col_indices = {h: i for i, h in enumerate(header_lower)}

        # Validate data rows
        seen_sense_ids: set[str] = set()
        for line_num, line in enumerate(lines[1:], start=2):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split("\t")

            # Get required fields
            lemma_idx = col_indices.get("lemma", 0)
            sense_id_idx = col_indices.get("sense_id", 1)
            gloss_idx = col_indices.get("gloss", 2)

            if len(parts) <= max(lemma_idx, sense_id_idx, gloss_idx):
                result.add_error(str(path), f"Line {line_num}: Not enough columns")
                continue

            lemma = parts[lemma_idx].strip()
            sense_id = parts[sense_id_idx].strip()
            gloss = parts[gloss_idx].strip()

            # Validate required values
            if not lemma:
                result.add_error(str(path), f"Line {line_num}: Empty lemma")
            if not sense_id:
                result.add_error(str(path), f"Line {line_num}: Empty sense_id")
            if not gloss:
                result.add_error(str(path), f"Line {line_num}: Empty gloss")

            # Check for duplicates
            full_sense_id = f"{lemma}:{sense_id}"
            if full_sense_id in seen_sense_ids:
                result.add_warning(
                    str(path), f"Line {line_num}: Duplicate sense_id: {full_sense_id}"
                )
            seen_sense_ids.add(full_sense_id)

            result.sense_count += 1

        return result

    def _validate_json_senses(
        self, path: Path, source_id: str
    ) -> SensePackValidationResult:
        """Validate JSON sense data file."""
        result = SensePackValidationResult()

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            result.add_error(str(path), f"Invalid JSON: {e}")
            return result

        if not isinstance(data, list):
            result.add_error(str(path), "JSON must be an array of sense entries")
            return result

        seen_sense_ids: set[str] = set()
        for i, entry in enumerate(data):
            if not isinstance(entry, dict):
                result.add_error(str(path), f"Entry {i}: Must be an object")
                continue

            # Check required fields
            for req_field in REQUIRED_SENSE_FIELDS:
                if req_field not in entry or not entry[req_field]:
                    result.add_error(
                        str(path), f"Entry {i}: Missing required field: {req_field}"
                    )

            # Check for duplicates
            lemma = entry.get("lemma", "")
            sense_id = entry.get("sense_id", "")
            full_sense_id = f"{lemma}:{sense_id}"
            if full_sense_id in seen_sense_ids:
                result.add_warning(
                    str(path), f"Entry {i}: Duplicate sense_id: {full_sense_id}"
                )
            seen_sense_ids.add(full_sense_id)

            result.sense_count += 1

        return result


class SensePackLoader:
    """Loads sense data from a sense pack.

    Usage:
        loader = SensePackLoader(pack_path)
        if loader.load():
            for sense in loader.iter_senses():
                print(sense.lemma, sense.gloss)
    """

    def __init__(self, pack_path: Path | str):
        """Initialize loader.

        Args:
            pack_path: Path to sense pack directory
        """
        self._path = Path(pack_path)
        self._manifest: SensePackManifest | None = None
        self._senses: list[SenseEntry] = []
        self._loaded = False

    @property
    def manifest(self) -> SensePackManifest | None:
        """Get manifest (None if not loaded)."""
        return self._manifest

    @property
    def is_loaded(self) -> bool:
        """Check if pack is loaded."""
        return self._loaded

    def load(self) -> bool:
        """Load the sense pack.

        Returns:
            True if loaded successfully
        """
        manifest_path = self._path / "manifest.json"
        if not manifest_path.exists():
            return False

        # Load manifest
        with open(manifest_path, encoding="utf-8") as f:
            manifest_data = json.load(f)
        self._manifest = SensePackManifest.from_dict(manifest_data)

        # Load sense data
        data_path = self._path / self._manifest.data_file
        if not data_path.exists():
            return False

        if self._manifest.data_file.endswith(".tsv"):
            self._load_tsv_senses(data_path)
        elif self._manifest.data_file.endswith(".json"):
            self._load_json_senses(data_path)
        else:
            return False

        self._loaded = True
        return True

    def _load_tsv_senses(self, path: Path) -> None:
        """Load senses from TSV file."""
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            return

        # Parse header
        header = lines[0].strip().split("\t")
        header_lower = [h.lower() for h in header]
        col_indices = {h: i for i, h in enumerate(header_lower)}

        source_id = self._manifest.source_id if self._manifest else ""

        for line in lines[1:]:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split("\t")

            # Get values with safe indexing
            def get_col(name: str, default: str = "") -> str:
                idx = col_indices.get(name)
                if idx is not None and idx < len(parts):
                    return parts[idx].strip()
                return default

            lemma = get_col("lemma")
            sense_id = get_col("sense_id")
            gloss = get_col("gloss")

            if not lemma or not sense_id or not gloss:
                continue

            # Parse weight
            weight_str = get_col("weight", "1.0")
            try:
                weight = float(weight_str)
            except ValueError:
                weight = 1.0

            self._senses.append(
                SenseEntry(
                    lemma=lemma,
                    sense_id=sense_id,
                    gloss=gloss,
                    definition=get_col("definition"),
                    domain=get_col("domain"),
                    weight=weight,
                    source_id=source_id,
                )
            )

    def _load_json_senses(self, path: Path) -> None:
        """Load senses from JSON file."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        source_id = self._manifest.source_id if self._manifest else ""

        for entry in data:
            if not isinstance(entry, dict):
                continue

            lemma = entry.get("lemma", "")
            sense_id = entry.get("sense_id", "")
            gloss = entry.get("gloss", "")

            if not lemma or not sense_id or not gloss:
                continue

            self._senses.append(
                SenseEntry(
                    lemma=lemma,
                    sense_id=sense_id,
                    gloss=gloss,
                    definition=entry.get("definition", ""),
                    domain=entry.get("domain", ""),
                    weight=entry.get("weight", 1.0),
                    source_id=source_id,
                )
            )

    def iter_senses(self) -> Iterator[SenseEntry]:
        """Iterate over loaded senses.

        Yields:
            SenseEntry objects
        """
        if not self._loaded:
            self.load()
        yield from self._senses

    def get_senses_for_lemma(self, lemma: str) -> list[SenseEntry]:
        """Get all senses for a lemma.

        Args:
            lemma: Greek lemma

        Returns:
            List of SenseEntry objects
        """
        if not self._loaded:
            self.load()
        return [s for s in self._senses if s.lemma == lemma]

    def __len__(self) -> int:
        """Number of senses in pack."""
        if not self._loaded:
            self.load()
        return len(self._senses)


def validate_sense_pack(
    pack_path: Path | str,
    strict: bool = False,
) -> SensePackValidationResult:
    """Convenience function to validate a sense pack.

    Args:
        pack_path: Path to sense pack directory
        strict: Treat warnings as errors

    Returns:
        SensePackValidationResult
    """
    validator = SensePackValidator(pack_path, strict=strict)
    return validator.validate()
