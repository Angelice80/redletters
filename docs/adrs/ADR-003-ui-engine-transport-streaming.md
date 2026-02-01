# ADR-003: UI↔Engine Transport & Streaming

**Status**: Accepted
**Date**: 2026-01-27
**Context**: Desktop GUI Architecture (Phase 5)
**Supersedes**: None
**Related**: ADR-001 (CLI-first architecture), Desktop App UX Spec

---

## Context

The Red Letters desktop application requires reliable, real-time communication between:
- **GUI** (Tauri/React frontend): User-facing cockpit
- **Engine** (Python/FastAPI daemon): Long-running processing backend

Requirements from Desktop Spec:
1. Real-time log streaming during job execution
2. Progress updates with sub-second latency
3. Reconnection after GUI close/reopen
4. Event replay for logs missed during disconnect
5. Heartbeat monitoring for engine health

## Decision

### Transport: HTTP/1.1 on 127.0.0.1

**Choice**: All communication via HTTP on localhost, port 47200.

```
┌─────────────┐     HTTP/1.1      ┌─────────────┐
│   Tauri     │◄────────────────►│   FastAPI   │
│   (GUI)     │  127.0.0.1:47200 │  (Engine)   │
└─────────────┘                   └─────────────┘
```

**Rationale**:
- **Simplicity**: HTTP is well-understood, debuggable, toolable
- **Firewall-friendly**: No special port forwarding concerns
- **Process isolation**: GUI and engine can restart independently
- **Compatibility**: Works on all platforms without special permissions

### Streaming: Server-Sent Events (SSE)

**Choice**: SSE for all event streaming (logs, progress, heartbeat).

**Endpoint**: `GET /v1/stream`

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

event: engine.heartbeat
id: 1
data: {"event_type":"engine.heartbeat","sequence_number":1,...}

event: job.log
id: 2
data: {"event_type":"job.log","sequence_number":2,"job_id":"...","message":"..."}
```

**Rationale**:
- **One-way sufficiency**: GUI only receives events; commands go via REST
- **Browser-native**: EventSource API, automatic reconnection built-in
- **Simpler than WebSockets**: No handshake upgrade, no ping/pong management
- **HTTP/1.1 compatible**: Works through all proxies (though we're localhost-only)

---

## Ordering Guarantees

### Sequence Numbers

Every event carries a `sequence_number`:
- **Global sequence**: Engine-wide, monotonically increasing
- **Per-job sequence**: Used for log ordering within a job

```json
{
  "event_type": "job.log",
  "sequence_number": 42,
  "job_sequence": 15,
  "job_id": "job_20240115_143000_a3f8",
  "timestamp_utc": "2024-01-15T14:30:01.234Z",
  "message": "Processing chapter 15"
}
```

### Client-Side Ordering

GUI MUST:
1. Buffer events in a priority queue keyed by sequence_number
2. Process events in order, even if received out-of-order
3. Detect gaps (missing sequence numbers) and request replay

### Gap Detection

If GUI receives sequence 45 after 42, it:
1. Buffers 45
2. Waits 500ms for 43-44 to arrive
3. If timeout: requests replay from 43 via `/v1/stream?resume_from=43`

---

## Reconnect Semantics

### Last-Event-ID Protocol

SSE standard: client sends `Last-Event-ID` header on reconnect.

```
GET /v1/stream HTTP/1.1
Last-Event-ID: 42
```

Engine responds with events starting from sequence 43.

### Replay via Query Parameter

Alternative for explicit replay requests:

```
GET /v1/stream?resume_from=42&job_id=job_20240115_143000_a3f8
```

Returns:
1. All events with sequence_number > 42
2. Filtered to specified job_id if provided
3. Seamlessly transitions to live stream after replay

### Replay Limits

| Scenario | Behavior |
|----------|----------|
| Events in SQLite | Full replay from database |
| Events older than 24h | Summarized (count + first/last) |
| Sequence gap too large (>10000) | Return error, suggest full refresh |

### Reconnection Timing

```
Attempt 1: Immediate
Attempt 2: 1 second delay
Attempt 3: 2 seconds delay
Attempt 4: 4 seconds delay
...
Max delay: 30 seconds
```

GUI shows "Reconnecting..." after 3 failed attempts.

---

## Delivery Semantics

### At-Least-Once Delivery

**Choice**: Events are delivered at-least-once, not exactly-once.

**Rationale**:
- Exactly-once requires distributed transactions (overkill for local app)
- At-least-once is achievable with SQLite persistence + replay
- Duplicates are cheap to handle; lost events are expensive

### Duplicate Handling (GUI Responsibility)

GUI MUST deduplicate by `sequence_number`:

```typescript
const seenSequences = new Set<number>();

