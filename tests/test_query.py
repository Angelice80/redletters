"""Tests for reference parsing and token retrieval."""

import pytest
from redletters.engine.query import parse_reference, normalize_book_name


class TestParseReference:
    """Tests for parse_reference function."""

    def test_simple_reference(self):
        """Basic reference parsing."""
        ref = parse_reference("Matthew 3:2")
        assert ref.book == "Matthew"
        assert ref.chapter == 3
        assert ref.verse == 2
        assert ref.verse_end is None

    def test_abbreviated_book(self):
        """Abbreviated book names."""
        ref = parse_reference("Matt 3:2")
        assert ref.book == "Matthew"

        ref = parse_reference("Mk 1:15")
        assert ref.book == "Mark"

    def test_verse_range(self):
        """Verse range parsing."""
        ref = parse_reference("John 3:16-17")
        assert ref.verse == 16
        assert ref.verse_end == 17

    def test_invalid_format_raises(self):
        """Invalid formats raise ValueError."""
        with pytest.raises(ValueError):
            parse_reference("not a reference")

        with pytest.raises(ValueError):
            parse_reference("Matthew")

        with pytest.raises(ValueError):
            parse_reference("3:16")

    def test_whitespace_handling(self):
        """Handles extra whitespace."""
        ref = parse_reference("  Matthew   3:2  ")
        assert ref.book == "Matthew"
        assert ref.chapter == 3


class TestNormalizeBookName:
    """Tests for book name normalization."""

    def test_lowercase_conversion(self):
        assert normalize_book_name("matthew") == "Matthew"
        assert normalize_book_name("MARK") == "Mark"

    def test_aliases(self):
        assert normalize_book_name("mt") == "Matthew"
        assert normalize_book_name("jn") == "John"
        assert normalize_book_name("lk") == "Luke"

    def test_unknown_book_titlecased(self):
        assert normalize_book_name("romans") == "Romans"
        assert normalize_book_name("GALATIANS") == "Galatians"
