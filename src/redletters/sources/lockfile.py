"""Pack lockfile for reproducible scholarly environments (v0.11.0).

Handles:
- Generating lockfiles from installed packs
- Verifying installed packs match lockfile
- Syncing environments to match lockfile

Design principles:
- Deterministic hash computation (sorted file order, consistent algorithm)
- Full provenance tracking (install source, catalog ID, version)
- Schema-versioned for forward compatibility
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from redletters.sources.catalog import SourceCatalog, SourceRole
from redletters.sources.installer import SourceInstaller

# Current tool and schema versions
TOOL_VERSION = "0.11.0"
LOCKFILE_SCHEMA_VERSION = "1.0.0"


@dataclass
class LockfileInstallSource:
    """Source from which a pack can be installed."""

    type: Literal["catalog", "local", "git", "zip"]
    catalog_id: str = ""
    path: str = ""
    url: str = ""
    revision: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict (omit empty fields)."""
        result = {"type": self.type}
        if self.catalog_id:
            result["catalog_id"] = self.catalog_id
        if self.path:
            result["path"] = self.path
        if self.url:
            result["url"] = self.url
        if self.revision:
            result["revision"] = self.revision
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "LockfileInstallSource":
        """Deserialize from dict."""
        return cls(
            type=data.get("type", "catalog"),
            catalog_id=data.get("catalog_id", ""),
            path=data.get("path", ""),
            url=data.get("url", ""),
            revision=data.get("revision", ""),
        )


@dataclass
class LockfilePack:
    """A locked pack entry with integrity hash."""

    pack_id: str
    version: str
    role: Literal["spine", "comparative", "sense_pack"]
    license: str
    content_hash: str
    install_source: LockfileInstallSource | None = None

    def to_dict(self) -> dict:
        """Serialize to dict."""
        result = {
            "pack_id": self.pack_id,
            "version": self.version,
            "role": self.role,
            "license": self.license,
            "content_hash": self.content_hash,
        }
        if self.install_source:
            result["install_source"] = self.install_source.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "LockfilePack":
        """Deserialize from dict."""
        install_source = None
        if "install_source" in data:
            install_source = LockfileInstallSource.from_dict(data["install_source"])

        return cls(
            pack_id=data["pack_id"],
            version=data["version"],
            role=data["role"],
            license=data["license"],
            content_hash=data["content_hash"],
            install_source=install_source,
        )


@dataclass
class Lockfile:
    """Pack lockfile for reproducible environments."""

    tool_version: str
    schema_version: str
    generated_at: str
    packs: list[LockfilePack] = field(default_factory=list)
    lockfile_hash: str = ""

    def to_dict(self, include_hash: bool = True) -> dict:
        """Serialize to dict."""
        result = {
            "tool_version": self.tool_version,
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "packs": [p.to_dict() for p in self.packs],
        }
        if include_hash and self.lockfile_hash:
            result["lockfile_hash"] = self.lockfile_hash
        return result

    def to_json(self, pretty: bool = True) -> str:
        """Serialize to JSON string."""
        return json.dumps(
            self.to_dict(),
            indent=2 if pretty else None,
            ensure_ascii=False,
            sort_keys=True,
        )

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of lockfile content (excluding hash field)."""
        content = json.dumps(
            self.to_dict(include_hash=False),
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: dict) -> "Lockfile":
        """Deserialize from dict."""
        return cls(
            tool_version=data["tool_version"],
            schema_version=data["schema_version"],
            generated_at=data["generated_at"],
            packs=[LockfilePack.from_dict(p) for p in data.get("packs", [])],
            lockfile_hash=data.get("lockfile_hash", ""),
        )

    @classmethod
    def load(cls, path: Path) -> "Lockfile":
        """Load lockfile from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def save(self, path: Path) -> None:
        """Save lockfile to JSON file."""
        # Compute hash before saving
        self.lockfile_hash = self.compute_hash()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(pretty=True), encoding="utf-8")


def _role_from_source_role(source_role: SourceRole) -> str:
    """Map SourceRole to lockfile role."""
    if source_role == SourceRole.CANONICAL_SPINE:
        return "spine"
    elif source_role == SourceRole.SENSE_PACK:
        return "sense_pack"
    else:
        return "comparative"