function handleEvent(event: StreamEvent) {
  if (seenSequences.has(event.sequence_number)) {
    return; // Duplicate, skip
  }
  seenSequences.add(event.sequence_number);

  // Prune old sequences to avoid memory leak (keep last 50,000)
  if (seenSequences.size > 50000) {
    const sorted = [...seenSequences].sort((a, b) => a - b);
    sorted.slice(0, 10000).forEach(s => seenSequences.delete(s));
  }

  processEvent(event);
}
```

### Ordering Contract

| Guarantee | Scope | Notes |
|-----------|-------|-------|
| Monotonic sequence | Global | sequence_number always increases |
| No gaps (steady state) | Per-connection | Gaps trigger replay |
| Gaps during replay | Expected | Client buffers and reorders |
| Ordering within job | Per-job | Use job_sequence for log order |

### What This Means in Practice

1. **Normal operation**: Events arrive in order, no duplicates
2. **Reconnection**: Replay may include events already seen → dedupe
3. **Network hiccup**: Rare out-of-order → client reorders via buffer
4. **Crash recovery**: Engine restarts → client reconnects, replays from last known

---

## Persist-Before-Send (Mechanical Enforcement)

### The Rule

**Events MUST be persisted to SQLite BEFORE being sent to any SSE connection.**

This is not a policy. It is enforced mechanically in code.

### Implementation Constraint

The event broadcaster does NOT accept raw event objects. It accepts **persisted event row IDs**.

```python
# WRONG - allows "optimization" that breaks guarantees
async def emit_event(event: BaseEvent):
    await broadcast(event)          # ← Sent before persisted
    await db.insert(event)          # ← Too late

# WRONG - sequence assigned outside transaction
async def emit_event(event: BaseEvent):
    event.sequence_number = get_next_sequence()  # ← Race condition
    await db.insert(event)
    await broadcast(event)

# CORRECT - transaction-bound sequence + persist-before-send
async def emit_event(event: BaseEvent) -> int:
    async with db.transaction():
        # Sequence assigned INSIDE transaction (atomic)
        row_id = await db.execute("""
            INSERT INTO job_events (event_type, payload, sequence_number)
            VALUES (?, ?, (SELECT COALESCE(MAX(sequence_number), 0) + 1 FROM job_events))
            RETURNING id, sequence_number
        """, event.event_type, event.to_json())

        event_id, sequence = row_id

    # AFTER commit: broadcast with the persisted row reference
    await broadcaster.send_by_id(event_id)
    return sequence
```

### Why This Matters

1. **No phantom events**: If broadcast fails, event still exists in DB for replay
2. **No sequence gaps**: Sequence assigned atomically in transaction
3. **No race conditions**: Two concurrent events cannot get the same sequence
4. **Auditable**: Every broadcasted event has a DB row; every DB row can be replayed

### Enforcement Points

| Layer | Enforcement |
|-------|-------------|
| Code review | Event emission MUST go through `emit_event()` |
| Type system | Broadcaster accepts `EventRowId`, not `BaseEvent` |
| Tests | Contract test: every event in stream exists in DB |
| Linting | Static analysis flag on direct broadcast calls |

### What "Optimization" Would Break

Future developer thinks: "We can skip DB write for heartbeats."

Result:
- GUI receives heartbeat sequence 100
- Engine crashes before DB write
- Engine restarts, next event is sequence 99 (from DB)
- GUI sees sequence decrease → gap detection → chaos

**Solution**: Even heartbeats go through persist-before-send.

---

## Backpressure

### Problem

If GUI falls behind (slow rendering, paused tab), events accumulate.

### Strategy: Ring Buffer + Persistence

**Engine-side**: Two-tier buffering.

```
┌─────────────────────────────────────────────────────┐
│ TIER 1: In-memory ring buffer (per connection)     │
│ - Size: 10,000 events                              │
│ - Overflow: Disconnect client (they can replay)    │
└─────────────────────────────────────────────────────┘
                        │
                        │ All events also written to:
                        ▼
