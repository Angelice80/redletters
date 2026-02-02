"""Reproducibility snapshot generation and verification.

v0.5.0: Create snapshots of export state for verification.
v0.10.0: Added schema_versions tracking for artifact validation.

Snapshot contains:
- Tool version and schema version
- Git commit (if available)
- Installed pack metadata (IDs, versions, licenses, hashes)
- Export file hashes for verification
- Schema versions used for each artifact type (v0.10.0)
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from redletters.export.identifiers import (
    canonical_json,
    file_hash,
)
from redletters.export.schema_versions import (
    EXPORT_SCHEMA_VERSION,
    CONFIDENCE_BUCKETING_VERSION,
)


# Tool version - should match pyproject.toml
TOOL_VERSION = "0.10.0"


def get_git_commit() -> str | None:
    """Get current git commit hash if in a git repo.

    Returns:
        40-character commit hash or None
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


@dataclass
class PackInfo:
    """Information about an installed pack with citation-grade metadata.

    v0.6.0: Added citation-grade fields for scholarly reproducibility.
    """

    pack_id: str
    version: str
    license: str
    pack_hash: str | None
    install_path: str | None
    # v0.6.0: Citation-grade provenance fields
    source_id: str = ""
    """Stable citation key (e.g., 'LSJ', 'BDAG')."""
    source_title: str = ""
    """Full bibliographic title."""
    edition: str = ""
    """Edition string."""
    publisher: str = ""
    """Publisher name."""
    year: int | None = None
    """Publication year."""
    license_url: str = ""
    """Link to license text."""
    role: str = ""
    """Pack role (source_text, sense_pack, etc.)."""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            "pack_id": self.pack_id,
            "version": self.version,
            "license": self.license,
            "pack_hash": self.pack_hash,
            "install_path": self.install_path,
        }
        # Add citation-grade fields if present
        if self.source_id:
            result["source_id"] = self.source_id
        if self.source_title:
            result["source_title"] = self.source_title
        if self.edition:
            result["edition"] = self.edition
        if self.publisher:
            result["publisher"] = self.publisher
        if self.year:
            result["year"] = self.year
        if self.license_url:
            result["license_url"] = self.license_url
        if self.role:
            result["role"] = self.role
        return result

    def citation_dict(self) -> dict:
        """Return minimal citation-grade provenance for receipts."""
        result = {"source_id": self.source_id or self.pack_id}
        if self.source_title:
            result["source_title"] = self.source_title
        if self.license:
            result["license"] = self.license
        if self.edition:
            result["edition"] = self.edition
        if self.publisher:
            result["publisher"] = self.publisher
        if self.year:
            result["year"] = self.year
        if self.license_url:
            result["license_url"] = self.license_url
        return result


@dataclass
class Snapshot:
    """Reproducibility snapshot.

    v0.10.0: Added schema_versions dict for tracking artifact schema versions.
    v0.11.0: Added lockfile_hash for pack integrity verification.
    """

    tool_version: str
    schema_version: str
    git_commit: str | None
    timestamp: str
    packs: list[PackInfo]
    export_hashes: dict[str, str]
    # v0.8.0: Track bucketing algorithm version
    confidence_bucketing_version: str = CONFIDENCE_BUCKETING_VERSION
    # v0.10.0: Track schema versions for all artifact types
    schema_versions: dict[str, str] = field(default_factory=dict)
    # v0.11.0: Optional lockfile hash for pack integrity
    lockfile_hash: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            "tool_version": self.tool_version,
            "schema_version": self.schema_version,
            "git_commit": self.git_commit,
            "timestamp": self.timestamp,
            "packs": [p.to_dict() for p in self.packs],
            "export_hashes": self.export_hashes,
            "confidence_bucketing_version": self.confidence_bucketing_version,
        }
        # v0.10.0: Include schema_versions if present
        if self.schema_versions:
            result["schema_versions"] = self.schema_versions
        # v0.11.0: Include lockfile_hash if present
        if self.lockfile_hash:
            result["lockfile_hash"] = self.lockfile_hash
        return result

    def to_json(self, pretty: bool = True) -> str:
        """Convert to JSON string."""
        if pretty:
            import json

            return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "Snapshot":
        """Create from dictionary."""
        packs = [
            PackInfo(
                pack_id=p["pack_id"],
                version=p["version"],
                license=p["license"],
                pack_hash=p.get("pack_hash"),
                install_path=p.get("install_path"),
                # v0.6.0: Citation-grade fields
                source_id=p.get("source_id", ""),
                source_title=p.get("source_title", ""),
                edition=p.get("edition", ""),
                publisher=p.get("publisher", ""),
                year=p.get("year"),
                license_url=p.get("license_url", ""),
                role=p.get("role", ""),
            )
            for p in data.get("packs", [])
        ]
        return cls(
            tool_version=data.get("tool_version", ""),
            schema_version=data.get("schema_version", ""),
            git_commit=data.get("git_commit"),
            timestamp=data.get("timestamp", ""),
            packs=packs,
            export_hashes=data.get("export_hashes", {}),
            confidence_bucketing_version=data.get(
                "confidence_bucketing_version", CONFIDENCE_BUCKETING_VERSION
            ),
            # v0.10.0: Load schema_versions if present
            schema_versions=data.get("schema_versions", {}),
        )


