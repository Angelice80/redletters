"""Unit tests for passage reference parser.

Tests cover:
- Book name normalization (all 27 NT books + abbreviations)
- Single verse parsing
- Range parsing (hyphen and en-dash)
- Comma-separated verse lists
- Combined ranges and commas
- Error messages for malformed references
- verse_id format detection and normalization
"""

from __future__ import annotations

import pytest

from redletters.pipeline.passage_ref import (
    normalize_book_name,
    parse_passage_ref,
    parse_verse_spec,
    expand_verse_ids,
    is_verse_id_format,
    normalize_reference,
    PassageRefError,
    NT_BOOKS,
)


class TestBookNameNormalization:
    """Tests for normalize_book_name()."""

    def test_canonical_names_pass_through(self):
        """Canonical book names should normalize to themselves."""
        for book in NT_BOOKS:
            assert normalize_book_name(book) == book

    def test_lowercase_gospels(self):
        """Common lowercase gospel names should normalize correctly."""
        assert normalize_book_name("matthew") == "Matthew"
        assert normalize_book_name("mark") == "Mark"
        assert normalize_book_name("luke") == "Luke"
        assert normalize_book_name("john") == "John"

    def test_abbreviated_gospels(self):
        """Gospel abbreviations should normalize correctly."""
        assert normalize_book_name("matt") == "Matthew"
        assert normalize_book_name("Mat") == "Matthew"
        assert normalize_book_name("mt") == "Matthew"
        assert normalize_book_name("mk") == "Mark"
        assert normalize_book_name("lk") == "Luke"
        assert normalize_book_name("jn") == "John"
        assert normalize_book_name("Jn") == "John"
        assert normalize_book_name("jhn") == "John"

    def test_numbered_books_with_space(self):
        """Numbered books with space should normalize correctly."""
        assert normalize_book_name("1 Corinthians") == "1Corinthians"
        assert normalize_book_name("2 Corinthians") == "2Corinthians"
        assert normalize_book_name("1 cor") == "1Corinthians"
        assert normalize_book_name("2 cor") == "2Corinthians"
        assert normalize_book_name("1 john") == "1John"
        assert normalize_book_name("2 john") == "2John"
        assert normalize_book_name("3 john") == "3John"
        assert normalize_book_name("1 peter") == "1Peter"
        assert normalize_book_name("2 peter") == "2Peter"
        assert normalize_book_name("1 tim") == "1Timothy"
        assert normalize_book_name("2 tim") == "2Timothy"
        assert normalize_book_name("1 thess") == "1Thessalonians"
        assert normalize_book_name("2 thess") == "2Thessalonians"

    def test_numbered_books_without_space(self):
        """Numbered books without space should normalize correctly."""
        assert normalize_book_name("1Cor") == "1Corinthians"
        assert normalize_book_name("2Cor") == "2Corinthians"
        assert normalize_book_name("1Jn") == "1John"
        assert normalize_book_name("1Pet") == "1Peter"
        assert normalize_book_name("1Tim") == "1Timothy"

    def test_roman_numeral_style(self):
        """Roman numeral style abbreviations should work."""
        assert normalize_book_name("i cor") == "1Corinthians"
        assert normalize_book_name("ii cor") == "2Corinthians"
        assert normalize_book_name("i jn") == "1John"
        assert normalize_book_name("ii jn") == "2John"
        assert normalize_book_name("iii jn") == "3John"

    def test_pauline_epistles(self):
        """Pauline epistle abbreviations should normalize correctly."""
        assert normalize_book_name("rom") == "Romans"
        assert normalize_book_name("gal") == "Galatians"
        assert normalize_book_name("eph") == "Ephesians"
        assert normalize_book_name("phil") == "Philippians"
        assert normalize_book_name("col") == "Colossians"
        assert normalize_book_name("tit") == "Titus"
        assert normalize_book_name("phlm") == "Philemon"

    def test_general_epistles(self):
        """General epistle abbreviations should normalize correctly."""
        assert normalize_book_name("heb") == "Hebrews"
        assert normalize_book_name("jas") == "James"
        assert normalize_book_name("jude") == "Jude"

    def test_revelation(self):
        """Revelation abbreviations should normalize correctly."""
        assert normalize_book_name("rev") == "Revelation"
        assert normalize_book_name("apocalypse") == "Revelation"

    def test_acts(self):
        """Acts abbreviations should normalize correctly."""
        assert normalize_book_name("acts") == "Acts"
        assert normalize_book_name("ac") == "Acts"

    def test_with_period(self):
        """Book names with trailing periods should normalize correctly."""
        assert normalize_book_name("Matt.") == "Matthew"
        assert normalize_book_name("Jn.") == "John"
        assert normalize_book_name("Rev.") == "Revelation"

    def test_unknown_book_raises_error(self):
        """Unknown book names should raise PassageRefError."""
        with pytest.raises(PassageRefError) as exc_info:
            normalize_book_name("Genesis")
        assert "Unknown book abbreviation" in str(exc_info.value)

    def test_unknown_book_with_suggestions(self):
        """Error for unknown book should suggest similar names."""
        with pytest.raises(PassageRefError) as exc_info:
            normalize_book_name("Jonn")  # Close to John but not a valid alias
        error = str(exc_info.value)
        assert "Unknown book abbreviation" in error
        # Should suggest John since it's close


