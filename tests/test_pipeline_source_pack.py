"""Tests for pipeline orchestrator with Source Pack integration.

Proves Sprint 2 integration:
- Orchestrator uses Source Pack spine provider when available
- Falls back to database tokens when no spine provider
- Builds variants on-demand when variant_builder provided
- Gate detection works with real(ish) spine data
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from redletters.sources.spine import FixtureSpine
from redletters.variants.builder import VariantBuilder
from redletters.variants.store import VariantStore
from redletters.variants.models import SignificanceLevel
from redletters.gates.state import AcknowledgementStore
from redletters.pipeline.orchestrator import (
    translate_passage,
    acknowledge_variant,
)
from redletters.pipeline.schemas import GateResponsePayload, TranslateResponse


# Get fixture paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SPINE_FIXTURE = FIXTURES_DIR / "spine_fixture.json"
COMPARATIVE_FIXTURE = FIXTURES_DIR / "comparative_fixture.json"


@pytest.fixture
def db_connection():
    """Create in-memory database with schemas."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Initialize stores to create schemas
    from redletters.variants.store import VariantStore

    variant_store = VariantStore(conn)
    variant_store.init_schema()

    ack_store = AcknowledgementStore(conn)
    ack_store.init_schema()

    yield conn
    conn.close()


@pytest.fixture
def spine():
    """Create fixture spine."""
    return FixtureSpine(SPINE_FIXTURE, source_key="sblgnt-fixture")


@pytest.fixture
def comparative():
    """Create comparative fixture spine."""
    return FixtureSpine(COMPARATIVE_FIXTURE, source_key="wh-fixture")


@pytest.fixture
def variant_builder(db_connection, spine, comparative):
    """Create variant builder with comparative edition."""
    store = VariantStore(db_connection)
    builder = VariantBuilder(spine, store)
    builder.add_edition("wh", comparative, "WH")
    return builder


class TestOrchestratorWithSpineProvider:
    """Test orchestrator using Source Pack spine provider."""

    def test_translate_with_spine_provider(self, db_connection, spine):
        """Orchestrator uses spine provider for Greek text."""
        result = translate_passage(
            conn=db_connection,
            reference="John 1:18",
            mode="readable",
            session_id="test-session",
            options={"spine_provider": spine},
        )

        # Should return TranslateResponse (no variants = no gate)
        assert isinstance(result, TranslateResponse)

        # Greek text should come from fixture
        assert "Θεὸν" in result.sblgnt_text
        assert "μονογενὴς" in result.sblgnt_text

    def test_translate_with_variant_builder_triggers_gate(
        self, db_connection, spine, variant_builder
    ):
        """When variant_builder builds MAJOR variant, gate is triggered."""
        result = translate_passage(
            conn=db_connection,
            reference="John 1:18",
            mode="readable",
            session_id="test-session",
            options={
                "spine_provider": spine,
                "variant_builder": variant_builder,
            },
        )

        # Should return GateResponsePayload for MAJOR variant
        assert isinstance(result, GateResponsePayload)
        assert result.gate_type == "variant"
        assert (
            "significant" in result.message.lower() or "major" in result.message.lower()
        )

        # Variants should be built on-demand
        from redletters.variants.store import VariantStore

        store = VariantStore(db_connection)
        variants = store.get_variants_for_verse("John.1.18")
        assert len(variants) == 1
        assert variants[0].significance == SignificanceLevel.MAJOR

    def test_acknowledge_then_translate(self, db_connection, spine, variant_builder):
        """After acknowledgement, translation proceeds."""
        # First call triggers gate
        result1 = translate_passage(
            conn=db_connection,
            reference="John 1:18",
            mode="readable",
            session_id="test-session",
            options={
                "spine_provider": spine,
                "variant_builder": variant_builder,
            },
        )
        assert isinstance(result1, GateResponsePayload)

        # Acknowledge the variant (reading 0 = SBLGNT)
        acknowledge_variant(
            conn=db_connection,
            session_id="test-session",
            variant_ref="John.1.18",
            reading_index=0,
        )

        # Second call should return translation
        result2 = translate_passage(
            conn=db_connection,
            reference="John 1:18",
            mode="readable",
            session_id="test-session",
            options={
                "spine_provider": spine,
                "variant_builder": variant_builder,
            },
        )
        assert isinstance(result2, TranslateResponse)
        assert result2.sblgnt_text is not None

    def test_no_variant_no_gate(self, db_connection, spine, comparative):
        """Verse with no variant difference doesn't trigger gate."""
        # Matt 3:2 has no difference in our fixtures
        store = VariantStore(db_connection)
        builder = VariantBuilder(spine, store)
        builder.add_edition("wh", comparative, "WH")

        result = translate_passage(
            conn=db_connection,
            reference="Matthew 3:2",
            mode="readable",
            session_id="test-session",
            options={
                "spine_provider": spine,
                "variant_builder": builder,
            },
        )

        # Should return TranslateResponse (identical texts = no variant)
        assert isinstance(result, TranslateResponse)

    def test_provenance_shows_sblgnt_spine(self, db_connection, spine):
        """Provenance info shows spine source from provider."""
        result = translate_passage(
            conn=db_connection,
            reference="John 3:16",
            mode="readable",
            session_id="test-session",
            options={"spine_provider": spine},
        )

        assert isinstance(result, TranslateResponse)
        # Provenance should include spine provider's source_key
        assert "sblgnt" in result.provenance.spine_source.lower()
        assert result.provenance.spine_marker == "default"


