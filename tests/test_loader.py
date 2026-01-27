"""Tests for provenance-gate loader.

These tests verify that the loader enforces epistemic boundaries:
1. Required fields must be present
2. Source provenance is recorded
3. SHA mismatch causes failure
4. End-to-end queries work on loaded data
"""

import sqlite3
import unicodedata
from pathlib import Path

import pytest

from redletters.db.schema_v2 import init_schema_v2, list_sources
from redletters.ingest.loader import (
    SHAMismatchError,
    compute_sha256,
    load_source,
)
from redletters.ingest.morphgnt_parser import parse_file
from redletters.ingest.strongs_parser import parse_strongs_xml


# Path to fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"
MORPHGNT_SAMPLE = FIXTURES_DIR / "morphgnt_sample.tsv"
STRONGS_SAMPLE = FIXTURES_DIR / "strongs_sample.xml"


class TestMorphGNTParserEmitsRequiredFields:
    """Every token must have: ref, pos, parse_code, surface_text, word, normalized, lemma."""

    def test_all_tokens_have_required_fields(self):
        """Parse sample file and verify all required fields are present."""
        tokens = parse_file(MORPHGNT_SAMPLE)

        assert len(tokens) > 0, "Should parse at least one token"

        required_fields = [
            "ref",
            "pos",
            "parse_code",
            "surface_text",
            "word",
            "normalized",
            "lemma",
        ]

        for token in tokens:
            for field in required_fields:
                value = getattr(token, field)
                assert value is not None, f"Token {token.ref} missing {field}"
                assert isinstance(value, str), (
                    f"Token {token.ref}.{field} should be string"
                )
                assert value.strip(), f"Token {token.ref}.{field} should not be empty"

    def test_nfc_normalization_verified(self):
        """Greek text should be NFC normalized."""
        tokens = parse_file(MORPHGNT_SAMPLE)

        for token in tokens:
            # Verify Greek fields are NFC normalized
            for field in ["surface_text", "word", "normalized", "lemma"]:
                value = getattr(token, field)
                nfc_value = unicodedata.normalize("NFC", value)
                assert value == nfc_value, (
                    f"Token {token.ref}.{field} not NFC normalized: "
                    f"{repr(value)} vs {repr(nfc_value)}"
                )

    def test_ref_format_is_canonical(self):
        """References should be in Book.Chapter.Verse.Position format."""
        tokens = parse_file(MORPHGNT_SAMPLE)

        for token in tokens:
            parts = token.ref.split(".")
            assert len(parts) == 4, f"Ref should have 4 parts: {token.ref}"
            # Book is a string
            assert parts[0], "Book should not be empty"
            # Chapter, verse, position are integers
            assert parts[1].isdigit(), f"Chapter should be numeric: {token.ref}"
            assert parts[2].isdigit(), f"Verse should be numeric: {token.ref}"
            assert parts[3].isdigit(), f"Position should be numeric: {token.ref}"

    def test_parse_code_is_8_characters(self):
        """Parse codes should be exactly 8 characters."""
        tokens = parse_file(MORPHGNT_SAMPLE)

        for token in tokens:
            assert len(token.parse_code) == 8, (
                f"Token {token.ref} parse_code should be 8 chars: {token.parse_code}"
            )


