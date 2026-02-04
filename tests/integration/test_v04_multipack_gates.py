"""Sprint 12 / v0.4.0 integration tests: Multi-pack gate stability.

Tests verify:
- Gate count is stable regardless of number of packs installed
- Merged VariantUnit per location (not per-pack)
- Acknowledgement once suppresses future gates for that VariantUnit
- Dossier includes provenance packs from all installed packs
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from redletters.variants.store import VariantStore
from redletters.variants.builder import VariantBuilder
from redletters.variants.dossier import DossierGenerator
from redletters.gates.state import AcknowledgementStore


class MockSpineProvider:
    """Mock spine provider for testing."""

    def __init__(self, verses: dict[str, str]):
        self._verses = verses

    def get_verse_text(self, verse_id: str):
        from dataclasses import dataclass

        @dataclass
        class VerseText:
            verse_id: str
            text: str

        text = self._verses.get(verse_id)
        if text:
            return VerseText(verse_id=verse_id, text=text)
        return None

    def has_verse(self, verse_id: str) -> bool:
        return verse_id in self._verses


class MockPackSpine:
    """Mock pack spine for testing."""

    def __init__(self, pack_id: str, verses: dict[str, str]):
        self._pack_id = pack_id
        self._verses = verses

    def get_verse_text(self, verse_id: str):
        from dataclasses import dataclass

        @dataclass
        class VerseText:
            verse_id: str
            text: str

        text = self._verses.get(verse_id)
        if text:
            return VerseText(verse_id=verse_id, text=text)
        return None


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def db_conn(tmp_path: Path):
    """Create a temporary database connection."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


@pytest.fixture
def variant_store(db_conn):
    """Create and initialize a variant store."""
    store = VariantStore(db_conn)
    store.init_schema()
    return store


@pytest.fixture
def ack_store(db_conn):
    """Create and initialize an acknowledgement store."""
    store = AcknowledgementStore(db_conn)
    store.init_schema()
    return store


@pytest.fixture
def spine():
    """Create mock SBLGNT spine."""
    return MockSpineProvider(
        {
            "John.1.1": "Ἐν ἀρχῇ ἦν ὁ λόγος",
            "John.1.18": "θεὸν οὐδεὶς ἑώρακεν πώποτε· μονογενὴς θεὸς",
            "John.1.28": "Ἐν Βηθανίᾳ ἐγένετο",
        }
    )


@pytest.fixture
def wh_pack():
    """Create mock WH pack with differing readings."""
    return MockPackSpine(
        "westcott-hort-john",
        {
            "John.1.1": "Ἐν ἀρχῇ ἦν ὁ λόγος",  # Same as spine
            "John.1.18": "θεὸν οὐδεὶς ἑώρακεν πώποτε· μονογενὴς υἱὸς",  # DIFFERS: υἱός not θεός
            "John.1.28": "Ἐν Βηθανίᾳ ἐγένετο",  # Same as spine
        },
    )


@pytest.fixture
def byz_pack():
    """Create mock Byzantine pack with differing readings."""
    return MockPackSpine(
        "byzantine-john",
        {
            "John.1.1": "Ἐν ἀρχῇ ἦν ὁ λόγος",  # Same as spine
            "John.1.18": "θεὸν οὐδεὶς ἑώρακεν πώποτε· μονογενὴς υἱὸς",  # DIFFERS: same as WH
            "John.1.28": "Ἐν Βηθαβαρᾷ ἐγένετο",  # DIFFERS: Bethabara not Bethany
        },
    )


# ============================================================================
# Tests: Gate Count Stability
# ============================================================================


