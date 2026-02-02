"""Sprint 9 integration tests: Multi-pack aggregation + true witness support.

Tests verify:
- Support set deduplication correctness
- Multi-pack aggregation merges identical readings
- Dossier shows support summary and evidence class
- Idempotent rebuild doesn't duplicate supports
- Gate not duplicated with multi-pack
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from redletters.variants.models import (
    VariantUnit,
    WitnessReading,
    WitnessType,
    WitnessSupportType,
    WitnessSupport,
    VariantClassification,
    SignificanceLevel,
)
from redletters.variants.store import VariantStore
from redletters.variants.builder import (
    normalize_for_aggregation,
    dedupe_support_set,
    map_witness_type_to_support_type,
)
from redletters.variants.dossier import (
    DossierGenerator,
    SupportSummary,
    TypeSummary,
    determine_evidence_class,
)


# ============================================================================
# Unit Tests: Support Set Deduplication
# ============================================================================


class TestSupportSetDedupe:
    """Unit tests for support set deduplication (Sprint 9: B1)."""

    def test_dedupe_same_siglum_same_pack(self):
        """Same siglum from same pack should yield single entry."""
        supports = [
            WitnessSupport(
                witness_siglum="WH",
                witness_type=WitnessSupportType.EDITION,
                source_pack_id="westcott-hort-john",
                century_range=(19, 19),
            ),
            WitnessSupport(
                witness_siglum="WH",
                witness_type=WitnessSupportType.EDITION,
                source_pack_id="westcott-hort-john",  # Same pack
                century_range=(19, 19),
            ),
        ]

        deduped, warnings = dedupe_support_set(supports)

        assert len(deduped) == 1
        assert deduped[0].witness_siglum == "WH"
        assert len(warnings) == 0

    def test_dedupe_same_siglum_diff_packs(self):
        """Same siglum from different packs should yield both entries with warning."""
        supports = [
            WitnessSupport(
                witness_siglum="WH",
                witness_type=WitnessSupportType.EDITION,
                source_pack_id="westcott-hort-john",
                century_range=(19, 19),
            ),
            WitnessSupport(
                witness_siglum="WH",
                witness_type=WitnessSupportType.EDITION,
                source_pack_id="westcott-hort-mark",  # Different pack
                century_range=(19, 19),
            ),
        ]

        deduped, warnings = dedupe_support_set(supports)

        assert len(deduped) == 2
        assert len(warnings) == 1
        assert "multiple packs" in warnings[0].lower()

    def test_dedupe_different_sigla(self):
        """Different sigla should all be kept."""
        supports = [
            WitnessSupport(
                witness_siglum="WH",
                witness_type=WitnessSupportType.EDITION,
                source_pack_id="pack-a",
            ),
            WitnessSupport(
                witness_siglum="Byz",
                witness_type=WitnessSupportType.TRADITION,
                source_pack_id="pack-b",
            ),
            WitnessSupport(
                witness_siglum="P66",
                witness_type=WitnessSupportType.MANUSCRIPT,
                source_pack_id="pack-c",
            ),
        ]

        deduped, warnings = dedupe_support_set(supports)

        assert len(deduped) == 3
        assert len(warnings) == 0


# ============================================================================
# Unit Tests: Normalization
# ============================================================================


class TestNormalization:
    """Unit tests for aggregation normalization (Sprint 9: B2)."""

    def test_normalize_removes_accents(self):
        """Normalization should remove Greek accents."""
        text_with_accents = "λόγος"
        text_without = "λογος"

        norm1 = normalize_for_aggregation(text_with_accents)
        norm2 = normalize_for_aggregation(text_without)

        assert norm1 == norm2

    def test_normalize_case_insensitive(self):
        """Normalization should be case insensitive."""
        upper = "ΛΟΓΟΣ"
        lower = "λογος"

        norm1 = normalize_for_aggregation(upper)
        norm2 = normalize_for_aggregation(lower)

        assert norm1 == norm2

    def test_normalize_collapses_whitespace(self):
        """Normalization should collapse whitespace."""
        spaced = "εν   αρχη    ην"
        compact = "εν αρχη ην"

        norm1 = normalize_for_aggregation(spaced)
        norm2 = normalize_for_aggregation(compact)

        assert norm1 == norm2

    def test_normalize_removes_punctuation(self):
        """Normalization should remove punctuation."""
        with_punct = "λόγος, καὶ ὁ λόγος."
        without = "λογος και ο λογος"

        normalized = normalize_for_aggregation(with_punct)

        assert "," not in normalized
        assert "." not in normalized


# ============================================================================
# Unit Tests: Witness Type Mapping
# ============================================================================


class TestWitnessTypeMapping:
    """Unit tests for WitnessType to WitnessSupportType mapping."""

    def test_map_edition_sigla(self):
        """Known edition sigla should map to EDITION."""
        assert (
            map_witness_type_to_support_type(WitnessType.VERSION, "WH")
            == WitnessSupportType.EDITION
        )
        assert (
            map_witness_type_to_support_type(WitnessType.VERSION, "SBLGNT")
            == WitnessSupportType.EDITION
        )
        assert (
            map_witness_type_to_support_type(WitnessType.VERSION, "NA28")
            == WitnessSupportType.EDITION
        )

    def test_map_tradition_sigla(self):
        """Known tradition sigla should map to TRADITION."""
        assert (
            map_witness_type_to_support_type(WitnessType.VERSION, "Byz")
            == WitnessSupportType.TRADITION
        )
        assert (
            map_witness_type_to_support_type(WitnessType.MINUSCULE, "f1")
            == WitnessSupportType.TRADITION
        )

    def test_map_papyrus(self):
        """PAPYRUS type should map to MANUSCRIPT."""
        assert (
            map_witness_type_to_support_type(WitnessType.PAPYRUS, "P66")
            == WitnessSupportType.MANUSCRIPT
        )

    def test_map_uncial(self):
        """UNCIAL type should map to MANUSCRIPT."""
        assert (
            map_witness_type_to_support_type(WitnessType.UNCIAL, "01")
            == WitnessSupportType.MANUSCRIPT
        )


# ============================================================================
# Unit Tests: Evidence Class
# ============================================================================


class TestEvidenceClass:
    """Unit tests for evidence class determination (Sprint 9: B3)."""

    def test_evidence_class_edition_only(self):
        """Edition-only support should yield 'edition-level evidence'."""
        summary = SupportSummary(
            total_count=2,
            by_type={"edition": TypeSummary(count=2, sigla=["WH", "NA28"])},
            earliest_century=19,
            provenance_packs=["pack-a"],
        )

        assert determine_evidence_class(summary) == "edition-level evidence"

    def test_evidence_class_manuscript_only(self):
        """Manuscript-only support should yield 'manuscript-level evidence'."""
        summary = SupportSummary(
            total_count=3,
            by_type={"manuscript": TypeSummary(count=3, sigla=["P66", "01", "03"])},
            earliest_century=2,
            provenance_packs=["pack-a"],
        )

        assert determine_evidence_class(summary) == "manuscript-level evidence"

    def test_evidence_class_tradition_only(self):
        """Tradition-only support should yield 'tradition aggregate'."""
        summary = SupportSummary(
            total_count=1,
            by_type={"tradition": TypeSummary(count=1, sigla=["Byz"])},
            earliest_century=9,
            provenance_packs=["pack-a"],
        )

        assert determine_evidence_class(summary) == "tradition aggregate"

    def test_evidence_class_mixed_with_manuscript(self):
        """Mixed support with manuscript should prioritize manuscript."""
        summary = SupportSummary(
            total_count=4,
            by_type={
                "edition": TypeSummary(count=2, sigla=["WH", "NA28"]),
                "manuscript": TypeSummary(count=2, sigla=["P66", "01"]),
            },
            earliest_century=2,
            provenance_packs=["pack-a"],
        )

        assert determine_evidence_class(summary) == "manuscript-level evidence"

    def test_evidence_class_empty(self):
        """Empty support should yield 'no recorded support'."""
        summary = SupportSummary(
            total_count=0,
            by_type={},
            earliest_century=None,
            provenance_packs=[],
        )

        assert determine_evidence_class(summary) == "no recorded support"


# ============================================================================
# Integration Tests: Multi-Pack Aggregation
# ============================================================================


class TestMultiPackAggregation:
    """Integration tests for multi-pack variant aggregation (Sprint 9: B2)."""

    @pytest.fixture
    def db_conn(self, tmp_path: Path):
        """Create a temporary database connection."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        return conn

    @pytest.fixture
    def variant_store(self, db_conn):
        """Create and initialize a variant store."""
        store = VariantStore(db_conn)
        store.init_schema()
        return store

    def test_save_variant_with_support_set(self, variant_store):
        """Variant with support_set should be saved and loaded correctly."""
        support = WitnessSupport(
            witness_siglum="WH",
            witness_type=WitnessSupportType.EDITION,
            source_pack_id="westcott-hort-john",
            century_range=(19, 19),
        )

        reading = WitnessReading(
            surface_text="μονογενὴς θεός",
            witnesses=["WH"],
            witness_types=[WitnessType.VERSION],
            normalized_text="μονογενης θεος",
            support_set=[support],
        )

        variant = VariantUnit(
            ref="John.1.18",
            position=0,
            readings=[reading],
            classification=VariantClassification.SUBSTITUTION,
            significance=SignificanceLevel.MAJOR,
        )

        variant_store.save_variant(variant)

        # Load and verify
        loaded = variant_store.get_variant("John.1.18", 0)
        assert loaded is not None
        assert len(loaded.readings) == 1
        assert len(loaded.readings[0].support_set) == 1
        assert loaded.readings[0].support_set[0].witness_siglum == "WH"
        assert (
            loaded.readings[0].support_set[0].witness_type == WitnessSupportType.EDITION
        )

    def test_add_support_to_existing_reading(self, variant_store):
        """Adding support to existing reading should work idempotently."""
        # Save initial variant
        support1 = WitnessSupport(
            witness_siglum="WH",
            witness_type=WitnessSupportType.EDITION,
            source_pack_id="pack-1",
        )

        reading = WitnessReading(
            surface_text="μονογενὴς θεός",
            normalized_text="μονογενης θεος",
            support_set=[support1],
        )

        variant = VariantUnit(
            ref="John.1.18",
            position=0,
            readings=[reading],
            classification=VariantClassification.SUBSTITUTION,
            significance=SignificanceLevel.MAJOR,
        )

        variant_store.save_variant(variant)

        # Get reading ID
        reading_id = variant_store.get_reading_id_by_normalized(
            "John.1.18", 0, "μονογενης θεος"
        )
        assert reading_id is not None

        # Add another support
        support2 = WitnessSupport(
            witness_siglum="Byz",
            witness_type=WitnessSupportType.TRADITION,
            source_pack_id="pack-2",
        )

        added = variant_store.add_support_to_reading(reading_id, support2)
        assert added is True

        # Try to add same support again (should be idempotent)
        added_again = variant_store.add_support_to_reading(reading_id, support2)
        assert added_again is False  # Already exists

        # Verify count
        count = variant_store.count_support_entries(reading_id)
        assert count == 2

    def test_idempotent_rebuild(self, variant_store):
        """Rebuilding variants should not duplicate support entries."""
        # Save initial variant with support
        support = WitnessSupport(
            witness_siglum="WH",
            witness_type=WitnessSupportType.EDITION,
            source_pack_id="pack-1",
        )

        reading = WitnessReading(
            surface_text="μονογενὴς θεός",
            normalized_text="μονογενης θεος",
            support_set=[support],
        )

        variant = VariantUnit(
            ref="John.1.18",
            position=0,
            readings=[reading],
            classification=VariantClassification.SUBSTITUTION,
            significance=SignificanceLevel.MAJOR,
        )

        variant_store.save_variant(variant)

        # Get initial support count
        reading_id = variant_store.get_reading_id_by_normalized(
            "John.1.18", 0, "μονογενης θεος"
        )
        initial_count = variant_store.count_support_entries(reading_id)

        # Try to add same support again
        added = variant_store.add_support_to_reading(reading_id, support)
        assert added is False

        # Count should be unchanged
        final_count = variant_store.count_support_entries(reading_id)
        assert final_count == initial_count


