"""Tests for acknowledgement gating.

Tests ADR-008 gate mechanism.
"""

import sqlite3
import pytest
from datetime import datetime

from redletters.claims.taxonomy import (
    ClaimType,
    Claim,
    TextSpan,
    ClaimDependency,
    VariantDependency,
    GrammarDependency,
)
from redletters.gates.detector import GateDetector, GateTrigger
from redletters.gates.checkpoint import Gate, GateResponse, GateType, GateCheckpoint
from redletters.gates.state import (
    AcknowledgementState,
    VariantAcknowledgement,
    AcknowledgementStore,
)


@pytest.fixture
def span():
    """Create default text span."""
    return TextSpan(book="John", chapter=1, verse_start=18)


@pytest.fixture
def in_memory_db():
    """Create in-memory SQLite database."""
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()


class TestGateDetector:
    """Tests for gate trigger detection."""

    def test_detect_variant_dependency(self, span):
        """Should detect variant dependency in claim."""
        detector = GateDetector()

        deps = ClaimDependency(
            variants=[
                VariantDependency(
                    variant_unit_ref="John.1.18",
                    reading_chosen=0,
                    rationale="P66/P75 support",
                )
            ]
        )
        claim = Claim(
            claim_type=ClaimType.TYPE4_THEOLOGICAL,
            text_span=span,
            content="This refers to Christ as God.",
            dependencies=deps,
        )

        result = detector.detect_for_claim(claim)

        assert result.gate_required
        assert GateTrigger.VARIANT_DEPENDENCY in result.triggers
        assert "John.1.18" in result.variant_refs

    def test_detect_grammar_ambiguity(self, span):
        """Should detect grammar ambiguity trigger."""
        detector = GateDetector()

        deps = ClaimDependency(
            grammar=[
                GrammarDependency(
                    token_ref="John.1.18.3",
                    parse_choice="subjective genitive",
                    alternatives=["objective genitive"],
                )
            ]
        )
        claim = Claim(
            claim_type=ClaimType.TYPE2_GRAMMATICAL,
            text_span=span,
            content="This is a subjective genitive.",
            dependencies=deps,
        )

        result = detector.detect_for_claim(claim)

        assert result.gate_required
        assert GateTrigger.GRAMMAR_AMBIGUITY in result.triggers

    def test_detect_escalation_requirement(self, span):
        """Should detect when claim requires mode escalation."""
        detector = GateDetector()

        claim = Claim(
            claim_type=ClaimType.TYPE5_MORAL,
            text_span=span,
            content="Christians must believe this.",
        )

        result = detector.detect_for_claim(claim, current_mode="readable")

        assert result.gate_required
        assert GateTrigger.CLAIM_ESCALATION in result.triggers
        assert result.escalation_required
        assert result.target_mode == "traceable"

    def test_no_gate_for_simple_claim(self, span):
        """Should not trigger gate for simple descriptive claim."""
        detector = GateDetector()

        claim = Claim(
            claim_type=ClaimType.TYPE0_DESCRIPTIVE,
            text_span=span,
            content="This word is a noun.",
        )

        result = detector.detect_for_claim(claim)

        assert not result.gate_required

    def test_detection_result_serialization(self, span):
        """Should serialize detection result."""
        detector = GateDetector()

        deps = ClaimDependency(
            variants=[
                VariantDependency(
                    variant_unit_ref="John.1.18",
                    reading_chosen=0,
                    rationale="Test",
                )
            ]
        )
        claim = Claim(
            claim_type=ClaimType.TYPE4_THEOLOGICAL,
            text_span=span,
            content="Test claim.",
            dependencies=deps,
        )

        result = detector.detect_for_claim(claim)
        d = result.to_dict()

        assert d["gate_required"]
        assert "variant_dependency" in d["triggers"]


class TestGateCreation:
    """Tests for gate creation."""

    def test_create_variant_gate(self):
        """Should create variant acknowledgement gate."""
        readings = [
            {"surface_text": "μονογενὴς θεός", "witnesses": ["P66", "P75", "א", "B"]},
            {"surface_text": "ὁ μονογενὴς υἱός", "witnesses": ["A", "C³", "Byz"]},
        ]

        gate = Gate.for_variant("John.1.18", readings, sblgnt_index=0)

        assert gate.gate_type == GateType.VARIANT
        assert gate.trigger == GateTrigger.VARIANT_DEPENDENCY
        assert gate.ref == "John.1.18"
        assert len(gate.options) == 3  # 2 readings + "view full"
        assert gate.options[0].is_default  # SBLGNT reading

    def test_create_escalation_gate(self):
        """Should create escalation gate."""
        gate = Gate.for_escalation(
            claim_type_label="Moral",
            from_mode="readable",
            to_mode="traceable",
        )

        assert gate.gate_type == GateType.ESCALATION
        assert gate.trigger == GateTrigger.CLAIM_ESCALATION
        assert "Moral" in gate.message
        assert len(gate.options) == 3  # switch, rewrite, cancel
        assert gate.options[0].is_default  # switch mode

    def test_gate_serialization(self):
        """Should serialize gate for UI."""
        readings = [
            {"surface_text": "θεός", "witnesses": ["P66"]},
        ]
        gate = Gate.for_variant("John.1.18", readings)

        d = gate.to_dict()

        assert "gate_id" in d
        assert d["gate_type"] == "variant"
        assert "options" in d