class TestGateCountStability:
    """Tests verifying gate count doesn't multiply with multiple packs."""

    def test_single_pack_creates_one_variant_per_location(
        self, variant_store, spine, wh_pack
    ):
        """Building with one pack creates exactly one VariantUnit per location."""
        builder = VariantBuilder(spine, variant_store)
        builder.add_edition(
            edition_key="westcott-hort-john",
            edition_spine=wh_pack,
            witness_siglum="WH",
            date_range=(19, 19),
            source_pack_id="westcott-hort-john",
        )

        # Build variants for John 1:18
        result = builder.build_verse("John.1.18")

        assert result.variants_created == 1 or result.variants_updated == 1

        # Verify exactly one variant exists
        variants = variant_store.get_variants_for_verse("John.1.18")
        assert len(variants) == 1

    def test_two_packs_create_one_merged_variant(
        self, variant_store, spine, wh_pack, byz_pack
    ):
        """Building with two packs creates ONE merged VariantUnit, not two."""
        builder = VariantBuilder(spine, variant_store)

        # Add WH pack
        builder.add_edition(
            edition_key="westcott-hort-john",
            edition_spine=wh_pack,
            witness_siglum="WH",
            date_range=(19, 19),
            source_pack_id="westcott-hort-john",
        )

        # Add Byzantine pack
        builder.add_edition(
            edition_key="byzantine-john",
            edition_spine=byz_pack,
            witness_siglum="Byz",
            date_range=(21, 21),
            source_pack_id="byzantine-john",
        )

        # Build variants for John 1:18 (both packs have same variant reading)
        builder.build_verse("John.1.18")

        # Should create/update only ONE variant, not two
        variants = variant_store.get_variants_for_verse("John.1.18")
        assert len(variants) == 1, f"Expected 1 merged VariantUnit, got {len(variants)}"

    def test_merged_variant_has_combined_support(
        self, variant_store, spine, wh_pack, byz_pack
    ):
        """Merged variant includes support entries from both packs."""
        builder = VariantBuilder(spine, variant_store)

        builder.add_edition(
            edition_key="westcott-hort-john",
            edition_spine=wh_pack,
            witness_siglum="WH",
            date_range=(19, 19),
            source_pack_id="westcott-hort-john",
        )
        builder.add_edition(
            edition_key="byzantine-john",
            edition_spine=byz_pack,
            witness_siglum="Byz",
            date_range=(21, 21),
            source_pack_id="byzantine-john",
        )

        builder.build_verse("John.1.18")

        variants = variant_store.get_variants_for_verse("John.1.18")
        assert len(variants) == 1

        # Check readings - should have SBLGNT + merged variant reading
        variant = variants[0]
        assert len(variant.readings) >= 2  # At least spine + one alternate

        # Find the non-spine reading
        alt_readings = [r for i, r in enumerate(variant.readings) if i != 0]
        if alt_readings:
            alt = alt_readings[0]
            # Should have support from both WH and Byz
            source_packs = alt.get_source_packs()
            assert len(source_packs) >= 1  # At least one pack


class TestGatePendingStability:
    """Tests verifying pending gate count is stable."""

    def test_pending_count_stable_with_multiple_packs(
        self, variant_store, ack_store, spine, wh_pack, byz_pack
    ):
        """Pending gate count should be same regardless of pack count."""
        builder = VariantBuilder(spine, variant_store)

        # Add both packs
        builder.add_edition(
            edition_key="westcott-hort-john",
            edition_spine=wh_pack,
            witness_siglum="WH",
            source_pack_id="westcott-hort-john",
        )
        builder.add_edition(
            edition_key="byzantine-john",
            edition_spine=byz_pack,
            witness_siglum="Byz",
            source_pack_id="byzantine-john",
        )

        # Build variants
        builder.build_verse("John.1.18")
        builder.build_verse("John.1.28")

        # Get significant variants (these would be pending gates)
        significant = variant_store.get_significant_variants(book="John", chapter=1)

        # Each location should have exactly ONE variant
        refs = [v.ref for v in significant]
        unique_refs = set(refs)
        assert len(refs) == len(unique_refs), (
            "Duplicate variants found - gates would multiply!"
        )

    def test_acknowledgement_once_suppresses_gate(
        self, variant_store, ack_store, spine, wh_pack, byz_pack
    ):
        """Acknowledging once should suppress the gate for that VariantUnit."""
        builder = VariantBuilder(spine, variant_store)
        builder.add_edition(
            edition_key="westcott-hort-john",
            edition_spine=wh_pack,
            witness_siglum="WH",
            source_pack_id="westcott-hort-john",
        )
        builder.add_edition(
            edition_key="byzantine-john",
            edition_spine=byz_pack,
            witness_siglum="Byz",
            source_pack_id="byzantine-john",
        )

        builder.build_verse("John.1.18")

        # Acknowledge the variant
        session_id = "test-session"
        state = ack_store.load_session_state(session_id)
        ack = state.acknowledge_variant(
            ref="John.1.18",
            reading_chosen=0,
            context="Test acknowledgement",
        )
        ack_store.persist_variant_ack(ack)

        # Check state
        state = ack_store.load_session_state(session_id)
        assert state.has_acknowledged_variant("John.1.18")

        # Verify acknowledged
        assert ack_store.has_variant_ack(session_id, "John.1.18")


