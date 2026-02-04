"""Tests for lemma normalization (v0.7.0).

Verifies deterministic, consistent normalization across:
- Diacritical variations
- Case variations
- Unicode normalization forms
"""

from redletters.senses import normalize_lemma, lemma_matches


class TestNormalizeLemma:
    """Tests for normalize_lemma function."""

    def test_strips_accents(self):
        """Accents are removed."""
        assert normalize_lemma("μετανοέω") == "μετανοεω"

    def test_strips_breathing_marks(self):
        """Breathing marks are removed."""
        assert normalize_lemma("ἄνθρωπος") == "ανθρωπος"

    def test_strips_iota_subscript(self):
        """Iota subscript is removed."""
        # Note: ᾳ (alpha with iota subscript) -> α
        assert normalize_lemma("ᾄδω") == "αδω"

    def test_lowercases_by_default(self):
        """Uppercase letters are lowercased by default."""
        assert normalize_lemma("Ἰησοῦς") == "ιησους"
        assert normalize_lemma("ΘΕΟΣ") == "θεος"

    def test_preserve_case_option(self):
        """preserve_case=True keeps original case."""
        assert normalize_lemma("Ἰησοῦς", preserve_case=True) == "Ιησους"
        assert normalize_lemma("ΘΕΟΣ", preserve_case=True) == "ΘΕΟΣ"

    def test_strips_whitespace(self):
        """Leading/trailing whitespace is stripped."""
        assert normalize_lemma("  λόγος  ") == "λογος"

    def test_empty_string(self):
        """Empty string returns empty string."""
        assert normalize_lemma("") == ""

    def test_already_normalized(self):
        """Already normalized text passes through."""
        assert normalize_lemma("θεος") == "θεος"

    def test_deterministic(self):
        """Same input always produces same output."""
        inputs = ["μετανοέω", "ἄνθρωπος", "Ἰησοῦς", "βασιλεία"]
        for inp in inputs:
            result1 = normalize_lemma(inp)
            result2 = normalize_lemma(inp)
            assert result1 == result2, f"Non-deterministic for {inp}"

    def test_nfc_normalization(self):
        """Different Unicode forms normalize to same result."""
        # NFD and NFC representations of same character
        # e with acute: é can be \u00e9 (precomposed) or e\u0301 (decomposed)
        nfc = "μετανοέω"  # NFC form
        import unicodedata

        nfd = unicodedata.normalize("NFD", nfc)
        assert normalize_lemma(nfc) == normalize_lemma(nfd)


class TestLemmaMatches:
    """Tests for lemma_matches helper."""

    def test_matching_after_normalization(self):
        """Different forms of same lemma match."""
        assert lemma_matches("μετανοέω", "μετανοεω")
        assert lemma_matches("Ἰησοῦς", "ιησους")

    def test_different_lemmas_dont_match(self):
        """Different lemmas do not match."""
        assert not lemma_matches("θεός", "λόγος")
        assert not lemma_matches("μετανοέω", "ἄνθρωπος")

    def test_case_insensitive_by_default(self):
        """Matching is case-insensitive."""
        assert lemma_matches("ΘΕΟΣ", "θεός")
        assert lemma_matches("Ἰησοῦς", "ΙΗΣΟΥΣ")


class TestNormalizationConsistency:
    """Tests verifying normalization is consistent with SensePackDB lookups."""

    def test_common_nt_lemmas(self):
        """Common NT lemmas normalize predictably."""
        test_cases = [
            ("λόγος", "λογος"),
            ("θεός", "θεος"),
            ("Χριστός", "χριστος"),
            ("πνεῦμα", "πνευμα"),
            ("ἀγάπη", "αγαπη"),
            ("πίστις", "πιστις"),
            ("δικαιοσύνη", "δικαιοσυνη"),
            ("βασιλεία", "βασιλεια"),
            ("ἐκκλησία", "εκκλησια"),
            ("εὐαγγέλιον", "ευαγγελιον"),
        ]
        for original, expected in test_cases:
            assert normalize_lemma(original) == expected, f"Failed for {original}"

    def test_verbs_with_augment(self):
        """Verbs with various diacriticals normalize correctly."""
        test_cases = [
            ("εἰμί", "ειμι"),
            ("λέγω", "λεγω"),
            ("ἔρχομαι", "ερχομαι"),
            ("ἀκούω", "ακουω"),
            ("ὁράω", "οραω"),
            ("γινώσκω", "γινωσκω"),
        ]
        for original, expected in test_cases:
            assert normalize_lemma(original) == expected, f"Failed for {original}"
