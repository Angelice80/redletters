"""Tests for parse code validation and category-collapse prevention.

These tests are Constitution-aligned guardrails that prevent:
1. Verbs from having nominal fields (case/gender) - unless participle
2. Nominals from having verbal fields (person/tense/voice/mood)
3. Indeclinables from having any morphological fields
4. Known lemmas from having wrong POS codes

Trust-critical: If decoding is wrong, everything downstream becomes
confidently wrong, which is the single most trust-killing failure mode.
"""

from pathlib import Path

import pytest

from redletters.ingest.morphgnt_parser import (
    INDECLINABLE_POS,
    NOMINAL_POS,
    VERBAL_POS,
    MorphGNTParseError,
    decode_parse_code,
    parse_file,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
MORPHGNT_SAMPLE = FIXTURES_DIR / "morphgnt_sample.tsv"


class TestPOSGatedDecoding:
    """Test that decode_parse_code gates fields by POS category."""

    def test_verb_decoding_populates_verbal_fields(self):
        """Verbs should have tense/voice/mood/person/number populated."""
        # 2PAD-P-- = 2nd person, present, active, imperative, plural
        result = decode_parse_code("2PAD-P--", "V-")

        assert result.person == "2nd"
        assert result.tense == "present"
        assert result.voice == "active"
        assert result.mood == "imperative"
        assert result.number == "plural"
        # Nominal fields must be None for non-participle verbs
        assert result.case is None
        assert result.gender is None
        assert result.degree is None
        assert result.errors == []

    def test_verb_with_case_field_populated_raises_error(self):
        """Non-participle verb with case field should flag an error."""
        # Simulate a malformed parse code: verb with case populated
        # 3PAI-S-N would be invalid (has case 'N' but not a participle)
        result = decode_parse_code("3PAIN---", "V-")

        # Should flag error about case being populated
        assert any("case field populated" in e for e in result.errors)

    def test_verb_with_gender_field_populated_raises_error(self):
        """Non-participle verb with gender field should flag an error."""
        result = decode_parse_code("3PAI--M-", "V-")

        assert any("gender field populated" in e for e in result.errors)

    def test_participle_decoding_has_case_number_gender(self):
        """Participles (verb with mood=P) should have case/number/gender."""
        # -PAPNSM- = present active participle, nominative singular masculine
        result = decode_parse_code("-PAPNSM-", "V-")

        assert result.tense == "present"
        assert result.voice == "active"
        assert result.mood == "participle"
        assert result.case == "nominative"
        assert result.number == "singular"
        assert result.gender == "masculine"
        # Participles should NOT have person
        assert result.person is None
        assert result.errors == []

    def test_nominal_decoding_populates_nominal_fields(self):
        """Nominals should have case/number/gender populated."""
        # ----NSF- = nominative singular feminine
        result = decode_parse_code("----NSF-", "N-")

        assert result.case == "nominative"
        assert result.number == "singular"
        assert result.gender == "feminine"
        # Verbal fields must be None for nominals
        assert result.person is None
        assert result.tense is None
        assert result.voice is None
        assert result.mood is None
        assert result.errors == []

    def test_nominal_with_tense_field_populated_raises_error(self):
        """Nominal with tense field should flag an error."""
        # -P--NSF- would be invalid (has tense 'P' but is noun)
        result = decode_parse_code("-P--NSF-", "N-")

        assert any("tense field populated" in e for e in result.errors)

    def test_nominal_with_voice_field_populated_raises_error(self):
        """Nominal with voice field should flag an error."""
        result = decode_parse_code("--A-NSF-", "N-")

        assert any("voice field populated" in e for e in result.errors)

    def test_nominal_with_mood_field_populated_raises_error(self):
        """Nominal with mood field should flag an error."""
        result = decode_parse_code("---INSF-", "N-")

        assert any("mood field populated" in e for e in result.errors)

    def test_nominal_with_person_field_populated_raises_error(self):
        """Nominal with person field should flag an error."""
        result = decode_parse_code("3---NSF-", "N-")

        assert any("person field populated" in e for e in result.errors)

    def test_indeclinable_decoding_has_no_fields(self):
        """Indeclinables should have all fields as None (except maybe degree)."""
        result = decode_parse_code("--------", "P-")  # Preposition

        assert result.person is None
        assert result.tense is None
        assert result.voice is None
        assert result.mood is None
        assert result.case is None
        assert result.number is None
        assert result.gender is None
        assert result.degree is None
        assert result.errors == []

    def test_indeclinable_with_any_field_populated_raises_error(self):
        """Indeclinable with any morphological field should flag error."""
        # Test various violations
        test_cases = [
            ("3-------", "person"),
            ("-P------", "tense"),
            ("--A-----", "voice"),
            ("---I----", "mood"),
            ("----N---", "case"),
            ("-----P--", "number"),
            ("------M-", "gender"),
        ]

        for parse_code, field_name in test_cases:
            result = decode_parse_code(parse_code, "P-")
            assert any(field_name in e for e in result.errors), (
                f"Should flag error for {field_name} in indeclinable: {parse_code}"
            )


class TestKnownLemmaPOSValidation:
    """Test that known lemmas have expected POS codes in fixtures."""

    def test_apo_is_preposition(self):
        """ἀπό should have POS = P- (preposition), not D- (adverb)."""
        tokens = parse_file(MORPHGNT_SAMPLE)

        # Find ἀπό tokens
        apo_tokens = [t for t in tokens if t.lemma == "ἀπό"]

        assert len(apo_tokens) > 0, "Should have at least one ἀπό token in fixture"

        for token in apo_tokens:
            assert token.pos == "P-", (
                f"ἀπό should be preposition (P-), not {token.pos} at {token.ref}"
            )

    def test_tote_is_adverb(self):
        """τότε should have POS = D- (adverb)."""
        tokens = parse_file(MORPHGNT_SAMPLE)

        tote_tokens = [t for t in tokens if t.lemma == "τότε"]

        assert len(tote_tokens) > 0, "Should have τότε token in fixture"

        for token in tote_tokens:
            assert token.pos == "D-", (
                f"τότε should be adverb (D-), not {token.pos} at {token.ref}"
            )

    def test_metanoeo_is_verb(self):
        """μετανοέω should have POS = V- (verb)."""
        tokens = parse_file(MORPHGNT_SAMPLE)

        # Find μετανοέω tokens
        metanoeo_tokens = [t for t in tokens if t.lemma == "μετανοέω"]

        assert len(metanoeo_tokens) > 0, "Should have μετανοέω tokens in fixture"

        for token in metanoeo_tokens:
            assert token.pos == "V-", (
                f"μετανοέω should be verb (V-), not {token.pos} at {token.ref}"
            )

    def test_basileia_is_noun(self):
        """βασιλεία should have POS = N- (noun)."""
        tokens = parse_file(MORPHGNT_SAMPLE)

        basileia_tokens = [t for t in tokens if t.lemma == "βασιλεία"]

        assert len(basileia_tokens) > 0, "Should have βασιλεία tokens in fixture"

        for token in basileia_tokens:
            assert token.pos == "N-", (
                f"βασιλεία should be noun (N-), not {token.pos} at {token.ref}"
            )


class TestCategoryCollapseGuards:
    """Integration tests that verify no category collapse in real fixture data."""

    def test_all_verbs_have_no_case_unless_participle(self):
        """Verb tokens must not have case populated (unless participle)."""
        tokens = parse_file(MORPHGNT_SAMPLE)

        verb_tokens = [t for t in tokens if t.pos in VERBAL_POS]
        assert len(verb_tokens) > 0, "Should have verb tokens in fixture"

        for token in verb_tokens:
            result = decode_parse_code(token.parse_code, token.pos)

            # If not participle, case must be None
            if result.mood != "participle":
                assert result.case is None, (
                    f"Non-participle verb {token.word} ({token.ref}) "
                    f"has case={result.case}"
                )
                assert result.gender is None, (
                    f"Non-participle verb {token.word} ({token.ref}) "
                    f"has gender={result.gender}"
                )

            # Check for decode errors
            assert result.errors == [], (
                f"Verb {token.word} ({token.ref}) has decode errors: {result.errors}"
            )

    def test_all_nominals_have_no_verbal_fields(self):
        """Nominal tokens must not have tense/voice/mood/person populated."""
        tokens = parse_file(MORPHGNT_SAMPLE)

        nominal_tokens = [t for t in tokens if t.pos in NOMINAL_POS]
        assert len(nominal_tokens) > 0, "Should have nominal tokens in fixture"

        for token in nominal_tokens:
            result = decode_parse_code(token.parse_code, token.pos)

            assert result.person is None, (
                f"Nominal {token.word} ({token.ref}) has person={result.person}"
            )
            assert result.tense is None, (
                f"Nominal {token.word} ({token.ref}) has tense={result.tense}"
            )
            assert result.voice is None, (
                f"Nominal {token.word} ({token.ref}) has voice={result.voice}"
            )
            assert result.mood is None, (
                f"Nominal {token.word} ({token.ref}) has mood={result.mood}"
            )

            assert result.errors == [], (
                f"Nominal {token.word} ({token.ref}) has decode errors: {result.errors}"
            )

    def test_all_indeclinables_have_empty_parse(self):
        """Indeclinable tokens should have all dashes in parse code."""
        tokens = parse_file(MORPHGNT_SAMPLE)

        indeclinable_tokens = [t for t in tokens if t.pos in INDECLINABLE_POS]
        assert len(indeclinable_tokens) > 0, "Should have indeclinable tokens"

        for token in indeclinable_tokens:
            result = decode_parse_code(token.parse_code, token.pos)

            # All fields except possibly degree should be None
            assert result.person is None, (
                f"Indeclinable {token.word} ({token.ref}) has person"
            )
            assert result.tense is None, (
                f"Indeclinable {token.word} ({token.ref}) has tense"
            )
            assert result.voice is None, (
                f"Indeclinable {token.word} ({token.ref}) has voice"
            )
            assert result.mood is None, (
                f"Indeclinable {token.word} ({token.ref}) has mood"
            )
            assert result.case is None, (
                f"Indeclinable {token.word} ({token.ref}) has case"
            )
            assert result.number is None, (
                f"Indeclinable {token.word} ({token.ref}) has number"
            )
            assert result.gender is None, (
                f"Indeclinable {token.word} ({token.ref}) has gender"
            )

            assert result.errors == [], (
                f"Indeclinable {token.word} ({token.ref}) has decode errors: "
                f"{result.errors}"
            )


class TestSourceRefAndTokenIndex:
    """Test that source_ref and token_index are stored correctly."""

    def test_source_ref_is_raw_morphgnt_reference(self):
        """source_ref should be the raw 6-digit MorphGNT reference."""
        tokens = parse_file(MORPHGNT_SAMPLE)

        for token in tokens:
            assert len(token.source_ref) == 6, (
                f"source_ref should be 6 chars: {token.source_ref}"
            )
            assert token.source_ref.isdigit(), (
                f"source_ref should be numeric: {token.source_ref}"
            )

    def test_token_index_is_explicit_integer(self):
        """token_index should be an explicit integer, not inferred from string."""
        tokens = parse_file(MORPHGNT_SAMPLE)

        for token in tokens:
            assert isinstance(token.token_index, int), (
                f"token_index should be int: {type(token.token_index)}"
            )
            assert token.token_index >= 1, (
                f"token_index should be 1-based: {token.token_index}"
            )

    def test_token_index_equals_position(self):
        """token_index should equal position for consistency."""
        tokens = parse_file(MORPHGNT_SAMPLE)

        for token in tokens:
            assert token.token_index == token.position, (
                f"token_index ({token.token_index}) != "
                f"position ({token.position}) for {token.ref}"
            )

    def test_ref_can_be_reconstructed_from_parts(self):
        """ref should be reconstructable from book, chapter, verse, position."""
        tokens = parse_file(MORPHGNT_SAMPLE)

        for token in tokens:
            expected_ref = (
                f"{token.book}.{token.chapter}.{token.verse}.{token.position}"
            )
            assert token.ref == expected_ref, (
                f"ref mismatch: {token.ref} != {expected_ref}"
            )


class TestStructuralValidation:
    """Test that structural validation catches malformed data."""

    def test_wrong_column_count_raises_error(self, tmp_path):
        """Lines with wrong column count should raise MorphGNTParseError."""
        bad_file = tmp_path / "bad.tsv"
        bad_file.write_text("010101\tV-\t2PAD-P--\tΜετανοεῖτε\n")  # Only 4 columns

        with pytest.raises(MorphGNTParseError) as exc_info:
            parse_file(bad_file)

        assert "7 columns" in str(exc_info.value)
        assert "Line 1" in str(exc_info.value)

    def test_wrong_parse_code_length_raises_error(self, tmp_path):
        """Parse codes not 8 characters should raise error."""
        bad_file = tmp_path / "bad.tsv"
        bad_file.write_text(
            "010101\tV-\t2PAD\tΜετανοεῖτε\tΜετανοεῖτε\tμετανοεῖτε\tμετανοέω\n"
        )

        with pytest.raises(MorphGNTParseError) as exc_info:
            parse_file(bad_file)

        assert "8 characters" in str(exc_info.value)

    def test_wrong_reference_length_raises_error(self, tmp_path):
        """Reference codes not 6 digits should raise error."""
        bad_file = tmp_path / "bad.tsv"
        bad_file.write_text(
            "0101\tV-\t2PAD-P--\tΜετανοεῖτε\tΜετανοεῖτε\tμετανοεῖτε\tμετανοέω\n"
        )

        with pytest.raises(MorphGNTParseError) as exc_info:
            parse_file(bad_file)

        assert "reference code length" in str(exc_info.value).lower()


class TestParseCodeDecodingEdgeCases:
    """Test edge cases in parse code decoding."""

    def test_unknown_code_generates_warning(self):
        """Unknown position codes should generate warnings."""
        result = decode_parse_code("ZZZZZZZZ", "V-")

        assert len(result.warnings) > 0, "Should have warnings for unknown codes"

    def test_invalid_length_generates_error(self):
        """Parse codes not 8 chars should generate error."""
        result = decode_parse_code("2PAD", "V-")

        assert len(result.errors) > 0, "Should have errors for invalid length"
        assert any("length" in e for e in result.errors)

    def test_unknown_pos_populates_all_fields_with_warning(self):
        """Unknown POS should populate all fields but warn."""
        result = decode_parse_code("2PAD-P--", "ZZ")  # Invalid POS

        assert len(result.warnings) > 0
        assert any("Unknown POS" in w for w in result.warnings)
        # All fields should be populated
        assert result.person is not None
        assert result.tense is not None