class SnapshotGenerator:
    """Generate reproducibility snapshots.

    Usage:
        generator = SnapshotGenerator(installer)
        snapshot = generator.generate(export_files=["apparatus.jsonl", "translation.jsonl"])
        snapshot.save("snapshot.json")
    """

    def __init__(self, installer: Any = None, data_root: str | None = None):
        """Initialize generator.

        Args:
            installer: SourceInstaller instance (optional)
            data_root: Override data root directory
        """
        self._installer = installer
        self._data_root = data_root

    def _get_installer(self) -> Any:
        """Get or create installer."""
        if self._installer is not None:
            return self._installer

        from redletters.sources.installer import SourceInstaller

        return SourceInstaller(data_root=self._data_root)

    def get_installed_packs(self) -> list[PackInfo]:
        """Get information about installed packs.

        v0.6.0: Includes citation-grade metadata for sense packs.

        Returns:
            List of PackInfo objects
        """
        installer = self._get_installer()
        status = installer.status()

        packs = []
        for source_id, info in status.get("sources", {}).items():
            if not info.get("installed"):
                continue

            # Get installed pack details
            installed = installer.get_installed(source_id)
            if installed:
                # Try to compute pack hash from manifest
                pack_hash = None
                manifest_path = Path(installed.install_path) / "manifest.json"
                if manifest_path.exists():
                    pack_hash = file_hash(str(manifest_path))

                packs.append(
                    PackInfo(
                        pack_id=source_id,
                        version=installed.version or "",
                        license=installed.license or "",
                        pack_hash=pack_hash,
                        install_path=str(installed.install_path),
                        role=getattr(installed, "role", ""),
                    )
                )

        # v0.6.0: Also get sense packs with full citation metadata
        try:
            sense_pack_status = installer.get_sense_pack_status()
            for sp in sense_pack_status:
                # Check if already in packs list
                if any(p.pack_id == sp["pack_id"] for p in packs):
                    # Update existing entry with citation metadata
                    for p in packs:
                        if p.pack_id == sp["pack_id"]:
                            p.source_id = sp.get("source_id", "")
                            p.source_title = sp.get("source_title", "")
                            p.edition = sp.get("edition", "")
                            p.publisher = sp.get("publisher", "")
                            p.year = sp.get("year")
                            p.license_url = sp.get("license_url", "")
                            p.role = "sense_pack"
                            break
                else:
                    # Add sense pack entry
                    packs.append(
                        PackInfo(
                            pack_id=sp["pack_id"],
                            version=sp.get("version", ""),
                            license=sp.get("license", ""),
                            pack_hash=sp.get("pack_hash"),
                            install_path=sp.get("install_path"),
                            source_id=sp.get("source_id", ""),
                            source_title=sp.get("source_title", ""),
                            edition=sp.get("edition", ""),
                            publisher=sp.get("publisher", ""),
                            year=sp.get("year"),
                            license_url=sp.get("license_url", ""),
                            role="sense_pack",
                        )
                    )
        except Exception:
            pass  # Sense pack DB not available

        return packs

    def generate(
        self,
        export_files: list[str | Path] | None = None,
        lockfile_path: str | Path | None = None,
    ) -> Snapshot:
        """Generate a snapshot.

        Args:
            export_files: List of export file paths to hash
            lockfile_path: Optional path to lockfile for integrity tracking (v0.11.0)

        Returns:
            Snapshot object
        """
        # Get git commit
        git_commit = get_git_commit()

        # Get installed packs
        packs = self.get_installed_packs()

        # Hash export files
        export_hashes = {}
        if export_files:
            for fp in export_files:
                fp = Path(fp)
                if fp.exists():
                    export_hashes[fp.name] = file_hash(str(fp))

        # v0.11.0: Compute lockfile hash if provided
        lockfile_hash = None
        if lockfile_path:
            lockfile_path = Path(lockfile_path)
            if lockfile_path.exists():
                lockfile_hash = file_hash(str(lockfile_path))

        # v0.10.0: Include all schema versions for validation/reproducibility
        from redletters.export.schema_versions import get_all_schema_versions

        return Snapshot(
            tool_version=TOOL_VERSION,
            schema_version=EXPORT_SCHEMA_VERSION,
            git_commit=git_commit,
            timestamp=datetime.now(timezone.utc).isoformat(),
            packs=packs,
            export_hashes=export_hashes,
            schema_versions=get_all_schema_versions(),
            lockfile_hash=lockfile_hash,
        )

    def save(
        self,
        output_path: str | Path,
        export_files: list[str | Path] | None = None,
        lockfile_path: str | Path | None = None,
    ) -> Snapshot:
        """Generate and save snapshot to file.

        Args:
            output_path: Output file path
            export_files: List of export file paths to hash
            lockfile_path: Optional path to lockfile for integrity tracking (v0.11.0)

        Returns:
            Snapshot object
        """
        snapshot = self.generate(export_files=export_files, lockfile_path=lockfile_path)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(snapshot.to_json(pretty=True), encoding="utf-8")

        return snapshot


