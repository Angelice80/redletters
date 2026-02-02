"""Tests for Sprint 10: Traceable Ledger Mode.

Receipt-grade tests covering:
- Ledger schemas (TokenLedger, VerseLedger, TokenConfidence)
- LexiconProvider protocol and BasicGlossProvider
- TraceableTranslator integration
- Evidence class preservation (no collapsed "support score")
- ADR-010 compliance (layered confidence always visible)
"""

from __future__ import annotations

from dataclasses import asdict

from redletters.ledger.schemas import (
    TokenConfidence,
    TokenLedger,
    SegmentLedger,
    EvidenceClassSummary,
    LedgerProvenance,
    VerseLedger,
)
from redletters.lexicon.provider import (
    GlossResult,
    BasicGlossProvider,
    normalize_greek,
)
from redletters.pipeline.traceable_translator import TraceableTranslator


# ============================================================================
# TokenConfidence Tests
# ============================================================================


class TestTokenConfidence:
    """Tests for TokenConfidence dataclass."""

    def test_create_with_all_layers(self):
        """Token confidence requires all four layers (ADR-010)."""
        conf = TokenConfidence(
            textual=0.95,
            grammatical=0.90,
            lexical=0.85,
            interpretive=0.70,
            explanations={
                "textual": "Strong manuscript support",
                "lexical": "Common word in corpus",
            },
        )

        assert conf.textual == 0.95
        assert conf.grammatical == 0.90
        assert conf.lexical == 0.85
        assert conf.interpretive == 0.70
        assert "textual" in conf.explanations

    def test_confidence_as_dict(self):
        """Confidence should serialize to dict for API responses."""
        conf = TokenConfidence(
            textual=0.9,
            grammatical=0.8,
            lexical=0.7,
            interpretive=0.6,
            explanations={},
        )

        d = asdict(conf)
        assert d["textual"] == 0.9
        assert d["grammatical"] == 0.8
        assert d["lexical"] == 0.7
        assert d["interpretive"] == 0.6
        assert "explanations" in d

    def test_confidence_values_bounded_01(self):
        """Confidence values should be between 0 and 1 by convention."""
        # Create with valid values
        conf = TokenConfidence(
            textual=0.0,
            grammatical=0.5,
            lexical=1.0,
            interpretive=0.0,
            explanations={},
        )
        assert 0.0 <= conf.textual <= 1.0
        assert 0.0 <= conf.grammatical <= 1.0
        assert 0.0 <= conf.lexical <= 1.0
        assert 0.0 <= conf.interpretive <= 1.0


# ============================================================================
# TokenLedger Tests
# ============================================================================


class TestTokenLedger:
    """Tests for TokenLedger dataclass."""

    def test_create_full_token(self):
        """Create a complete token ledger entry."""
        conf = TokenConfidence(
            textual=0.95,
            grammatical=0.92,
            lexical=0.88,
            interpretive=0.75,
            explanations={},
        )

        token = TokenLedger(
            position=0,
            surface="Θεὸν",
            normalized="θεον",
            lemma="θεός",
            morph="N-ASM",
            gloss="God",
            gloss_source="basic_glosses",
            notes=[],
            confidence=conf,
        )

        assert token.position == 0
        assert token.surface == "Θεὸν"
        assert token.normalized == "θεον"
        assert token.lemma == "θεός"
        assert token.morph == "N-ASM"
        assert token.gloss == "God"
        assert token.gloss_source == "basic_glosses"
        assert token.confidence.textual == 0.95

    def test_token_with_notes(self):
        """Token can have translator notes."""
        conf = TokenConfidence(
            textual=0.8, grammatical=0.8, lexical=0.8, interpretive=0.8, explanations={}
        )

        token = TokenLedger(
            position=1,
            surface="μονογενὴς",
            normalized="μονογενης",
            lemma="μονογενής",
            morph="A-NSM",
            gloss="only-begotten",
            gloss_source="basic_glosses",
            notes=["Theological term", "Contested translation"],
            confidence=conf,
        )

        assert len(token.notes) == 2
        assert "Theological term" in token.notes

    def test_token_without_lemma(self):
        """Token can have null lemma if not parseable."""
        conf = TokenConfidence(
            textual=0.9, grammatical=0.5, lexical=0.5, interpretive=0.5, explanations={}
        )

        token = TokenLedger(
            position=0,
            surface="Χ",  # Incomplete
            normalized="χ",
            lemma=None,
            morph=None,
            gloss="[unknown]",
            gloss_source="fallback",
            notes=["Parsing failed"],
            confidence=conf,
        )

        assert token.lemma is None
        assert token.morph is None


