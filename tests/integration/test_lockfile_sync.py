"""Integration tests for lockfile generation and sync (v0.11.0).

Tests verify:
- Lockfile generation captures all installed packs
- Sync passes on identical environment
- Sync detects modified pack (hash mismatch)
- Sync with --force records audit trail
- Missing packs are detected
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


from redletters.sources.installer import InstalledManifest, InstalledSource
from redletters.sources.lockfile import (
    LOCKFILE_SCHEMA_VERSION,
    TOOL_VERSION,
    Lockfile,
    LockfileGenerator,
    LockfilePack,
    LockfileSyncer,
)


# ============================================================================
# Test Fixtures
# ============================================================================


def create_mock_installed_source(
    source_id: str,
    version: str = "1.0.0",
    license_: str = "MIT",
    content_hash: str | None = None,
) -> InstalledSource:
    """Create a mock InstalledSource for testing."""
    if content_hash is None:
        content_hash = hashlib.sha256(source_id.encode()).hexdigest()

    return InstalledSource(
        source_id=source_id,
        name=f"Test Pack {source_id}",
        installed_at="2024-01-01T00:00:00Z",
        install_path=f"/data/sources/{source_id}",
        version=version,
        revision="abc123",
        license=license_,
        file_count=10,
        sha256_manifest=content_hash,
    )


def create_mock_manifest(sources: list[InstalledSource]) -> InstalledManifest:
    """Create a mock InstalledManifest."""
    manifest = InstalledManifest()
    for source in sources:
        manifest.add(source)
    return manifest


# ============================================================================
# Lockfile Generation Tests
# ============================================================================


class TestLockfileGeneration:
    """Integration tests for lockfile generation."""

    def test_generate_empty_environment(self):
        """Empty environment produces lockfile with no packs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock installer with empty manifest
            with patch(
                "redletters.sources.lockfile.SourceInstaller"
            ) as mock_installer_cls:
                mock_installer = MagicMock()
                mock_installer.manifest = InstalledManifest()
                mock_installer.get_sense_pack_status.return_value = []
                mock_installer_cls.return_value = mock_installer

                with patch(
                    "redletters.sources.lockfile.SourceCatalog"
                ) as mock_catalog_cls:
                    mock_catalog = MagicMock()
                    mock_catalog.get.return_value = None
                    mock_catalog_cls.load.return_value = mock_catalog

                    generator = LockfileGenerator(data_root=Path(tmpdir))
                    lockfile = generator.generate()

                    assert lockfile.tool_version == TOOL_VERSION
                    assert lockfile.schema_version == LOCKFILE_SCHEMA_VERSION
                    assert len(lockfile.packs) == 0
                    assert lockfile.lockfile_hash != ""

    def test_generate_with_installed_packs(self):
        """Installed packs are captured in lockfile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sources = [
                create_mock_installed_source(
                    "morphgnt-sblgnt", "1.0.0", "CC-BY-SA-4.0"
                ),
                create_mock_installed_source(
                    "westcott-hort-john", "0.9.0", "Public Domain"
                ),
            ]

            with patch(
                "redletters.sources.lockfile.SourceInstaller"
            ) as mock_installer_cls:
                mock_installer = MagicMock()
                mock_installer.manifest = create_mock_manifest(sources)
                mock_installer.get_installed.side_effect = lambda sid: next(
                    (s for s in sources if s.source_id == sid), None
                )
                mock_installer.get_sense_pack_status.return_value = []
                mock_installer_cls.return_value = mock_installer

                with patch(
                    "redletters.sources.lockfile.SourceCatalog"
                ) as mock_catalog_cls:
                    mock_catalog = MagicMock()
                    mock_catalog.get.return_value = None
                    mock_catalog_cls.load.return_value = mock_catalog

                    generator = LockfileGenerator(data_root=Path(tmpdir))
                    lockfile = generator.generate()

                    assert len(lockfile.packs) == 2
                    pack_ids = {p.pack_id for p in lockfile.packs}
                    assert "morphgnt-sblgnt" in pack_ids
                    assert "westcott-hort-john" in pack_ids

    def test_generate_includes_sense_packs(self):
        """Sense packs are included in lockfile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(
                "redletters.sources.lockfile.SourceInstaller"
            ) as mock_installer_cls:
                mock_installer = MagicMock()
                mock_installer.manifest = InstalledManifest()
                mock_installer.manifest.is_installed = lambda x: False
                mock_installer.get_sense_pack_status.return_value = [
                    {
                        "pack_id": "bdag-senses",
                        "version": "1.0",
                        "license": "EULA",
                        "pack_hash": "a" * 64,
                        "install_path": "/data/senses/bdag",
                    }
                ]
                mock_installer_cls.return_value = mock_installer

                with patch(
                    "redletters.sources.lockfile.SourceCatalog"
                ) as mock_catalog_cls:
                    mock_catalog = MagicMock()
                    mock_catalog.get.return_value = None
                    mock_catalog_cls.load.return_value = mock_catalog

                    generator = LockfileGenerator(data_root=Path(tmpdir))
                    lockfile = generator.generate()

                    assert len(lockfile.packs) == 1
                    assert lockfile.packs[0].pack_id == "bdag-senses"
                    assert lockfile.packs[0].role == "sense_pack"

    def test_save_and_reload(self):
        """Lockfile can be saved and reloaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile = Lockfile(
                tool_version=TOOL_VERSION,
                schema_version=LOCKFILE_SCHEMA_VERSION,
                generated_at="2024-01-01T00:00:00Z",
                packs=[
                    LockfilePack(
                        pack_id="test-pack",
                        version="1.0",
                        role="spine",
                        license="MIT",
                        content_hash="a" * 64,
                    )
                ],
            )

            path = Path(tmpdir) / "lock.json"
            lockfile.save(path)

            loaded = Lockfile.load(path)

            assert loaded.tool_version == lockfile.tool_version
            assert len(loaded.packs) == 1
            assert loaded.packs[0].pack_id == "test-pack"


# ============================================================================
# Lockfile Sync Tests
# ============================================================================


class TestLockfileSync:
    """Integration tests for lockfile sync and verification."""

    def test_verify_matching_environment(self):
        """Verify passes when environment matches lockfile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            content_hash = "a" * 64

            lockfile = Lockfile(
                tool_version=TOOL_VERSION,
                schema_version=LOCKFILE_SCHEMA_VERSION,
                generated_at="2024-01-01T00:00:00Z",
                packs=[
                    LockfilePack(
                        pack_id="test-pack",
                        version="1.0",
                        role="spine",
                        license="MIT",
                        content_hash=content_hash,
                    )
                ],
            )

            sources = [
                create_mock_installed_source("test-pack", "1.0", "MIT", content_hash)
            ]

            with patch(
                "redletters.sources.lockfile.SourceInstaller"
            ) as mock_installer_cls:
                mock_installer = MagicMock()
                mock_installer.manifest = create_mock_manifest(sources)
                mock_installer.get_installed.side_effect = lambda sid: next(
                    (s for s in sources if s.source_id == sid), None
                )
                mock_installer.get_sense_pack_status.return_value = []
                mock_installer_cls.return_value = mock_installer

                with patch(
                    "redletters.sources.lockfile.SourceCatalog"
                ) as mock_catalog_cls:
                    mock_catalog = MagicMock()
                    mock_catalog_cls.load.return_value = mock_catalog

                    syncer = LockfileSyncer(data_root=Path(tmpdir))
                    result = syncer.verify(lockfile)

                    assert result.valid is True
                    assert result.ok_count == 1
                    assert len(result.missing) == 0
                    assert len(result.mismatched) == 0

    def test_verify_detects_missing_pack(self):
        """Verify fails when pack is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile = Lockfile(
                tool_version=TOOL_VERSION,
                schema_version=LOCKFILE_SCHEMA_VERSION,
                generated_at="2024-01-01T00:00:00Z",
                packs=[
                    LockfilePack(
                        pack_id="missing-pack",
                        version="1.0",
                        role="spine",
                        license="MIT",
                        content_hash="a" * 64,
                    )
                ],
            )

            with patch(
                "redletters.sources.lockfile.SourceInstaller"
            ) as mock_installer_cls:
                mock_installer = MagicMock()
                mock_installer.manifest = InstalledManifest()
                mock_installer.get_installed.return_value = None
                mock_installer.get_sense_pack_status.return_value = []
                mock_installer_cls.return_value = mock_installer

                with patch(
                    "redletters.sources.lockfile.SourceCatalog"
                ) as mock_catalog_cls:
                    mock_catalog = MagicMock()
                    mock_catalog_cls.load.return_value = mock_catalog

                    syncer = LockfileSyncer(data_root=Path(tmpdir))
                    result = syncer.verify(lockfile)

                    assert result.valid is False
                    assert "missing-pack" in result.missing

    def test_verify_detects_hash_mismatch(self):
        """Verify fails when pack hash differs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            expected_hash = "a" * 64
            actual_hash = "b" * 64

            lockfile = Lockfile(
                tool_version=TOOL_VERSION,
                schema_version=LOCKFILE_SCHEMA_VERSION,
                generated_at="2024-01-01T00:00:00Z",
                packs=[
                    LockfilePack(
                        pack_id="modified-pack",
                        version="1.0",
                        role="spine",
                        license="MIT",
                        content_hash=expected_hash,
                    )
                ],
            )

            sources = [
                create_mock_installed_source("modified-pack", "1.0", "MIT", actual_hash)
            ]

            with patch(
                "redletters.sources.lockfile.SourceInstaller"
            ) as mock_installer_cls:
                mock_installer = MagicMock()
                mock_installer.manifest = create_mock_manifest(sources)
                mock_installer.get_installed.side_effect = lambda sid: next(
                    (s for s in sources if s.source_id == sid), None
                )
                mock_installer.get_sense_pack_status.return_value = []
                mock_installer_cls.return_value = mock_installer

                with patch(
                    "redletters.sources.lockfile.SourceCatalog"
                ) as mock_catalog_cls:
                    mock_catalog = MagicMock()
                    mock_catalog_cls.load.return_value = mock_catalog

                    syncer = LockfileSyncer(data_root=Path(tmpdir))
                    result = syncer.verify(lockfile)

                    assert result.valid is False
                    assert "modified-pack" in result.mismatched
                    # Find the status for the modified pack
                    pack_status = next(
                        p for p in result.packs if p.pack_id == "modified-pack"
                    )
                    assert pack_status.expected_hash == expected_hash
                    assert pack_status.actual_hash == actual_hash

    def test_verify_detects_extra_packs(self):
        """Verify reports extra installed packs not in lockfile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lockfile = Lockfile(
                tool_version=TOOL_VERSION,
                schema_version=LOCKFILE_SCHEMA_VERSION,
                generated_at="2024-01-01T00:00:00Z",
                packs=[],  # Empty lockfile
            )

            sources = [create_mock_installed_source("extra-pack", "1.0", "MIT")]

            with patch(
                "redletters.sources.lockfile.SourceInstaller"
            ) as mock_installer_cls:
                mock_installer = MagicMock()
                mock_installer.manifest = create_mock_manifest(sources)
                mock_installer.get_sense_pack_status.return_value = []
                mock_installer_cls.return_value = mock_installer

                with patch(
                    "redletters.sources.lockfile.SourceCatalog"
                ) as mock_catalog_cls:
                    mock_catalog = MagicMock()
                    mock_catalog_cls.load.return_value = mock_catalog

                    syncer = LockfileSyncer(data_root=Path(tmpdir))
                    result = syncer.verify(lockfile)

                    # Extra packs don't invalidate (just reported)
                    assert result.valid is True
                    assert "extra-pack" in result.extra

    def test_sync_with_force_accepts_mismatch(self):
        """Sync with --force accepts hash mismatches with audit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            expected_hash = "a" * 64
            actual_hash = "b" * 64

            lockfile = Lockfile(
                tool_version=TOOL_VERSION,
                schema_version=LOCKFILE_SCHEMA_VERSION,
                generated_at="2024-01-01T00:00:00Z",
                packs=[
                    LockfilePack(
                        pack_id="modified-pack",
                        version="1.0",
                        role="spine",
                        license="MIT",
                        content_hash=expected_hash,
                    )
                ],
            )

            sources = [
                create_mock_installed_source("modified-pack", "1.0", "MIT", actual_hash)
            ]

            with patch(
                "redletters.sources.lockfile.SourceInstaller"
            ) as mock_installer_cls:
                mock_installer = MagicMock()
                mock_installer.manifest = create_mock_manifest(sources)
                mock_installer.get_installed.side_effect = lambda sid: next(
                    (s for s in sources if s.source_id == sid), None
                )
                mock_installer.get_sense_pack_status.return_value = []
                mock_installer_cls.return_value = mock_installer

                with patch(
                    "redletters.sources.lockfile.SourceCatalog"
                ) as mock_catalog_cls:
                    mock_catalog = MagicMock()
                    mock_catalog_cls.load.return_value = mock_catalog

                    syncer = LockfileSyncer(data_root=Path(tmpdir))

                    # Without force: should fail
                    result_no_force = syncer.sync(lockfile, force=False)
                    assert result_no_force.valid is False

                    # With force: should succeed with audit
                    result_force = syncer.sync(lockfile, force=True)
                    assert result_force.valid is True
                    assert result_force.forced is True
                    assert result_force.forced_at != ""


