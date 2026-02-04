"""Tests for research bundle creation and verification (v0.12.0).

Tests deterministic bundle creation, hash verification, and tamper detection.
"""

from __future__ import annotations

import json
import zipfile

import pytest

from redletters.export.bundle import (
    ArtifactEntry,
    BundleCreator,
    BundleManifest,
    BundleVerifier,
    BUNDLE_SCHEMA_VERSION,
    TOOL_VERSION,
    create_bundle,
    verify_bundle,
)
from redletters.export.identifiers import file_hash


class TestArtifactEntry:
    """Tests for ArtifactEntry dataclass."""

    def test_to_dict_basic(self):
        """ArtifactEntry serializes to dict."""
        entry = ArtifactEntry(
            path="apparatus.jsonl",
            artifact_type="apparatus",
            sha256="a" * 64,
        )
        d = entry.to_dict()
        assert d["path"] == "apparatus.jsonl"
        assert d["artifact_type"] == "apparatus"
        assert d["sha256"] == "a" * 64
        assert "schema_version" not in d  # Not set

    def test_to_dict_with_schema_version(self):
        """ArtifactEntry includes schema_version when set."""
        entry = ArtifactEntry(
            path="snapshot.json",
            artifact_type="snapshot",
            sha256="b" * 64,
            schema_version="1.0.0",
        )
        d = entry.to_dict()
        assert d["schema_version"] == "1.0.0"

    def test_from_dict_roundtrip(self):
        """ArtifactEntry round-trips through dict."""
        entry = ArtifactEntry(
            path="translation.jsonl",
            artifact_type="translation",
            sha256="c" * 64,
            schema_version="1.0.0",
        )
        d = entry.to_dict()
        restored = ArtifactEntry.from_dict(d)
        assert restored.path == entry.path
        assert restored.artifact_type == entry.artifact_type
        assert restored.sha256 == entry.sha256
        assert restored.schema_version == entry.schema_version


class TestBundleManifest:
    """Tests for BundleManifest dataclass."""

    def test_to_json_deterministic(self):
        """BundleManifest produces deterministic JSON."""
        manifest = BundleManifest(
            schema_version="1.0.0",
            tool_version="0.12.0",
            created_utc="2026-02-02T12:00:00Z",
            lockfile_hash="a" * 64,
            snapshot_hash="b" * 64,
            artifacts=[
                ArtifactEntry(
                    path="a.jsonl", artifact_type="apparatus", sha256="c" * 64
                ),
            ],
        )
        json1 = manifest.to_json(pretty=False)
        json2 = manifest.to_json(pretty=False)
        assert json1 == json2

    def test_compute_content_hash_deterministic(self):
        """Content hash is deterministic regardless of artifact order."""
        artifacts = [
            ArtifactEntry(path="a.jsonl", artifact_type="apparatus", sha256="c" * 64),
            ArtifactEntry(path="t.jsonl", artifact_type="translation", sha256="d" * 64),
        ]
        manifest1 = BundleManifest(
            schema_version="1.0.0",
            tool_version="0.12.0",
            created_utc="2026-02-02T12:00:00Z",
            lockfile_hash="a" * 64,
            snapshot_hash="b" * 64,
            artifacts=artifacts,
        )
        # Reverse artifact order
        manifest2 = BundleManifest(
            schema_version="1.0.0",
            tool_version="0.12.0",
            created_utc="2026-02-02T12:00:00Z",
            lockfile_hash="a" * 64,
            snapshot_hash="b" * 64,
            artifacts=list(reversed(artifacts)),
        )
        # Content hash should be the same (sorted internally)
        assert manifest1.compute_content_hash() == manifest2.compute_content_hash()

    def test_load_save_roundtrip(self, tmp_path):
        """BundleManifest can be saved and loaded."""
        manifest = BundleManifest(
            schema_version="1.0.0",
            tool_version="0.12.0",
            created_utc="2026-02-02T12:00:00Z",
            lockfile_hash="a" * 64,
            snapshot_hash="b" * 64,
            artifacts=[
                ArtifactEntry(
                    path="a.jsonl", artifact_type="apparatus", sha256="c" * 64
                ),
            ],
            content_hash="e" * 64,
            schemas_included=True,
            notes="Test bundle",
        )
        manifest_path = tmp_path / "manifest.json"
        manifest.save(manifest_path)

        loaded = BundleManifest.load(manifest_path)
        assert loaded.schema_version == manifest.schema_version
        assert loaded.tool_version == manifest.tool_version
        assert loaded.lockfile_hash == manifest.lockfile_hash
        assert loaded.snapshot_hash == manifest.snapshot_hash
        assert loaded.content_hash == manifest.content_hash
        assert loaded.schemas_included == manifest.schemas_included
        assert loaded.notes == manifest.notes
        assert len(loaded.artifacts) == 1


