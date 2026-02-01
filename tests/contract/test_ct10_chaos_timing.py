"""Contract test CT-10: Chaos timing tests per SPRINT-2-DOD.

Tests SSE reconnect under hostile timing conditions:
- Disconnect at random event counts
- Rapid connect/disconnect cycles
- Disconnect during high-frequency event bursts
- Verify Last-Event-ID replay correctness after chaos

These tests probe the spaces between events where reality hides bugs.
"""

from __future__ import annotations

import json
import random
from unittest.mock import patch

import pytest

from redletters.engine_spine.auth import generate_auth_token
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


@pytest.fixture
def patched_auth(tmp_path):
    """Create a test token with patched file storage."""
    token = generate_auth_token()
    token_path = tmp_path / ".auth_token"
    token_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    token_path.write_text(token)
    token_path.chmod(0o600)

    with patch.object(
        __import__("redletters.engine_spine.auth", fromlist=["TOKEN_FILE_PATH"]),
        "TOKEN_FILE_PATH",
        token_path,
    ):
        with patch(
            "redletters.engine_spine.auth._keyring_available",
            return_value=False,
        ):
            import redletters.engine_spine.auth as auth_module

            auth_module._token_storage.clear_cache()
            yield (tmp_path, token)


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
            subsystem="chaos",
            message=f"Event {i}",
        )
        db.persist_event(event, job_id=job_id)
        sequences.append(event.sequence_number)
    return sequences


class TestRandomDisconnect:
    """Tests for disconnect at random event counts."""

    @pytest.mark.asyncio
    async def test_disconnect_at_random_event_count(self, db):
        """Disconnect after random number of events, replay catches up."""
        create_test_job(db, "chaos_job")

        # Emit 20 events
        all_sequences = emit_events(db, "chaos_job", 20)

        # Simulate multiple "sessions" with random disconnect points
        for _ in range(10):
            # Random disconnect point (saw 1-15 events)
            disconnect_after = random.randint(1, 15)
            last_seen = all_sequences[disconnect_after - 1]

            # "Reconnect" with Last-Event-ID
            replayed = db.get_events_since(last_seen, job_id="chaos_job")
            replayed_seqs = [e["sequence"] for e in replayed]

            # Should get exactly the remaining events
            expected = all_sequences[disconnect_after:]
            assert replayed_seqs == expected, (
                f"Disconnect after {disconnect_after}: "
                f"expected {expected}, got {replayed_seqs}"
            )

    @pytest.mark.asyncio
    async def test_disconnect_at_first_event(self, db):
        """Disconnect after seeing only the first event."""
        create_test_job(db, "chaos_job")
        sequences = emit_events(db, "chaos_job", 10)

        # Saw only event 0
        last_seen = sequences[0]
        replayed = db.get_events_since(last_seen, job_id="chaos_job")
        replayed_seqs = [e["sequence"] for e in replayed]

        assert replayed_seqs == sequences[1:]

    @pytest.mark.asyncio
    async def test_disconnect_at_last_event(self, db):
        """Disconnect after seeing the last event (nothing to replay)."""
        create_test_job(db, "chaos_job")
        sequences = emit_events(db, "chaos_job", 10)

        # Saw everything
        last_seen = sequences[-1]
        replayed = db.get_events_since(last_seen, job_id="chaos_job")

        assert replayed == []


class TestRapidReconnect:
    """Tests for rapid connect/disconnect cycles."""

    @pytest.mark.asyncio
    async def test_rapid_reconnect_cycles(self, db):
        """10 rapid reconnects don't corrupt sequence tracking."""
        create_test_job(db, "rapid_job")

        # Emit initial batch (return value intentionally unused - events fetched via DB)
        emit_events(db, "rapid_job", 5)

        # Simulate 10 rapid reconnect cycles
        collected_sequences: list[int] = []
        last_seen = 0

        for cycle in range(10):
            # "Connect" and read events since last_seen
            events = db.get_events_since(last_seen, job_id="rapid_job")

            for e in events:
                seq = e["sequence"]
                if seq not in collected_sequences:
                    collected_sequences.append(seq)
                last_seen = max(last_seen, seq)

            # Emit more events "during connection"
            new_seqs = emit_events(db, "rapid_job", 2)

            # "Disconnect" at random point (may or may not see new events)
            if random.random() > 0.5 and new_seqs:
                # Saw some of the new events
                seen_count = random.randint(1, len(new_seqs))
                last_seen = new_seqs[seen_count - 1]
                collected_sequences.extend(new_seqs[:seen_count])

        # Final "connection" to catch up
        final_events = db.get_events_since(last_seen, job_id="rapid_job")
        for e in final_events:
            seq = e["sequence"]
            if seq not in collected_sequences:
                collected_sequences.append(seq)

        # Verify we collected all events with no duplicates
        all_events = db.get_events_since(0, job_id="rapid_job")
        all_seqs = [e["sequence"] for e in all_events]

        assert sorted(collected_sequences) == sorted(all_seqs)
        assert len(collected_sequences) == len(set(collected_sequences))

    @pytest.mark.asyncio
    async def test_reconnect_same_sequence_repeatedly(self, db):
        """Reconnecting from same Last-Event-ID is idempotent."""
        create_test_job(db, "idempotent_job")
        sequences = emit_events(db, "idempotent_job", 10)

        fixed_point = sequences[4]

        # Reconnect 20 times from same point
        results = []
        for _ in range(20):
            replayed = db.get_events_since(fixed_point, job_id="idempotent_job")
            results.append([e["sequence"] for e in replayed])

        # All results identical
        assert all(r == results[0] for r in results)
        assert results[0] == sequences[5:]


