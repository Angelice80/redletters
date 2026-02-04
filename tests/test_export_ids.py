"""Tests for export ID generation and canonical serialization.

v0.5.0: Reproducible Scholar Exports
"""

from redletters.export.identifiers import (
    verse_id,
    variant_unit_id,
    reading_id,
    token_id,
    normalize_text,
    canonical_json,
    content_hash,
)


class TestVerseId:
    """Test verse ID generation."""

    def test_standard_format(self):
        """Should produce Book.Chapter.Verse format."""
        assert verse_id("John", 1, 18) == "John.1.18"
        assert verse_id("Matthew", 3, 2) == "Matthew.3.2"

    def test_multi_word_book(self):
        """Should handle multi-word book names."""
        assert verse_id("1John", 1, 1) == "1John.1.1"
        assert verse_id("Song of Solomon", 1, 1) == "Song of Solomon.1.1"


class TestVariantUnitId:
    """Test variant unit ID generation."""

    def test_standard_format(self):
        """Should produce verse_id:position format."""
        assert variant_unit_id("John.1.18", 3) == "John.1.18:3"
        assert variant_unit_id("Matthew.3.2", 0) == "Matthew.3.2:0"

    def test_position_zero(self):
        """Should handle position 0."""
        assert variant_unit_id("John.1.1", 0) == "John.1.1:0"


class TestReadingId:
    """Test reading ID generation."""

    def test_deterministic(self):
        """Same inputs should produce same output."""
        id1 = reading_id("John.1.18:3", "μονογενης θεος")
        id2 = reading_id("John.1.18:3", "μονογενης θεος")
        assert id1 == id2

    def test_different_texts_differ(self):
        """Different texts should produce different IDs."""
        id1 = reading_id("John.1.18:3", "μονογενης θεος")
        id2 = reading_id("John.1.18:3", "μονογενης υιος")
        assert id1 != id2

    def test_different_positions_differ(self):
        """Same text at different positions should differ."""
        id1 = reading_id("John.1.18:3", "μονογενης θεος")
        id2 = reading_id("John.1.18:4", "μονογενης θεος")
        assert id1 != id2

    def test_includes_unit_id(self):
        """Should include unit ID as prefix."""
        rid = reading_id("John.1.18:3", "μονογενης θεος")
        assert rid.startswith("John.1.18:3#")

    def test_hash_length(self):
        """Should have 12-char hash suffix."""
        rid = reading_id("John.1.18:3", "μονογενης θεος")
        parts = rid.split("#")
        assert len(parts) == 2
        assert len(parts[1]) == 12


class TestTokenId:
    """Test token ID generation."""

    def test_standard_format(self):
        """Should produce verse_id:position format."""
        assert token_id("John.1.18", 5) == "John.1.18:5"
        assert token_id("Matthew.3.2", 0) == "Matthew.3.2:0"


class TestNormalizeText:
    """Test text normalization."""

    def test_strips_whitespace(self):
        """Should strip leading/trailing whitespace."""
        assert normalize_text("  test  ") == "test"

    def test_lowercases(self):
        """Should lowercase text."""
        assert normalize_text("HELLO") == "hello"

    def test_unicode_normalization(self):
        """Should apply NFC normalization."""
        # Combining characters should be normalized
        text = normalize_text("cafe\u0301")  # e + combining acute
        assert text == "café"


class TestCanonicalJson:
    """Test canonical JSON serialization."""

    def test_sorted_keys(self):
        """Should sort dictionary keys."""
        obj = {"b": 1, "a": 2, "c": 3}
        result = canonical_json(obj)
        assert result == '{"a":2,"b":1,"c":3}'

    def test_no_whitespace(self):
        """Should not add extra whitespace."""
        obj = {"key": "value"}
        result = canonical_json(obj)
        assert " " not in result
        assert "\n" not in result

    def test_no_ascii_escapes(self):
        """Should not escape Unicode characters."""
        obj = {"greek": "μονογενης"}
        result = canonical_json(obj)
        assert "μονογενης" in result
        assert "\\u" not in result

    def test_nested_objects_sorted(self):
        """Should sort keys in nested objects."""
        obj = {"outer": {"b": 1, "a": 2}}
        result = canonical_json(obj)
        assert '"a":2' in result
        assert result.index('"a"') < result.index('"b"')

    def test_deterministic(self):
        """Same object should produce same JSON."""
        obj = {"key": [1, 2, 3], "nested": {"x": "y"}}
        result1 = canonical_json(obj)
        result2 = canonical_json(obj)
        assert result1 == result2


class TestContentHash:
    """Test content hashing."""

    def test_sha256_length(self):
        """Should produce 64-char hex string."""
        h = content_hash({"key": "value"})
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self):
        """Same object should produce same hash."""
        h1 = content_hash({"key": "value"})
        h2 = content_hash({"key": "value"})
        assert h1 == h2

    def test_different_objects_differ(self):
        """Different objects should have different hashes."""
        h1 = content_hash({"key": "value1"})
        h2 = content_hash({"key": "value2"})
        assert h1 != h2

    def test_key_order_independent(self):
        """Key order should not affect hash (canonical JSON sorts keys)."""
        h1 = content_hash({"a": 1, "b": 2})
        h2 = content_hash({"b": 2, "a": 1})
        assert h1 == h2


class TestIdStability:
    """Integration tests for ID stability across sessions."""

    def test_reading_id_stable_across_calls(self):
        """Reading ID should be stable for same inputs."""
        # Simulate generating IDs in different sessions
        id1 = reading_id("John.1.18:3", "μονογενης θεος")

        # "New session" - recalculate
        id2 = reading_id("John.1.18:3", "μονογενης θεος")

        assert id1 == id2, "Reading ID should be stable across sessions"

    def test_content_hash_stable(self):
        """Content hash should be stable for same data."""
        data = {
            "variant_unit_id": "John.1.18:3",
            "readings": [
                {"text": "μονογενης θεος"},
                {"text": "μονογενης υιος"},
            ],
        }

        h1 = content_hash(data)
        h2 = content_hash(data)

        assert h1 == h2, "Content hash should be stable"
