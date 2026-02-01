# STORY-005a: Job API Core (Create/List/Read)

**Epic**: Desktop App Architecture
**ADRs**: ADR-003, ADR-004
**Priority**: P0 (Core Functionality)
**Depends On**: STORY-001 (Auth Middleware), STORY-004 (Job Schema)
**Estimate**: 2 days

> **Split Note**: Original STORY-005 split for tighter scope.
> - **005a** (this): Create, List, Read — core job lifecycle
> - **005b**: Cancel, Logs, Artifacts — job operations

---

## Design Decision: Create = Start (Atomic)

**Choice**: `POST /v1/jobs` creates AND queues the job atomically.

```
POST /v1/jobs → job created in "queued" state → execution begins
```

**NOT**:
```
POST /v1/jobs → "draft" state
POST /v1/jobs/{id}/start → "queued" state
```

**Rationale**:
- Simpler mental model for v1
- No orphaned drafts cluttering the database
- "Drafts" are really UI-side presets/templates (not engine concern)
- Replay/retry always creates a new job (no draft resurrection)

**Future Extension**: If needed, add `options.start_immediately: false` to defer start.
For now, every created job is immediately queued.

---

## User Story

**As a** GUI developer,
**I want** REST API endpoints to create and view jobs,
**So that** I can start translation jobs and check their status.

---

## Acceptance Criteria

### AC-1: Create Job (Atomic Create+Start)
- [ ] `POST /v1/jobs` creates AND queues a job atomically
- [ ] Job starts in `queued` state (never `draft`)
- [ ] Accepts input spec, config, and options
- [ ] Returns job_id, state (`queued`), created_at, queue_position
- [ ] Assigns `run_id` immediately (for correlation)
- [ ] Idempotency key prevents duplicates (returns existing job)
- [ ] Validates config before accepting (422 on invalid)
- [ ] Path validation via ADR-005 allowlist

### AC-2: List Jobs
- [ ] `GET /v1/jobs` returns paginated job list
- [ ] Default: 50 items, sorted by created_at DESC
- [ ] Supports filters: `state`, `created_after`, `created_before`
- [ ] Supports search by job_id prefix
- [ ] Returns summary (id, state, created_at, progress_percent, error_code)

### AC-3: Get Job Detail
- [ ] `GET /v1/jobs/{job_id}` returns full job detail
- [ ] Includes: config, progress, error (if any), artifact list
- [ ] Does NOT include logs (separate endpoint in 005b)
- [ ] 404 if job not found

### AC-4: Validation Error Responses
- [ ] Invalid config returns 422 with field-level errors
- [ ] Path not in allowlist returns 403 with actionable message
- [ ] Missing required fields return clear error messages

---

## Technical Design

### Endpoint Definitions

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Literal

router = APIRouter(prefix="/v1/jobs", dependencies=[Depends(require_auth)])

@router.post("", status_code=201)
async def create_job(request: CreateJobRequest) -> CreateJobResponse:
    """Create a new translation job."""
    # Validate paths
    validate_input_paths(request.inputs)
    if request.config.output_dir:
        validate_output_path(request.config.output_dir)

    # Check idempotency
    if request.idempotency_key:
        existing = await find_by_idempotency_key(request.idempotency_key)
        if existing:
            return existing  # Return existing job

    # Create job
    job = await create_job_record(request)
    return CreateJobResponse(
        job_id=job.job_id,
        state=job.state,
        created_at=job.created_at,
        queue_position=await get_queue_position(job.job_id)
    )

@router.get("")
async def list_jobs(
    state: str | None = Query(None, description="Filter by state"),
    created_after: datetime | None = Query(None),
    created_before: datetime | None = Query(None),
    search: str | None = Query(None, description="Search by job_id prefix"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200)
) -> ListJobsResponse:
    """List jobs with optional filters."""
    jobs, total = await query_jobs(
        state=state,
        created_after=created_after,
        created_before=created_before,
        search=search,
        offset=offset,
        limit=limit
    )
    return ListJobsResponse(jobs=jobs, total=total, offset=offset, limit=limit)

@router.get("/{job_id}")
async def get_job(job_id: str) -> JobDetail:
    """Get full job details."""
    job = await find_job(job_id)
    if not job:
        raise HTTPException(404, detail={
            "error_code": "E_JOB_NOT_FOUND",
            "message": f"Job not found: {job_id}"
        })
    return job
```

### Request/Response Schemas

```python
class CreateJobRequest(BaseModel):
    idempotency_key: str | None = Field(None, max_length=128)
    inputs: list[InputSpec] = Field(..., min_length=1)
    config: JobConfig
    options: JobOptions | None = None

class InputSpec(BaseModel):
    type: Literal["reference", "file"]
    reference: str | None = None  # "Luke 1-24"
    file_path: str | None = None

    @model_validator(mode="after")
    def check_input(self):
        if self.type == "reference" and not self.reference:
            raise ValueError("reference required when type=reference")
        if self.type == "file" and not self.file_path:
            raise ValueError("file_path required when type=file")
        return self

class JobConfig(BaseModel):
    profile: str = "default"
    format: Literal["json", "xml"] = "json"
    styles: list[str] = Field(
        default=["ultra-literal", "natural", "meaning-first", "jewish-context"]
    )
    include_receipts: bool = True
    output_dir: str | None = None

class CreateJobResponse(BaseModel):
    job_id: str
    state: str
    created_at: datetime
    queue_position: int | None = None
    config_hash: str

class JobSummary(BaseModel):
    job_id: str
    state: str
    created_at: datetime
    progress_percent: int | None
    progress_phase: str | None
    error_code: str | None

class ListJobsResponse(BaseModel):
    jobs: list[JobSummary]
    total: int
    offset: int
    limit: int

class JobDetail(BaseModel):
    job_id: str
    run_id: str
    state: str
    priority: str
    created_at: datetime
    queued_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    config: JobConfig
    input_spec: list[InputSpec]
    progress_percent: int | None
    progress_phase: str | None
    error_code: str | None
    error_message: str | None
    workspace_path: str | None
    artifacts: list[ArtifactSummary]
```

### Files Changed/Created

- `src/redletters/engine/api/jobs.py` — Job endpoints
- `src/redletters/engine/api/schemas.py` — Pydantic models
- `src/redletters/engine/services/job_service.py` — Business logic

---

## Test Plan

| Test | Type | Description |
|------|------|-------------|
| `test_create_job_returns_201` | Integration | Happy path |
| `test_create_job_validates_config` | Integration | Invalid config → 422 |
| `test_create_job_validates_paths` | Integration | Path not allowed → 403 |
| `test_idempotency_key_returns_existing` | Integration | Same key → same job |
| `test_list_jobs_pagination` | Integration | Offset/limit work |
| `test_list_jobs_filter_by_state` | Integration | State filter |
| `test_list_jobs_filter_by_date` | Integration | Date range filter |
| `test_list_jobs_search` | Integration | job_id prefix search |
| `test_get_job_returns_detail` | Integration | Happy path |
| `test_get_job_not_found` | Integration | 404 response |

---

## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Tests written and passing
- [ ] OpenAPI schema generated and reviewed
- [ ] Error responses follow standard format
- [ ] Path validation integrated with ADR-005 allowlist
- [ ] Idempotency works correctly
