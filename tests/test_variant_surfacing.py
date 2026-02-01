"""Tests for variant surfacing.

Tests ADR-008 variant storage and display.
"""

import sqlite3
import pytest

from redletters.variants.models import (
    VariantUnit,
    WitnessReading,
    WitnessType,
    VariantClassification,
    SignificanceLevel,
)
from redletters.variants.store import VariantStore


@pytest.fixture
def in_memory_db():
    """Create in-memory SQLite database."""
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def variant_store(in_memory_db):
    """Create variant store with initialized schema."""
    store = VariantStore(in_memory_db)
    store.init_schema()
    return store


@pytest.fixture
def john_1_18_variant():
    """Create sample variant for John 1:18 (monogenes theos vs monogenes huios)."""
    return VariantUnit(
        ref="John.1.18",
        position=3,
        readings=[
            WitnessReading(
                surface_text="μονογενὴς θεός",
                witnesses=["P66", "P75", "א", "B", "C*"],
                witness_types=[
                    WitnessType.PAPYRUS,
                    WitnessType.PAPYRUS,
                    WitnessType.UNCIAL,
                    WitnessType.UNCIAL,
                    WitnessType.UNCIAL,
                ],
                date_range=(2, 4),
                notes="Alexandrian witnesses",
            ),
            WitnessReading(
                surface_text="ὁ μονογενὴς υἱός",
                witnesses=["A", "C³", "Θ", "Ψ", "f¹", "f¹³", "33", "Byz"],
                witness_types=[
                    WitnessType.UNCIAL,
                    WitnessType.UNCIAL,
                    WitnessType.UNCIAL,
                    WitnessType.UNCIAL,
                    WitnessType.MINUSCULE,
                    WitnessType.MINUSCULE,
                    WitnessType.MINUSCULE,
                    WitnessType.MINUSCULE,
                ],
                date_range=(5, 9),
                notes="Byzantine tradition",
            ),
        ],
        sblgnt_reading_index=0,  # SBLGNT follows Alexandrian
        classification=VariantClassification.SUBSTITUTION,
        significance=SignificanceLevel.MAJOR,
        notes="Significant christological variant",
    )


class TestVariantModels:
    """Tests for variant data models."""

    def test_create_witness_reading(self):
        """Should create witness reading with properties."""
        reading = WitnessReading(
            surface_text="μονογενὴς θεός",
            witnesses=["P66", "P75", "א", "B"],
            witness_types=[
                WitnessType.PAPYRUS,
                WitnessType.PAPYRUS,
                WitnessType.UNCIAL,
                WitnessType.UNCIAL,
            ],
            date_range=(2, 4),
        )

        assert reading.has_papyri
        assert reading.has_primary_uncials
        assert reading.earliest_century == 2
        assert "P66" in reading.witness_summary

    def test_create_variant_unit(self, john_1_18_variant):
        """Should create variant unit with readings."""
        variant = john_1_18_variant

        assert variant.ref == "John.1.18"
        assert variant.reading_count == 2
        assert variant.sblgnt_reading.surface_text == "μονογενὴς θεός"
        assert variant.is_significant
        assert variant.requires_acknowledgement

    def test_get_non_sblgnt_readings(self, john_1_18_variant):
        """Should return non-SBLGNT readings."""
        variant = john_1_18_variant
        non_sblgnt = variant.get_non_sblgnt_readings()

        assert len(non_sblgnt) == 1
        idx, reading = non_sblgnt[0]
        assert idx == 1
        assert "υἱός" in reading.surface_text

    def test_variant_serialization(self, john_1_18_variant):
        """Should serialize to dict."""
        d = john_1_18_variant.to_dict()

        assert d["ref"] == "John.1.18"
        assert len(d["readings"]) == 2
        assert d["significance"] == "major"
        assert d["requires_acknowledgement"] is True

    def test_variant_deserialization(self, john_1_18_variant):
        """Should deserialize from dict."""
        d = john_1_18_variant.to_dict()
        restored = VariantUnit.from_dict(d)

        assert restored.ref == john_1_18_variant.ref
        assert restored.reading_count == john_1_18_variant.reading_count
        assert restored.significance == john_1_18_variant.significance