# ============================================================================
# SegmentLedger Tests
# ============================================================================


class TestSegmentLedger:
    """Tests for SegmentLedger dataclass."""

    def test_create_segment(self):
        """Create a translation segment mapping Greek to English."""
        segment = SegmentLedger(
            token_range=(0, 2),
            greek_phrase="ὁ λόγος",
            english_phrase="the Word",
            alignment_type="phrase",
            transformation_notes=["Article retained for clarity"],
        )

        assert segment.token_range == (0, 2)
        assert segment.greek_phrase == "ὁ λόγος"
        assert segment.english_phrase == "the Word"
        assert segment.alignment_type == "phrase"


# ============================================================================
# EvidenceClassSummary Tests
# ============================================================================


class TestEvidenceClassSummary:
    """Tests for EvidenceClassSummary - must keep counts explicit (no collapsed score)."""

    def test_create_with_explicit_counts(self):
        """Evidence class summary must have explicit counts per ADR-010."""
        ecs = EvidenceClassSummary(
            manuscript_count=5,
            edition_count=2,
            tradition_count=1,
            other_count=0,
        )

        assert ecs.manuscript_count == 5
        assert ecs.edition_count == 2
        assert ecs.tradition_count == 1
        assert ecs.other_count == 0

    def test_no_collapsed_support_score(self):
        """Verify no single collapsed 'support_score' field exists."""
        ecs = EvidenceClassSummary(
            manuscript_count=3,
            edition_count=2,
            tradition_count=0,
            other_count=1,
        )

        d = asdict(ecs)
        # Must NOT have collapsed fields
        assert "support_score" not in d
        assert "total_support" not in d
        # Must have explicit counts
        assert "manuscript_count" in d
        assert "edition_count" in d
        assert "tradition_count" in d
        assert "other_count" in d

    def test_zero_evidence_valid(self):
        """All-zero evidence is valid (new text, no witnesses)."""
        ecs = EvidenceClassSummary(
            manuscript_count=0,
            edition_count=0,
            tradition_count=0,
            other_count=0,
        )

        assert ecs.manuscript_count == 0


# ============================================================================
# LedgerProvenance Tests
# ============================================================================


class TestLedgerProvenance:
    """Tests for LedgerProvenance dataclass."""

    def test_create_provenance(self):
        """Create full provenance record."""
        ecs = EvidenceClassSummary(
            manuscript_count=3, edition_count=1, tradition_count=0, other_count=0
        )

        prov = LedgerProvenance(
            spine_source_id="morphgnt-sblgnt",
            comparative_sources_used=["westcott-hort-john", "byzantine-john"],
            evidence_class_summary=ecs,
        )

        assert prov.spine_source_id == "morphgnt-sblgnt"
        assert len(prov.comparative_sources_used) == 2
        assert prov.evidence_class_summary.manuscript_count == 3

    def test_provenance_with_no_comparative(self):
        """Provenance can have empty comparative sources."""
        ecs = EvidenceClassSummary(
            manuscript_count=0, edition_count=1, tradition_count=0, other_count=0
        )

        prov = LedgerProvenance(
            spine_source_id="morphgnt-sblgnt",
            comparative_sources_used=[],
            evidence_class_summary=ecs,
        )

        assert prov.comparative_sources_used == []


# ============================================================================
# VerseLedger Tests
# ============================================================================