# ============================================================================
# Integration Tests: Dossier Output
# ============================================================================


class TestDossierOutput:
    """Integration tests for dossier output with support summary (Sprint 9: B3)."""

    @pytest.fixture
    def db_conn(self, tmp_path: Path):
        """Create a temporary database connection."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        return conn

    @pytest.fixture
    def variant_store(self, db_conn):
        """Create and initialize a variant store."""
        store = VariantStore(db_conn)
        store.init_schema()
        return store

    def test_dossier_shows_support_summary(self, variant_store):
        """Dossier should include support_summary for each reading."""
        # Create variant with support_set
        supports = [
            WitnessSupport(
                witness_siglum="WH",
                witness_type=WitnessSupportType.EDITION,
                source_pack_id="westcott-hort-john",
                century_range=(19, 19),
            ),
            WitnessSupport(
                witness_siglum="P66",
                witness_type=WitnessSupportType.MANUSCRIPT,
                source_pack_id="papyri-pack",
                century_range=(2, 2),
            ),
        ]

        reading = WitnessReading(
            surface_text="μονογενὴς θεός",
            normalized_text="μονογενης θεος",
            support_set=supports,
        )

        variant = VariantUnit(
            ref="John.1.18",
            position=0,
            readings=[reading],
            classification=VariantClassification.SUBSTITUTION,
            significance=SignificanceLevel.MAJOR,
        )

        variant_store.save_variant(variant)

        # Generate dossier
        generator = DossierGenerator(variant_store)
        dossier = generator.generate("John.1.18")

        # Verify support summary
        assert len(dossier.variants) == 1
        assert len(dossier.variants[0].readings) == 1

        dr = dossier.variants[0].readings[0]
        assert dr.support_summary is not None
        assert dr.support_summary.total_count == 2
        assert "edition" in dr.support_summary.by_type
        assert "manuscript" in dr.support_summary.by_type
        assert dr.support_summary.earliest_century == 2

    def test_dossier_shows_evidence_class(self, variant_store):
        """Dossier should include evidence_class for each reading."""
        # Create variant with edition-only support
        support = WitnessSupport(
            witness_siglum="WH",
            witness_type=WitnessSupportType.EDITION,
            source_pack_id="westcott-hort-john",
        )

        reading = WitnessReading(
            surface_text="μονογενὴς θεός",
            normalized_text="μονογενης θεος",
            support_set=[support],
        )

        variant = VariantUnit(
            ref="John.1.18",
            position=0,
            readings=[reading],
            classification=VariantClassification.SUBSTITUTION,
            significance=SignificanceLevel.MAJOR,
        )

        variant_store.save_variant(variant)

        # Generate dossier
        generator = DossierGenerator(variant_store)
        dossier = generator.generate("John.1.18")

        # Verify evidence class
        dr = dossier.variants[0].readings[0]
        assert dr.evidence_class == "edition-level evidence"

    def test_dossier_provenance_packs(self, variant_store):
        """Dossier should list provenance packs correctly."""
        # Create variant with multiple pack sources
        supports = [
            WitnessSupport(
                witness_siglum="WH",
                witness_type=WitnessSupportType.EDITION,
                source_pack_id="westcott-hort-john",
            ),
            WitnessSupport(
                witness_siglum="Byz",
                witness_type=WitnessSupportType.TRADITION,
                source_pack_id="byzantine-john",
            ),
        ]

        reading = WitnessReading(
            surface_text="μονογενὴς θεός",
            normalized_text="μονογενης θεος",
            support_set=supports,
        )

        variant = VariantUnit(
            ref="John.1.18",
            position=0,
            readings=[reading],
            classification=VariantClassification.SUBSTITUTION,
            significance=SignificanceLevel.MAJOR,
        )

        variant_store.save_variant(variant)

        # Generate dossier
        generator = DossierGenerator(variant_store)
        dossier = generator.generate("John.1.18")

        # Verify provenance
        dr = dossier.variants[0].readings[0]
        assert "westcott-hort-john" in dr.support_summary.provenance_packs
        assert "byzantine-john" in dr.support_summary.provenance_packs
        assert "westcott-hort-john" in dr.source_packs
        assert "byzantine-john" in dr.source_packs

    def test_dossier_no_epistemic_inflation(self, variant_store):
        """Dossier JSON should not contain epistemic inflation language."""
        # Create variant
        support = WitnessSupport(
            witness_siglum="P66",
            witness_type=WitnessSupportType.MANUSCRIPT,
            source_pack_id="papyri-pack",
            century_range=(2, 2),
        )

        reading = WitnessReading(
            surface_text="μονογενὴς θεός",
            normalized_text="μονογενης θεος",
            support_set=[support],
        )

        variant = VariantUnit(
            ref="John.1.18",
            position=0,
            readings=[reading],
            classification=VariantClassification.SUBSTITUTION,
            significance=SignificanceLevel.MAJOR,
        )

        variant_store.save_variant(variant)

        # Generate dossier
        generator = DossierGenerator(variant_store)
        dossier = generator.generate("John.1.18")

        # Convert to dict and check for epistemic inflation
        dossier_dict = dossier.to_dict()
        dossier_str = str(dossier_dict).lower()

        # These phrases should NOT appear
        forbidden_phrases = [
            "more likely",
            "probably original",
            "weight of evidence",
            "best reading",
            "superior",
            "inferior",
            "corruption",
            "authentic",
        ]

        for phrase in forbidden_phrases:
            assert phrase not in dossier_str, f"Found epistemic inflation: '{phrase}'"


# ============================================================================
# Integration Tests: WitnessReading Methods
# ============================================================================


class TestWitnessReadingMethods:
    """Tests for WitnessReading helper methods (Sprint 9)."""

    def test_get_support_by_type(self):
        """get_support_by_type should group support entries correctly."""
        supports = [
            WitnessSupport(
                witness_siglum="WH",
                witness_type=WitnessSupportType.EDITION,
                source_pack_id="pack-1",
            ),
            WitnessSupport(
                witness_siglum="NA28",
                witness_type=WitnessSupportType.EDITION,
                source_pack_id="pack-2",
            ),
            WitnessSupport(
                witness_siglum="P66",
                witness_type=WitnessSupportType.MANUSCRIPT,
                source_pack_id="pack-3",
            ),
        ]

        reading = WitnessReading(
            surface_text="test",
            support_set=supports,
        )

        by_type = reading.get_support_by_type()

        assert WitnessSupportType.EDITION in by_type
        assert len(by_type[WitnessSupportType.EDITION]) == 2
        assert WitnessSupportType.MANUSCRIPT in by_type
        assert len(by_type[WitnessSupportType.MANUSCRIPT]) == 1

    def test_get_source_packs(self):
        """get_source_packs should return unique pack IDs."""
        supports = [
            WitnessSupport(
                witness_siglum="WH",
                witness_type=WitnessSupportType.EDITION,
                source_pack_id="pack-1",
            ),
            WitnessSupport(
                witness_siglum="NA28",
                witness_type=WitnessSupportType.EDITION,
                source_pack_id="pack-1",  # Same pack
            ),
            WitnessSupport(
                witness_siglum="P66",
                witness_type=WitnessSupportType.MANUSCRIPT,
                source_pack_id="pack-2",
            ),
        ]

        reading = WitnessReading(
            surface_text="test",
            source_pack_id="pack-3",  # Legacy field
            support_set=supports,
        )

        packs = reading.get_source_packs()

        assert len(packs) == 3
        assert "pack-1" in packs
        assert "pack-2" in packs
        assert "pack-3" in packs

    def test_earliest_century_from_support_set(self):
        """earliest_century should consider support_set entries."""
        supports = [
            WitnessSupport(
                witness_siglum="WH",
                witness_type=WitnessSupportType.EDITION,
                source_pack_id="pack-1",
                century_range=(19, 19),
            ),
            WitnessSupport(
                witness_siglum="P66",
                witness_type=WitnessSupportType.MANUSCRIPT,
                source_pack_id="pack-2",
                century_range=(2, 3),  # Earlier
            ),
        ]

        reading = WitnessReading(
            surface_text="test",
            date_range=(4, 5),  # Legacy field
            support_set=supports,
        )

        assert reading.earliest_century == 2
