# STORY-010: Stream Replay & Ordering Contract Tests

**Epic**: Desktop App Architecture
**ADRs**: ADR-003 (Delivery Semantics)
**Priority**: P0 (Without this, production will be haunted)
**Depends On**: STORY-002 (SSE Streaming)
**Estimate**: 1.5 days

---

## User Story

**As a** developer maintaining the event stream,
**I want** contract tests that verify ordering and replay guarantees,
**So that** I can refactor with confidence and catch regressions before production.

---

## Acceptance Criteria

### AC-1: Sequence Monotonicity Tests
- [ ] Test: sequence_number always increases (no decreases)
- [ ] Test: no duplicate sequence_numbers in a stream
- [ ] Test: sequence persists across engine restarts
- [ ] Test: sequence advances even for heartbeats

### AC-2: Resume from Last-Event-ID Tests
- [ ] Test: `Last-Event-ID: N` returns events starting from N+1
- [ ] Test: Resume works after disconnect
- [ ] Test: Resume returns replayed events THEN live events
- [ ] Test: Resume with invalid ID returns error (not silent skip)

### AC-3: Resume via Query Parameter Tests
- [ ] Test: `?resume_from=N` equivalent to Last-Event-ID
- [ ] Test: `?resume_from=N&job_id=X` filters by job
- [ ] Test: Resume from very old sequence returns summary (not all events)

### AC-4: Gap Detection Tests
- [ ] Test: Client receives out-of-order events (reordering works)
- [ ] Test: Client detects gap and requests replay
- [ ] Test: Gap larger than threshold triggers warning

### AC-5: Duplicate Handling Tests
- [ ] Test: Same event delivered twice (replay scenario)
- [ ] Test: Client deduplicates by sequence_number
- [ ] Test: Dedupe set doesn't grow unbounded (pruning works)

### AC-6: At-Least-Once Semantics Tests
- [ ] Test: Event written to DB before sent to stream
- [ ] Test: Event in stream implies event in DB (for replay)
- [ ] Test: No events lost during engine shutdown

### AC-7: GUI Reboot Mid-Run (CT-07)
- [ ] Test: Full scenario covering the real-world "user closes laptop" case
- [ ] Sequence: Start job → receive N events → kill client → wait → reconnect → verify
- [ ] Verify: No gaps in event sequence
- [ ] Verify: No duplicate events after dedupe
- [ ] Verify: Correct final receipt once job completes
- [ ] Verify: Job state in GUI matches engine state

### AC-8: Engine Restart Mid-Run (CT-08)
- [ ] Test: Full scenario covering the "engine crashes during job" case
- [ ] Sequence: Start job → receive 20 events → kill engine process → restart engine → GUI reconnects → verify
- [ ] Verify: Job state transitions to `failed` (v1 behavior: fail fast, no resume)
- [ ] Verify: Receipt reflects crash (`exit_code: E_ENGINE_CRASH`)
- [ ] Verify: No event ordering violations (sequence continues from DB)
- [ ] Verify: GUI can create new job after reconnect
- [ ] Document: Explicit decision that v1 does NOT resume crashed jobs

> **Design Decision**: For v1, crashed jobs fail fast with clear error. True job resumption
> (checkpointing, partial progress recovery) is a v2 feature. This test verifies we fail honestly.

---

## Technical Design

### Test Fixtures

```python
import pytest
import asyncio
import httpx
from httpx_sse import aconnect_sse

@pytest.fixture
async def engine():
    """Start engine for testing."""
    proc = await start_test_engine()
    yield proc
    await stop_test_engine(proc)

@pytest.fixture
async def client(engine):
    """HTTP client with auth token."""
    async with httpx.AsyncClient(base_url="http://127.0.0.1:47200") as client:
        client.headers["Authorization"] = f"Bearer {get_test_token()}"
        yield client

@pytest.fixture
async def stream_client(client):
    """SSE stream client."""
    async def connect(resume_from: int | None = None):
        url = "/v1/stream"
        if resume_from:
            url += f"?resume_from={resume_from}"
        return await aconnect_sse(client, "GET", url)
    return connect
```

