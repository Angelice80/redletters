"""Tests for sense conflict detection (v0.7.0).

Verifies:
- conflicts output includes all matches across packs
- conflicts shows pack provenance
- conflicts detects disagreements
- conflicts is deterministic
"""

from __future__ import annotations

import sqlite3

import pytest

from redletters.senses.conflicts import SenseConflictDetector
from redletters.sources.sense_db import init_sense_pack_schema


@pytest.fixture
def test_db():
    """Create in-memory test database with sense pack schema."""
    conn = sqlite3.connect(":memory:")
    init_sense_pack_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def detector(test_db):
    """Create SenseConflictDetector with test database."""
    return SenseConflictDetector(test_db)


def install_test_pack(
    conn: sqlite3.Connection,
    pack_id: str,
    source_id: str,
    source_title: str,
    senses: list[tuple[str, str, str, float]],  # (lemma, sense_id, gloss, weight)
    priority: int = 0,
    version: str = "1.0.0",
    license: str = "CC0",
):
    """Helper to install a test sense pack."""
    conn.execute(
        """
        INSERT INTO installed_sense_packs
        (pack_id, name, version, license, source_id, source_title,
         edition, publisher, year, license_url, source_url, notes,
         installed_at, install_path, sense_count, pack_hash, priority)
        VALUES (?, ?, ?, ?, ?, ?, '', '', NULL, '', '', '', datetime('now'), '', ?, '', ?)
        """,
        (
            pack_id,
            pack_id,
            version,
            license,
            source_id,
            source_title,
            len(senses),
            priority,
        ),
    )

    for lemma, sense_id, gloss, weight in senses:
        conn.execute(
            """
            INSERT INTO pack_senses (pack_id, lemma, sense_id, gloss, definition, domain, weight)
            VALUES (?, ?, ?, ?, '', '', ?)
            """,
            (pack_id, lemma, sense_id, gloss, weight),
        )

    conn.commit()


class TestConflictsBasic:
    """Basic functionality tests."""

    def test_detect_no_packs(self, detector):
        """Detect with no packs installed returns empty result."""
        result = detector.detect("λόγος")

        assert result.lemma_input == "λόγος"
        assert result.lemma_normalized == "λογος"
        assert result.packs_checked == []
        assert result.entries == []
        assert not result.has_conflict
        assert "No matches" in result.conflict_summary

    def test_detect_single_pack_single_entry(self, test_db, detector):
        """Detect with single pack and single entry."""
        install_test_pack(
            test_db,
            pack_id="test-pack",
            source_id="TestLex",
            source_title="Test Lexicon",
            senses=[("λογος", "logos.1", "word", 0.9)],
        )

        result = detector.detect("λόγος")

        assert len(result.entries) == 1
        assert result.entries[0].gloss == "word"
        assert result.entries[0].pack_id == "test-pack"
        assert not result.has_conflict


class TestConflictsMultiplePacks:
    """Tests for multi-pack conflict detection."""

    def test_detect_agreement_across_packs(self, test_db, detector):
        """Packs agreeing on primary gloss = no conflict."""
        install_test_pack(
            test_db,
            pack_id="pack-a",
            source_id="LexA",
            source_title="Lexicon A",
            senses=[("λογος", "logos.1", "word", 0.9)],
            priority=1,
        )
        install_test_pack(
            test_db,
            pack_id="pack-b",
            source_id="LexB",
            source_title="Lexicon B",
            senses=[("λογος", "logos.1", "word", 0.85)],
            priority=2,
        )

        result = detector.detect("λόγος")

        assert len(result.entries) == 2
        assert len(result.packs_with_matches) == 2
        assert not result.has_conflict
        assert "Agreement" in result.conflict_summary

    def test_detect_conflict_different_primary_glosses(self, test_db, detector):
        """Packs disagreeing on primary gloss = conflict."""
        install_test_pack(
            test_db,
            pack_id="pack-a",
            source_id="LexA",
            source_title="Lexicon A",
            senses=[("λογος", "logos.1", "word", 0.9)],
            priority=1,
        )
        install_test_pack(
            test_db,
            pack_id="pack-b",
            source_id="LexB",
            source_title="Lexicon B",
            senses=[("λογος", "logos.1", "reason", 0.85)],
            priority=2,
        )

        result = detector.detect("λόγος")

        assert result.has_conflict
        assert "CONFLICT" in result.conflict_summary
        assert "word" in result.conflict_summary
        assert "reason" in result.conflict_summary
        assert len(result.unique_glosses) == 2

    def test_detect_shows_all_entries(self, test_db, detector):
        """All entries from all packs are included."""
        install_test_pack(
            test_db,
            pack_id="pack-a",
            source_id="LexA",
            source_title="Lexicon A",
            senses=[
                ("λογος", "logos.1", "word", 0.9),
                ("λογος", "logos.2", "reason", 0.7),
            ],
            priority=1,
        )
        install_test_pack(
            test_db,
            pack_id="pack-b",
            source_id="LexB",
            source_title="Lexicon B",
            senses=[("λογος", "logos.1", "speech", 0.8)],
            priority=2,
        )

        result = detector.detect("λόγος")

        assert len(result.entries) == 3
        glosses = [e.gloss for e in result.entries]
        assert "word" in glosses
        assert "reason" in glosses
        assert "speech" in glosses


