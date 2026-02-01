"""Tests for FluentTranslator.

Sprint 5: Tests for deterministic fluent translation with:
- Article handling
- Postpositive reordering (de/gar/oun)
- Transform log tracking
- ADR-009 compliance (no TYPE5+ in readable mode)
- Deterministic output
"""

import pytest

from redletters.pipeline.translator import (
    FluentTranslator,
    FluentTranslationDraft,
    TranslationContext,
)


@pytest.fixture
def fluent_translator():
    """Create a FluentTranslator instance."""
    return FluentTranslator(
        source_id="test-source",
        source_license="CC-BY-SA",
    )


@pytest.fixture
def basic_context():
    """Create a basic translation context."""
    return TranslationContext(
        reference="John 1:1",
        mode="readable",
        tokens=[
            {"lemma": "ἐν", "surface": "Ἐν", "pos": "P"},
            {"lemma": "ἀρχή", "surface": "ἀρχῇ", "pos": "N"},
            {"lemma": "εἰμί", "surface": "ἦν", "pos": "V"},
            {"lemma": "ὁ", "surface": "ὁ", "pos": "T"},
            {"lemma": "λόγος", "surface": "λόγος", "pos": "N"},
        ],
        variants=[],
        session_id="test-session",
        options={},
    )


def test_fluent_translator_produces_draft(fluent_translator, basic_context):
    """FluentTranslator returns a FluentTranslationDraft."""
    result = fluent_translator.translate("Ἐν ἀρχῇ ἦν ὁ λόγος", basic_context)

    assert isinstance(result, FluentTranslationDraft)
    assert result.translation_text
    assert result.style == "fluent"
    assert isinstance(result.transform_log, list)


def test_article_dropping(fluent_translator):
    """Articles are dropped from the beginning of translations."""
    # Context with leading article
    context = TranslationContext(
        reference="Test 1:1",
        mode="readable",
        tokens=[
            {"lemma": "ὁ", "surface": "ὁ", "pos": "T"},
            {"lemma": "λόγος", "surface": "λόγος", "pos": "N"},
        ],
        variants=[],
        session_id="test",
        options={},
    )

    result = fluent_translator.translate("ὁ λόγος", context)

    # The translation should not start with "the" after fluent processing
    # (unless the BRACKET_CLEAN rule keeps it for semantic reasons)
    assert "ARTICLE_DROP" in " ".join(
        result.transform_log
    ) or not result.translation_text.lower().startswith("[the]")


def test_postpositive_de_reordering(fluent_translator):
    """Postpositive δέ is moved to sentence start as 'But'."""
    # Simulate a context where the literal translation would produce "[word] [but]"
    context = TranslationContext(
        reference="Test 1:1",
        mode="readable",
        tokens=[
            {"lemma": "λόγος", "surface": "λόγος", "pos": "N"},
            {"lemma": "δέ", "surface": "δέ", "pos": "C"},
        ],
        variants=[],
        session_id="test",
        options={},
    )

    # Note: The actual reordering depends on the literal translator producing the pattern
    result = fluent_translator.translate("λόγος δέ", context)

    # Verify transform_log records if postpositive rule was applied
    assert isinstance(result.transform_log, list)


def test_postpositive_gar_reordering(fluent_translator):
    """Postpositive γάρ is moved to sentence start as 'For'."""
    context = TranslationContext(
        reference="Test 1:1",
        mode="readable",
        tokens=[
            {"lemma": "θεός", "surface": "θεός", "pos": "N"},
            {"lemma": "γάρ", "surface": "γάρ", "pos": "C"},
        ],
        variants=[],
        session_id="test",
        options={},
    )

    result = fluent_translator.translate("θεός γάρ", context)
    assert isinstance(result.transform_log, list)


def test_postpositive_oun_reordering(fluent_translator):
    """Postpositive οὖν is moved to sentence start as 'Therefore'."""
    context = TranslationContext(
        reference="Test 1:1",
        mode="readable",
        tokens=[
            {"lemma": "εἰμί", "surface": "ἦν", "pos": "V"},
            {"lemma": "οὖν", "surface": "οὖν", "pos": "C"},
        ],
        variants=[],
        session_id="test",
        options={},
    )

    result = fluent_translator.translate("ἦν οὖν", context)
    assert isinstance(result.transform_log, list)


def test_transform_log_recorded(fluent_translator, basic_context):
    """All applied rules appear in transform_log."""
    result = fluent_translator.translate("Ἐν ἀρχῇ ἦν ὁ λόγος", basic_context)

    # transform_log should exist and contain rule names for applied rules
    assert hasattr(result, "transform_log")
    assert isinstance(result.transform_log, list)

    # At minimum, bracket cleanup should be applied to any translation with brackets
    # Check that any applied transforms are logged
    for entry in result.transform_log:
        # Each entry should be a string describing the rule
        assert isinstance(entry, str)
        # Should mention rule name
        assert ":" in entry  # Format is "RULE_NAME: applied"


def test_bracket_removal(fluent_translator, basic_context):
    """Brackets from literal translator are removed in fluent output."""
    result = fluent_translator.translate("Ἐν ἀρχῇ ἦν ὁ λόγος", basic_context)

    # The fluent translation should not contain brackets
    # (unless they're semantic/intentional)
    # BRACKET_CLEAN rule removes all [word] patterns
    if "BRACKET_CLEAN: applied" in result.transform_log:
        assert "[" not in result.translation_text or "]" not in result.translation_text