### Monotonicity Tests

```python
@pytest.mark.asyncio
async def test_sequence_always_increases(stream_client):
    """Sequence numbers must be monotonically increasing."""
    events = []
    async with await stream_client() as stream:
        async for event in stream.aiter_sse():
            events.append(json.loads(event.data))
            if len(events) >= 10:
                break

    sequences = [e["sequence_number"] for e in events]
    assert sequences == sorted(sequences), "Sequence not monotonic"
    assert len(sequences) == len(set(sequences)), "Duplicate sequences"


@pytest.mark.asyncio
async def test_sequence_persists_across_restart(engine, stream_client):
    """Sequence continues after engine restart."""
    # Get current sequence
    async with await stream_client() as stream:
        event = await anext(stream.aiter_sse())
        seq_before = json.loads(event.data)["sequence_number"]

    # Restart engine
    await restart_engine(engine)

    # Get new sequence
    async with await stream_client() as stream:
        event = await anext(stream.aiter_sse())
        seq_after = json.loads(event.data)["sequence_number"]

    assert seq_after > seq_before, "Sequence did not persist across restart"
```

### Resume Tests

```python
@pytest.mark.asyncio
async def test_resume_from_last_event_id(stream_client, client):
    """Resume returns events after Last-Event-ID."""
    # Create some events
    await create_test_job(client)

    # Collect events
    events = []
    async with await stream_client() as stream:
        async for event in stream.aiter_sse():
            events.append(json.loads(event.data))
            if len(events) >= 5:
                break

    # Resume from middle
    resume_point = events[2]["sequence_number"]
    resumed_events = []

    async with await stream_client(resume_from=resume_point) as stream:
        async for event in stream.aiter_sse():
            resumed_events.append(json.loads(event.data))
            if len(resumed_events) >= 3:
                break

    # Verify we got events after resume point
    assert all(e["sequence_number"] > resume_point for e in resumed_events)


@pytest.mark.asyncio
async def test_resume_invalid_sequence_returns_error(stream_client):
    """Resume from future sequence returns error, not silent skip."""
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        async with await stream_client(resume_from=999999999) as stream:
            await anext(stream.aiter_sse())

    assert exc_info.value.response.status_code == 400
```

### Duplicate Handling Tests

```python
@pytest.mark.asyncio
async def test_client_deduplicates_by_sequence(stream_client):
    """Client-side dedupe handles replayed events."""

    class DeduplicatingConsumer:
        def __init__(self):
            self.seen = set()
            self.events = []

        def consume(self, event: dict):
            seq = event["sequence_number"]
            if seq in self.seen:
                return False  # Duplicate
            self.seen.add(seq)
            self.events.append(event)
            return True

    consumer = DeduplicatingConsumer()

    # Connect, get some events
    async with await stream_client() as stream:
        async for event in stream.aiter_sse():
            consumer.consume(json.loads(event.data))
            if len(consumer.events) >= 5:
                break

    # Reconnect with resume (will replay some events)
    resume_point = consumer.events[0]["sequence_number"]

    async with await stream_client(resume_from=resume_point) as stream:
        async for event in stream.aiter_sse():
            was_new = consumer.consume(json.loads(event.data))
            # First few should be duplicates
            if len(consumer.events) >= 8:
                break

    # Verify no duplicate sequences in final list
    sequences = [e["sequence_number"] for e in consumer.events]
    assert len(sequences) == len(set(sequences))
```

### At-Least-Once Semantics Tests

