"""Tests for claim enforcement rules.

Tests ADR-009 mode-based gating.
"""

import pytest

from redletters.claims.taxonomy import (
    ClaimType,
    Claim,
    TextSpan,
    ClaimDependency,
    GrammarDependency,
    ContextDependency,
)
from redletters.claims.enforcement import (
    EnforcementEngine,
    DependencyRequirement,
)


@pytest.fixture
def engine():
    """Create enforcement engine."""
    return EnforcementEngine()


@pytest.fixture
def span():
    """Create default text span."""
    return TextSpan(book="Matthew", chapter=3, verse_start=2)


class TestReadableModeEnforcement:
    """Tests for readable mode restrictions."""

    def test_type0_allowed_in_readable(self, engine, span):
        """TYPE0 descriptive claims should be fully allowed."""
        claim = Claim(
            claim_type=ClaimType.TYPE0_DESCRIPTIVE,
            text_span=span,
            content="This word is a verb.",
        )

        result = engine.check_claim(claim, "readable")

        assert result.allowed

    def test_type1_allowed_as_range(self, engine, span):
        """TYPE1 claims should be allowed when presenting ranges."""
        claim = Claim(
            claim_type=ClaimType.TYPE1_LEXICAL_RANGE,
            text_span=span,
            content="This word can mean kingdom, reign, or royal power.",
        )

        result = engine.check_claim(claim, "readable")

        assert result.allowed

    def test_type1_blocked_for_single_selection(self, engine, span):
        """TYPE1 should be blocked when selecting single meaning."""
        claim = Claim(
            claim_type=ClaimType.TYPE1_LEXICAL_RANGE,
            text_span=span,
            content="This word means kingdom definitively.",
        )

        result = engine.check_claim(claim, "readable")

        # Should either be blocked or require rewrite
        assert not result.allowed or result.hypothesis_markers_required

    def test_type2_requires_hypothesis_markers(self, engine, span):
        """TYPE2 grammatical claims should require uncertainty markers."""
        claim = Claim(
            claim_type=ClaimType.TYPE2_GRAMMATICAL,
            text_span=span,
            content="This is a subjective genitive.",  # No uncertainty
        )

        result = engine.check_claim(claim, "readable")

        # Should suggest hypothesis markers
        assert result.hypothesis_markers_required or not result.allowed

    def test_type2_allowed_with_hypothesis_markers(self, engine, span):
        """TYPE2 with proper markers should be allowed."""
        claim = Claim(
            claim_type=ClaimType.TYPE2_GRAMMATICAL,
            text_span=span,
            content="This is likely a subjective genitive.",
        )

        result = engine.check_claim(claim, "readable")

        assert result.allowed

    def test_type4_requires_tradition_framing(self, engine, span):
        """TYPE4 theological claims need tradition attribution in readable."""
        claim = Claim(
            claim_type=ClaimType.TYPE4_THEOLOGICAL,
            text_span=span,
            content="This teaches the deity of Christ.",
        )

        result = engine.check_claim(claim, "readable")

        assert not result.allowed
        assert any("tradition" in s.lower() for s in result.rewrite_suggestions)

    def test_type4_allowed_with_tradition(self, engine, span):
        """TYPE4 with tradition attribution should be allowed."""
        claim = Claim(
            claim_type=ClaimType.TYPE4_THEOLOGICAL,
            text_span=span,
            content="In the Reformed tradition, this teaches election.",
        )

        result = engine.check_claim(claim, "readable")

        assert result.allowed

    def test_type5_forbidden_in_readable(self, engine, span):
        """TYPE5 moral claims should be forbidden in readable mode."""
        claim = Claim(
            claim_type=ClaimType.TYPE5_MORAL,
            text_span=span,
            content="Christians must forgive unconditionally.",
        )

        result = engine.check_claim(claim, "readable")

        assert not result.allowed
        assert result.required_escalation == ClaimType.TYPE5_MORAL

    def test_type6_forbidden_in_readable(self, engine, span):
        """TYPE6 metaphysical claims should be forbidden in readable mode."""
        claim = Claim(
            claim_type=ClaimType.TYPE6_METAPHYSICAL,
            text_span=span,
            content="This proves the existence of God.",
        )

        result = engine.check_claim(claim, "readable")

        assert not result.allowed
        assert result.required_escalation == ClaimType.TYPE6_METAPHYSICAL

    def test_type7_forbidden_in_readable(self, engine, span):
        """TYPE7 harmonized claims should be forbidden in readable mode."""
        claim = Claim(
            claim_type=ClaimType.TYPE7_HARMONIZED,
            text_span=span,
            content="When read with Romans 8, this confirms predestination.",
        )

        result = engine.check_claim(claim, "readable")

        assert not result.allowed
        assert result.required_escalation == ClaimType.TYPE7_HARMONIZED

    def test_epistemic_pressure_blocked_in_readable(self, engine, span):
        """Epistemic pressure language should be blocked in readable mode."""
        claim = Claim(
            claim_type=ClaimType.TYPE2_GRAMMATICAL,
            text_span=span,
            content="Clearly, this genitive is subjective.",
        )

        result = engine.check_claim(claim, "readable")

        assert not result.allowed or len(result.epistemic_warnings) > 0


