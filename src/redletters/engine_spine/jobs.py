"""Job lifecycle management per ADR-004."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import stat
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from redletters.engine_spine.models import (
    ArtifactInfo,
    EventRowId,
    JobConfig,
    JobLog,
    JobProgress,
    JobReceipt,
    JobResponse,
    JobState,
    JobStateChanged,
    LogLevel,
    ReceiptTimestamps,
)

if TYPE_CHECKING:
    from redletters.engine_spine.broadcaster import EventBroadcaster
    from redletters.engine_spine.database import EngineDatabase

logger = logging.getLogger(__name__)

# Timeouts per ADR-004
CLAIM_TIMEOUT_SECONDS = 30
HEARTBEAT_TIMEOUT_SECONDS = 30
MAX_CLAIM_ATTEMPTS = 3


def generate_job_id() -> str:
    """Generate a unique job ID.

    Format: job_YYYYMMDD_HHMMSS_xxxx
    """
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    return f"job_{timestamp}_{suffix}"


def generate_run_id() -> str:
    """Generate a unique run ID for receipts."""
    return uuid.uuid4().hex


class JobManager:
    """Manages job lifecycle: creation, execution, completion.

    Implements ADR-004 state machine and ADR-003 event emission.
    """

    def __init__(
        self,
        db: "EngineDatabase",
        broadcaster: "EventBroadcaster",
        workspace_base: Path,
        safe_mode: bool = False,
    ):
        self._db = db
        self._broadcaster = broadcaster
        self._workspace_base = workspace_base
        self._safe_mode = safe_mode

        # Track running jobs
        self._running_jobs: dict[str, asyncio.Task] = {}

    @property
    def is_safe_mode(self) -> bool:
        """Check if jobs are disabled."""
        return self._safe_mode

    def get_job_counts(self) -> tuple[int, int]:
        """Get (active_jobs, queue_depth) counts."""
        jobs = self._db.list_jobs()
        active = sum(1 for j in jobs if j["state"] == JobState.RUNNING.value)
        queued = sum(1 for j in jobs if j["state"] == JobState.QUEUED.value)
        return active, queued

    async def create_job(
        self,
        config: JobConfig,
        idempotency_key: str | None = None,
    ) -> JobResponse:
        """Create a new job in queued state.

        Per Sprint-1-DOD: POST /v1/jobs creates job atomically.
        No draft state - job is immediately queued.

        Args:
            config: Job configuration
            idempotency_key: Optional idempotency key

        Returns:
            JobResponse with created job

        Raises:
            ValueError: If idempotency key already exists (returns existing job)
        """
        # Check idempotency
        if idempotency_key:
            existing = self._db.get_job_by_idempotency_key(idempotency_key)
            if existing:
                return self._job_dict_to_response(existing)

        # Generate IDs
        job_id = generate_job_id()

        # Create workspace
        workspace_path = self._workspace_base / job_id
        workspace_path.mkdir(parents=True, exist_ok=True)
        (workspace_path / "input").mkdir()
        (workspace_path / "output").mkdir()
        (workspace_path / "temp").mkdir()

        # Prepare job data
        config_json = config.model_dump_json()
        config_hash = hashlib.sha256(config_json.encode()).hexdigest()[:16]
        input_spec_json = json.dumps({"paths": config.input_paths})

        # Create job record
        job_dict = self._db.create_job(
            job_id=job_id,
            config_json=config_json,
            config_hash=config_hash,
            input_spec_json=input_spec_json,
            workspace_path=str(workspace_path),
            idempotency_key=idempotency_key,
        )

        # Emit state change event
        await self._emit_state_change(job_id, None, JobState.QUEUED)

        logger.info(f"Created job: {job_id}")
        return self._job_dict_to_response(job_dict)

    async def get_job(self, job_id: str) -> JobResponse | None:
        """Get job by ID."""
        job_dict = self._db.get_job(job_id)
        if job_dict:
            return self._job_dict_to_response(job_dict)
        return None

    async def list_jobs(
        self,
        states: list[JobState] | None = None,
        limit: int = 100,
    ) -> list[JobResponse]:
        """List jobs, optionally filtered by state."""
        jobs = self._db.list_jobs(states=states, limit=limit)
        return [self._job_dict_to_response(j) for j in jobs]

    async def start_job(self, job_id: str) -> bool:
        """Attempt to claim and start a job.

        Returns True if job was started, False if already claimed.
        """
        if self._safe_mode:
            raise RuntimeError("Engine in safe mode - jobs disabled")

        # Try to claim
        if not self._db.claim_job(job_id):
            return False

        # Emit state change
        await self._emit_state_change(job_id, JobState.QUEUED, JobState.RUNNING)

        logger.info(f"Job started: {job_id}")
        return True

    async def update_progress(
        self,
        job_id: str,
        phase: str,
        percent: int | None = None,
        items_completed: int | None = None,
        items_total: int | None = None,
        message: str | None = None,
    ) -> None:
        """Update job progress and emit event."""
        self._db.update_job_progress(
            job_id,
            percent=percent,
            phase=phase,
            items_completed=items_completed,
            items_total=items_total,
        )

        # Emit progress event
        event = JobProgress(
            sequence_number=0,
            job_id=job_id,
            job_sequence=0,
            phase=phase,
            progress_percent=percent,
            items_completed=items_completed,
            items_total=items_total,
        )
        event_id = self._db.persist_event(event, job_id)
        await self._broadcaster.broadcast_by_id(event_id)

        # Optionally emit log
        if message:
            await self.log(job_id, LogLevel.INFO, "progress", message)

    async def log(
        self,
        job_id: str,
        level: LogLevel,
        subsystem: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Emit a job log event."""
        event = JobLog(
            sequence_number=0,
            job_id=job_id,
            job_sequence=0,
            level=level,
            subsystem=subsystem,
            message=message,
            payload=payload,
        )
        event_id = self._db.persist_event(event, job_id)
        await self._broadcaster.broadcast_by_id(event_id)

    async def complete_job(
        self,
        job_id: str,
        outputs: list[ArtifactInfo] | None = None,
        scholarly_result: dict | None = None,
    ) -> JobReceipt:
        """Mark job as completed and generate receipt.

        Args:
            job_id: Job identifier
            outputs: List of output artifacts
            scholarly_result: Scholarly job result payload (Sprint 18)
        """
        job = self._db.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        # Update state
        self._db.update_job_state(job_id, JobState.COMPLETED)

        # Emit state change
        await self._emit_state_change(job_id, JobState.RUNNING, JobState.COMPLETED)

        # Generate receipt (include scholarly_result if provided)
        receipt = await self._generate_receipt(
            job, "completed", outputs, scholarly_result=scholarly_result
        )

        logger.info(f"Job completed: {job_id}")
        return receipt

    async def fail_job(
        self,
        job_id: str,
        error_code: str,
        error_message: str,
        error_details: dict[str, Any] | None = None,
    ) -> JobReceipt:
        """Mark job as failed and generate receipt."""
        job = self._db.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        old_state = JobState(job["state"])

        # Update state with error info
        self._db.update_job_state(
            job_id,
            JobState.FAILED,
            error_code=error_code,
            error_message=error_message,
            error_details_json=error_details,
        )

        # Emit state change
        await self._emit_state_change(job_id, old_state, JobState.FAILED)

        # Generate failure receipt
        receipt = await self._generate_receipt(
            job,
            "failed",
            error_code=error_code,
            error_message=error_message,
            error_details=error_details,
        )

        logger.error(f"Job failed: {job_id} - {error_code}: {error_message}")
        return receipt

    async def cancel_job(self, job_id: str) -> JobReceipt | None:
        """Cancel a job (queued or running)."""
        job = self._db.get_job(job_id)
        if not job:
            return None

        old_state = JobState(job["state"])

        if old_state == JobState.RUNNING:
            # Mark as cancelling, wait for cleanup
            self._db.update_job_state(job_id, JobState.CANCELLING)
            await self._emit_state_change(job_id, old_state, JobState.CANCELLING)
            # In real impl, worker would see this and clean up
            # For now, just transition directly
            await asyncio.sleep(0.1)

        # Final cancelled state
        self._db.update_job_state(job_id, JobState.CANCELLED)
        await self._emit_state_change(job_id, JobState.CANCELLING, JobState.CANCELLED)

        # Generate cancellation receipt
        receipt = await self._generate_receipt(job, "cancelled")

        logger.info(f"Job cancelled: {job_id}")
        return receipt

    async def recover_orphaned_jobs(self) -> list[str]:
        """Recover jobs stuck in running/cancelling state after crash.

        Per ADR-004: On startup, find orphaned jobs and mark as failed.

        Returns:
            List of recovered job IDs
        """
        orphaned = self._db.get_orphaned_jobs()
        recovered = []

        for job in orphaned:
            job_id = job["job_id"]
            logger.warning(f"Recovering orphaned job: {job_id}")

            # Mark as failed with crash error
            await self.fail_job(
                job_id,
                error_code="E_ENGINE_CRASH",
                error_message="Engine terminated unexpectedly",
                error_details={"recovered_from_state": job["state"]},
            )
            recovered.append(job_id)

        return recovered

    async def _emit_state_change(
        self,
        job_id: str,
        old_state: JobState | None,
        new_state: JobState,
    ) -> EventRowId:
        """Emit job state change event."""
        event = JobStateChanged(
            sequence_number=0,
            job_id=job_id,
            old_state=old_state,
            new_state=new_state,
        )
        event_id = self._db.persist_event(event, job_id)
        await self._broadcaster.broadcast_by_id(event_id)
        return event_id

    async def _generate_receipt(
        self,
        job: dict[str, Any],
        status: str,
        outputs: list[ArtifactInfo] | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        error_details: dict[str, Any] | None = None,
        scholarly_result: dict | None = None,
    ) -> JobReceipt:
        """Generate and write receipt.json.

        Per Sprint-1-DOD: chmod 444 after write (immutable).
        """
        job_id = job["job_id"]
        workspace_path = Path(job["workspace_path"])

        # Parse config
        config = json.loads(job["config_json"])

        # Get source pins (versions of data sources used)
        source_pins = await self._get_source_pins()

        # Build receipt
        receipt = JobReceipt(
            job_id=job_id,
            run_id=generate_run_id(),
            receipt_status=status,
            exit_code=error_code,
            timestamps=ReceiptTimestamps(
                created=datetime.fromisoformat(job["created_at"]),
                started=datetime.fromisoformat(job["started_at"])
                if job["started_at"]
                else None,
                completed=datetime.now(timezone.utc),
            ),
            config_snapshot=config,
            source_pins=source_pins,
            outputs=outputs or [],
            inputs_summary={
                "paths": json.loads(job["input_spec_json"]).get("paths", [])
            },
            error_code=error_code,
            error_message=error_message,
            error_details=error_details,
        )

        # Write receipt atomically: temp → fsync → rename
        # Prevents partial writes on crash (Sprint-2 hardening)
        receipt_path = workspace_path / "receipt.json"
        temp_path = receipt_path.with_suffix(
            f".tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}"
        )

        # Build receipt content, optionally including scholarly_result (Sprint 18)
        receipt_dict = json.loads(receipt.model_dump_json())
        if scholarly_result:
            receipt_dict["scholarly_result"] = scholarly_result
        content = json.dumps(receipt_dict, indent=2, default=str)
        content_bytes = content.encode("utf-8")

        # Write to temp file with fsync
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        # Atomic rename (POSIX guarantees)
        os.replace(temp_path, receipt_path)

        # fsync directory for full durability (belt+suspenders)
        try:
            dir_fd = os.open(workspace_path, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass  # Best effort on platforms without O_DIRECTORY

        # Make immutable (chmod 444)
        os.chmod(receipt_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

        # Compute hash from memory (not disk re-read)
        sha256 = hashlib.sha256(content_bytes).hexdigest()

        # Register artifact
        artifact_id = self._db.register_artifact(
            job_id=job_id,
            name="receipt.json",
            path=str(receipt_path),
            artifact_type="receipt",
        )

        # Complete artifact with hash
        self._db.complete_artifact(artifact_id, len(content_bytes), sha256)

        # Store receipt in DB (re-read to get current state)
        current_job = self._db.get_job(job_id)
        current_state = (
            JobState(current_job["state"]) if current_job else JobState.FAILED
        )
        self._db.update_job_state(
            job_id,
            current_state,
            receipt_json=content,  # Include scholarly_result if present
            receipt_hash=sha256,
        )

        logger.info(f"Receipt generated: {receipt_path}")
        return receipt

    async def _get_source_pins(self) -> dict[str, str]:
        """Get version pins for all data sources.

        Returns empty dict if sources table doesn't exist (engine-only mode).
        """
        import sqlite3

        conn = self._db.connect()
        try:
            cursor = conn.execute("SELECT name, version, sha256 FROM sources")
            pins = {}
            for row in cursor:
                version = row["version"]
                if row["sha256"]:
                    version = f"{version}@{row['sha256'][:8]}"
                pins[row["name"]] = version
            return pins
        except sqlite3.OperationalError:
            # sources table doesn't exist (engine-only mode)
            return {}

    def _job_dict_to_response(self, job: dict[str, Any]) -> JobResponse:
        """Convert job dict to JobResponse."""
        # Extract result from receipt if available (Sprint 18)
        result = None
        if job.get("receipt_json"):
            try:
                receipt = json.loads(job["receipt_json"])
                # For scholarly jobs, result is embedded in receipt
                if receipt.get("scholarly_result"):
                    result = receipt["scholarly_result"]
            except (json.JSONDecodeError, KeyError):
                pass

        return JobResponse(
            job_id=job["job_id"],
            state=JobState(job["state"]),
            created_at=datetime.fromisoformat(job["created_at"]),
            started_at=datetime.fromisoformat(job["started_at"])
            if job["started_at"]
            else None,
            completed_at=datetime.fromisoformat(job["completed_at"])
            if job["completed_at"]
            else None,
            config=JobConfig.model_validate_json(job["config_json"]),
            progress_percent=job["progress_percent"],
            progress_phase=job["progress_phase"],
            error_code=job["error_code"],
            error_message=job["error_message"],
            result=result,
        )
