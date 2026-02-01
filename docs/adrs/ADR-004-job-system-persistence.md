# ADR-004: Job System & Persistence

**Status**: Accepted
**Date**: 2026-01-27
**Context**: Desktop GUI Architecture (Phase 5)
**Supersedes**: None
**Related**: ADR-001 (SQLite decision), ADR-002 (Provenance model), ADR-003 (Transport)

---

## Source of Truth Declaration

Three overlapping records of reality exist. Without declared precedence: Schrödinger's Job.

### Precedence Rules

```
┌─────────────────────────────────────────────────────────────────┐
│ DURING JOB EXECUTION                                            │
│                                                                 │
│   SQLite (jobs + job_events tables)                             │
│   ════════════════════════════════                              │
│   • Authoritative for: job state, event ordering, progress      │
│   • Why: ACID guarantees, crash recovery, SSE replay source     │
│   • Events written to DB BEFORE sent to stream (at-least-once)  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ job completes/fails/cancels
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ AFTER JOB COMPLETION                                            │
│                                                                 │
│   receipt.json (in workspace)                                   │
│   ═══════════════════════════                                   │
│   • Authoritative for: "what happened" (immutable final record) │
│   • Why: Signed, hashed, versioned, portable                    │
│   • Contains: timestamps, config, source pins, output hashes    │
│   • NEVER modified after write (chmod 444)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ references
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ ARTIFACTS                                                       │
│                                                                 │
│   workspace/output/* files                                      │
│   ════════════════════════                                      │
│   • Authoritative for: actual output content                    │
│   • BUT: only valid as referenced by receipt.json               │
│   • receipt.json contains: path, size, sha256 for each artifact │
│   • Verification: compare file hash to receipt hash             │
└─────────────────────────────────────────────────────────────────┘
```

### Conflict Resolution

| Scenario | Resolution |
|----------|------------|
| DB says "completed", no receipt.json | Job failed silently; mark as `failed`, generate partial receipt |
| receipt.json exists, DB says "running" | Engine crashed after write; trust receipt, update DB |
| Artifact hash ≠ receipt hash | Artifact corrupted; mark as `quarantined`, preserve receipt |
| DB event count ≠ receipt summary | Events are ephemeral (retention); receipt is authoritative |
| Client has events DB doesn't | Impossible (DB written first); client bug, ignore |

### Recovery Path (DB Corruption)

```
1. Detect corruption (PRAGMA integrity_check fails)
2. Rename corrupt: engine.db → engine.db.corrupt.<timestamp>
3. Create fresh database with current schema
4. Scan ~/.greek2english/workspaces/*/receipt.json
5. For each receipt:
   a. Rebuild jobs row from receipt metadata
   b. Rebuild artifacts rows from receipt.outputs
   c. Events are NOT recovered (ephemeral by design)
6. Notify user: "Database recovered. History restored. Event logs unavailable."
```

### What This Means in Practice

- **Never lie about job state**: If in doubt, check receipt.json
- **Receipt is the audit trail**: Everything else can be rebuilt from it
- **Events are cache**: Useful for replay, but not source of truth after job ends
- **Artifacts are content**: Verified by hash in receipt, not independently trusted

---

## Context

The desktop application runs translation jobs that may:
- Take minutes to complete
- Generate detailed logs (thousands of entries)
- Produce artifacts (output files, receipts)
- Be interrupted (user cancel, GUI close, crash, system shutdown)

We need durable storage for:
1. Job configuration and state
2. Event logs (for replay after disconnect)
3. Artifacts metadata
4. Receipts (immutable provenance records)

ADR-001 established SQLite for data storage. This ADR extends that decision for job management.

## Decision

### SQLite for Durable Jobs + Events

**Choice**: Single SQLite database at `~/.greek2english/engine.db` stores all job-related data.

**Rationale**:
- Consistent with ADR-001 (already using SQLite for corpus data)
- Single file backup/migration
- ACID guarantees for job state transitions
- WAL mode for concurrent read/write
- Sufficient performance for expected scale

### Per-Job Workspace Folders

**Choice**: Each job gets an isolated workspace directory.