```python
@pytest.mark.asyncio
async def test_event_persisted_before_sent(client, stream_client):
    """Events are in DB before (or as) they're sent to stream."""
    events_received = []

    async def collect_events():
        async with await stream_client() as stream:
            async for event in stream.aiter_sse():
                data = json.loads(event.data)
                events_received.append(data)
                if len(events_received) >= 10:
                    break

    # Start collecting in background
    collect_task = asyncio.create_task(collect_events())

    # Create a job (generates events)
    await create_test_job(client)

    await collect_task

    # Verify all received events are in database
    for event in events_received:
        db_event = await get_event_from_db(event["sequence_number"])
        assert db_event is not None, f"Event {event['sequence_number']} not in DB"


@pytest.mark.asyncio
async def test_no_events_lost_during_shutdown(engine, stream_client, client):
    """Graceful shutdown doesn't lose pending events."""
    # Start a job
    job = await create_test_job(client)

    # Collect events
    events_before_shutdown = []
    async with await stream_client() as stream:
        async for event in stream.aiter_sse():
            events_before_shutdown.append(json.loads(event.data))
            if len(events_before_shutdown) >= 3:
                break

    last_seq = events_before_shutdown[-1]["sequence_number"]

    # Shutdown gracefully
    await client.post("/v1/engine/shutdown")
    await wait_for_shutdown(engine)

    # Restart
    await start_engine()

    # Resume from last known
    events_after_restart = []
    async with await stream_client(resume_from=last_seq) as stream:
        async for event in stream.aiter_sse():
            events_after_restart.append(json.loads(event.data))
            if len(events_after_restart) >= 3:
                break

    # Should have events after last_seq (no gap)
    assert all(e["sequence_number"] > last_seq for e in events_after_restart)
```

### CT-07: GUI Reboot Mid-Run (The Nasty One)

```python
@pytest.mark.asyncio
@pytest.mark.contract
async def test_ct07_gui_reboot_mid_run(engine, client, stream_client):
    """
    CT-07: The real-world "user closes laptop" scenario.

    This is the test that catches "works on my machine" before it ships.
    """
    # Phase 1: Start job and collect some events
    job_response = await client.post("/v1/jobs", json={
        "inputs": [{"type": "reference", "reference": "Luke 1-5"}],
        "config": {"format": "json"}
    })
    job_id = job_response.json()["job_id"]

    events_before_disconnect = []
    async with await stream_client() as stream:
        async for event in stream.aiter_sse():
            data = json.loads(event.data)
            events_before_disconnect.append(data)
            # Collect enough to have meaningful progress
            if len(events_before_disconnect) >= 20:
                break

    last_seen_seq = events_before_disconnect[-1]["sequence_number"]
    print(f"[CT-07] Collected {len(events_before_disconnect)} events, last seq: {last_seen_seq}")

    # Phase 2: Simulate GUI crash (just disconnect, don't send any cleanup)
    # Connection is already closed by exiting the context manager
    print("[CT-07] GUI disconnected (simulating crash)")

    # Phase 3: Wait (job continues running on engine)
    await asyncio.sleep(10)  # Let job make progress
    print("[CT-07] Waited 10 seconds while job ran headless")

    # Phase 4: Reconnect with Last-Event-ID
    events_after_reconnect = []
    seen_sequences = {e["sequence_number"] for e in events_before_disconnect}
    duplicates = []

    async with await stream_client(resume_from=last_seen_seq) as stream:
        async for event in stream.aiter_sse():
            data = json.loads(event.data)
            seq = data["sequence_number"]

            # Track duplicates (shouldn't happen after dedupe, but let's verify)
            if seq in seen_sequences:
                duplicates.append(seq)
            else:
                seen_sequences.add(seq)
                events_after_reconnect.append(data)

            # Wait for job completion or timeout
            if data.get("event_type") == "job.state_changed" and data.get("new_state") in ("completed", "failed"):
                break
            if len(events_after_reconnect) >= 100:  # Safety limit
                break

    print(f"[CT-07] Received {len(events_after_reconnect)} new events after reconnect")
    print(f"[CT-07] Duplicates received (before client dedupe): {len(duplicates)}")

    # Phase 5: Verify no gaps
    all_sequences = sorted(seen_sequences)
    gaps = []
    for i in range(1, len(all_sequences)):
        if all_sequences[i] != all_sequences[i-1] + 1:
            gaps.append((all_sequences[i-1], all_sequences[i]))

    assert len(gaps) == 0, f"Sequence gaps detected: {gaps}"
    print(f"[CT-07] ✓ No gaps in sequence (total events: {len(all_sequences)})")

    # Phase 6: Verify job state
    job_detail = await client.get(f"/v1/jobs/{job_id}")
    job_state = job_detail.json()["state"]
    assert job_state in ("completed", "failed", "running"), f"Unexpected state: {job_state}"
    print(f"[CT-07] ✓ Job state: {job_state}")

    # Phase 7: If completed, verify receipt
    if job_state == "completed":
        receipt_response = await client.get(f"/v1/jobs/{job_id}/receipt")
        assert receipt_response.status_code == 200
        receipt = receipt_response.json()

        assert receipt["job_id"] == job_id
        assert receipt["receipt_status"] == "final"
        assert "receipt_hash" in receipt
        print(f"[CT-07] ✓ Receipt verified: {receipt['receipt_hash'][:20]}...")

    print("[CT-07] ✓ ALL CHECKS PASSED")
```