┌─────────────────────────────────────────────────────┐
│ TIER 2: SQLite persistence (job_events table)      │
│ - Size: Retention-limited (24h/7d/permanent)       │
│ - Overflow: Pruned by retention policy             │
└─────────────────────────────────────────────────────┘
```

**Critical**: We NEVER drop events silently. Options on overflow:
1. Disconnect client → they reconnect and replay from SQLite
2. If SQLite is the bottleneck → batched writes (see ADR-004)

### Engine-Side Limits

| Buffer | Limit | On Overflow | Recovery |
|--------|-------|-------------|----------|
| Per-connection ring | 10,000 events | Disconnect client | Client reconnects, replays |
| SQLite write queue | 1,000 events | Batch flush | Automatic |
| SQLite storage | Per retention policy | Prune oldest | Expected behavior |

### Client-Side Handling

GUI maintains local buffer:
1. Max 5,000 events in memory
2. Virtualized list rendering (only visible rows in DOM)
3. "Pause" mode stops auto-scroll, keeps buffering (up to 10,000)
4. Beyond 10,000: show "X events skipped" summary with link to full logs

### Chunked Replay

For large replays, engine sends events in chunks:
```
event: replay.chunk
data: {"events": [...1000 events...], "has_more": true}

event: replay.chunk
data: {"events": [...500 events...], "has_more": false}

event: replay.complete
data: {"replayed_count": 1500, "now_live": true}
```

### Why Not Drop?

**Dropping is dangerous** for a "receipt-grade" system:
- Dropped log might contain the error that explains a failure
- User trusts receipts → can't silently omit data
- Storage is cheap; lost trust is expensive

---

## Why Not WebSockets (Yet)

### WebSockets Advantages (Theoretical)

1. Full-duplex (but we don't need it)
2. Lower latency (marginal for our use case)
3. Binary support (we use JSON)

### Why SSE Wins for Red Letters

| Factor | SSE | WebSocket |
|--------|-----|-----------|
| Complexity | Lower | Higher |
| Reconnection | Automatic (EventSource) | Manual |
| Debugging | Curl-friendly | Requires wscat |
| Firewall | HTTP-native | May need configuration |
| Tauri support | Native fetch | Needs websocket crate |
| Error handling | HTTP status codes | Custom protocol |

### When We'd Reconsider WebSockets

1. **Bi-directional streaming**: If GUI needed to stream data TO engine
2. **High-frequency updates**: Sub-100ms latency requirements
3. **Large binary payloads**: If we streamed audio/video

None of these apply to Red Letters. SSE is the right tool.

### Migration Path

If future needs require WebSockets:
1. Add `/v1/ws` endpoint alongside `/v1/stream`
2. Same event schema, different transport
3. GUI can detect capability and use preferred transport

---

## Event Schema

### Base Event (All Events)

```typescript
interface BaseEvent {
  event_type: string;           // Namespaced: "engine.*", "job.*"
  sequence_number: number;      // Global monotonic
  timestamp_utc: string;        // ISO 8601 with milliseconds
}
```

### Engine Events

```typescript
interface EngineHeartbeat extends BaseEvent {
  event_type: "engine.heartbeat";
  uptime_ms: number;
  health: "healthy" | "degraded";
  active_jobs: number;
  queue_depth: number;
}

interface EngineShuttingDown extends BaseEvent {
  event_type: "engine.shutting_down";
  reason: "user_request" | "update" | "error";
  grace_period_ms: number;
}
```

### Job Events

```typescript
interface JobStateChanged extends BaseEvent {
  event_type: "job.state_changed";
  job_id: string;
  old_state: JobState;
  new_state: JobState;
}