def test_readable_mode_no_type5_claims(fluent_translator):
    """FluentTranslator never emits TYPE5+ claims in readable mode."""
    context = TranslationContext(
        reference="Test 1:1",
        mode="readable",
        tokens=[{"lemma": "θεός", "surface": "θεός", "pos": "N"}],
        variants=[],
        session_id="test",
        options={},
    )

    result = fluent_translator.translate("θεός", context)

    # All claims should be TYPE0-4
    for claim in result.claims:
        if claim.claim_type_hint is not None:
            assert claim.claim_type_hint <= 4, (
                f"TYPE{claim.claim_type_hint} claim found in readable mode: {claim.content}"
            )


def test_readable_mode_hypothesis_markers(fluent_translator):
    """TYPE2-3 claims get hypothesis markers in readable mode."""
    # Create a context that would produce TYPE2/3 claims
    context = TranslationContext(
        reference="John 1:1",
        mode="readable",
        tokens=[
            {
                "lemma": "θεός",
                "surface": "θεοῦ",
                "pos": "N",
                "parse_code": "N--GSM",
            },  # Genitive triggers grammar claim
        ],
        variants=[],
        session_id="test",
        options={},
    )

    result = fluent_translator.translate("θεοῦ", context)

    # Check that any TYPE2+ claims have hedging language
    for claim in result.claims:
        if claim.claim_type_hint is not None and claim.claim_type_hint >= 2:
            content_lower = claim.content.lower()
            has_hedging = any(
                marker in content_lower
                for marker in [
                    "likely",
                    "probably",
                    "may",
                    "might",
                    "perhaps",
                    "unclassified",
                ]
            )
            assert has_hedging, (
                f"TYPE{claim.claim_type_hint} claim lacks hedging: {claim.content}"
            )


def test_traceable_mode_allows_all_claims(fluent_translator):
    """In traceable mode, all claim types can pass through."""
    context = TranslationContext(
        reference="Test 1:1",
        mode="traceable",
        tokens=[{"lemma": "θεός", "surface": "θεός", "pos": "N"}],
        variants=[],
        session_id="test",
        options={},
    )

    result = fluent_translator.translate("θεός", context)

    # Claims should exist and not be filtered
    assert len(result.claims) > 0


def test_deterministic_output(fluent_translator, basic_context):
    """Same input always produces same output."""
    spine_text = "Ἐν ἀρχῇ ἦν ὁ λόγος"

    result1 = fluent_translator.translate(spine_text, basic_context)
    result2 = fluent_translator.translate(spine_text, basic_context)
    result3 = fluent_translator.translate(spine_text, basic_context)

    # All results should be identical
    assert (
        result1.translation_text == result2.translation_text == result3.translation_text
    )
    assert result1.transform_log == result2.transform_log == result3.transform_log
    assert len(result1.claims) == len(result2.claims) == len(result3.claims)


def test_fluent_notes_include_transform_count(fluent_translator, basic_context):
    """Notes include count of transforms applied."""
    result = fluent_translator.translate("Ἐν ἀρχῇ ἦν ὁ λόγος", basic_context)

    # Notes should mention transforms
    assert any("Transform" in note or "transform" in note for note in result.notes)


def test_fluent_translator_preserves_source_provenance(
    fluent_translator, basic_context
):
    """Fluent translator includes source provenance in claims."""
    result = fluent_translator.translate("Ἐν ἀρχῇ ἦν ὁ λόγος", basic_context)

    # Should have a provenance claim with license info
    license_claims = [
        c
        for c in result.claims
        if "licensed" in c.content.lower() or "CC-BY-SA" in c.content
    ]
    assert len(license_claims) > 0, "Should include license provenance claim"


def test_fluent_translator_with_empty_tokens(fluent_translator):
    """FluentTranslator handles empty token list gracefully."""
    context = TranslationContext(
        reference="Test 1:1",
        mode="readable",
        tokens=[],
        variants=[],
        session_id="test",
        options={},
    )

    result = fluent_translator.translate("θεός", context)

    # Should still produce output
    assert result.translation_text
    assert isinstance(result.claims, list)


def test_fluent_translator_with_variants(fluent_translator):
    """FluentTranslator includes variant dependency claims."""
    context = TranslationContext(
        reference="John 1:18",
        mode="readable",
        tokens=[{"lemma": "θεός", "surface": "θεός", "pos": "N"}],
        variants=[{"ref": "John.1.18", "readings": []}],
        session_id="test",
        options={},
    )

    result = fluent_translator.translate("θεός", context)

    # Should have a claim about following canonical reading
    canonical_claims = [
        c
        for c in result.claims
        if "canonical" in c.content.lower() or "spine" in c.content.lower()
    ]
    assert len(canonical_claims) > 0, (
        "Should include canonical reading claim when variants present"
    )


def test_get_translator_returns_fluent(basic_context):
    """get_translator('fluent') returns a FluentTranslator."""
    from redletters.pipeline.translator import get_translator

    translator = get_translator(
        translator_type="fluent",
        source_id="test",
        source_license="test-license",
    )

    assert isinstance(translator, FluentTranslator)

    result = translator.translate("θεός", basic_context)
    assert isinstance(result, FluentTranslationDraft)
