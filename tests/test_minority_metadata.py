"""Tests for minority metadata derivation (v0.9.0).

Tests conservative derivation of attestation_strength from support data.
"""

from redletters.variants.dossier import (
    MinorityMetadata,
    derive_minority_metadata,
    SupportSummary,
    TypeSummary,
)


class TestMinorityMetadataDerivation:
    """Tests for derive_minority_metadata function."""

    def test_no_support_returns_none_strength(self):
        """With zero witnesses, attestation_strength should be None."""
        support = SupportSummary(
            total_count=0,
            by_type={},
            earliest_century=None,
            provenance_packs=[],
        )
        result = derive_minority_metadata(support)
        assert result.attestation_strength is None

    def test_multiple_witnesses_is_strong(self):
        """3+ witnesses should yield 'strong' attestation."""
        support = SupportSummary(
            total_count=3,
            by_type={
                "manuscript": TypeSummary(count=3, sigla=["01", "02", "03"]),
            },
            earliest_century=5,
            provenance_packs=["pack-a"],
        )
        result = derive_minority_metadata(support)
        assert result.attestation_strength == "strong"

    def test_early_attestation_is_strong(self):
        """Early attestation (2nd-3rd century) should yield 'strong'."""
        support = SupportSummary(
            total_count=1,
            by_type={
                "manuscript": TypeSummary(count=1, sigla=["P66"], century_range=(2, 2)),
            },
            earliest_century=2,
            provenance_packs=["pack-a"],
        )
        result = derive_minority_metadata(support)
        assert result.attestation_strength == "strong"

    def test_third_century_is_strong(self):
        """3rd century attestation should still be 'strong'."""
        support = SupportSummary(
            total_count=1,
            by_type={
                "manuscript": TypeSummary(count=1, sigla=["P75"], century_range=(3, 3)),
            },
            earliest_century=3,
            provenance_packs=["pack-a"],
        )
        result = derive_minority_metadata(support)
        assert result.attestation_strength == "strong"

    def test_mid_century_single_witness_is_moderate(self):
        """Single witness from 4th-6th century should be 'moderate'."""
        support = SupportSummary(
            total_count=1,
            by_type={
                "manuscript": TypeSummary(count=1, sigla=["A"], century_range=(5, 5)),
            },
            earliest_century=5,
            provenance_packs=["pack-a"],
        )
        result = derive_minority_metadata(support)
        assert result.attestation_strength == "moderate"

    def test_two_witnesses_is_moderate(self):
        """Two witnesses without early attestation should be 'moderate'."""
        support = SupportSummary(
            total_count=2,
            by_type={
                "manuscript": TypeSummary(
                    count=2, sigla=["01", "02"], century_range=(7, 8)
                ),
            },
            earliest_century=7,
            provenance_packs=["pack-a"],
        )
        result = derive_minority_metadata(support)
        assert result.attestation_strength == "moderate"

    def test_single_late_witness_is_weak(self):
        """Single witness from 7th century or later should be 'weak'."""
        support = SupportSummary(
            total_count=1,
            by_type={
                "manuscript": TypeSummary(
                    count=1, sigla=["minusc"], century_range=(9, 9)
                ),
            },
            earliest_century=9,
            provenance_packs=["pack-a"],
        )
        result = derive_minority_metadata(support)
        assert result.attestation_strength == "weak"

    def test_single_witness_no_century_is_weak(self):
        """Single witness with no century data should be 'weak'."""
        support = SupportSummary(
            total_count=1,
            by_type={
                "manuscript": TypeSummary(count=1, sigla=["unknown"]),
            },
            earliest_century=None,
            provenance_packs=["pack-a"],
        )
        result = derive_minority_metadata(support)
        assert result.attestation_strength == "weak"

    def test_historical_uptake_not_derived(self):
        """historical_uptake should never be derived, only from pack metadata."""
        support = SupportSummary(
            total_count=5,
            by_type={
                "manuscript": TypeSummary(count=5, sigla=["a", "b", "c", "d", "e"]),
            },
            earliest_century=2,
            provenance_packs=["pack-a"],
        )
        result = derive_minority_metadata(support)
        assert result.historical_uptake is None

    def test_ideological_usage_not_derived(self):
        """ideological_usage should always be empty (not derived)."""
        support = SupportSummary(
            total_count=3,
            by_type={
                "manuscript": TypeSummary(count=3, sigla=["a", "b", "c"]),
            },
            earliest_century=4,
            provenance_packs=["pack-a"],
        )
        result = derive_minority_metadata(support)
        assert result.ideological_usage == []


class TestMinorityMetadataDataclass:
    """Tests for MinorityMetadata dataclass."""

    def test_to_dict(self):
        """to_dict should serialize all fields."""
        meta = MinorityMetadata(
            attestation_strength="moderate",
            historical_uptake="medium",
            ideological_usage=["adoptionist_controversy"],
        )
        d = meta.to_dict()
        assert d["attestation_strength"] == "moderate"
        assert d["historical_uptake"] == "medium"
        assert d["ideological_usage"] == ["adoptionist_controversy"]

    def test_to_dict_with_nones(self):
        """to_dict should handle None values."""
        meta = MinorityMetadata()
        d = meta.to_dict()
        assert d["attestation_strength"] is None
        assert d["historical_uptake"] is None
        assert d["ideological_usage"] == []