class TestConflictsProvenance:
    """Tests for pack provenance in conflict entries."""

    def test_entries_include_pack_ref(self, test_db, detector):
        """Entries include pack_id@version reference."""
        install_test_pack(
            test_db,
            pack_id="scholarly-pack",
            source_id="BDAG",
            source_title="BDAG Lexicon",
            senses=[("λογος", "logos.1", "word", 0.9)],
            version="3.0.0",
        )

        result = detector.detect("λόγος")
        entry_dict = result.entries[0].to_dict()

        assert entry_dict["pack_ref"] == "scholarly-pack@3.0.0"
        assert entry_dict["source_id"] == "BDAG"

    def test_entries_include_citation_fields(self, test_db):
        """Entries include full citation metadata."""
        test_db.execute(
            """
            INSERT INTO installed_sense_packs
            (pack_id, name, version, license, source_id, source_title,
             edition, publisher, year, license_url, source_url, notes,
             installed_at, install_path, sense_count, pack_hash, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', datetime('now'), '', 1, '', 0)
            """,
            (
                "test-pack",
                "Test Pack",
                "2.0.0",
                "CC BY-SA",
                "TestLex",
                "Test Lexicon Full Title",
                "2nd",
                "Test Publisher",
                2020,
                "https://example.com/license",
            ),
        )
        test_db.execute(
            """
            INSERT INTO pack_senses (pack_id, lemma, sense_id, gloss, definition, domain, weight)
            VALUES (?, ?, ?, ?, '', '', ?)
            """,
            ("test-pack", "λογος", "logos.1", "word", 0.9),
        )
        test_db.commit()

        detector = SenseConflictDetector(test_db)
        result = detector.detect("λόγος")

        entry = result.entries[0]
        assert entry.source_id == "TestLex"
        assert entry.source_title == "Test Lexicon Full Title"
        assert entry.edition == "2nd"
        assert entry.publisher == "Test Publisher"
        assert entry.year == 2020
        assert entry.license == "CC BY-SA"


class TestConflictsDeterminism:
    """Tests for deterministic behavior."""

    def test_detect_is_deterministic(self, test_db, detector):
        """Multiple calls return identical results."""
        install_test_pack(
            test_db,
            pack_id="pack-a",
            source_id="LexA",
            source_title="Lexicon A",
            senses=[("λογος", "logos.1", "word", 0.9)],
            priority=1,
        )
        install_test_pack(
            test_db,
            pack_id="pack-b",
            source_id="LexB",
            source_title="Lexicon B",
            senses=[("λογος", "logos.1", "reason", 0.8)],
            priority=2,
        )

        result1 = detector.detect("λόγος")
        result2 = detector.detect("λόγος")

        assert result1.to_dict() == result2.to_dict()


class TestConflictsSerialization:
    """Tests for JSON serialization."""

    def test_to_dict_includes_all_fields(self, test_db, detector):
        """to_dict() includes all required fields."""
        install_test_pack(
            test_db,
            pack_id="test-pack",
            source_id="TestLex",
            source_title="Test Lexicon",
            senses=[("λογος", "logos.1", "word", 0.9)],
        )

        result = detector.detect("λόγος")
        data = result.to_dict()

        assert "lemma_input" in data
        assert "lemma_normalized" in data
        assert "packs_checked" in data
        assert "entries" in data
        assert "unique_glosses" in data
        assert "packs_with_matches" in data
        assert "has_conflict" in data
        assert "conflict_summary" in data
        assert "schema_version" in data


class TestListPacks:
    """Tests for list_packs helper."""

    def test_list_packs_empty(self, detector):
        """list_packs with no packs returns empty list."""
        packs = detector.list_packs()
        assert packs == []

    def test_list_packs_returns_precedence_order(self, test_db, detector):
        """list_packs returns packs in precedence order."""
        install_test_pack(
            test_db,
            pack_id="pack-b",
            source_id="B",
            source_title="Pack B",
            senses=[],
            priority=2,
        )
        install_test_pack(
            test_db,
            pack_id="pack-a",
            source_id="A",
            source_title="Pack A",
            senses=[],
            priority=1,
        )

        packs = detector.list_packs()

        assert len(packs) == 2
        assert packs[0]["pack_id"] == "pack-a"
        assert packs[1]["pack_id"] == "pack-b"
