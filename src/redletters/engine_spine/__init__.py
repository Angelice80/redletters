"""Engine Spine: Desktop application backend with job system and event streaming.

This module implements ADR-003/004/005/006 for the desktop application:
- SSE event streaming with at-least-once delivery
- Job lifecycle management with persist-before-send
- Per-install auth token (keychain + file fallback)
- Diagnostics bundle with secret scrubbing
- Kill-switches (safe-mode, reset --confirm-destroy)

Usage:
    # Start engine server
    redletters engine start

    # Start in safe mode (diagnostics only)
    redletters engine start --safe-mode

    # Check status
    redletters engine status

    # Export diagnostics
    redletters diagnostics export --output ~/diagnostics

    # Reset engine data
    redletters engine reset --confirm-destroy
"""

from redletters.engine_spine.models import (
    BaseEvent,
    EngineHealth,
    EngineHeartbeat,
    EngineMode,
    EngineStatus,
    EventRowId,
    JobConfig,
    JobLog,
    JobProgress,
    JobReceipt,
    JobResponse,
    JobState,
    JobStateChanged,
    LogLevel,
)

__all__ = [
    # Models
    "BaseEvent",
    "EngineHealth",
    "EngineHeartbeat",
    "EngineMode",
    "EngineStatus",
    "EventRowId",
    "JobConfig",
    "JobLog",
    "JobProgress",
    "JobReceipt",
    "JobResponse",
    "JobState",
    "JobStateChanged",
    "LogLevel",
]