class TestHighFrequencyBursts:
    """Tests for disconnect during high-frequency event bursts."""

    @pytest.mark.asyncio
    async def test_burst_then_disconnect(self, db):
        """High-frequency burst followed by disconnect."""
        create_test_job(db, "burst_job")

        # Burst of 100 events
        burst_seqs = emit_events(db, "burst_job", 100)

        # Disconnect at various points during the burst
        test_points = [10, 25, 50, 75, 90, 99]

        for point in test_points:
            last_seen = burst_seqs[point]
            replayed = db.get_events_since(last_seen, job_id="burst_job")
            replayed_seqs = [e["sequence"] for e in replayed]

            expected = burst_seqs[point + 1 :]
            assert replayed_seqs == expected, (
                f"Disconnect at {point}: expected {len(expected)} events, "
                f"got {len(replayed_seqs)}"
            )

    @pytest.mark.asyncio
    async def test_interleaved_bursts_multiple_jobs(self, db):
        """Interleaved bursts from multiple jobs."""
        create_test_job(db, "job_x")
        create_test_job(db, "job_y")
        create_test_job(db, "job_z")

        # Interleave events from all jobs
        all_global_seqs = []
        job_seqs = {"job_x": [], "job_y": [], "job_z": []}

        for i in range(30):
            for job_id in ["job_x", "job_y", "job_z"]:
                event = JobLog(
                    sequence_number=0,
                    job_id=job_id,
                    job_sequence=0,
                    level=LogLevel.INFO,
                    subsystem="burst",
                    message=f"Event {i}",
                )
                db.persist_event(event, job_id=job_id)
                all_global_seqs.append(event.sequence_number)
                job_seqs[job_id].append(event.sequence_number)

        # Disconnect mid-burst, filter to single job
        for job_id, seqs in job_seqs.items():
            mid_point = seqs[len(seqs) // 2]
            replayed = db.get_events_since(mid_point, job_id=job_id)
            replayed_seqs = [e["sequence"] for e in replayed]

            expected = [s for s in seqs if s > mid_point]
            assert replayed_seqs == expected

    @pytest.mark.asyncio
    async def test_global_sequence_survives_chaos(self, db):
        """Global sequence monotonicity survives chaotic multi-job writes."""
        jobs = [f"chaos_{i}" for i in range(5)]
        for job_id in jobs:
            create_test_job(db, job_id)

        # Chaotic interleaved writes
        for _ in range(50):
            job_id = random.choice(jobs)
            emit_events(db, job_id, random.randint(1, 5))

        # Verify global monotonicity
        all_events = db.get_events_since(0)
        all_seqs = [e["sequence"] for e in all_events]

        # Strictly increasing
        for i in range(1, len(all_seqs)):
            assert all_seqs[i] > all_seqs[i - 1], (
                f"Monotonicity violated at index {i}: "
                f"{all_seqs[i - 1]} -> {all_seqs[i]}"
            )


class TestEdgeCases:
    """Edge cases that hide bugs."""

    @pytest.mark.asyncio
    async def test_reconnect_before_any_events(self, db):
        """Reconnect with Last-Event-ID=0 before any events exist."""
        create_test_job(db, "empty_job")

        # No events yet
        replayed = db.get_events_since(0, job_id="empty_job")
        assert replayed == []

        # Now emit events
        sequences = emit_events(db, "empty_job", 5)

        # Reconnect from 0 gets all
        replayed = db.get_events_since(0, job_id="empty_job")
        assert [e["sequence"] for e in replayed] == sequences

    @pytest.mark.asyncio
    async def test_reconnect_with_future_sequence(self, db):
        """Reconnect with Last-Event-ID higher than any existing event."""
        create_test_job(db, "future_job")
        sequences = emit_events(db, "future_job", 10)

        # Ask for events after a sequence that doesn't exist yet
        future_seq = sequences[-1] + 1000
        replayed = db.get_events_since(future_seq, job_id="future_job")

        assert replayed == []

    @pytest.mark.asyncio
    async def test_sequence_gap_impossible(self, db):
        """Verify the database cannot produce sequence gaps."""
        create_test_job(db, "gap_test")

        # Emit events rapidly
        sequences = emit_events(db, "gap_test", 100)

        # Check for gaps
        for i in range(1, len(sequences)):
            gap = sequences[i] - sequences[i - 1]
            assert gap == 1, f"Gap detected: {sequences[i - 1]} -> {sequences[i]}"

    @pytest.mark.asyncio
    async def test_concurrent_writes_no_duplicate_sequence(self, db):
        """Simulated concurrent writes don't produce duplicate sequences."""
        create_test_job(db, "concurrent_job")

        # Simulate "concurrent" writes (sequential in test, but verifies DB constraint)
        all_seqs = set()
        for _ in range(100):
            event = JobLog(
                sequence_number=0,
                job_id="concurrent_job",
                job_sequence=0,
                level=LogLevel.INFO,
                subsystem="concurrent",
                message="Concurrent event",
            )
            db.persist_event(event, job_id="concurrent_job")

            # Check for duplicate
            assert event.sequence_number not in all_seqs, (
                f"Duplicate sequence: {event.sequence_number}"
            )
            all_seqs.add(event.sequence_number)
