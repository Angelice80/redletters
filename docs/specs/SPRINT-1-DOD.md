# Sprint 1: Definition of Done

**Status**: LOCKED (Do not modify without team consensus)
**Date**: 2026-01-28
**Purpose**: Ship criteria, not vibes. If any item is missing, you have a demo, not a platform.

---

## Ship Criteria (ALL Required)

### 1. Engine Boots + Status

| Requirement | Verification |
|-------------|--------------|
| `/v1/engine/status` returns version | `curl localhost:47200/v1/engine/status` shows `version` field |
| `/v1/engine/status` returns build hash | Response includes `build_hash` (git SHA or similar) |
| `/v1/engine/status` returns API version | Response includes `api_version: "v1"` |
| `/v1/engine/status` returns capabilities | Response includes `capabilities` array |
| Heartbeat emits on schedule | SSE stream receives `engine.heartbeat` every 3 seconds |
| GUI displays connection state | Status pill shows Connected (green) / Degraded (orange) / Disconnected (red) |

**Test**: `pytest tests/integration/test_engine_status.py`

---

### 2. Auth Is Real

| Requirement | Verification |
|-------------|--------------|
| Token required for all endpoints | Request without `Authorization` header → 401 |
| Token required for SSE stream | `/v1/stream` without token → 401 |
| Keychain storage works (macOS) | Token stored/retrieved from Keychain Services |
| Keychain storage works (Windows) | Token stored/retrieved from Credential Manager |
| Fallback file storage works | When keychain unavailable: file created with 0600, warning logged |
| Fallback warning path tested | Integration test verifies warning is emitted |

**Test**: `pytest tests/integration/test_auth.py`

---

### 3. Single Job Vertical Slice Works

| Requirement | Verification |
|-------------|--------------|
| `POST /v1/jobs` creates job | Returns 201 with `job_id` |
| Job starts immediately | State is `queued` (not `draft`) |
| Job transitions: queued → running | `job.state_changed` event emitted |
| Job transitions: running → completed | `job.state_changed` event emitted |
| Job can fail: running → failed | Error jobs produce `failed` state |
| Persist-before-send verified | Every event in SSE stream exists in `job_events` table |

**Test**: `pytest tests/integration/test_job_lifecycle.py`

**Contract Test**: `pytest tests/contract/test_persist_before_send.py`

---

### 4. Reconnect Correctness

| Requirement | Verification |
|-------------|--------------|
| CT-07 passes | GUI reboot mid-run: no gaps, no dupes, correct receipt |
| CT-08 passes | Engine restart mid-run: job fails fast, crash receipt produced |
| Last-Event-ID works | Reconnect with header replays from correct sequence |
| `?resume_from=N` works | Query parameter equivalent to Last-Event-ID |
| Sequence numbers monotonic | No decreases, no duplicates across restart |

**Test**: `pytest tests/contract/test_ct07_gui_reboot.py`
**Test**: `pytest tests/contract/test_ct08_engine_restart.py`

---

### 5. Receipt Exists and Is Honest

| Requirement | Verification |
|-------------|--------------|
| Completed jobs produce `receipt.json` | File exists in workspace |
| Failed jobs produce `receipt.json` | File exists with `receipt_status: "failed"` |
| Cancelled jobs produce `receipt.json` | File exists with `receipt_status: "cancelled"` |
| Crash jobs produce receipt | File exists with `exit_code: "E_ENGINE_CRASH"` |
| Receipts are immutable | chmod 444 after write, DB trigger prevents modification |
| Receipt includes correlation IDs | `run_id` present and matches events |
| Receipt references artifacts | `outputs` array with path, size, sha256 for each |
| Receipt includes config snapshot | `config_snapshot` matches job config |
| Receipt includes source pins | `source_pins` with versions/hashes of data sources |

**Test**: `pytest tests/integration/test_receipts.py`

---

### 6. Diagnostics Bundle Works

