"""Contract test CT-12: Load tests per SPRINT-2-DOD.

Tests multiple concurrent clients don't break reconnect semantics:
- Multiple clients connect simultaneously
- Clients disconnect/reconnect while others stay connected
- Burst of reconnects (stress sequencing and replay)

These tests verify the system handles concurrent load correctly.
"""

from __future__ import annotations

import asyncio
import json
import random

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
            subsystem="load",
            message=f"Event {i}",
        )
        db.persist_event(event, job_id=job_id)
        sequences.append(event.sequence_number)
    return sequences


class TestSimultaneousClients:
    """Tests for multiple simultaneous client connections."""

    @pytest.mark.asyncio
    async def test_ten_clients_connect_simultaneously(self, db):
        """10 clients connecting at once all receive events."""
        create_test_job(db, "load_job")

        # Emit events
        all_seqs = emit_events(db, "load_job", 100)

        # Simulate 10 clients reading simultaneously
        async def client_read(client_id: int) -> list[int]:
            # Each client reads all events
            events = db.get_events_since(0, job_id="load_job")
            return [e["sequence"] for e in events]

        # Run all clients concurrently
        results = await asyncio.gather(*[client_read(i) for i in range(10)])

        # All clients should get same complete data
        for i, result in enumerate(results):
            assert result == all_seqs, f"Client {i} got incomplete data"

    @pytest.mark.asyncio
    async def test_clients_at_different_offsets(self, db):
        """Clients at different Last-Event-ID offsets all work."""
        create_test_job(db, "offset_job")
        all_seqs = emit_events(db, "offset_job", 100)

        # 10 clients at random offsets
        async def client_read(offset_index: int) -> tuple[int, list[int]]:
            if offset_index == 0:
                last_seen = 0
            else:
                last_seen = all_seqs[offset_index - 1]
            events = db.get_events_since(last_seen, job_id="offset_job")
            return offset_index, [e["sequence"] for e in events]

        offsets = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
        results = await asyncio.gather(*[client_read(o) for o in offsets])

        for offset, seqs in results:
            expected = all_seqs[offset:]
            assert seqs == expected, f"Client at offset {offset} failed"


class TestReconnectWhileOthersConnected:
    """Tests for clients reconnecting while others remain connected."""

    @pytest.mark.asyncio
    async def test_half_disconnect_half_stay(self, db):
        """5 clients disconnect/reconnect while 5 stay connected."""
        create_test_job(db, "mixed_job")

        # Initial events
        batch1 = emit_events(db, "mixed_job", 50)

        # 5 "connected" clients read all of batch1
        connected_states = {}
        for i in range(5):
            events = db.get_events_since(0, job_id="mixed_job")
            connected_states[f"connected_{i}"] = {
                "last_seen": events[-1]["sequence"],
                "collected": [e["sequence"] for e in events],
            }

        # 5 "disconnected" clients only saw first 25
        disconnected_states = {}
        for i in range(5):
            disconnected_states[f"disconnected_{i}"] = {
                "last_seen": batch1[24],
                "collected": batch1[:25],
            }

        # More events arrive
        batch2 = emit_events(db, "mixed_job", 50)

        # Connected clients continue reading
        for client_id, state in connected_states.items():
            new_events = db.get_events_since(state["last_seen"], job_id="mixed_job")
            state["collected"].extend(e["sequence"] for e in new_events)
            if new_events:
                state["last_seen"] = new_events[-1]["sequence"]

        # Disconnected clients "reconnect" with their last_seen
        for client_id, state in disconnected_states.items():
            catch_up = db.get_events_since(state["last_seen"], job_id="mixed_job")
            state["collected"].extend(e["sequence"] for e in catch_up)

        # All clients should have same complete data
        expected = batch1 + batch2
        for client_id, state in connected_states.items():
            assert state["collected"] == expected, f"{client_id} incomplete"
        for client_id, state in disconnected_states.items():
            assert state["collected"] == expected, f"{client_id} incomplete"


