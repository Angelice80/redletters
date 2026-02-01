"""Sprint 2 Source Pack Vertical Slice Integration Tests.

End-to-end tests proving the complete Source Pack flow:
1. Load SBLGNT spine from fixture
2. Load comparative edition from fixture
3. Build variants on-demand by diffing editions
4. Trigger variant gate for significant/major variants
5. Acknowledge variant
6. Complete translation with spine_text + surfaced variants

Test data: John 1:18 has μονογενὴς θεὸς (SBLGNT) vs μονογενὴς υἱὸς (WH-style)
This is a MAJOR variant (theological term differs) that must trigger gating.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from redletters.sources.spine import FixtureSpine
from redletters.sources.catalog import SourceCatalog
from redletters.variants.builder import VariantBuilder
from redletters.variants.store import VariantStore
from redletters.variants.models import SignificanceLevel
from redletters.gates.state import AcknowledgementStore
from redletters.pipeline.orchestrator import translate_passage, acknowledge_variant
from redletters.pipeline.schemas import GateResponsePayload, TranslateResponse


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SPINE_FIXTURE = FIXTURES_DIR / "spine_fixture.json"
COMPARATIVE_FIXTURE = FIXTURES_DIR / "comparative_fixture.json"


@pytest.fixture
def db_connection():
    """Create in-memory database with required schemas."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Initialize stores
    variant_store = VariantStore(conn)
    variant_store.init_schema()

    ack_store = AcknowledgementStore(conn)
    ack_store.init_schema()

    yield conn
    conn.close()


@pytest.fixture
def spine():
    """SBLGNT spine loaded from fixture."""
    return FixtureSpine(SPINE_FIXTURE, source_key="morphgnt-sblgnt")


@pytest.fixture
def comparative():
    """Comparative edition (WH-style) loaded from fixture."""
    return FixtureSpine(COMPARATIVE_FIXTURE, source_key="test-wh")


@pytest.fixture
def variant_builder(db_connection, spine, comparative):
    """Variant builder with comparative edition registered."""
    store = VariantStore(db_connection)
    builder = VariantBuilder(spine, store)
    builder.add_edition("test-wh", comparative, "WH")
    return builder


