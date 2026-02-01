# STORY-001: Engine Service Lifecycle + Auth Middleware

**Epic**: Desktop App Architecture
**ADRs**: ADR-003, ADR-004, ADR-005, ADR-006
**Priority**: P0 (Foundation)
**Estimate**: 3.5 days

> **Note**: This story includes auth middleware setup (not full token management).
> This prevents retrofitting auth into STORY-002 (SSE) later.
> Full token issuance/rotation remains in STORY-003.

---

## User Story

**As a** desktop app user,
**I want** the translation engine to run as a persistent background service,
**So that** I can close and reopen the GUI without losing running jobs.

---

## Acceptance Criteria

### AC-1: Engine Startup
- [ ] Engine binds to `127.0.0.1:47200` only (never `0.0.0.0`)
- [ ] Engine writes PID to `~/.greek2english/engine.pid`
- [ ] Engine checks for existing instance before binding
- [ ] If port busy, check if healthy engine exists; if not, wait 5s and retry
- [ ] Engine logs startup to `~/.greek2english/logs/engine.log`

### AC-2: Health Endpoint
- [ ] `GET /v1/engine/status` returns:
  ```json
  {
    "engine_version": "1.0.0",
    "api_version": "1.0",
    "health": "healthy",
    "uptime_ms": 12345,
    "started_at": "2024-01-15T12:00:00Z",
    "active_jobs": 0,
    "queue_depth": 0
  }
  ```
- [ ] Response within 100ms
- [ ] Works without authentication (status is public)

### AC-3: Graceful Shutdown
- [ ] `POST /v1/engine/shutdown` initiates graceful shutdown
- [ ] Running job completes current phase before stopping
- [ ] Queued jobs preserved in database
- [ ] Engine emits `engine.shutting_down` event
- [ ] Process exits with code 0 on success
- [ ] SIGTERM triggers same graceful shutdown

### AC-4: Crash Recovery
- [ ] On startup, detect orphaned `running` jobs in database
- [ ] Mark orphaned jobs as `failed` with error `E_ENGINE_CRASH`
- [ ] Move partial outputs to quarantine folder
- [ ] Log recovery actions

### AC-5: Single Instance Enforcement
- [ ] Second engine instance detects existing instance
- [ ] Second instance exits with clear message: "Engine already running on port 47200"
- [ ] Stale PID (process dead) allows new instance to start

### AC-6: Auth Middleware Bootstrap
- [ ] Auth middleware installed on FastAPI app
- [ ] All endpoints except `/v1/engine/status` require `Authorization: Bearer <token>`
- [ ] Missing/invalid token returns 401 with structured error
- [ ] Token read from keychain or fallback file
- [ ] If no token exists on first run, generate and store one
- [ ] Token masked in all logs (MaskingFormatter applied)

> **Scope Boundary**: This AC sets up the middleware and basic token generation.
> STORY-003 adds: rotation, reset CLI, rate limiting, advanced key management.

---

## Technical Design

### Startup Sequence

```python
async def start_engine():
    # 1. Check for existing instance
    if await check_existing_engine():
        logger.error("Engine already running")
        sys.exit(1)

    # 2. Initialize/load auth token
    token = await load_or_create_token()
    install_auth_middleware(app, token)

    # 3. Initialize database (run migrations)
    await init_database()

    # 4. Recover from crash
    await recover_orphaned_jobs()

    # 5. Write PID file
    write_pid_file()

    # 6. Start FastAPI server
    await start_server(host="127.0.0.1", port=47200)
```

### Auth Middleware (Minimal)

```python
from fastapi import Request, HTTPException
import secrets

def install_auth_middleware(app: FastAPI, expected_token: str):
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        # Skip auth for status endpoint
        if request.url.path == "/v1/engine/status":
            return await call_next(request)

        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            raise HTTPException(401, detail={
                "error_code": "E_AUTH_MISSING",
                "message": "Authorization header required"
            })

        token = auth[7:]
        if not secrets.compare_digest(token, expected_token):
            raise HTTPException(401, detail={
                "error_code": "E_AUTH_INVALID",
                "message": "Invalid token"
            })

        return await call_next(request)
```

### Files Changed/Created

- `src/redletters/engine/server.py` — FastAPI app and lifecycle
- `src/redletters/engine/health.py` — Status endpoint
- `src/redletters/engine/shutdown.py` — Graceful shutdown logic
- `src/redletters/engine/recovery.py` — Crash recovery
- `src/redletters/engine/singleton.py` — Instance detection
- `src/redletters/engine/auth.py` — Token loading and middleware
- `src/redletters/engine/logging.py` — MaskingFormatter for token safety

---

## Test Plan

| Test | Type | Description |
|------|------|-------------|
| `test_engine_binds_localhost_only` | Unit | Verify binding to 127.0.0.1 |
| `test_status_endpoint_returns_health` | Integration | GET /v1/engine/status |
| `test_status_works_without_auth` | Integration | No token needed for status |
| `test_other_endpoints_require_auth` | Integration | 401 without token |
| `test_valid_token_allows_access` | Integration | 200 with correct token |
| `test_graceful_shutdown_preserves_jobs` | Integration | Shutdown with queued job |
| `test_crash_recovery_marks_failed` | Integration | Simulate crash, verify recovery |
| `test_second_instance_exits` | Integration | Start two engines |
| `test_token_not_in_logs` | Unit | MaskingFormatter works |

---

## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Tests written and passing
- [ ] Engine can be started via `python -m redletters.engine`
- [ ] Engine survives GUI close/reopen
- [ ] Logs written to correct location (with tokens masked)
- [ ] Auth middleware rejects unauthenticated requests
- [ ] Token generated on first run and stored securely
- [ ] No regressions in existing CLI commands
