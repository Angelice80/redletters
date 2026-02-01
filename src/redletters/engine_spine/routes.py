"""FastAPI routes for Engine Spine per ADR-003/004/005 and Sprint-1-DOD."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from redletters.engine_spine.middleware import require_auth
from redletters.engine_spine.models import (
    EngineStatus,
    JobCreateRequest,
    JobResponse,
    JobState,
)
from redletters.engine_spine.status import get_engine_state
from redletters.engine_spine.stream import (
    create_sse_response,
    parse_last_event_id,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["engine"])


# --- Engine Status ---


@router.get(
    "/engine/status",
    response_model=EngineStatus,
    summary="Get engine status",
    description="Returns engine version, build hash, API version, capabilities, mode, and health.",
)
async def get_engine_status(_: None = Depends(require_auth)) -> EngineStatus:
    """GET /v1/engine/status - Engine status per Sprint-1-DOD."""
    state = get_engine_state()
    if not state.is_initialized or not state.status_manager:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    return state.status_manager.get_status()


# --- SSE Streaming ---


@router.get(
    "/stream",
    summary="SSE event stream",
    description="Server-Sent Events stream with at-least-once delivery and replay support.",
)
async def stream_events(
    request: Request,
    resume_from: Optional[int] = Query(None, description="Resume from sequence number"),
    job_id: Optional[str] = Query(None, description="Filter events by job ID"),
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    _: None = Depends(require_auth),
):
    """GET /v1/stream - SSE stream per ADR-003."""
    state = get_engine_state()
    if not state.is_initialized or not state.broadcaster:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    # Prefer Last-Event-ID header over query param
    from_sequence = parse_last_event_id(last_event_id) or resume_from

    from redletters.engine_spine.broadcaster import ReplayBuffer

    replay_buffer = ReplayBuffer(state.db)

    return create_sse_response(
        broadcaster=state.broadcaster,
        replay_buffer=replay_buffer,
        resume_from=from_sequence,
        job_id=job_id,
    )


# --- Job Management ---


@router.post(
    "/jobs",
    response_model=JobResponse,
    status_code=201,
    summary="Create a new job",
    description="Creates job in queued state. Job starts immediately when resources available.",
    responses={
        201: {"description": "Job created"},
        503: {"description": "Engine in safe mode - jobs disabled"},
    },
)
async def create_job(
    request: JobCreateRequest,
    _: None = Depends(require_auth),
) -> JobResponse:
    """POST /v1/jobs - Create job per Sprint-1-DOD."""
    state = get_engine_state()
    if not state.is_initialized:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    # Import here to avoid circular imports
    from redletters.engine_spine.jobs import JobManager
    from pathlib import Path

    # Check safe mode
    if state.status_manager and state.status_manager.is_safe_mode:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "E_SAFE_MODE",
                "code": "safe_mode",
                "message": "Engine in safe mode. Jobs disabled.",
            },
        )

    # Create job manager
    workspace_base = Path("~/.greek2english/workspaces").expanduser()
    job_manager = JobManager(
        db=state.db,
        broadcaster=state.broadcaster,
        workspace_base=workspace_base,
        safe_mode=state.status_manager.is_safe_mode if state.status_manager else False,
    )

    return await job_manager.create_job(
        config=request.config,
        idempotency_key=request.idempotency_key,
    )


@router.get(
    "/jobs",
    response_model=List[JobResponse],
    summary="List jobs",
    description="List jobs with optional state filter.",
)
async def list_jobs(
    state_filter: Optional[List[JobState]] = Query(None, alias="state"),
    limit: int = Query(100, le=1000),
    _: None = Depends(require_auth),
) -> List[JobResponse]:
    """GET /v1/jobs - List jobs."""
    engine_state = get_engine_state()
    if not engine_state.is_initialized:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    from redletters.engine_spine.jobs import JobManager
    from pathlib import Path

    workspace_base = Path("~/.greek2english/workspaces").expanduser()
    job_manager = JobManager(
        db=engine_state.db,
        broadcaster=engine_state.broadcaster,
        workspace_base=workspace_base,
    )

    return await job_manager.list_jobs(states=state_filter, limit=limit)


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get job details",
    responses={404: {"description": "Job not found"}},
)
async def get_job(
    job_id: str,
    _: None = Depends(require_auth),
) -> JobResponse:
    """GET /v1/jobs/{job_id} - Get job by ID."""
    engine_state = get_engine_state()
    if not engine_state.is_initialized:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    from redletters.engine_spine.jobs import JobManager
    from pathlib import Path

    workspace_base = Path("~/.greek2english/workspaces").expanduser()
    job_manager = JobManager(
        db=engine_state.db,
        broadcaster=engine_state.broadcaster,
        workspace_base=workspace_base,
    )

    job = await job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return job


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=JobResponse,
    summary="Cancel a job",
    responses={404: {"description": "Job not found"}},
)
async def cancel_job(
    job_id: str,
    _: None = Depends(require_auth),
) -> JobResponse:
    """POST /v1/jobs/{job_id}/cancel - Cancel job."""
    engine_state = get_engine_state()
    if not engine_state.is_initialized:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    from redletters.engine_spine.jobs import JobManager
    from pathlib import Path

    workspace_base = Path("~/.greek2english/workspaces").expanduser()
    job_manager = JobManager(
        db=engine_state.db,
        broadcaster=engine_state.broadcaster,
        workspace_base=workspace_base,
    )

    receipt = await job_manager.cancel_job(job_id)
    if not receipt:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    job = await job_manager.get_job(job_id)
    return job


# --- Engine Control ---


@router.post(
    "/engine/shutdown",
    summary="Request engine shutdown",
    description="Request graceful engine shutdown with optional grace period.",
)
async def request_shutdown(
    reason: str = Query("user_request"),
    grace_period_ms: int = Query(30000),
    _: None = Depends(require_auth),
):
    """POST /v1/engine/shutdown - Request graceful shutdown."""
    state = get_engine_state()
    if not state.is_initialized or not state.status_manager:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    # Emit shutdown event
    await state.status_manager.emit_shutdown_event(reason, grace_period_ms)

    return {
        "status": "shutdown_requested",
        "reason": reason,
        "grace_period_ms": grace_period_ms,
    }


# --- Job Receipt ---


@router.get(
    "/jobs/{job_id}/receipt",
    summary="Get job receipt",
    description="Get the immutable receipt for a completed/failed/cancelled job.",
    responses={
        404: {"description": "Job not found or receipt not available"},
    },
)
async def get_job_receipt(
    job_id: str,
    _: None = Depends(require_auth),
):
    """GET /v1/jobs/{job_id}/receipt - Get job receipt."""
    import json
    from pathlib import Path

    engine_state = get_engine_state()
    if not engine_state.is_initialized:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    # Get job from database
    job_dict = engine_state.db.get_job(job_id)
    if not job_dict:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # Check if receipt exists in database
    receipt_json = job_dict.get("receipt_json")
    if receipt_json:
        return json.loads(receipt_json)

    # Try to read from workspace file
    workspace_path = job_dict.get("workspace_path")
    if workspace_path:
        receipt_path = Path(workspace_path) / "receipt.json"
        if receipt_path.exists():
            return json.loads(receipt_path.read_text())

    # No receipt available
    raise HTTPException(
        status_code=404,
        detail=f"Receipt not available for job {job_id}. "
        "Job may still be in progress or receipt was not generated.",
    )


# --- Diagnostics ---


@router.post(
    "/diagnostics/export",
    summary="Export diagnostics bundle",
    description="Export a diagnostics bundle with integrity report.",
)
async def export_diagnostics(
    full_integrity: bool = Query(
        False, description="Hash all files regardless of size"
    ),
    _: None = Depends(require_auth),
):
    """POST /v1/diagnostics/export - Export diagnostics bundle."""
    from datetime import datetime
    from pathlib import Path

    from redletters.engine_spine.diagnostics import DiagnosticsExporter

    engine_state = get_engine_state()
    if not engine_state.is_initialized:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    # Generate output path
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = Path(f"~/.greek2english/diagnostics/bundle-{timestamp}").expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create exporter and generate bundle
    exporter = DiagnosticsExporter(
        db=engine_state.db,
        status_manager=engine_state.status_manager,
    )

    # Generate integrity report (without exporting full bundle for now)
    report = exporter.generate_integrity_report(full_integrity=full_integrity)

    # Export the bundle
    bundle_path = exporter.export_bundle(
        output_path=output_path,
        as_zip=True,
        full_integrity=full_integrity,
    )

    return {
        "path": str(bundle_path),
        "report": {
            "generated_at": report.generated_at.isoformat(),
            "full_integrity_mode": report.full_integrity_mode,
            "size_threshold_bytes": report.size_threshold_bytes,
            "summary": report.summary,
            "failures": report.failures,
        },
    }
