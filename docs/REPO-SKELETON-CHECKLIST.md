# Repo Skeleton Checklist

**Purpose**: Enforce ADR decisions at the code level. Complete before first sprint ends.

**Philosophy**: Most teams optimize for "first demo dopamine" and ship fragile polling UIs. This checklist installs guardrails.

---

## 1. OpenAPI Spec + Contract Tests in CI

### Files Required

```
src/redletters/engine/api/
├── openapi.yaml          # Generated from FastAPI, committed
└── schemas/
    ├── events.py         # Pydantic models for SSE events
    ├── jobs.py           # Job request/response models
    └── receipts.py       # Receipt model

tests/
├── contract/
│   ├── test_stream_ordering.py    # STORY-010
│   ├── test_stream_replay.py      # STORY-010
│   ├── test_ct07_gui_reboot.py    # CT-07: the nasty one
│   └── conftest.py
└── integration/
    └── ...
```

### CI Requirements

```yaml
# .github/workflows/contract-tests.yml
name: Contract Tests

on: [push, pull_request]

jobs:
  contract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Start engine
        run: |
          python -m redletters.engine &
          sleep 5

      - name: Run contract tests
        run: pytest tests/contract/ -v --tb=short

      - name: Verify OpenAPI spec matches code
        run: |
          python -c "from redletters.engine.server import app; import json; print(json.dumps(app.openapi()))" > /tmp/generated.json
          diff -u src/redletters/engine/api/openapi.yaml /tmp/generated.json || (echo "OpenAPI spec out of sync!" && exit 1)
```

### Checklist

- [ ] OpenAPI spec generated and committed
- [ ] Contract tests in `tests/contract/`
- [ ] CI workflow runs contract tests on every PR
- [ ] PR cannot merge if contract tests fail
- [ ] OpenAPI spec drift check in CI

---

## 2. Event Schema Types Shared (Engine ↔ UI)

### Approach: Generate TypeScript from Pydantic

```bash
# Generate TypeScript types from Python models
pip install pydantic-to-typescript
pydantic2ts --module src/redletters/engine/api/schemas/events.py --output gui/src/types/events.ts
```

### Files Required

```
src/redletters/engine/api/schemas/
├── events.py             # Source of truth (Python)
└── __init__.py

gui/src/types/
├── events.ts             # Generated (TypeScript)
├── jobs.ts               # Generated
└── receipts.ts           # Generated

scripts/
└── generate-types.sh     # Runs pydantic2ts
```

### CI Requirement

```yaml
- name: Verify TypeScript types are fresh
  run: |
    ./scripts/generate-types.sh
    git diff --exit-code gui/src/types/ || (echo "TypeScript types out of sync!" && exit 1)
```

### Checklist

- [ ] Pydantic models are single source of truth
- [ ] TypeScript types generated, not hand-written
- [ ] CI verifies types are fresh
- [ ] No `any` types in GUI event handling code

---

## 3. Workspace + DB Directories Standardized

### Directory Structure (per ADR-006)

```
~/.greek2english/                    # XDG_DATA_HOME on Linux
├── config.toml                      # User configuration
├── engine.db                        # SQLite database
├── engine.pid                       # Process lock
├── .auth_token                      # Fallback token storage (mode 0600)
├── logs/
│   └── engine.log                   # Rotated logs
├── workspaces/
│   └── job_<id>/
│       ├── input/
│       ├── output/
│       ├── temp/                    # Deleted on completion
│       └── receipt.json             # Immutable
├── quarantine/                      # Crashed job artifacts
│   └── job_<id>/
└── backups/                         # Optional DB backups
    └── engine.db.<timestamp>
```

### Code Requirements

```python
# src/redletters/engine/paths.py

from pathlib import Path
import os

def get_data_dir() -> Path:
    """Get data directory, respecting XDG on Linux."""
    if os.name == "nt":  # Windows
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    elif os.name == "darwin":  # macOS
        base = Path.home() / "Library/Application Support"
    else:  # Linux
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))

    return base / "greek2english"

DATA_DIR = get_data_dir()
CONFIG_PATH = DATA_DIR / "config.toml"
DB_PATH = DATA_DIR / "engine.db"
WORKSPACES_DIR = DATA_DIR / "workspaces"
QUARANTINE_DIR = DATA_DIR / "quarantine"
LOGS_DIR = DATA_DIR / "logs"
```

### Checklist

- [ ] `paths.py` module with all path constants
- [ ] No hardcoded paths anywhere else
- [ ] Paths respect platform conventions
- [ ] Workspace structure matches ADR-004
- [ ] Quarantine directory exists and is used

---

## 4. Diagnostics Bundle Command (Implemented Early)

### CLI Command

```bash
redletters diagnostics export --output ~/Desktop/diagnostics.zip
```

### Bundle Contents

```
diagnostics-<timestamp>.zip
├── system_info.json          # OS, version, platform, memory
├── engine_status.json        # /v1/engine/status response
├── config.toml               # User config (secrets scrubbed)
├── recent_logs.jsonl         # Last 1000 log lines (tokens masked)
├── job_summary.json          # Last 10 jobs (no full receipts)
├── db_stats.json             # Table sizes, index health
└── README.txt                # Instructions for support
```

### Security Requirements (per ADR-005)