class TestSourcePackVerticalSlice:
    """Complete vertical slice using Source Pack infrastructure."""

    def test_john_118_gate_triggered_major_variant(
        self, db_connection, spine, variant_builder
    ):
        """John 1:18 triggers MAJOR variant gate (θεὸς vs υἱὸς)."""
        result = translate_passage(
            conn=db_connection,
            reference="John 1:18",
            mode="readable",
            session_id="slice-test-1",
            options={
                "spine_provider": spine,
                "variant_builder": variant_builder,
            },
        )

        # Must return gate (not translation)
        assert isinstance(result, GateResponsePayload), (
            f"Expected GateResponsePayload for MAJOR variant, got {type(result)}"
        )
        assert result.gate_type == "variant"
        assert (
            "major" in result.message.lower() or "significant" in result.message.lower()
        )

        # Verify variant was built correctly
        store = VariantStore(db_connection)
        variants = store.get_variants_for_verse("John.1.18")
        assert len(variants) == 1

        variant = variants[0]
        assert variant.significance == SignificanceLevel.MAJOR
        assert len(variant.readings) >= 2

        # SBLGNT reading should be first (index 0)
        assert variant.sblgnt_reading_index == 0
        sblgnt = variant.sblgnt_reading
        assert sblgnt is not None
        assert "θεὸς" in sblgnt.surface_text

    def test_john_118_acknowledge_then_translate(
        self, db_connection, spine, variant_builder
    ):
        """After acknowledging John 1:18 variant, translation proceeds."""
        session_id = "slice-test-2"

        # Step 1: First call triggers gate
        result1 = translate_passage(
            conn=db_connection,
            reference="John 1:18",
            mode="readable",
            session_id=session_id,
            options={
                "spine_provider": spine,
                "variant_builder": variant_builder,
            },
        )
        assert isinstance(result1, GateResponsePayload)

        # Step 2: Acknowledge choosing SBLGNT reading (index 0)
        acknowledge_variant(
            conn=db_connection,
            session_id=session_id,
            variant_ref="John.1.18",
            reading_index=0,
            context="source-pack-test",
        )

        # Step 3: Second call proceeds to translation
        result2 = translate_passage(
            conn=db_connection,
            reference="John 1:18",
            mode="readable",
            session_id=session_id,
            options={
                "spine_provider": spine,
                "variant_builder": variant_builder,
            },
        )

        assert isinstance(result2, TranslateResponse), (
            f"Expected TranslateResponse after acknowledgement, got {type(result2)}"
        )
        assert result2.response_type == "translation"

        # Spine text should be from fixture
        assert "Θεὸν" in result2.sblgnt_text
        assert "μονογενὴς" in result2.sblgnt_text

        # Variants should be surfaced side-by-side
        assert len(result2.variants) >= 1
        var_display = result2.variants[0]
        assert var_display.acknowledged is True
        assert "θεὸς" in var_display.sblgnt_reading

    def test_matthew_32_no_gate_identical_text(
        self, db_connection, spine, variant_builder
    ):
        """Matthew 3:2 has no variant (identical in both editions)."""
        result = translate_passage(
            conn=db_connection,
            reference="Matthew 3:2",
            mode="readable",
            session_id="slice-test-3",
            options={
                "spine_provider": spine,
                "variant_builder": variant_builder,
            },
        )

        # Should proceed directly to translation (no gate)
        assert isinstance(result, TranslateResponse), (
            f"Expected TranslateResponse for identical text, got {type(result)}"
        )

        # Spine text should be from fixture
        assert "Μετανοεῖτε" in result.sblgnt_text

    def test_john_316_minor_variant_no_gate(
        self, db_connection, spine, variant_builder
    ):
        """John 3:16 has a minor variant (αὐτοῦ addition) - may or may not gate."""
        result = translate_passage(
            conn=db_connection,
            reference="John 3:16",
            mode="readable",
            session_id="slice-test-4",
            options={
                "spine_provider": spine,
                "variant_builder": variant_builder,
            },
        )

        # Check if variant was built
        store = VariantStore(db_connection)
        variants = store.get_variants_for_verse("John.3.16")

        if variants:
            variant = variants[0]
            # If minor, should not gate
            if variant.significance in (
                SignificanceLevel.TRIVIAL,
                SignificanceLevel.MINOR,
            ):
                assert isinstance(result, TranslateResponse)
            # If significant/major, should gate
            else:
                assert isinstance(result, GateResponsePayload)
        else:
            # No variant means translation proceeds
            assert isinstance(result, TranslateResponse)