class TestTraceableModeEnforcement:
    """Tests for traceable mode requirements."""

    def test_all_types_allowed_in_traceable(self, engine, span):
        """All claim types should be allowed in traceable mode with dependencies."""
        for claim_type in ClaimType:
            deps = ClaimDependency(
                grammar=[GrammarDependency(token_ref="test", parse_choice="test")],
                context=[ContextDependency(assumption="test", evidence="test")],
            )
            claim = Claim(
                claim_type=claim_type,
                text_span=span,
                content="Test claim.",
                dependencies=deps,
            )

            result = engine.check_claim(claim, "traceable")

            # Should be allowed if dependencies are present
            if claim_type.value >= 2:
                # Higher types need dependencies
                assert result.allowed or len(result.missing_dependencies) > 0
            else:
                # Lower types always allowed
                assert result.allowed

    def test_type2_requires_grammar_dependency(self, engine, span):
        """TYPE2 claims require grammar dependency in traceable."""
        claim_without_deps = Claim(
            claim_type=ClaimType.TYPE2_GRAMMATICAL,
            text_span=span,
            content="This is a subjective genitive.",
        )

        result = engine.check_claim(claim_without_deps, "traceable")

        assert not result.allowed
        assert DependencyRequirement.GRAMMAR in result.missing_dependencies

    def test_type2_allowed_with_grammar_dependency(self, engine, span):
        """TYPE2 claims with grammar dependency should be allowed."""
        deps = ClaimDependency(
            grammar=[
                GrammarDependency(
                    token_ref="Matt.3.2.1",
                    parse_choice="subjective genitive",
                    alternatives=["objective genitive"],
                    rationale="Agency context suggests subject",
                )
            ]
        )
        claim = Claim(
            claim_type=ClaimType.TYPE2_GRAMMATICAL,
            text_span=span,
            content="This is a subjective genitive.",
            dependencies=deps,
        )

        result = engine.check_claim(claim, "traceable")

        assert result.allowed

    def test_type4_requires_tradition_dependency(self, engine, span):
        """TYPE4 claims require tradition attribution."""
        claim = Claim(
            claim_type=ClaimType.TYPE4_THEOLOGICAL,
            text_span=span,
            content="This teaches election.",
        )

        result = engine.check_claim(claim, "traceable")

        # Should require tradition dependency
        assert (
            not result.allowed
            or DependencyRequirement.TRADITION in result.missing_dependencies
        )

    def test_type5_requires_hermeneutic(self, engine, span):
        """TYPE5 moral claims require hermeneutical framework."""
        claim = Claim(
            claim_type=ClaimType.TYPE5_MORAL,
            text_span=span,
            content="Christians must forgive.",
        )

        result = engine.check_claim(claim, "traceable")

        # Should require hermeneutic
        assert (
            not result.allowed
            or DependencyRequirement.HERMENEUTIC in result.missing_dependencies
        )


class TestDependencyRequirements:
    """Tests for dependency requirement lookup."""

    def test_type0_no_dependencies(self, engine):
        """TYPE0 should have no required dependencies."""
        reqs = engine.get_dependency_requirements(ClaimType.TYPE0_DESCRIPTIVE)
        assert len(reqs) == 0

    def test_type2_requires_grammar(self, engine):
        """TYPE2 should require grammar dependency."""
        reqs = engine.get_dependency_requirements(ClaimType.TYPE2_GRAMMATICAL)
        assert DependencyRequirement.GRAMMAR in reqs

    def test_type5_requires_multiple(self, engine):
        """TYPE5 should require tradition and hermeneutic."""
        reqs = engine.get_dependency_requirements(ClaimType.TYPE5_MORAL)
        assert DependencyRequirement.TRADITION in reqs
        assert DependencyRequirement.HERMENEUTIC in reqs


class TestAllowedTypesLookup:
    """Tests for mode-specific type restrictions."""

    def test_readable_mode_restrictions(self, engine):
        """Readable mode should have restrictions on TYPE5-7."""
        allowed = engine.get_allowed_types("readable")

        assert "Fully allowed" in allowed[ClaimType.TYPE0_DESCRIPTIVE]
        assert "Forbidden" in allowed[ClaimType.TYPE5_MORAL]
        assert "Forbidden" in allowed[ClaimType.TYPE6_METAPHYSICAL]
        assert "Forbidden" in allowed[ClaimType.TYPE7_HARMONIZED]

    def test_traceable_mode_all_allowed(self, engine):
        """Traceable mode should allow all types with dependencies."""
        allowed = engine.get_allowed_types("traceable")

        for claim_type in ClaimType:
            assert "Allowed" in allowed[claim_type]
