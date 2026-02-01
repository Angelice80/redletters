"""Contract tests for persist-before-send per ADR-003.

This test verifies the mechanical enforcement of persist-before-send:
- Events MUST be persisted to SQLite BEFORE being sent to any SSE connection
- The broadcaster accepts only EventRowId, not raw events
- Every event in SSE stream exists in job_events table
"""

import asyncio
import json

import pytest

from redletters.engine_spine.broadcaster import EventBroadcaster
from redletters.engine_spine.database import EngineDatabase
from redletters.engine_spine.models import (
    EngineHeartbeat,
    EventRowId,
    JobLog,
    JobStateChanged,
    LogLevel,
    JobState,
)


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "engine.db"
    database = EngineDatabase(db_path)
    database.init_schema()
    return database


@pytest.fixture
def broadcaster(db):
    """Create broadcaster."""
    return EventBroadcaster(db)


def create_test_job(db, job_id: str) -> None:
    """Helper to create a test job record for foreign key constraints."""
    db.create_job(
        job_id=job_id,
        config_json=json.dumps({"input_paths": ["/test/path"]}),
        config_hash="testhash",
        input_spec_json=json.dumps({"paths": ["/test/path"]}),
        workspace_path="/tmp/test_workspace",
    )


class TestPersistBeforeSend:
    """Tests for persist-before-send contract."""

    def test_event_persistence_returns_row_id(self, db):
        """persist_event returns EventRowId."""
        event = EngineHeartbeat(
            sequence_number=0,
            uptime_ms=1000,
        )

        row_id = db.persist_event(event)

        assert isinstance(row_id, int)
        assert row_id > 0

    def test_sequence_assigned_in_persistence(self, db):
        """Sequence number is assigned during persistence."""
        event = EngineHeartbeat(
            sequence_number=0,  # Will be overwritten
            uptime_ms=1000,
        )

        db.persist_event(event)

        # Event should now have sequence number assigned
        assert event.sequence_number > 0

    def test_persisted_event_in_database(self, db):
        """Persisted event exists in database."""
        # Create job record first for foreign key
        create_test_job(db, "test_job_123")

        event = JobStateChanged(
            sequence_number=0,
            job_id="test_job_123",
            old_state=None,
            new_state=JobState.QUEUED,
        )

        row_id = db.persist_event(event, job_id="test_job_123")

        # Verify in database
        event_data = db.get_event_by_id(row_id)
        assert event_data is not None
        assert event_data["event"]["job_id"] == "test_job_123"
        assert event_data["event"]["new_state"] == "queued"

    @pytest.mark.asyncio
    async def test_broadcaster_only_accepts_row_id(self, db, broadcaster):
        """Broadcaster only accepts EventRowId, not raw events."""
        event = EngineHeartbeat(
            sequence_number=0,
            uptime_ms=1000,
        )

        # This should fail - cannot broadcast raw event
        # The broadcaster.broadcast_by_id expects an int (EventRowId)
        # SQLite will raise InterfaceError when trying to use Pydantic model as param
        with pytest.raises(Exception) as exc_info:
            await broadcaster.broadcast_by_id(event)  # type: ignore

        # Verify it fails with a type-related error
        assert any(
            s in type(exc_info.value).__name__
            for s in ["TypeError", "ValueError", "InterfaceError"]
        )

    @pytest.mark.asyncio
    async def test_broadcast_requires_persisted_event(self, db, broadcaster):
        """Cannot broadcast event that doesn't exist in DB."""
        # Try to broadcast non-existent event
        with pytest.raises(ValueError):
            await broadcaster.broadcast_by_id(EventRowId(99999))

    @pytest.mark.asyncio
    async def test_broadcast_after_persist_succeeds(self, db, broadcaster):
        """Broadcast succeeds after event is persisted."""
        # Add a connection
        conn = await broadcaster.add_connection()

        # Persist event
        event = EngineHeartbeat(
            sequence_number=0,
            uptime_ms=1000,
        )
        row_id = db.persist_event(event)

        # Broadcast should succeed
        delivered = await broadcaster.broadcast_by_id(row_id)
        assert delivered == 1

        # Connection should have received the event
        assert conn.queue.qsize() == 1

    def test_sequence_numbers_monotonic_increasing(self, db):
        """Sequence numbers are strictly monotonically increasing."""
        sequences = []

        for i in range(10):
            event = EngineHeartbeat(
                sequence_number=0,
                uptime_ms=i * 1000,
            )
            db.persist_event(event)
            sequences.append(event.sequence_number)

        # Verify monotonically increasing
        for i in range(1, len(sequences)):
            assert sequences[i] > sequences[i - 1]

    def test_sequence_numbers_unique(self, db):
        """No duplicate sequence numbers."""
        sequences = []

        for i in range(100):
            event = EngineHeartbeat(
                sequence_number=0,
                uptime_ms=i * 100,
            )
            db.persist_event(event)
            sequences.append(event.sequence_number)

        # All should be unique
        assert len(sequences) == len(set(sequences))

    def test_sequence_assigned_atomically(self, db):
        """Sequence assignment is atomic with persistence."""
        # Create job record first for foreign key
        create_test_job(db, "test_job")

        # Verify the sequence is assigned in the same transaction
        # by checking it's consistent with the stored value
        event = JobLog(
            sequence_number=0,
            job_id="test_job",
            job_sequence=0,
            level=LogLevel.INFO,
            subsystem="test",
            message="Test message",
        )

        row_id = db.persist_event(event, job_id="test_job")

        # Get event from DB
        event_data = db.get_event_by_id(row_id)

        # The sequence in the event should match what's stored
        assert event_data["sequence"] == event.sequence_number


