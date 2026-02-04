"""Pydantic models for Engine Spine events and data structures.

All event models follow ADR-003 event schema.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, NewType, Optional

from pydantic import BaseModel, Field

# Type-safe wrapper for persisted event row IDs
# Broadcaster ONLY accepts this type, not raw events
EventRowId = NewType("EventRowId", int)


class JobState(str, Enum):
    """Job state machine states per ADR-004."""

    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class EngineMode(str, Enum):
    """Engine operating modes."""

    NORMAL = "normal"
    SAFE = "safe"


class EngineHealth(str, Enum):
    """Engine health states."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"


class LogLevel(str, Enum):
    """Log levels for job events."""

    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


# --- Request/Response Models ---


class JobType(str, Enum):
    """Job type discriminator for executor routing."""

    TRANSLATION = "translation"
    SCHOLARLY = "scholarly"


class JobConfig(BaseModel):
    """Job configuration submitted with POST /v1/jobs."""

    # Job type discriminator (Sprint 18)
    job_type: JobType = Field(JobType.TRANSLATION, description="Job type")

    # Required fields for translation jobs
    input_paths: List[str] = Field(
        default_factory=list, description="Paths to input files"
    )

    # Optional configuration
    output_dir: Optional[str] = Field(None, description="Output directory override")
    style: str = Field("natural", description="Rendering style")
    options: Dict[str, Any] = Field(
        default_factory=dict, description="Additional options"
    )

    # Scholarly job fields (Sprint 18) - only used when job_type == SCHOLARLY
    reference: Optional[str] = Field(
        None, description="Scripture reference for scholarly jobs"
    )
    mode: str = Field("traceable", description="Translation mode: readable/traceable")
    force: bool = Field(False, description="Bypass pending gates")
    session_id: Optional[str] = Field(None, description="Session ID for gate tracking")
    include_schemas: bool = Field(False, description="Include JSON schemas in bundle")
    create_zip: bool = Field(False, description="Create zip archive of bundle")


class JobCreateRequest(BaseModel):
    """Request body for POST /v1/jobs."""

    config: JobConfig
    idempotency_key: Optional[str] = Field(
        None, description="Client-provided idempotency key"
    )


class JobResponse(BaseModel):
    """Response for job creation and retrieval."""

    job_id: str
    state: JobState
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    config: JobConfig
    progress_percent: Optional[int] = None
    progress_phase: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    # Sprint 18: Scholarly job result payload (populated for completed scholarly jobs)
    result: Optional[Dict[str, Any]] = Field(
        None, description="Job result payload (type depends on job_type)"
    )


class BackendShape(BaseModel):
    """Backend shape for GUI compatibility detection.

    Sprint 19: Guardrail against backend mode mismatch.
    Populated by introspecting app.routes at startup.
    """

    backend_mode: str = Field(
        "full", description="Backend mode: 'full' (unified) or 'engine_only'"
    )
    has_translate: bool = Field(True, description="Whether /translate route exists")
    has_sources_status: bool = Field(
        True, description="Whether /sources/status route exists"
    )
    has_acknowledge: bool = Field(True, description="Whether /acknowledge route exists")
    has_variants_dossier: bool = Field(
        True, description="Whether /variants/dossier route exists"
    )


class EngineStatus(BaseModel):
    """Response for GET /v1/engine/status."""

    version: str
    build_hash: str
    api_version: str = "v1"
    capabilities: List[str] = Field(default_factory=list)
    mode: EngineMode = EngineMode.NORMAL
    health: EngineHealth = EngineHealth.HEALTHY
    uptime_seconds: float = 0.0
    active_jobs: int = 0
    queue_depth: int = 0

    # Sprint 19: Backend shape for GUI mismatch detection
    shape: Optional[BackendShape] = Field(
        None, description="Backend route shape for compatibility detection"
    )


# --- Event Models (SSE) ---


class BaseEvent(BaseModel):
    """Base event model per ADR-003."""

    event_type: str
    sequence_number: int
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_sse_data(self) -> str:
        """Serialize for SSE data field."""
        return self.model_dump_json()


class EngineHeartbeat(BaseEvent):
    """Engine heartbeat event - emitted every 3 seconds."""

    event_type: str = "engine.heartbeat"
    uptime_ms: int
    health: EngineHealth = EngineHealth.HEALTHY
    active_jobs: int = 0
    queue_depth: int = 0


