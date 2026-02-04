"""Tests for claims analyzer (v0.8.0).

Tests the ClaimsAnalyzer for reversible theology.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

import pytest

from redletters.analysis import ClaimsAnalyzer, ClaimAnalysis, Claim
from redletters.analysis.claims_analyzer import DependencyAnalysis
from redletters.variants.store import VariantStore
from redletters.variants.models import (
    VariantUnit,
    VariantClassification,
    SignificanceLevel,
    WitnessReading,
)
from redletters.gates.state import AcknowledgementStore, VariantAcknowledgement


@pytest.fixture
def in_memory_db():
    """Create an in-memory database for testing."""
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def variant_store(in_memory_db):
    """Create a variant store with schema initialized."""
    store = VariantStore(in_memory_db)
    store.init_schema()
    return store


@pytest.fixture
def ack_store(in_memory_db):
    """Create an acknowledgement store with schema initialized."""
    store = AcknowledgementStore(in_memory_db)
    store.init_schema()
    return store


class TestClaimDataclass:
    """Test Claim dataclass."""

    def test_claim_fields(self):
        """Claim stores all required fields."""
        claim = Claim(
            label="test-claim",
            text="Test claim text",
            dependencies=["John.1.18", "John.3.16"],
        )
        assert claim.label == "test-claim"
        assert claim.text == "Test claim text"
        assert claim.dependencies == ["John.1.18", "John.3.16"]

    def test_claim_default_dependencies(self):
        """Claim defaults to empty dependencies list."""
        claim = Claim(label="test", text="Test")
        assert claim.dependencies == []


class TestDependencyAnalysis:
    """Test DependencyAnalysis dataclass."""

    def test_to_dict_includes_all_fields(self):
        """to_dict() includes all fields."""
        analysis = DependencyAnalysis(
            reference="John.1.18",
            has_low_confidence_tokens=True,
            low_confidence_count=2,
            has_pending_gates=True,
            pending_gate_count=1,
            has_significant_variants=True,
            significant_variant_count=1,
            notes=["test note"],
        )
        d = analysis.to_dict()
        assert d["reference"] == "John.1.18"
        assert d["has_low_confidence_tokens"] is True
        assert d["low_confidence_count"] == 2
        assert d["has_pending_gates"] is True
        assert d["pending_gate_count"] == 1
        assert d["has_significant_variants"] is True
        assert d["significant_variant_count"] == 1
        assert d["notes"] == ["test note"]


class TestClaimAnalysis:
    """Test ClaimAnalysis dataclass."""

    def test_to_dict_includes_all_fields(self):
        """to_dict() includes all fields."""
        analysis = ClaimAnalysis(
            label="test",
            text="Test text",
            dependencies_analyzed=2,
            has_uncertainty=True,
            uncertainty_score="high",
            dependency_analyses=[],
            summary_notes=["Note 1"],
        )
        d = analysis.to_dict()
        assert d["label"] == "test"
        assert d["text"] == "Test text"
        assert d["dependencies_analyzed"] == 2
        assert d["has_uncertainty"] is True
        assert d["uncertainty_score"] == "high"
        assert d["dependency_analyses"] == []
        assert d["summary_notes"] == ["Note 1"]


class TestClaimsAnalyzerNoDependencies:
    """Test ClaimsAnalyzer with claims that have no dependencies."""

    def test_claim_no_dependencies_no_uncertainty(self, in_memory_db, variant_store):
        """Claim with no dependencies has no uncertainty."""
        analyzer = ClaimsAnalyzer(in_memory_db, variant_store)
        claim = Claim(label="test", text="Test claim", dependencies=[])
        result = analyzer.analyze_claim(claim)

        assert result.dependencies_analyzed == 0
        assert result.has_uncertainty is False
        assert result.uncertainty_score == "none"


class TestClaimsAnalyzerNoVariants:
    """Test ClaimsAnalyzer with no variants in the store."""

    def test_claim_no_variants_no_uncertainty(self, in_memory_db, variant_store):
        """Claim with dependencies but no variants has no uncertainty."""
        analyzer = ClaimsAnalyzer(in_memory_db, variant_store)
        claim = Claim(
            label="test",
            text="Test claim",
            dependencies=["John.1.18"],
        )
        result = analyzer.analyze_claim(claim)

        assert result.dependencies_analyzed == 1
        assert result.has_uncertainty is False
        assert result.uncertainty_score == "none"
        assert len(result.dependency_analyses) == 1
        assert result.dependency_analyses[0].has_significant_variants is False


class TestClaimsAnalyzerWithVariants:
    """Test ClaimsAnalyzer with variants in the store."""

    def _add_variant(
        self,
        store: VariantStore,
        ref: str,
        significance: SignificanceLevel = SignificanceLevel.SIGNIFICANT,
    ):
        """Helper to add a variant to the store."""
        variant = VariantUnit(
            ref=ref,
            position=0,
            readings=[
                WitnessReading(surface_text="reading1"),
                WitnessReading(surface_text="reading2"),
            ],
            sblgnt_reading_index=0,
            classification=VariantClassification.SUBSTITUTION,
            significance=significance,
        )
        store.save_variant(variant)

    def test_significant_variant_creates_uncertainty(self, in_memory_db, variant_store):
        """Significant variant in dependency creates uncertainty."""
        self._add_variant(variant_store, "John.1.18", SignificanceLevel.SIGNIFICANT)

        analyzer = ClaimsAnalyzer(in_memory_db, variant_store)
        claim = Claim(
            label="test",
            text="Test claim",
            dependencies=["John.1.18"],
        )
        result = analyzer.analyze_claim(claim)

        assert result.has_uncertainty is True
        assert result.uncertainty_score == "high"  # Pending gate
        assert result.dependency_analyses[0].has_significant_variants is True
        assert result.dependency_analyses[0].significant_variant_count == 1

    def test_trivial_variant_no_uncertainty(self, in_memory_db, variant_store):
        """Trivial variant does not create uncertainty."""
        self._add_variant(variant_store, "John.1.18", SignificanceLevel.TRIVIAL)

        analyzer = ClaimsAnalyzer(in_memory_db, variant_store)
        claim = Claim(
            label="test",
            text="Test claim",
            dependencies=["John.1.18"],
        )
        result = analyzer.analyze_claim(claim)

        assert result.has_uncertainty is False
        assert result.uncertainty_score == "none"

    def test_minor_variant_no_uncertainty(self, in_memory_db, variant_store):
        """Minor variant does not create uncertainty."""
        self._add_variant(variant_store, "John.1.18", SignificanceLevel.MINOR)

        analyzer = ClaimsAnalyzer(in_memory_db, variant_store)
        claim = Claim(
            label="test",
            text="Test claim",
            dependencies=["John.1.18"],
        )
        result = analyzer.analyze_claim(claim)

        assert result.has_uncertainty is False
        assert result.uncertainty_score == "none"


class TestClaimsAnalyzerWithAcknowledgements:
    """Test ClaimsAnalyzer with acknowledged variants."""

    def _add_variant(self, store: VariantStore, ref: str):
        """Helper to add a significant variant."""
        variant = VariantUnit(
            ref=ref,
            position=0,
            readings=[
                WitnessReading(surface_text="reading1"),
                WitnessReading(surface_text="reading2"),
            ],
            sblgnt_reading_index=0,
            classification=VariantClassification.SUBSTITUTION,
            significance=SignificanceLevel.SIGNIFICANT,
        )
        store.save_variant(variant)

    def _acknowledge(self, store: AcknowledgementStore, ref: str, session_id: str):
        """Helper to acknowledge a variant."""
        ack = VariantAcknowledgement(
            ref=ref,
            reading_chosen=0,
            timestamp=datetime.now(),
            context="test",
            session_id=session_id,
        )
        store.persist_variant_ack(ack)

    def test_acknowledged_variant_medium_uncertainty(
        self, in_memory_db, variant_store, ack_store
    ):
        """Acknowledged variant still has medium uncertainty (variants exist)."""
        self._add_variant(variant_store, "John.1.18")
        self._acknowledge(ack_store, "John.1.18", "test-session")

        analyzer = ClaimsAnalyzer(in_memory_db, variant_store)
        claim = Claim(
            label="test",
            text="Test claim",
            dependencies=["John.1.18"],
        )
        result = analyzer.analyze_claim(claim, session_id="test-session")

        # No pending gates, but variants exist
        assert result.has_uncertainty is True
        assert result.uncertainty_score == "medium"
        assert result.dependency_analyses[0].has_pending_gates is False
        assert result.dependency_analyses[0].has_significant_variants is True

    def test_different_session_high_uncertainty(
        self, in_memory_db, variant_store, ack_store
    ):
        """Variant acknowledged in different session still causes high uncertainty."""
        self._add_variant(variant_store, "John.1.18")
        self._acknowledge(ack_store, "John.1.18", "other-session")

        analyzer = ClaimsAnalyzer(in_memory_db, variant_store)
        claim = Claim(
            label="test",
            text="Test claim",
            dependencies=["John.1.18"],
        )
        result = analyzer.analyze_claim(claim, session_id="test-session")

        # Pending gate because different session
        assert result.uncertainty_score == "high"
        assert result.dependency_analyses[0].has_pending_gates is True


class TestClaimsAnalyzerMultipleDependencies:
    """Test ClaimsAnalyzer with multiple dependencies."""

    def _add_variant(
        self,
        store: VariantStore,
        ref: str,
        significance: SignificanceLevel = SignificanceLevel.SIGNIFICANT,
    ):
        """Helper to add a variant."""
        variant = VariantUnit(
            ref=ref,
            position=0,
            readings=[
                WitnessReading(surface_text="reading1"),
                WitnessReading(surface_text="reading2"),
            ],
            sblgnt_reading_index=0,
            classification=VariantClassification.SUBSTITUTION,
            significance=significance,
        )
        store.save_variant(variant)

    def test_multiple_dependencies_aggregates_uncertainty(
        self, in_memory_db, variant_store
    ):
        """Multiple dependencies aggregate uncertainty."""
        self._add_variant(variant_store, "John.1.18", SignificanceLevel.SIGNIFICANT)
        self._add_variant(variant_store, "John.3.16", SignificanceLevel.MAJOR)

        analyzer = ClaimsAnalyzer(in_memory_db, variant_store)
        claim = Claim(
            label="test",
            text="Test claim",
            dependencies=["John.1.18", "John.3.16"],
        )
        result = analyzer.analyze_claim(claim)

        assert result.dependencies_analyzed == 2
        assert result.has_uncertainty is True
        # 2 pending gates total
        total_pending = sum(d.pending_gate_count for d in result.dependency_analyses)
        assert total_pending == 2

    def test_mixed_significance_dependencies(self, in_memory_db, variant_store):
        """Mixed significance dependencies are analyzed correctly."""
        self._add_variant(variant_store, "John.1.18", SignificanceLevel.SIGNIFICANT)
        self._add_variant(variant_store, "John.3.16", SignificanceLevel.TRIVIAL)

        analyzer = ClaimsAnalyzer(in_memory_db, variant_store)
        claim = Claim(
            label="test",
            text="Test claim",
            dependencies=["John.1.18", "John.3.16"],
        )
        result = analyzer.analyze_claim(claim)

        assert result.dependencies_analyzed == 2
        # Only John.1.18 has significant variant
        assert result.dependency_analyses[0].has_significant_variants is True
        assert result.dependency_analyses[1].has_significant_variants is False


class TestClaimsAnalyzerMultipleClaims:
    """Test ClaimsAnalyzer with multiple claims."""

    def test_analyze_claims_returns_list(self, in_memory_db, variant_store):
        """analyze_claims() returns list of results."""
        analyzer = ClaimsAnalyzer(in_memory_db, variant_store)
        claims = [
            Claim(label="claim1", text="First claim", dependencies=["John.1.18"]),
            Claim(label="claim2", text="Second claim", dependencies=["John.3.16"]),
        ]
        results = analyzer.analyze_claims(claims)

        assert len(results) == 2
        assert results[0].label == "claim1"
        assert results[1].label == "claim2"


class TestClaimsAnalyzerFromDict:
    """Test ClaimsAnalyzer.analyze_from_dict()."""

    def test_analyze_from_dict_parses_claims(self, in_memory_db, variant_store):
        """analyze_from_dict() parses claims from dictionary."""
        data = {
            "claims": [
                {
                    "label": "test-claim",
                    "text": "Test claim text",
                    "dependencies": ["John.1.18"],
                }
            ]
        }

        analyzer = ClaimsAnalyzer(in_memory_db, variant_store)
        results = analyzer.analyze_from_dict(data)

        assert len(results) == 1
        assert results[0].label == "test-claim"
        assert results[0].text == "Test claim text"

    def test_analyze_from_dict_empty_claims(self, in_memory_db, variant_store):
        """analyze_from_dict() handles empty claims list."""
        data = {"claims": []}

        analyzer = ClaimsAnalyzer(in_memory_db, variant_store)
        results = analyzer.analyze_from_dict(data)

        assert results == []

    def test_analyze_from_dict_missing_fields(self, in_memory_db, variant_store):
        """analyze_from_dict() handles missing optional fields."""
        data = {
            "claims": [
                {"label": "test"}  # Missing text and dependencies
            ]
        }

        analyzer = ClaimsAnalyzer(in_memory_db, variant_store)
        results = analyzer.analyze_from_dict(data)

        assert len(results) == 1
        assert results[0].label == "test"
        assert results[0].text == ""
        assert results[0].dependencies_analyzed == 0


class TestSummaryNotes:
    """Test summary notes generation."""

    def _add_variant(self, store: VariantStore, ref: str):
        """Helper to add a significant variant."""
        variant = VariantUnit(
            ref=ref,
            position=0,
            readings=[
                WitnessReading(surface_text="reading1"),
                WitnessReading(surface_text="reading2"),
            ],
            sblgnt_reading_index=0,
            classification=VariantClassification.SUBSTITUTION,
            significance=SignificanceLevel.SIGNIFICANT,
        )
        store.save_variant(variant)

    def test_summary_includes_pending_gates(self, in_memory_db, variant_store):
        """Summary includes note about pending gates."""
        self._add_variant(variant_store, "John.1.18")

        analyzer = ClaimsAnalyzer(in_memory_db, variant_store)
        claim = Claim(
            label="test",
            text="Test claim",
            dependencies=["John.1.18"],
        )
        result = analyzer.analyze_claim(claim)

        assert any("pending gate" in note for note in result.summary_notes)

    def test_summary_no_uncertainty(self, in_memory_db, variant_store):
        """Summary indicates when no uncertainty found."""
        analyzer = ClaimsAnalyzer(in_memory_db, variant_store)
        claim = Claim(
            label="test",
            text="Test claim",
            dependencies=["John.1.18"],
        )
        result = analyzer.analyze_claim(claim)

        assert any("No significant" in note for note in result.summary_notes)
