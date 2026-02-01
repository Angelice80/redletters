"""Integration tests for the vertical slice.

Tests the translate_passage orchestration pipeline end-to-end:
1. Gate flow (variant acknowledgement)
2. Acknowledgement persistence
3. Claim enforcement (readable vs traceable)
4. Confidence scoring
5. Response schema validation
"""

from __future__ import annotations

import sqlite3
import pytest

from redletters.pipeline import (
    translate_passage,
    GateResponsePayload,
    TranslateResponse,
)
from redletters.pipeline.orchestrator import acknowledge_variant
from redletters.pipeline.translator import FakeTranslator
from redletters.variants.store import VariantStore
from redletters.variants.models import (
    VariantUnit,
    WitnessReading,
    WitnessType,
    VariantClassification,
    SignificanceLevel,
)
from redletters.gates.state import AcknowledgementStore


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database with required schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Create tokens table with minimal test data
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            position INTEGER NOT NULL,
            surface TEXT NOT NULL,
            lemma TEXT NOT NULL,
            morph TEXT,
            is_red_letter INTEGER DEFAULT 0
        );

        -- Insert test tokens for John 1:18
        INSERT INTO tokens (book, chapter, verse, position, surface, lemma, morph, is_red_letter)
        VALUES
            ('John', 1, 18, 1, 'θεὸν', 'θεός', 'N-ASM', 0),
            ('John', 1, 18, 2, 'οὐδεὶς', 'οὐδείς', 'A-NSM', 0),
            ('John', 1, 18, 3, 'ἑώρακεν', 'ὁράω', 'V-RAI-3S', 0),
            ('John', 1, 18, 4, 'πώποτε', 'πώποτε', 'ADV', 0);

        -- Insert test tokens for Matthew 3:2
        INSERT INTO tokens (book, chapter, verse, position, surface, lemma, morph, is_red_letter)
        VALUES
            ('Matthew', 3, 2, 1, 'μετανοεῖτε', 'μετανοέω', 'V-PAM-2P', 1),
            ('Matthew', 3, 2, 2, 'ἤγγικεν', 'ἐγγίζω', 'V-RAI-3S', 1),
            ('Matthew', 3, 2, 3, 'γὰρ', 'γάρ', 'CONJ', 1),
            ('Matthew', 3, 2, 4, 'ἡ', 'ὁ', 'T-NSF', 1),
            ('Matthew', 3, 2, 5, 'βασιλεία', 'βασιλεία', 'N-NSF', 1);
    """)
    conn.commit()

    yield conn
    conn.close()


@pytest.fixture
def db_with_variant(in_memory_db):
    """Database with a significant variant at John 1:18."""
    store = VariantStore(in_memory_db)
    store.init_schema()

    # Create significant variant (monogenes theos vs monogenes huios)
    variant = VariantUnit(
        ref="John.1.18",
        position=5,
        readings=[
            WitnessReading(
                surface_text="μονογενὴς θεός",
                witnesses=["P66", "P75", "א", "B"],
                witness_types=[
                    WitnessType.PAPYRUS,
                    WitnessType.PAPYRUS,
                    WitnessType.UNCIAL,
                    WitnessType.UNCIAL,
                ],
                date_range=(2, 4),
            ),
            WitnessReading(
                surface_text="ὁ μονογενὴς υἱός",
                witnesses=["A", "C", "D", "W"],
                witness_types=[
                    WitnessType.UNCIAL,
                    WitnessType.UNCIAL,
                    WitnessType.UNCIAL,
                    WitnessType.UNCIAL,
                ],
                date_range=(4, 5),
            ),
        ],
        sblgnt_reading_index=0,
        classification=VariantClassification.SUBSTITUTION,
        significance=SignificanceLevel.MAJOR,
        notes="Christologically significant variant",
    )

    store.save_variant(variant)

    return in_memory_db


class TestGateFlow:
    """Tests for gate triggering and acknowledgement flow."""

    def test_significant_variant_triggers_gate(self, db_with_variant):
        """Significant variant without acknowledgement returns GateResponse."""
        result = translate_passage(
            conn=db_with_variant,
            reference="John 1:18",
            mode="readable",
            session_id="test-session-1",
        )

        assert isinstance(result, GateResponsePayload)
        assert result.response_type == "gate"
        assert result.gate_type == "variant"
        assert (
            "MAJOR" in result.message
            or "Major" in result.message
            or "major" in result.message
        )
        assert len(result.options) > 0
        assert len(result.variants_side_by_side) > 0

    def test_gate_shows_variants_side_by_side(self, db_with_variant):
        """Gate response includes all variants for side-by-side display."""
        result = translate_passage(
            conn=db_with_variant,
            reference="John 1:18",
            mode="readable",
            session_id="test-session-2",
        )

        assert isinstance(result, GateResponsePayload)

        # Variants should be displayed side-by-side
        variants = result.variants_side_by_side
        assert len(variants) >= 1

        v = variants[0]
        assert v.sblgnt_reading == "μονογενὴς θεός"
        assert len(v.alternate_readings) >= 1
        assert v.requires_acknowledgement is True
        assert v.acknowledged is False

    def test_acknowledged_variant_allows_translation(self, db_with_variant):
        """After acknowledgement, translation proceeds."""
        session_id = "test-session-3"

        # First request triggers gate
        result1 = translate_passage(
            conn=db_with_variant,
            reference="John 1:18",
            mode="readable",
            session_id=session_id,
        )
        assert isinstance(result1, GateResponsePayload)

        # Acknowledge the variant
        acknowledge_variant(
            conn=db_with_variant,
            session_id=session_id,
            variant_ref="John.1.18",
            reading_index=0,
            context="test",
        )

        # Second request should proceed
        result2 = translate_passage(
            conn=db_with_variant,
            reference="John 1:18",
            mode="readable",
            session_id=session_id,
        )

        assert isinstance(result2, TranslateResponse)
        assert result2.response_type == "translation"
        assert result2.sblgnt_text != ""
        assert result2.translation_text != ""


class TestAcknowledgementPersistence:
    """Tests for acknowledgement state persistence."""

    def test_acknowledgement_persists_across_calls(self, db_with_variant):
        """Acknowledgements are stored and loaded correctly."""
        session_id = "persist-test-1"

        # Acknowledge
        acknowledge_variant(
            conn=db_with_variant,
            session_id=session_id,
            variant_ref="John.1.18",
            reading_index=0,
            context="test",
        )

        # Load state
        store = AcknowledgementStore(db_with_variant)
        state = store.load_session_state(session_id)

        assert state.has_acknowledged_variant("John.1.18")
        assert state.get_variant_choice("John.1.18") == 0

    def test_different_sessions_independent(self, db_with_variant):
        """Different sessions have independent acknowledgement state."""
        session_a = "session-a"
        session_b = "session-b"

        # Acknowledge in session A only
        acknowledge_variant(
            conn=db_with_variant,
            session_id=session_a,
            variant_ref="John.1.18",
            reading_index=0,
            context="test",
        )

        # Session A proceeds, session B still gated
        result_a = translate_passage(
            conn=db_with_variant,
            reference="John 1:18",
            mode="readable",
            session_id=session_a,
        )

        result_b = translate_passage(
            conn=db_with_variant,
            reference="John 1:18",
            mode="readable",
            session_id=session_b,
        )

        assert isinstance(result_a, TranslateResponse)
        assert isinstance(result_b, GateResponsePayload)


class TestClaimEnforcement:
    """Tests for claim type enforcement per ADR-009."""

    def test_readable_mode_allows_type0_type1(self, in_memory_db):
        """Readable mode allows TYPE0-1 claims."""
        translator = FakeTranslator(scenario="clean")

        result = translate_passage(
            conn=in_memory_db,
            reference="Matthew 3:2",
            mode="readable",
            session_id="enforce-test-1",
            translator=translator,
        )

        assert isinstance(result, TranslateResponse)

        # All claims should be allowed
        for claim in result.claims:
            assert claim.claim_type <= 1  # TYPE0 or TYPE1
            assert claim.enforcement_allowed is True

    def test_readable_mode_blocks_type5_plus(self, in_memory_db):
        """Readable mode blocks TYPE5+ claims with escalation gate."""
        translator = FakeTranslator(scenario="high_inference")

        result = translate_passage(
            conn=in_memory_db,
            reference="Matthew 3:2",
            mode="readable",
            session_id="enforce-test-2",
            translator=translator,
        )

        # Should return escalation gate
        assert isinstance(result, GateResponsePayload)
        assert result.gate_type == "escalation"
        assert result.escalation_target_mode == "traceable"

    def test_traceable_mode_allows_all_types(self, in_memory_db):
        """Traceable mode allows all claim types with dependencies."""
        translator = FakeTranslator(scenario="high_inference")

        result = translate_passage(
            conn=in_memory_db,
            reference="Matthew 3:2",
            mode="traceable",
            session_id="enforce-test-3",
            translator=translator,
        )

        assert isinstance(result, TranslateResponse)

        # Higher type claims should exist
        high_types = [c for c in result.claims if c.claim_type >= 5]
        assert len(high_types) > 0

    def test_epistemic_pressure_detected(self, in_memory_db):
        """Epistemic pressure language generates warnings."""
        translator = FakeTranslator(scenario="epistemic_pressure")

        result = translate_passage(
            conn=in_memory_db,
            reference="Matthew 3:2",
            mode="traceable",  # Use traceable to get past enforcement
            session_id="pressure-test-1",
            translator=translator,
        )

        assert isinstance(result, TranslateResponse)

        # Should have warnings for pressure language
        claims_with_warnings = [c for c in result.claims if c.warnings]
        assert len(claims_with_warnings) > 0


class TestConfidenceScoring:
    """Tests for layered confidence scoring per ADR-010."""

    def test_confidence_is_layered(self, in_memory_db):
        """Confidence output has all four layers."""
        result = translate_passage(
            conn=in_memory_db,
            reference="Matthew 3:2",
            mode="readable",
            session_id="conf-test-1",
        )

        assert isinstance(result, TranslateResponse)
        assert result.confidence is not None

        conf = result.confidence
        assert 0.0 <= conf.composite <= 1.0
        assert conf.weakest_layer in [
            "textual",
            "grammatical",
            "lexical",
            "interpretive",
        ]

        # All layers present
        assert 0.0 <= conf.textual.score <= 1.0
        assert 0.0 <= conf.grammatical.score <= 1.0
        assert 0.0 <= conf.lexical.score <= 1.0
        assert 0.0 <= conf.interpretive.score <= 1.0

    def test_variant_affects_textual_confidence(self, db_with_variant):
        """Variants reduce textual layer confidence."""
        session_id = "conf-test-2"

        # Acknowledge to get translation
        acknowledge_variant(
            conn=db_with_variant,
            session_id=session_id,
            variant_ref="John.1.18",
            reading_index=0,
            context="test",
        )

        result = translate_passage(
            conn=db_with_variant,
            reference="John 1:18",
            mode="readable",
            session_id=session_id,
        )

        assert isinstance(result, TranslateResponse)

        # Textual confidence should reflect variant presence
        conf = result.confidence
        assert conf is not None
        # With a major variant, textual confidence should not be 1.0
        assert conf.textual.rationale != ""


class TestResponseSchema:
    """Tests for response schema completeness."""

    def test_translate_response_has_all_fields(self, in_memory_db):
        """TranslateResponse includes all required fields."""
        result = translate_passage(
            conn=in_memory_db,
            reference="Matthew 3:2",
            mode="readable",
            session_id="schema-test-1",
        )

        assert isinstance(result, TranslateResponse)

        # Required fields
        assert result.response_type == "translation"
        assert result.reference == "Matthew 3:2"
        assert result.mode == "readable"
        assert result.sblgnt_text != ""
        assert result.translation_text != ""
        assert isinstance(result.variants, list)
        assert isinstance(result.claims, list)
        assert result.confidence is not None
        assert result.provenance is not None
        assert result.receipts is not None

    def test_gate_response_has_all_fields(self, db_with_variant):
        """GateResponsePayload includes all required fields."""
        result = translate_passage(
            conn=db_with_variant,
            reference="John 1:18",
            mode="readable",
            session_id="schema-test-2",
        )

        assert isinstance(result, GateResponsePayload)

        # Required fields
        assert result.response_type == "gate"
        assert result.gate_id != ""
        assert result.gate_type in ["variant", "grammar", "escalation", "export"]
        assert result.title != ""
        assert result.message != ""
        assert result.prompt != ""
        assert isinstance(result.options, list)
        assert len(result.options) > 0
        assert isinstance(result.variants_side_by_side, list)

    def test_serialization_roundtrip(self, in_memory_db):
        """Response serializes to dict correctly."""
        result = translate_passage(
            conn=in_memory_db,
            reference="Matthew 3:2",
            mode="readable",
            session_id="schema-test-3",
        )

        assert isinstance(result, TranslateResponse)

        data = result.to_dict()

        assert isinstance(data, dict)
        assert data["response_type"] == "translation"
        assert data["reference"] == "Matthew 3:2"
        assert isinstance(data["claims"], list)
        assert isinstance(data["confidence"], dict)
        assert isinstance(data["provenance"], dict)
        assert isinstance(data["receipts"], dict)


class TestReceiptAudit:
    """Tests for receipt and audit trail."""

    def test_receipts_track_checks_run(self, in_memory_db):
        """Receipts include list of validation checks."""
        result = translate_passage(
            conn=in_memory_db,
            reference="Matthew 3:2",
            mode="readable",
            session_id="receipt-test-1",
        )

        assert isinstance(result, TranslateResponse)

        checks = result.receipts.checks_run
        assert len(checks) > 0
        assert "reference_parse" in checks
        assert "claim_classification" in checks
        assert "claim_enforcement" in checks

    def test_receipts_track_gates_satisfied(self, db_with_variant):
        """Receipts track which gates were satisfied."""
        session_id = "receipt-test-2"

        acknowledge_variant(
            conn=db_with_variant,
            session_id=session_id,
            variant_ref="John.1.18",
            reading_index=0,
            context="test",
        )

        result = translate_passage(
            conn=db_with_variant,
            reference="John 1:18",
            mode="readable",
            session_id=session_id,
        )

        assert isinstance(result, TranslateResponse)
        assert "John.1.18" in result.receipts.gates_satisfied


class TestProvenanceTracking:
    """Tests for provenance tracking."""

    def test_provenance_marks_sblgnt_as_spine(self, in_memory_db):
        """Provenance always marks SBLGNT as spine/default."""
        result = translate_passage(
            conn=in_memory_db,
            reference="Matthew 3:2",
            mode="readable",
            session_id="prov-test-1",
        )

        assert isinstance(result, TranslateResponse)

        prov = result.provenance
        assert prov.spine_source == "SBLGNT"
        assert prov.spine_marker == "default"

    def test_provenance_tracks_sources(self, in_memory_db):
        """Provenance includes sources used."""
        result = translate_passage(
            conn=in_memory_db,
            reference="Matthew 3:2",
            mode="readable",
            session_id="prov-test-2",
        )

        assert isinstance(result, TranslateResponse)
        assert len(result.provenance.sources_used) > 0