# ============================================================================
# End-to-End Lockfile Workflow Tests
# ============================================================================


class TestLockfileWorkflow:
    """End-to-end tests for lockfile workflow."""

    def test_roundtrip_generate_verify(self):
        """Generate lockfile then verify same environment passes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            content_hash = hashlib.sha256(b"test-content").hexdigest()
            sources = [
                create_mock_installed_source("test-pack", "1.0", "MIT", content_hash)
            ]

            with patch(
                "redletters.sources.lockfile.SourceInstaller"
            ) as mock_installer_cls:
                mock_installer = MagicMock()
                mock_installer.manifest = create_mock_manifest(sources)
                mock_installer.get_installed.side_effect = lambda sid: next(
                    (s for s in sources if s.source_id == sid), None
                )
                mock_installer.get_sense_pack_status.return_value = []
                mock_installer_cls.return_value = mock_installer

                with patch(
                    "redletters.sources.lockfile.SourceCatalog"
                ) as mock_catalog_cls:
                    mock_catalog = MagicMock()
                    mock_catalog.get.return_value = None
                    mock_catalog_cls.load.return_value = mock_catalog

                    # Generate lockfile
                    generator = LockfileGenerator(data_root=Path(tmpdir))
                    lockfile_path = Path(tmpdir) / "lock.json"
                    lockfile = generator.save(lockfile_path)

                    # Verify against same environment
                    loaded_lockfile = Lockfile.load(lockfile_path)
                    syncer = LockfileSyncer(data_root=Path(tmpdir))
                    result = syncer.verify(loaded_lockfile)

                    assert result.valid is True
                    assert result.ok_count == 1
