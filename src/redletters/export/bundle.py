"""Research bundle creation and verification (v0.12.0).

Provides deterministic bundle packaging for shareable scholarly research:
- Lockfile (required) - pack integrity
- Snapshot (required) - reproducibility state
- Output artifacts (required) - apparatus, translation, etc.
- Citations (optional) - bibliography
- Schemas (optional) - JSON schema files for validation

Design principles:
- Deterministic manifest (sorted artifact order, canonical JSON)
- Full integrity verification (SHA-256 hashes for all files)
- Reuses existing validators (snapshot verify, output validate, lockfile sync)
"""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from redletters.export.identifiers import canonical_json, file_hash
from redletters.export.validator import (
    detect_artifact_type,
    validate_output,
)

# Current versions
TOOL_VERSION = "0.12.0"
BUNDLE_SCHEMA_VERSION = "1.0.0"

# Artifact type ordering for deterministic manifest
ARTIFACT_TYPE_ORDER = [
    "apparatus",
    "citations",
    "dossier",
    "lockfile",
    "quote",
    "schema",
    "snapshot",
    "translation",
]


@dataclass
class ArtifactEntry:
    """Entry for a single artifact in the bundle manifest."""

    path: str
    artifact_type: str
    sha256: str
    schema_version: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict."""
        result = {
            "path": self.path,
            "artifact_type": self.artifact_type,
            "sha256": self.sha256,
        }
        if self.schema_version:
            result["schema_version"] = self.schema_version
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "ArtifactEntry":
        """Deserialize from dict."""
        return cls(
            path=data["path"],
            artifact_type=data["artifact_type"],
            sha256=data["sha256"],
            schema_version=data.get("schema_version", ""),
        )


@dataclass
class BundleManifest:
    """Bundle manifest with deterministic serialization."""

    schema_version: str
    tool_version: str
    created_utc: str
    lockfile_hash: str
    snapshot_hash: str
    artifacts: list[ArtifactEntry] = field(default_factory=list)
    content_hash: str = ""
    schemas_included: bool = False
    notes: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict."""
        result = {
            "schema_version": self.schema_version,
            "tool_version": self.tool_version,
            "created_utc": self.created_utc,
            "lockfile_hash": self.lockfile_hash,
            "snapshot_hash": self.snapshot_hash,
            "artifacts": [a.to_dict() for a in self.artifacts],
        }
        if self.content_hash:
            result["content_hash"] = self.content_hash
        if self.schemas_included:
            result["schemas_included"] = self.schemas_included
        if self.notes:
            result["notes"] = self.notes
        return result

    def to_json(self, pretty: bool = True) -> str:
        """Serialize to JSON string."""
        if pretty:
            return json.dumps(
                self.to_dict(),
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
        return canonical_json(self.to_dict())

    def compute_content_hash(self) -> str:
        """Compute deterministic hash of all artifact hashes.

        Concatenates artifact hashes in sorted order and hashes the result.
        This provides a single fingerprint for the entire bundle content.
        """
        # Sort artifacts by type then path for determinism
        sorted_artifacts = sorted(
            self.artifacts,
            key=lambda a: (
                ARTIFACT_TYPE_ORDER.index(a.artifact_type)
                if a.artifact_type in ARTIFACT_TYPE_ORDER
                else 999,
                a.path,
            ),
        )
        # Concatenate all hashes
        hash_concat = "".join(a.sha256 for a in sorted_artifacts)
        # Hash the concatenation
        return hashlib.sha256(hash_concat.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: dict) -> "BundleManifest":
        """Deserialize from dict."""
        return cls(
            schema_version=data["schema_version"],
            tool_version=data["tool_version"],
            created_utc=data["created_utc"],
            lockfile_hash=data["lockfile_hash"],
            snapshot_hash=data["snapshot_hash"],
            artifacts=[ArtifactEntry.from_dict(a) for a in data.get("artifacts", [])],
            content_hash=data.get("content_hash", ""),
            schemas_included=data.get("schemas_included", False),
            notes=data.get("notes", ""),
        )

    @classmethod
    def load(cls, path: Path) -> "BundleManifest":
        """Load manifest from JSON file."""
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    def save(self, path: Path) -> None:
        """Save manifest to JSON file."""
        path.write_text(self.to_json(pretty=True), encoding="utf-8")


def _detect_type_from_path(filepath: Path) -> str:
    """Detect artifact type from file path and content."""
    name = filepath.name.lower()

    # Check for specific known files
    if name == "lockfile.json":
        return "lockfile"
    if name == "snapshot.json":
        return "snapshot"
    if name.endswith(".schema.json"):
        return "schema"

    # Use existing detector
    detected = detect_artifact_type(filepath)
    if detected:
        return detected

    # Fallback to extension-based detection
    if filepath.suffix == ".jsonl":
        # Try to read first line to detect
        try:
            first_line = filepath.read_text(encoding="utf-8").split("\n")[0]
            record = json.loads(first_line)
            detected = detect_artifact_type(filepath, record)
            if detected:
                return detected
        except Exception:
            pass

    return "unknown"


def _get_schema_version_from_file(filepath: Path, artifact_type: str) -> str:
    """Extract schema version from file content."""
    if artifact_type == "schema":
        return ""

    try:
        content = filepath.read_text(encoding="utf-8")
        if filepath.suffix == ".jsonl":
            # Get from first line
            first_line = content.split("\n")[0]
            data = json.loads(first_line)
        else:
            data = json.loads(content)

        return data.get("schema_version", "")
    except Exception:
        return ""


@dataclass
class BundleCreateResult:
    """Result of bundle creation."""

    success: bool
    bundle_path: Path | None = None
    manifest: BundleManifest | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class BundleCreator:
    """Creates deterministic research bundles."""

    def __init__(
        self,
        schema_dir: Path | None = None,
    ):
        """Initialize creator.

        Args:
            schema_dir: Directory containing JSON schema files (optional)
        """
        self.schema_dir = (
            schema_dir
            or Path(__file__).parent.parent.parent.parent / "docs" / "schemas"
        )

    def create(
        self,
        output_dir: Path,
        lockfile_path: Path,
        snapshot_path: Path,
        input_paths: list[Path],
        include_schemas: bool = False,
        create_zip: bool = False,
        notes: str = "",
    ) -> BundleCreateResult:
        """Create a research bundle.

        Args:
            output_dir: Output directory for the bundle
            lockfile_path: Path to lockfile.json
            snapshot_path: Path to snapshot.json
            input_paths: List of artifact file paths to include
            include_schemas: Whether to include JSON schema files
            create_zip: Whether to also create a zip archive
            notes: Optional notes to include in manifest

        Returns:
            BundleCreateResult with success status and details
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Validate required files exist
        if not lockfile_path.exists():
            errors.append(f"Lockfile not found: {lockfile_path}")
        if not snapshot_path.exists():
            errors.append(f"Snapshot not found: {snapshot_path}")

        # Validate input files
        valid_inputs: list[Path] = []
        for p in input_paths:
            if not p.exists():
                errors.append(f"Input file not found: {p}")
            else:
                valid_inputs.append(p)

        if not valid_inputs:
            errors.append("No valid input artifacts provided")

        if errors:
            return BundleCreateResult(success=False, errors=errors)

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build artifact list
        artifacts: list[ArtifactEntry] = []

        # Add lockfile
        lockfile_dest = output_dir / "lockfile.json"
        shutil.copy2(lockfile_path, lockfile_dest)
        lockfile_hash = file_hash(str(lockfile_dest))
        artifacts.append(
            ArtifactEntry(
                path="lockfile.json",
                artifact_type="lockfile",
                sha256=lockfile_hash,
                schema_version="1.0.0",
            )
        )

        # Add snapshot
        snapshot_dest = output_dir / "snapshot.json"
        shutil.copy2(snapshot_path, snapshot_dest)
        snapshot_hash = file_hash(str(snapshot_dest))
        artifacts.append(
            ArtifactEntry(
                path="snapshot.json",
                artifact_type="snapshot",
                sha256=snapshot_hash,
                schema_version=_get_schema_version_from_file(snapshot_dest, "snapshot"),
            )
        )

        # Add input artifacts
        for input_path in valid_inputs:
            # Detect artifact type
            artifact_type = _detect_type_from_path(input_path)
            if artifact_type == "unknown":
                warnings.append(f"Could not detect type for: {input_path.name}")
                artifact_type = "unknown"

            # Copy file to bundle
            dest_path = output_dir / input_path.name
            shutil.copy2(input_path, dest_path)

            # Compute hash and get schema version
            artifacts.append(
                ArtifactEntry(
                    path=input_path.name,
                    artifact_type=artifact_type,
                    sha256=file_hash(str(dest_path)),
                    schema_version=_get_schema_version_from_file(
                        dest_path, artifact_type
                    ),
                )
            )

        # Optionally add schemas
        if include_schemas and self.schema_dir.exists():
            schemas_dir = output_dir / "schemas"
            schemas_dir.mkdir(exist_ok=True)

            for schema_file in sorted(self.schema_dir.glob("*.schema.json")):
                dest_path = schemas_dir / schema_file.name
                shutil.copy2(schema_file, dest_path)
                artifacts.append(
                    ArtifactEntry(
                        path=f"schemas/{schema_file.name}",
                        artifact_type="schema",
                        sha256=file_hash(str(dest_path)),
                    )
                )

        # Sort artifacts by type then path for determinism
        artifacts.sort(
            key=lambda a: (
                ARTIFACT_TYPE_ORDER.index(a.artifact_type)
                if a.artifact_type in ARTIFACT_TYPE_ORDER
                else 999,
                a.path,
            )
        )

        # Create manifest
        manifest = BundleManifest(
            schema_version=BUNDLE_SCHEMA_VERSION,
            tool_version=TOOL_VERSION,
            created_utc=datetime.now(timezone.utc).isoformat(),
            lockfile_hash=lockfile_hash,
            snapshot_hash=snapshot_hash,
            artifacts=artifacts,
            schemas_included=include_schemas,
            notes=notes,
        )

        # Compute content hash
        manifest.content_hash = manifest.compute_content_hash()

        # Save manifest
        manifest_path = output_dir / "manifest.json"
        manifest.save(manifest_path)

        # Optionally create zip
        if create_zip:
            zip_path = output_dir.with_suffix(".zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file in sorted(output_dir.rglob("*")):
                    if file.is_file():
                        arcname = file.relative_to(output_dir)
                        zf.write(file, arcname)

        return BundleCreateResult(
            success=True,
            bundle_path=output_dir,
            manifest=manifest,
            warnings=warnings,
        )


@dataclass
class BundleVerifyResult:
    """Result of bundle verification."""

    valid: bool
    manifest: BundleManifest | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    file_checks: dict[str, dict] = field(default_factory=dict)
    snapshot_valid: bool | None = None
    outputs_valid: bool | None = None

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "file_checks": self.file_checks,
            "snapshot_valid": self.snapshot_valid,
            "outputs_valid": self.outputs_valid,
        }


class BundleVerifier:
    """Verifies research bundle integrity."""

    def __init__(self):
        """Initialize verifier."""
        pass

    def verify(
        self,
        bundle_path: Path,
        check_snapshot: bool = True,
        check_outputs: bool = True,
    ) -> BundleVerifyResult:
        """Verify a research bundle.

        Args:
            bundle_path: Path to bundle directory or zip file
            check_snapshot: Whether to verify snapshot integrity
            check_outputs: Whether to validate output files against schemas

        Returns:
            BundleVerifyResult with verification status
        """
        errors: list[str] = []
        warnings: list[str] = []
        file_checks: dict[str, dict] = {}

        # Handle zip file
        if bundle_path.suffix == ".zip":
            # Extract to temp directory
            import tempfile

            temp_dir = Path(tempfile.mkdtemp())
            with zipfile.ZipFile(bundle_path, "r") as zf:
                zf.extractall(temp_dir)
            bundle_path = temp_dir

        # Check manifest exists
        manifest_path = bundle_path / "manifest.json"
        if not manifest_path.exists():
            errors.append("manifest.json not found in bundle")
            return BundleVerifyResult(valid=False, errors=errors)

        # Load manifest
        try:
            manifest = BundleManifest.load(manifest_path)
        except Exception as e:
            errors.append(f"Failed to load manifest: {e}")
            return BundleVerifyResult(valid=False, errors=errors)

        # Verify each artifact
        for artifact in manifest.artifacts:
            artifact_path = bundle_path / artifact.path
            if not artifact_path.exists():
                errors.append(f"Missing artifact: {artifact.path}")
                file_checks[artifact.path] = {
                    "status": "missing",
                    "expected_hash": artifact.sha256,
                }
                continue

            # Compute actual hash
            actual_hash = file_hash(str(artifact_path))
            if actual_hash != artifact.sha256:
                errors.append(
                    f"Hash mismatch for {artifact.path}: "
                    f"expected={artifact.sha256[:16]}..., "
                    f"actual={actual_hash[:16]}..."
                )
                file_checks[artifact.path] = {
                    "status": "hash_mismatch",
                    "expected_hash": artifact.sha256,
                    "actual_hash": actual_hash,
                }
            else:
                file_checks[artifact.path] = {
                    "status": "ok",
                    "hash": actual_hash,
                }

        # Verify content hash
        computed_content_hash = manifest.compute_content_hash()
        if manifest.content_hash and manifest.content_hash != computed_content_hash:
            errors.append(
                f"Content hash mismatch: "
                f"manifest={manifest.content_hash[:16]}..., "
                f"computed={computed_content_hash[:16]}..."
            )

        # Verify lockfile and snapshot hashes match manifest
        lockfile_path = bundle_path / "lockfile.json"
        if lockfile_path.exists():
            actual_lockfile_hash = file_hash(str(lockfile_path))
            if actual_lockfile_hash != manifest.lockfile_hash:
                errors.append("Lockfile hash in manifest does not match actual file")

        snapshot_path = bundle_path / "snapshot.json"
        if snapshot_path.exists():
            actual_snapshot_hash = file_hash(str(snapshot_path))
            if actual_snapshot_hash != manifest.snapshot_hash:
                errors.append("Snapshot hash in manifest does not match actual file")

        # Optional: Verify snapshot integrity
        snapshot_valid = None
        if check_snapshot and snapshot_path.exists():
            from redletters.export.snapshot import SnapshotVerifier

            snapshot_verifier = SnapshotVerifier()

            # Get list of output files from manifest (exclude lockfile, snapshot, schemas)
            output_files = [
                bundle_path / a.path
                for a in manifest.artifacts
                if a.artifact_type not in ("lockfile", "snapshot", "schema")
            ]

            if output_files:
                snapshot_result = snapshot_verifier.verify(
                    snapshot_path, input_files=output_files
                )
                snapshot_valid = snapshot_result.valid
                if not snapshot_result.valid:
                    for err in snapshot_result.errors:
                        warnings.append(f"Snapshot verify: {err}")

        # Optional: Validate output files against schemas
        outputs_valid = None
        if check_outputs:
            all_outputs_valid = True
            for artifact in manifest.artifacts:
                if artifact.artifact_type in ("lockfile", "snapshot", "schema"):
                    continue

                artifact_path = bundle_path / artifact.path
                if not artifact_path.exists():
                    continue

                result = validate_output(
                    artifact_path, artifact_type=artifact.artifact_type
                )
                if not result.valid:
                    all_outputs_valid = False
                    for err in result.errors:
                        warnings.append(f"Output validation ({artifact.path}): {err}")

            outputs_valid = all_outputs_valid

        return BundleVerifyResult(
            valid=len(errors) == 0,
            manifest=manifest,
            errors=errors,
            warnings=warnings,
            file_checks=file_checks,
            snapshot_valid=snapshot_valid,
            outputs_valid=outputs_valid,
        )


def create_bundle(
    output_dir: Path,
    lockfile_path: Path,
    snapshot_path: Path,
    input_paths: list[Path],
    include_schemas: bool = False,
    create_zip: bool = False,
    notes: str = "",
) -> BundleCreateResult:
    """Convenience function to create a research bundle.

    Args:
        output_dir: Output directory for the bundle
        lockfile_path: Path to lockfile.json
        snapshot_path: Path to snapshot.json
        input_paths: List of artifact file paths to include
        include_schemas: Whether to include JSON schema files
        create_zip: Whether to also create a zip archive
        notes: Optional notes to include in manifest

    Returns:
        BundleCreateResult
    """
    creator = BundleCreator()
    return creator.create(
        output_dir=output_dir,
        lockfile_path=lockfile_path,
        snapshot_path=snapshot_path,
        input_paths=input_paths,
        include_schemas=include_schemas,
        create_zip=create_zip,
        notes=notes,
    )


def verify_bundle(
    bundle_path: Path,
    check_snapshot: bool = True,
    check_outputs: bool = True,
) -> BundleVerifyResult:
    """Convenience function to verify a research bundle.

    Args:
        bundle_path: Path to bundle directory or zip file
        check_snapshot: Whether to verify snapshot integrity
        check_outputs: Whether to validate output files against schemas

    Returns:
        BundleVerifyResult
    """
    verifier = BundleVerifier()
    return verifier.verify(
        bundle_path=bundle_path,
        check_snapshot=check_snapshot,
        check_outputs=check_outputs,
    )
