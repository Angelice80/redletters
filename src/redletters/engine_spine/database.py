"""Database layer for Engine Spine job system.

Implements ADR-004 schema and persist-before-send pattern per ADR-003.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from redletters.engine_spine.models import (
    BaseEvent,
    EventRowId,
    JobState,
    LogLevel,
)


# --- Schema SQL ---

ENGINE_SCHEMA_SQL = """
-- Schema version tracking for engine
CREATE TABLE IF NOT EXISTS engine_schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT
);

-- Job records per ADR-004
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    state TEXT NOT NULL DEFAULT 'queued'
        CHECK (state IN ('queued', 'running', 'cancelling',
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
    exit_code TEXT,
    error_code TEXT,
    error_message TEXT,
    error_details_json TEXT,

    -- Receipt (written on completion)
    receipt_json TEXT,
    receipt_hash TEXT,

    -- Idempotency
    idempotency_key TEXT UNIQUE,
    idempotency_expires_at TEXT,

    -- Worker claim tracking
    claim_attempts INTEGER DEFAULT 0,
    claimed_at TEXT,
    last_heartbeat_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_idempotency ON jobs(idempotency_key)
    WHERE idempotency_key IS NOT NULL;

-- Job events (logs, progress updates) per ADR-003/004
CREATE TABLE IF NOT EXISTS job_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT,  -- NULL for engine-level events
    sequence_number INTEGER NOT NULL UNIQUE,
    job_sequence INTEGER,
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

    -- Full event JSON for replay
    event_json TEXT NOT NULL,

    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_job_events_job_seq ON job_events(job_id, job_sequence);
CREATE INDEX IF NOT EXISTS idx_job_events_global_seq ON job_events(sequence_number);
CREATE INDEX IF NOT EXISTS idx_job_events_timestamp ON job_events(timestamp_utc);
CREATE INDEX IF NOT EXISTS idx_job_events_level ON job_events(job_id, level)
    WHERE level IN ('warn', 'error');

-- Artifacts (output files) per ADR-004
CREATE TABLE IF NOT EXISTS artifacts (
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

CREATE INDEX IF NOT EXISTS idx_artifacts_job ON artifacts(job_id);

-- Global sequence counter (singleton table)
CREATE TABLE IF NOT EXISTS sequence_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_sequence INTEGER NOT NULL DEFAULT 0
);

-- Initialize sequence state
INSERT OR IGNORE INTO sequence_state (id, last_sequence) VALUES (1, 0);
"""

SCHEMA_VERSION = 1


class EngineDatabase:
    """Database manager for engine spine.

    Implements persist-before-send pattern: events are persisted
    atomically with sequence numbers before being broadcast.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                isolation_level="DEFERRED",
                check_same_thread=False,  # We handle thread safety
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=30000")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def init_schema(self) -> None:
        """Initialize engine schema."""
        conn = self.connect()
        conn.executescript(ENGINE_SCHEMA_SQL)

        # Record schema version
        conn.execute(
            """
            INSERT OR REPLACE INTO engine_schema_version (version, applied_at, description)
            VALUES (?, ?, ?)
            """,
            (
                SCHEMA_VERSION,
                datetime.now(timezone.utc).isoformat(),
                "Initial engine schema",
            ),
        )
        conn.commit()

    def get_schema_version(self) -> int | None:
        """Get current schema version."""
        conn = self.connect()
        try:
            cursor = conn.execute("SELECT MAX(version) FROM engine_schema_version")
            row = cursor.fetchone()
            return row[0] if row and row[0] else None
        except sqlite3.OperationalError:
            return None

    # --- Persist-Before-Send Event System ---

    def persist_event(self, event: BaseEvent, job_id: str | None = None) -> EventRowId:
        """Persist event atomically with sequence number.

        This is the ONLY way to emit events. The broadcaster
        accepts EventRowId, not raw events.

        Returns:
            EventRowId that can be passed to broadcaster
        """
        conn = self.connect()

        with conn:
            # Atomically get next sequence number
            cursor = conn.execute(
                """
                UPDATE sequence_state
                SET last_sequence = last_sequence + 1
                WHERE id = 1
                RETURNING last_sequence
                """
            )
            sequence_number = cursor.fetchone()[0]

            # Update event with assigned sequence
            event.sequence_number = sequence_number

            # Get job_sequence if this is a job event
            job_sequence = None
            if job_id and hasattr(event, "job_sequence"):
                cursor = conn.execute(
                    """
                    SELECT COALESCE(MAX(job_sequence), 0) + 1
                    FROM job_events
                    WHERE job_id = ?
                    """,
                    (job_id,),
                )
                job_sequence = cursor.fetchone()[0]
                event.job_sequence = job_sequence

            # Extract fields for indexed columns
            level = getattr(event, "level", None)
            if isinstance(level, LogLevel):
                level = level.value

            # Insert event
            cursor = conn.execute(
                """
                INSERT INTO job_events (
                    job_id, sequence_number, job_sequence, timestamp_utc,
                    event_type, level, subsystem, message, payload_json,
                    correlation_id, phase, progress_percent, items_completed,
                    items_total, event_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                (
                    job_id,
                    sequence_number,
                    job_sequence,
                    event.timestamp_utc.isoformat(),
                    event.event_type,
                    level,
                    getattr(event, "subsystem", None),
                    getattr(event, "message", None),
                    json.dumps(getattr(event, "payload", None))
                    if hasattr(event, "payload")
                    else None,
                    getattr(event, "correlation_id", None),
                    getattr(event, "phase", None),
                    getattr(event, "progress_percent", None),
                    getattr(event, "items_completed", None),
                    getattr(event, "items_total", None),
                    event.model_dump_json(),
                ),
            )
            row_id = cursor.fetchone()[0]

        return EventRowId(row_id)

    def get_event_by_id(self, event_id: EventRowId) -> dict[str, Any] | None:
        """Get persisted event by row ID."""
        conn = self.connect()
        cursor = conn.execute(
            "SELECT event_json, sequence_number FROM job_events WHERE id = ?",
            (event_id,),
        )
        row = cursor.fetchone()
        if row:
            return {
                "event": json.loads(row["event_json"]),
                "sequence": row["sequence_number"],
            }
        return None

    def get_events_since(
        self,
        after_sequence: int,
        job_id: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Get events with sequence > after_sequence for replay."""
        conn = self.connect()

        if job_id:
            cursor = conn.execute(
                """
                SELECT event_json, sequence_number
                FROM job_events
                WHERE sequence_number > ? AND job_id = ?
                ORDER BY sequence_number
                LIMIT ?
                """,
                (after_sequence, job_id, limit),
            )
        else:
            cursor = conn.execute(
                """
                SELECT event_json, sequence_number
                FROM job_events
                WHERE sequence_number > ?
                ORDER BY sequence_number
                LIMIT ?
                """,
                (after_sequence, limit),
            )

        return [
            {"event": json.loads(row["event_json"]), "sequence": row["sequence_number"]}
            for row in cursor
        ]

    def get_current_sequence(self) -> int:
        """Get current global sequence number."""
        conn = self.connect()
        cursor = conn.execute("SELECT last_sequence FROM sequence_state WHERE id = 1")
        row = cursor.fetchone()
        return row[0] if row else 0

    # --- Job Management ---

    def create_job(
        self,
        job_id: str,
        config_json: str,
        config_hash: str,
        input_spec_json: str,
        workspace_path: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Create a new job in queued state."""
        conn = self.connect()
        now = datetime.now(timezone.utc).isoformat()

        with conn:
            cursor = conn.execute(
                """
                INSERT INTO jobs (
                    job_id, state, created_at, queued_at, updated_at,
                    config_json, config_hash, input_spec_json,
                    workspace_path, idempotency_key
                ) VALUES (?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (
                    job_id,
                    now,
                    now,
                    now,
                    config_json,
                    config_hash,
                    input_spec_json,
                    workspace_path,
                    idempotency_key,
                ),
            )
            row = cursor.fetchone()

        return dict(row)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Get job by ID."""
        conn = self.connect()
        cursor = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_job_by_idempotency_key(self, key: str) -> dict[str, Any] | None:
        """Get job by idempotency key."""
        conn = self.connect()
        cursor = conn.execute("SELECT * FROM jobs WHERE idempotency_key = ?", (key,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_jobs(
        self,
        states: list[JobState] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List jobs, optionally filtered by state."""
        conn = self.connect()

        if states:
            placeholders = ",".join("?" * len(states))
            cursor = conn.execute(
                f"""
                SELECT * FROM jobs
                WHERE state IN ({placeholders})
                ORDER BY created_at DESC
                LIMIT ?
                """,
                [s.value for s in states] + [limit],
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )

        return [dict(row) for row in cursor]

    def update_job_state(
        self,
        job_id: str,
        new_state: JobState,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Update job state with optional additional fields."""
        conn = self.connect()
        now = datetime.now(timezone.utc).isoformat()

        # Build update fields
        fields = ["state = ?", "updated_at = ?"]
        values: list[Any] = [new_state.value, now]

        # Handle state-specific timestamps
        if new_state == JobState.RUNNING:
            fields.append("started_at = ?")
            values.append(now)
        elif new_state in (JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED):
            fields.append("completed_at = ?")
            values.append(now)

        # Add extra fields
        for key, value in kwargs.items():
            if key.endswith("_json") and not isinstance(value, str):
                value = json.dumps(value)
            fields.append(f"{key} = ?")
            values.append(value)

        values.append(job_id)

        with conn:
            cursor = conn.execute(
                f"UPDATE jobs SET {', '.join(fields)} WHERE job_id = ? RETURNING *",
                values,
            )
            row = cursor.fetchone()

        return dict(row) if row else None

    def fetch_next_queued_job_id(self) -> str | None:
        """Fetch the next queued job ID (FIFO by created_at).

        Returns:
            Job ID if a queued job exists, None otherwise
        """
        conn = self.connect()
        cursor = conn.execute(
            """
            SELECT job_id FROM jobs
            WHERE state = 'queued'
            ORDER BY created_at ASC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        return row["job_id"] if row else None

    def claim_job(self, job_id: str) -> bool:
        """Attempt to claim a queued job for execution.

        Returns True if claim successful, False if already claimed.
        """
        conn = self.connect()
        now = datetime.now(timezone.utc).isoformat()

        with conn:
            cursor = conn.execute(
                """
                UPDATE jobs
                SET state = 'running',
                    started_at = ?,
                    updated_at = ?,
                    claimed_at = ?,
                    claim_attempts = claim_attempts + 1
                WHERE job_id = ? AND state = 'queued'
                RETURNING job_id
                """,
                (now, now, now, job_id),
            )
            return cursor.fetchone() is not None

    def release_job_claim(self, job_id: str) -> None:
        """Release claim on a job (return to queued)."""
        conn = self.connect()
        now = datetime.now(timezone.utc).isoformat()

        with conn:
            conn.execute(
                """
                UPDATE jobs
                SET state = 'queued',
                    started_at = NULL,
                    updated_at = ?,
                    claimed_at = NULL
                WHERE job_id = ? AND state = 'running'
                """,
                (now, job_id),
            )

    def update_job_progress(
        self,
        job_id: str,
        percent: int | None = None,
        phase: str | None = None,
        items_completed: int | None = None,
        items_total: int | None = None,
    ) -> None:
        """Update job progress fields."""
        conn = self.connect()
        now = datetime.now(timezone.utc).isoformat()

        fields = ["updated_at = ?", "last_heartbeat_at = ?"]
        values: list[Any] = [now, now]

        if percent is not None:
            fields.append("progress_percent = ?")
            values.append(percent)
        if phase is not None:
            fields.append("progress_phase = ?")
            values.append(phase)
        if items_completed is not None:
            fields.append("items_completed = ?")
            values.append(items_completed)
        if items_total is not None:
            fields.append("items_total = ?")
            values.append(items_total)

        values.append(job_id)

        with conn:
            conn.execute(
                f"UPDATE jobs SET {', '.join(fields)} WHERE job_id = ?",
                values,
            )

    def get_orphaned_jobs(self) -> list[dict[str, Any]]:
        """Find jobs stuck in running/cancelling state (crash recovery)."""
        conn = self.connect()
        cursor = conn.execute(
            "SELECT * FROM jobs WHERE state IN ('running', 'cancelling')"
        )
        return [dict(row) for row in cursor]

    def get_stale_claims(self, timeout_seconds: int = 30) -> list[dict[str, Any]]:
        """Find jobs that were claimed but never started."""
        conn = self.connect()
        cursor = conn.execute(
            """
            SELECT * FROM jobs
            WHERE state = 'running'
            AND started_at IS NOT NULL
            AND last_heartbeat_at < datetime('now', ?)
            """,
            (f"-{timeout_seconds} seconds",),
        )
        return [dict(row) for row in cursor]

    # --- Artifact Management ---

    def register_artifact(
        self,
        job_id: str,
        name: str,
        path: str,
        artifact_type: str,
    ) -> int:
        """Register a pending artifact."""
        conn = self.connect()
        now = datetime.now(timezone.utc).isoformat()

        with conn:
            cursor = conn.execute(
                """
                INSERT INTO artifacts (job_id, name, path, artifact_type, created_at)
                VALUES (?, ?, ?, ?, ?)
                RETURNING id
                """,
                (job_id, name, path, artifact_type, now),
            )
            return cursor.fetchone()[0]

    def complete_artifact(
        self,
        artifact_id: int,
        size_bytes: int,
        sha256: str,
    ) -> None:
        """Mark artifact as complete with hash."""
        conn = self.connect()
        now = datetime.now(timezone.utc).isoformat()

        with conn:
            conn.execute(
                """
                UPDATE artifacts
                SET status = 'complete', size_bytes = ?, sha256 = ?, verified_at = ?
                WHERE id = ?
                """,
                (size_bytes, sha256, now, artifact_id),
            )

    def get_job_artifacts(self, job_id: str) -> list[dict[str, Any]]:
        """Get all artifacts for a job."""
        conn = self.connect()
        cursor = conn.execute("SELECT * FROM artifacts WHERE job_id = ?", (job_id,))
        return [dict(row) for row in cursor]

    # --- Cleanup ---

    def delete_events_before(self, cutoff: datetime, keep_errors: bool = True) -> int:
        """Delete events older than cutoff. Returns count deleted."""
        conn = self.connect()

        if keep_errors:
            cursor = conn.execute(
                """
                DELETE FROM job_events
                WHERE timestamp_utc < ?
                AND level NOT IN ('warn', 'error')
                """,
                (cutoff.isoformat(),),
            )
        else:
            cursor = conn.execute(
                "DELETE FROM job_events WHERE timestamp_utc < ?",
                (cutoff.isoformat(),),
            )

        conn.commit()
        return cursor.rowcount

    def vacuum(self) -> None:
        """Reclaim space."""
        conn = self.connect()
        conn.execute("PRAGMA incremental_vacuum(1000)")

    def check_integrity(self) -> bool:
        """Check database integrity."""
        conn = self.connect()
        cursor = conn.execute("PRAGMA quick_check")
        result = cursor.fetchone()
        return result[0] == "ok"