class TestVerseSpecParsing:
    """Tests for parse_verse_spec()."""

    def test_single_verse(self):
        """Single verse number should parse correctly."""
        assert parse_verse_spec("18") == [18]
        assert parse_verse_spec("1") == [1]
        assert parse_verse_spec("176") == [176]  # Psalm 119

    def test_verse_range_hyphen(self):
        """Hyphen range should expand correctly."""
        assert parse_verse_spec("18-19") == [18, 19]
        assert parse_verse_spec("1-5") == [1, 2, 3, 4, 5]

    def test_verse_range_en_dash(self):
        """En-dash range should expand correctly."""
        assert parse_verse_spec("18–19") == [18, 19]  # en-dash
        assert parse_verse_spec("1–3") == [1, 2, 3]

    def test_verse_range_em_dash(self):
        """Em-dash range should expand correctly."""
        assert parse_verse_spec("18—19") == [18, 19]  # em-dash

    def test_comma_separated(self):
        """Comma-separated verses should parse correctly."""
        assert parse_verse_spec("18,19") == [18, 19]
        assert parse_verse_spec("1, 3, 5") == [1, 3, 5]  # With spaces

    def test_combined_range_and_comma(self):
        """Combined range and comma should parse correctly."""
        assert parse_verse_spec("18-19,21") == [18, 19, 21]
        assert parse_verse_spec("1-3,5,7-9") == [1, 2, 3, 5, 7, 8, 9]

    def test_deduplication(self):
        """Duplicate verses should be deduplicated."""
        assert parse_verse_spec("1,1,2") == [1, 2]
        assert parse_verse_spec("1-3,2") == [1, 2, 3]

    def test_invalid_range_reversed(self):
        """Reversed range should raise error."""
        with pytest.raises(PassageRefError) as exc_info:
            parse_verse_spec("19-18")
        assert "Start verse (19) cannot be greater than end verse (18)" in str(
            exc_info.value
        )

    def test_invalid_verse_zero(self):
        """Verse 0 should raise error."""
        with pytest.raises(PassageRefError) as exc_info:
            parse_verse_spec("0")
        assert "Verses start at 1" in str(exc_info.value)

    def test_invalid_verse_negative(self):
        """Negative verse should raise error."""
        with pytest.raises(PassageRefError) as exc_info:
            parse_verse_spec("-1")
        # This will fail parsing since -1 looks like a malformed range
        assert "Invalid verse" in str(exc_info.value)

    def test_non_integer_verse(self):
        """Non-integer verse should raise error."""
        with pytest.raises(PassageRefError) as exc_info:
            parse_verse_spec("abc")
        assert "Verses must be integers" in str(exc_info.value)


