"""Tests for fetch provenance and commit pinning.

These tests verify that:
1. Catalog commits match snapshot manifests (hard assertion)
2. Marker files contain commit info when catalog specifies it
3. Floating refs are rejected by default
4. Delimiter detection is receipt-grade
"""

from pathlib import Path

import pytest
import yaml

from redletters.ingest.fetch import (
    MARKER_KEYS,
    SourceSpec,
    catalog_to_source_spec,
    load_sources_catalog,
    read_marker,
    write_marker,
)
from redletters.ingest.morphgnt_parser import (
    DelimiterAmbiguityError,
    detect_delimiter,
    parse_file,
)


# Path to snapshot manifest
SNAPSHOT_DIR = Path(__file__).parent / "data" / "morphgnt-snapshot"
MANIFEST_PATH = SNAPSHOT_DIR / "MANIFEST.yaml"
CATALOG_PATH = Path(__file__).parent.parent / "sources_catalog.yaml"


class TestSnapshotCommitMatchesCatalog:
    """Verify snapshot manifest commit equals catalog commit (hard assertion)."""

    def test_snapshot_commit_matches_catalog(self):
        """The test snapshot commit must match the pinned commit in sources_catalog.yaml.

        This is a constitutional constraint: if someone swaps the snapshot
        without updating the catalog, tests may silently pass on wrong data.
        """
        # Load catalog
        catalog = load_sources_catalog(CATALOG_PATH)
        assert "morphgnt-sblgnt" in catalog, "Catalog should have morphgnt-sblgnt"
        catalog_commit = catalog["morphgnt-sblgnt"].get("commit")
        assert catalog_commit, "Catalog should have pinned commit"

        # Load snapshot manifest
        assert MANIFEST_PATH.exists(), f"Manifest should exist: {MANIFEST_PATH}"
        with open(MANIFEST_PATH) as f:
            manifest = yaml.safe_load(f)

        manifest_commit = manifest.get("source", {}).get("commit")
        assert manifest_commit, "Manifest should have source.commit"

        # Hard assertion: commits must match
        assert manifest_commit == catalog_commit, (
            f"Snapshot commit mismatch!\n"
            f"  Catalog: {catalog_commit}\n"
            f"  Manifest: {manifest_commit}\n"
            f"Either update the catalog to match the snapshot, "
            f"or regenerate the snapshot from the catalog commit."
        )


class TestMarkerContainsCommitWhenPinned:
    """Verify .fetched marker contains git_commit when catalog specifies it."""

    def test_marker_contains_commit_when_catalog_pins_it(self, tmp_path):
        """write_marker should include git_commit field from metadata."""
        meta = {
            "name": "MorphGNT-SBLGNT",
            "version": "6.12",
            "license": "CC-BY-SA-3.0",
            "url": "https://github.com/morphgnt/sblgnt",
            "retrieved_at": "2026-01-27T00:00:00-05:00",
            "sha256": "abc123",
            "git_commit": "b4d1e66a22c389aae24fe6e4e80db34e1e5c0b11",
            "git_tag": "",
            "files": "61-Mt-morphgnt.txt",
            "notes": "Test marker",
        }
        marker = tmp_path / ".fetched"
        write_marker(marker, meta)

        # Read back and verify
        text = marker.read_text(encoding="utf-8")
        assert "git_commit=b4d1e66a22c389aae24fe6e4e80db34e1e5c0b11" in text
        assert "git_tag=" in text  # Empty but present

        # Verify via read_marker
        read_meta = read_marker(marker)
        assert read_meta["git_commit"] == "b4d1e66a22c389aae24fe6e4e80db34e1e5c0b11"

    def test_marker_always_has_all_keys(self, tmp_path):
        """Marker should always write all MARKER_KEYS, even if empty."""
        meta = {
            "name": "Test Source",
            "version": "1.0",
            "license": "MIT",
            # Missing many fields
        }
        marker = tmp_path / ".fetched"
        write_marker(marker, meta)

        text = marker.read_text(encoding="utf-8")

        # All keys should be present (even if empty)
        for key in MARKER_KEYS:
            assert f"{key}=" in text, f"Marker should have {key}= line"

    def test_marker_keys_in_stable_order(self, tmp_path):
        """Marker keys should always be in MARKER_KEYS order."""
        meta = {
            # Deliberately out of order
            "notes": "Some notes",
            "name": "Test",
            "sha256": "abc",
            "version": "1.0",
            "license": "MIT",
            "url": "http://test",
            "retrieved_at": "2026-01-01",
            "git_commit": "abc123",
            "git_tag": "v1.0",
            "files": "a.txt,b.txt",
        }
        marker = tmp_path / ".fetched"
        write_marker(marker, meta)

        lines = marker.read_text().strip().split("\n")
        keys_found = [line.split("=")[0] for line in lines]

        assert keys_found == MARKER_KEYS, (
            f"Keys should be in stable order:\n"
            f"  Expected: {MARKER_KEYS}\n"
            f"  Got: {keys_found}"
        )


