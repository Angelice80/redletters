"""Tests for layered confidence scoring.

Tests ADR-010 confidence implementation.
"""

from redletters.claims.taxonomy import (
    ClaimType,
    Claim,
    TextSpan,
    ClaimDependency,
    ContextDependency,
)
from redletters.confidence.scoring import (
    TextualConfidence,
    GrammaticalConfidence,
    LexicalConfidence,
    InterpretiveConfidence,
    LayeredConfidence,
    ConfidenceCalculator,
)


class TestTextualConfidence:
    """Tests for textual (manuscript) confidence layer."""

    def test_no_variant_high_confidence(self):
        """No variant should give high confidence."""
        conf = TextualConfidence.calculate(variant_exists=False)

        assert conf.score >= 0.4  # At least base score for no variant
        assert "No variant" in conf.rationale

    def test_variant_with_papyri_support(self):
        """Papyri support should increase confidence."""
        conf = TextualConfidence.calculate(
            variant_exists=True,
            papyri_support=True,
            primary_uncials=["א", "B"],
            witness_agreement=0.85,
        )

        assert conf.score >= 0.5  # Should have reasonable confidence
        assert conf.papyri_support
        assert "Papyri" in conf.rationale

    def test_variant_without_support(self):
        """Variant without good support should have low confidence."""
        conf = TextualConfidence.calculate(
            variant_exists=True,
            papyri_support=False,
            primary_uncials=[],
            witness_agreement=0.5,
        )

        assert conf.score < 0.5  # Lower confidence
        assert conf.variant_exists

    def test_early_witness_bonus(self):
        """Early witnesses (2nd-3rd century) should add confidence."""
        conf = TextualConfidence.calculate(
            variant_exists=True,
            earliest_witness_century=2,
            papyri_support=True,
        )

        assert "century" in conf.rationale.lower()

    def test_default_factories(self):
        """Default factories should work."""
        high = TextualConfidence.default_high()
        uncertain = TextualConfidence.default_uncertain()

        assert high.score > uncertain.score


class TestGrammaticalConfidence:
    """Tests for grammatical confidence layer."""

    def test_single_parse_high_confidence(self):
        """Single unambiguous parse should give 1.0."""
        conf = GrammaticalConfidence.calculate(parse_count=1)

        assert conf.score == 1.0
        assert "Single" in conf.rationale

    def test_multiple_parses_lower_confidence(self):
        """Multiple parses should lower confidence."""
        conf = GrammaticalConfidence.calculate(
            parse_count=3,
            chosen_parse="subjective genitive",
            alternatives=["objective genitive", "genitive of source"],
        )

        assert conf.score < 1.0
        assert conf.parse_ambiguity_count == 3
        assert len(conf.alternative_parses) == 2

    def test_syntax_ambiguity_low_confidence(self):
        """Syntactic ambiguity should give low confidence."""
        conf = GrammaticalConfidence.calculate(
            parse_count=2,
            syntax_ambiguous=True,
        )

        assert conf.score <= 0.4

    def test_context_disambiguation_helps(self):
        """Context-based disambiguation should increase score."""
        without_context = GrammaticalConfidence.calculate(
            parse_count=2,
            context_disambiguates=False,
        )
        with_context = GrammaticalConfidence.calculate(
            parse_count=2,
            context_disambiguates=True,
        )

        assert with_context.score > without_context.score


class TestLexicalConfidence:
    """Tests for lexical confidence layer."""

    def test_single_sense_high_confidence(self):
        """Single sense should give 1.0."""
        conf = LexicalConfidence.calculate(
            lemma="δέ",
            sense_count=1,
        )

        assert conf.score == 1.0

    def test_broad_range_lower_confidence(self):
        """Broad semantic range should lower confidence."""
        conf = LexicalConfidence.calculate(
            lemma="λόγος",
            sense_count=12,
            sense_chosen="word",
            sense_range=["word", "reason", "account", "speech"],
        )

        assert conf.score < 0.5
        assert "Broad" in conf.rationale or "range" in conf.rationale.lower()

    def test_collocation_support_helps(self):
        """Collocational support should increase score."""
        without_coll = LexicalConfidence.calculate(
            lemma="λόγος",
            sense_count=8,
            collocation_supported=False,
        )
        with_coll = LexicalConfidence.calculate(
            lemma="λόγος",
            sense_count=8,
            sense_chosen="word",
            collocation_supported=True,
        )

        assert with_coll.score > without_coll.score

    def test_hapax_low_confidence(self):
        """Hapax legomenon should give very low confidence."""
        conf = LexicalConfidence.calculate(
            lemma="ἁπαξλεγόμενον",
            is_hapax=True,
        )

        assert conf.score <= 0.3
        assert "Hapax" in conf.rationale