| Requirement | Verification |
|-------------|--------------|
| `redletters diagnostics export` produces output | ZIP file or folder created |
| Bundle includes system info | `system_info.json` present |
| Bundle includes recent logs | `recent_logs.jsonl` present |
| Bundle includes job summary | `job_summary.json` present |
| Bundle includes engine status | `engine_status.json` present |
| Secrets are scrubbed | `grep -r "rl_" bundle/` returns nothing |
| Token never present | Regex scan for `rl_[A-Za-z0-9_-]{20,}` finds zero matches |

**Test**: `pytest tests/integration/test_diagnostics.py`

---

## Demo Script (Executable by Anyone)

This is your investor demo, except the investor is Future-You.

```bash
#!/bin/bash
# Sprint 1 Demo Script - No Handwaving Edition
# Run this to verify Sprint 1 is actually complete

set -e  # Fail on first error

echo "=== STEP 1: Launch GUI, verify connection ==="
echo "Expected: GUI shows 'Connected' + engine version"
read -p "Launch GUI now, then press Enter when connected..."

echo ""
echo "=== STEP 2: Start a job, verify logs stream ==="
echo "Expected: Logs appear in real-time in GUI"
read -p "Start a job in GUI, wait for logs to stream, press Enter..."

echo ""
echo "=== STEP 3: Kill GUI, wait, relaunch ==="
echo "Expected: Stream resumes with Last-Event-ID, no duplicates, no gaps"
echo "Killing GUI in 3 seconds..."
sleep 3
pkill -f "Greek2English" || echo "GUI may have different process name"
echo "Waiting 10 seconds while job runs headless..."
sleep 10
echo "Relaunch GUI now."
read -p "Press Enter when GUI reconnected and logs resumed..."
echo "Verify: No duplicate log lines, no gaps in sequence"

echo ""
echo "=== STEP 4: Start new job, kill engine, verify fail-fast ==="
read -p "Start a new job in GUI, press Enter when running..."
echo "Killing engine in 3 seconds..."
sleep 3
pkill -f "redletters.engine" || pkill -f "uvicorn"
echo "Waiting 5 seconds..."
sleep 5
echo "Restart engine now (or let GUI auto-restart it)."
read -p "Press Enter when engine restarted..."
echo "Verify: Job shows 'failed' state, not 'running' or limbo"

echo ""
echo "=== STEP 5: Export diagnostics, verify no secrets ==="
redletters diagnostics export --output /tmp/diagnostics-test
echo "Scanning for leaked tokens..."
if grep -r "rl_[A-Za-z0-9_-]\{20,\}" /tmp/diagnostics-test; then
    echo "❌ FAIL: Token found in diagnostics bundle!"
    exit 1
else
    echo "✓ No tokens found in diagnostics bundle"
fi

echo ""
echo "=== STEP 6: Verify receipt ==="
echo "Open the receipt.json for the completed job."
echo "Verify it contains:"
echo "  - inputs (what was processed)"
echo "  - config_snapshot (settings used)"
echo "  - source_pins (data versions)"
echo "  - outputs with sha256 hashes"
read -p "Press Enter when verified..."

echo ""
echo "==================================="
echo "✓ SPRINT 1 DEMO COMPLETE"
echo "==================================="
```

---

## Kill-Switches (Implement Now)

These prevent "oops we bricked state" catastrophes.

### 1. Engine Safe Mode

**Purpose**: Start engine with jobs disabled, diagnostics only.

**Usage**:
```bash
redletters engine start --safe-mode
```

**Behavior**:
- Engine starts and binds to port
- `/v1/engine/status` works (returns `"mode": "safe"`)
- `/v1/stream` works (heartbeats only)
- `POST /v1/jobs` returns 503 with message: "Engine in safe mode. Jobs disabled."
- `GET /v1/jobs` works (read existing jobs)
- `redletters diagnostics export` works
- No job execution, no queue processing

**When to Use**:
- Database corruption suspected
- Need to export diagnostics before nuke
- Debugging startup issues

