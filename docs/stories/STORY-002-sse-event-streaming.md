# STORY-002: SSE Event Streaming

**Epic**: Desktop App Architecture
**ADRs**: ADR-003
**Priority**: P0 (Foundation)
**Depends On**: STORY-001 (Engine Service Lifecycle)
**Estimate**: 2 days

---

## User Story

**As a** GUI developer,
**I want** real-time event streaming from the engine,
**So that** I can display live logs, progress, and health updates.

---

## Acceptance Criteria

### AC-1: SSE Endpoint
- [ ] `GET /v1/stream` returns `text/event-stream`
- [ ] Connection stays open indefinitely
- [ ] Events formatted per SSE spec (event type, id, data)

### AC-2: Heartbeat Events
- [ ] Engine emits `engine.heartbeat` every 3 seconds
- [ ] Heartbeat includes: `uptime_ms`, `health`, `active_jobs`, `queue_depth`
- [ ] Heartbeat never skips sequence numbers

### AC-3: Sequence Numbers
- [ ] Every event has monotonically increasing `sequence_number`
- [ ] Sequence persists across connections (stored in database)
- [ ] `id:` field in SSE matches sequence number

### AC-4: Reconnection with Replay
- [ ] Client can send `Last-Event-ID` header
- [ ] Client can use `?resume_from=<seq>` query parameter
- [ ] Engine replays missed events from database
- [ ] Seamless transition from replay to live stream

### AC-5: Event Schema
- [ ] All events include: `event_type`, `sequence_number`, `timestamp_utc`
- [ ] Job events include: `job_id`, `job_sequence`
- [ ] Events are valid JSON

---

## Technical Design

### Event Types

```python
# Engine events
EngineHeartbeat = {
    "event_type": "engine.heartbeat",
    "sequence_number": 1,
    "timestamp_utc": "2024-01-15T14:30:00Z",
    "uptime_ms": 9234567,
    "health": "healthy",
    "active_jobs": 1,
    "queue_depth": 2
}

EngineShuttingDown = {
    "event_type": "engine.shutting_down",
    "sequence_number": 100,
    "timestamp_utc": "2024-01-15T14:35:00Z",
    "reason": "user_request",
    "grace_period_ms": 30000
}

# Job events (future stories will emit these)
JobProgress = {
    "event_type": "job.progress",
    "sequence_number": 50,
    "job_id": "job_123",
    "job_sequence": 10,
    ...
}
```

### SSE Format

```
event: engine.heartbeat
id: 1
data: {"event_type":"engine.heartbeat","sequence_number":1,...}

event: engine.heartbeat
id: 2
data: {"event_type":"engine.heartbeat","sequence_number":2,...}
```

### Replay Logic

```python
@app.get("/v1/stream")
async def stream(
    resume_from: int | None = Query(None),
    request: Request
):
    # Check Last-Event-ID header
    last_id = request.headers.get("Last-Event-ID")
    if last_id:
        resume_from = int(last_id)

    async def event_generator():
        # Replay missed events
        if resume_from:
            async for event in replay_from_db(resume_from):
                yield format_sse(event)

        # Switch to live stream
        async for event in live_events():
            yield format_sse(event)

    return EventSourceResponse(event_generator())
```

### Files Changed/Created

- `src/redletters/engine/streaming.py` — SSE endpoint and event generator
- `src/redletters/engine/events.py` — Event types and formatting
- `src/redletters/engine/sequence.py` — Sequence number management
- `src/redletters/engine/heartbeat.py` — Heartbeat task

---

## Test Plan

| Test | Type | Description |
|------|------|-------------|
| `test_stream_returns_event_stream` | Integration | Content-Type header |
| `test_heartbeat_emitted_every_3s` | Integration | Timing verification |
| `test_sequence_numbers_monotonic` | Unit | No gaps, no duplicates |
| `test_resume_from_replays_missed` | Integration | Disconnect/reconnect |
| `test_last_event_id_header_works` | Integration | SSE standard header |

---

## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Tests written and passing
- [ ] Can connect with `curl` and see heartbeats
- [ ] Can disconnect, reconnect with resume, see replayed events
- [ ] No memory leaks on long-running connections
