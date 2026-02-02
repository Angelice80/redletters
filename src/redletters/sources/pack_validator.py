"""Pack validation for Pack Spec v1.1.

Sprint 8: B1 - Validates pack manifest and data files against spec.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


# Valid witness types per Pack Spec v1.1
VALID_WITNESS_TYPES = {"edition", "manuscript", "papyrus", "version", "father"}

# Required manifest fields for v1.1
REQUIRED_FIELDS_V11 = {"name", "license", "siglum", "witness_type", "coverage"}

# Required manifest fields for v1.0 (backward compat)
REQUIRED_FIELDS_V10 = {"name", "license"}

# verse_id pattern: Book.Chapter.Verse
VERSE_ID_PATTERN = re.compile(r"^[A-Za-z0-9]+\.(\d+)\.(\d+)$")


@dataclass
class ValidationError:
    """A single validation error."""

    path: str
    message: str
    severity: str = "error"  # error, warning


@dataclass
class ValidationResult:
    """Result of pack validation."""

    valid: bool = True
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    manifest_version: str = "unknown"
    verse_count: int = 0
    books_found: list[str] = field(default_factory=list)

    def add_error(self, path: str, message: str) -> None:
        """Add an error."""
        self.errors.append(ValidationError(path, message, "error"))
        self.valid = False

    def add_warning(self, path: str, message: str) -> None:
        """Add a warning."""
        self.warnings.append(ValidationError(path, message, "warning"))

    def merge(self, other: "ValidationResult") -> None:
        """Merge another result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.valid:
            self.valid = False
        self.verse_count += other.verse_count


