"""Acknowledgement state tracking.

Persists user acknowledgements for audit trail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3


@dataclass
class VariantAcknowledgement:
    """Record of a variant acknowledgement."""

    ref: str
    reading_chosen: int
    timestamp: datetime
    context: str
    session_id: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict:
        """Serialize for storage/API."""
        return {
            "ref": self.ref,
            "reading_chosen": self.reading_chosen,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "session_id": self.session_id,
            "notes": self.notes,
        }


@dataclass
class AcknowledgementState:
    """In-memory acknowledgement state for a session."""

    session_id: str
    acknowledged_variants: dict[str, VariantAcknowledgement] = field(
        default_factory=dict
    )
    acknowledged_grammars: dict[str, str] = field(default_factory=dict)
    escalations_accepted: list[str] = field(default_factory=list)

    def has_acknowledged_variant(self, ref: str) -> bool:
        """Check if variant has been acknowledged."""
        return ref in self.acknowledged_variants

    def get_variant_choice(self, ref: str) -> int | None:
        """Get acknowledged reading index for variant."""
        ack = self.acknowledged_variants.get(ref)
        return ack.reading_chosen if ack else None

    def acknowledge_variant(
        self,
        ref: str,
        reading_chosen: int,
        context: str,
        notes: str | None = None,
    ) -> VariantAcknowledgement:
        """Record variant acknowledgement."""
        ack = VariantAcknowledgement(
            ref=ref,
            reading_chosen=reading_chosen,
            timestamp=datetime.now(),
            context=context,
            session_id=self.session_id,
            notes=notes,
        )
        self.acknowledged_variants[ref] = ack
        return ack


ACKNOWLEDGEMENT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS acknowledgements (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    ack_type TEXT NOT NULL,
    ref TEXT NOT NULL,
    choice TEXT NOT NULL,
    context TEXT,
    timestamp TEXT NOT NULL,
    notes TEXT,
    UNIQUE(session_id, ack_type, ref)
);

CREATE INDEX IF NOT EXISTS idx_ack_session ON acknowledgements(session_id);
"""


class AcknowledgementStore:
    """Persistent storage for acknowledgements."""

    def __init__(self, conn: "sqlite3.Connection"):
        """Initialize store with database connection."""
        self._conn = conn

    def init_schema(self) -> None:
        """Initialize acknowledgement table."""
        self._conn.executescript(ACKNOWLEDGEMENT_SCHEMA_SQL)
        self._conn.commit()

    def persist_variant_ack(self, ack: VariantAcknowledgement) -> int:
        """Persist a variant acknowledgement."""
        cursor = self._conn.execute(
            """
            INSERT INTO acknowledgements (session_id, ack_type, ref, choice,
                                         context, timestamp, notes)
            VALUES (?, 'variant', ?, ?, ?, ?, ?)
            ON CONFLICT(session_id, ack_type, ref) DO UPDATE SET
                choice = excluded.choice,
                context = excluded.context,
                timestamp = excluded.timestamp,
                notes = excluded.notes
            RETURNING id
            """,
            (
                ack.session_id,
                ack.ref,
                str(ack.reading_chosen),
                ack.context,
                ack.timestamp.isoformat(),
                ack.notes,
            ),
        )
        result = cursor.fetchone()[0]
        self._conn.commit()
        return result

    def load_session_state(self, session_id: str) -> AcknowledgementState:
        """Load acknowledgement state for a session."""
        state = AcknowledgementState(session_id=session_id)

        cursor = self._conn.execute(
            """
            SELECT ack_type, ref, choice, context, timestamp, notes
            FROM acknowledgements
            WHERE session_id = ?
            """,
            (session_id,),
        )

        for row in cursor:
            ack_type, ref, choice, context, timestamp, notes = row

            if ack_type == "variant":
                state.acknowledged_variants[ref] = VariantAcknowledgement(
                    ref=ref,
                    reading_chosen=int(choice),
                    timestamp=datetime.fromisoformat(timestamp),
                    context=context or "",
                    session_id=session_id,
                    notes=notes,
                )
            elif ack_type == "grammar":
                state.acknowledged_grammars[ref] = choice
            elif ack_type == "escalation":
                state.escalations_accepted.append(ref)

        return state

    def has_variant_ack(self, session_id: str, ref: str) -> bool:
        """Check if variant has been acknowledged in session."""
        cursor = self._conn.execute(
            """
            SELECT 1 FROM acknowledgements
            WHERE session_id = ? AND ack_type = 'variant' AND ref = ?
            """,
            (session_id, ref),
        )
        return cursor.fetchone() is not None

    def get_session_acks(self, session_id: str) -> dict[str, int]:
        """Get all variant acknowledgements for a session.

        Args:
            session_id: Session ID to query

        Returns:
            Dict mapping variant_ref to acknowledged reading index
        """
        cursor = self._conn.execute(
            """
            SELECT ref, choice
            FROM acknowledgements
            WHERE session_id = ? AND ack_type = 'variant'
            """,
            (session_id,),
        )

        return {row[0]: int(row[1]) for row in cursor}
