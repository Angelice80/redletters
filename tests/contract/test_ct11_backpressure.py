"""Contract test CT-11: Backpressure / slow consumer tests per SPRINT-2-DOD.

Tests SSE handles slow consumers without data loss:
- Consumer pauses mid-stream (events buffered)
- Consumer reads slowly (no loss)
- Multiple slow consumers (all receive events)

These tests verify the server doesn't drop events when consumers lag.
"""

from __future__ import annotations

import json

import pytest

from redletters.engine_spine.database import EngineDatabase
from redletters.engine_spine.models import JobLog, LogLevel
from redletters.engine_spine.status import EngineState


@pytest.fixture(autouse=True)
def reset_engine_state():
    """Reset engine state singleton between tests."""
    yield
    EngineState.get_instance().reset()


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "engine.db"
    database = EngineDatabase(db_path)
    database.init_schema()
    return database


def create_test_job(db, job_id: str) -> None:
    """Helper to create a test job record."""
    db.create_job(
        job_id=job_id,
        config_json=json.dumps({"input_paths": ["/test/path"]}),
        config_hash="testhash",
        input_spec_json=json.dumps({"paths": ["/test/path"]}),
        workspace_path="/tmp/test_workspace",
    )


def emit_events(db, job_id: str, count: int) -> list[int]:
    """Emit N events and return their sequence numbers."""
    sequences = []
    for i in range(count):
        event = JobLog(
            sequence_number=0,
            job_id=job_id,
            job_sequence=0,
            level=LogLevel.INFO,
            subsystem="backpressure",
            message=f"Event {i}",
        )
        db.persist_event(event, job_id=job_id)
        sequences.append(event.sequence_number)
    return sequences


class TestSlowConsumer:
    """Tests for slow consumer scenarios."""

    @pytest.mark.asyncio
    async def test_consumer_pauses_mid_stream(self, db):
        """Consumer pauses, more events arrive, consumer resumes."""
        create_test_job(db, "pause_job")

        # Initial events
        batch1 = emit_events(db, "pause_job", 10)

        # Consumer reads first 5
        events = db.get_events_since(0, job_id="pause_job")
        consumer_seqs = [e["sequence"] for e in events[:5]]
        last_seen = consumer_seqs[-1]

        # "Pause" - more events arrive while consumer is paused
        batch2 = emit_events(db, "pause_job", 20)

        # Consumer "resumes" with Last-Event-ID
        resumed = db.get_events_since(last_seen, job_id="pause_job")
        resumed_seqs = [e["sequence"] for e in resumed]

        # Should get remaining from batch1 + all of batch2
        expected = batch1[5:] + batch2
        assert resumed_seqs == expected

    @pytest.mark.asyncio
    async def test_consumer_reads_slowly(self, db):
        """Consumer reads one event at a time, events keep arriving."""
        create_test_job(db, "slow_job")

        # Producer emits events
        all_seqs = emit_events(db, "slow_job", 50)

        # Slow consumer reads one at a time
        collected = []
        last_seen = 0

        for _ in range(len(all_seqs)):
            # Get one event
            events = db.get_events_since(last_seen, job_id="slow_job", limit=1)
            if not events:
                break
            collected.append(events[0]["sequence"])
            last_seen = events[0]["sequence"]

        assert collected == all_seqs

    @pytest.mark.asyncio
    async def test_consumer_catches_up_after_long_pause(self, db):
        """Consumer catches up correctly after extended pause."""
        create_test_job(db, "catchup_job")

        # Emit events
        batch1 = emit_events(db, "catchup_job", 10)

        # Consumer sees first event only
        last_seen = batch1[0]

        # Long "pause" - many more events arrive
        batch2 = emit_events(db, "catchup_job", 100)
        batch3 = emit_events(db, "catchup_job", 100)

        # Consumer catches up
        caught_up = db.get_events_since(last_seen, job_id="catchup_job")
        caught_up_seqs = [e["sequence"] for e in caught_up]

        expected = batch1[1:] + batch2 + batch3
        assert caught_up_seqs == expected
        assert len(caught_up_seqs) == 209  # 9 + 100 + 100