class TestVariantStore:
    """Tests for variant persistence."""

    def test_save_and_retrieve_variant(self, variant_store, john_1_18_variant):
        """Should save and retrieve variant."""
        variant_id = variant_store.save_variant(john_1_18_variant)

        assert variant_id > 0

        retrieved = variant_store.get_variant("John.1.18", 3)

        assert retrieved is not None
        assert retrieved.ref == "John.1.18"
        assert retrieved.reading_count == 2

    def test_get_variants_for_verse(self, variant_store, john_1_18_variant):
        """Should get all variants in a verse."""
        # Save variant
        variant_store.save_variant(john_1_18_variant)

        # Add another at different position
        variant2 = VariantUnit(
            ref="John.1.18",
            position=5,
            readings=[
                WitnessReading(
                    surface_text="τοῦ πατρός",
                    witnesses=["P66"],
                    witness_types=[WitnessType.PAPYRUS],
                ),
            ],
            classification=VariantClassification.SPELLING,
            significance=SignificanceLevel.TRIVIAL,
        )
        variant_store.save_variant(variant2)

        variants = variant_store.get_variants_for_verse("John.1.18")

        assert len(variants) == 2
        assert variants[0].position < variants[1].position

    def test_get_significant_variants(self, variant_store, john_1_18_variant):
        """Should filter by significance level."""
        variant_store.save_variant(john_1_18_variant)

        # Add trivial variant
        trivial = VariantUnit(
            ref="John.1.19",
            position=1,
            readings=[
                WitnessReading(
                    surface_text="καί",
                    witnesses=["P66"],
                    witness_types=[WitnessType.PAPYRUS],
                ),
            ],
            classification=VariantClassification.SPELLING,
            significance=SignificanceLevel.TRIVIAL,
        )
        variant_store.save_variant(trivial)

        significant = variant_store.get_significant_variants()

        assert len(significant) == 1
        assert significant[0].ref == "John.1.18"

    def test_has_variant_check(self, variant_store, john_1_18_variant):
        """Should check for variant existence."""
        assert not variant_store.has_variant("John.1.18", 3)

        variant_store.save_variant(john_1_18_variant)

        assert variant_store.has_variant("John.1.18", 3)
        assert not variant_store.has_variant("John.1.18", 99)

    def test_has_significant_variant_check(self, variant_store, john_1_18_variant):
        """Should check for significant variant in verse."""
        assert not variant_store.has_significant_variant("John.1.18")

        variant_store.save_variant(john_1_18_variant)

        assert variant_store.has_significant_variant("John.1.18")

    def test_count_variants(self, variant_store, john_1_18_variant):
        """Should count variants."""
        assert variant_store.count_variants() == 0

        variant_store.save_variant(john_1_18_variant)

        assert variant_store.count_variants() == 1
        assert variant_store.count_variants(SignificanceLevel.MAJOR) == 1
        assert variant_store.count_variants(SignificanceLevel.TRIVIAL) == 0

    def test_delete_variant(self, variant_store, john_1_18_variant):
        """Should delete variant."""
        variant_store.save_variant(john_1_18_variant)
        assert variant_store.has_variant("John.1.18", 3)

        deleted = variant_store.delete_variant("John.1.18", 3)

        assert deleted
        assert not variant_store.has_variant("John.1.18", 3)

    def test_update_existing_variant(self, variant_store, john_1_18_variant):
        """Should update existing variant on conflict."""
        variant_store.save_variant(john_1_18_variant)

        # Modify and save again
        john_1_18_variant.notes = "Updated notes"
        variant_store.save_variant(john_1_18_variant)

        retrieved = variant_store.get_variant("John.1.18", 3)
        assert retrieved.notes == "Updated notes"

    def test_fk_cascade_deletes_children(self, in_memory_db, john_1_18_variant):
        """FK cascade should delete readings/witnesses when variant deleted.

        Receipt-grade test: verify SQLite FK enforcement actually works.
        Prevents 'works on my laptop' DB drift.

        Note: Counts only rows tied to this specific variant_unit_id,
        not table-wide counts. This keeps the test deterministic even
        if fixture scope changes or other tests share the DB.
        """
        store = VariantStore(in_memory_db)
        store.init_schema()

        # Save variant with readings and witnesses
        variant_id = store.save_variant(john_1_18_variant)

        # Verify child rows exist FOR THIS VARIANT (isolated query)
        readings_before = in_memory_db.execute(
            "SELECT COUNT(*) FROM witness_readings WHERE variant_unit_id = ?",
            (variant_id,),
        ).fetchone()[0]
        witnesses_before = in_memory_db.execute(
            """SELECT COUNT(*) FROM reading_witnesses rw
               JOIN witness_readings wr ON rw.reading_id = wr.id
               WHERE wr.variant_unit_id = ?""",
            (variant_id,),
        ).fetchone()[0]

        assert readings_before > 0, "Readings should exist before delete"
        assert witnesses_before > 0, "Witnesses should exist before delete"

        # Delete parent (variant_unit)
        store.delete_variant("John.1.18", 3)

        # Verify cascade deleted children FOR THIS VARIANT
        readings_after = in_memory_db.execute(
            "SELECT COUNT(*) FROM witness_readings WHERE variant_unit_id = ?",
            (variant_id,),
        ).fetchone()[0]
        witnesses_after = in_memory_db.execute(
            """SELECT COUNT(*) FROM reading_witnesses rw
               JOIN witness_readings wr ON rw.reading_id = wr.id
               WHERE wr.variant_unit_id = ?""",
            (variant_id,),
        ).fetchone()[0]

        assert readings_after == 0, "FK cascade should delete readings"
        assert witnesses_after == 0, "FK cascade should delete witnesses"


