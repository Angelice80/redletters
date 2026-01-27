"""Tests for database connection and Unicode normalization."""

import tempfile
import unicodedata
from pathlib import Path


from redletters.db.connection import get_connection, init_db, normalize_greek


class TestNormalizeGreek:
    """Tests for Greek text normalization."""

    def test_nfc_normalization(self):
        """NFC normalization produces consistent output."""
        # Composed form (NFC)
        composed = "μετανοέω"
        # Decomposed form (NFD) - same visual appearance, different bytes
        decomposed = unicodedata.normalize("NFD", composed)

        # They should look the same but be different
        assert composed != decomposed
        assert len(composed) != len(decomposed)

        # After normalization, they should be identical
        assert normalize_greek(composed) == normalize_greek(decomposed)

    def test_already_normalized_unchanged(self):
        """Already NFC-normalized text is unchanged."""
        text = "βασιλεία"
        assert normalize_greek(text) == text

    def test_empty_string(self):
        """Empty string returns empty string."""
        assert normalize_greek("") == ""

    def test_ascii_unchanged(self):
        """ASCII text passes through unchanged."""
        assert normalize_greek("hello") == "hello"


class TestGetConnection:
    """Tests for database connection setup."""

    def test_wal_mode_enabled(self):
        """WAL journal mode is enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = get_connection(db_path)

            cursor = conn.execute("PRAGMA journal_mode")
            result = cursor.fetchone()[0]
            assert result == "wal"

            conn.close()

    def test_foreign_keys_enabled(self):
        """Foreign key constraints are enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = get_connection(db_path)

            cursor = conn.execute("PRAGMA foreign_keys")
            result = cursor.fetchone()[0]
            assert result == 1

            conn.close()

    def test_row_factory_set(self):
        """Row factory allows dict-like access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = get_connection(db_path)

            conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
            conn.execute("INSERT INTO test VALUES (1, 'foo')")

            cursor = conn.execute("SELECT * FROM test")
            row = cursor.fetchone()

            # Should be able to access by column name
            assert row["id"] == 1
            assert row["name"] == "foo"

            conn.close()


class TestUnicodeIntegration:
    """Integration tests for Unicode normalization in queries."""

    def test_lemma_lookup_with_different_normalizations(self):
        """Lemma lookups work regardless of Unicode normalization form."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = get_connection(db_path)
            init_db(conn)

            # Insert with NFC form
            lemma_nfc = unicodedata.normalize("NFC", "μετανοέω")
            conn.execute(
                """
                INSERT INTO lexeme_senses (lemma, sense_id, gloss, source, weight)
                VALUES (?, ?, ?, ?, ?)
                """,
                (lemma_nfc, "test.1", "repent", "test", 1.0),
            )
            conn.commit()

            # Query with NFD form (decomposed)
            lemma_nfd = unicodedata.normalize("NFD", "μετανοέω")
            lemma_query = unicodedata.normalize("NFC", lemma_nfd)

            cursor = conn.execute(
                "SELECT gloss FROM lexeme_senses WHERE lemma = ?",
                (lemma_query,),
            )
            result = cursor.fetchone()

            assert result is not None
            assert result["gloss"] == "repent"

            conn.close()
