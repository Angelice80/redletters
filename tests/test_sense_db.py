"""Tests for sense pack database operations (v0.6.0).

Covers:
- Schema initialization
- Pack installation to database
- Sense querying with provenance
- Deterministic precedence
"""

import json
import sqlite3

import pytest

from redletters.sources.sense_db import (
    SensePackDB,
    InstalledSensePack,
    init_sense_pack_schema,
)
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
    """Create a sample sense pack directory."""
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
def second_pack(tmp_path):
    """Create a second sense pack for precedence testing."""
    pack_dir = tmp_path / "lsj-excerpt"
    pack_dir.mkdir()
    (pack_dir / "manifest.json").write_text(
        json.dumps(
            {
                "pack_id": "lsj-excerpt",
                "name": "LSJ Excerpt",
                "version": "1.0.0",
                "role": "sense_pack",
                "license": "Public Domain",
                "source_id": "LSJ",
                "source_title": "A Greek-English Lexicon",
                "edition": "9th",
            }
        )
    )
    (pack_dir / "senses.tsv").write_text(
        "lemma\tsense_id\tgloss\tdefinition\tdomain\tweight\n"
        "λόγος\tlogos.1\tspeech\tthe faculty of speech\tlanguage\t0.85\n"
        "λόγος\tlogos.3\taccount\ta reckoning\tcommerce\t0.5\n"
    )
    return pack_dir


class TestSensePackDBSchema:
    """Tests for schema initialization."""

    def test_schema_creates_tables(self, db_conn):
        """Test that schema creates required tables."""
        cursor = db_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor}

        assert "installed_sense_packs" in tables
        assert "pack_senses" in tables

    def test_schema_is_idempotent(self, db_conn):
        """Test that schema can be initialized multiple times."""
        init_sense_pack_schema(db_conn)
        init_sense_pack_schema(db_conn)
        # Should not raise


class TestSensePackDBInstall:
    """Tests for pack installation."""

    def test_install_pack(self, db_conn, sample_pack):
        """Test installing a sense pack."""
        db = SensePackDB(db_conn)
        loader = SensePackLoader(sample_pack)
        loader.load()

        installed = db.install_pack(loader, str(sample_pack), "testhash123")

        assert installed.pack_id == "test-senses"
        assert installed.source_id == "TEST"
        assert db.is_pack_installed("test-senses")

        # Check sense count from database (not from returned object)
        pack = db.get_installed_pack("test-senses")
        assert pack is not None
        assert pack.sense_count == 3

    def test_install_pack_stores_citation_fields(self, db_conn, sample_pack):
        """Test that installation preserves citation-grade metadata."""
        db = SensePackDB(db_conn)
        loader = SensePackLoader(sample_pack)
        loader.load()

        db.install_pack(loader, str(sample_pack))

        pack = db.get_installed_pack("test-senses")
        assert pack is not None
        assert pack.source_id == "TEST"
        assert pack.source_title == "Test Greek Dictionary"
        assert pack.edition == "1st"
        assert pack.publisher == "Test Publisher"
        assert pack.year == 2026

    def test_reinstall_replaces_senses(self, db_conn, sample_pack):
        """Test that reinstalling replaces existing senses."""
        db = SensePackDB(db_conn)
        loader = SensePackLoader(sample_pack)
        loader.load()

        # Install twice
        db.install_pack(loader, str(sample_pack))
        db.install_pack(loader, str(sample_pack))

        # Should still have 3 senses (not 6)
        senses = db.get_senses_for_lemma("λόγος")
        logos_senses = [s for s in senses if s["lemma"] == "λόγος"]
        assert len(logos_senses) == 2

    def test_uninstall_pack(self, db_conn, sample_pack):
        """Test uninstalling a sense pack."""
        db = SensePackDB(db_conn)
        loader = SensePackLoader(sample_pack)
        loader.load()

        db.install_pack(loader, str(sample_pack))
        assert db.is_pack_installed("test-senses")

        result = db.uninstall_pack("test-senses")
        assert result is True
        assert not db.is_pack_installed("test-senses")

        # Senses should be removed
        senses = db.get_senses_for_lemma("λόγος")
        assert len(senses) == 0