class TestMultipleSlowConsumers:
    """Tests for multiple consumers at different speeds."""

    @pytest.mark.asyncio
    async def test_multiple_consumers_different_rates(self, db):
        """Multiple consumers at different read rates all get complete data."""
        create_test_job(db, "multi_job")

        # Emit events
        all_seqs = emit_events(db, "multi_job", 30)

        # Consumer A: fast (reads all at once)
        consumer_a = db.get_events_since(0, job_id="multi_job")
        a_seqs = [e["sequence"] for e in consumer_a]

        # Consumer B: medium (reads in batches of 10)
        b_seqs = []
        b_last = 0
        while True:
            batch = db.get_events_since(b_last, job_id="multi_job", limit=10)
            if not batch:
                break
            b_seqs.extend(e["sequence"] for e in batch)
            b_last = batch[-1]["sequence"]

        # Consumer C: slow (reads one at a time)
        c_seqs = []
        c_last = 0
        for _ in range(100):  # safety limit
            events = db.get_events_since(c_last, job_id="multi_job", limit=1)
            if not events:
                break
            c_seqs.append(events[0]["sequence"])
            c_last = events[0]["sequence"]

        # All consumers should have same complete data
        assert a_seqs == all_seqs
        assert b_seqs == all_seqs
        assert c_seqs == all_seqs

    @pytest.mark.asyncio
    async def test_consumers_at_different_positions(self, db):
        """Consumers at different Last-Event-ID positions all work correctly."""
        create_test_job(db, "position_job")

        # Emit events
        all_seqs = emit_events(db, "position_job", 50)

        # 5 consumers at different positions
        positions = [0, 10, 25, 40, 49]

        for pos in positions:
            last_seen = all_seqs[pos] if pos > 0 else 0
            if pos == 0:
                # Position 0 means start from beginning
                last_seen = 0
                expected = all_seqs
            else:
                last_seen = all_seqs[pos - 1]
                expected = all_seqs[pos:]

            events = db.get_events_since(last_seen, job_id="position_job")
            got = [e["sequence"] for e in events]

            # Adjust expected for pos=0 case
            if pos == 0:
                expected = all_seqs

            assert got == expected, f"Consumer at position {pos} failed"


class TestBufferBehavior:
    """Tests for event buffering behavior."""

    @pytest.mark.asyncio
    async def test_events_persisted_before_read(self, db):
        """Events are persisted before any consumer reads them."""
        create_test_job(db, "persist_job")

        # Emit events
        seqs = emit_events(db, "persist_job", 20)

        # Immediate read should get all events
        events = db.get_events_since(0, job_id="persist_job")
        assert len(events) == 20
        assert [e["sequence"] for e in events] == seqs

    @pytest.mark.asyncio
    async def test_no_events_lost_under_rapid_writes(self, db):
        """Rapid event writes don't lose any events."""
        create_test_job(db, "rapid_job")

        # Rapid writes
        all_seqs = []
        for _ in range(10):
            batch = emit_events(db, "rapid_job", 50)
            all_seqs.extend(batch)

        # Read all
        events = db.get_events_since(0, job_id="rapid_job")
        got_seqs = [e["sequence"] for e in events]

        assert got_seqs == all_seqs
        assert len(got_seqs) == 500

    @pytest.mark.asyncio
    async def test_late_consumer_gets_full_history(self, db):
        """Consumer that connects late gets full event history."""
        create_test_job(db, "late_job")

        # Producer writes many events
        batch1 = emit_events(db, "late_job", 100)
        batch2 = emit_events(db, "late_job", 100)
        batch3 = emit_events(db, "late_job", 100)

        # "Late" consumer connects now
        events = db.get_events_since(0, job_id="late_job")
        got_seqs = [e["sequence"] for e in events]

        expected = batch1 + batch2 + batch3
        assert got_seqs == expected
        assert len(got_seqs) == 300


class TestReplayLimit:
    """Tests for replay with limit parameter."""

    @pytest.mark.asyncio
    async def test_limit_respects_order(self, db):
        """Limit returns oldest events first."""
        create_test_job(db, "limit_job")
        seqs = emit_events(db, "limit_job", 100)

        # Get first 10
        events = db.get_events_since(0, job_id="limit_job", limit=10)
        got = [e["sequence"] for e in events]

        assert got == seqs[:10]

    @pytest.mark.asyncio
    async def test_paginated_reads(self, db):
        """Paginated reads reconstruct full stream."""
        create_test_job(db, "paginate_job")
        all_seqs = emit_events(db, "paginate_job", 100)

        # Read in pages of 15
        collected = []
        last_seen = 0
        page_size = 15

        while True:
            page = db.get_events_since(
                last_seen, job_id="paginate_job", limit=page_size
            )
            if not page:
                break
            collected.extend(e["sequence"] for e in page)
            last_seen = page[-1]["sequence"]

        assert collected == all_seqs