class LockfileGenerator:
    """Generates lockfiles from installed pack state."""

    def __init__(
        self,
        data_root: Path | None = None,
        catalog_path: Path | None = None,
    ):
        """Initialize generator.

        Args:
            data_root: Override data root directory
            catalog_path: Override catalog path
        """
        self.data_root = data_root
        self.catalog_path = catalog_path
        self._installer: SourceInstaller | None = None
        self._catalog: SourceCatalog | None = None

    def _get_installer(self) -> SourceInstaller:
        """Get or create installer instance."""
        if self._installer is None:
            self._installer = SourceInstaller(data_root=self.data_root)
        return self._installer

    def _get_catalog(self) -> SourceCatalog:
        """Get or create catalog instance."""
        if self._catalog is None:
            self._catalog = SourceCatalog.load(self.catalog_path)
        return self._catalog

    def generate(self) -> Lockfile:
        """Generate lockfile from current installed state.

        Returns:
            Lockfile with all installed packs
        """
        installer = self._get_installer()
        catalog = self._get_catalog()
        manifest = installer.manifest

        packs: list[LockfilePack] = []

        # Get all installed sources from manifest
        for source_id, installed in manifest.sources.items():
            # Lookup source in catalog for role info
            source = catalog.get(source_id)
            if source:
                role = _role_from_source_role(source.role)
                install_source = self._build_install_source(source_id, source)
            else:
                # Fallback: treat as comparative if not found
                role = "comparative"
                install_source = LockfileInstallSource(
                    type="local",
                    path=installed.install_path,
                )

            packs.append(
                LockfilePack(
                    pack_id=source_id,
                    version=installed.version or "",
                    role=role,
                    license=installed.license or "",
                    content_hash=installed.sha256_manifest,
                    install_source=install_source,
                )
            )

        # Also get sense packs from database
        sense_packs = self._get_sense_packs(installer)
        packs.extend(sense_packs)

        # Sort by pack_id for deterministic output
        packs.sort(key=lambda p: p.pack_id)

        lockfile = Lockfile(
            tool_version=TOOL_VERSION,
            schema_version=LOCKFILE_SCHEMA_VERSION,
            generated_at=datetime.now(timezone.utc).isoformat(),
            packs=packs,
        )

        # Compute and store hash
        lockfile.lockfile_hash = lockfile.compute_hash()

        return lockfile

    def _build_install_source(self, source_id: str, source) -> LockfileInstallSource:
        """Build install source from catalog entry."""
        # Check if it's a local pack
        if source.pack_path:
            return LockfileInstallSource(
                type="local",
                path=source.pack_path,
            )

        # Check if it has a git repo
        if source.repo:
            return LockfileInstallSource(
                type="git",
                catalog_id=source_id,
                url=source.repo,
                revision=source.commit or source.git_tag or "",
            )

        # Default to catalog reference
        return LockfileInstallSource(
            type="catalog",
            catalog_id=source_id,
        )

    def _get_sense_packs(self, installer: SourceInstaller) -> list[LockfilePack]:
        """Get sense packs from database."""
        packs = []
        try:
            sense_pack_status = installer.get_sense_pack_status()
            for sp in sense_pack_status:
                # Skip if already in main manifest
                if installer.manifest.is_installed(sp["pack_id"]):
                    continue

                packs.append(
                    LockfilePack(
                        pack_id=sp["pack_id"],
                        version=sp.get("version", ""),
                        role="sense_pack",
                        license=sp.get("license", ""),
                        content_hash=sp.get("pack_hash", ""),
                        install_source=LockfileInstallSource(
                            type="local",
                            path=sp.get("install_path", ""),
                        ),
                    )
                )
        except Exception:
            # Sense pack DB may not exist
            pass

        return packs

    def save(self, output_path: Path) -> Lockfile:
        """Generate and save lockfile.

        Args:
            output_path: Path to save lockfile

        Returns:
            Generated Lockfile
        """
        lockfile = self.generate()
        lockfile.save(output_path)
        return lockfile