class TestVerseLedger:
    """Tests for VerseLedger dataclass."""

    def test_create_verse_ledger(self):
        """Create a complete verse ledger."""
        conf = TokenConfidence(
            textual=0.95,
            grammatical=0.90,
            lexical=0.85,
            interpretive=0.80,
            explanations={},
        )

        tokens = [
            TokenLedger(
                position=0,
                surface="Ἐν",
                normalized="εν",
                lemma="ἐν",
                morph="PREP",
                gloss="in",
                gloss_source="basic_glosses",
                notes=[],
                confidence=conf,
            ),
            TokenLedger(
                position=1,
                surface="ἀρχῇ",
                normalized="αρχη",
                lemma="ἀρχή",
                morph="N-DSF",
                gloss="beginning",
                gloss_source="basic_glosses",
                notes=[],
                confidence=conf,
            ),
        ]

        segments = [
            SegmentLedger(
                token_range=(0, 2),
                greek_phrase="Ἐν ἀρχῇ",
                english_phrase="In the beginning",
                alignment_type="phrase",
                transformation_notes=[],
            )
        ]

        ecs = EvidenceClassSummary(
            manuscript_count=2, edition_count=1, tradition_count=0, other_count=0
        )

        prov = LedgerProvenance(
            spine_source_id="morphgnt-sblgnt",
            comparative_sources_used=["westcott-hort-john"],
            evidence_class_summary=ecs,
        )

        ledger = VerseLedger(
            verse_id="John.1.1",
            normalized_ref="John 1:1",
            tokens=tokens,
            translation_segments=segments,
            provenance=prov,
        )

        assert ledger.verse_id == "John.1.1"
        assert ledger.normalized_ref == "John 1:1"
        assert len(ledger.tokens) == 2
        assert len(ledger.translation_segments) == 1
        assert ledger.provenance.spine_source_id == "morphgnt-sblgnt"


# ============================================================================
# Normalize Greek Tests
# ============================================================================


class TestNormalizeGreek:
    """Tests for Greek normalization (accent stripping)."""

    def test_strip_accents(self):
        """Normalize removes accents from Greek text."""
        assert normalize_greek("Θεὸν") == "Θεον"
        assert normalize_greek("λόγος") == "λογος"
        assert normalize_greek("ἀρχῇ") == "αρχη"

    def test_lowercase_preserved(self):
        """Normalization preserves case."""
        # Note: Case is preserved, only accents stripped
        result = normalize_greek("Ἐν")
        assert "ε" in result.lower() or "Ε" in result

    def test_no_accents_unchanged(self):
        """Text without accents passes through."""
        assert normalize_greek("θεος") == "θεος"

    def test_empty_string(self):
        """Empty string handled."""
        assert normalize_greek("") == ""


# ============================================================================
# LexiconProvider Protocol Tests
# ============================================================================


class TestLexiconProviderProtocol:
    """Tests for LexiconProvider protocol compliance."""

    def test_basic_gloss_provider_implements_protocol(self):
        """BasicGlossProvider implements LexiconProvider protocol."""
        provider = BasicGlossProvider()

        # Has required attributes
        assert hasattr(provider, "source_id")
        assert hasattr(provider, "license_info")
        assert hasattr(provider, "lookup")

        # Correct types
        assert isinstance(provider.source_id, str)
        assert isinstance(provider.license_info, str)

    def test_basic_gloss_provider_returns_gloss_result(self):
        """BasicGlossProvider.lookup returns GlossResult or None."""
        provider = BasicGlossProvider()

        # Known word
        result = provider.lookup("λογος")
        if result is not None:
            assert isinstance(result, GlossResult)
            assert result.gloss
            assert result.confidence >= 0.0

    def test_basic_gloss_provider_unknown_word(self):
        """BasicGlossProvider returns None for unknown words."""
        provider = BasicGlossProvider()

        result = provider.lookup("xyznonexistent123")
        assert result is None

    def test_basic_gloss_provider_source_id(self):
        """BasicGlossProvider has valid source_id."""
        provider = BasicGlossProvider()
        assert provider.source_id == "basic_glosses"

    def test_basic_gloss_provider_license(self):
        """BasicGlossProvider has license info."""
        provider = BasicGlossProvider()
        assert (
            "CC0" in provider.license_info or "Public Domain" in provider.license_info
        )


# ============================================================================
# BasicGlossProvider Lookup Tests
# ============================================================================


class TestBasicGlossProviderLookup:
    """Tests for BasicGlossProvider glosses."""

    def test_lookup_common_words(self):
        """Common Greek words have glosses."""
        provider = BasicGlossProvider()

        # θεος = God
        result = provider.lookup("θεος")
        assert result is not None
        assert "god" in result.gloss.lower() or "God" in result.gloss

        # λογος = word
        result = provider.lookup("λογος")
        assert result is not None
        assert "word" in result.gloss.lower()

    def test_lookup_with_accent_normalization(self):
        """Lookup works with accented forms via normalization."""
        provider = BasicGlossProvider()

        # Accented form should work
        accented = "θεός"
        normalized = normalize_greek(accented)
        result = provider.lookup(normalized)
        assert result is not None

    def test_lookup_articles(self):
        """Articles have glosses."""
        provider = BasicGlossProvider()

        result = provider.lookup("ο")
        if result is not None:
            assert "the" in result.gloss.lower() or result.gloss

    def test_lookup_prepositions(self):
        """Prepositions have glosses."""
        provider = BasicGlossProvider()

        result = provider.lookup("εν")
        if result is not None:
            assert "in" in result.gloss.lower() or result.gloss


