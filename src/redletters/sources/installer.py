"""License-aware source pack installer.

Handles:
- Installing source packs from various sources (git, zip, local)
- EULA enforcement for licensed content
- Manifest tracking of installed sources
- Verification of installed files

Design principles:
- EULA sources require explicit --accept-eula flag
- Open-license sources can be installed freely
- All installations are tracked in installed_sources.json
- No EULA-restricted text is ever bundled in the repo
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from redletters.sources.catalog import SourceCatalog, SourcePack


# Licenses that require EULA acceptance
EULA_LICENSES = {
    "EULA",
    "Proprietary",
    "Academic use",
    "Academic",
    "Commercial",
    "RESTRICTED",
}

# Licenses that are permissive (no EULA required)
PERMISSIVE_LICENSES = {
    "CC0-1.0",
    "CC-BY-4.0",
    "CC-BY-3.0",
    "CC-BY-SA-4.0",
    "CC-BY-SA-3.0",
    "Public Domain",
    "MIT",
    "Apache-2.0",
    "BSD-3-Clause",
    "BSD-2-Clause",
}


@dataclass
class InstallSpec:
    """Installation specification for a source pack."""

    source_type: Literal["git", "zip", "local", "manual"]
    url: str = ""
    path: str = ""
    subdir: str = ""
    revision: str = ""  # Git commit or tag

    @classmethod
    def from_dict(cls, data: dict) -> "InstallSpec":
        """Create from catalog dict."""
        return cls(
            source_type=data.get("type", "manual"),
            url=data.get("url", ""),
            path=data.get("path", ""),
            subdir=data.get("subdir", ""),
            revision=data.get("revision", data.get("commit", "")),
        )


@dataclass
class InstalledSource:
    """Record of an installed source pack."""

    source_id: str
    name: str
    installed_at: str
    install_path: str
    version: str = ""
    revision: str = ""
    license: str = ""
    eula_accepted_at: str | None = None
    file_count: int = 0
    sha256_manifest: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "source_id": self.source_id,
            "name": self.name,
            "installed_at": self.installed_at,
            "install_path": self.install_path,
            "version": self.version,
            "revision": self.revision,
            "license": self.license,
            "eula_accepted_at": self.eula_accepted_at,
            "file_count": self.file_count,
            "sha256_manifest": self.sha256_manifest,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InstalledSource":
        """Deserialize from dict."""
        return cls(
            source_id=data["source_id"],
            name=data["name"],
            installed_at=data["installed_at"],
            install_path=data["install_path"],
            version=data.get("version", ""),
            revision=data.get("revision", ""),
            license=data.get("license", ""),
            eula_accepted_at=data.get("eula_accepted_at"),
            file_count=data.get("file_count", 0),
            sha256_manifest=data.get("sha256_manifest", ""),
        )


@dataclass
class InstallResult:
    """Result of an installation attempt."""

    success: bool
    source_id: str
    message: str
    install_path: str = ""
    eula_required: bool = False
    error: str = ""

    @property
    def needs_eula(self) -> bool:
        """True if EULA acceptance is required."""
        return self.eula_required and not self.success


@dataclass
class InstalledManifest:
    """Manifest of all installed source packs."""

    sources: dict[str, InstalledSource] = field(default_factory=dict)
    manifest_version: str = "1.0"
    last_updated: str = ""

    def add(self, source: InstalledSource) -> None:
        """Add or update an installed source."""
        self.sources[source.source_id] = source
        self.last_updated = datetime.utcnow().isoformat()

    def remove(self, source_id: str) -> bool:
        """Remove an installed source."""
        if source_id in self.sources:
            del self.sources[source_id]
            self.last_updated = datetime.utcnow().isoformat()
            return True
        return False

    def get(self, source_id: str) -> InstalledSource | None:
        """Get installed source by ID."""
        return self.sources.get(source_id)

    def is_installed(self, source_id: str) -> bool:
        """Check if source is installed."""
        return source_id in self.sources

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "manifest_version": self.manifest_version,
            "last_updated": self.last_updated,
            "sources": {k: v.to_dict() for k, v in self.sources.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InstalledManifest":
        """Deserialize from dict."""
        manifest = cls(
            manifest_version=data.get("manifest_version", "1.0"),
            last_updated=data.get("last_updated", ""),
        )
        for source_id, source_data in data.get("sources", {}).items():
            manifest.sources[source_id] = InstalledSource.from_dict(source_data)
        return manifest

    @classmethod
    def load(cls, path: Path) -> "InstalledManifest":
        """Load from file."""
        if not path.exists():
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def save(self, path: Path) -> None:
        """Save to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