@dataclass
class PackSyncStatus:
    """Status of a single pack during sync verification."""

    pack_id: str
    status: Literal["ok", "missing", "hash_mismatch", "extra"]
    expected_hash: str = ""
    actual_hash: str = ""
    message: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict."""
        result = {
            "pack_id": self.pack_id,
            "status": self.status,
        }
        if self.expected_hash:
            result["expected_hash"] = self.expected_hash
        if self.actual_hash:
            result["actual_hash"] = self.actual_hash
        if self.message:
            result["message"] = self.message
        return result


@dataclass
class SyncResult:
    """Result of lockfile sync operation."""

    valid: bool
    packs: list[PackSyncStatus] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    mismatched: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    forced: bool = False
    forced_at: str = ""

    @property
    def ok_count(self) -> int:
        """Count of packs that match."""
        return sum(1 for p in self.packs if p.status == "ok")

    def to_dict(self) -> dict:
        """Serialize to dict."""
        result = {
            "valid": self.valid,
            "packs": [p.to_dict() for p in self.packs],
            "missing": self.missing,
            "mismatched": self.mismatched,
            "extra": self.extra,
        }
        if self.forced:
            result["forced"] = self.forced
            result["forced_at"] = self.forced_at
        return result


class LockfileSyncer:
    """Verifies and syncs pack installations against lockfile."""

    def __init__(
        self,
        data_root: Path | None = None,
        catalog_path: Path | None = None,
    ):
        """Initialize syncer.

        Args:
            data_root: Override data root directory
            catalog_path: Override catalog path
        """
        self.data_root = data_root
        self.catalog_path = catalog_path
        self._installer: SourceInstaller | None = None
        self._catalog: SourceCatalog | None = None

    def _get_installer(self) -> SourceInstaller:
        """Get or create installer instance."""
        if self._installer is None:
            self._installer = SourceInstaller(data_root=self.data_root)
        return self._installer

    def _get_catalog(self) -> SourceCatalog:
        """Get or create catalog instance."""
        if self._catalog is None:
            self._catalog = SourceCatalog.load(self.catalog_path)
        return self._catalog

    def _get_installed_hash(self, pack_id: str) -> str | None:
        """Get content hash for installed pack.

        Returns:
            SHA-256 hash string or None if not installed
        """
        installer = self._get_installer()

        # Check main manifest first
        installed = installer.get_installed(pack_id)
        if installed and installed.sha256_manifest:
            return installed.sha256_manifest

        # Check sense packs
        try:
            sense_pack_status = installer.get_sense_pack_status()
            for sp in sense_pack_status:
                if sp["pack_id"] == pack_id:
                    return sp.get("pack_hash", "")
        except Exception:
            pass

        return None

    def verify(self, lockfile: Lockfile) -> SyncResult:
        """Verify installed packs match lockfile.

        Args:
            lockfile: Lockfile to verify against

        Returns:
            SyncResult with verification status
        """
        installer = self._get_installer()
        manifest = installer.manifest

        packs: list[PackSyncStatus] = []
        missing: list[str] = []
        mismatched: list[str] = []

        # Build set of locked pack IDs
        locked_pack_ids = {p.pack_id for p in lockfile.packs}

        # Check each locked pack
        for locked_pack in lockfile.packs:
            actual_hash = self._get_installed_hash(locked_pack.pack_id)

            if actual_hash is None:
                # Pack not installed
                packs.append(
                    PackSyncStatus(
                        pack_id=locked_pack.pack_id,
                        status="missing",
                        expected_hash=locked_pack.content_hash,
                        message="Pack not installed",
                    )
                )
                missing.append(locked_pack.pack_id)
            elif actual_hash != locked_pack.content_hash:
                # Hash mismatch
                packs.append(
                    PackSyncStatus(
                        pack_id=locked_pack.pack_id,
                        status="hash_mismatch",
                        expected_hash=locked_pack.content_hash,
                        actual_hash=actual_hash,
                        message="Content hash differs",
                    )
                )
                mismatched.append(locked_pack.pack_id)
            else:
                # OK
                packs.append(
                    PackSyncStatus(
                        pack_id=locked_pack.pack_id,
                        status="ok",
                        expected_hash=locked_pack.content_hash,
                        actual_hash=actual_hash,
                    )
                )

        # Check for extra installed packs not in lockfile
        extra: list[str] = []
        for source_id in manifest.sources:
            if source_id not in locked_pack_ids:
                packs.append(
                    PackSyncStatus(
                        pack_id=source_id,
                        status="extra",
                        message="Installed but not in lockfile",
                    )
                )
                extra.append(source_id)

        valid = len(missing) == 0 and len(mismatched) == 0

        return SyncResult(
            valid=valid,
            packs=packs,
            missing=missing,
            mismatched=mismatched,
            extra=extra,
        )

    def sync(self, lockfile: Lockfile, force: bool = False) -> SyncResult:
        """Sync installed packs to match lockfile.

        Args:
            lockfile: Lockfile to sync to
            force: If True, accept hash mismatches with audit record

        Returns:
            SyncResult with sync status
        """
        # First verify current state
        result = self.verify(lockfile)

        # If already valid, nothing to do
        if result.valid:
            return result

        # If mismatches exist and not forced, fail
        if result.mismatched and not force:
            return result

        installer = self._get_installer()

        # Install missing packs
        for pack_id in result.missing:
            # Find locked pack info
            locked_pack = next(
                (p for p in lockfile.packs if p.pack_id == pack_id), None
            )
            if not locked_pack:
                continue

            # Try to install from catalog
            if locked_pack.install_source:
                source = locked_pack.install_source
                if source.type == "catalog" and source.catalog_id:
                    # Install from catalog
                    try:
                        install_result = installer.install(
                            source.catalog_id, accept_eula=True
                        )
                        if install_result.success:
                            # Update status
                            for ps in result.packs:
                                if ps.pack_id == pack_id:
                                    ps.status = "ok"
                                    ps.message = "Installed from catalog"
                                    break
                            result.missing.remove(pack_id)
                    except Exception as e:
                        # Update message with error
                        for ps in result.packs:
                            if ps.pack_id == pack_id:
                                ps.message = f"Install failed: {e}"
                                break

        # If force mode, mark mismatches as accepted
        if force and result.mismatched:
            result.forced = True
            result.forced_at = datetime.now(timezone.utc).isoformat()
            for pack_id in result.mismatched:
                for ps in result.packs:
                    if ps.pack_id == pack_id:
                        ps.message = "Hash mismatch accepted (--force)"
                        break
            # Clear mismatched list since we're accepting them
            result.mismatched = []

        # Recompute validity
        result.valid = len(result.missing) == 0 and len(result.mismatched) == 0

        return result
