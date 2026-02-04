"""Engine status and heartbeat per ADR-003 and Sprint-1-DOD."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
from typing import TYPE_CHECKING

from redletters import __version__
from redletters.engine_spine.models import (
    BackendShape,
    EngineHealth,
    EngineHeartbeat,
    EngineMode,
    EngineStatus,
    EventRowId,
)

if TYPE_CHECKING:
    from pathlib import Path

    from redletters.engine_spine.broadcaster import EventBroadcaster
    from redletters.engine_spine.database import EngineDatabase
    from redletters.engine_spine.executor import JobExecutor

logger = logging.getLogger(__name__)

# Heartbeat interval per ADR-003
HEARTBEAT_INTERVAL_SECONDS = 3


def _get_git_hash() -> str:
    """Get current git commit hash for build_hash field."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fallback: check for BUILD_HASH env var (set in CI)
    return os.environ.get("BUILD_HASH", "dev")


class EngineStatusManager:
    """Manages engine status and heartbeat emission.

    Tracks:
    - Engine mode (normal/safe)
    - Health status
    - Uptime
    - Active jobs and queue depth
    - Backend shape (Sprint 19: route availability for GUI mismatch detection)
    """

    def __init__(
        self,
        db: "EngineDatabase",
        broadcaster: "EventBroadcaster",
        safe_mode: bool = False,
    ):
        self._db = db
        self._broadcaster = broadcaster
        self._mode = EngineMode.SAFE if safe_mode else EngineMode.NORMAL
        self._health = EngineHealth.HEALTHY
        self._start_time = time.time()
        self._heartbeat_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()
        self._build_hash = _get_git_hash()

        # Track job counts (updated by job manager)
        self._active_jobs = 0
        self._queue_depth = 0

        # Sprint 19: Backend shape (set by app after route registration)
        self._backend_shape: "BackendShape | None" = None

    @property
    def mode(self) -> EngineMode:
        """Current engine mode."""
        return self._mode

    @property
    def is_safe_mode(self) -> bool:
        """True if engine is in safe mode (jobs disabled)."""
        return self._mode == EngineMode.SAFE

    @property
    def uptime_seconds(self) -> float:
        """Seconds since engine start."""
        return time.time() - self._start_time

    @property
    def uptime_ms(self) -> int:
        """Milliseconds since engine start."""
        return int(self.uptime_seconds * 1000)

    def get_status(self) -> EngineStatus:
        """Get current engine status for /v1/engine/status endpoint."""
        # Refresh job counts from DB for accurate metrics
        self._refresh_job_counts()
        return EngineStatus(
            version=__version__,
            build_hash=self._build_hash,
            api_version="v1",
            capabilities=self._get_capabilities(),
            mode=self._mode,
            health=self._health,
            uptime_seconds=self.uptime_seconds,
            active_jobs=self._active_jobs,
            queue_depth=self._queue_depth,
            shape=self._backend_shape,
        )

    def set_backend_shape(self, shape: BackendShape) -> None:
        """Set backend shape from route introspection.

        Sprint 19: Called by app after routes are registered.
        """
        self._backend_shape = shape
        logger.info(
            f"Backend shape set: mode={shape.backend_mode}, "
            f"translate={shape.has_translate}, sources_status={shape.has_sources_status}"
        )

    def _get_capabilities(self) -> list[str]:
        """Get list of engine capabilities."""
        caps = [
            "sse_streaming",
            "event_replay",
            "job_management",
            "receipt_generation",
            "diagnostics_export",
        ]
        if not self.is_safe_mode:
            caps.append("job_execution")
        return caps

    def update_job_counts(self, active: int, queued: int) -> None:
        """Update job count metrics."""
        self._active_jobs = active
        self._queue_depth = queued

    def set_health(self, health: EngineHealth) -> None:
        """Set engine health status."""
        if health != self._health:
            logger.info(
                f"Engine health changed: {self._health.value} -> {health.value}"
            )
            self._health = health

    async def start_heartbeat(self) -> None:
        """Start the heartbeat emission task."""
        if self._heartbeat_task is not None:
            return

        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"Heartbeat started (interval: {HEARTBEAT_INTERVAL_SECONDS}s)")

    async def stop_heartbeat(self) -> None:
        """Stop the heartbeat emission task."""
        self._shutdown_event.set()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
        logger.info("Heartbeat stopped")

    async def _heartbeat_loop(self) -> None:
        """Background task that emits heartbeat events."""
        while not self._shutdown_event.is_set():
            try:
                await self._emit_heartbeat()
                await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)

    async def _emit_heartbeat(self) -> None:
        """Emit a single heartbeat event."""
        # Fetch real job counts from DB
        self._refresh_job_counts()

        event = EngineHeartbeat(
            sequence_number=0,  # Will be set by persist_event
            uptime_ms=self.uptime_ms,
            health=self._health,
            active_jobs=self._active_jobs,
            queue_depth=self._queue_depth,
        )

        # Persist-before-send
        event_id = self._db.persist_event(event)

        # Broadcast to all connections
        await self._broadcaster.broadcast_by_id(event_id)

    def _refresh_job_counts(self) -> None:
        """Refresh job counts from database."""
        try:
            conn = self._db.connect()
            cursor = conn.execute(
                """
                SELECT state, COUNT(*) as cnt
                FROM jobs
                WHERE state IN ('queued', 'running', 'cancelling')
                GROUP BY state
                """
            )
            counts = {row["state"]: row["cnt"] for row in cursor}
            self._queue_depth = counts.get("queued", 0)
            self._active_jobs = counts.get("running", 0) + counts.get("cancelling", 0)
        except Exception as e:
            logger.warning(f"Failed to refresh job counts: {e}")

    async def emit_shutdown_event(
        self,
        reason: str,
        grace_period_ms: int,
    ) -> EventRowId:
        """Emit engine shutdown notification.

        Args:
            reason: Shutdown reason ("user_request", "update", "error")
            grace_period_ms: Grace period before shutdown

        Returns:
            Event row ID
        """
        from redletters.engine_spine.models import EngineShuttingDown

        event = EngineShuttingDown(
            sequence_number=0,
            reason=reason,
            grace_period_ms=grace_period_ms,
        )

        event_id = self._db.persist_event(event)
        await self._broadcaster.broadcast_by_id(event_id)
        return event_id


class EngineState:
    """Singleton managing global engine state."""

    _instance: "EngineState | None" = None

    def __init__(self):
        self.db: "EngineDatabase | None" = None
        self.broadcaster: "EventBroadcaster | None" = None
        self.status_manager: EngineStatusManager | None = None
        self.executor: "JobExecutor | None" = None  # Set by lifespan
        self.workspace_base: "Path | None" = None  # Sprint 18: For job creation
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "EngineState":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(
        self,
        db: "EngineDatabase",
        broadcaster: "EventBroadcaster",
        safe_mode: bool = False,
        workspace_base: "Path | None" = None,
    ) -> None:
        """Initialize engine state."""
        self.db = db
        self.broadcaster = broadcaster
        self.status_manager = EngineStatusManager(db, broadcaster, safe_mode)
        self.workspace_base = workspace_base
        self._initialized = True

    @property
    def is_initialized(self) -> bool:
        """Check if engine is initialized."""
        return self._initialized

    def reset(self) -> None:
        """Reset state (for testing)."""
        self.db = None
        self.broadcaster = None
        self.status_manager = None
        self.executor = None
        self.workspace_base = None
        self._initialized = False
        EngineState._instance = None


def get_engine_state() -> EngineState:
    """Get the global engine state."""
    return EngineState.get_instance()
