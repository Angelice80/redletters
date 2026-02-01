# STORY-004: Job Persistence Schema

**Epic**: Desktop App Architecture
**ADRs**: ADR-004
**Priority**: P0 (Foundation)
**Depends On**: STORY-001 (Engine Service Lifecycle)
**Estimate**: 2 days

---

## User Story

**As a** user running long translation jobs,
**I want** my jobs and logs to persist in a database,
**So that** I can review history and recover from crashes.

---

## Acceptance Criteria

### AC-1: Schema Migration System
- [ ] `schema_version` table tracks current version
- [ ] Migrations stored in `migrations/` directory
- [ ] Migrations run automatically on engine startup
- [ ] Failed migration rolls back and logs error

### AC-2: Jobs Table
- [ ] `jobs` table stores all job metadata
- [ ] States: `draft`, `queued`, `running`, `cancelling`, `cancelled`, `completed`, `failed`, `archived`
- [ ] Timestamps: `created_at`, `queued_at`, `started_at`, `completed_at`, `updated_at`
- [ ] Config stored as JSON
- [ ] Idempotency key for duplicate prevention

### AC-3: Job Events Table
- [ ] `job_events` table stores logs and progress
- [ ] Global `sequence_number` for SSE ordering
- [ ] Per-job `job_sequence` for log ordering
- [ ] Indexed for efficient replay queries

### AC-4: Artifacts Table
- [ ] `artifacts` table tracks output files
- [ ] Links to job via `job_id`
- [ ] Stores path, size, hash, status

### AC-5: WAL Mode
- [ ] Database uses WAL mode for concurrent reads
- [ ] Busy timeout of 30 seconds
- [ ] Verified with concurrent read/write test

---

## Technical Design

### Migration System

```python
MIGRATIONS = [
    Migration(1, "001_initial_schema.sql", "Initial job tables"),
    Migration(2, "002_add_artifacts.sql", "Artifact tracking"),
]

async def run_migrations(db: Database):
    current = await get_schema_version(db)

    for migration in MIGRATIONS:
        if migration.version > current:
            async with db.transaction():
                await execute_sql_file(migration.path)
                await set_schema_version(db, migration.version)
                log.info(f"Applied migration {migration.version}")
```

### Initial Schema (001_initial_schema.sql)

```sql
-- Schema version tracking
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT
);

-- Jobs
CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,
    state TEXT NOT NULL DEFAULT 'draft',
    priority TEXT NOT NULL DEFAULT 'normal',
    created_at TEXT NOT NULL,
    queued_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL,
    config_json TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    input_spec_json TEXT NOT NULL,
    output_dir TEXT,
    workspace_path TEXT,
    progress_percent INTEGER,
    progress_phase TEXT,
    exit_code TEXT,
    error_code TEXT,
    error_message TEXT,
    receipt_json TEXT,
    idempotency_key TEXT UNIQUE
);

CREATE INDEX idx_jobs_state ON jobs(state);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);

-- Job events
CREATE TABLE job_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    job_sequence INTEGER NOT NULL,
    timestamp_utc TEXT NOT NULL,
    event_type TEXT NOT NULL,
    level TEXT,
    subsystem TEXT,
    message TEXT,
    payload_json TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE INDEX idx_job_events_job_seq ON job_events(job_id, job_sequence);
CREATE INDEX idx_job_events_global_seq ON job_events(sequence_number);

-- Global sequence counter
CREATE TABLE sequence_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_sequence INTEGER NOT NULL DEFAULT 0
);

INSERT INTO sequence_state (id, last_sequence) VALUES (1, 0);

-- Artifacts
CREATE TABLE artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    size_bytes INTEGER,
    sha256 TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE INDEX idx_artifacts_job ON artifacts(job_id);
```

### Files Changed/Created

- `src/redletters/engine/database.py` — Database connection and WAL setup
- `src/redletters/engine/migrations/` — Migration SQL files
- `src/redletters/engine/migrate.py` — Migration runner
- `src/redletters/engine/models.py` — SQLAlchemy/Pydantic models

---

## Test Plan

| Test | Type | Description |
|------|------|-------------|
| `test_migration_creates_tables` | Integration | Fresh database |
| `test_migration_is_idempotent` | Integration | Run twice, no error |
| `test_job_crud_operations` | Integration | Create, read, update |
| `test_event_sequence_monotonic` | Unit | Sequence generation |
| `test_wal_mode_enabled` | Integration | PRAGMA query |
| `test_concurrent_read_write` | Integration | Parallel access |

---

## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Tests written and passing
- [ ] Database created at `~/.greek2english/engine.db`
- [ ] Migrations logged on startup
- [ ] No regression in existing data model (sources, tokens, lexicon_entries)
- [ ] Coexists with ADR-002 schema (different concerns, same file)
