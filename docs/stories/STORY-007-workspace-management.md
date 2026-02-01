# STORY-007: Workspace Management

**Epic**: Desktop App Architecture
**ADRs**: ADR-004
**Priority**: P1 (Job Execution Support)
**Depends On**: STORY-004 (Job Schema)
**Estimate**: 1.5 days

---

## User Story

**As a** system administrator,
**I want** each job to have an isolated workspace folder,
**So that** job files are organized and cleanup is straightforward.

---

## Acceptance Criteria

### AC-1: Workspace Creation
- [ ] When job starts, create workspace at `~/.greek2english/workspaces/{job_id}/`
- [ ] Create subdirectories: `input/`, `output/`, `temp/`
- [ ] Record workspace path in jobs table

### AC-2: Workspace Contents
- [ ] Input files copied/linked to `input/` directory
- [ ] Generated outputs written to `output/` directory
- [ ] Working files written to `temp/` directory
- [ ] Final receipt written to workspace root

### AC-3: Cleanup on Completion
- [ ] On job completion, delete `temp/` directory
- [ ] Keep `output/` and receipt
- [ ] Update job record with final workspace state

### AC-4: Cleanup on Failure
- [ ] On job failure, preserve all files for debugging
- [ ] Mark workspace as "failed" in database
- [ ] Schedule for cleanup after 7 days

### AC-5: Quarantine on Crash
- [ ] On crash recovery, move partial outputs to `quarantine/`
- [ ] Quarantine path: `~/.greek2english/quarantine/{job_id}/`
- [ ] Log quarantine action

### AC-6: Retention Policy
- [ ] Background task runs daily
- [ ] Delete completed job temp files immediately
- [ ] Delete failed job workspaces after 7 days
- [ ] Delete cancelled job workspaces after 24 hours
- [ ] Archive job deletes workspace, keeps DB record

---

## Technical Design

### Workspace Structure

```
~/.greek2english/workspaces/
└── job_20240115_143000_a3f8/
    ├── input/
    │   └── luke.xml              # Copied input file
    ├── output/
    │   ├── luke_rendered.json    # Primary output
    │   └── luke_receipts.jsonl   # Per-verse receipts
    ├── temp/
    │   └── processing_state.json # Working data (deleted on complete)
    └── receipt.json              # Final job receipt
```

### Workspace Manager

```python
from pathlib import Path
import shutil

class WorkspaceManager:
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.quarantine_path = base_path.parent / "quarantine"

    async def create(self, job_id: str) -> Path:
        workspace = self.base_path / job_id
        (workspace / "input").mkdir(parents=True)
        (workspace / "output").mkdir()
        (workspace / "temp").mkdir()
        return workspace

    async def cleanup_completed(self, job_id: str):
        workspace = self.base_path / job_id
        shutil.rmtree(workspace / "temp", ignore_errors=True)

    async def quarantine(self, job_id: str):
        workspace = self.base_path / job_id
        if workspace.exists():
            dest = self.quarantine_path / job_id
            shutil.move(str(workspace), str(dest))

    async def delete(self, job_id: str):
        workspace = self.base_path / job_id
        shutil.rmtree(workspace, ignore_errors=True)
```

### Cleanup Task

```python
from datetime import datetime, timedelta

async def cleanup_workspaces():
    """Run daily via scheduler."""
    now = datetime.utcnow()

    # Get jobs needing cleanup
    jobs = await db.query("""
        SELECT job_id, state, completed_at, workspace_path
        FROM jobs
        WHERE workspace_path IS NOT NULL
        AND state IN ('completed', 'failed', 'cancelled')
    """)

    for job in jobs:
        completed = datetime.fromisoformat(job.completed_at)
        age = now - completed

        if job.state == "completed":
            # Delete temp immediately (keep output)
            await workspace_manager.cleanup_completed(job.job_id)

        elif job.state == "failed" and age > timedelta(days=7):
            await workspace_manager.delete(job.job_id)
            await db.execute(
                "UPDATE jobs SET workspace_path = NULL WHERE job_id = ?",
                [job.job_id]
            )

        elif job.state == "cancelled" and age > timedelta(days=1):
            await workspace_manager.delete(job.job_id)
```

### Files Changed/Created

- `src/redletters/engine/workspace.py` — Workspace manager
- `src/redletters/engine/cleanup.py` — Cleanup task
- `src/redletters/engine/scheduler.py` — Background task scheduling

---

## Test Plan

| Test | Type | Description |
|------|------|-------------|
| `test_workspace_created_on_job_start` | Integration | Directory structure |
| `test_temp_deleted_on_completion` | Integration | Cleanup behavior |
| `test_failed_workspace_preserved` | Integration | Debugging support |
| `test_quarantine_on_crash` | Integration | Recovery behavior |
| `test_cleanup_respects_retention` | Unit | Age-based cleanup |

---

## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Tests written and passing
- [ ] Workspaces created in correct location
- [ ] Cleanup runs without errors
- [ ] Disk space reclaimed after retention period