### CT-08: Engine Restart Mid-Run (The Sibling)

```python
@pytest.mark.asyncio
@pytest.mark.contract
async def test_ct08_engine_restart_mid_run(engine, client, stream_client):
    """
    CT-08: The "engine dies while job running" scenario.

    v1 Behavior: Fail fast. Crashed jobs → failed state with clear error.
    This test verifies we fail HONESTLY (no phantom success, no limbo state).
    """
    # Phase 1: Start job and collect some events
    job_response = await client.post("/v1/jobs", json={
        "inputs": [{"type": "reference", "reference": "Luke 1-5"}],
        "config": {"format": "json"}
    })
    job_id = job_response.json()["job_id"]

    events_before_crash = []
    last_seq = 0
    async with await stream_client() as stream:
        async for event in stream.aiter_sse():
            data = json.loads(event.data)
            events_before_crash.append(data)
            last_seq = data["sequence_number"]
            # Collect enough to be mid-run
            if len(events_before_crash) >= 20:
                break

    print(f"[CT-08] Collected {len(events_before_crash)} events, last seq: {last_seq}")

    # Phase 2: Kill engine process (simulating crash)
    engine_pid = await get_engine_pid()
    print(f"[CT-08] Killing engine process {engine_pid}")
    os.kill(engine_pid, signal.SIGKILL)  # Hard kill, no cleanup

    # Wait for process to die
    await asyncio.sleep(2)

    # Phase 3: Restart engine
    print("[CT-08] Restarting engine")
    new_engine = await start_test_engine()

    # Give engine time to run recovery
    await asyncio.sleep(3)

    # Phase 4: Verify job state (should be failed)
    async with httpx.AsyncClient(base_url="http://127.0.0.1:47200") as new_client:
        new_client.headers["Authorization"] = f"Bearer {get_test_token()}"

        job_detail = await new_client.get(f"/v1/jobs/{job_id}")
        assert job_detail.status_code == 200
        job = job_detail.json()

        assert job["state"] == "failed", f"Expected 'failed', got '{job['state']}'"
        assert job["error_code"] == "E_ENGINE_CRASH", f"Wrong error code: {job['error_code']}"
        print(f"[CT-08] ✓ Job correctly marked as failed: {job['error_code']}")

    # Phase 5: Verify sequence continuity
    async with await stream_client(resume_from=last_seq) as stream:
        event = await anext(stream.aiter_sse())
        data = json.loads(event.data)
        new_seq = data["sequence_number"]

        # Sequence should continue from where DB left off (no regression)
        assert new_seq > last_seq, f"Sequence regression: {new_seq} <= {last_seq}"
        print(f"[CT-08] ✓ Sequence continued: {last_seq} → {new_seq}")

    # Phase 6: Verify we can create new job (system is healthy)
    new_job_response = await new_client.post("/v1/jobs", json={
        "inputs": [{"type": "reference", "reference": "John 1"}],
        "config": {"format": "json"}
    })
    assert new_job_response.status_code == 201
    print(f"[CT-08] ✓ New job created successfully: {new_job_response.json()['job_id']}")

    # Phase 7: Verify receipt exists for crashed job
    receipt_response = await new_client.get(f"/v1/jobs/{job_id}/receipt")
    if receipt_response.status_code == 200:
        receipt = receipt_response.json()
        assert receipt["receipt_status"] == "crash"
        assert "crash" in receipt.get("error", {}).get("code", "").lower() or \
               receipt.get("exit_code") == "E_ENGINE_CRASH"
        print(f"[CT-08] ✓ Crash receipt generated")
    else:
        # Acceptable: no receipt for crash (partial receipts are optional in v1)
        print(f"[CT-08] ℹ No receipt for crashed job (acceptable in v1)")

    print("[CT-08] ✓ ALL CHECKS PASSED")

    # Cleanup
    await stop_test_engine(new_engine)
```