### 2. Reset Engine Data

**Purpose**: Nuclear option — fresh start after exporting evidence.

**Usage**:
```bash
redletters engine reset --confirm-destroy
```

**Behavior**:
1. **Requires explicit flag** — no accidental nukes
2. **Auto-exports diagnostics** to `~/Desktop/greek2english-reset-<timestamp>.zip`
3. **Deletes**:
   - `~/.greek2english/engine.db`
   - `~/.greek2english/workspaces/*`
   - `~/.greek2english/logs/*`
   - `~/.greek2english/cache/*` (if exists)
4. **Preserves**:
   - `~/.greek2english/config.toml` (user settings)
   - Auth token in keychain (user can reset separately)
5. **Logs action** to preserved config: `last_reset: "2026-01-28T14:30:00Z"`
6. **On next start**: Fresh database, clean slate

**Safety**:
```bash
# Without flag: refuses
$ redletters engine reset
Error: This will delete all jobs, receipts, and logs.
       Run with --confirm-destroy to proceed.
       A diagnostics bundle will be exported first.

# With flag: proceeds
$ redletters engine reset --confirm-destroy
Exporting diagnostics to ~/Desktop/greek2english-reset-20260128-143000.zip...
Deleting engine.db...
Deleting workspaces/...
Deleting logs/...
✓ Reset complete. Engine will start fresh on next launch.
```

---

## CI Gate

All of the above is enforced in CI:

```yaml
# .github/workflows/sprint1-gate.yml
name: Sprint 1 Gate

on:
  push:
    branches: [main]
  pull_request:

jobs:
  sprint1-criteria:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Start engine
        run: |
          python -m redletters.engine &
          sleep 5

      - name: Verify engine status
        run: |
          response=$(curl -s -H "Authorization: Bearer $TEST_TOKEN" localhost:47200/v1/engine/status)
          echo "$response" | jq -e '.version' || exit 1
          echo "$response" | jq -e '.build_hash' || exit 1
          echo "$response" | jq -e '.api_version' || exit 1

      - name: Run contract tests
        run: pytest tests/contract/ -v --tb=short

      - name: Run integration tests
        run: pytest tests/integration/ -v --tb=short

      - name: Verify diagnostics scrubbing
        run: |
          python -m redletters.cli diagnostics export --output /tmp/diag
          if grep -r "rl_[A-Za-z0-9_-]\{20,\}" /tmp/diag; then
            echo "Token found in diagnostics!"
            exit 1
          fi

      - name: Verify receipt generation
        run: pytest tests/integration/test_receipts.py -v
```

---

## What This Document Is

- **Contract**: If these aren't true, Sprint 1 isn't done
- **Checklist**: Run through before declaring victory
- **CI Gate**: Automated enforcement of criteria
- **Demo Script**: Executable proof, not hand-waving

## What This Document Isn't

- **Flexible**: These are ship criteria, not aspirations
- **Negotiable**: Missing one = demo, not platform
- **Optional**: Every item is required

---

## Explicit Scope Exclusions

### UI Polish Is Out of Scope

**UI polish is explicitly out of scope for Sprint 1.** UI must expose required controls and display required states/logs/receipts; visual refinement belongs to Sprint 2+.

The engine spine is the product. The GUI is the test harness with a haircut.

| In Scope (Sprint 1) | Out of Scope (Sprint 2+) |
|---------------------|--------------------------|
| Status pill (Connected/Degraded/Disconnected) | Animations, transitions |
| Start Job button | Fancy form validation UX |
| Log display (scrolling list) | Syntax highlighting, filtering UI |
| Receipt viewer (JSON display) | Pretty-printed receipts |
| Error messages (functional) | Toast notifications, modals |
| Settings (allowed paths) | Settings UI polish |

**Why**: Otherwise someone will spend 2 days on a sidebar animation while CT-07 flakes.

---

*"The difference between a demo and a product is that a demo works when you're looking at it."*
