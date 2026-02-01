"""Tests for claim taxonomy and classification.

Tests ADR-009 claim taxonomy implementation.
"""

from redletters.claims.taxonomy import (
    ClaimType,
    Claim,
    TextSpan,
    ClaimDependency,
    VariantDependency,
    GrammarDependency,
)
from redletters.claims.classifier import ClaimClassifier, ClaimContext
from redletters.claims.epistemic_pressure import EpistemicPressureDetector


class TestClaimType:
    """Tests for ClaimType enum."""

    def test_claim_types_ordered_by_epistemic_distance(self):
        """Claim types should be ordered from 0 (descriptive) to 7 (harmonized)."""
        assert ClaimType.TYPE0_DESCRIPTIVE.value == 0
        assert ClaimType.TYPE1_LEXICAL_RANGE.value == 1
        assert ClaimType.TYPE2_GRAMMATICAL.value == 2
        assert ClaimType.TYPE3_CONTEXTUAL.value == 3
        assert ClaimType.TYPE4_THEOLOGICAL.value == 4
        assert ClaimType.TYPE5_MORAL.value == 5
        assert ClaimType.TYPE6_METAPHYSICAL.value == 6
        assert ClaimType.TYPE7_HARMONIZED.value == 7

    def test_claim_type_labels(self):
        """Each claim type should have a human-readable label."""
        assert ClaimType.TYPE0_DESCRIPTIVE.label == "Descriptive"
        assert ClaimType.TYPE4_THEOLOGICAL.label == "Theological"
        assert ClaimType.TYPE7_HARMONIZED.label == "Harmonized"

    def test_base_confidence_decreases_with_type(self):
        """Higher claim types should have lower base confidence."""
        assert ClaimType.TYPE0_DESCRIPTIVE.base_confidence == 1.0
        assert (
            ClaimType.TYPE4_THEOLOGICAL.base_confidence
            < ClaimType.TYPE1_LEXICAL_RANGE.base_confidence
        )
        assert (
            ClaimType.TYPE6_METAPHYSICAL.base_confidence
            < ClaimType.TYPE4_THEOLOGICAL.base_confidence
        )


class TestClaim:
    """Tests for Claim dataclass."""

    def test_create_simple_claim(self):
        """Should create a claim with required fields."""
        span = TextSpan(book="Matthew", chapter=3, verse_start=2)
        claim = Claim(
            claim_type=ClaimType.TYPE0_DESCRIPTIVE,
            text_span=span,
            content="This word is a verb.",
        )

        assert claim.claim_type == ClaimType.TYPE0_DESCRIPTIVE
        assert claim.text_span.ref == "Matthew.3.2"
        assert claim.inference_distance == 0

    def test_claim_with_dependencies(self):
        """Should track dependencies correctly."""
        span = TextSpan(book="John", chapter=1, verse_start=18)
        deps = ClaimDependency(
            variants=[
                VariantDependency(
                    variant_unit_ref="John.1.18",
                    reading_chosen=0,
                    rationale="P66/P75/Sinaiticus support",
                )
            ],
            grammar=[
                GrammarDependency(
                    token_ref="John.1.18.3",
                    parse_choice="subjective genitive",
                    alternatives=["objective genitive"],
                )
            ],
        )
        claim = Claim(
            claim_type=ClaimType.TYPE4_THEOLOGICAL,
            text_span=span,
            content="This teaches the divinity of Christ.",
            dependencies=deps,
        )

        assert claim.dependencies.has_dependencies
        assert claim.dependencies.variant_count == 1
        assert claim.dependencies.total_count == 2

    def test_requires_escalation_for_high_types(self):
        """TYPE5+ claims should require escalation."""
        span = TextSpan(book="Matthew", chapter=5, verse_start=1)

        moral = Claim(
            claim_type=ClaimType.TYPE5_MORAL,
            text_span=span,
            content="Christians must forgive.",
        )
        theological = Claim(
            claim_type=ClaimType.TYPE4_THEOLOGICAL,
            text_span=span,
            content="This refers to Christ.",
        )

        assert moral.requires_escalation
        assert not theological.requires_escalation

    def test_claim_serialization(self):
        """Should serialize to dict for API."""
        span = TextSpan(book="Matthew", chapter=3, verse_start=2)
        claim = Claim(
            claim_type=ClaimType.TYPE2_GRAMMATICAL,
            text_span=span,
            content="This genitive is subjective.",
            confidence=0.75,
        )

        d = claim.to_dict()
        assert d["claim_type"] == 2
        assert d["claim_type_label"] == "Grammatical"
        assert d["text_span"]["ref"] == "Matthew.3.2"
        assert d["confidence"] == 0.75