class TestSourcePackADRCompliance:
    """ADR compliance tests using Source Pack infrastructure."""

    def test_adr007_sblgnt_is_canonical_spine(self):
        """ADR-007: SBLGNT is designated as canonical spine in catalog."""
        catalog = SourceCatalog.load()

        assert catalog.spine is not None
        assert catalog.spine.key == "morphgnt-sblgnt"
        assert catalog.spine.is_spine is True

    def test_adr007_sblgnt_is_default_reading(
        self, db_connection, spine, variant_builder
    ):
        """ADR-007: SBLGNT reading is always the default (index 0)."""
        # Build variant
        variant_builder.build_verse("John.1.18")

        store = VariantStore(db_connection)
        variants = store.get_variants_for_verse("John.1.18")

        assert len(variants) == 1
        variant = variants[0]

        # SBLGNT must be index 0
        assert variant.sblgnt_reading_index == 0

        # SBLGNT reading should match spine text
        sblgnt_reading = variant.sblgnt_reading
        spine_verse = spine.get_verse_text("John.1.18")

        assert sblgnt_reading is not None
        assert spine_verse is not None
        # Both should have θεὸς (not υἱὸς)
        assert "θεὸς" in spine_verse.text
        assert "θεὸς" in sblgnt_reading.surface_text

    def test_adr008_variants_surfaced_side_by_side(
        self, db_connection, spine, variant_builder
    ):
        """ADR-008: Variants are surfaced side-by-side, not buried."""
        result = translate_passage(
            conn=db_connection,
            reference="John 1:18",
            mode="readable",
            session_id="adr008-test-1",
            options={
                "spine_provider": spine,
                "variant_builder": variant_builder,
            },
        )

        assert isinstance(result, GateResponsePayload)
        assert result.variants_side_by_side is not None
        assert len(result.variants_side_by_side) > 0

        var_display = result.variants_side_by_side[0]
        # Should show SBLGNT and alternates
        assert var_display.sblgnt_reading is not None
        assert len(var_display.alternate_readings) > 0

    def test_adr008_significant_major_require_ack(
        self, db_connection, spine, variant_builder
    ):
        """ADR-008: Significant/major variants require explicit acknowledgement."""
        # John 1:18 is MAJOR
        result = translate_passage(
            conn=db_connection,
            reference="John 1:18",
            mode="readable",
            session_id="adr008-test-2",
            options={
                "spine_provider": spine,
                "variant_builder": variant_builder,
            },
        )

        # Must gate
        assert isinstance(result, GateResponsePayload)
        assert result.gate_type == "variant"

        # Variant should require acknowledgement
        store = VariantStore(db_connection)
        variants = store.get_variants_for_verse("John.1.18")
        assert variants[0].requires_acknowledgement is True


class TestVariantBuilderIdempotency:
    """Tests proving variant builder is idempotent."""

    def test_rebuild_does_not_duplicate(self, db_connection, spine, comparative):
        """Building same verse twice does not create duplicates."""
        store = VariantStore(db_connection)
        builder = VariantBuilder(spine, store)
        builder.add_edition("test-wh", comparative, "WH")

        # Build twice
        result1 = builder.build_verse("John.1.18")
        result2 = builder.build_verse("John.1.18")

        # First creates, second updates
        assert result1.variants_created == 1
        assert result2.variants_updated == 1

        # Only one variant exists
        variants = store.get_variants_for_verse("John.1.18")
        assert len(variants) == 1

    def test_rebuild_preserves_significance(self, db_connection, spine, comparative):
        """Rebuilding preserves computed significance."""
        store = VariantStore(db_connection)
        builder = VariantBuilder(spine, store)
        builder.add_edition("test-wh", comparative, "WH")

        # Build
        builder.build_verse("John.1.18")
        variants1 = store.get_variants_for_verse("John.1.18")
        sig1 = variants1[0].significance

        # Rebuild
        builder.build_verse("John.1.18")
        variants2 = store.get_variants_for_verse("John.1.18")
        sig2 = variants2[0].significance

        assert sig1 == sig2 == SignificanceLevel.MAJOR


class TestProvenanceTracking:
    """Tests for provenance in Source Pack flow."""

    def test_provenance_shows_sblgnt_spine(self, db_connection, spine, variant_builder):
        """Provenance always marks SBLGNT as spine source."""
        session_id = "prov-test-1"

        # Acknowledge to get translation
        translate_passage(
            conn=db_connection,
            reference="John 1:18",
            mode="readable",
            session_id=session_id,
            options={
                "spine_provider": spine,
                "variant_builder": variant_builder,
            },
        )

        acknowledge_variant(
            conn=db_connection,
            session_id=session_id,
            variant_ref="John.1.18",
            reading_index=0,
        )

        result = translate_passage(
            conn=db_connection,
            reference="John 1:18",
            mode="readable",
            session_id=session_id,
            options={
                "spine_provider": spine,
                "variant_builder": variant_builder,
            },
        )

        assert isinstance(result, TranslateResponse)
        # Provenance should include spine provider's source_key
        assert "sblgnt" in result.provenance.spine_source.lower()
        assert result.provenance.spine_marker == "default"
