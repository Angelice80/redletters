# STORY-011: Engine Kill-Switches (Safe Mode + Reset)

**Epic**: Desktop App Architecture
**ADRs**: ADR-004 (Persistence), ADR-005 (Security)
**Priority**: P0 (Without this, first corruption = support nightmare)
**Depends On**: STORY-001 (Engine Lifecycle)
**Estimate**: 0.5 days

---

## User Story

**As a** user who has somehow bricked their engine state,
**I want** explicit recovery options that don't require reading source code,
**So that** I can recover from corruption without losing all evidence of what went wrong.

---

## Rationale

Humans are... humans. Without explicit kill-switches:
- Corrupted DB → user deletes random files → makes it worse
- Stuck job → user force-kills repeatedly → corrupts more state
- Support request → "I deleted everything, now it's really broken"

These switches make recovery explicit and evidence-preserving.

---

## Acceptance Criteria

### AC-1: Safe Mode

- [ ] `redletters engine start --safe-mode` starts engine in safe mode
- [ ] `/v1/engine/status` returns `"mode": "safe"` when in safe mode
- [ ] SSE stream works (heartbeats only)
- [ ] `POST /v1/jobs` returns 503: "Engine in safe mode. Jobs disabled."
- [ ] `GET /v1/jobs` works (read existing jobs)
- [ ] `GET /v1/jobs/{id}` works (read job details)
- [ ] `GET /v1/jobs/{id}/receipt` works (read receipts)
- [ ] `redletters diagnostics export` works in safe mode
- [ ] No job execution occurs, queue processing disabled

### AC-2: Reset Engine Data

- [ ] `redletters engine reset` without flag shows warning and refuses
- [ ] `redletters engine reset --confirm-destroy` proceeds with reset
- [ ] Before reset: auto-exports diagnostics to `~/Desktop/greek2english-reset-<timestamp>.zip`
- [ ] Deletes: `engine.db`, `workspaces/*`, `logs/*`, `cache/*`
- [ ] Preserves: `config.toml`, auth token in keychain
- [ ] Logs reset action with timestamp to config file
- [ ] On next start: fresh database created automatically

### AC-3: Safe Mode Indicators

- [ ] GUI shows "SAFE MODE" banner when engine reports `mode: safe`
- [ ] GUI disables "New Job" button in safe mode
- [ ] GUI can still browse existing jobs and export diagnostics

---

## Technical Design

### Safe Mode Implementation

```python
# src/redletters/engine/server.py

class EngineState:
    def __init__(self):
        self.safe_mode = False

engine_state = EngineState()

def create_app(safe_mode: bool = False) -> FastAPI:
    app = FastAPI()
    engine_state.safe_mode = safe_mode

    @app.get("/v1/engine/status")
    async def get_status():
        return {
            "version": __version__,
            "build_hash": get_build_hash(),
            "api_version": "v1",
            "mode": "safe" if engine_state.safe_mode else "normal",
            "capabilities": [] if engine_state.safe_mode else get_capabilities(),
        }

    return app


# src/redletters/engine/api/jobs.py

@router.post("")
async def create_job(request: CreateJobRequest):
    if engine_state.safe_mode:
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "E_SAFE_MODE",
                "message": "Engine in safe mode. Jobs disabled. "
                           "Restart without --safe-mode to enable jobs."
            }
        )
    # ... normal job creation


# src/redletters/cli/engine.py

@click.command()
@click.option("--safe-mode", is_flag=True, help="Start in safe mode (diagnostics only)")
def start(safe_mode: bool):
    """Start the Red Letters engine."""
    if safe_mode:
        click.echo("Starting engine in SAFE MODE (jobs disabled)")

    app = create_app(safe_mode=safe_mode)
    uvicorn.run(app, host="127.0.0.1", port=47200)
```

### Reset Implementation

```python
# src/redletters/cli/engine.py

@click.command()
@click.option("--confirm-destroy", is_flag=True, help="Confirm destructive reset")
def reset(confirm_destroy: bool):
    """Reset engine data (DESTRUCTIVE)."""
    if not confirm_destroy:
        click.echo("This will delete all jobs, receipts, and logs.", err=True)
        click.echo("Run with --confirm-destroy to proceed.", err=True)
        click.echo("A diagnostics bundle will be exported first.", err=True)
        raise SystemExit(1)

    data_dir = get_data_dir()

    # Step 1: Export diagnostics first
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    export_path = Path.home() / "Desktop" / f"greek2english-reset-{timestamp}.zip"
    click.echo(f"Exporting diagnostics to {export_path}...")

    try:
        create_diagnostics_bundle(export_path)
        click.echo(f"✓ Diagnostics exported")
    except Exception as e:
        click.echo(f"Warning: Could not export diagnostics: {e}", err=True)
        if not click.confirm("Continue with reset anyway?"):
            raise SystemExit(1)

    # Step 2: Delete data
    targets = [
        data_dir / "engine.db",
        data_dir / "engine.db-wal",
        data_dir / "engine.db-shm",
        data_dir / "workspaces",
        data_dir / "logs",
        data_dir / "cache",
    ]

    for target in targets:
        if target.exists():
            click.echo(f"Deleting {target.name}...")
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

    # Step 3: Record reset in config
    config_path = data_dir / "config.toml"
    if config_path.exists():
        config = toml.load(config_path)
    else:
        config = {}

    config["last_reset"] = datetime.utcnow().isoformat() + "Z"
    config_path.write_text(toml.dumps(config))

    click.echo("✓ Reset complete. Engine will start fresh on next launch.")
```

### Files Changed/Created

- `src/redletters/engine/server.py` — Safe mode flag
- `src/redletters/engine/api/jobs.py` — Safe mode check
- `src/redletters/cli/engine.py` — `--safe-mode` and `reset` commands

---

## Test Plan

| Test | Type | Description |
|------|------|-------------|
| `test_safe_mode_status` | Integration | Status returns `mode: safe` |
| `test_safe_mode_blocks_jobs` | Integration | POST /v1/jobs returns 503 |
| `test_safe_mode_allows_reads` | Integration | GET endpoints work |
| `test_safe_mode_allows_diagnostics` | Integration | Export works |
| `test_reset_requires_flag` | CLI | Without flag → error |
| `test_reset_exports_first` | CLI | Diagnostics created before delete |
| `test_reset_deletes_data` | CLI | DB and workspaces deleted |
| `test_reset_preserves_config` | CLI | config.toml survives |
| `test_reset_logs_timestamp` | CLI | last_reset recorded |

---

## Definition of Done

- [ ] Safe mode prevents job creation
- [ ] Safe mode allows all read operations
- [ ] Reset requires explicit flag
- [ ] Reset exports diagnostics first
- [ ] Reset preserves config and auth token
- [ ] GUI shows safe mode indicator
- [ ] Both commands documented in CLI help