class PackValidator:
    """Validates packs against Pack Spec v1.1.

    Usage:
        validator = PackValidator(pack_path)
        result = validator.validate()

        if not result.valid:
            for err in result.errors:
                print(f"ERROR: {err.path}: {err.message}")
    """

    def __init__(self, pack_path: Path | str, strict: bool = False):
        """Initialize validator.

        Args:
            pack_path: Path to pack directory
            strict: If True, treat warnings as errors
        """
        self._path = Path(pack_path)
        self._strict = strict
        self._manifest: dict | None = None

    def validate(self, expected_version: str = "1.1") -> ValidationResult:
        """Run full validation.

        Args:
            expected_version: Expected format_version (default "1.1")

        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()

        # Check pack directory exists
        if not self._path.exists():
            result.add_error(str(self._path), "Pack directory does not exist")
            return result

        if not self._path.is_dir():
            result.add_error(str(self._path), "Pack path is not a directory")
            return result

        # Validate manifest
        manifest_result = self._validate_manifest(expected_version)
        result.merge(manifest_result)

        if not result.valid:
            return result

        # Validate data files
        data_result = self._validate_data_files()
        result.merge(data_result)

        # In strict mode, warnings become errors
        if self._strict:
            for warning in result.warnings:
                result.add_error(warning.path, f"[strict] {warning.message}")

        return result

    def _validate_manifest(self, expected_version: str) -> ValidationResult:
        """Validate manifest.json."""
        result = ValidationResult()
        manifest_path = self._path / "manifest.json"

        if not manifest_path.exists():
            result.add_error(str(manifest_path), "manifest.json not found")
            return result

        try:
            with open(manifest_path, encoding="utf-8") as f:
                self._manifest = json.load(f)
        except json.JSONDecodeError as e:
            result.add_error(str(manifest_path), f"Invalid JSON: {e}")
            return result

        # Get format version
        format_version = self._manifest.get("format_version", "1.0")
        result.manifest_version = format_version

        # Check version expectation
        if expected_version == "1.1" and format_version != "1.1":
            result.add_warning(
                str(manifest_path),
                f"format_version is '{format_version}', expected '1.1'",
            )

        # Validate required fields based on version
        if format_version == "1.1":
            required = REQUIRED_FIELDS_V11
        else:
            required = REQUIRED_FIELDS_V10

        for field_name in required:
            if field_name not in self._manifest:
                # Check for legacy aliases
                if field_name == "siglum" and "witness_siglum" in self._manifest:
                    continue
                if field_name == "coverage" and "books" in self._manifest:
                    continue
                result.add_error(
                    str(manifest_path), f"Missing required field: {field_name}"
                )

        # Validate id/pack_id
        pack_id = self._manifest.get("id", self._manifest.get("pack_id"))
        if not pack_id:
            result.add_error(str(manifest_path), "Missing pack id (id or pack_id)")
        elif not re.match(r"^[a-z0-9-]+$", pack_id):
            result.add_warning(
                str(manifest_path),
                f"pack_id '{pack_id}' should be lowercase slug format",
            )

        # Validate witness_type
        witness_type = self._manifest.get("witness_type", "version")
        if witness_type not in VALID_WITNESS_TYPES:
            result.add_error(
                str(manifest_path),
                f"Invalid witness_type: '{witness_type}'. "
                f"Must be one of: {', '.join(VALID_WITNESS_TYPES)}",
            )

        # Validate coverage/books
        coverage = self._manifest.get("coverage", self._manifest.get("books", []))
        if not coverage:
            result.add_error(str(manifest_path), "coverage (or books) list is empty")
        else:
            result.books_found = list(coverage)

        # Validate century_range format
        century_range = self._manifest.get(
            "century_range", self._manifest.get("date_range")
        )
        if century_range:
            if not isinstance(century_range, list) or len(century_range) != 2:
                result.add_error(
                    str(manifest_path),
                    "century_range must be [earliest, latest] array",
                )
            elif not all(isinstance(c, int) for c in century_range):
                result.add_error(
                    str(manifest_path), "century_range values must be integers"
                )
            elif century_range[0] > century_range[1]:
                result.add_error(
                    str(manifest_path),
                    "century_range[0] must be <= century_range[1]",
                )

        return result

    def _validate_data_files(self) -> ValidationResult:
        """Validate TSV data files."""
        result = ValidationResult()

        if not self._manifest:
            return result

        coverage = self._manifest.get("coverage", self._manifest.get("books", []))

        for book in coverage:
            book_path = self._path / book
            if not book_path.exists():
                result.add_error(str(book_path), f"Book directory not found: {book}")
                continue

            # Find chapter files
            chapter_files = sorted(book_path.glob("chapter_*.tsv"))
            if not chapter_files:
                result.add_error(
                    str(book_path), f"No chapter TSV files found for {book}"
                )
                continue

            for chapter_file in chapter_files:
                chapter_result = self._validate_chapter_file(chapter_file, book)
                result.merge(chapter_result)

        return result

    def _validate_chapter_file(self, path: Path, book: str) -> ValidationResult:
        """Validate a single chapter TSV file."""
        result = ValidationResult()

        # Extract expected chapter from filename
        match = re.match(r"chapter_(\d+)\.tsv", path.name)
        if not match:
            result.add_error(str(path), "Invalid chapter filename format")
            return result

        expected_chapter = int(match.group(1))

        try:
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            result.add_error(str(path), f"Cannot read file: {e}")
            return result

        if not lines:
            result.add_error(str(path), "File is empty")
            return result

        # Check for header row (v1.1 requirement)
        first_line = lines[0].strip()
        has_header = first_line.startswith("verse_id")

        if not has_header:
            # v1.0 packs may not have headers - warn but allow
            result.add_warning(
                str(path), "No header row (should start with 'verse_id')"
            )
            data_lines = lines
        else:
            # Validate header columns
            headers = first_line.split("\t")
            if headers[0] != "verse_id":
                result.add_error(str(path), "First column must be 'verse_id'")
            if len(headers) < 2 or headers[1] != "text":
                result.add_warning(str(path), "Second column should be 'text'")
            data_lines = lines[1:]

        # Validate data rows
        seen_verse_ids: set[str] = set()
        last_verse_num = 0

        for line_num, line in enumerate(data_lines, start=2 if has_header else 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split("\t", 1)
            if len(parts) < 2:
                result.add_error(str(path), f"Line {line_num}: Missing tab separator")
                continue

            verse_id = parts[0]

            # Validate verse_id format
            id_match = VERSE_ID_PATTERN.match(verse_id)
            if not id_match:
                result.add_error(
                    str(path),
                    f"Line {line_num}: Invalid verse_id format: '{verse_id}'",
                )
                continue

            # Check book prefix
            if not verse_id.startswith(f"{book}."):
                result.add_error(
                    str(path),
                    f"Line {line_num}: verse_id '{verse_id}' does not match book '{book}'",
                )

            # Check chapter matches filename
            chapter_num = int(id_match.group(1))
            if chapter_num != expected_chapter:
                result.add_error(
                    str(path),
                    f"Line {line_num}: verse in chapter {chapter_num} "
                    f"but file is chapter_{expected_chapter}.tsv",
                )

            # Check for duplicates
            if verse_id in seen_verse_ids:
                result.add_error(
                    str(path), f"Line {line_num}: Duplicate verse_id: {verse_id}"
                )
            seen_verse_ids.add(verse_id)

            # Check verse ordering (should be ascending)
            verse_num = int(id_match.group(2))
            if verse_num <= last_verse_num:
                result.add_warning(
                    str(path),
                    f"Line {line_num}: Verse {verse_num} not in ascending order "
                    f"(after verse {last_verse_num})",
                )
            last_verse_num = verse_num

            result.verse_count += 1

        return result


def validate_pack(
    pack_path: Path | str,
    strict: bool = False,
    expected_version: str = "1.1",
) -> ValidationResult:
    """Convenience function to validate a pack.

    Args:
        pack_path: Path to pack directory
        strict: Treat warnings as errors
        expected_version: Expected format_version

    Returns:
        ValidationResult
    """
    validator = PackValidator(pack_path, strict=strict)
    return validator.validate(expected_version=expected_version)