class TestLoaderRecordsSourceProvenance:
    """After load, sources row exists with name/version/license/sha256/retrieved_at."""

    @pytest.fixture
    def db_conn(self):
        """Create an in-memory database with schema v2."""
        conn = sqlite3.connect(":memory:")
        init_schema_v2(conn)
        yield conn
        conn.close()

    @pytest.fixture
    def mock_source_dir(self, tmp_path):
        """Create a mock source directory with sample data and marker file."""
        source_dir = tmp_path / "morphgnt-sblgnt"
        source_dir.mkdir()

        # Copy sample file
        sample_content = MORPHGNT_SAMPLE.read_bytes()
        sample_file = source_dir / "sample-morphgnt.txt"
        sample_file.write_bytes(sample_content)

        # Compute SHA256 of the directory
        sha256 = compute_sha256(source_dir)

        # Create marker file with metadata
        marker = source_dir / ".fetched"
        marker.write_text(
            f"name=MorphGNT-SBLGNT\n"
            f"version=6.12\n"
            f"license=CC-BY-SA-3.0\n"
            f"url=https://github.com/morphgnt/sblgnt\n"
            f"retrieved_at=2026-01-27T00:00:00+00:00\n"
            f"sha256={sha256}\n"
            f"notes=Test fixture\n"
        )

        return source_dir

    def test_source_row_created_with_full_metadata(
        self, db_conn, mock_source_dir, tmp_path, monkeypatch
    ):
        """After load, sources table should have complete provenance record."""

        # Patch get_source_path to return our mock directory
        def mock_get_source_path(source_key, data_dir=None):
            if source_key == "morphgnt-sblgnt":
                return mock_source_dir
            return None

        monkeypatch.setattr(
            "redletters.ingest.loader.get_source_path",
            mock_get_source_path,
        )

        # Load the source
        report = load_source(db_conn, "morphgnt-sblgnt", tmp_path)

        # Verify report
        assert report.success, f"Load should succeed: {report.error}"
        assert report.source_id > 0, "Should have valid source_id"

        # Verify sources table
        sources = list_sources(db_conn)
        assert len(sources) == 1, "Should have one source"

        source = sources[0]
        assert source["name"] == "MorphGNT-SBLGNT"
        assert source["version"] == "6.12"
        assert source["license"] == "CC-BY-SA-3.0"
        assert source["url"], "URL should be non-empty"
        assert source["retrieved_at"], "retrieved_at should be non-empty"
        assert source["sha256"], "sha256 should be non-empty"

    def test_sha256_matches_computed(
        self, db_conn, mock_source_dir, tmp_path, monkeypatch
    ):
        """Recorded SHA256 should match what we compute."""

        def mock_get_source_path(source_key, data_dir=None):
            if source_key == "morphgnt-sblgnt":
                return mock_source_dir
            return None

        monkeypatch.setattr(
            "redletters.ingest.loader.get_source_path",
            mock_get_source_path,
        )

        report = load_source(db_conn, "morphgnt-sblgnt", tmp_path)

        # Verify SHA256 in report matches computed
        expected_sha = compute_sha256(mock_source_dir)
        assert report.sha256_actual == expected_sha