class TestEpistemicPressureDetector:
    """Tests for epistemic pressure language detection."""

    def test_detect_certainty_markers(self):
        """Should detect certainty markers like 'clearly', 'obviously'."""
        detector = EpistemicPressureDetector()

        text = "Clearly, this text means salvation by faith."
        warnings = detector.detect(text)

        assert len(warnings) >= 1
        assert any(w.matched_text.lower() == "clearly" for w in warnings)
        assert any(w.severity == "block" for w in warnings)

    def test_detect_false_objectivity(self):
        """Should detect false objectivity like 'the text says'."""
        detector = EpistemicPressureDetector()

        text = "The text says that Jesus is God."
        warnings = detector.detect(text)

        assert len(warnings) >= 1
        assert any("text says" in w.matched_text.lower() for w in warnings)

    def test_detect_suppressed_agency(self):
        """Should detect suppressed agency like 'it is clear that'."""
        detector = EpistemicPressureDetector()

        text = "It is clear that Paul intended salvation."
        warnings = detector.detect(text)

        assert len(warnings) >= 1
        assert any("clear" in w.matched_text.lower() for w in warnings)

    def test_no_warnings_for_qualified_language(self):
        """Should not warn on properly qualified language."""
        detector = EpistemicPressureDetector()

        text = "One interpretation suggests this refers to Israel."
        warnings = detector.detect(text)

        # Should have no blocking warnings
        blocking = [w for w in warnings if w.severity == "block"]
        assert len(blocking) == 0

    def test_has_blocking_warnings(self):
        """Should identify if text has any blocking-level warnings."""
        detector = EpistemicPressureDetector()

        assert detector.has_blocking_warnings("Clearly, this is true.")
        assert not detector.has_blocking_warnings("This may be true.")


