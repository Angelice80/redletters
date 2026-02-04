"""Tests for citations export (v0.7.0).

Verifies:
- citations export includes all installed packs
- citations export is deterministic
- CSL-JSON format is valid
- content hash enables verification
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from redletters.export.citations import (
    CITATIONS_SCHEMA_VERSION,
    CitationEntry,
    CitationsExporter,
)
from redletters.sources.sense_db import init_sense_pack_schema


@pytest.fixture
def test_db():
    """Create in-memory test database with sense pack schema."""
    conn = sqlite3.connect(":memory:")
    init_sense_pack_schema(conn)
    yield conn
    conn.close()


def install_test_sense_pack(
    conn: sqlite3.Connection,
    pack_id: str,
    source_id: str,
    source_title: str,
    edition: str = "",
    publisher: str = "",
    year: int | None = None,
    license: str = "CC0",
    license_url: str = "",
):
    """Helper to install a test sense pack."""
    conn.execute(
        """
        INSERT INTO installed_sense_packs
        (pack_id, name, version, license, source_id, source_title,
         edition, publisher, year, license_url, source_url, notes,
         installed_at, install_path, sense_count, pack_hash, priority)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', datetime('now'), '', 0, '', 0)
        """,
        (
            pack_id,
            pack_id,
            "1.0.0",
            license,
            source_id,
            source_title,
            edition,
            publisher,
            year,
            license_url,
        ),
    )
    conn.commit()


class TestCitationEntry:
    """Tests for CitationEntry class."""

    def test_to_csl_dict_minimal(self):
        """Minimal citation entry produces valid CSL-JSON."""
        entry = CitationEntry(
            id="test-pack",
            type="dataset",
            title="Test Dataset",
        )
        csl = entry.to_csl_dict()

        assert csl["id"] == "test-pack"
        assert csl["type"] == "dataset"
        assert csl["title"] == "Test Dataset"

    def test_to_csl_dict_full(self):
        """Full citation entry includes all fields."""
        entry = CitationEntry(
            id="lexicon-pack",
            type="book",
            title="A Greek Lexicon",
            edition="3rd",
            publisher="University Press",
            issued={"date-parts": [[2000]]},
            URL="https://example.com",
            license="CC BY-SA",
            license_url="https://creativecommons.org/licenses/by-sa/4.0/",
            version="2.0.0",
            pack_role="sense_pack",
        )
        csl = entry.to_csl_dict()

        assert csl["edition"] == "3rd"
        assert csl["publisher"] == "University Press"
        assert csl["issued"] == {"date-parts": [[2000]]}
        assert csl["URL"] == "https://example.com"
        assert csl["x-license"] == "CC BY-SA"
        assert csl["x-license-url"] == "https://creativecommons.org/licenses/by-sa/4.0/"
        assert csl["version"] == "2.0.0"
        assert csl["x-pack-role"] == "sense_pack"


class TestCitationsExporter:
    """Tests for CitationsExporter."""

    def test_export_schema_version(self, test_db):
        """Export includes schema version."""
        exporter = CitationsExporter(conn=test_db)
        result = exporter.export()

        assert result.schema_version == CITATIONS_SCHEMA_VERSION
        assert result.content_hash  # Hash should always be computed

    def test_export_single_sense_pack(self, test_db):
        """Export includes sense pack with full citation metadata."""
        install_test_sense_pack(
            test_db,
            pack_id="test-lexicon",
            source_id="TestLex",
            source_title="Test Lexicon",
            edition="2nd",
            publisher="Test Publisher",
            year=2020,
            license="CC BY-SA",
        )

        exporter = CitationsExporter(conn=test_db)
        result = exporter.export()

        # Find the test pack in results
        test_entries = [e for e in result.entries if e.id == "test-lexicon"]
        assert len(test_entries) == 1

        entry = test_entries[0]
        assert entry.title == "Test Lexicon"
        assert entry.edition == "2nd"
        assert entry.publisher == "Test Publisher"
        assert entry.issued == {"date-parts": [[2020]]}
        assert entry.license == "CC BY-SA"

    def test_export_multiple_sense_packs_sorted(self, test_db):
        """Sense packs are sorted deterministically by pack_id."""
        # Install in non-sorted order
        install_test_sense_pack(
            test_db,
            pack_id="zzz-pack",
            source_id="ZZZ",
            source_title="ZZZ Pack",
        )
        install_test_sense_pack(
            test_db,
            pack_id="aaa-pack",
            source_id="AAA",
            source_title="AAA Pack",
        )

        exporter = CitationsExporter(conn=test_db)
        result = exporter.export()

        # Find our test packs
        sense_packs = [e for e in result.entries if e.pack_role == "sense_pack"]
        assert len(sense_packs) >= 2

        # Check that aaa-pack comes before zzz-pack
        aaa_idx = next(i for i, e in enumerate(sense_packs) if e.id == "aaa-pack")
        zzz_idx = next(i for i, e in enumerate(sense_packs) if e.id == "zzz-pack")
        assert aaa_idx < zzz_idx


class TestCitationsExportDeterminism:
    """Tests for deterministic export."""

    def test_export_is_deterministic(self, test_db):
        """Multiple exports produce identical results."""
        install_test_sense_pack(
            test_db,
            pack_id="test-pack",
            source_id="TestLex",
            source_title="Test Lexicon",
            year=2020,
        )

        exporter = CitationsExporter(conn=test_db)
        result1 = exporter.export()
        result2 = exporter.export()

        # Content hash should be identical
        assert result1.content_hash == result2.content_hash

        # CSL-JSON output should be identical
        csl1 = result1.to_csl_json()
        csl2 = result2.to_csl_json()
        assert csl1 == csl2

    def test_export_hash_changes_with_content(self, test_db):
        """Content hash changes when packs change."""
        install_test_sense_pack(
            test_db,
            pack_id="pack-a",
            source_id="A",
            source_title="Pack A",
        )

        exporter = CitationsExporter(conn=test_db)
        result1 = exporter.export()
        hash1 = result1.content_hash

        # Add another pack
        install_test_sense_pack(
            test_db,
            pack_id="pack-b",
            source_id="B",
            source_title="Pack B",
        )

        result2 = exporter.export()
        hash2 = result2.content_hash

        assert hash1 != hash2


class TestCitationsExportToFile:
    """Tests for file export."""

    def test_export_to_file_csljson(self, test_db):
        """Export to CSL-JSON file."""
        install_test_sense_pack(
            test_db,
            pack_id="test-pack",
            source_id="TestLex",
            source_title="Test Lexicon",
        )

        exporter = CitationsExporter(conn=test_db)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "citations.json"
            result = exporter.export_to_file(output_path, format="csljson")

            assert result["entries_count"] >= 1
            assert result["format"] == "csljson"

            # Verify file contents
            data = json.loads(output_path.read_text())
            assert isinstance(data, list)
            # Find our test pack in the exported data
            test_entries = [e for e in data if e["id"] == "test-pack"]
            assert len(test_entries) == 1
            assert test_entries[0]["title"] == "Test Lexicon"

    def test_export_to_file_full(self, test_db):
        """Export to full format with metadata."""
        install_test_sense_pack(
            test_db,
            pack_id="test-pack",
            source_id="TestLex",
            source_title="Test Lexicon",
        )

        exporter = CitationsExporter(conn=test_db)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "citations_full.json"
            exporter.export_to_file(output_path, format="full")

            # Verify file contents
            data = json.loads(output_path.read_text())
            assert "schema_version" in data
            assert "entries" in data
            assert "content_hash" in data

    def test_export_twice_produces_identical_files(self, test_db):
        """Two exports produce byte-identical files."""
        install_test_sense_pack(
            test_db,
            pack_id="test-pack",
            source_id="TestLex",
            source_title="Test Lexicon",
            year=2020,
        )

        exporter = CitationsExporter(conn=test_db)

        with tempfile.TemporaryDirectory() as tmpdir:
            path1 = Path(tmpdir) / "citations1.json"
            path2 = Path(tmpdir) / "citations2.json"

            exporter.export_to_file(path1, format="csljson")
            exporter.export_to_file(path2, format="csljson")

            content1 = path1.read_text()
            content2 = path2.read_text()

            assert content1 == content2


class TestCSLJSONFormat:
    """Tests for CSL-JSON format compliance."""

    def test_csl_json_has_required_fields(self, test_db):
        """CSL-JSON entries have required fields."""
        install_test_sense_pack(
            test_db,
            pack_id="test-pack",
            source_id="TestLex",
            source_title="Test Lexicon",
        )

        exporter = CitationsExporter(conn=test_db)
        result = exporter.export()
        csl = result.to_csl_json()

        # CSL-JSON requires id, type, and at least one of: title, container-title
        entry = csl[0]
        assert "id" in entry
        assert "type" in entry
        assert "title" in entry

    def test_csl_json_types_are_valid(self, test_db):
        """CSL types used are standard CSL types."""
        install_test_sense_pack(
            test_db,
            pack_id="test-pack",
            source_id="TestLex",
            source_title="Test Lexicon",
        )

        exporter = CitationsExporter(conn=test_db)
        result = exporter.export()

        valid_types = {
            "article",
            "book",
            "chapter",
            "dataset",
            "document",
            "software",
            "webpage",
        }

        for entry in result.entries:
            assert entry.type in valid_types, f"Invalid CSL type: {entry.type}"