class TestBundleCreator:
    """Tests for BundleCreator."""

    @pytest.fixture
    def sample_files(self, tmp_path):
        """Create sample files for testing."""
        # Create lockfile
        lockfile = tmp_path / "lockfile.json"
        lockfile.write_text(
            json.dumps(
                {
                    "tool_version": "0.11.0",
                    "schema_version": "1.0.0",
                    "generated_at": "2026-02-02T12:00:00Z",
                    "packs": [],
                }
            ),
            encoding="utf-8",
        )

        # Create snapshot
        snapshot = tmp_path / "snapshot.json"
        snapshot.write_text(
            json.dumps(
                {
                    "tool_version": "0.10.0",
                    "schema_version": "1.0.0",
                    "git_commit": None,
                    "timestamp": "2026-02-02T12:00:00Z",
                    "packs": [],
                    "export_hashes": {},
                }
            ),
            encoding="utf-8",
        )

        # Create apparatus output
        apparatus = tmp_path / "apparatus.jsonl"
        apparatus.write_text(
            json.dumps(
                {
                    "variant_unit_id": "John.1.1:0",
                    "verse_id": "John.1.1",
                    "readings": [{"text": "test"}],
                    "schema_version": "1.0.0",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        return {
            "lockfile": lockfile,
            "snapshot": snapshot,
            "apparatus": apparatus,
        }

    def test_create_basic_bundle(self, tmp_path, sample_files):
        """Creates a basic bundle with required files."""
        output_dir = tmp_path / "bundle"
        creator = BundleCreator()
        result = creator.create(
            output_dir=output_dir,
            lockfile_path=sample_files["lockfile"],
            snapshot_path=sample_files["snapshot"],
            input_paths=[sample_files["apparatus"]],
        )

        assert result.success
        assert result.bundle_path == output_dir
        assert result.manifest is not None
        assert len(result.manifest.artifacts) == 3  # lockfile, snapshot, apparatus
        assert (output_dir / "manifest.json").exists()
        assert (output_dir / "lockfile.json").exists()
        assert (output_dir / "snapshot.json").exists()
        assert (output_dir / "apparatus.jsonl").exists()

    def test_create_bundle_with_zip(self, tmp_path, sample_files):
        """Creates a bundle with zip archive."""
        output_dir = tmp_path / "bundle"
        creator = BundleCreator()
        result = creator.create(
            output_dir=output_dir,
            lockfile_path=sample_files["lockfile"],
            snapshot_path=sample_files["snapshot"],
            input_paths=[sample_files["apparatus"]],
            create_zip=True,
        )

        assert result.success
        zip_path = output_dir.with_suffix(".zip")
        assert zip_path.exists()

        # Verify zip contents
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            assert "manifest.json" in names
            assert "lockfile.json" in names
            assert "snapshot.json" in names
            assert "apparatus.jsonl" in names

    def test_create_bundle_fails_missing_lockfile(self, tmp_path, sample_files):
        """Fails when lockfile is missing."""
        output_dir = tmp_path / "bundle"
        creator = BundleCreator()
        result = creator.create(
            output_dir=output_dir,
            lockfile_path=tmp_path / "nonexistent.json",
            snapshot_path=sample_files["snapshot"],
            input_paths=[sample_files["apparatus"]],
        )

        assert not result.success
        assert any("Lockfile not found" in e for e in result.errors)

    def test_create_bundle_fails_missing_snapshot(self, tmp_path, sample_files):
        """Fails when snapshot is missing."""
        output_dir = tmp_path / "bundle"
        creator = BundleCreator()
        result = creator.create(
            output_dir=output_dir,
            lockfile_path=sample_files["lockfile"],
            snapshot_path=tmp_path / "nonexistent.json",
            input_paths=[sample_files["apparatus"]],
        )

        assert not result.success
        assert any("Snapshot not found" in e for e in result.errors)

    def test_create_bundle_fails_no_inputs(self, tmp_path, sample_files):
        """Fails when no valid inputs provided."""
        output_dir = tmp_path / "bundle"
        creator = BundleCreator()
        result = creator.create(
            output_dir=output_dir,
            lockfile_path=sample_files["lockfile"],
            snapshot_path=sample_files["snapshot"],
            input_paths=[tmp_path / "nonexistent.jsonl"],
        )

        assert not result.success
        assert any("No valid input artifacts" in e for e in result.errors)

    def test_artifacts_sorted_deterministically(self, tmp_path, sample_files):
        """Artifacts are sorted by type then path."""
        # Create additional files
        translation = tmp_path / "translation.jsonl"
        translation.write_text(
            json.dumps(
                {
                    "verse_id": "John.1.1",
                    "tokens": [],
                    "confidence_summary": {},
                    "schema_version": "1.0.0",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        output_dir = tmp_path / "bundle"
        creator = BundleCreator()
        result = creator.create(
            output_dir=output_dir,
            lockfile_path=sample_files["lockfile"],
            snapshot_path=sample_files["snapshot"],
            input_paths=[translation, sample_files["apparatus"]],  # Reverse order
        )

        assert result.success
        # Check order: apparatus before translation (alphabetical by type)
        types = [a.artifact_type for a in result.manifest.artifacts]
        assert types == ["apparatus", "lockfile", "snapshot", "translation"]


class TestBundleVerifier:
    """Tests for BundleVerifier."""

    @pytest.fixture
    def sample_bundle(self, tmp_path):
        """Create a sample bundle for testing."""
        bundle_dir = tmp_path / "bundle"
        bundle_dir.mkdir()

        # Create lockfile
        lockfile = bundle_dir / "lockfile.json"
        lockfile_content = json.dumps(
            {
                "tool_version": "0.11.0",
                "schema_version": "1.0.0",
                "generated_at": "2026-02-02T12:00:00Z",
                "packs": [],
            }
        )
        lockfile.write_text(lockfile_content, encoding="utf-8")

        # Create snapshot
        snapshot = bundle_dir / "snapshot.json"
        snapshot_content = json.dumps(
            {
                "tool_version": "0.10.0",
                "schema_version": "1.0.0",
                "git_commit": None,
                "timestamp": "2026-02-02T12:00:00Z",
                "packs": [],
                "export_hashes": {},
            }
        )
        snapshot.write_text(snapshot_content, encoding="utf-8")

        # Create apparatus
        apparatus = bundle_dir / "apparatus.jsonl"
        apparatus_content = (
            json.dumps(
                {
                    "variant_unit_id": "John.1.1:0",
                    "verse_id": "John.1.1",
                    "readings": [{"text": "test"}],
                    "schema_version": "1.0.0",
                }
            )
            + "\n"
        )
        apparatus.write_text(apparatus_content, encoding="utf-8")

        # Create manifest
        manifest = BundleManifest(
            schema_version=BUNDLE_SCHEMA_VERSION,
            tool_version=TOOL_VERSION,
            created_utc="2026-02-02T12:00:00Z",
            lockfile_hash=file_hash(str(lockfile)),
            snapshot_hash=file_hash(str(snapshot)),
            artifacts=[
                ArtifactEntry(
                    path="apparatus.jsonl",
                    artifact_type="apparatus",
                    sha256=file_hash(str(apparatus)),
                    schema_version="1.0.0",
                ),
                ArtifactEntry(
                    path="lockfile.json",
                    artifact_type="lockfile",
                    sha256=file_hash(str(lockfile)),
                    schema_version="1.0.0",
                ),
                ArtifactEntry(
                    path="snapshot.json",
                    artifact_type="snapshot",
                    sha256=file_hash(str(snapshot)),
                    schema_version="1.0.0",
                ),
            ],
        )
        manifest.content_hash = manifest.compute_content_hash()
        manifest.save(bundle_dir / "manifest.json")

        return bundle_dir

    def test_verify_valid_bundle(self, sample_bundle):
        """Verifies a valid bundle."""
        verifier = BundleVerifier()
        result = verifier.verify(
            sample_bundle, check_snapshot=False, check_outputs=False
        )

        assert result.valid
        assert len(result.errors) == 0
        assert len(result.file_checks) == 3
        assert all(fc["status"] == "ok" for fc in result.file_checks.values())

    def test_verify_detects_missing_file(self, sample_bundle):
        """Detects missing artifact file."""
        # Remove apparatus file
        (sample_bundle / "apparatus.jsonl").unlink()

        verifier = BundleVerifier()
        result = verifier.verify(
            sample_bundle, check_snapshot=False, check_outputs=False
        )

        assert not result.valid
        assert any("Missing artifact" in e for e in result.errors)

    def test_verify_detects_tampered_file(self, sample_bundle):
        """Detects tampered artifact file."""
        # Modify apparatus file
        apparatus = sample_bundle / "apparatus.jsonl"
        apparatus.write_text("TAMPERED CONTENT\n", encoding="utf-8")

        verifier = BundleVerifier()
        result = verifier.verify(
            sample_bundle, check_snapshot=False, check_outputs=False
        )

        assert not result.valid
        assert any("Hash mismatch" in e for e in result.errors)
        assert result.file_checks["apparatus.jsonl"]["status"] == "hash_mismatch"

    def test_verify_detects_tampered_lockfile(self, sample_bundle):
        """Detects tampered lockfile."""
        lockfile = sample_bundle / "lockfile.json"
        lockfile.write_text('{"tampered": true}', encoding="utf-8")

        verifier = BundleVerifier()
        result = verifier.verify(
            sample_bundle, check_snapshot=False, check_outputs=False
        )

        assert not result.valid
        assert any("Hash mismatch" in e for e in result.errors)

    def test_verify_detects_missing_manifest(self, sample_bundle):
        """Detects missing manifest."""
        (sample_bundle / "manifest.json").unlink()

        verifier = BundleVerifier()
        result = verifier.verify(
            sample_bundle, check_snapshot=False, check_outputs=False
        )

        assert not result.valid
        assert any("manifest.json not found" in e for e in result.errors)

    def test_verify_zip_bundle(self, sample_bundle):
        """Verifies a zip bundle."""
        # Create zip from bundle
        zip_path = sample_bundle.with_suffix(".zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            for file in sample_bundle.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(sample_bundle))

        verifier = BundleVerifier()
        result = verifier.verify(zip_path, check_snapshot=False, check_outputs=False)

        assert result.valid


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.fixture
    def sample_files(self, tmp_path):
        """Create sample files for testing."""
        lockfile = tmp_path / "lockfile.json"
        lockfile.write_text(
            json.dumps(
                {
                    "tool_version": "0.11.0",
                    "schema_version": "1.0.0",
                    "generated_at": "2026-02-02T12:00:00Z",
                    "packs": [],
                }
            ),
            encoding="utf-8",
        )

        snapshot = tmp_path / "snapshot.json"
        snapshot.write_text(
            json.dumps(
                {
                    "tool_version": "0.10.0",
                    "schema_version": "1.0.0",
                    "git_commit": None,
                    "timestamp": "2026-02-02T12:00:00Z",
                    "packs": [],
                    "export_hashes": {},
                }
            ),
            encoding="utf-8",
        )

        apparatus = tmp_path / "apparatus.jsonl"
        apparatus.write_text(
            json.dumps(
                {
                    "variant_unit_id": "John.1.1:0",
                    "verse_id": "John.1.1",
                    "readings": [{"text": "test"}],
                    "schema_version": "1.0.0",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        return {
            "lockfile": lockfile,
            "snapshot": snapshot,
            "apparatus": apparatus,
        }

    def test_create_bundle_function(self, tmp_path, sample_files):
        """create_bundle convenience function works."""
        output_dir = tmp_path / "bundle"
        result = create_bundle(
            output_dir=output_dir,
            lockfile_path=sample_files["lockfile"],
            snapshot_path=sample_files["snapshot"],
            input_paths=[sample_files["apparatus"]],
        )

        assert result.success
        assert (output_dir / "manifest.json").exists()

    def test_verify_bundle_function(self, tmp_path, sample_files):
        """verify_bundle convenience function works."""
        output_dir = tmp_path / "bundle"
        create_result = create_bundle(
            output_dir=output_dir,
            lockfile_path=sample_files["lockfile"],
            snapshot_path=sample_files["snapshot"],
            input_paths=[sample_files["apparatus"]],
        )

        assert create_result.success

        verify_result = verify_bundle(
            bundle_path=output_dir,
            check_snapshot=False,
            check_outputs=False,
        )

        assert verify_result.valid


class TestContentHashDeterminism:
    """Tests for deterministic content hashing."""

    def test_same_content_same_hash(self, tmp_path):
        """Same content produces same content hash."""
        # Create two bundles with same content
        for i in range(2):
            bundle_dir = tmp_path / f"bundle{i}"
            bundle_dir.mkdir()

            lockfile = bundle_dir / "lockfile.json"
            lockfile.write_text(
                json.dumps(
                    {
                        "tool_version": "0.11.0",
                        "schema_version": "1.0.0",
                        "generated_at": "2026-02-02T12:00:00Z",
                        "packs": [],
                    }
                ),
                encoding="utf-8",
            )

            snapshot = bundle_dir / "snapshot.json"
            snapshot.write_text(
                json.dumps(
                    {
                        "tool_version": "0.10.0",
                        "schema_version": "1.0.0",
                        "git_commit": None,
                        "timestamp": "2026-02-02T12:00:00Z",
                        "packs": [],
                        "export_hashes": {},
                    }
                ),
                encoding="utf-8",
            )

            apparatus = bundle_dir / "apparatus.jsonl"
            apparatus.write_text(
                json.dumps(
                    {
                        "variant_unit_id": "John.1.1:0",
                        "verse_id": "John.1.1",
                        "readings": [{"text": "test"}],
                        "schema_version": "1.0.0",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

        # Create bundles
        creator = BundleCreator()
        results = []
        for i in range(2):
            bundle_dir = tmp_path / f"bundle{i}"
            output_dir = tmp_path / f"output{i}"
            result = creator.create(
                output_dir=output_dir,
                lockfile_path=bundle_dir / "lockfile.json",
                snapshot_path=bundle_dir / "snapshot.json",
                input_paths=[bundle_dir / "apparatus.jsonl"],
            )
            results.append(result)

        # Content hashes should match
        assert results[0].manifest.content_hash == results[1].manifest.content_hash

    def test_different_content_different_hash(self, tmp_path):
        """Different content produces different content hash."""
        # Create two bundles with different content
        for i in range(2):
            bundle_dir = tmp_path / f"bundle{i}"
            bundle_dir.mkdir()

            lockfile = bundle_dir / "lockfile.json"
            lockfile.write_text(
                json.dumps(
                    {
                        "tool_version": "0.11.0",
                        "schema_version": "1.0.0",
                        "generated_at": "2026-02-02T12:00:00Z",
                        "packs": [],
                    }
                ),
                encoding="utf-8",
            )

            snapshot = bundle_dir / "snapshot.json"
            snapshot.write_text(
                json.dumps(
                    {
                        "tool_version": "0.10.0",
                        "schema_version": "1.0.0",
                        "git_commit": None,
                        "timestamp": "2026-02-02T12:00:00Z",
                        "packs": [],
                        "export_hashes": {},
                    }
                ),
                encoding="utf-8",
            )

            apparatus = bundle_dir / "apparatus.jsonl"
            # Different content for each bundle
            apparatus.write_text(
                json.dumps(
                    {
                        "variant_unit_id": f"John.1.{i}:0",
                        "verse_id": f"John.1.{i}",
                        "readings": [{"text": f"test{i}"}],
                        "schema_version": "1.0.0",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

        # Create bundles
        creator = BundleCreator()
        results = []
        for i in range(2):
            bundle_dir = tmp_path / f"bundle{i}"
            output_dir = tmp_path / f"output{i}"
            result = creator.create(
                output_dir=output_dir,
                lockfile_path=bundle_dir / "lockfile.json",
                snapshot_path=bundle_dir / "snapshot.json",
                input_paths=[bundle_dir / "apparatus.jsonl"],
            )
            results.append(result)

        # Content hashes should differ
        assert results[0].manifest.content_hash != results[1].manifest.content_hash