@dataclass
class VerificationResult:
    """Result of snapshot verification."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    file_hashes: dict[str, dict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "file_hashes": self.file_hashes,
        }


class SnapshotVerifier:
    """Verify export files against a snapshot.

    Usage:
        verifier = SnapshotVerifier()
        result = verifier.verify(snapshot_path, input_files=["apparatus.jsonl"])
    """

    def __init__(self):
        """Initialize verifier."""
        pass

    def load_snapshot(self, snapshot_path: str | Path) -> Snapshot:
        """Load snapshot from file.

        Args:
            snapshot_path: Path to snapshot JSON file

        Returns:
            Snapshot object
        """
        import json

        snapshot_path = Path(snapshot_path)
        data = json.loads(snapshot_path.read_text(encoding="utf-8"))
        return Snapshot.from_dict(data)

    def verify(
        self,
        snapshot_path: str | Path,
        input_files: list[str | Path],
    ) -> VerificationResult:
        """Verify input files against snapshot.

        Args:
            snapshot_path: Path to snapshot JSON file
            input_files: List of export file paths to verify

        Returns:
            VerificationResult object
        """
        errors = []
        warnings = []
        file_hashes = {}

        # Load snapshot
        try:
            snapshot = self.load_snapshot(snapshot_path)
        except Exception as e:
            return VerificationResult(
                valid=False,
                errors=[f"Failed to load snapshot: {e}"],
            )

        # Verify schema version
        if snapshot.schema_version != EXPORT_SCHEMA_VERSION:
            warnings.append(
                f"Schema version mismatch: snapshot={snapshot.schema_version}, "
                f"current={EXPORT_SCHEMA_VERSION}"
            )

        # Verify each input file
        for fp in input_files:
            fp = Path(fp)
            filename = fp.name

            if not fp.exists():
                errors.append(f"Input file not found: {fp}")
                continue

            # Compute current hash
            current_hash = file_hash(str(fp))
            expected_hash = snapshot.export_hashes.get(filename)

            file_hashes[filename] = {
                "current": current_hash,
                "expected": expected_hash,
                "match": current_hash == expected_hash if expected_hash else None,
            }

            if expected_hash is None:
                warnings.append(f"File not in snapshot: {filename}")
            elif current_hash != expected_hash:
                errors.append(
                    f"Hash mismatch for {filename}: "
                    f"expected={expected_hash[:16]}..., "
                    f"actual={current_hash[:16]}..."
                )

        # Check for missing expected files
        for expected_file in snapshot.export_hashes.keys():
            found = any(Path(fp).name == expected_file for fp in input_files)
            if not found:
                warnings.append(f"Expected file not provided: {expected_file}")

        return VerificationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            file_hashes=file_hashes,
        )

    def verify_with_recompute(
        self,
        snapshot_path: str | Path,
        input_files: list[str | Path],
    ) -> VerificationResult:
        """Verify and show all hash comparisons.

        Same as verify() but includes all details for reporting.
        """
        return self.verify(snapshot_path, input_files)