class TestClaimClassifier:
    """Tests for claim classification."""

    def test_classify_descriptive_claim(self):
        """Should classify pure description as TYPE0."""
        classifier = ClaimClassifier()

        result = classifier.classify("This word is a verb in the aorist tense.")

        assert result.claim_type == ClaimType.TYPE0_DESCRIPTIVE

    def test_classify_lexical_range_claim(self):
        """Should classify semantic range statements as TYPE1."""
        classifier = ClaimClassifier()

        result = classifier.classify(
            "The word logos can mean word, reason, or account."
        )

        assert result.claim_type == ClaimType.TYPE1_LEXICAL_RANGE

    def test_classify_grammatical_claim(self):
        """Should classify grammar-based interpretations as TYPE2.

        Note: "should be parsed" is grammatical advice, not moral prescription.
        The classifier distinguishes grammatical "should" from moral "should".
        """
        classifier = ClaimClassifier()

        # Grammatical "should" - translation/parsing recommendation
        result = classifier.classify(
            "This genitive should be parsed as a subjective genitive based on the syntax."
        )

        assert result.claim_type == ClaimType.TYPE2_GRAMMATICAL

    def test_classify_grammatical_should_vs_moral_should(self):
        """Grammatical 'should be parsed/translated' must not be TYPE5_MORAL.

        This is a critical distinction: 'should be parsed' is grammar advice,
        'Christians should forgive' is moral prescription.
        """
        classifier = ClaimClassifier()

        # These are grammatical recommendations, NOT moral prescriptions
        grammatical_claims = [
            "The verb should be translated as 'love'.",
            "This participle should be read as causal.",
            "The phrase must be understood as a hendiadys.",
            "Scholars should render this as 'faithfulness'.",
        ]

        for claim in grammatical_claims:
            result = classifier.classify(claim)
            assert result.claim_type == ClaimType.TYPE2_GRAMMATICAL, (
                f"'{claim}' should be TYPE2_GRAMMATICAL, got {result.claim_type}"
            )

    def test_classify_theological_claim(self):
        """Should classify doctrinal statements as TYPE4."""
        classifier = ClaimClassifier()

        result = classifier.classify(
            "This passage teaches the doctrine of the Trinity."
        )

        assert result.claim_type == ClaimType.TYPE4_THEOLOGICAL

    def test_classify_moral_claim(self):
        """Should classify ethical prescriptions as TYPE5.

        Moral claims require moral framing: subject (believers/Christians/we)
        + prescriptive language, OR moral vocabulary (sin, righteous, etc.).
        """
        classifier = ClaimClassifier()

        result = classifier.classify(
            "Christians should forgive others unconditionally."
        )

        assert result.claim_type == ClaimType.TYPE5_MORAL

    def test_classify_moral_claim_variations(self):
        """Various moral framing patterns should classify as TYPE5."""
        classifier = ClaimClassifier()

        moral_claims = [
            "Believers must love their enemies.",
            "We should practice forgiveness daily.",
            "Disciples ought to serve one another.",
            "This passage addresses the sin of pride.",
            "The text calls us to righteous living.",
            "You must obey this command.",
        ]

        for claim in moral_claims:
            result = classifier.classify(claim)
            assert result.claim_type == ClaimType.TYPE5_MORAL, (
                f"'{claim}' should be TYPE5_MORAL, got {result.claim_type}"
            )

    def test_classify_boundary_cases_guardrails(self):
        """Lock boundary cases to prevent classifier drift.

        These are the knife-edge cases where "should" could go either way.
        The test locks our intentional decisions so future changes are visible.

        Design decision (per ADR-009): When both grammatical and moral signals
        are present, the classifier conservatively picks the higher type (moral).
        This is intentional: "We should read..." triggers both "we should" (moral)
        and "should read" (grammatical), so it classifies as TYPE5.

        To get TYPE2, use impersonal phrasing: "This should be translated..."
        """
        classifier = ClaimClassifier()

        # GRAMMATICAL: impersonal translation/parsing suggestions (TYPE2)
        # Note: Use impersonal subjects to avoid "we should" moral trigger
        grammatical_boundaries = [
            ("This should be translated as 'love'.", ClaimType.TYPE2_GRAMMATICAL),
            ("The aorist should be rendered 'loved'.", ClaimType.TYPE2_GRAMMATICAL),
            ("The participle should be read as causal.", ClaimType.TYPE2_GRAMMATICAL),
        ]

        for claim, expected in grammatical_boundaries:
            result = classifier.classify(claim)
            assert result.claim_type == expected, (
                f"BOUNDARY: '{claim}' should be {expected.label}, got {result.claim_type.label}"
            )

        # MORAL: "we should" with any following verb (TYPE5)
        # Design: "we should" always triggers moral because "we" implies community
        # Even "We should read this as..." is classified as moral (conservative)
        moral_boundaries = [
            ("We should love our neighbor as ourselves.", ClaimType.TYPE5_MORAL),
            ("We should forgive those who wrong us.", ClaimType.TYPE5_MORAL),
            (
                "We should read this as an imperative.",
                ClaimType.TYPE5_MORAL,
            ),  # Mixed signals → TYPE5
        ]

        for claim, expected in moral_boundaries:
            result = classifier.classify(claim)
            assert result.claim_type == expected, (
                f"BOUNDARY: '{claim}' should be {expected.label}, got {result.claim_type.label}"
            )

    def test_classify_harmonized_claim(self):
        """Should classify cross-reference synthesis as TYPE7."""
        classifier = ClaimClassifier()

        result = classifier.classify(
            "When read with Romans 8, this passage confirms election."
        )

        assert result.claim_type == ClaimType.TYPE7_HARMONIZED

    def test_epistemic_pressure_affects_classification(self):
        """Epistemic pressure should trigger warnings."""
        classifier = ClaimClassifier()

        result = classifier.classify("Clearly, this proves the resurrection happened.")

        assert len(result.warnings) > 0
        assert "Epistemic pressure" in str(result.signals)

    def test_context_affects_minimum_type(self):
        """Context with variants should require minimum TYPE2."""
        classifier = ClaimClassifier()
        context = ClaimContext(
            text_span=TextSpan(book="John", chapter=1, verse_start=18),
            has_variant_at_span=True,
        )

        min_type = classifier.get_minimum_required_type(context)
        assert min_type >= ClaimType.TYPE2_GRAMMATICAL
