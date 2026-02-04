"""Tests for incentive tags derivation (v0.9.0).

Tests conservative derivation of incentive logic tags.
"""

from redletters.variants.dossier import (
    derive_incentive_tags,
    SupportSummary,
)
from redletters.variants.models import WitnessReading


class TestIncentiveTagsDerivation:
    """Tests for derive_incentive_tags function."""

    def test_single_reading_no_tags(self):
        """With only one reading, no tags should be generated."""
        readings = [
            WitnessReading(surface_text="τὸν θεόν"),
        ]
        summaries = [
            SupportSummary(
                total_count=1, by_type={}, earliest_century=3, provenance_packs=[]
            ),
        ]
        tags = derive_incentive_tags(readings, summaries)
        assert tags == []

    def test_brevity_preference_present_with_length_difference(self):
        """Readings differing by 2+ words should tag brevity_preference_present."""
        readings = [
            WitnessReading(surface_text="ὁ θεὸς μονογενὴς"),  # 3 words
            WitnessReading(
                surface_text="ὁ μονογενὴς υἱός τοῦ θεοῦ καὶ πατρός"
            ),  # 7 words
        ]
        summaries = [
            SupportSummary(
                total_count=1, by_type={}, earliest_century=3, provenance_packs=[]
            ),
            SupportSummary(
                total_count=1, by_type={}, earliest_century=4, provenance_packs=[]
            ),
        ]
        tags = derive_incentive_tags(readings, summaries)
        assert "brevity_preference_present" in tags

    def test_no_brevity_tag_for_similar_length(self):
        """Readings differing by less than 2 words should not tag brevity."""
        readings = [
            WitnessReading(surface_text="τὸν θεόν"),  # 2 words
            WitnessReading(surface_text="τὸν υἱόν"),  # 2 words
        ]
        summaries = [
            SupportSummary(
                total_count=1, by_type={}, earliest_century=3, provenance_packs=[]
            ),
            SupportSummary(
                total_count=1, by_type={}, earliest_century=3, provenance_packs=[]
            ),
        ]
        tags = derive_incentive_tags(readings, summaries)
        assert "brevity_preference_present" not in tags

    def test_age_bias_risk_with_century_spread(self):
        """Readings with 2+ century spread should tag age_bias_risk."""
        readings = [
            WitnessReading(surface_text="θεὸν"),
            WitnessReading(surface_text="υἱόν"),
        ]
        summaries = [
            SupportSummary(
                total_count=1, by_type={}, earliest_century=2, provenance_packs=[]
            ),
            SupportSummary(
                total_count=1, by_type={}, earliest_century=5, provenance_packs=[]
            ),
        ]
        tags = derive_incentive_tags(readings, summaries)
        assert "age_bias_risk" in tags

    def test_no_age_bias_tag_for_similar_centuries(self):
        """Readings with less than 2 century spread should not tag age bias."""
        readings = [
            WitnessReading(surface_text="θεὸν"),
            WitnessReading(surface_text="υἱόν"),
        ]
        summaries = [
            SupportSummary(
                total_count=1, by_type={}, earliest_century=3, provenance_packs=[]
            ),
            SupportSummary(
                total_count=1, by_type={}, earliest_century=4, provenance_packs=[]
            ),
        ]
        tags = derive_incentive_tags(readings, summaries)
        assert "age_bias_risk" not in tags

    def test_no_age_bias_tag_with_missing_century_data(self):
        """With missing century data, age_bias_risk should not be tagged."""
        readings = [
            WitnessReading(surface_text="θεὸν"),
            WitnessReading(surface_text="υἱόν"),
        ]
        summaries = [
            SupportSummary(
                total_count=1, by_type={}, earliest_century=2, provenance_packs=[]
            ),
            SupportSummary(
                total_count=1, by_type={}, earliest_century=None, provenance_packs=[]
            ),
        ]
        tags = derive_incentive_tags(readings, summaries)
        # Only one century known, cannot compute spread
        assert "age_bias_risk" not in tags

    def test_both_tags_can_be_present(self):
        """Both brevity and age bias tags can co-exist."""
        readings = [
            WitnessReading(surface_text="ὁ θεὸς"),  # 2 words
            WitnessReading(surface_text="ὁ μονογενὴς υἱὸς τοῦ θεοῦ"),  # 5 words
        ]
        summaries = [
            SupportSummary(
                total_count=1, by_type={}, earliest_century=2, provenance_packs=[]
            ),
            SupportSummary(
                total_count=1, by_type={}, earliest_century=5, provenance_packs=[]
            ),
        ]
        tags = derive_incentive_tags(readings, summaries)
        assert "brevity_preference_present" in tags
        assert "age_bias_risk" in tags

    def test_empty_readings_list_no_tags(self):
        """Empty readings list should return empty tags."""
        tags = derive_incentive_tags([], [])
        assert tags == []

    def test_deterministic_output(self):
        """Same inputs should produce same output."""
        readings = [
            WitnessReading(surface_text="ὁ θεὸς μονογενὴς"),
            WitnessReading(surface_text="ὁ υἱός"),
        ]
        summaries = [
            SupportSummary(
                total_count=1, by_type={}, earliest_century=2, provenance_packs=[]
            ),
            SupportSummary(
                total_count=1, by_type={}, earliest_century=5, provenance_packs=[]
            ),
        ]
        tags1 = derive_incentive_tags(readings, summaries)
        tags2 = derive_incentive_tags(readings, summaries)
        assert tags1 == tags2


class TestIncentiveTagsOnDossierReading:
    """Tests for incentive_tags on DossierReading."""

    def test_dossier_reading_has_incentive_tags_field(self):
        """DossierReading should have incentive_tags field."""
        from redletters.variants.dossier import DossierReading, WitnessSummary

        reading = DossierReading(
            index=0,
            text="θεὸν",
            is_spine=True,
            witnesses=[],
            witness_summary=WitnessSummary(),
            source_packs=[],
            incentive_tags=["brevity_preference_present"],
        )
        assert reading.incentive_tags == ["brevity_preference_present"]

    def test_dossier_reading_to_dict_includes_tags(self):
        """to_dict should include incentive_tags."""
        from redletters.variants.dossier import DossierReading, WitnessSummary

        reading = DossierReading(
            index=0,
            text="θεὸν",
            is_spine=True,
            witnesses=[],
            witness_summary=WitnessSummary(),
            source_packs=[],
            incentive_tags=["age_bias_risk"],
        )
        d = reading.to_dict()
        assert d["incentive_tags"] == ["age_bias_risk"]
