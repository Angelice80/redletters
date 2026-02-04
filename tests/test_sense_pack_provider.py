"""Tests for sense pack provider (v0.6.0).

Covers:
- SensePackProvider with citation-grade provenance
- ChainedSenseProvider with fallback
- Deterministic results
"""

import json
import sqlite3

import pytest

from redletters.lexicon.sense_pack_provider import (
    CitationGlossResult,
    SensePackProvider,
    ChainedSenseProvider,
    get_sense_provider,
)
from redletters.sources.sense_db import SensePackDB, init_sense_pack_schema
from redletters.sources.sense_pack import SensePackLoader


@pytest.fixture
def db_conn():
    """Create in-memory database connection."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_sense_pack_schema(conn)
    return conn


@pytest.fixture
def sample_pack(tmp_path):
    """Create a sample sense pack."""
    pack_dir = tmp_path / "test-senses"
    pack_dir.mkdir()
    (pack_dir / "manifest.json").write_text(
        json.dumps(
            {
                "pack_id": "test-senses",
                "name": "Test Sense Pack",
                "version": "1.0.0",
                "role": "sense_pack",
                "license": "CC0",
                "source_id": "TEST",
                "source_title": "Test Greek Dictionary",
                "edition": "1st",
                "publisher": "Test Publisher",
                "year": 2026,
            }
        )
    )
    (pack_dir / "senses.tsv").write_text(
        "lemma\tsense_id\tgloss\tdefinition\tdomain\tweight\n"
        "λόγος\tlogos.1\tword\tspoken word\tspeech\t0.9\n"
        "λόγος\tlogos.2\treason\tlogical principle\tcognition\t0.6\n"
        "θεός\ttheos.1\tGod\tthe divine being\treligion\t0.95\n"
    )
    return pack_dir


@pytest.fixture
def db_with_pack(db_conn, sample_pack):
    """Database with sample pack installed."""
    db = SensePackDB(db_conn)
    loader = SensePackLoader(sample_pack)
    loader.load()
    db.install_pack(loader, str(sample_pack))
    return db_conn


class TestCitationGlossResult:
    """Tests for CitationGlossResult."""

    def test_to_dict_includes_citation_fields(self):
        """Test serialization includes citation fields."""
        result = CitationGlossResult(
            gloss="word",
            source="LSJ",
            confidence=0.9,
            alternatives=["speech", "reason"],
            source_title="A Greek-English Lexicon",
            edition="9th",
            publisher="Clarendon Press",
            year=1996,
        )

        d = result.to_dict()
        assert d["gloss"] == "word"
        assert d["source"] == "LSJ"
        assert d["source_title"] == "A Greek-English Lexicon"
        assert d["edition"] == "9th"
        assert d["year"] == 1996

    def test_citation_dict(self):
        """Test citation_dict returns minimal provenance."""
        result = CitationGlossResult(
            gloss="word",
            source="LSJ",
            confidence=0.9,
            source_title="A Greek-English Lexicon",
            edition="9th",
        )

        citation = result.citation_dict()
        assert "source_id" in citation
        assert citation["source_id"] == "LSJ"
        assert citation["source_title"] == "A Greek-English Lexicon"


class TestSensePackProvider:
    """Tests for SensePackProvider."""

    def test_lookup_returns_citation_result(self, db_with_pack):
        """Test lookup returns CitationGlossResult."""
        provider = SensePackProvider(db_with_pack)
        result = provider.lookup("λόγος")

        assert result is not None
        assert isinstance(result, CitationGlossResult)
        assert result.gloss == "word"
        assert result.source == "TEST"
        assert result.source_title == "Test Greek Dictionary"

    def test_lookup_includes_alternatives(self, db_with_pack):
        """Test lookup includes alternative glosses."""
        provider = SensePackProvider(db_with_pack)
        result = provider.lookup("λόγος")

        assert result is not None
        assert "reason" in result.alternatives

    def test_lookup_missing_lemma(self, db_with_pack):
        """Test lookup returns None for missing lemma."""
        provider = SensePackProvider(db_with_pack)
        result = provider.lookup("nonexistent")

        assert result is None

    def test_lookup_all(self, db_with_pack):
        """Test lookup_all returns all senses."""
        provider = SensePackProvider(db_with_pack)
        results = provider.lookup_all("λόγος")

        assert len(results) == 2
        glosses = {r.gloss for r in results}
        assert "word" in glosses
        assert "reason" in glosses

    def test_source_id_reflects_packs(self, db_with_pack):
        """Test source_id includes pack information."""
        provider = SensePackProvider(db_with_pack)
        assert "test-senses" in provider.source_id

    def test_has_senses(self, db_with_pack):
        """Test has_senses returns True when packs installed."""
        provider = SensePackProvider(db_with_pack)
        assert provider.has_senses()

    def test_no_senses_when_empty(self, db_conn):
        """Test has_senses returns False when no packs."""
        provider = SensePackProvider(db_conn)
        assert not provider.has_senses()

    def test_get_installed_packs(self, db_with_pack):
        """Test get_installed_packs returns pack info."""
        provider = SensePackProvider(db_with_pack)
        packs = provider.get_installed_packs()

        assert len(packs) == 1
        assert packs[0]["pack_id"] == "test-senses"
        assert packs[0]["source_id"] == "TEST"


class TestChainedSenseProvider:
    """Tests for ChainedSenseProvider."""

    def test_uses_sense_pack_first(self, db_with_pack):
        """Test that sense packs are tried before basic glosses."""
        provider = ChainedSenseProvider(conn=db_with_pack, include_basic=True)
        result = provider.lookup("λόγος")

        assert result is not None
        # Should get sense pack result, not basic
        assert result.source == "TEST"

    def test_falls_back_to_basic(self, db_conn):
        """Test fallback to BasicGlossProvider."""
        # Empty sense pack DB
        provider = ChainedSenseProvider(conn=db_conn, include_basic=True)
        result = provider.lookup("θεός")

        assert result is not None
        assert result.source == "basic_glosses"

    def test_lookup_with_citation(self, db_with_pack):
        """Test lookup_with_citation returns CitationGlossResult."""
        provider = ChainedSenseProvider(conn=db_with_pack)
        result = provider.lookup_with_citation("λόγος")

        assert result is not None
        assert isinstance(result, CitationGlossResult)
        assert result.source == "TEST"

    def test_no_providers(self):
        """Test behavior with no providers."""
        provider = ChainedSenseProvider(conn=None, include_basic=False)
        result = provider.lookup("λόγος")

        assert result is None


class TestGetSenseProvider:
    """Tests for get_sense_provider factory."""

    def test_returns_chained_provider(self, db_conn):
        """Test factory returns ChainedSenseProvider."""
        provider = get_sense_provider(db_conn)
        assert isinstance(provider, ChainedSenseProvider)

    def test_works_without_connection(self):
        """Test factory works without DB connection."""
        provider = get_sense_provider(None)
        assert isinstance(provider, ChainedSenseProvider)
        # Should still have basic provider
        result = provider.lookup("θεός")
        assert result is not None


class TestDeterministicResults:
    """Tests for deterministic behavior."""

    def test_same_pack_same_results(self, db_with_pack):
        """Test that same pack gives same results."""
        provider1 = SensePackProvider(db_with_pack)
        provider2 = SensePackProvider(db_with_pack)

        result1 = provider1.lookup("λόγος")
        result2 = provider2.lookup("λόγος")

        assert result1 is not None
        assert result2 is not None
        assert result1.gloss == result2.gloss
        assert result1.source == result2.source

    def test_results_stable_across_queries(self, db_with_pack):
        """Test multiple queries return same results."""
        provider = SensePackProvider(db_with_pack)

        results = [provider.lookup("λόγος") for _ in range(5)]

        glosses = [r.gloss for r in results if r]
        assert len(set(glosses)) == 1  # All same gloss