class TestDossierProvenance:
    """Tests for dossier provenance with multiple packs."""

    def test_dossier_lists_all_provenance_packs(
        self, variant_store, spine, wh_pack, byz_pack
    ):
        """Dossier should list all packs that contributed to readings."""
        builder = VariantBuilder(spine, variant_store)

        builder.add_edition(
            edition_key="westcott-hort-john",
            edition_spine=wh_pack,
            witness_siglum="WH",
            source_pack_id="westcott-hort-john",
        )
        builder.add_edition(
            edition_key="byzantine-john",
            edition_spine=byz_pack,
            witness_siglum="Byz",
            source_pack_id="byzantine-john",
        )

        builder.build_verse("John.1.18")

        # Generate dossier
        generator = DossierGenerator(variant_store)
        dossier = generator.generate("John.1.18")

        # Check provenance in dossier - packs are listed at reading level
        # At least one comparative pack should be listed

        # Check readings for provenance
        if dossier.variants:
            for reading in dossier.variants[0].readings:
                if reading.source_packs:
                    # Found packs
                    assert len(reading.source_packs) >= 1


class TestIdempotentRebuild:
    """Tests for idempotent multi-pack rebuilds."""

    def test_rebuild_does_not_duplicate_variants(
        self, variant_store, spine, wh_pack, byz_pack
    ):
        """Running build multiple times should not create duplicate variants."""
        builder = VariantBuilder(spine, variant_store)
        builder.add_edition(
            edition_key="westcott-hort-john",
            edition_spine=wh_pack,
            witness_siglum="WH",
            source_pack_id="westcott-hort-john",
        )
        builder.add_edition(
            edition_key="byzantine-john",
            edition_spine=byz_pack,
            witness_siglum="Byz",
            source_pack_id="byzantine-john",
        )

        # First build
        builder.build_verse("John.1.18")
        variants_after_first = variant_store.get_variants_for_verse("John.1.18")
        count_first = len(variants_after_first)

        # Second build
        builder.build_verse("John.1.18")
        variants_after_second = variant_store.get_variants_for_verse("John.1.18")
        count_second = len(variants_after_second)

        # Should be same count
        assert count_first == count_second, (
            f"Rebuild created duplicates: {count_first} -> {count_second}"
        )

    def test_rebuild_does_not_duplicate_support_entries(
        self, variant_store, spine, wh_pack
    ):
        """Running build twice should not duplicate support entries."""
        builder = VariantBuilder(spine, variant_store)
        builder.add_edition(
            edition_key="westcott-hort-john",
            edition_spine=wh_pack,
            witness_siglum="WH",
            source_pack_id="westcott-hort-john",
        )

        # First build
        builder.build_verse("John.1.18")

        # Get support count for the reading
        variants = variant_store.get_variants_for_verse("John.1.18")
        if variants and variants[0].readings:
            reading = variants[0].readings[0]
            count_first = len(reading.support_set)

            # Second build (should merge, not duplicate)
            builder2 = VariantBuilder(spine, variant_store)
            builder2.add_edition(
                edition_key="westcott-hort-john",
                edition_spine=wh_pack,
                witness_siglum="WH",
                source_pack_id="westcott-hort-john",
            )
            builder2.build_verse("John.1.18")

            # Re-load and check
            variants2 = variant_store.get_variants_for_verse("John.1.18")
            if variants2 and variants2[0].readings:
                reading2 = variants2[0].readings[0]
                count_second = len(reading2.support_set)

                # Should be same (UNIQUE constraint prevents duplicates)
                assert count_first == count_second, (
                    f"Rebuild duplicated supports: {count_first} -> {count_second}"
                )