class TestSignificanceLevels:
    """Tests for significance classification."""

    def test_trivial_does_not_require_ack(self):
        """Trivial variants should not require acknowledgement."""
        variant = VariantUnit(
            ref="Matt.1.1",
            position=1,
            readings=[
                WitnessReading(
                    surface_text="Ἰησοῦ",
                    witnesses=["P1"],
                    witness_types=[WitnessType.PAPYRUS],
                ),
            ],
            significance=SignificanceLevel.TRIVIAL,
        )

        assert not variant.requires_acknowledgement

    def test_minor_does_not_require_ack(self):
        """Minor variants should not require acknowledgement."""
        variant = VariantUnit(
            ref="Matt.1.1",
            position=1,
            readings=[
                WitnessReading(
                    surface_text="Ἰησοῦ",
                    witnesses=["P1"],
                    witness_types=[WitnessType.PAPYRUS],
                ),
            ],
            significance=SignificanceLevel.MINOR,
        )

        assert not variant.requires_acknowledgement

    def test_significant_requires_ack(self):
        """Significant variants should require acknowledgement."""
        variant = VariantUnit(
            ref="John.1.18",
            position=3,
            readings=[
                WitnessReading(
                    surface_text="θεός",
                    witnesses=["P66"],
                    witness_types=[WitnessType.PAPYRUS],
                ),
            ],
            significance=SignificanceLevel.SIGNIFICANT,
        )

        assert variant.requires_acknowledgement

    def test_major_requires_ack(self, john_1_18_variant):
        """Major variants should require acknowledgement."""
        assert john_1_18_variant.significance == SignificanceLevel.MAJOR
        assert john_1_18_variant.requires_acknowledgement
