# STORY-005b: Job API Operations (Cancel/Logs/Artifacts)

**Epic**: Desktop App Architecture
**ADRs**: ADR-003, ADR-004
**Priority**: P0 (Core Functionality)
**Depends On**: STORY-005a (Job API Core), STORY-009 (Receipts)
**Estimate**: 1.5 days

> **Split Note**: Original STORY-005 split for tighter scope.
> - **005a**: Create, List, Read — core job lifecycle
> - **005b** (this): Cancel, Logs, Artifacts — job operations

---

## User Story

**As a** GUI developer,
**I want** REST API endpoints to cancel jobs and retrieve logs/artifacts,
**So that** I can manage running jobs and investigate completed ones.

---

## Acceptance Criteria

### AC-1: Cancel Job
- [ ] `POST /v1/jobs/{job_id}/cancel` initiates cancellation
- [ ] Returns immediately (cancellation is async)
- [ ] Job transitions: `running` → `cancelling` → `cancelled`
- [ ] Emits `job.state_changed` events
- [ ] Queued jobs cancel immediately (no `cancelling` state)
- [ ] Already-cancelled jobs return 200 (idempotent)
- [ ] Completed/failed jobs return 409 (conflict)

### AC-2: Get Job Logs
- [ ] `GET /v1/jobs/{job_id}/logs` returns historical logs
- [ ] Supports pagination: `offset`, `limit` (default 1000)
- [ ] Supports level filter: `level=warn,error`
- [ ] Returns in `job_sequence` order
- [ ] 404 if job not found

### AC-3: Get Job Artifacts
- [ ] `GET /v1/jobs/{job_id}/artifacts` returns artifact list
- [ ] Each artifact includes: name, path, type, size, sha256, status
- [ ] Status indicates: pending, complete, failed, quarantined
- [ ] 404 if job not found

### AC-4: Get Job Receipt
- [ ] `GET /v1/jobs/{job_id}/receipt` returns receipt JSON
- [ ] Available for: completed, failed, cancelled jobs
- [ ] Returns 404 if job running or receipt not yet generated
- [ ] Includes `Content-Disposition` header for download

---

## Technical Design

### Endpoint Definitions

```python
@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str) -> CancelResponse:
    """Request job cancellation."""
    job = await find_job(job_id)
    if not job:
        raise HTTPException(404, detail={"error_code": "E_JOB_NOT_FOUND"})

    if job.state in ("completed", "failed"):
        raise HTTPException(409, detail={
            "error_code": "E_JOB_ALREADY_FINISHED",
            "message": f"Cannot cancel {job.state} job"
        })

    if job.state in ("cancelled", "cancelling"):
        return CancelResponse(
            job_id=job_id,
            state=job.state,
            message="Job already cancelling or cancelled"
        )

    # Initiate cancellation
    await request_cancellation(job_id)

    return CancelResponse(
        job_id=job_id,
        state="cancelling",
        message="Cancellation requested"
    )

@router.get("/{job_id}/logs")
async def get_logs(
    job_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=10000),
    level: str | None = Query(None, description="Comma-separated: trace,debug,info,warn,error")
) -> LogsResponse:
    """Get historical job logs."""
    job = await find_job(job_id)
    if not job:
        raise HTTPException(404, detail={"error_code": "E_JOB_NOT_FOUND"})

    levels = level.split(",") if level else None
    logs, total = await query_job_events(
        job_id=job_id,
        levels=levels,
        offset=offset,
        limit=limit
    )

    return LogsResponse(
        logs=logs,
        total=total,
        offset=offset,
        limit=limit,
        has_more=offset + len(logs) < total
    )

@router.get("/{job_id}/artifacts")
async def get_artifacts(job_id: str) -> ArtifactsResponse:
    """Get job artifacts."""
    job = await find_job(job_id)
    if not job:
        raise HTTPException(404, detail={"error_code": "E_JOB_NOT_FOUND"})

    artifacts = await query_artifacts(job_id)
    return ArtifactsResponse(artifacts=artifacts)

@router.get("/{job_id}/receipt")
async def get_receipt(
    job_id: str,
    response: Response
) -> Receipt:
    """Get job receipt (terminal jobs only)."""
    job = await find_job(job_id)
    if not job:
        raise HTTPException(404, detail={"error_code": "E_JOB_NOT_FOUND"})

    if job.state not in ("completed", "failed", "cancelled"):
        raise HTTPException(404, detail={
            "error_code": "E_RECEIPT_NOT_READY",
            "message": f"Receipt not available for {job.state} job"
        })

    if not job.receipt_json:
        raise HTTPException(404, detail={
            "error_code": "E_RECEIPT_NOT_GENERATED",
            "message": "Receipt has not been generated yet"
        })

    response.headers["Content-Disposition"] = (
        f'attachment; filename="receipt-{job_id}.json"'
    )
    return Receipt.model_validate_json(job.receipt_json)
```

### Response Schemas

```python
class CancelResponse(BaseModel):
    job_id: str
    state: str
    message: str

class LogEntry(BaseModel):
    id: int
    job_sequence: int
    timestamp_utc: datetime
    level: str
    subsystem: str
    message: str
    payload: dict | None = None
    correlation_id: str | None = None

class LogsResponse(BaseModel):
    logs: list[LogEntry]
    total: int
    offset: int
    limit: int
    has_more: bool

class ArtifactSummary(BaseModel):
    id: int
    name: str
    path: str
    artifact_type: str
    size_bytes: int | None
    sha256: str | None
    status: str
    created_at: datetime

class ArtifactsResponse(BaseModel):
    artifacts: list[ArtifactSummary]
```

### Cancellation Flow

```python
async def request_cancellation(job_id: str):
    """Request async cancellation of a job."""
    job = await find_job(job_id)

    if job.state == "queued":
        # Queued jobs cancel immediately
        await update_job_state(job_id, "cancelled")
        await emit_event("job.state_changed", job_id=job_id,
                         old_state="queued", new_state="cancelled")
    else:
        # Running jobs need graceful stop
        await update_job_state(job_id, "cancelling")
        await emit_event("job.state_changed", job_id=job_id,
                         old_state="running", new_state="cancelling")
        # Job executor will check this flag and stop at next checkpoint
```

### Files Changed/Created

- `src/redletters/engine/api/jobs.py` — Add cancel/logs/artifacts endpoints
- `src/redletters/engine/services/cancellation.py` — Cancellation logic

---

## Test Plan

| Test | Type | Description |
|------|------|-------------|
| `test_cancel_running_job` | Integration | State → cancelling |
| `test_cancel_queued_job` | Integration | State → cancelled (immediate) |
| `test_cancel_completed_job_fails` | Integration | 409 response |
| `test_cancel_is_idempotent` | Integration | Cancel twice → OK |
| `test_get_logs_pagination` | Integration | Offset/limit work |
| `test_get_logs_level_filter` | Integration | Only warn/error returned |
| `test_get_logs_ordered_by_sequence` | Integration | Correct order |
| `test_get_artifacts_list` | Integration | All artifacts returned |
| `test_get_receipt_completed_job` | Integration | Receipt returned |
| `test_get_receipt_running_job_fails` | Integration | 404 response |

---

## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Tests written and passing
- [ ] Cancel emits correct events
- [ ] Logs pagination works correctly
- [ ] Receipt download works (Content-Disposition)
- [ ] OpenAPI schema updated