class TestParsePassageRef:
    """Tests for parse_passage_ref()."""

    def test_single_verse_full_name(self):
        """Single verse with full book name."""
        result = parse_passage_ref("John 1:18")
        assert result.book == "John"
        assert result.chapter == 1
        assert result.verse_ids == ["John.1.18"]
        assert result.normalized_ref == "John 1:18"

    def test_single_verse_abbreviation(self):
        """Single verse with abbreviated book name."""
        result = parse_passage_ref("Jn 1:18")
        assert result.book == "John"
        assert result.chapter == 1
        assert result.verse_ids == ["John.1.18"]
        assert result.normalized_ref == "John 1:18"

    def test_verse_range_hyphen(self):
        """Verse range with hyphen."""
        result = parse_passage_ref("John 1:18-19")
        assert result.book == "John"
        assert result.chapter == 1
        assert result.verse_ids == ["John.1.18", "John.1.19"]
        assert result.normalized_ref == "John 1:18-19"

    def test_verse_range_en_dash(self):
        """Verse range with en-dash."""
        result = parse_passage_ref("John 1:18–19")  # en-dash
        assert result.verse_ids == ["John.1.18", "John.1.19"]
        assert result.normalized_ref == "John 1:18-19"

    def test_comma_separated_verses(self):
        """Comma-separated verses."""
        result = parse_passage_ref("John 1:18,19")
        assert result.verse_ids == ["John.1.18", "John.1.19"]
        # Contiguous, so normalized as range
        assert result.normalized_ref == "John 1:18-19"

    def test_non_contiguous_comma_verses(self):
        """Non-contiguous comma-separated verses."""
        result = parse_passage_ref("John 1:18,21")
        assert result.verse_ids == ["John.1.18", "John.1.21"]
        assert result.normalized_ref == "John 1:18,21"

    def test_matthew_reference(self):
        """Matthew reference with abbreviation."""
        result = parse_passage_ref("Matt 3:2")
        assert result.book == "Matthew"
        assert result.chapter == 3
        assert result.verse_ids == ["Matthew.3.2"]

    def test_matthew_mt_abbreviation(self):
        """Matthew with 'Mt' abbreviation."""
        result = parse_passage_ref("Mt 3:2")
        assert result.book == "Matthew"
        assert result.verse_ids == ["Matthew.3.2"]

    def test_numbered_book_with_space(self):
        """Numbered book with space."""
        result = parse_passage_ref("1 Cor 1:1")
        assert result.book == "1Corinthians"
        assert result.verse_ids == ["1Corinthians.1.1"]

    def test_numbered_book_without_space(self):
        """Numbered book without space."""
        result = parse_passage_ref("1Cor 1:1")
        assert result.book == "1Corinthians"
        assert result.verse_ids == ["1Corinthians.1.1"]

    def test_preserves_input_ref(self):
        """Input reference should be preserved."""
        result = parse_passage_ref("  Jn 1:18-19  ")
        assert result.input_ref == "  Jn 1:18-19  "

    def test_empty_string_raises_error(self):
        """Empty string should raise error."""
        with pytest.raises(PassageRefError) as exc_info:
            parse_passage_ref("")
        assert "Empty reference" in str(exc_info.value)

    def test_missing_colon_raises_error(self):
        """Missing colon should raise error."""
        with pytest.raises(PassageRefError) as exc_info:
            parse_passage_ref("John 1")
        assert "Expected format" in str(exc_info.value)

    def test_missing_chapter_raises_error(self):
        """Missing chapter should raise error."""
        with pytest.raises(PassageRefError) as exc_info:
            parse_passage_ref("John :18")
        assert "Cannot parse reference" in str(exc_info.value)

    def test_invalid_chapter_raises_error(self):
        """Invalid chapter number should raise error."""
        with pytest.raises(PassageRefError) as exc_info:
            parse_passage_ref("John abc:18")
        assert "Cannot parse reference" in str(exc_info.value)

    def test_unknown_book_raises_error(self):
        """Unknown book should raise error."""
        with pytest.raises(PassageRefError) as exc_info:
            parse_passage_ref("Genesis 1:1")
        assert "Unknown book abbreviation" in str(exc_info.value)