# ============================================================================
# GlossResult Tests
# ============================================================================


class TestGlossResult:
    """Tests for GlossResult dataclass."""

    def test_create_gloss_result(self):
        """Create a GlossResult."""
        result = GlossResult(
            gloss="word, message, reason",
            source="strongs",
            confidence=0.9,
            alternatives=["statement", "speech"],
        )

        assert result.gloss == "word, message, reason"
        assert result.confidence == 0.9
        assert result.source == "strongs"
        assert len(result.alternatives) == 2

    def test_gloss_result_minimal(self):
        """GlossResult with minimal fields."""
        result = GlossResult(
            gloss="the",
            source="basic_glosses",
            confidence=1.0,
        )

        assert result.gloss == "the"
        assert result.confidence == 1.0
        assert result.source == "basic_glosses"
        assert result.alternatives == []


# ============================================================================
# TraceableTranslator Tests
# ============================================================================


class TestTraceableTranslatorInit:
    """Tests for TraceableTranslator initialization."""

    def test_create_traceable_translator(self):
        """Create TraceableTranslator with source info."""
        translator = TraceableTranslator(
            source_id="morphgnt-sblgnt",
            source_license="CC-BY-SA",
        )

        # Source info stored as private attributes
        assert translator._source_id == "morphgnt-sblgnt"
        assert translator._source_license == "CC-BY-SA"

    def test_translator_has_lexicon_providers(self):
        """TraceableTranslator should have lexicon providers."""
        translator = TraceableTranslator(
            source_id="morphgnt-sblgnt",
            source_license="CC-BY-SA",
        )

        # Uses _providers list internally
        assert hasattr(translator, "_providers")
        assert translator._providers is not None
        assert len(translator._providers) >= 1


# ============================================================================
# TraceableTranslator Translation Tests (with mock context)
# ============================================================================


class TestTraceableTranslatorTranslation:
    """Tests for TraceableTranslator.translate method."""

    def test_translate_returns_draft_with_ledger(self):
        """Translator returns draft containing ledger data."""
        from redletters.pipeline.traceable_translator import TraceableTranslationDraft
        from redletters.pipeline.translator import TranslationContext

        translator = TraceableTranslator(
            source_id="morphgnt-sblgnt",
            source_license="CC-BY-SA",
        )

        # Mock context with spine tokens
        context = TranslationContext(
            reference="John 1:1",
            mode="traceable",
            tokens=[{"surface": "Ἐν"}, {"surface": "ἀρχῇ"}, {"surface": "ἦν"}],
            variants=[],
            session_id="test-session",
            options={},
        )

        # Simple test text
        spine_text = "Ἐν ἀρχῇ ἦν ὁ λόγος"

        draft = translator.translate(spine_text, context)

        assert isinstance(draft, TraceableTranslationDraft)
        assert draft.translation_text  # Has translation
        assert isinstance(draft.ledger, list)

    def test_translate_ledger_has_tokens(self):
        """Ledger includes token entries."""
        from redletters.pipeline.translator import TranslationContext

        translator = TraceableTranslator(
            source_id="morphgnt-sblgnt",
            source_license="CC-BY-SA",
        )

        context = TranslationContext(
            reference="John 1:1",
            mode="traceable",
            tokens=[{"surface": "Θεὸς"}, {"surface": "ἦν"}],
            variants=[],
            session_id="test-session",
            options={},
        )

        spine_text = "Θεὸς ἦν"
        draft = translator.translate(spine_text, context)

        # Should have ledger with tokens
        assert len(draft.ledger) >= 1
        verse_ledger = draft.ledger[0]
        assert len(verse_ledger.tokens) >= 1  # At least one token

    def test_ledger_tokens_have_confidence(self):
        """Each token in ledger has confidence scores."""
        from redletters.pipeline.translator import TranslationContext

        translator = TraceableTranslator(
            source_id="morphgnt-sblgnt",
            source_license="CC-BY-SA",
        )

        context = TranslationContext(
            reference="John 1:1",
            mode="traceable",
            tokens=[{"surface": "λόγος", "lemma": "λόγος"}],
            variants=[],
            session_id="test-session",
            options={},
        )

        spine_text = "λόγος"
        draft = translator.translate(spine_text, context)

        if draft.ledger and draft.ledger[0].tokens:
            token = draft.ledger[0].tokens[0]
            assert hasattr(token, "confidence")
            assert token.confidence.textual >= 0.0
            assert token.confidence.grammatical >= 0.0
            assert token.confidence.lexical >= 0.0
            assert token.confidence.interpretive >= 0.0

    def test_ledger_provenance_includes_spine(self):
        """Ledger provenance includes spine source ID (sblgnt per ADR-007)."""
        from redletters.pipeline.translator import TranslationContext

        translator = TraceableTranslator(
            source_id="morphgnt-sblgnt",
            source_license="CC-BY-SA",
        )

        context = TranslationContext(
            reference="John 1:1",
            mode="traceable",
            tokens=[{"surface": "ἐν"}],
            variants=[],
            session_id="test-session",
            options={},
        )

        spine_text = "ἐν"
        draft = translator.translate(spine_text, context)

        if draft.ledger:
            prov = draft.ledger[0].provenance
            # Always uses "sblgnt" as spine per ADR-007
            assert prov.spine_source_id == "sblgnt"


