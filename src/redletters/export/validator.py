"""Output validation for schema contracts (v0.10.0).

Provides deterministic validation of generated outputs against JSON schemas.
No network calls, stable error messages.

Usage:
    validator = OutputValidator()
    result = validator.validate_file("apparatus.jsonl", artifact_type="apparatus")
    if not result.valid:
        print(result.errors)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from redletters.export.schema_versions import (
    EXPORT_SCHEMA_VERSION,
    CITATIONS_SCHEMA_VERSION,
    QUOTE_SCHEMA_VERSION,
    DOSSIER_SCHEMA_VERSION,
    RUNLOG_SCHEMA_VERSION,
)


# Artifact type to schema version mapping
ARTIFACT_SCHEMA_VERSIONS = {
    "apparatus": EXPORT_SCHEMA_VERSION,
    "translation": EXPORT_SCHEMA_VERSION,
    "snapshot": EXPORT_SCHEMA_VERSION,
    "citations": CITATIONS_SCHEMA_VERSION,
    "quote": QUOTE_SCHEMA_VERSION,
    "dossier": DOSSIER_SCHEMA_VERSION,
    "runlog": RUNLOG_SCHEMA_VERSION,
}

# Required fields for each artifact type (minimal structural validation)
REQUIRED_FIELDS = {
    "apparatus": ["variant_unit_id", "verse_id", "readings", "schema_version"],
    "translation": ["verse_id", "tokens", "confidence_summary", "schema_version"],
    "snapshot": ["tool_version", "schema_version", "packs", "export_hashes"],
    "citations": ["schema_version", "entries", "content_hash"],
    "quote": [
        "reference",
        "mode",
        "gate_status",
        "generated_at",
        "schema_version",
    ],
    "dossier": [
        "reference",
        "scope",
        "spine",
        "variants",
        "provenance",
        "schema_version",
    ],
    "runlog": [
        "schema_version",
        "tool_version",
        "command",
        "started_at",
        "completed_at",
        "reference",
        "mode",
        "files_created",
        "validations",
        "success",
    ],
}


@dataclass
class ValidationResult:
    """Result of output validation."""

    valid: bool
    artifact_type: str
    file_path: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    records_checked: int = 0
    schema_version_found: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "artifact_type": self.artifact_type,
            "file_path": self.file_path,
            "errors": self.errors,
            "warnings": self.warnings,
            "records_checked": self.records_checked,
            "schema_version_found": self.schema_version_found,
        }


def detect_artifact_type(file_path: Path, content: Any = None) -> str | None:
    """Auto-detect artifact type from file extension and content.

    Args:
        file_path: Path to the file
        content: Optional parsed content (dict or list)

    Returns:
        Artifact type string or None if cannot determine
    """
    name = file_path.name.lower()
    suffix = file_path.suffix.lower()

    # Check filename patterns first
    if "apparatus" in name:
        return "apparatus"
    if "translation" in name:
        return "translation"
    if "snapshot" in name:
        return "snapshot"
    if "citation" in name:
        return "citations"
    if "quote" in name:
        return "quote"
    if "dossier" in name:
        return "dossier"
    if "run_log" in name or "runlog" in name:
        return "runlog"

    # Check content structure for JSON files
    if content and isinstance(content, dict):
        # Runlog has command and validations
        if (
            "command" in content
            and "validations" in content
            and "files_created" in content
        ):
            return "runlog"
        # Snapshot has unique structure
        if "tool_version" in content and "export_hashes" in content:
            return "snapshot"
        # Citations have entries array
        if "entries" in content and "content_hash" in content:
            return "citations"
        # Quote has gate_status
        if "gate_status" in content and "reference" in content:
            return "quote"
        # Dossier has variants and spine
        if "variants" in content and "spine" in content:
            return "dossier"
        # Apparatus record has variant_unit_id
        if "variant_unit_id" in content:
            return "apparatus"
        # Translation record has tokens and verse_id
        if "tokens" in content and "verse_id" in content:
            return "translation"

    # JSONL files - need to check first line
    if suffix == ".jsonl":
        return None  # Caller should check first record

    return None


def validate_record(
    record: dict, artifact_type: str, line_number: int | None = None
) -> list[str]:
    """Validate a single record against required fields.

    Args:
        record: Parsed JSON record
        artifact_type: Type of artifact
        line_number: Optional line number for JSONL files

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    required = REQUIRED_FIELDS.get(artifact_type, [])
    prefix = f"Line {line_number}: " if line_number else ""

    # Check required fields
    for required_field in required:
        if required_field not in record:
            errors.append(f"{prefix}Missing required field: {required_field}")

    # Validate schema_version format if present
    schema_version = record.get("schema_version")
    if schema_version:
        if not isinstance(schema_version, str):
            errors.append(f"{prefix}schema_version must be a string")
        elif not all(part.isdigit() for part in schema_version.split(".") if part):
            errors.append(
                f"{prefix}schema_version must be semver format (got: {schema_version})"
            )

    # Artifact-specific validation
    if artifact_type == "apparatus":
        readings = record.get("readings", [])
        if not isinstance(readings, list) or len(readings) == 0:
            errors.append(f"{prefix}readings must be a non-empty array")

    elif artifact_type == "translation":
        tokens = record.get("tokens", [])
        if not isinstance(tokens, list):
            errors.append(f"{prefix}tokens must be an array")

    elif artifact_type == "snapshot":
        packs = record.get("packs", [])
        if not isinstance(packs, list):
            errors.append(f"{prefix}packs must be an array")
        export_hashes = record.get("export_hashes", {})
        if not isinstance(export_hashes, dict):
            errors.append(f"{prefix}export_hashes must be an object")

    elif artifact_type == "citations":
        entries = record.get("entries", [])
        if not isinstance(entries, list):
            errors.append(f"{prefix}entries must be an array")

    elif artifact_type == "quote":
        gate_status = record.get("gate_status", {})
        if not isinstance(gate_status, dict):
            errors.append(f"{prefix}gate_status must be an object")
        if "gates_cleared" not in gate_status:
            errors.append(f"{prefix}gate_status missing gates_cleared field")

    elif artifact_type == "dossier":
        variants = record.get("variants", [])
        if not isinstance(variants, list):
            errors.append(f"{prefix}variants must be an array")
        spine = record.get("spine", {})
        if not isinstance(spine, dict):
            errors.append(f"{prefix}spine must be an object")

    elif artifact_type == "runlog":
        command = record.get("command", {})
        if not isinstance(command, dict):
            errors.append(f"{prefix}command must be an object")
        else:
            if "reference" not in command:
                errors.append(f"{prefix}command missing reference field")
            if "output_dir" not in command:
                errors.append(f"{prefix}command missing output_dir field")
            if "mode" not in command:
                errors.append(f"{prefix}command missing mode field")
        files_created = record.get("files_created", [])
        if not isinstance(files_created, list):
            errors.append(f"{prefix}files_created must be an array")
        validations = record.get("validations", [])
        if not isinstance(validations, list):
            errors.append(f"{prefix}validations must be an array")

    return errors