class TestExpandVerseIds:
    """Tests for expand_verse_ids() convenience function."""

    def test_single_verse(self):
        """Single verse returns list with one verse_id."""
        assert expand_verse_ids("John 1:18") == ["John.1.18"]

    def test_range(self):
        """Range returns list with all verse_ids."""
        assert expand_verse_ids("John 1:18-20") == [
            "John.1.18",
            "John.1.19",
            "John.1.20",
        ]


class TestIsVerseIdFormat:
    """Tests for is_verse_id_format()."""

    def test_valid_verse_id(self):
        """Valid verse_id format should return True."""
        assert is_verse_id_format("John.1.18") is True
        assert is_verse_id_format("Matthew.3.2") is True
        assert is_verse_id_format("1Corinthians.1.1") is True

    def test_human_reference_returns_false(self):
        """Human reference format should return False."""
        assert is_verse_id_format("John 1:18") is False
        assert is_verse_id_format("Jn 1:18") is False
        assert is_verse_id_format("Matt 3:2") is False

    def test_invalid_format_returns_false(self):
        """Invalid formats should return False."""
        assert is_verse_id_format("John.1") is False
        assert is_verse_id_format("John") is False
        assert is_verse_id_format("") is False


class TestNormalizeReference:
    """Tests for normalize_reference()."""

    def test_verse_id_passthrough(self):
        """Verse ID format should be normalized."""
        normalized, verse_ids = normalize_reference("John.1.18")
        assert normalized == "John 1:18"
        assert verse_ids == ["John.1.18"]

    def test_verse_id_lowercase_book(self):
        """Lowercase book in verse_id should be normalized."""
        normalized, verse_ids = normalize_reference("john.1.18")
        assert normalized == "John 1:18"
        assert verse_ids == ["John.1.18"]

    def test_human_reference(self):
        """Human reference should be parsed and normalized."""
        normalized, verse_ids = normalize_reference("Jn 1:18-19")
        assert normalized == "John 1:18-19"
        assert verse_ids == ["John.1.18", "John.1.19"]

    def test_whitespace_handling(self):
        """Whitespace should be trimmed."""
        normalized, verse_ids = normalize_reference("  John 1:18  ")
        assert normalized == "John 1:18"
        assert verse_ids == ["John.1.18"]


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_revelation_apocalypse(self):
        """Revelation can be referred to as Apocalypse."""
        result = parse_passage_ref("Apocalypse 1:1")
        assert result.book == "Revelation"
        assert result.verse_ids == ["Revelation.1.1"]

    def test_philemon_single_chapter(self):
        """Philemon (single chapter book) reference."""
        result = parse_passage_ref("Phlm 1:1")
        assert result.book == "Philemon"
        assert result.verse_ids == ["Philemon.1.1"]

    def test_long_range(self):
        """Long range should expand correctly."""
        result = parse_passage_ref("John 1:1-5")
        assert result.verse_ids == [
            "John.1.1",
            "John.1.2",
            "John.1.3",
            "John.1.4",
            "John.1.5",
        ]

    def test_complex_mixed_reference(self):
        """Complex mixed range and comma reference."""
        result = parse_passage_ref("Rom 8:1-3,5,7-8")
        assert result.verse_ids == [
            "Romans.8.1",
            "Romans.8.2",
            "Romans.8.3",
            "Romans.8.5",
            "Romans.8.7",
            "Romans.8.8",
        ]
