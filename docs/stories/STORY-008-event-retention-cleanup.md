# STORY-008: Event Retention & Cleanup

**Epic**: Desktop App Architecture
**ADRs**: ADR-004
**Priority**: P2 (Operations)
**Depends On**: STORY-004 (Job Schema)
**Estimate**: 1 day

---

## User Story

**As a** long-term user,
**I want** old log events to be automatically cleaned up,
**So that** my database doesn't grow unbounded.

---

## Acceptance Criteria

### AC-1: Retention Policy
- [ ] TRACE/DEBUG/INFO events: 24 hours
- [ ] WARN events: 7 days
- [ ] ERROR events: Permanent (with job)
- [ ] Job summary + receipt: Permanent

### AC-2: Cleanup Task
- [ ] Background task runs daily at 3 AM local time
- [ ] Deletes events beyond retention period
- [ ] Runs incrementally (not one giant delete)

### AC-3: Vacuum
- [ ] After cleanup, run incremental vacuum
- [ ] Reclaim space from deleted rows
- [ ] Limit vacuum to avoid blocking

### AC-4: Size Monitoring
- [ ] Track database size on startup
- [ ] Warn if over 500 MB
- [ ] Error if over 1 GB (force cleanup)

### AC-5: Manual Cleanup
- [ ] `redletters db cleanup` triggers cleanup manually
- [ ] `redletters db stats` shows database statistics
- [ ] `redletters db vacuum` forces full vacuum

---

## Technical Design

### Retention Cleanup

```python
from datetime import datetime, timedelta

async def cleanup_old_events():
    now = datetime.utcnow()
    cutoff_24h = (now - timedelta(hours=24)).isoformat()
    cutoff_7d = (now - timedelta(days=7)).isoformat()

    # Delete in batches to avoid long locks
    batch_size = 10000

    # TRACE/DEBUG/INFO older than 24h
    while True:
        result = await db.execute("""
            DELETE FROM job_events
            WHERE id IN (
                SELECT id FROM job_events
                WHERE timestamp_utc < ?
                AND level IN ('trace', 'debug', 'info')
                LIMIT ?
            )
        """, [cutoff_24h, batch_size])

        if result.rowcount == 0:
            break
        await asyncio.sleep(0.1)  # Yield to other tasks

    # WARN older than 7 days
    while True:
        result = await db.execute("""
            DELETE FROM job_events
            WHERE id IN (
                SELECT id FROM job_events
                WHERE timestamp_utc < ?
                AND level = 'warn'
                LIMIT ?
            )
        """, [cutoff_7d, batch_size])

        if result.rowcount == 0:
            break
        await asyncio.sleep(0.1)

    # Incremental vacuum (reclaim some pages)
    await db.execute("PRAGMA incremental_vacuum(1000)")
```

### Size Monitoring

```python
async def check_database_size():
    path = get_database_path()
    size_bytes = path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)

    if size_mb > 1000:
        log.error(f"Database size critical: {size_mb:.1f} MB")
        await force_cleanup()
    elif size_mb > 500:
        log.warning(f"Database size warning: {size_mb:.1f} MB")

    return {
        "size_bytes": size_bytes,
        "size_mb": size_mb,
        "status": "critical" if size_mb > 1000 else "warning" if size_mb > 500 else "ok"
    }
```

### CLI Commands

```python
@cli.command()
def db_stats():
    """Show database statistics."""
    stats = engine.get_db_stats()
    print(f"Database size: {stats['size_mb']:.1f} MB")
    print(f"Total jobs: {stats['job_count']}")
    print(f"Total events: {stats['event_count']}")
    print(f"Oldest event: {stats['oldest_event']}")

@cli.command()
def db_cleanup():
    """Run cleanup manually."""
    deleted = engine.run_cleanup()
    print(f"Deleted {deleted} events")

@cli.command()
def db_vacuum():
    """Run full vacuum (may take time)."""
    before = get_db_size()
    engine.run_vacuum()
    after = get_db_size()
    print(f"Reclaimed {before - after:.1f} MB")
```

### Files Changed/Created

- `src/redletters/engine/retention.py` — Cleanup logic
- `src/redletters/engine/monitoring.py` — Size monitoring
- `src/redletters/cli/db.py` — Database CLI commands

---

## Test Plan

| Test | Type | Description |
|------|------|-------------|
| `test_cleanup_deletes_old_info_logs` | Integration | 24h retention |
| `test_cleanup_keeps_recent_logs` | Integration | No premature deletion |
| `test_cleanup_keeps_error_logs` | Integration | Permanent errors |
| `test_cleanup_batch_processing` | Unit | Incremental deletes |
| `test_vacuum_reclaims_space` | Integration | Size reduction |
| `test_size_warning_threshold` | Unit | 500 MB warning |

---

## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Tests written and passing
- [ ] Cleanup runs without blocking normal operations
- [ ] Database size stays reasonable under normal use
- [ ] CLI commands work correctly