```
~/.greek2english/
├── engine.db              # Main database
├── engine.pid             # Process lock
├── logs/
│   └── engine.log         # Engine-level logs
└── workspaces/
    ├── job_20240115_143000_a3f8/
    │   ├── input/         # Copied/linked input files
    │   ├── output/        # Generated artifacts
    │   ├── temp/          # Working files (deleted on completion)
    │   └── receipt.json   # Final provenance receipt
    └── job_20240115_144500_b7e2/
        └── ...
```

**Rationale**:
- Isolation prevents cross-job contamination
- Easy cleanup on job deletion
- Artifacts naturally grouped
- Temp files don't pollute user directories

---

## Schema

### Core Tables

```sql
-- Schema version tracking
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT
);

-- Job records
CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,
    state TEXT NOT NULL DEFAULT 'draft'
        CHECK (state IN ('draft', 'queued', 'running', 'cancelling',
                         'cancelled', 'completed', 'failed', 'archived')),
    priority TEXT NOT NULL DEFAULT 'normal'
        CHECK (priority IN ('low', 'normal', 'high')),

    -- Timestamps
    created_at TEXT NOT NULL,
    queued_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL,

    -- Configuration (immutable after queued)
    config_json TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    input_spec_json TEXT NOT NULL,

    -- Output
    output_dir TEXT,
    workspace_path TEXT,

    -- Progress (updated during execution)
    progress_percent INTEGER,
    progress_phase TEXT,
    items_completed INTEGER,
    items_total INTEGER,

    -- Result
    exit_code TEXT,        -- null=running, 'success', 'cancelled', 'error'
    error_code TEXT,
    error_message TEXT,
    error_details_json TEXT,

    -- Receipt (written on completion)
    receipt_json TEXT,
    receipt_hash TEXT,

    -- Idempotency
    idempotency_key TEXT UNIQUE,
    idempotency_expires_at TEXT
);

CREATE INDEX idx_jobs_state ON jobs(state);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
CREATE INDEX idx_jobs_idempotency ON jobs(idempotency_key)
    WHERE idempotency_key IS NOT NULL;

-- Job events (logs, progress updates)
CREATE TABLE job_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,      -- Global sequence
    job_sequence INTEGER NOT NULL,         -- Per-job sequence
    timestamp_utc TEXT NOT NULL,
    event_type TEXT NOT NULL,

    -- For log events
    level TEXT,
    subsystem TEXT,
    message TEXT,
    payload_json TEXT,
    correlation_id TEXT,

    -- For progress events
    phase TEXT,
    progress_percent INTEGER,
    items_completed INTEGER,
    items_total INTEGER,

    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE INDEX idx_job_events_job_seq ON job_events(job_id, job_sequence);
CREATE INDEX idx_job_events_global_seq ON job_events(sequence_number);
CREATE INDEX idx_job_events_timestamp ON job_events(timestamp_utc);
CREATE INDEX idx_job_events_level ON job_events(job_id, level)
    WHERE level IN ('warn', 'error');

-- Artifacts (output files)
CREATE TABLE artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    artifact_type TEXT NOT NULL
        CHECK (artifact_type IN ('output', 'receipt', 'log', 'partial')),
    size_bytes INTEGER,
    sha256 TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'writing', 'complete', 'failed', 'quarantined')),
    created_at TEXT NOT NULL,
    verified_at TEXT,

    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE INDEX idx_artifacts_job ON artifacts(job_id);

-- Global sequence counter
CREATE TABLE sequence_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_sequence INTEGER NOT NULL DEFAULT 0
);

INSERT INTO sequence_state (id, last_sequence) VALUES (1, 0);
```

---

## Schema Migration Plan

### Version Tracking

Each migration is a SQL file with a version number:

```
migrations/
├── 001_initial_schema.sql
├── 002_add_job_events.sql
├── 003_add_artifacts.sql
└── ...
```

### Migration Execution

```python
def migrate_database(db_path: Path):
    conn = sqlite3.connect(db_path)

    # Get current version
    current = get_current_version(conn)  # 0 if new db

    # Find pending migrations
    for migration in get_migrations_after(current):
        with conn:  # Transaction
            execute_migration(conn, migration)
            set_version(conn, migration.version)
            log.info(f"Applied migration {migration.version}: {migration.description}")

    conn.close()
```

### Migration Rules