class TestLoaderEnforcesSHAMismatch:
    """Load once -> ok. Mutate fixture -> expect loader to raise/exit non-zero."""

    @pytest.fixture
    def db_conn(self):
        """Create an in-memory database with schema v2."""
        conn = sqlite3.connect(":memory:")
        init_schema_v2(conn)
        yield conn
        conn.close()

    def test_sha_mismatch_raises_error(self, db_conn, tmp_path, monkeypatch):
        """If file content changes but SHA in marker doesn't, raise SHAMismatchError."""
        source_dir = tmp_path / "morphgnt-sblgnt"
        source_dir.mkdir()

        # Copy sample file
        sample_content = MORPHGNT_SAMPLE.read_bytes()
        sample_file = source_dir / "sample-morphgnt.txt"
        sample_file.write_bytes(sample_content)

        # Create marker with WRONG SHA256 (simulating file mutation)
        marker = source_dir / ".fetched"
        wrong_sha = "0" * 64  # Wrong hash
        marker.write_text(
            f"name=MorphGNT-SBLGNT\n"
            f"version=6.12\n"
            f"license=CC-BY-SA-3.0\n"
            f"url=https://github.com/morphgnt/sblgnt\n"
            f"retrieved_at=2026-01-27T00:00:00+00:00\n"
            f"sha256={wrong_sha}\n"
        )

        def mock_get_source_path(source_key, data_dir=None):
            if source_key == "morphgnt-sblgnt":
                return source_dir
            return None

        monkeypatch.setattr(
            "redletters.ingest.loader.get_source_path",
            mock_get_source_path,
        )

        # Should raise SHAMismatchError
        with pytest.raises(SHAMismatchError) as exc_info:
            load_source(db_conn, "morphgnt-sblgnt", tmp_path)

        assert exc_info.value.expected == wrong_sha
        assert exc_info.value.actual != wrong_sha

    def test_first_load_ok_then_mutate_fails(self, db_conn, tmp_path, monkeypatch):
        """First load succeeds, then mutating file causes failure."""
        source_dir = tmp_path / "morphgnt-sblgnt"
        source_dir.mkdir()

        # Copy sample file
        sample_content = MORPHGNT_SAMPLE.read_bytes()
        sample_file = source_dir / "sample-morphgnt.txt"
        sample_file.write_bytes(sample_content)

        # Compute correct SHA256
        correct_sha = compute_sha256(source_dir)

        # Create marker with correct SHA
        marker = source_dir / ".fetched"
        marker.write_text(
            f"name=MorphGNT-SBLGNT\n"
            f"version=6.12\n"
            f"license=CC-BY-SA-3.0\n"
            f"url=https://github.com/morphgnt/sblgnt\n"
            f"retrieved_at=2026-01-27T00:00:00+00:00\n"
            f"sha256={correct_sha}\n"
        )

        def mock_get_source_path(source_key, data_dir=None):
            if source_key == "morphgnt-sblgnt":
                return source_dir
            return None

        monkeypatch.setattr(
            "redletters.ingest.loader.get_source_path",
            mock_get_source_path,
        )

        # First load should succeed
        report = load_source(db_conn, "morphgnt-sblgnt", tmp_path)
        assert report.success, "First load should succeed"

        # Now MUTATE the file
        sample_file.write_text("TAMPERED DATA\n")

        # Second load should fail with SHA mismatch
        with pytest.raises(SHAMismatchError):
            load_source(db_conn, "morphgnt-sblgnt", tmp_path)


