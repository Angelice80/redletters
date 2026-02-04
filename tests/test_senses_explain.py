"""Tests for sense resolution explainer (v0.7.0).

Verifies:
- explain output includes pack order
- explain output includes chosen entry
- explain is deterministic
- provenance fields are included
"""

from __future__ import annotations

import sqlite3

import pytest

from redletters.senses.explain import SenseExplainer
from redletters.sources.sense_db import init_sense_pack_schema


@pytest.fixture
def test_db():
    """Create in-memory test database with sense pack schema."""
    conn = sqlite3.connect(":memory:")
    init_sense_pack_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def explainer(test_db):
    """Create SenseExplainer with test database."""
    return SenseExplainer(test_db)


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
    # Insert pack metadata
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

    # Insert senses
    for lemma, sense_id, gloss, weight in senses:
        conn.execute(
            """
            INSERT INTO pack_senses (pack_id, lemma, sense_id, gloss, definition, domain, weight)
            VALUES (?, ?, ?, ?, '', '', ?)
            """,
            (pack_id, lemma, sense_id, gloss, weight),
        )

    conn.commit()


class TestExplainBasic:
    """Basic functionality tests."""

    def test_explain_no_packs(self, explainer):
        """Explain with no packs installed returns empty result."""
        result = explainer.explain("λόγος")

        assert result.lemma_input == "λόγος"
        assert result.lemma_normalized == "λογος"
        assert result.packs_consulted == []
        assert result.matches == []
        assert result.chosen is None
        assert "No matches" in result.reason

    def test_explain_single_pack_single_match(self, test_db, explainer):
        """Explain with single pack and single match."""
        install_test_pack(
            test_db,
            pack_id="test-pack",
            source_id="TestLex",
            source_title="Test Lexicon",
            senses=[("λογος", "logos.1", "word", 0.9)],
        )

        result = explainer.explain("λόγος")

        assert result.has_matches
        assert len(result.matches) == 1
        assert result.chosen is not None
        assert result.chosen.gloss == "word"
        assert result.chosen.source_id == "TestLex"

    def test_explain_normalizes_input(self, test_db, explainer):
        """Explain normalizes input lemma for lookup."""
        install_test_pack(
            test_db,
            pack_id="test-pack",
            source_id="TestLex",
            source_title="Test Lexicon",
            senses=[("λογος", "logos.1", "word", 0.9)],
        )

        # Query with accents - should find the entry stored without accents
        result = explainer.explain("λόγος")

        assert result.lemma_normalized == "λογος"
        assert result.has_matches


class TestExplainPrecedence:
    """Tests for pack precedence order."""

    def test_explain_shows_packs_in_order(self, test_db, explainer):
        """Packs are listed in priority order."""
        install_test_pack(
            test_db,
            pack_id="pack-a",
            source_id="A",
            source_title="Pack A",
            senses=[],
            priority=2,
        )
        install_test_pack(
            test_db,
            pack_id="pack-b",
            source_id="B",
            source_title="Pack B",
            senses=[],
            priority=1,
        )

        result = explainer.explain("λόγος")

        # Lower priority number = higher precedence (consulted first)
        assert result.packs_consulted == ["pack-b", "pack-a"]

    def test_explain_chooses_first_by_precedence(self, test_db, explainer):
        """When multiple packs have the lemma, first by precedence is chosen."""
        install_test_pack(
            test_db,
            pack_id="pack-secondary",
            source_id="Secondary",
            source_title="Secondary Lexicon",
            senses=[("λογος", "logos.1", "speech", 0.95)],
            priority=2,
        )
        install_test_pack(
            test_db,
            pack_id="pack-primary",
            source_id="Primary",
            source_title="Primary Lexicon",
            senses=[("λογος", "logos.1", "word", 0.8)],
            priority=1,
        )

        result = explainer.explain("λόγος")

        # pack-primary has priority=1 (higher precedence than priority=2)
        assert result.chosen.pack_id == "pack-primary"
        assert result.chosen.gloss == "word"
        assert "precedence" in result.reason.lower()


class TestExplainProvenance:
    """Tests for citation/provenance fields."""

    def test_explain_includes_citation_fields(self, test_db):
        """Explain result includes full citation fields."""
        # Insert pack with citation metadata
        test_db.execute(
            """
            INSERT INTO installed_sense_packs
            (pack_id, name, version, license, source_id, source_title,
             edition, publisher, year, license_url, source_url, notes,
             installed_at, install_path, sense_count, pack_hash, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', datetime('now'), '', 1, '', 0)
            """,
            (
                "scholarly-pack",
                "Scholarly Pack",
                "2.0.0",
                "CC BY-SA",
                "BDAG",
                "A Greek-English Lexicon of the NT",
                "3rd",
                "University of Chicago Press",
                2000,
                "https://example.com/license",
            ),
        )
        test_db.execute(
            """
            INSERT INTO pack_senses (pack_id, lemma, sense_id, gloss, definition, domain, weight)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "scholarly-pack",
                "λογος",
                "logos.1",
                "word",
                "spoken or written word",
                "communication",
                0.9,
            ),
        )
        test_db.commit()

        explainer = SenseExplainer(test_db)
        result = explainer.explain("λόγος")

        assert result.chosen is not None
        assert result.chosen.source_id == "BDAG"
        assert result.chosen.source_title == "A Greek-English Lexicon of the NT"
        assert result.chosen.edition == "3rd"
        assert result.chosen.publisher == "University of Chicago Press"
        assert result.chosen.year == 2000
        assert result.chosen.license == "CC BY-SA"


class TestExplainDeterminism:
    """Tests for deterministic behavior."""

    def test_explain_is_deterministic(self, test_db, explainer):
        """Multiple calls return identical results."""
        install_test_pack(
            test_db,
            pack_id="test-pack",
            source_id="TestLex",
            source_title="Test Lexicon",
            senses=[
                ("λογος", "logos.1", "word", 0.9),
                ("λογος", "logos.2", "reason", 0.7),
            ],
        )

        result1 = explainer.explain("λόγος")
        result2 = explainer.explain("λόγος")

        assert result1.to_dict() == result2.to_dict()


class TestExplainSerialization:
    """Tests for JSON serialization."""

    def test_to_dict_includes_all_fields(self, test_db, explainer):
        """to_dict() includes all required fields."""
        install_test_pack(
            test_db,
            pack_id="test-pack",
            source_id="TestLex",
            source_title="Test Lexicon",
            senses=[("λογος", "logos.1", "word", 0.9)],
        )

        result = explainer.explain("λόγος")
        data = result.to_dict()

        assert "lemma_input" in data
        assert "lemma_normalized" in data
        assert "packs_consulted" in data
        assert "matches" in data
        assert "chosen" in data
        assert "reason" in data
        assert "schema_version" in data

    def test_match_to_dict_includes_citation(self, test_db, explainer):
        """Match.to_dict() includes citation fields."""
        install_test_pack(
            test_db,
            pack_id="test-pack",
            source_id="TestLex",
            source_title="Test Lexicon",
            senses=[("λογος", "logos.1", "word", 0.9)],
        )

        result = explainer.explain("λόγος")
        match_dict = result.matches[0].to_dict()

        assert "pack_id" in match_dict
        assert "source_id" in match_dict
        assert "source_title" in match_dict
        assert "gloss" in match_dict
        assert "weight" in match_dict
