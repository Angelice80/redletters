"""Tests for pack lockfile generation and verification (v0.11.0)."""

import json
import tempfile
from pathlib import Path


from redletters.sources.lockfile import (
    LOCKFILE_SCHEMA_VERSION,
    TOOL_VERSION,
    Lockfile,
    LockfileInstallSource,
    LockfilePack,
    PackSyncStatus,
    SyncResult,
)


class TestLockfileInstallSource:
    """Tests for LockfileInstallSource dataclass."""

    def test_to_dict_catalog(self):
        source = LockfileInstallSource(
            type="catalog",
            catalog_id="morphgnt-sblgnt",
        )
        d = source.to_dict()
        assert d["type"] == "catalog"
        assert d["catalog_id"] == "morphgnt-sblgnt"
        assert "path" not in d
        assert "url" not in d

    def test_to_dict_git(self):
        source = LockfileInstallSource(
            type="git",
            catalog_id="morphgnt-sblgnt",
            url="https://github.com/morphgnt/sblgnt.git",
            revision="abc123",
        )
        d = source.to_dict()
        assert d["type"] == "git"
        assert d["url"] == "https://github.com/morphgnt/sblgnt.git"
        assert d["revision"] == "abc123"

    def test_from_dict(self):
        data = {
            "type": "local",
            "path": "/data/packs/test",
        }
        source = LockfileInstallSource.from_dict(data)
        assert source.type == "local"
        assert source.path == "/data/packs/test"


class TestLockfilePack:
    """Tests for LockfilePack dataclass."""

    def test_to_dict(self):
        pack = LockfilePack(
            pack_id="morphgnt-sblgnt",
            version="1.0.0",
            role="spine",
            license="CC-BY-SA-4.0",
            content_hash="a" * 64,
            install_source=LockfileInstallSource(
                type="catalog",
                catalog_id="morphgnt-sblgnt",
            ),
        )
        d = pack.to_dict()
        assert d["pack_id"] == "morphgnt-sblgnt"
        assert d["version"] == "1.0.0"
        assert d["role"] == "spine"
        assert d["license"] == "CC-BY-SA-4.0"
        assert d["content_hash"] == "a" * 64
        assert d["install_source"]["type"] == "catalog"

    def test_from_dict(self):
        data = {
            "pack_id": "test-pack",
            "version": "2.0",
            "role": "comparative",
            "license": "MIT",
            "content_hash": "b" * 64,
        }
        pack = LockfilePack.from_dict(data)
        assert pack.pack_id == "test-pack"
        assert pack.role == "comparative"
        assert pack.install_source is None