class TestSourceSpecModes:
    """Test SourceSpec pinned vs floating detection."""

    def test_is_pinned_true_when_full_sha_and_files_and_repo(self):
        """is_pinned() should return True when full SHA + files + valid repo."""
        spec = SourceSpec(
            name="Test",
            version="1.0",
            license="MIT",
            repo="https://github.com/owner/project",
            git_commit="b4d1e66a22c389aae24fe6e4e80db34e1e5c0b11",  # Full 40-char SHA
            files=["file1.txt", "file2.txt"],
        )
        assert spec.is_pinned() is True
        assert spec.owner == "owner"
        assert spec.project == "project"

    def test_is_pinned_false_when_abbreviated_sha(self):
        """is_pinned() should return False for abbreviated SHAs."""
        spec = SourceSpec(
            name="Test",
            version="1.0",
            license="MIT",
            repo="https://github.com/owner/project",
            git_commit="abc123",  # Abbreviated - not pinned
            files=["file1.txt"],
        )
        assert spec.is_pinned() is False

    def test_is_pinned_false_when_missing_repo(self):
        """is_pinned() should return False when repo missing."""
        spec = SourceSpec(
            name="Test",
            version="1.0",
            license="MIT",
            git_commit="b4d1e66a22c389aae24fe6e4e80db34e1e5c0b11",
            files=["file1.txt"],
        )
        assert spec.is_pinned() is False

    def test_is_floating_true_for_branch_names(self):
        """is_floating() should return True for branch names."""
        for ref in ["master", "main", "HEAD", "develop", ""]:
            spec = SourceSpec(
                name="Test",
                version="1.0",
                license="MIT",
                git_commit=ref,
            )
            assert spec.is_floating() is True, f"'{ref}' should be floating"

    def test_is_floating_true_for_abbreviated_sha(self):
        """is_floating() should return True for abbreviated SHAs."""
        spec = SourceSpec(
            name="Test",
            version="1.0",
            license="MIT",
            git_commit="abc123def",  # 9 chars - abbreviated
        )
        assert spec.is_floating() is True

    def test_is_floating_false_for_full_sha(self):
        """is_floating() should return False only for full 40-char SHAs."""
        spec = SourceSpec(
            name="Test",
            version="1.0",
            license="MIT",
            git_commit="b4d1e66a22c389aae24fe6e4e80db34e1e5c0b11",
        )
        assert spec.is_floating() is False

    def test_owner_project_derived_from_repo(self):
        """owner and project should be derived from repo URL."""
        spec = SourceSpec(
            name="Test",
            version="1.0",
            license="MIT",
            repo="https://github.com/morphgnt/sblgnt",
        )
        assert spec.owner == "morphgnt"
        assert spec.project == "sblgnt"

    def test_owner_project_none_when_no_repo(self):
        """owner and project should be None when repo not set."""
        spec = SourceSpec(
            name="Test",
            version="1.0",
            license="MIT",
        )
        assert spec.owner is None
        assert spec.project is None


class TestDelimiterDetection:
    """Test receipt-grade delimiter detection."""

    def test_detect_tab_delimiter(self):
        """Should detect TAB when line has tabs."""
        line = "010503\tV-\t3PAAI---\tἀκούσατε\tακουσατε\tἀκούω"
        assert detect_delimiter(line) == "TAB"

    def test_detect_space_delimiter(self):
        """Should detect SPACE when line has only spaces."""
        line = "010503 V- 3PAAI--- ἀκούσατε ακουσατε ἀκούω"
        assert detect_delimiter(line) == "SPACE"

    def test_ambiguous_raises_error(self):
        """Should raise DelimiterAmbiguityError when both tabs and multi-space."""
        line = "010503\tV-  3PAAI---\tἀκούσατε"  # Tab + multi-space
        with pytest.raises(DelimiterAmbiguityError):
            detect_delimiter(line, line_number=1)

    def test_parse_file_returns_delimiter(self):
        """parse_file should return detected delimiter."""
        # Use the sample fixture
        sample_path = Path(__file__).parent / "fixtures" / "morphgnt_sample.tsv"
        if sample_path.exists():
            tokens, delimiter = parse_file_with_delimiter(sample_path)
            assert delimiter in ("TAB", "SPACE"), (
                f"Should detect delimiter: {delimiter}"
            )
            assert len(tokens) > 0, "Should parse tokens"