interface JobProgress extends BaseEvent {
  event_type: "job.progress";
  job_id: string;
  job_sequence: number;        // Per-job ordering
  phase: string;
  progress_percent?: number;   // null if indeterminate
  items_completed?: number;
  items_total?: number;
  eta_seconds?: number;        // null if unknown
}

interface JobLog extends BaseEvent {
  event_type: "job.log";
  job_id: string;
  job_sequence: number;
  level: "trace" | "debug" | "info" | "warn" | "error";
  subsystem: string;
  message: string;
  payload?: Record<string, unknown>;
  correlation_id?: string;
}
```

---

## Heartbeat Protocol

### Engine Responsibilities

1. Emit `engine.heartbeat` every **3 seconds**
2. Heartbeat is always sent, even if no jobs running
3. Heartbeat skips no sequence numbers (can be used for gap detection)

### GUI Health States

| Condition | State | UI Display |
|-----------|-------|------------|
| Heartbeat < 3s ago | `CONNECTED` | Green pill |
| Heartbeat 3-10s ago | `CONNECTED` | Green pill (normal variance) |
| Heartbeat 10-30s ago | `DEGRADED` | Orange pill, "Connection unstable" |
| Heartbeat > 30s ago | `DISCONNECTED` | Red pill, reconnect UI |

### Missed Heartbeat Handling

```
Time 0s:  Heartbeat received (seq 100)
Time 3s:  Heartbeat expected (seq 101), not received
Time 6s:  Heartbeat expected (seq 102), not received
Time 10s: GUI shows "degraded" warning
Time 30s: GUI shows "disconnected", starts reconnection
```

---

## Error Handling

### SSE Connection Errors

| Error | Cause | Recovery |
|-------|-------|----------|
| HTTP 401 | Invalid/missing token | Prompt for re-auth |
| HTTP 503 | Engine overloaded | Exponential backoff |
| Connection refused | Engine not running | Show "Engine offline" |
| Timeout (60s) | Network/engine hung | Reconnect with backoff |

### Event Parse Errors

If event data is malformed:
1. Log to console (debug builds only)
2. Skip event, continue processing
3. Increment error counter
4. If >10 errors/minute: disconnect, reconnect

---

## Implementation Notes

### FastAPI Server

```python
from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse

@app.get("/v1/stream")
async def stream(
    resume_from: int | None = None,
    job_id: str | None = None
):
    async def event_generator():
        # 1. Replay from SQLite if resume_from specified
        if resume_from:
            async for event in replay_events(resume_from, job_id):
                yield event

        # 2. Switch to live stream
        async for event in live_event_stream():
            yield event

    return EventSourceResponse(event_generator())
```

### Tauri/React Client

```typescript
function useEventStream(lastEventId?: number) {
  useEffect(() => {
    const url = new URL('/v1/stream', ENGINE_URL);
    if (lastEventId) {
      url.searchParams.set('resume_from', lastEventId.toString());
    }

    const eventSource = new EventSource(url.toString());

    eventSource.onmessage = (e) => {
      const event = JSON.parse(e.data);
      eventQueue.enqueue(event);
    };

    eventSource.onerror = () => {
      scheduleReconnect();
    };

    return () => eventSource.close();
  }, [lastEventId]);
}
```

---

## Consequences

### Positive
- Simple, debuggable transport
- Automatic reconnection via EventSource
- Works on all platforms without special configuration
- Clear upgrade path to WebSockets if needed

### Negative
- SSE is one-way only (fine for our use case)
- HTTP/1.1 connection per stream (not multiplexed)
- No built-in binary support (JSON sufficient for us)

### Risks
- Large replay requests could slow engine (mitigated by chunking)
- Browser tab throttling may affect background tabs (mitigated by replay on focus)

---

## Related Documents

- [Desktop App UX Spec](../specs/desktop-app-ux-architecture-spec.md) — Full UI specification
- [ADR-001](../ADR-001-architecture.md) — Core architecture
- [ADR-004](./ADR-004-job-system-persistence.md) — Job persistence