class TestBurstReconnect:
    """Tests for burst of rapid reconnections."""

    @pytest.mark.asyncio
    async def test_burst_of_50_reconnects(self, db):
        """50 rapid reconnects all reach consistent state."""
        create_test_job(db, "burst_job")

        # Emit events
        all_seqs = emit_events(db, "burst_job", 200)

        # 50 "clients" reconnect from random positions
        async def reconnect_client(client_id: int) -> tuple[int, list[int]]:
            # Random starting position
            if client_id == 0:
                last_seen = 0
            else:
                pos = random.randint(0, len(all_seqs) - 1)
                last_seen = all_seqs[pos]

            events = db.get_events_since(last_seen, job_id="burst_job")
            return client_id, [e["sequence"] for e in events]

        # All reconnect simultaneously
        results = await asyncio.gather(*[reconnect_client(i) for i in range(50)])

        # Each client should have gotten correct events from their position
        for client_id, seqs in results:
            # Verify sequences are valid (subset of all_seqs, in order)
            for seq in seqs:
                assert seq in all_seqs, f"Client {client_id} got invalid seq {seq}"

            # Verify order
            if seqs:
                for i in range(1, len(seqs)):
                    assert seqs[i] > seqs[i - 1], f"Client {client_id} out of order"

    @pytest.mark.asyncio
    async def test_all_clients_eventually_consistent(self, db):
        """All clients eventually see the same complete stream."""
        create_test_job(db, "consistent_job")

        # Producer writes events
        all_seqs = emit_events(db, "consistent_job", 100)

        # 20 clients at random positions
        client_positions = {i: random.randint(0, 99) for i in range(20)}

        # Each client catches up to current
        client_final_states = {}

        for client_id, start_pos in client_positions.items():
            if start_pos == 0:
                last_seen = 0
            else:
                last_seen = all_seqs[start_pos - 1]

            events = db.get_events_since(last_seen, job_id="consistent_job")
            # Full state would be events before position + caught up events
            full_state = all_seqs[:start_pos] + [e["sequence"] for e in events]
            client_final_states[client_id] = full_state

        # All should have complete data
        for client_id, state in client_final_states.items():
            assert sorted(state) == all_seqs, f"Client {client_id} inconsistent"


class TestConcurrentWriteAndRead:
    """Tests for concurrent write and read operations."""

    @pytest.mark.asyncio
    async def test_reads_during_writes(self, db):
        """Reads during writes see consistent state."""
        create_test_job(db, "concurrent_job")

        # Write some events
        batch1 = emit_events(db, "concurrent_job", 50)

        # Read
        read1 = db.get_events_since(0, job_id="concurrent_job")
        read1_seqs = [e["sequence"] for e in read1]
        assert read1_seqs == batch1

        # More writes
        batch2 = emit_events(db, "concurrent_job", 50)

        # Read again
        read2 = db.get_events_since(read1_seqs[-1], job_id="concurrent_job")
        read2_seqs = [e["sequence"] for e in read2]
        assert read2_seqs == batch2

        # Full read
        full = db.get_events_since(0, job_id="concurrent_job")
        full_seqs = [e["sequence"] for e in full]
        assert full_seqs == batch1 + batch2

    @pytest.mark.asyncio
    async def test_interleaved_jobs_under_load(self, db):
        """Multiple jobs interleaved under load maintain correct filtering."""
        jobs = [f"job_{i}" for i in range(5)]
        for job_id in jobs:
            create_test_job(db, job_id)

        # Interleave events from all jobs
        job_seqs = {job_id: [] for job_id in jobs}
        for _ in range(20):
            for job_id in jobs:
                seqs = emit_events(db, job_id, 5)
                job_seqs[job_id].extend(seqs)

        # Each job filter returns only that job's events
        for job_id, expected in job_seqs.items():
            events = db.get_events_since(0, job_id=job_id)
            got = [e["sequence"] for e in events]
            assert got == expected, f"Job {job_id} filter failed"

        # Global read gets all events in order
        all_events = db.get_events_since(0)
        all_seqs = [e["sequence"] for e in all_events]

        # Should be strictly increasing
        for i in range(1, len(all_seqs)):
            assert all_seqs[i] > all_seqs[i - 1]

        # Count should be 5 jobs * 20 rounds * 5 events = 500
        assert len(all_seqs) == 500


class TestStressSequencing:
    """Stress tests for sequence number correctness."""

    @pytest.mark.asyncio
    async def test_high_volume_no_duplicates(self, db):
        """High volume writes produce no duplicate sequences."""
        create_test_job(db, "volume_job")

        # 1000 events
        all_seqs = emit_events(db, "volume_job", 1000)

        # No duplicates
        assert len(all_seqs) == len(set(all_seqs))

        # Strictly increasing
        for i in range(1, len(all_seqs)):
            assert all_seqs[i] == all_seqs[i - 1] + 1

    @pytest.mark.asyncio
    async def test_parallel_reads_same_result(self, db):
        """Parallel reads at same position return identical results."""
        create_test_job(db, "parallel_job")
        all_seqs = emit_events(db, "parallel_job", 100)

        fixed_position = all_seqs[49]

        async def read_from_position() -> list[int]:
            events = db.get_events_since(fixed_position, job_id="parallel_job")
            return [e["sequence"] for e in events]

        # 20 parallel reads
        results = await asyncio.gather(*[read_from_position() for _ in range(20)])

        # All identical
        expected = all_seqs[50:]
        for result in results:
            assert result == expected