class TestCatalogLoading:
    """Test catalog loading and conversion."""

    def test_load_sources_catalog(self):
        """Should load catalog from repo root."""
        catalog = load_sources_catalog(CATALOG_PATH)
        assert isinstance(catalog, dict)
        assert "morphgnt-sblgnt" in catalog

    def test_catalog_to_source_spec(self):
        """Should convert catalog entry to SourceSpec."""
        config = {
            "name": "Test Source",
            "repo": "https://github.com/test/repo",
            "commit": "b4d1e66a22c389aae24fe6e4e80db34e1e5c0b11",  # Full SHA
            "git_tag": "v1.0",
            "version": "1.0",
            "license": "MIT",
            "files": ["file1.txt", "file2.txt"],
            "notes": "Test notes",
        }
        spec = catalog_to_source_spec("test-source", config)

        assert spec.name == "Test Source"
        assert spec.repo == "https://github.com/test/repo"
        assert spec.owner == "test"  # Derived from repo
        assert spec.project == "repo"  # Derived from repo
        assert spec.git_commit == "b4d1e66a22c389aae24fe6e4e80db34e1e5c0b11"
        assert spec.git_tag == "v1.0"
        assert spec.files == ["file1.txt", "file2.txt"]
        assert spec.is_pinned() is True


# =============================================================================
# Security Hardening Tests
# =============================================================================

# Import additional functions for hardening tests
from redletters.ingest.fetch import (  # noqa: E402
    UnsupportedURLError,
    is_path_safe,
    is_tar_member_symlink,
    is_zip_member_symlink,
    parse_github_repo_url,
)
from redletters.ingest.morphgnt_parser import (  # noqa: E402
    MorphGNTToken,
    parse_file_with_delimiter,
)


class TestParseFileAPIContract:
    """Lock the parse_file() return type contract to prevent future breakage."""

    def test_parse_file_returns_list_by_default(self):
        """parse_file() must return list[MorphGNTToken], not a tuple."""
        sample_path = Path(__file__).parent / "fixtures" / "morphgnt_sample.tsv"
        if not sample_path.exists():
            pytest.skip("Sample file not found")

        result = parse_file(sample_path)

        # CRITICAL: default must be list, not tuple
        assert isinstance(result, list), (
            f"parse_file() must return list by default, got {type(result)}"
        )
        assert len(result) > 0, "Should have parsed tokens"
        assert isinstance(result[0], MorphGNTToken), (
            f"Elements must be MorphGNTToken, got {type(result[0])}"
        )

    def test_parse_file_with_delimiter_returns_tuple(self):
        """parse_file(return_delimiter=True) must return (list, str) tuple."""
        sample_path = Path(__file__).parent / "fixtures" / "morphgnt_sample.tsv"
        if not sample_path.exists():
            pytest.skip("Sample file not found")

        result = parse_file(sample_path, return_delimiter=True)

        assert isinstance(result, tuple), (
            f"return_delimiter=True must return tuple, got {type(result)}"
        )
        tokens, delimiter = result
        assert isinstance(tokens, list)
        assert isinstance(delimiter, str)
        assert delimiter in ("TAB", "SPACE")

    def test_parse_file_with_delimiter_wrapper(self):
        """parse_file_with_delimiter() wrapper returns correct types."""
        sample_path = Path(__file__).parent / "fixtures" / "morphgnt_sample.tsv"
        if not sample_path.exists():
            pytest.skip("Sample file not found")

        tokens, delimiter = parse_file_with_delimiter(sample_path)

        assert isinstance(tokens, list)
        assert isinstance(delimiter, str)
        assert len(tokens) > 0