1. **Forward-only**: No rollback support (keep it simple)
2. **Additive preferred**: Add columns with defaults, avoid renames
3. **Tested**: Each migration tested on production-like data
4. **Atomic**: Each migration in a transaction

### Breaking Changes

If a migration would break compatibility:
1. Bump engine MAJOR version
2. Document in CHANGELOG
3. Provide data export before migration
4. GUI shows migration warning on first launch

---

## Corruption & Lock Handling

### SQLite Corruption Detection

```python
def check_database_health(db_path: Path) -> HealthStatus:
    conn = sqlite3.connect(db_path)
    try:
        # Quick integrity check
        result = conn.execute("PRAGMA quick_check").fetchone()
        if result[0] != "ok":
            return HealthStatus.CORRUPTED

        # Verify we can read key tables
        conn.execute("SELECT COUNT(*) FROM jobs").fetchone()
        conn.execute("SELECT COUNT(*) FROM job_events LIMIT 1").fetchone()

        return HealthStatus.HEALTHY
    except sqlite3.DatabaseError as e:
        return HealthStatus.CORRUPTED
    finally:
        conn.close()
```

### Corruption Recovery

| Severity | Detection | Recovery |
|----------|-----------|----------|
| Soft (index) | Query errors | `REINDEX` automatically |
| Hard (page) | PRAGMA check fails | Backup corrupt, create fresh, rebuild from workspaces |
| Total loss | File unreadable | Create fresh, rebuild from workspaces, notify user |

**Recovery Flow**:
```
1. Detect corruption on startup
2. Rename corrupt file: engine.db → engine.db.corrupt.20240115
3. Create fresh database with current schema
4. Scan workspace directories for recoverable data:
   - Each workspace has receipt.json → rebuild jobs table
   - Each workspace has output/ → rebuild artifacts table
   - Events are NOT recoverable (acceptable loss)
5. Show notification: "Database recovered. Job history restored. Event logs unavailable."
6. Log location of corrupt file for debug
```

**Workspace-Based Reconstruction**:

```python
async def rebuild_from_workspaces(db: Database, workspace_base: Path):
    """Reconstruct job records from workspace receipts."""
    recovered = 0

    for workspace in workspace_base.iterdir():
        if not workspace.is_dir():
            continue

        receipt_path = workspace / "receipt.json"
        if not receipt_path.exists():
            continue

        try:
            receipt = json.loads(receipt_path.read_text())
            await db.execute("""
                INSERT INTO jobs (job_id, state, created_at, completed_at,
                                  config_json, receipt_json, workspace_path)
                VALUES (?, 'completed', ?, ?, ?, ?, ?)
            """, [
                receipt["job_id"],
                receipt["timestamps"]["created"],
                receipt["timestamps"]["completed"],
                json.dumps(receipt.get("config_snapshot", {})),
                json.dumps(receipt),
                str(workspace)
            ])
            recovered += 1
        except Exception as e:
            log.warning(f"Could not recover from {workspace}: {e}")

    log.info(f"Recovered {recovered} jobs from workspace receipts")
```

**What IS Recoverable**:
- Job metadata (from receipt.json)
- Final artifacts (from output/ directory)
- Configuration used (from receipt.json config_snapshot)

**What is NOT Recoverable**:
- Event logs (ephemeral by design, subject to retention anyway)
- Progress history (not critical)
- Queue position history (not critical)

**Backup Strategy** (Optional, User-Configurable):

```toml
# ~/.greek2english/config.toml
[backup]
enabled = true
frequency = "daily"
keep_count = 7
path = "~/.greek2english/backups/"
```

```python
async def backup_database():
    """Create timestamped backup using SQLite backup API."""
    backup_path = get_backup_path()
    async with aiosqlite.connect(db_path) as src:
        async with aiosqlite.connect(backup_path) as dst:
            await src.backup(dst)
    prune_old_backups(keep=7)
```

### Lock Handling

SQLite busy timeout: **30 seconds** (WAL mode reduces contention).

```python
conn = sqlite3.connect(
    db_path,
    timeout=30.0,
    isolation_level="DEFERRED"
)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=30000")
```

**Lock Scenarios**:

| Scenario | Cause | Handling |
|----------|-------|----------|
| Reader blocks writer | Long query | WAL mode eliminates this |
| Writer blocks writer | Concurrent jobs | Queue at application level |
| Stale lock | Crash without cleanup | Check PID file, clear if stale |
| System lock | File sync issue | Retry with backoff, then fail |

**Stale Lock Detection**:
```python
def check_stale_lock(db_path: Path) -> bool:
    pid_file = db_path.parent / "engine.pid"
    if not pid_file.exists():
        return False

    pid = int(pid_file.read_text().strip())
    try:
        os.kill(pid, 0)  # Check if process exists
        return False  # Process alive, lock valid
    except OSError:
        return True  # Process dead, lock stale
```

---

## Retention Policy

### Event Log Retention

| Retention | Events | Reason |
|-----------|--------|--------|
| 24 hours | All events | Full replay capability |
| 7 days | WARN/ERROR only | Debugging window |
| 30 days | Aggregated stats | Trend analysis |
| Permanent | Job summary + receipt | Audit trail |

### Automatic Cleanup

```python
async def cleanup_old_events():
    """Run daily via scheduler"""
    cutoff_24h = datetime.utcnow() - timedelta(hours=24)
    cutoff_7d = datetime.utcnow() - timedelta(days=7)

    with db.transaction():
        # Delete DEBUG/INFO older than 24h
        db.execute("""
            DELETE FROM job_events
            WHERE timestamp_utc < ?
            AND level IN ('trace', 'debug', 'info')
        """, [cutoff_24h.isoformat()])

        # Delete WARN older than 7 days
        db.execute("""
            DELETE FROM job_events
            WHERE timestamp_utc < ?
            AND level = 'warn'
        """, [cutoff_7d.isoformat()])

        # Keep ERROR permanently (with job)

    # Reclaim space
    db.execute("PRAGMA incremental_vacuum(1000)")
```

### Workspace Cleanup

| Job State | Workspace Retention |
|-----------|---------------------|
| `running` | Keep everything |
| `completed` | Keep output + receipt, delete temp |
| `failed` | Keep all (for debugging) for 7 days |
| `cancelled` | Keep partial output for 24 hours |
| `archived` | Delete workspace, keep receipt in DB |

```python
async def cleanup_workspaces():
    """Run daily"""
    for job in get_jobs_for_cleanup():
        workspace = Path(job.workspace_path)

        if job.state == "completed":
            shutil.rmtree(workspace / "temp", ignore_errors=True)

        elif job.state == "failed" and job.completed_at < days_ago(7):
            archive_for_support(workspace)
            shutil.rmtree(workspace)

        elif job.state == "cancelled" and job.completed_at < days_ago(1):
            shutil.rmtree(workspace)

        elif job.state == "archived":
            shutil.rmtree(workspace, ignore_errors=True)
```

### Database Size Limits

| Metric | Soft Limit | Hard Limit | Action |
|--------|------------|------------|--------|
| Database size | 500 MB | 1 GB | Warn user, suggest archive |
| Events count | 500,000 | 1,000,000 | Force cleanup |
| Job count | 1,000 | 5,000 | Suggest archive |

---

## Job State Machine

```
                         ┌───────┐
                         │ DRAFT │ (GUI editing config)
                         └───┬───┘
                             │ POST /v1/jobs
                             ▼
                         ┌────────┐
              ┌──────────│ QUEUED │──────────┐
              │          └───┬────┘          │
              │              │ resources     │ user cancel
              │              │ available     │
              │              ▼               ▼
              │          ┌─────────┐    ┌────────────┐
              │          │ RUNNING │    │ CANCELLED  │
              │          └────┬────┘    └────────────┘
              │               │
    ┌─────────┼───────────────┼───────────────┐
    │         │               │               │
    │ cancel  │ success       │ error         │
    ▼         ▼               ▼               │
┌────────────┐ ┌───────────┐ ┌──────────┐     │
│ CANCELLING │ │ COMPLETED │ │  FAILED  │     │
└─────┬──────┘ └───────────┘ └──────────┘     │
      │                                       │
      │ cleanup complete                      │
      ▼                                       │
┌────────────┐                                │
│ CANCELLED  │                                │
└────────────┘                                │

    (Any terminal state) ──user action──▶ ARCHIVED
```

