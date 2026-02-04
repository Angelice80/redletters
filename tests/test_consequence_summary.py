"""Tests for ConsequenceSummary (v0.8.0).

Tests the ConsequenceSummary dataclass and derive_consequence_summary() function.
"""

from __future__ import annotations

from redletters.variants.dossier import (
    ConsequenceSummary,
    derive_consequence_summary,
    DossierVariant,
    DossierReading,
    DossierReason,
    DossierAcknowledgement,
    WitnessSummary,
)


class TestConsequenceSummaryDataclass:
    """Test ConsequenceSummary dataclass."""

    def test_default_notes_is_empty_list(self):
        """Notes defaults to empty list."""
        cs = ConsequenceSummary(
            affects_surface=True,
            affects_gloss=False,
            affects_omission_addition=False,
        )
        assert cs.notes == []

    def test_to_dict_includes_all_fields(self):
        """to_dict() includes all fields."""
        cs = ConsequenceSummary(
            affects_surface=True,
            affects_gloss=True,
            affects_omission_addition=False,
            notes=["test note"],
        )
        d = cs.to_dict()
        assert d["affects_surface"] is True
        assert d["affects_gloss"] is True
        assert d["affects_omission_addition"] is False
        assert d["notes"] == ["test note"]

    def test_to_dict_with_empty_notes(self):
        """to_dict() works with empty notes."""
        cs = ConsequenceSummary(
            affects_surface=False,
            affects_gloss=False,
            affects_omission_addition=False,
        )
        d = cs.to_dict()
        assert d["notes"] == []


class TestDeriveConsequenceSummaryOmission:
    """Test derive_consequence_summary() for OMISSION classification."""

    def test_omission_affects_surface(self):
        """OMISSION affects surface text."""
        cs = derive_consequence_summary("omission")
        assert cs.affects_surface is True

    def test_omission_does_not_affect_gloss(self):
        """OMISSION does not affect gloss."""
        cs = derive_consequence_summary("omission")
        assert cs.affects_gloss is False

    def test_omission_affects_omission_addition(self):
        """OMISSION affects omission/addition."""
        cs = derive_consequence_summary("omission")
        assert cs.affects_omission_addition is True

    def test_omission_has_descriptive_note(self):
        """OMISSION has descriptive note."""
        cs = derive_consequence_summary("omission")
        assert len(cs.notes) > 0
        assert "absence" in cs.notes[0].lower()


class TestDeriveConsequenceSummaryAddition:
    """Test derive_consequence_summary() for ADDITION classification."""

    def test_addition_affects_surface(self):
        """ADDITION affects surface text."""
        cs = derive_consequence_summary("addition")
        assert cs.affects_surface is True

    def test_addition_does_not_affect_gloss(self):
        """ADDITION does not affect gloss."""
        cs = derive_consequence_summary("addition")
        assert cs.affects_gloss is False

    def test_addition_affects_omission_addition(self):
        """ADDITION affects omission/addition."""
        cs = derive_consequence_summary("addition")
        assert cs.affects_omission_addition is True


class TestDeriveConsequenceSummarySubstitution:
    """Test derive_consequence_summary() for SUBSTITUTION classification."""

    def test_substitution_affects_surface(self):
        """SUBSTITUTION affects surface text."""
        cs = derive_consequence_summary("substitution")
        assert cs.affects_surface is True

    def test_substitution_affects_gloss(self):
        """SUBSTITUTION affects gloss."""
        cs = derive_consequence_summary("substitution")
        assert cs.affects_gloss is True

    def test_substitution_does_not_affect_omission_addition(self):
        """SUBSTITUTION does not affect omission/addition."""
        cs = derive_consequence_summary("substitution")
        assert cs.affects_omission_addition is False


