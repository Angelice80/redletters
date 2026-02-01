# Sprint-2 Definition of Done

**Goal**: Validate streaming behavior under real-world conditions and harden tamper-evidence.

Sprint 2 starts by hardening persistence (atomic receipt writes), then validates streaming under real IO (async SSE), then adds timing chaos and light load.

## Prerequisites (from Sprint-1)

- [x] Sequence numbers sourced from persisted DB state (not runtime counter)
- [x] Receipt hash stored in DB for tamper-evidence
- [x] Atomic receipt write: temp → fsync → rename (Sprint-2 hardening, done early)

## Completed

- [x] **Atomic receipt write** - 4 tests (temp→fsync→rename pattern)
- [x] **CT-09 Async SSE** - 8 tests (httpx.AsyncClient, replay correctness)
- [x] **CT-10 Chaos timing** - 12 tests (random disconnect, rapid reconnect, bursts)
- [x] **CT-11 Backpressure** - 10 tests (slow consumers, pagination, late join)
- [x] **CT-12 Load** - 9 tests (concurrent clients, burst reconnects, stress sequencing)
- [x] **Diagnostics hash enhancement** - 11 tests (integrity_report.json, tamper detection)

## CT-09: Async SSE Client Tests

**Contract**: Real streaming behavior under httpx.AsyncClient.

| Test | Assertion |
|------|-----------|
| Connect, read N events, disconnect | Events received match persisted count |
| Reconnect with Last-Event-ID | No gaps in replayed sequence |
| Reconnect with Last-Event-ID | No duplicates in replayed sequence |
| Reconnect with Last-Event-ID | Monotonicity preserved |
| Cross-job replay | Events from multiple jobs ordered correctly |

**Implementation**: `tests/contract/test_ct09_async_sse.py`

```python
# Pattern: async context manager with timeout
async with httpx.AsyncClient() as client:
    async with client.stream("GET", url, headers=auth) as response:
        async for line in response.aiter_lines():
            # Parse SSE, track sequences, disconnect after N events
```

## CT-10: Chaos Timing Tests

**Contract**: SSE reconnect survives hostile timing conditions.

| Test | Assertion |
|------|-----------|
| Disconnect at random byte boundaries | Reconnect recovers full stream |
| Disconnect at random event counts | Last-Event-ID replay correct |
| Rapid connect/disconnect cycles (10x) | No sequence gaps across all reconnects |
| Disconnect during high-frequency events | Replay catches all missed events |

**Implementation**: `tests/contract/test_ct10_chaos_timing.py`

## CT-11: Slow Consumer / Backpressure

**Contract**: SSE handles slow consumers without data loss.

| Test | Assertion |
|------|-----------|
| Consumer pauses for 5s mid-stream | All events eventually received |
| Consumer reads 1 byte/sec | Events buffered, no loss |
| Multiple slow consumers | Events delivered to all |

**Implementation**: `tests/contract/test_ct11_backpressure.py`

## CT-12: Light Load Test

**Contract**: Multiple concurrent clients don't break reconnect semantics.

| Test | Assertion |
|------|-----------|
| 10 clients connect simultaneously | All receive events |
| 5 clients disconnect/reconnect while 5 stay connected | Reconnecting clients catch up |
| Burst of 50 reconnects | All clients reach consistent state |

**Implementation**: `tests/contract/test_ct12_load.py`

## Diagnostics Bundle Enhancement

**Contract**: Bundle includes DB-authoritative hashes for tamper-evidence.

| Field | Source | Purpose |
|-------|--------|---------|
| `expected_hash` | jobs.receipt_hash / artifacts.sha256 | DB-authoritative hash |
| `actual_hash` | Live SHA-256 computation | Current file hash |
| `status` | Comparison result | MATCH/MISMATCH/MISSING/SKIPPED_LARGE |
| `summary` | Aggregated counts | ok/warn/fail/skipped totals |
| `failures` | Compact list | Quick review of tamper incidents |

**Implementation**: `src/redletters/engine_spine/diagnostics.py`

**Output Files**:
- `integrity_report.json` - Machine-readable with full details
- `integrity_report.txt` - Human-readable summary

**Size Threshold Policy**:
- Receipts: Always hashed (small files, critical for provenance)
- Artifacts: ≤100MB hashed by default, larger → SKIPPED_LARGE
- Environment variable `REDLETTERS_INTEGRITY_SIZE_THRESHOLD` configurable
- `--full-integrity` flag hashes all files regardless of size

## Test Counts (Actual)

| Category | Target | Actual |
|----------|--------|--------|
| Atomic write | - | 4 |
| CT-07 SSE reconnect (unskipped) | 2 | 2 |
| CT-09 Async SSE | 5+ | 8 |
| CT-10 Chaos | 4+ | 12 |
| CT-11 Backpressure | 3+ | 10 |
| CT-12 Load | 3+ | 9 |
| Diagnostics hash tests | 3+ | 11 |
| **Total new tests** | **20+** | **56** |

## Definition of Done Checklist

- [x] CT-07 skipped tests are unskipped and run with async client (2 tests unskipped)
- [x] CT-09 through CT-12 implemented and passing (39 tests)
- [x] Diagnostics bundle includes `receipt_hash_from_db` and `artifact_sha256_from_db`
- [x] Hash mismatch detection in diagnostics (MATCH/MISMATCH/MISSING/SKIPPED_LARGE)
- [x] All tests pass in CI (152 passed, 0 skipped)
- [x] No temp files left behind after receipt writes (verified, 4 tests)

## Risk Surface After Sprint-2

If all tests pass:
- Reconnect contract is "court-admissible"
- Tamper-evidence is verifiable
- Streaming behavior validated under hostile conditions

Remaining risks:
- Windows compatibility (SSE + file perms + subprocess kill differ)
- Full E2E with Electron/Tauri GUI orchestration