### State Transitions

| From | To | Trigger | Side Effects |
|------|-----|---------|--------------|
| DRAFT | QUEUED | `POST /v1/jobs` | Validate config, assign job_id |
| QUEUED | RUNNING | Scheduler picks job | Create workspace, start processing |
| QUEUED | CANCELLED | User cancel | None |
| RUNNING | COMPLETED | Processing done | Write receipt, finalize artifacts |
| RUNNING | FAILED | Error thrown | Write partial receipt, preserve state |
| RUNNING | CANCELLING | User cancel | Set flag, wait for checkpoint |
| CANCELLING | CANCELLED | Cleanup done | Archive partial, clean temp |
| * | ARCHIVED | User archives | Delete workspace, keep DB record |

### Queued vs Running: Precise Semantics

**QUEUED**: Job accepted, persisted, waiting for worker slot.

**RUNNING**: Worker has claimed exclusive lock, processing has begun.

```
┌────────────────────────────────────────────────────────────────┐
│ State        │ Meaning                  │ Guarantee             │
├──────────────┼──────────────────────────┼───────────────────────┤
│ queued       │ In queue, not claimed    │ Will eventually run   │
│              │                          │ or timeout/fail       │
├──────────────┼──────────────────────────┼───────────────────────┤
│ running      │ Worker lock acquired,    │ job.started event     │
│              │ execution in progress    │ was emitted           │
└────────────────────────────────────────────────────────────────┘
```

**Transition Contract**:

1. `queued → running` ONLY when:
   - Worker acquires exclusive job lock (via DB transaction)
   - Workspace is created successfully
   - `job.started` event is emitted

2. If worker fails to emit `job.started` within **30 seconds** of claiming:
   - Job releases lock, returns to `queued`
   - Counter increments `claim_attempts`
   - After 3 failed claims → automatic `failed` state

**Heartbeat Guarantee** (Preventing "Stuck in Queued"):

```python
# Scheduler emits heartbeat for each queued job every 10 seconds
async def emit_queue_heartbeats():
    for job in get_queued_jobs():
        await emit_event(JobQueueHeartbeat(
            job_id=job.job_id,
            queue_position=job.queue_position,
            estimated_wait_seconds=estimate_wait(job),
            claim_attempts=job.claim_attempts
        ))
```

**GUI Contract**:
- Every job gets either `job.started` or `job.failed` within **60 seconds** of creation
- OR receives periodic `job.queue_heartbeat` events explaining the wait
- Absence of both for 60s = display "Job may be stuck" warning

### Crash Recovery

On engine startup:
```python
def recover_from_crash():
    # Find jobs that were running when we crashed
    orphaned = db.query("""
        SELECT * FROM jobs WHERE state IN ('running', 'cancelling')
    """)

    for job in orphaned:
        log.warn(f"Recovering orphaned job: {job.job_id}")

        # Mark as failed with crash reason
        db.execute("""
            UPDATE jobs
            SET state = 'failed',
                error_code = 'E_ENGINE_CRASH',
                error_message = 'Engine terminated unexpectedly',
                completed_at = ?
            WHERE job_id = ?
        """, [datetime.utcnow().isoformat(), job.job_id])

        # Quarantine any partial output
        quarantine_workspace(job.workspace_path)
```

---

## Performance Considerations

### Write Batching

Log events are batched before database write:
```python
class EventBatcher:
    def __init__(self, flush_interval=0.5, batch_size=100):
        self.buffer = []
        self.flush_interval = flush_interval
        self.batch_size = batch_size

    async def add(self, event):
        self.buffer.append(event)
        if len(self.buffer) >= self.batch_size:
            await self.flush()

    async def flush(self):
        if not self.buffer:
            return
        events = self.buffer
        self.buffer = []
        await db.executemany(INSERT_EVENT, events)
```

### Read Optimization

```sql
-- Covering index for common log query
CREATE INDEX idx_job_events_log_query
ON job_events(job_id, job_sequence, level, timestamp_utc, message);

-- Partial index for error lookup
CREATE INDEX idx_job_events_errors
ON job_events(job_id, timestamp_utc)
WHERE level IN ('warn', 'error');
```

### Connection Pooling