class TestOrchestratorFallback:
    """Test orchestrator falling back to database tokens."""

    def test_fallback_without_spine_provider(self, db_connection):
        """Without spine_provider, uses database tokens (fails if no tokens table)."""
        # This will fail since tokens table doesn't exist in test DB
        # The fallback behavior is: try spine_provider first, then database
        # Since neither is available, it should raise an error
        with pytest.raises((ValueError, Exception)):
            translate_passage(
                conn=db_connection,
                reference="John 1:18",
                mode="readable",
                session_id="test-session",
                options={},  # No spine_provider
            )


class TestADRCompliance:
    """Test ADR compliance for Sprint 2."""

    def test_adr007_sblgnt_is_spine_default(
        self, db_connection, spine, variant_builder
    ):
        """ADR-007: SBLGNT is always the default reading."""
        # Build variants
        result = translate_passage(
            conn=db_connection,
            reference="John 1:18",
            mode="readable",
            session_id="test-session",
            options={
                "spine_provider": spine,
                "variant_builder": variant_builder,
            },
        )

        # Gate response should show SBLGNT as default
        assert isinstance(result, GateResponsePayload)

        # Check variants side-by-side
        variants = result.variants_side_by_side
        assert len(variants) > 0

        # SBLGNT reading should be there
        john_variant = variants[0]
        assert "θεὸς" in john_variant.sblgnt_reading  # SBLGNT has θεὸς

    def test_adr008_significant_variant_requires_ack(
        self, db_connection, spine, variant_builder
    ):
        """ADR-008: Significant/major variants require acknowledgement."""
        result = translate_passage(
            conn=db_connection,
            reference="John 1:18",
            mode="readable",
            session_id="test-session",
            options={
                "spine_provider": spine,
                "variant_builder": variant_builder,
            },
        )

        # Gate should be triggered
        assert isinstance(result, GateResponsePayload)
        assert result.gate_type == "variant"

        # Should have options to choose reading
        assert len(result.options) > 0
        has_sblgnt_option = any("SBLGNT" in opt.label for opt in result.options)
        assert has_sblgnt_option

    def test_adr008_variants_surfaced_side_by_side(
        self, db_connection, spine, variant_builder
    ):
        """ADR-008: Variants are surfaced side-by-side."""
        result = translate_passage(
            conn=db_connection,
            reference="John 1:18",
            mode="readable",
            session_id="test-session",
            options={
                "spine_provider": spine,
                "variant_builder": variant_builder,
            },
        )

        assert isinstance(result, GateResponsePayload)
        assert result.variants_side_by_side is not None
        assert len(result.variants_side_by_side) > 0

        # Each variant should have SBLGNT reading and alternates
        variant_display = result.variants_side_by_side[0]
        assert variant_display.sblgnt_reading is not None
        assert len(variant_display.alternate_readings) > 0