class TestLockfile:
    """Tests for Lockfile dataclass."""

    def test_to_json_determinism(self):
        """Verify JSON output is deterministic (sorted keys)."""
        lockfile = Lockfile(
            tool_version=TOOL_VERSION,
            schema_version=LOCKFILE_SCHEMA_VERSION,
            generated_at="2024-01-01T00:00:00Z",
            packs=[
                LockfilePack(
                    pack_id="z-pack",
                    version="1.0",
                    role="comparative",
                    license="MIT",
                    content_hash="z" * 64,
                ),
                LockfilePack(
                    pack_id="a-pack",
                    version="1.0",
                    role="spine",
                    license="MIT",
                    content_hash="a" * 64,
                ),
            ],
        )

        json1 = lockfile.to_json()
        json2 = lockfile.to_json()

        assert json1 == json2
        # Verify sorted keys
        data = json.loads(json1)
        keys = list(data.keys())
        assert keys == sorted(keys)

    def test_compute_hash_stability(self):
        """Verify hash computation is stable across runs."""
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
                ),
            ],
        )

        hash1 = lockfile.compute_hash()
        hash2 = lockfile.compute_hash()

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_compute_hash_changes_with_content(self):
        """Verify hash changes when content changes."""
        lockfile1 = Lockfile(
            tool_version=TOOL_VERSION,
            schema_version=LOCKFILE_SCHEMA_VERSION,
            generated_at="2024-01-01T00:00:00Z",
            packs=[],
        )

        lockfile2 = Lockfile(
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
                ),
            ],
        )

        assert lockfile1.compute_hash() != lockfile2.compute_hash()

    def test_save_and_load(self):
        """Verify round-trip serialization."""
        lockfile = Lockfile(
            tool_version=TOOL_VERSION,
            schema_version=LOCKFILE_SCHEMA_VERSION,
            generated_at="2024-01-01T00:00:00Z",
            packs=[
                LockfilePack(
                    pack_id="test-pack",
                    version="1.0",
                    role="sense_pack",
                    license="MIT",
                    content_hash="a" * 64,
                    install_source=LockfileInstallSource(
                        type="local",
                        path="/data/test",
                    ),
                ),
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "lock.json"
            lockfile.save(path)

            loaded = Lockfile.load(path)

            assert loaded.tool_version == lockfile.tool_version
            assert loaded.schema_version == lockfile.schema_version
            assert loaded.generated_at == lockfile.generated_at
            assert len(loaded.packs) == 1
            assert loaded.packs[0].pack_id == "test-pack"
            assert loaded.packs[0].install_source.type == "local"
            # Hash should be computed on save
            assert loaded.lockfile_hash == lockfile.compute_hash()


class TestPackSyncStatus:
    """Tests for PackSyncStatus dataclass."""

    def test_to_dict_minimal(self):
        status = PackSyncStatus(pack_id="test", status="ok")
        d = status.to_dict()
        assert d["pack_id"] == "test"
        assert d["status"] == "ok"
        assert "expected_hash" not in d
        assert "message" not in d

    def test_to_dict_full(self):
        status = PackSyncStatus(
            pack_id="test",
            status="hash_mismatch",
            expected_hash="a" * 64,
            actual_hash="b" * 64,
            message="Content differs",
        )
        d = status.to_dict()
        assert d["expected_hash"] == "a" * 64
        assert d["actual_hash"] == "b" * 64
        assert d["message"] == "Content differs"


class TestSyncResult:
    """Tests for SyncResult dataclass."""

    def test_ok_count(self):
        result = SyncResult(
            valid=True,
            packs=[
                PackSyncStatus(pack_id="a", status="ok"),
                PackSyncStatus(pack_id="b", status="ok"),
                PackSyncStatus(pack_id="c", status="missing"),
            ],
        )
        assert result.ok_count == 2

    def test_to_dict_forced(self):
        result = SyncResult(
            valid=True,
            packs=[],
            forced=True,
            forced_at="2024-01-01T00:00:00Z",
        )
        d = result.to_dict()
        assert d["forced"] is True
        assert d["forced_at"] == "2024-01-01T00:00:00Z"


class TestLockfileSchema:
    """Tests for lockfile schema compliance."""

    def test_lockfile_includes_schema_version(self):
        lockfile = Lockfile(
            tool_version=TOOL_VERSION,
            schema_version=LOCKFILE_SCHEMA_VERSION,
            generated_at="2024-01-01T00:00:00Z",
            packs=[],
        )
        d = lockfile.to_dict()
        assert d["schema_version"] == "1.0.0"

    def test_lockfile_pack_role_enum(self):
        """Verify pack roles are valid enum values."""
        for role in ["spine", "comparative", "sense_pack"]:
            pack = LockfilePack(
                pack_id="test",
                version="1.0",
                role=role,
                license="MIT",
                content_hash="a" * 64,
            )
            assert pack.role == role

    def test_lockfile_json_valid(self):
        """Verify generated JSON is valid."""
        lockfile = Lockfile(
            tool_version=TOOL_VERSION,
            schema_version=LOCKFILE_SCHEMA_VERSION,
            generated_at="2024-01-01T00:00:00Z",
            packs=[
                LockfilePack(
                    pack_id="test",
                    version="1.0",
                    role="spine",
                    license="MIT",
                    content_hash="a" * 64,
                ),
            ],
        )
        lockfile.lockfile_hash = lockfile.compute_hash()

        json_str = lockfile.to_json()
        parsed = json.loads(json_str)

        assert "tool_version" in parsed
        assert "schema_version" in parsed
        assert "generated_at" in parsed
        assert "packs" in parsed
        assert "lockfile_hash" in parsed
        assert len(parsed["lockfile_hash"]) == 64
