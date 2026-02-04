"""Tests for PackCoverage (v0.8.0).

Tests the PackCoverage dataclass and coverage_summary in Dossier.
"""

from __future__ import annotations

from redletters.variants.dossier import (
    PackCoverage,
    Dossier,
    DossierSpine,
    DossierProvenance,
)


class TestPackCoverageDataclass:
    """Test PackCoverage dataclass."""

    def test_to_dict_includes_all_fields(self):
        """to_dict() includes all fields."""
        pc = PackCoverage(
            pack_id="test-pack",
            covers_scope=True,
            reason="has_readings",
        )
        d = pc.to_dict()
        assert d["pack_id"] == "test-pack"
        assert d["covers_scope"] is True
        assert d["reason"] == "has_readings"

    def test_to_dict_with_false_covers_scope(self):
        """to_dict() works with false covers_scope."""
        pc = PackCoverage(
            pack_id="empty-pack",
            covers_scope=False,
            reason="no_readings_in_scope",
        )
        d = pc.to_dict()
        assert d["covers_scope"] is False
        assert d["reason"] == "no_readings_in_scope"

    def test_reason_has_readings(self):
        """Reason 'has_readings' indicates pack has data."""
        pc = PackCoverage(
            pack_id="pack-a",
            covers_scope=True,
            reason="has_readings",
        )
        assert pc.covers_scope is True
        assert pc.reason == "has_readings"

    def test_reason_no_readings_in_scope(self):
        """Reason 'no_readings_in_scope' indicates pack is in scope but empty."""
        pc = PackCoverage(
            pack_id="pack-b",
            covers_scope=False,
            reason="no_readings_in_scope",
        )
        assert pc.covers_scope is False
        assert pc.reason == "no_readings_in_scope"


class TestDossierWithCoverageSummary:
    """Test Dossier integration with coverage_summary."""

    def _make_minimal_dossier(
        self, coverage_summary: list[PackCoverage] | None = None
    ) -> Dossier:
        """Create minimal Dossier for testing."""
        return Dossier(
            reference="John.1.18",
            scope="verse",
            generated_at="2024-01-01T00:00:00Z",
            spine=DossierSpine(source_id="test-spine", text="test"),
            variants=[],
            provenance=DossierProvenance(
                spine_source="test-spine",
                comparative_packs=[],
                build_timestamp="2024-01-01T00:00:00Z",
            ),
            coverage_summary=coverage_summary or [],
        )

    def test_to_dict_without_coverage_summary(self):
        """to_dict() works without coverage_summary."""
        d = self._make_minimal_dossier(coverage_summary=[])
        result = d.to_dict()
        # Empty list is not included
        assert "coverage_summary" not in result

    def test_to_dict_with_coverage_summary(self):
        """to_dict() includes coverage_summary when present."""
        coverage = [
            PackCoverage(pack_id="pack-a", covers_scope=True, reason="has_readings"),
            PackCoverage(
                pack_id="pack-b", covers_scope=False, reason="no_readings_in_scope"
            ),
        ]
        d = self._make_minimal_dossier(coverage_summary=coverage)
        result = d.to_dict()
        assert "coverage_summary" in result
        assert len(result["coverage_summary"]) == 2
        assert result["coverage_summary"][0]["pack_id"] == "pack-a"
        assert result["coverage_summary"][0]["covers_scope"] is True
        assert result["coverage_summary"][1]["pack_id"] == "pack-b"
        assert result["coverage_summary"][1]["covers_scope"] is False


class TestCoverageSummaryAbsenceAsData:
    """Test that coverage_summary captures absence as meaningful data."""

    def test_absence_is_recorded(self):
        """Packs without readings in scope are recorded."""
        pc = PackCoverage(
            pack_id="empty-pack",
            covers_scope=False,
            reason="no_readings_in_scope",
        )
        # Absence is data: we know the pack was considered but had nothing
        assert pc.covers_scope is False
        # The reason explains WHY it's absent
        assert pc.reason == "no_readings_in_scope"

    def test_presence_is_recorded(self):
        """Packs with readings are recorded."""
        pc = PackCoverage(
            pack_id="full-pack",
            covers_scope=True,
            reason="has_readings",
        )
        assert pc.covers_scope is True

    def test_coverage_summary_multiple_packs(self):
        """Coverage summary can track multiple packs."""
        coverage = [
            PackCoverage(pack_id="pack-1", covers_scope=True, reason="has_readings"),
            PackCoverage(pack_id="pack-2", covers_scope=True, reason="has_readings"),
            PackCoverage(
                pack_id="pack-3", covers_scope=False, reason="no_readings_in_scope"
            ),
        ]
        # 2 packs have data, 1 doesn't
        packs_with_data = [c for c in coverage if c.covers_scope]
        packs_without_data = [c for c in coverage if not c.covers_scope]
        assert len(packs_with_data) == 2
        assert len(packs_without_data) == 1
