"""Tests for export friction (v0.8.0).

Tests the PendingGatesError and check_pending_gates() functionality.
"""

from __future__ import annotations

import sqlite3

import pytest

from redletters.export import PendingGatesError, PendingGate
from redletters.export.apparatus import check_pending_gates, raise_if_pending_gates
from redletters.variants.store import VariantStore
from redletters.variants.models import (
    VariantUnit,
    VariantClassification,
    SignificanceLevel,
    WitnessReading,
)
from redletters.gates.state import AcknowledgementStore


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


class TestPendingGateDataclass:
    """Test PendingGate dataclass."""

    def test_pending_gate_fields(self):
        """PendingGate stores all required fields."""
        pg = PendingGate(
            variant_ref="John.1.18",
            significance="significant",
            spine_reading="μονογενὴς θεός",
            readings_count=2,
        )
        assert pg.variant_ref == "John.1.18"
        assert pg.significance == "significant"
        assert pg.spine_reading == "μονογενὴς θεός"
        assert pg.readings_count == 2


class TestPendingGatesError:
    """Test PendingGatesError exception."""

    def test_error_message_format(self):
        """Error message includes count and references."""
        error = PendingGatesError(
            reference="John.1",
            session_id="test-session",
            pending_gates=[
                PendingGate(
                    variant_ref="John.1.18",
                    significance="significant",
                    spine_reading="test",
                    readings_count=2,
                ),
            ],
        )
        msg = str(error)
        assert "1 pending gate" in msg
        assert "John.1.18" in msg
        assert "--force" in msg

    def test_to_dict_includes_all_fields(self):
        """to_dict() includes all necessary fields."""
        error = PendingGatesError(
            reference="John.1",
            session_id="test-session",
            pending_gates=[
                PendingGate(
                    variant_ref="John.1.18",
                    significance="significant",
                    spine_reading="test",
                    readings_count=2,
                ),
            ],
        )
        d = error.to_dict()
        assert d["error"] == "pending_gates"
        assert d["reference"] == "John.1"
        assert d["session_id"] == "test-session"
        assert d["pending_count"] == 1
        assert len(d["pending_gates"]) == 1
        assert d["pending_gates"][0]["variant_ref"] == "John.1.18"

    def test_to_dict_includes_instructions(self):
        """to_dict() includes helpful instructions."""
        error = PendingGatesError(
            reference="John.1",
            session_id="test-session",
            pending_gates=[],
        )
        d = error.to_dict()
        assert "instructions" in d
        assert len(d["instructions"]) > 0


class TestCheckPendingGates:
    """Test check_pending_gates() function."""

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

    def test_no_variants_returns_empty(self, in_memory_db, variant_store):
        """No variants means no pending gates."""
        pending = check_pending_gates(
            in_memory_db, "John.1.18", "test-session", variant_store
        )
        assert pending == []

    def test_trivial_variant_not_pending(self, in_memory_db, variant_store):
        """Trivial variants don't create pending gates."""
        self._add_variant(variant_store, "John.1.18", SignificanceLevel.TRIVIAL)
        pending = check_pending_gates(
            in_memory_db, "John.1.18", "test-session", variant_store
        )
        assert pending == []

    def test_minor_variant_not_pending(self, in_memory_db, variant_store):
        """Minor variants don't create pending gates."""
        self._add_variant(variant_store, "John.1.18", SignificanceLevel.MINOR)
        pending = check_pending_gates(
            in_memory_db, "John.1.18", "test-session", variant_store
        )
        assert pending == []

    def test_significant_variant_is_pending(self, in_memory_db, variant_store):
        """Significant variants create pending gates."""
        self._add_variant(variant_store, "John.1.18", SignificanceLevel.SIGNIFICANT)
        pending = check_pending_gates(
            in_memory_db, "John.1.18", "test-session", variant_store
        )
        assert len(pending) == 1
        assert pending[0].variant_ref == "John.1.18"
        assert pending[0].significance == "significant"

    def test_major_variant_is_pending(self, in_memory_db, variant_store):
        """Major variants create pending gates."""
        self._add_variant(variant_store, "John.1.18", SignificanceLevel.MAJOR)
        pending = check_pending_gates(
            in_memory_db, "John.1.18", "test-session", variant_store
        )
        assert len(pending) == 1
        assert pending[0].significance == "major"

    def test_acknowledged_variant_not_pending(
        self, in_memory_db, variant_store, ack_store
    ):
        """Acknowledged variants are not pending."""
        self._add_variant(variant_store, "John.1.18", SignificanceLevel.SIGNIFICANT)
        # Acknowledge the variant
        from redletters.gates.state import VariantAcknowledgement
        from datetime import datetime

        ack = VariantAcknowledgement(
            ref="John.1.18",
            reading_chosen=0,
            timestamp=datetime.now(),
            context="test",
            session_id="test-session",
        )
        ack_store.persist_variant_ack(ack)

        pending = check_pending_gates(
            in_memory_db, "John.1.18", "test-session", variant_store
        )
        assert pending == []

    def test_different_session_still_pending(
        self, in_memory_db, variant_store, ack_store
    ):
        """Acknowledgement in different session doesn't clear gate."""
        self._add_variant(variant_store, "John.1.18", SignificanceLevel.SIGNIFICANT)
        # Acknowledge in different session
        from redletters.gates.state import VariantAcknowledgement
        from datetime import datetime

        ack = VariantAcknowledgement(
            ref="John.1.18",
            reading_chosen=0,
            timestamp=datetime.now(),
            context="test",
            session_id="other-session",
        )
        ack_store.persist_variant_ack(ack)

        pending = check_pending_gates(
            in_memory_db, "John.1.18", "test-session", variant_store
        )
        assert len(pending) == 1


class TestRaiseIfPendingGates:
    """Test raise_if_pending_gates() function."""

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

    def test_no_pending_gates_doesnt_raise(self, in_memory_db, variant_store):
        """No pending gates doesn't raise."""
        # Should not raise
        raise_if_pending_gates(in_memory_db, "John.1.18", "test-session", variant_store)

    def test_pending_gates_raises(self, in_memory_db, variant_store):
        """Pending gates raises PendingGatesError."""
        self._add_variant(variant_store, "John.1.18", SignificanceLevel.SIGNIFICANT)
        with pytest.raises(PendingGatesError) as exc_info:
            raise_if_pending_gates(
                in_memory_db, "John.1.18", "test-session", variant_store
            )
        assert exc_info.value.reference == "John.1.18"
        assert len(exc_info.value.pending_gates) == 1


class TestExportFrictionFlow:
    """Test the complete export friction flow."""

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

    def test_blocked_then_acknowledged_then_export(
        self, in_memory_db, variant_store, ack_store
    ):
        """Full flow: blocked -> ack -> export succeeds."""
        self._add_variant(variant_store, "John.1.18", SignificanceLevel.SIGNIFICANT)

        # First check - should have pending gates
        pending = check_pending_gates(
            in_memory_db, "John.1.18", "test-session", variant_store
        )
        assert len(pending) == 1

        # Acknowledge
        from redletters.gates.state import VariantAcknowledgement
        from datetime import datetime

        ack = VariantAcknowledgement(
            ref="John.1.18",
            reading_chosen=0,
            timestamp=datetime.now(),
            context="test",
            session_id="test-session",
        )
        ack_store.persist_variant_ack(ack)

        # Second check - should be clear
        pending = check_pending_gates(
            in_memory_db, "John.1.18", "test-session", variant_store
        )
        assert pending == []