class EngineShuttingDown(BaseEvent):
    """Engine shutdown notification."""

    event_type: str = "engine.shutting_down"
    reason: str  # "user_request", "update", "error"
    grace_period_ms: int


class JobStateChanged(BaseEvent):
    """Job state transition event."""

    event_type: str = "job.state_changed"
    job_id: str
    old_state: Optional[JobState]
    new_state: JobState


class JobProgress(BaseEvent):
    """Job progress update."""

    event_type: str = "job.progress"
    job_id: str
    job_sequence: int  # Per-job ordering
    phase: str
    progress_percent: Optional[int] = None
    items_completed: Optional[int] = None
    items_total: Optional[int] = None
    eta_seconds: Optional[int] = None


class JobLog(BaseEvent):
    """Job log entry."""

    event_type: str = "job.log"
    job_id: str
    job_sequence: int  # Per-job ordering
    level: LogLevel
    subsystem: str
    message: str
    payload: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None


class JobQueueHeartbeat(BaseEvent):
    """Queue heartbeat for waiting jobs."""

    event_type: str = "job.queue_heartbeat"
    job_id: str
    queue_position: int
    estimated_wait_seconds: Optional[int] = None
    claim_attempts: int = 0


class ReplayChunk(BaseEvent):
    """Chunked replay for large event replays."""

    event_type: str = "replay.chunk"
    events: List[Dict[str, Any]]
    has_more: bool


class ReplayComplete(BaseEvent):
    """Marks end of replay, transition to live."""

    event_type: str = "replay.complete"
    replayed_count: int
    now_live: bool = True


# --- Receipt Models ---


class ArtifactInfo(BaseModel):
    """Artifact metadata for receipts."""

    path: str
    size_bytes: int
    sha256: str


class ReceiptTimestamps(BaseModel):
    """Timestamps section of receipt."""

    created: datetime
    started: Optional[datetime] = None
    completed: Optional[datetime] = None


class JobReceipt(BaseModel):
    """Immutable receipt for completed/failed/cancelled jobs.

    Written as receipt.json in workspace, chmod 444.
    """

    schema_version: str = "1.0"
    job_id: str
    run_id: str
    receipt_status: str  # "completed", "failed", "cancelled"
    exit_code: Optional[str] = None  # e.g., "E_ENGINE_CRASH"

    timestamps: ReceiptTimestamps
    config_snapshot: Dict[str, Any]
    source_pins: Dict[str, str]  # source_name -> version/hash

    outputs: List[ArtifactInfo] = Field(default_factory=list)
    inputs_summary: Dict[str, Any] = Field(default_factory=dict)

    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


# --- Error Response ---


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


# --- Scholarly Run Models (v0.14.0) ---


class ScholarlyRunRequest(BaseModel):
    """Request body for POST /run/scholarly."""

    reference: str = Field(..., description="Scripture reference (e.g., 'John 1:1-18')")
    mode: str = Field(
        "traceable", description="Translation mode: 'readable' or 'traceable'"
    )
    force: bool = Field(
        False, description="Bypass pending gates with responsibility recorded"
    )
    session_id: Optional[str] = Field(
        None, description="Session ID for acknowledgement tracking"
    )
    include_schemas: bool = Field(False, description="Include JSON schemas in bundle")
    create_zip: bool = Field(False, description="Create zip archive of bundle")


class ScholarlyRunResponse(BaseModel):
    """Response for POST /run/scholarly (async job mode)."""

    success: bool
    job_id: str
    reference: str
    mode: str
    force: bool
    session_id: str
    message: str


class ScholarlyJobResult(BaseModel):
    """Result payload for completed scholarly jobs (stored in receipt).

    Sprint 18: Jobs-first scholarly runs.
    """

    # Outcome status
    success: bool
    gate_blocked: bool = False
    pending_gates: List[str] = Field(default_factory=list)

    # Output artifacts (if successful)
    output_dir: Optional[str] = None
    bundle_path: Optional[str] = None

    # Run log summary (if successful)
    run_log_summary: Optional[Dict[str, Any]] = None

    # Error details (if failed)
    errors: List[str] = Field(default_factory=list)

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