### Files Changed/Created

- `tests/integration/test_stream_ordering.py` — Ordering tests
- `tests/integration/test_stream_replay.py` — Replay tests
- `tests/integration/test_stream_semantics.py` — At-least-once tests
- `tests/integration/conftest.py` — Test fixtures

---

## Test Plan

This story IS the test plan. All tests listed in Technical Design must pass.

Additional meta-tests:
| Test | Type | Description |
|------|------|-------------|
| `test_all_contract_tests_exist` | Meta | Verify all ACs have corresponding tests |
| `test_contract_tests_run_in_ci` | CI | These tests are in CI pipeline |

---

---

## Test Stability Requirements

### Deterministic Clocking

All timeouts MUST be configurable via environment variables for CI tuning:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ENGINE_HEARTBEAT_MS` | 3000 | Heartbeat interval |
| `CLAIM_TIMEOUT_MS` | 30000 | Worker claim timeout |
| `QUEUE_HEARTBEAT_MS` | 10000 | Queue position heartbeat |
| `TEST_EVENT_WAIT_MS` | 500 | Test event collection timeout |
| `TEST_RECONNECT_DELAY_MS` | 1000 | Delay before reconnect in tests |

```python
# tests/conftest.py
import os

HEARTBEAT_MS = int(os.environ.get("ENGINE_HEARTBEAT_MS", 3000))
CLAIM_TIMEOUT_MS = int(os.environ.get("CLAIM_TIMEOUT_MS", 30000))
# ... etc
```

### Flake Budget

**Rule**: If CT-07 or CT-08 fails once, CI reruns automatically once. If it fails twice, PR is blocked.

```yaml
# .github/workflows/contract-tests.yml
- name: Run contract tests (with retry)
  uses: nick-fields/retry@v2
  with:
    timeout_minutes: 10
    max_attempts: 2
    command: pytest tests/contract/ -v --tb=short
```

**Rationale**: If tests are flaky, humans will disable them. If humans can disable them, they will. Not because they're evil—because deadlines exist.

### CI Resource Discipline

**Rule**: CT-07 and CT-08 run serially on a single worker to avoid port contention.

```yaml
jobs:
  contract-tests:
    runs-on: ubuntu-latest
    # No matrix strategy - single worker
    steps:
      - name: Run contract tests serially
        run: pytest tests/contract/ -v --tb=short -x  # -x stops on first failure
```

**No parallel test execution** for contract tests. Integration tests that touch the same port (47200) will race.

---

## Definition of Done

- [ ] All acceptance criteria have corresponding tests
- [ ] All tests pass
- [ ] Tests run in CI pipeline
- [ ] Tests documented as "contract tests" (not to be deleted lightly)
- [ ] README updated with "how to run contract tests"
- [ ] Any test failure blocks PR merge
- [ ] All timeouts configurable via environment variables
- [ ] Flake retry (max 2 attempts) configured in CI
- [ ] Contract tests run serially (no parallel workers)