class TestGateCheckpoint:
    """Tests for gate validation."""

    def test_validate_acknowledged_response(self):
        """Should accept acknowledged response with valid option."""
        readings = [
            {"surface_text": "θεός", "witnesses": ["P66"]},
        ]
        gate = Gate.for_variant("John.1.18", readings)

        response = GateResponse(
            gate_id=gate.gate_id,
            option_selected="reading_0",
            acknowledged=True,
        )

        checkpoint = GateCheckpoint()
        assert checkpoint.validate_response(gate, response)

    def test_reject_unacknowledged_response(self):
        """Should reject unacknowledged response."""
        readings = [
            {"surface_text": "θεός", "witnesses": ["P66"]},
        ]
        gate = Gate.for_variant("John.1.18", readings)

        response = GateResponse(
            gate_id=gate.gate_id,
            option_selected="reading_0",
            acknowledged=False,  # Not acknowledged
        )

        checkpoint = GateCheckpoint()
        assert not checkpoint.validate_response(gate, response)

    def test_reject_cancel_option(self):
        """Should reject cancel option."""
        gate = Gate.for_escalation("Moral", "readable", "traceable")

        response = GateResponse(
            gate_id=gate.gate_id,
            option_selected="cancel",
            acknowledged=True,
        )

        checkpoint = GateCheckpoint()
        assert not checkpoint.validate_response(gate, response)

    def test_reject_invalid_option(self):
        """Should reject invalid option selection."""
        readings = [
            {"surface_text": "θεός", "witnesses": ["P66"]},
        ]
        gate = Gate.for_variant("John.1.18", readings)

        response = GateResponse(
            gate_id=gate.gate_id,
            option_selected="invalid_option",
            acknowledged=True,
        )

        checkpoint = GateCheckpoint()
        assert not checkpoint.validate_response(gate, response)

    def test_reject_mismatched_gate_id(self):
        """Should reject response with wrong gate ID."""
        readings = [
            {"surface_text": "θεός", "witnesses": ["P66"]},
        ]
        gate = Gate.for_variant("John.1.18", readings)

        response = GateResponse(
            gate_id="wrong_gate_id",
            option_selected="reading_0",
            acknowledged=True,
        )

        checkpoint = GateCheckpoint()
        assert not checkpoint.validate_response(gate, response)


class TestAcknowledgementState:
    """Tests for in-memory acknowledgement state."""

    def test_acknowledge_variant(self):
        """Should track variant acknowledgement."""
        state = AcknowledgementState(session_id="test-session")

        assert not state.has_acknowledged_variant("John.1.18")

        ack = state.acknowledge_variant(
            ref="John.1.18",
            reading_chosen=0,
            context="Creating theological claim",
        )

        assert state.has_acknowledged_variant("John.1.18")
        assert state.get_variant_choice("John.1.18") == 0
        assert ack.session_id == "test-session"

    def test_no_acknowledgement(self):
        """Should return None for unacknowledged variants."""
        state = AcknowledgementState(session_id="test-session")

        assert state.get_variant_choice("John.1.18") is None


class TestAcknowledgementStore:
    """Tests for persistent acknowledgement storage."""

    def test_persist_and_load_variant_ack(self, in_memory_db):
        """Should persist and load variant acknowledgement."""
        store = AcknowledgementStore(in_memory_db)
        store.init_schema()

        ack = VariantAcknowledgement(
            ref="John.1.18",
            reading_chosen=0,
            timestamp=datetime.now(),
            context="Creating theological claim",
            session_id="test-session",
        )

        ack_id = store.persist_variant_ack(ack)
        assert ack_id > 0

        # Load session state
        state = store.load_session_state("test-session")

        assert state.has_acknowledged_variant("John.1.18")
        assert state.get_variant_choice("John.1.18") == 0

    def test_has_variant_ack_check(self, in_memory_db):
        """Should check for existing acknowledgement."""
        store = AcknowledgementStore(in_memory_db)
        store.init_schema()

        assert not store.has_variant_ack("test-session", "John.1.18")

        ack = VariantAcknowledgement(
            ref="John.1.18",
            reading_chosen=0,
            timestamp=datetime.now(),
            context="Test",
            session_id="test-session",
        )
        store.persist_variant_ack(ack)

        assert store.has_variant_ack("test-session", "John.1.18")
        assert not store.has_variant_ack("other-session", "John.1.18")

    def test_update_existing_ack(self, in_memory_db):
        """Should update existing acknowledgement on conflict."""
        store = AcknowledgementStore(in_memory_db)
        store.init_schema()

        # First ack
        ack1 = VariantAcknowledgement(
            ref="John.1.18",
            reading_chosen=0,
            timestamp=datetime.now(),
            context="First context",
            session_id="test-session",
        )
        store.persist_variant_ack(ack1)

        # Update with different choice
        ack2 = VariantAcknowledgement(
            ref="John.1.18",
            reading_chosen=1,  # Changed
            timestamp=datetime.now(),
            context="Updated context",
            session_id="test-session",
        )
        store.persist_variant_ack(ack2)

        # Should have updated value
        state = store.load_session_state("test-session")
        assert state.get_variant_choice("John.1.18") == 1

    def test_load_empty_session(self, in_memory_db):
        """Should return empty state for unknown session."""
        store = AcknowledgementStore(in_memory_db)
        store.init_schema()

        state = store.load_session_state("unknown-session")

        assert state.session_id == "unknown-session"
        assert len(state.acknowledged_variants) == 0