```python
def create_diagnostics_bundle(output_path: Path):
    bundle = {}

    # Scrub secrets
    config = load_config()
    config.pop("auth_token", None)
    bundle["config"] = config

    # Mask tokens in logs
    logs = get_recent_logs(limit=1000)
    bundle["recent_logs"] = [mask_sensitive(log) for log in logs]

    # Final check: abort if token pattern found
    bundle_str = json.dumps(bundle)
    if re.search(r'rl_[A-Za-z0-9_-]{20,}', bundle_str):
        raise SecurityError("Token detected in diagnostics bundle")

    write_zip(output_path, bundle)
```

### Checklist

- [ ] `redletters diagnostics export` command exists
- [ ] Bundle includes all required files
- [ ] Tokens/secrets are scrubbed (verified by test)
- [ ] Bundle is small enough to email (<10 MB typical)
- [ ] README.txt explains how to submit for support

---

## 5. Source of Truth Enforcement

### Database Constraints

```sql
-- Enforce receipt immutability
CREATE TRIGGER prevent_receipt_update
BEFORE UPDATE ON jobs
FOR EACH ROW
WHEN OLD.receipt_json IS NOT NULL AND NEW.receipt_json != OLD.receipt_json
BEGIN
    SELECT RAISE(ABORT, 'Receipt is immutable once written');
END;

-- Enforce state machine
CREATE TRIGGER enforce_state_machine
BEFORE UPDATE ON jobs
FOR EACH ROW
BEGIN
    SELECT CASE
        WHEN OLD.state = 'completed' AND NEW.state != 'archived' THEN
            RAISE(ABORT, 'Completed jobs can only transition to archived')
        WHEN OLD.state = 'failed' AND NEW.state NOT IN ('archived') THEN
            RAISE(ABORT, 'Failed jobs can only transition to archived')
        WHEN OLD.state = 'cancelled' AND NEW.state NOT IN ('archived') THEN
            RAISE(ABORT, 'Cancelled jobs can only transition to archived')
    END;
END;
```

### Checklist

- [ ] DB triggers enforce receipt immutability
- [ ] DB triggers enforce state machine
- [ ] Recovery code trusts receipt.json over DB for terminal jobs
- [ ] Artifact verification compares hash to receipt

---

## 6. Event Ordering Enforcement

### Sequence Number Generation

```python
# Atomic sequence increment (no gaps)
async def next_sequence() -> int:
    async with db.transaction():
        result = await db.execute("""
            UPDATE sequence_state
            SET last_sequence = last_sequence + 1
            WHERE id = 1
            RETURNING last_sequence
        """)
        return result.fetchone()[0]
```

### Event Persistence Before Send

```python
async def emit_event(event: BaseEvent):
    # 1. Assign sequence
    event.sequence_number = await next_sequence()

    # 2. Persist to DB FIRST
    await db.execute(
        "INSERT INTO job_events (...) VALUES (...)",
        event.to_db_row()
    )

    # 3. THEN broadcast to SSE connections
    await event_broadcaster.send(event)
```

### Checklist

- [ ] Sequence generated atomically (no gaps)
- [ ] Events persisted before broadcast
- [ ] SSE endpoint replays from DB on resume
- [ ] Client dedupe by sequence_number documented

---

## 7. First Sprint Definition of Done

**See [SPRINT-1-DOD.md](./specs/SPRINT-1-DOD.md) for the authoritative, locked ship criteria.**

Quick reference (not authoritative — check the DoD):

- [ ] Engine boots + status (version, build hash, API version, capabilities, heartbeat)
- [ ] Auth is real (token required everywhere, keychain works, fallback tested)
- [ ] Single job vertical slice works (create → queued → running → completed/failed)
- [ ] Reconnect correctness (CT-07 GUI reboot + CT-08 engine restart)
- [ ] Receipts exist and are honest (every outcome produces receipt, immutable, correlation IDs)
- [ ] Diagnostics bundle works (export, scrubbed, token never present)
- [ ] Kill-switches implemented (`--safe-mode`, `reset --confirm-destroy`)

**Demo Script**: The Sprint 1 DoD includes an executable demo script. If the script doesn't pass, Sprint 1 isn't done.

---

## Quick Reference: File Locations

| Concern | Location |
|---------|----------|
| **Sprint 1 DoD** | `docs/specs/SPRINT-1-DOD.md` |
| **Error Code Registry** | `docs/specs/ERROR-CODE-REGISTRY.md` |
| OpenAPI spec | `src/redletters/engine/api/openapi.yaml` |
| Event schemas (Python) | `src/redletters/engine/api/schemas/events.py` |
| Event schemas (TypeScript) | `gui/src/types/events.ts` |
| Path constants | `src/redletters/engine/paths.py` |
| Auth middleware | `src/redletters/engine/auth.py` |
| Error definitions | `src/redletters/engine/errors.py` |
| Receipt generation | `src/redletters/engine/receipt.py` |
| Contract tests | `tests/contract/` |
| CT-07 test | `tests/contract/test_ct07_gui_reboot.py` |
| CT-08 test | `tests/contract/test_ct08_engine_restart.py` |
| Diagnostics command | `src/redletters/cli/diagnostics.py` |
| Safe mode / Reset | `src/redletters/cli/engine.py` |

---

*This checklist is the difference between "it works" and "it ships."*