class OutputValidator:
    """Validates generated output files against schema contracts.

    Provides deterministic, offline validation with stable error messages.
    """

    def __init__(self):
        """Initialize validator."""
        pass

    def validate_file(
        self,
        file_path: str | Path,
        artifact_type: str | None = None,
    ) -> ValidationResult:
        """Validate an output file.

        Args:
            file_path: Path to the file to validate
            artifact_type: Type of artifact (auto-detect if not specified)

        Returns:
            ValidationResult with validation status and any errors
        """
        file_path = Path(file_path)

        # Check file exists
        if not file_path.exists():
            return ValidationResult(
                valid=False,
                artifact_type=artifact_type or "unknown",
                file_path=str(file_path),
                errors=[f"File not found: {file_path}"],
            )

        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            return ValidationResult(
                valid=False,
                artifact_type=artifact_type or "unknown",
                file_path=str(file_path),
                errors=[f"Failed to read file: {e}"],
            )

        # Handle JSONL vs JSON
        if file_path.suffix.lower() == ".jsonl":
            return self._validate_jsonl(file_path, content, artifact_type)
        else:
            return self._validate_json(file_path, content, artifact_type)

    def _validate_json(
        self,
        file_path: Path,
        content: str,
        artifact_type: str | None,
    ) -> ValidationResult:
        """Validate a JSON file."""
        errors = []
        warnings = []

        # Parse JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return ValidationResult(
                valid=False,
                artifact_type=artifact_type or "unknown",
                file_path=str(file_path),
                errors=[f"Invalid JSON: {e}"],
            )

        # Auto-detect type if needed
        if artifact_type is None:
            artifact_type = detect_artifact_type(file_path, data)
            if artifact_type is None:
                return ValidationResult(
                    valid=False,
                    artifact_type="unknown",
                    file_path=str(file_path),
                    errors=[
                        "Could not auto-detect artifact type. Use --type to specify."
                    ],
                )

        # Validate required fields
        record_errors = validate_record(data, artifact_type)
        errors.extend(record_errors)

        # Check schema version
        schema_version = data.get("schema_version", "")
        expected_version = ARTIFACT_SCHEMA_VERSIONS.get(artifact_type, "")
        if schema_version and expected_version and schema_version != expected_version:
            warnings.append(
                f"Schema version mismatch: found={schema_version}, expected={expected_version}"
            )

        return ValidationResult(
            valid=len(errors) == 0,
            artifact_type=artifact_type,
            file_path=str(file_path),
            errors=errors,
            warnings=warnings,
            records_checked=1,
            schema_version_found=schema_version,
        )

    def _validate_jsonl(
        self,
        file_path: Path,
        content: str,
        artifact_type: str | None,
    ) -> ValidationResult:
        """Validate a JSONL file (line-by-line JSON)."""
        errors = []
        warnings = []
        records_checked = 0
        schema_version_found = ""

        lines = content.strip().split("\n")
        if not lines or (len(lines) == 1 and not lines[0].strip()):
            return ValidationResult(
                valid=False,
                artifact_type=artifact_type or "unknown",
                file_path=str(file_path),
                errors=["Empty JSONL file"],
            )

        # Process each line
        for i, line in enumerate(lines, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"Line {i}: Invalid JSON: {e}")
                continue

            records_checked += 1

            # Auto-detect type from first record if needed
            if artifact_type is None and records_checked == 1:
                artifact_type = detect_artifact_type(file_path, record)
                if artifact_type is None:
                    return ValidationResult(
                        valid=False,
                        artifact_type="unknown",
                        file_path=str(file_path),
                        errors=[
                            "Could not auto-detect artifact type from first record. Use --type to specify."
                        ],
                    )

            # Validate record
            record_errors = validate_record(record, artifact_type, line_number=i)
            errors.extend(record_errors)

            # Capture schema version from first record
            if records_checked == 1:
                schema_version_found = record.get("schema_version", "")

        # Check schema version
        expected_version = ARTIFACT_SCHEMA_VERSIONS.get(artifact_type, "")
        if (
            schema_version_found
            and expected_version
            and schema_version_found != expected_version
        ):
            warnings.append(
                f"Schema version mismatch: found={schema_version_found}, expected={expected_version}"
            )

        return ValidationResult(
            valid=len(errors) == 0,
            artifact_type=artifact_type or "unknown",
            file_path=str(file_path),
            errors=errors,
            warnings=warnings,
            records_checked=records_checked,
            schema_version_found=schema_version_found,
        )


def validate_output(
    file_path: str | Path,
    artifact_type: str | None = None,
) -> ValidationResult:
    """Convenience function to validate an output file.

    Args:
        file_path: Path to the file to validate
        artifact_type: Type of artifact (auto-detect if not specified)

    Returns:
        ValidationResult
    """
    validator = OutputValidator()
    return validator.validate_file(file_path, artifact_type)