Single connection with WAL mode is sufficient for our workload:
- One writer (job executor)
- Multiple readers (API handlers, GUI queries)

WAL mode allows concurrent reads during writes.

---

## Artifact Hash Verification (Pragmatic Approach)

### The Problem

Hashing large artifacts is expensive. Naive implementation verifies on every UI refresh → "Jobs list" becomes CPU benchmark.

### Design Choice: Hash on Write, Verify on Demand

```
┌─────────────────────────────────────────────────────────────────┐
│ WRITE TIME                                                      │
│                                                                 │
│ Artifact written → hash computed DURING write (streaming)       │
│ Stored in DB: size, mtime, sha256                               │
│ Cost: ~0 (I/O-bound anyway)                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ READ TIME (UI)                                                  │
│                                                                 │
│ List jobs: show size + mtime (NO hash verification)             │
│ Job detail: show artifact list (NO hash verification)           │
│ Cost: ~0 (metadata only)                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ VERIFY TIME (On Demand)                                         │
│                                                                 │
│ When: Export, integrity check command, suspicious mtime change  │
│ Action: Re-hash artifact, compare to stored hash                │
│ Cost: O(file size), user-initiated                              │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation

```python
class ArtifactWriter:
    """Write artifact with streaming hash computation."""

    async def write(self, job_id: str, name: str, content: AsyncIterator[bytes]):
        path = get_artifact_path(job_id, name)
        hasher = hashlib.sha256()
        size = 0

        async with aiofiles.open(path, 'wb') as f:
            async for chunk in content:
                await f.write(chunk)
                hasher.update(chunk)  # Hash during write
                size += len(chunk)

        # Store metadata (no extra read needed)
        await db.execute("""
            INSERT INTO artifacts (job_id, name, path, size_bytes, sha256, status)
            VALUES (?, ?, ?, ?, ?, 'complete')
        """, [job_id, name, str(path), size, hasher.hexdigest()])


async def verify_artifact(artifact_id: int) -> VerifyResult:
    """Verify on demand (export, integrity check)."""
    artifact = await get_artifact(artifact_id)
    path = Path(artifact.path)

    # Quick check: size + mtime
    stat = path.stat()
    if stat.st_size != artifact.size_bytes:
        return VerifyResult.SIZE_MISMATCH

    # Full check: hash
    hasher = hashlib.sha256()
    async with aiofiles.open(path, 'rb') as f:
        while chunk := await f.read(65536):
            hasher.update(chunk)

    if hasher.hexdigest() != artifact.sha256:
        return VerifyResult.HASH_MISMATCH

    # Update verification timestamp
    await db.execute("""
        UPDATE artifacts SET verified_at = ? WHERE id = ?
    """, [datetime.utcnow().isoformat(), artifact_id])

    return VerifyResult.OK
```

### When Verification Happens

| Scenario | Verification |
|----------|--------------|
| Job list in GUI | Never (metadata only) |
| Job detail view | Never (metadata only) |
| Export to folder | Full hash verification |
| `redletters verify` command | Full hash verification |
| mtime changed since write | Automatic re-verify + warn |
| Receipt generation | Full hash verification (required) |

### Size/Mtime as Fast Proxy

For display purposes, `(size, mtime)` is sufficient:
- If different: definitely modified
- If same: probably unmodified (for display purposes)

Only cryptographic verification matters for:
- Export
- Receipt generation
- Trust decisions

---

## Consequences

### Positive
- Durable job state survives crashes
- Full audit trail with receipts
- Efficient event replay for reconnection
- Isolated workspaces prevent contamination

### Negative
- Single SQLite file is a bottleneck for extreme concurrency
- Workspace cleanup adds complexity
- Database growth requires monitoring

### Risks
- Corruption possible (mitigated by backups + recovery)
- Large event volumes may slow queries (mitigated by retention + indexes)
- Disk space exhaustion (mitigated by limits + cleanup)

---

## Related Documents

- [ADR-001](../ADR-001-architecture.md) — SQLite decision
- [ADR-002](../ADR-002-provenance-first-data-model.md) — Provenance model
- [ADR-003](./ADR-003-ui-engine-transport-streaming.md) — Event streaming
- [Desktop App UX Spec](../specs/desktop-app-ux-architecture-spec.md) — Job UI requirements