class TestSensePackDBQuery:
    """Tests for sense querying."""

    def test_get_senses_for_lemma(self, db_conn, sample_pack):
        """Test querying senses by lemma."""
        db = SensePackDB(db_conn)
        loader = SensePackLoader(sample_pack)
        loader.load()
        db.install_pack(loader, str(sample_pack))

        senses = db.get_senses_for_lemma("λόγος")
        assert len(senses) == 2
        assert senses[0]["gloss"] in ["word", "reason"]

    def test_senses_include_provenance(self, db_conn, sample_pack):
        """Test that senses include citation-grade provenance."""
        db = SensePackDB(db_conn)
        loader = SensePackLoader(sample_pack)
        loader.load()
        db.install_pack(loader, str(sample_pack))

        senses = db.get_senses_for_lemma("λόγος")
        sense = senses[0]

        assert "source_id" in sense
        assert sense["source_id"] == "TEST"
        assert "source_title" in sense
        assert sense["source_title"] == "Test Greek Dictionary"
        assert "license" in sense
        assert sense["edition"] == "1st"
        assert sense["year"] == 2026

    def test_get_primary_gloss(self, db_conn, sample_pack):
        """Test getting highest-weighted gloss."""
        db = SensePackDB(db_conn)
        loader = SensePackLoader(sample_pack)
        loader.load()
        db.install_pack(loader, str(sample_pack))

        gloss = db.get_primary_gloss("λόγος")
        assert gloss is not None
        assert gloss["gloss"] == "word"  # weight 0.9 > 0.6
        assert gloss["source_id"] == "TEST"

    def test_get_senses_missing_lemma(self, db_conn, sample_pack):
        """Test querying for non-existent lemma."""
        db = SensePackDB(db_conn)
        loader = SensePackLoader(sample_pack)
        loader.load()
        db.install_pack(loader, str(sample_pack))

        senses = db.get_senses_for_lemma("nonexistent")
        assert senses == []


class TestSensePackDBPrecedence:
    """Tests for deterministic pack precedence."""

    def test_precedence_by_priority(self, db_conn, sample_pack, second_pack):
        """Test that pack priority determines sense precedence."""
        db = SensePackDB(db_conn)

        # Install first pack with lower priority (higher precedence)
        loader1 = SensePackLoader(sample_pack)
        loader1.load()
        db.install_pack(loader1, str(sample_pack), priority=1)

        # Install second pack with higher priority (lower precedence)
        loader2 = SensePackLoader(second_pack)
        loader2.load()
        db.install_pack(loader2, str(second_pack), priority=2)

        # Query senses - first pack's "word" should come before second's "speech"
        senses = db.get_senses_for_lemma("λόγος")

        # First sense should be from first pack (higher precedence)
        # logos.1 from test-senses should appear, logos.1 from lsj-excerpt should be deduplicated
        sense_ids = [s["sense_id"] for s in senses]
        assert "logos.1" in sense_ids
        assert "logos.2" in sense_ids
        assert "logos.3" in sense_ids  # Only in second pack

    def test_precedence_deduplicate_same_sense_id(
        self, db_conn, sample_pack, second_pack
    ):
        """Test that same sense_id from multiple packs is deduplicated."""
        db = SensePackDB(db_conn)

        loader1 = SensePackLoader(sample_pack)
        loader1.load()
        db.install_pack(loader1, str(sample_pack), priority=1)

        loader2 = SensePackLoader(second_pack)
        loader2.load()
        db.install_pack(loader2, str(second_pack), priority=2)

        senses = db.get_senses_for_lemma("λόγος")

        # Should have 3 senses total: logos.1 (from first), logos.2, logos.3
        assert len(senses) == 3

        # The logos.1 should be from first pack (word, not speech)
        logos1 = next(s for s in senses if s["sense_id"] == "logos.1")
        assert logos1["gloss"] == "word"
        assert logos1["source_id"] == "TEST"

    def test_auto_priority_by_install_order(self, db_conn, sample_pack, second_pack):
        """Test that auto-assigned priority follows install order."""
        db = SensePackDB(db_conn)

        # Install without explicit priority
        loader1 = SensePackLoader(sample_pack)
        loader1.load()
        db.install_pack(loader1, str(sample_pack))

        loader2 = SensePackLoader(second_pack)
        loader2.load()
        db.install_pack(loader2, str(second_pack))

        packs = db.get_all_installed_packs()
        assert len(packs) == 2
        assert packs[0].priority < packs[1].priority


class TestInstalledSensePack:
    """Tests for InstalledSensePack dataclass."""

    def test_citation_dict(self):
        """Test citation_dict method."""
        pack = InstalledSensePack(
            pack_id="test",
            name="Test",
            version="1.0",
            license="CC BY-SA 4.0",
            source_id="TEST",
            source_title="Test Dictionary",
            edition="2nd",
            publisher="Test Press",
            year=2025,
            license_url="https://example.com/license",
        )

        citation = pack.citation_dict()
        assert citation["source_id"] == "TEST"
        assert citation["source_title"] == "Test Dictionary"
        assert citation["license"] == "CC BY-SA 4.0"
        assert citation["edition"] == "2nd"
        assert citation["year"] == 2025
        assert citation["license_url"] == "https://example.com/license"

    def test_to_dict(self):
        """Test to_dict serialization."""
        pack = InstalledSensePack(
            pack_id="test",
            name="Test",
            version="1.0",
            license="CC0",
            source_id="TEST",
            source_title="Test Dictionary",
            installed_at="2026-02-02T12:00:00",
            install_path="/path/to/pack",
            sense_count=100,
        )

        d = pack.to_dict()
        assert d["pack_id"] == "test"
        assert d["source_id"] == "TEST"
        assert d["sense_count"] == 100