class TestGitHubURLParsing:
    """Test GitHub URL parsing including SSH format detection."""

    def test_https_url_basic(self):
        """Should parse basic HTTPS URL."""
        result = parse_github_repo_url("https://github.com/owner/repo")
        assert result == ("owner", "repo")

    def test_https_url_trailing_slash(self):
        """Should handle trailing slash."""
        result = parse_github_repo_url("https://github.com/owner/repo/")
        assert result == ("owner", "repo")

    def test_https_url_with_git_extension(self):
        """Should handle .git extension."""
        result = parse_github_repo_url("https://github.com/owner/repo.git")
        assert result == ("owner", "repo")

    def test_http_url(self):
        """Should handle HTTP (will use HTTPS for raw URLs)."""
        result = parse_github_repo_url("http://github.com/owner/repo")
        assert result == ("owner", "repo")

    def test_ssh_url_raises_unsupported_error(self):
        """Should raise UnsupportedURLError for SSH format with helpful message."""
        with pytest.raises(UnsupportedURLError) as exc_info:
            parse_github_repo_url("git@github.com:owner/repo.git")

        error_msg = str(exc_info.value)
        assert "SSH URL format not supported" in error_msg
        assert "https://github.com/owner/repo" in error_msg

    def test_ssh_protocol_url_raises_unsupported_error(self):
        """Should raise UnsupportedURLError for ssh:// protocol."""
        with pytest.raises(UnsupportedURLError) as exc_info:
            parse_github_repo_url("ssh://git@github.com/owner/repo.git")

        error_msg = str(exc_info.value)
        assert "SSH URL format not supported" in error_msg

    def test_invalid_url_returns_none(self):
        """Should return None for non-GitHub URLs."""
        assert parse_github_repo_url("https://gitlab.com/owner/repo") is None
        assert parse_github_repo_url("") is None
        assert parse_github_repo_url(None) is None


class TestPathSafety:
    """Test is_path_safe() for zip-slip and traversal attacks."""

    def test_safe_simple_path(self, tmp_path):
        """Normal paths should be safe."""
        assert is_path_safe("file.txt", tmp_path) is True
        assert is_path_safe("dir/file.txt", tmp_path) is True
        assert is_path_safe("dir/subdir/file.txt", tmp_path) is True

    def test_unsafe_traversal_dotdot(self, tmp_path):
        """Paths with .. should be rejected."""
        assert is_path_safe("../file.txt", tmp_path) is False
        assert is_path_safe("dir/../../../file.txt", tmp_path) is False
        assert is_path_safe("dir/subdir/../../file.txt", tmp_path) is False

    def test_unsafe_absolute_unix(self, tmp_path):
        """Absolute Unix paths should be rejected."""
        assert is_path_safe("/etc/passwd", tmp_path) is False
        assert is_path_safe("/tmp/file.txt", tmp_path) is False

    def test_unsafe_absolute_windows(self, tmp_path):
        """Absolute Windows paths should be rejected."""
        assert is_path_safe("C:\\Windows\\System32", tmp_path) is False
        assert is_path_safe("D:\\file.txt", tmp_path) is False

    def test_unsafe_backslash_traversal(self, tmp_path):
        """Backslash traversal should be rejected."""
        assert is_path_safe("..\\file.txt", tmp_path) is False
        assert is_path_safe("dir\\..\\..\\file.txt", tmp_path) is False


class TestSymlinkDetection:
    """Test symlink detection in archives."""

    def test_zip_symlink_detection(self):
        """Should detect symlinks in zip external attributes."""
        import zipfile

        # Create a mock ZipInfo with symlink attributes
        info = zipfile.ZipInfo("link.txt")
        # Unix mode 0o120777 (symlink with rwxrwxrwx)
        info.external_attr = 0o120777 << 16
        assert is_zip_member_symlink(info) is True

        # Regular file (0o100644)
        info_regular = zipfile.ZipInfo("file.txt")
        info_regular.external_attr = 0o100644 << 16
        assert is_zip_member_symlink(info_regular) is False

        # Directory (0o040755)
        info_dir = zipfile.ZipInfo("dir/")
        info_dir.external_attr = 0o040755 << 16
        assert is_zip_member_symlink(info_dir) is False

    def test_tar_symlink_detection(self):
        """Should detect symlinks in tar members."""
        import io
        import tarfile

        # Create a tar archive in memory with a symlink
        buffer = io.BytesIO()
        with tarfile.open(mode="w", fileobj=buffer) as tf:
            # Add a regular file
            info = tarfile.TarInfo(name="file.txt")
            info.size = 4
            tf.addfile(info, io.BytesIO(b"test"))

            # Add a symlink
            link_info = tarfile.TarInfo(name="link.txt")
            link_info.type = tarfile.SYMTYPE
            link_info.linkname = "file.txt"
            tf.addfile(link_info)

        # Read back and test
        buffer.seek(0)
        with tarfile.open(mode="r", fileobj=buffer) as tf:
            members = tf.getmembers()
            file_member = [m for m in members if m.name == "file.txt"][0]
            link_member = [m for m in members if m.name == "link.txt"][0]

            assert is_tar_member_symlink(file_member) is False
            assert is_tar_member_symlink(link_member) is True