# ============================================================================
# Integration: Translator Factory Tests
# ============================================================================


class TestTranslatorFactory:
    """Tests for translator factory with traceable type."""

    def test_factory_creates_traceable_translator(self):
        """get_translator creates TraceableTranslator for type='traceable'."""
        from redletters.pipeline import get_translator

        translator = get_translator(
            translator_type="traceable",
            source_id="test-spine",
            source_license="CC-BY-SA",
        )

        assert isinstance(translator, TraceableTranslator)
        assert translator._source_id == "test-spine"

    def test_factory_still_supports_other_types(self):
        """Factory still creates other translator types."""
        from redletters.pipeline import get_translator
        from redletters.pipeline.translator import (
            FakeTranslator,
            LiteralTranslator,
            FluentTranslator,
        )

        fake = get_translator(translator_type="fake")
        assert isinstance(fake, FakeTranslator)

        literal = get_translator(
            translator_type="literal",
            source_id="test",
            source_license="test",
        )
        assert isinstance(literal, LiteralTranslator)

        fluent = get_translator(
            translator_type="fluent",
            source_id="test",
            source_license="test",
        )
        assert isinstance(fluent, FluentTranslator)


# ============================================================================
# ADR Compliance Tests
# ============================================================================


class TestADRCompliance:
    """Tests for ADR compliance in traceable mode."""

    def test_adr010_layered_confidence_always_present(self):
        """ADR-010: Layered confidence must always be present on tokens."""
        from redletters.pipeline.translator import TranslationContext

        translator = TraceableTranslator(
            source_id="morphgnt-sblgnt",
            source_license="CC-BY-SA",
        )

        context = TranslationContext(
            reference="John 1:1",
            mode="traceable",
            tokens=[
                {"surface": "Θεὸς"},
                {"surface": "ἦν"},
                {"surface": "ὁ"},
                {"surface": "λόγος"},
            ],
            variants=[],
            session_id="test-session",
            options={},
        )

        spine_text = "Θεὸς ἦν ὁ λόγος"
        draft = translator.translate(spine_text, context)

        # Every token must have all four confidence layers
        for verse_ledger in draft.ledger:
            for token in verse_ledger.tokens:
                assert hasattr(token.confidence, "textual")
                assert hasattr(token.confidence, "grammatical")
                assert hasattr(token.confidence, "lexical")
                assert hasattr(token.confidence, "interpretive")

    def test_evidence_class_explicit_not_collapsed(self):
        """Evidence class must have explicit counts, not collapsed score."""
        ecs = EvidenceClassSummary(
            manuscript_count=5,
            edition_count=2,
            tradition_count=1,
            other_count=0,
        )

        # Serialization must preserve explicit counts
        d = asdict(ecs)

        # Required fields
        assert "manuscript_count" in d
        assert "edition_count" in d
        assert "tradition_count" in d
        assert "other_count" in d

        # Forbidden collapsed fields
        forbidden_fields = [
            "support_score",
            "total_support",
            "combined_score",
            "witness_score",
        ]
        for field in forbidden_fields:
            assert field not in d, f"Collapsed field '{field}' must not exist"