class SourceInstaller:
    """Installer for source packs with license awareness.

    Usage:
        installer = SourceInstaller()
        result = installer.install("morphgnt-sblgnt")

        # For EULA sources:
        result = installer.install("sblgnt-apparatus", accept_eula=True)
    """

    def __init__(
        self,
        catalog: SourceCatalog | None = None,
        data_root: Path | str | None = None,
    ):
        """Initialize installer.

        Args:
            catalog: Source catalog (loaded if not provided)
            data_root: Override data root path
        """
        self.catalog = catalog or SourceCatalog.load()
        self.data_root = self._resolve_data_root(data_root)
        self._manifest: InstalledManifest | None = None

    def _resolve_data_root(self, override: Path | str | None) -> Path:
        """Resolve data root directory."""
        if override:
            return Path(override)

        env_root = os.environ.get("REDLETTERS_DATA_ROOT")
        if env_root:
            return Path(env_root)

        return Path.home() / ".redletters" / "data"

    @property
    def manifest_path(self) -> Path:
        """Path to installed sources manifest."""
        return self.data_root / "installed_sources.json"

    @property
    def manifest(self) -> InstalledManifest:
        """Load or return cached manifest."""
        if self._manifest is None:
            self._manifest = InstalledManifest.load(self.manifest_path)
        return self._manifest

    def _save_manifest(self) -> None:
        """Save manifest to disk."""
        self.manifest.save(self.manifest_path)

    def requires_eula(self, source: SourcePack) -> bool:
        """Check if source requires EULA acceptance.

        Args:
            source: Source pack to check

        Returns:
            True if EULA acceptance is required
        """
        license_ = source.license.upper()

        # Check explicit EULA markers
        if license_ in EULA_LICENSES or "EULA" in license_:
            return True

        # Check if it's explicitly permissive
        if source.license in PERMISSIVE_LICENSES:
            return False

        # Default: conservative - unknown licenses require EULA
        # But for known academic open licenses, don't require
        if any(
            open_marker in license_
            for open_marker in ["CC-", "MIT", "APACHE", "BSD", "PUBLIC"]
        ):
            return False

        return True

    def get_install_path(self, source_id: str) -> Path:
        """Get installation path for a source."""
        return self.data_root / source_id

    def is_installed(self, source_id: str) -> bool:
        """Check if source is installed."""
        return self.manifest.is_installed(source_id)

    def get_installed(self, source_id: str) -> InstalledSource | None:
        """Get installed source info."""
        return self.manifest.get(source_id)

    def install(
        self,
        source_id: str,
        accept_eula: bool = False,
        force: bool = False,
    ) -> InstallResult:
        """Install a source pack.

        Args:
            source_id: Source identifier from catalog
            accept_eula: If True, accept EULA for licensed content
            force: If True, reinstall even if already installed

        Returns:
            InstallResult with status and details
        """
        # Validate source exists
        source = self.catalog.get(source_id)
        if source is None:
            return InstallResult(
                success=False,
                source_id=source_id,
                message=f"Source not found in catalog: {source_id}",
                error="source_not_found",
            )

        # Check if already installed
        if self.is_installed(source_id) and not force:
            installed = self.get_installed(source_id)
            return InstallResult(
                success=True,
                source_id=source_id,
                message=f"Already installed at {installed.install_path}",
                install_path=installed.install_path,
            )

        # Check EULA requirement
        needs_eula = self.requires_eula(source)
        if needs_eula and not accept_eula:
            return InstallResult(
                success=False,
                source_id=source_id,
                message=f"Source '{source.name}' requires EULA acceptance.\n"
                f"License: {source.license}\n"
                f"Run with --accept-eula to acknowledge the license terms.",
                eula_required=True,
                error="eula_required",
            )

        # Determine install method
        install_spec = self._get_install_spec(source)

        if install_spec.source_type == "manual":
            return InstallResult(
                success=False,
                source_id=source_id,
                message=f"Source '{source.name}' requires manual installation.\n"
                f"See notes: {source.notes[:200] if source.notes else 'N/A'}",
                error="manual_install_required",
            )

        # Perform installation
        try:
            install_path = self._do_install(source, install_spec)
        except Exception as e:
            return InstallResult(
                success=False,
                source_id=source_id,
                message=f"Installation failed: {e}",
                error=str(e),
            )

        # Create installed source record
        installed = InstalledSource(
            source_id=source_id,
            name=source.name,
            installed_at=datetime.utcnow().isoformat(),
            install_path=str(install_path),
            version=source.version,
            revision=source.commit or install_spec.revision,
            license=source.license,
            eula_accepted_at=datetime.utcnow().isoformat() if needs_eula else None,
            file_count=self._count_files(install_path),
            sha256_manifest=self._compute_manifest_hash(install_path),
        )

        # Update manifest
        self.manifest.add(installed)
        self._save_manifest()

        return InstallResult(
            success=True,
            source_id=source_id,
            message=f"Installed {source.name} to {install_path}",
            install_path=str(install_path),
            eula_required=needs_eula,
        )

    def _get_install_spec(self, source: SourcePack) -> InstallSpec:
        """Get installation spec for a source."""
        # Sprint 7: Check if source is a local pack
        if source.is_pack and source.pack_path:
            # Resolve pack path relative to catalog location
            catalog_dir = self.catalog.path.parent if self.catalog.path else Path.cwd()
            pack_path = catalog_dir / source.pack_path
            return InstallSpec(
                source_type="local",
                path=str(pack_path),
            )

        # Check if source has explicit install config
        if source.provenance and "install" in source.provenance:
            return InstallSpec.from_dict(source.provenance["install"])

        # Infer from repo and commit
        if source.repo and source.commit:
            return InstallSpec(
                source_type="git",
                url=source.repo,
                revision=source.commit,
            )
        elif source.repo:
            return InstallSpec(
                source_type="git",
                url=source.repo,
            )

        # Manual install required
        return InstallSpec(source_type="manual")

    def _do_install(self, source: SourcePack, spec: InstallSpec) -> Path:
        """Perform the actual installation."""
        install_path = self.get_install_path(source.key)

        # Clean up existing installation
        if install_path.exists():
            shutil.rmtree(install_path)

        install_path.mkdir(parents=True, exist_ok=True)

        if spec.source_type == "git":
            self._install_from_git(spec, install_path)
        elif spec.source_type == "zip":
            self._install_from_zip(spec, install_path)
        elif spec.source_type == "local":
            self._install_from_local(spec, install_path)
        else:
            raise ValueError(f"Unknown install type: {spec.source_type}")

        return install_path

    def _install_from_git(self, spec: InstallSpec, install_path: Path) -> None:
        """Clone a git repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "repo"

            # Clone the repo
            cmd = ["git", "clone", "--depth", "1"]
            if spec.revision:
                cmd.extend(["--branch", spec.revision])
            cmd.extend([spec.url, str(tmp_path)])

            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError:
                # Try shallow clone then checkout for commits
                cmd = ["git", "clone", "--depth", "1", spec.url, str(tmp_path)]
                subprocess.run(cmd, check=True, capture_output=True, text=True)

                if spec.revision:
                    # Fetch specific commit
                    subprocess.run(
                        ["git", "fetch", "--depth", "1", "origin", spec.revision],
                        cwd=tmp_path,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    subprocess.run(
                        ["git", "checkout", spec.revision],
                        cwd=tmp_path,
                        check=True,
                        capture_output=True,
                        text=True,
                    )

            # Copy files (excluding .git)
            source_dir = tmp_path / spec.subdir if spec.subdir else tmp_path
            for item in source_dir.iterdir():
                if item.name == ".git":
                    continue
                dest = install_path / item.name
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

    def _install_from_zip(self, spec: InstallSpec, install_path: Path) -> None:
        """Download and extract a zip file."""
        import urllib.request
        import zipfile

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            urllib.request.urlretrieve(spec.url, tmp.name)

            with zipfile.ZipFile(tmp.name, "r") as zf:
                # Extract to install path
                if spec.subdir:
                    for member in zf.namelist():
                        if member.startswith(spec.subdir):
                            # Strip subdir prefix
                            target = install_path / member[len(spec.subdir) :].lstrip(
                                "/"
                            )
                            if member.endswith("/"):
                                target.mkdir(parents=True, exist_ok=True)
                            else:
                                target.parent.mkdir(parents=True, exist_ok=True)
                                with zf.open(member) as src, open(target, "wb") as dst:
                                    dst.write(src.read())
                else:
                    zf.extractall(install_path)

            Path(tmp.name).unlink()

    def _install_from_local(self, spec: InstallSpec, install_path: Path) -> None:
        """Copy from local path."""
        source = Path(spec.path)
        if spec.subdir:
            source = source / spec.subdir

        if source.is_dir():
            shutil.copytree(source, install_path, dirs_exist_ok=True)
        else:
            shutil.copy2(source, install_path / source.name)

    def _count_files(self, path: Path) -> int:
        """Count files in directory."""
        count = 0
        for _ in path.rglob("*"):
            count += 1
        return count

    def _compute_manifest_hash(self, path: Path) -> str:
        """Compute hash of all files for integrity checking."""
        hasher = hashlib.sha256()

        for file_path in sorted(path.rglob("*")):
            if file_path.is_file():
                rel_path = file_path.relative_to(path)
                hasher.update(str(rel_path).encode())
                hasher.update(file_path.read_bytes())

        return hasher.hexdigest()

    def uninstall(self, source_id: str) -> InstallResult:
        """Uninstall a source pack.

        Args:
            source_id: Source identifier

        Returns:
            InstallResult with status
        """
        if not self.is_installed(source_id):
            return InstallResult(
                success=False,
                source_id=source_id,
                message=f"Source not installed: {source_id}",
                error="not_installed",
            )

        installed = self.get_installed(source_id)
        install_path = Path(installed.install_path)

        # Remove files
        if install_path.exists():
            shutil.rmtree(install_path)

        # Update manifest
        self.manifest.remove(source_id)
        self._save_manifest()

        return InstallResult(
            success=True,
            source_id=source_id,
            message=f"Uninstalled {source_id}",
        )

    def status(self) -> dict:
        """Get status of all sources.

        Returns:
            Dict with source statuses
        """
        result = {
            "data_root": str(self.data_root),
            "manifest_path": str(self.manifest_path),
            "sources": {},
        }

        for key, source in self.catalog.sources.items():
            installed = self.get_installed(key)

            status_info = {
                "name": source.name,
                "role": source.role.value,
                "license": source.license,
                "requires_eula": self.requires_eula(source),
                "installed": installed is not None,
            }

            if installed:
                status_info.update(
                    {
                        "install_path": installed.install_path,
                        "installed_at": installed.installed_at,
                        "version": installed.version,
                        "eula_accepted": installed.eula_accepted_at is not None,
                    }
                )

            result["sources"][key] = status_info

        return result

    def install_sense_pack(
        self,
        pack_path: Path | str,
        accept_license: bool = False,
        force: bool = False,
        db_conn=None,
    ) -> InstallResult:
        """Install a sense pack from a local directory.

        Sense packs provide lexicon/gloss data with citation-grade provenance.

        Args:
            pack_path: Path to sense pack directory
            accept_license: If True, accept license for non-PD content
            force: If True, reinstall even if already installed
            db_conn: Database connection (created if not provided)

        Returns:
            InstallResult with status and details
        """
        from redletters.sources.sense_pack import (
            SensePackLoader,
            validate_sense_pack,
        )
        from redletters.sources.sense_db import SensePackDB

        pack_path = Path(pack_path)

        # Validate pack
        validation = validate_sense_pack(pack_path)
        if not validation.valid:
            errors = "; ".join(e.message for e in validation.errors[:3])
            return InstallResult(
                success=False,
                source_id=str(pack_path),
                message=f"Invalid sense pack: {errors}",
                error="validation_failed",
            )

        manifest = validation.manifest
        if manifest is None:
            return InstallResult(
                success=False,
                source_id=str(pack_path),
                message="Could not load manifest",
                error="manifest_error",
            )

        pack_id = manifest.pack_id

        # Check license acceptance
        if manifest.requires_license_acceptance and not accept_license:
            return InstallResult(
                success=False,
                source_id=pack_id,
                message=f"Sense pack '{manifest.name}' requires license acceptance.\n"
                f"License: {manifest.license}\n"
                f"Run with --accept-license to acknowledge the license terms.",
                eula_required=True,
                error="license_required",
            )

        # Check if already installed
        if self.manifest.is_installed(pack_id) and not force:
            installed = self.manifest.get(pack_id)
            return InstallResult(
                success=True,
                source_id=pack_id,
                message=f"Already installed at {installed.install_path}",
                install_path=installed.install_path,
            )

        # Install files to data directory
        install_path = self.get_install_path(pack_id)
        if install_path.exists():
            shutil.rmtree(install_path)
        shutil.copytree(pack_path, install_path)

        # Load senses into database
        close_conn = False
        if db_conn is None:
            from redletters.db.connection import get_connection

            db_conn = get_connection()
            close_conn = True

        try:
            sense_db = SensePackDB(db_conn)
            sense_db.ensure_schema()

            loader = SensePackLoader(install_path)
            loader.load()

            pack_hash = self._compute_manifest_hash(install_path)
            installed_pack = sense_db.install_pack(loader, str(install_path), pack_hash)

            # Also track in main installer manifest
            installed = InstalledSource(
                source_id=pack_id,
                name=manifest.name,
                installed_at=datetime.utcnow().isoformat(),
                install_path=str(install_path),
                version=manifest.version,
                revision="",
                license=manifest.license,
                eula_accepted_at=(
                    datetime.utcnow().isoformat()
                    if manifest.requires_license_acceptance
                    else None
                ),
                file_count=self._count_files(install_path),
                sha256_manifest=pack_hash,
            )

            self.manifest.add(installed)
            self._save_manifest()

            return InstallResult(
                success=True,
                source_id=pack_id,
                message=f"Installed sense pack '{manifest.name}' ({installed_pack.sense_count} senses)",
                install_path=str(install_path),
                eula_required=manifest.requires_license_acceptance,
            )
        finally:
            if close_conn:
                db_conn.close()

    def get_sense_pack_status(self, db_conn=None) -> list[dict]:
        """Get status of installed sense packs.

        Args:
            db_conn: Database connection (created if not provided)

        Returns:
            List of sense pack status dicts
        """
        from redletters.sources.sense_db import SensePackDB

        close_conn = False
        if db_conn is None:
            from redletters.db.connection import get_connection

            db_conn = get_connection()
            close_conn = True

        try:
            sense_db = SensePackDB(db_conn)
            sense_db.ensure_schema()
            return sense_db.get_pack_status()
        finally:
            if close_conn:
                db_conn.close()


# SpineMissingError is defined in spine.py to avoid circular imports