class TestE2EQueryReturnsRealTokens:
    """Load sample MorphGNT, query DB for specific ref, assert token order and fields."""

    @pytest.fixture
    def loaded_db(self, tmp_path, monkeypatch):
        """Create database and load sample MorphGNT data."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        init_schema_v2(conn)

        # Create mock source directory
        source_dir = tmp_path / "morphgnt-sblgnt"
        source_dir.mkdir()

        # Copy sample file
        sample_content = MORPHGNT_SAMPLE.read_bytes()
        sample_file = source_dir / "sample-morphgnt.txt"
        sample_file.write_bytes(sample_content)

        # Compute SHA256
        sha256 = compute_sha256(source_dir)

        # Create marker
        marker = source_dir / ".fetched"
        marker.write_text(
            f"name=MorphGNT-SBLGNT\n"
            f"version=6.12\n"
            f"license=CC-BY-SA-3.0\n"
            f"url=https://github.com/morphgnt/sblgnt\n"
            f"retrieved_at=2026-01-27T00:00:00+00:00\n"
            f"sha256={sha256}\n"
        )

        def mock_get_source_path(source_key, data_dir=None):
            if source_key == "morphgnt-sblgnt":
                return source_dir
            return None

        monkeypatch.setattr(
            "redletters.ingest.loader.get_source_path",
            mock_get_source_path,
        )

        # Load source
        load_source(conn, "morphgnt-sblgnt", tmp_path)

        yield conn
        conn.close()

    def test_query_returns_tokens_for_verse(self, loaded_db):
        """Query for Matthew 5:3 should return tokens in correct order."""
        cursor = loaded_db.execute(
            """
            SELECT ref, surface_text, lemma, pos, parse_code
            FROM tokens
            WHERE ref LIKE 'Matthew.5.3.%'
            """
        )
        tokens = cursor.fetchall()

        # Our sample has Matthew 5:3 (Beatitude)
        assert len(tokens) > 0, "Should find tokens for Matthew 5:3"

        # Sort by position (integer) since SQL ORDER BY does lexicographic sorting
        tokens_sorted = sorted(tokens, key=lambda t: int(t[0].split(".")[-1]))

        # Verify positions are sequential
        positions = [int(t[0].split(".")[-1]) for t in tokens_sorted]
        assert positions == list(range(1, len(positions) + 1)), (
            f"Tokens should have sequential positions: {positions}"
        )

        # First token should be "Μακάριοι" (Blessed)
        first_token = tokens_sorted[0]
        assert "μακάριος" in first_token[2].lower(), (
            f"First lemma should be makarios: {first_token}"
        )

    def test_token_has_all_required_fields(self, loaded_db):
        """Every token in DB should have all required fields populated."""
        cursor = loaded_db.execute(
            """
            SELECT ref, surface_text, word, normalized, lemma, pos, parse_code
            FROM tokens
            """
        )
        tokens = cursor.fetchall()

        for token in tokens:
            ref, surface_text, word, normalized, lemma, pos, parse_code = token
            assert ref, "ref should not be empty"
            assert surface_text, "surface_text should not be empty"
            assert word, "word should not be empty"
            assert normalized, "normalized should not be empty"
            assert lemma, "lemma should not be empty"
            assert pos, "pos should not be empty"
            assert parse_code, "parse_code should not be empty"
            assert len(parse_code) == 8, f"parse_code should be 8 chars: {parse_code}"

    def test_lemma_is_nfc_normalized(self, loaded_db):
        """Lemmas in DB should be NFC normalized."""
        cursor = loaded_db.execute("SELECT lemma FROM tokens")
        lemmas = [row[0] for row in cursor.fetchall()]

        for lemma in lemmas:
            nfc = unicodedata.normalize("NFC", lemma)
            assert lemma == nfc, f"Lemma not NFC: {repr(lemma)} vs {repr(nfc)}"

    def test_source_id_links_to_sources_table(self, loaded_db):
        """Every token should have a valid source_id."""
        cursor = loaded_db.execute(
            """
            SELECT t.ref, t.source_id, s.name
            FROM tokens t
            JOIN sources s ON t.source_id = s.id
            LIMIT 5
            """
        )
        rows = cursor.fetchall()

        assert len(rows) > 0, "Should have tokens with source links"
        for ref, source_id, source_name in rows:
            assert source_id > 0, f"Token {ref} should have valid source_id"
            assert source_name == "MorphGNT-SBLGNT", (
                f"Source should be MorphGNT: {source_name}"
            )


class TestStrongsParser:
    """Test Strong's XML parsing with fixtures."""

    def test_parse_strongs_sample(self):
        """Parse sample Strong's XML and verify entries."""
        entries = parse_strongs_xml(STRONGS_SAMPLE)

        assert len(entries) == 10, f"Should parse 10 entries: {len(entries)}"

        # Find specific entry
        basileia = next((e for e in entries if e.strongs_id == "G0932"), None)
        assert basileia is not None, "Should find G0932 (basileia)"
        assert basileia.lemma == "βασιλεία"
        assert (
            "kingdom" in basileia.gloss.lower() or "royalty" in basileia.gloss.lower()
        )

    def test_all_entries_have_required_fields(self):
        """Every entry should have strongs_id, lemma, and gloss."""
        entries = parse_strongs_xml(STRONGS_SAMPLE)

        for entry in entries:
            assert entry.strongs_id, "Entry missing strongs_id"
            assert entry.lemma, f"Entry {entry.strongs_id} missing lemma"
            assert entry.gloss, f"Entry {entry.strongs_id} missing gloss"

    def test_lemmas_are_nfc_normalized(self):
        """Greek lemmas should be NFC normalized."""
        entries = parse_strongs_xml(STRONGS_SAMPLE)

        for entry in entries:
            nfc = unicodedata.normalize("NFC", entry.lemma)
            assert entry.lemma == nfc, (
                f"Entry {entry.strongs_id} lemma not NFC: "
                f"{repr(entry.lemma)} vs {repr(nfc)}"
            )