class TestDeriveConsequenceSummaryWordOrder:
    """Test derive_consequence_summary() for WORD_ORDER classification."""

    def test_word_order_affects_surface(self):
        """WORD_ORDER affects surface text."""
        cs = derive_consequence_summary("word_order")
        assert cs.affects_surface is True

    def test_word_order_does_not_affect_gloss(self):
        """WORD_ORDER does not affect gloss."""
        cs = derive_consequence_summary("word_order")
        assert cs.affects_gloss is False

    def test_word_order_does_not_affect_omission_addition(self):
        """WORD_ORDER does not affect omission/addition."""
        cs = derive_consequence_summary("word_order")
        assert cs.affects_omission_addition is False


class TestDeriveConsequenceSummarySpelling:
    """Test derive_consequence_summary() for SPELLING classification."""

    def test_spelling_does_not_affect_surface(self):
        """SPELLING does not affect surface text (orthographic only)."""
        cs = derive_consequence_summary("spelling")
        assert cs.affects_surface is False

    def test_spelling_does_not_affect_gloss(self):
        """SPELLING does not affect gloss."""
        cs = derive_consequence_summary("spelling")
        assert cs.affects_gloss is False

    def test_spelling_does_not_affect_omission_addition(self):
        """SPELLING does not affect omission/addition."""
        cs = derive_consequence_summary("spelling")
        assert cs.affects_omission_addition is False


class TestDeriveConsequenceSummaryConflation:
    """Test derive_consequence_summary() for CONFLATION classification."""

    def test_conflation_affects_surface(self):
        """CONFLATION affects surface text."""
        cs = derive_consequence_summary("conflation")
        assert cs.affects_surface is True

    def test_conflation_affects_gloss(self):
        """CONFLATION affects gloss."""
        cs = derive_consequence_summary("conflation")
        assert cs.affects_gloss is True

    def test_conflation_does_not_affect_omission_addition(self):
        """CONFLATION does not affect omission/addition."""
        cs = derive_consequence_summary("conflation")
        assert cs.affects_omission_addition is False


class TestDeriveConsequenceSummaryUnknown:
    """Test derive_consequence_summary() for unknown classification."""

    def test_unknown_defaults_to_conservative(self):
        """Unknown classification uses conservative defaults."""
        cs = derive_consequence_summary("unknown_type")
        # Conservative: assume affects surface and gloss
        assert cs.affects_surface is True
        assert cs.affects_gloss is True
        assert cs.affects_omission_addition is False

    def test_unknown_includes_classification_in_notes(self):
        """Unknown classification includes the classification in notes."""
        cs = derive_consequence_summary("mysterious_variant")
        assert any("mysterious_variant" in note for note in cs.notes)


class TestDossierVariantWithConsequence:
    """Test DossierVariant integration with ConsequenceSummary."""

    def _make_minimal_variant(
        self, consequence: ConsequenceSummary | None = None
    ) -> DossierVariant:
        """Create minimal DossierVariant for testing."""
        return DossierVariant(
            ref="John.1.18",
            position=0,
            classification="substitution",
            significance="significant",
            gating_requirement="requires_acknowledgement",
            reason=DossierReason(code="test", summary="test"),
            readings=[
                DossierReading(
                    index=0,
                    text="test",
                    is_spine=True,
                    witnesses=[],
                    witness_summary=WitnessSummary(),
                    source_packs=[],
                )
            ],
            acknowledgement=DossierAcknowledgement(required=True, acknowledged=False),
            consequence=consequence,
        )

    def test_to_dict_without_consequence(self):
        """to_dict() works without consequence."""
        v = self._make_minimal_variant(consequence=None)
        d = v.to_dict()
        assert "consequence" not in d

    def test_to_dict_with_consequence(self):
        """to_dict() includes consequence when present."""
        cs = ConsequenceSummary(
            affects_surface=True,
            affects_gloss=True,
            affects_omission_addition=False,
            notes=["test"],
        )
        v = self._make_minimal_variant(consequence=cs)
        d = v.to_dict()
        assert "consequence" in d
        assert d["consequence"]["affects_surface"] is True
        assert d["consequence"]["affects_gloss"] is True