class TestInterpretiveConfidence:
    """Tests for interpretive confidence layer."""

    def test_descriptive_claim_high_confidence(self):
        """TYPE0 descriptive claim should have base 1.0."""
        conf = InterpretiveConfidence.calculate(claim_type=ClaimType.TYPE0_DESCRIPTIVE)

        assert conf.score == 1.0

    def test_theological_claim_lower_confidence(self):
        """TYPE4 theological claim should have lower base."""
        conf = InterpretiveConfidence.calculate(claim_type=ClaimType.TYPE4_THEOLOGICAL)

        assert conf.score < 0.5
        assert "Theological" in conf.rationale

    def test_metaphysical_claim_lowest_confidence(self):
        """TYPE6 metaphysical claim should have very low base."""
        conf = InterpretiveConfidence.calculate(claim_type=ClaimType.TYPE6_METAPHYSICAL)

        assert conf.score <= 0.3

    def test_inference_steps_reduce_confidence(self):
        """Additional inference steps should reduce score."""
        base = InterpretiveConfidence.calculate(
            claim_type=ClaimType.TYPE3_CONTEXTUAL,
            inference_steps=1,
        )
        extended = InterpretiveConfidence.calculate(
            claim_type=ClaimType.TYPE3_CONTEXTUAL,
            inference_steps=5,
        )

        assert extended.score < base.score

    def test_from_claim_object(self):
        """Should calculate from Claim object."""
        span = TextSpan(book="Matthew", chapter=3, verse_start=2)
        deps = ClaimDependency(
            context=[
                ContextDependency(assumption="Historical context", evidence="Josephus"),
                ContextDependency(assumption="Literary genre", evidence="Narrative"),
            ]
        )
        claim = Claim(
            claim_type=ClaimType.TYPE3_CONTEXTUAL,
            text_span=span,
            content="This refers to the temple destruction.",
            dependencies=deps,
        )

        conf = InterpretiveConfidence.calculate(claim=claim)

        assert conf.claim_type == ClaimType.TYPE3_CONTEXTUAL
        assert conf.assumption_count == 2


class TestLayeredConfidence:
    """Tests for aggregated layered confidence."""

    def test_composite_calculation(self):
        """Composite should be weighted average of layers."""
        textual = TextualConfidence(score=1.0, rationale="Test")
        grammatical = GrammaticalConfidence(score=0.8, rationale="Test")
        lexical = LexicalConfidence(score=0.6, lemma="test", rationale="Test")
        interpretive = InterpretiveConfidence(score=0.4, rationale="Test")

        layered = LayeredConfidence(
            textual=textual,
            grammatical=grammatical,
            lexical=lexical,
            interpretive=interpretive,
        )

        # Default weights: text=0.30, gram=0.25, lex=0.25, interp=0.20
        expected = 1.0 * 0.30 + 0.8 * 0.25 + 0.6 * 0.25 + 0.4 * 0.20
        assert abs(layered.composite - expected) < 0.01

    def test_weakest_layer_identification(self):
        """Should identify the weakest layer."""
        layered = LayeredConfidence(
            textual=TextualConfidence(score=0.9, rationale="Test"),
            grammatical=GrammaticalConfidence(score=0.7, rationale="Test"),
            lexical=LexicalConfidence(score=0.3, lemma="test", rationale="Test"),
            interpretive=InterpretiveConfidence(score=0.5, rationale="Test"),
        )

        assert layered.weakest_layer == "lexical"

    def test_serialization(self):
        """Should serialize to dict for API."""
        layered = LayeredConfidence(
            textual=TextualConfidence(score=0.9, rationale="High support"),
            grammatical=GrammaticalConfidence(score=0.8, rationale="Clear parse"),
            lexical=LexicalConfidence(
                score=0.7, lemma="test", rationale="Limited range"
            ),
            interpretive=InterpretiveConfidence(score=0.6, rationale="TYPE2"),
        )

        d = layered.to_dict()

        assert "composite" in d
        assert "layers" in d
        assert "textual" in d["layers"]
        assert d["layers"]["textual"]["score"] == 0.9
        assert "weakest_layer" in d


class TestConfidenceCalculator:
    """Tests for confidence calculator."""

    def test_calculate_with_defaults(self):
        """Should calculate with default high confidence."""
        calc = ConfidenceCalculator()
        conf = calc.calculate()

        assert conf.composite > 0.8  # All defaults are high

    def test_calculate_with_claim(self):
        """Should incorporate claim type into interpretive layer."""
        calc = ConfidenceCalculator()
        span = TextSpan(book="Matthew", chapter=5, verse_start=1)
        claim = Claim(
            claim_type=ClaimType.TYPE4_THEOLOGICAL,
            text_span=span,
            content="Test theological claim.",
        )

        conf = calc.calculate(claim=claim)

        assert conf.interpretive.claim_type == ClaimType.TYPE4_THEOLOGICAL
        assert conf.interpretive.score < 0.5

    def test_explain_high_confidence(self):
        """Should explain high confidence correctly."""
        calc = ConfidenceCalculator()
        conf = calc.calculate()
        explanation = calc.explain(conf)

        assert "High confidence" in explanation.summary

    def test_explain_low_confidence(self):
        """Should explain low confidence and suggest improvements."""
        calc = ConfidenceCalculator()
        conf = LayeredConfidence(
            textual=TextualConfidence(score=0.3, rationale="Low"),
            grammatical=GrammaticalConfidence(score=0.3, rationale="Low"),
            lexical=LexicalConfidence(score=0.3, lemma="test", rationale="Low"),
            interpretive=InterpretiveConfidence(score=0.3, rationale="Low"),
        )

        explanation = calc.explain(conf)

        assert (
            "Low confidence" in explanation.summary or "Very low" in explanation.summary
        )
        assert len(explanation.improvement_suggestions) > 0

    def test_compare_confidences(self):
        """Should compare two confidence scores."""
        calc = ConfidenceCalculator()
        conf_a = calc.calculate()

        span = TextSpan(book="John", chapter=1, verse_start=18)
        claim = Claim(
            claim_type=ClaimType.TYPE6_METAPHYSICAL,
            text_span=span,
            content="Metaphysical claim.",
        )
        conf_b = calc.calculate(claim=claim)

        comparison = calc.compare(conf_a, conf_b)

        assert "interpretive" in comparison
        # conf_a should have higher interpretive (TYPE0 default vs TYPE6)
        diff = comparison["interpretive"][2]  # (a_score, b_score, difference)
        assert diff > 0