class TestEventReplay:
    """Tests for event replay from database."""

    def test_replay_returns_persisted_events(self, db):
        """Replay returns events that were persisted."""
        # Create job record first
        create_test_job(db, "test_job")

        # Persist some events
        for i in range(5):
            event = JobLog(
                sequence_number=0,
                job_id="test_job",
                job_sequence=0,
                level=LogLevel.INFO,
                subsystem="test",
                message=f"Message {i}",
            )
            db.persist_event(event, job_id="test_job")

        # Replay from beginning
        events = db.get_events_since(0)

        assert len(events) == 5

    def test_replay_respects_sequence_filter(self, db):
        """Replay only returns events after specified sequence."""
        # Create job record first
        create_test_job(db, "test_job")

        # Persist some events
        sequences = []
        for i in range(5):
            event = JobLog(
                sequence_number=0,
                job_id="test_job",
                job_sequence=0,
                level=LogLevel.INFO,
                subsystem="test",
                message=f"Message {i}",
            )
            db.persist_event(event, job_id="test_job")
            sequences.append(event.sequence_number)

        # Replay from middle
        events = db.get_events_since(sequences[2])

        # Should get events after sequence[2]
        assert len(events) == 2  # Events at index 3 and 4

    def test_replay_filters_by_job(self, db):
        """Replay can filter by job_id."""
        # Create job records first
        create_test_job(db, "job_a")
        create_test_job(db, "job_b")

        # Persist events for different jobs
        for i in range(3):
            event = JobLog(
                sequence_number=0,
                job_id="job_a",
                job_sequence=0,
                level=LogLevel.INFO,
                subsystem="test",
                message=f"Job A message {i}",
            )
            db.persist_event(event, job_id="job_a")

        for i in range(2):
            event = JobLog(
                sequence_number=0,
                job_id="job_b",
                job_sequence=0,
                level=LogLevel.INFO,
                subsystem="test",
                message=f"Job B message {i}",
            )
            db.persist_event(event, job_id="job_b")

        # Replay only job_a
        events = db.get_events_since(0, job_id="job_a")

        assert len(events) == 3
        for event_data in events:
            assert event_data["event"]["job_id"] == "job_a"


class TestStreamConsistency:
    """Tests ensuring SSE stream is consistent with database."""

    @pytest.mark.asyncio
    async def test_every_broadcasted_event_in_database(self, db, broadcaster):
        """Every event sent via broadcaster exists in database."""
        # Add connection (connection object unused - side effect registers listener)
        await broadcaster.add_connection()

        # Persist and broadcast multiple events
        event_ids = []
        for i in range(5):
            event = EngineHeartbeat(
                sequence_number=0,
                uptime_ms=i * 1000,
            )
            row_id = db.persist_event(event)
            event_ids.append(row_id)
            await broadcaster.broadcast_by_id(row_id)

        # All events should be in database
        for row_id in event_ids:
            event_data = db.get_event_by_id(row_id)
            assert event_data is not None

    @pytest.mark.asyncio
    async def test_sequence_consistency(self, db, broadcaster):
        """Sequence numbers in broadcast match database."""
        conn = await broadcaster.add_connection()

        # Persist and broadcast
        event = EngineHeartbeat(
            sequence_number=0,
            uptime_ms=1000,
        )
        row_id = db.persist_event(event)
        await broadcaster.broadcast_by_id(row_id)

        # Get event from connection queue
        received = await asyncio.wait_for(conn.queue.get(), timeout=1.0)

        # Get event from database
        db_event = db.get_event_by_id(row_id)

        # Sequences should match
        assert received["sequence_number"] == db_event["sequence"]
