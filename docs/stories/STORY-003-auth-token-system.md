# STORY-003: Auth Token Advanced Features

**Epic**: Desktop App Architecture
**ADRs**: ADR-005
**Priority**: P0 (Security Foundation)
**Depends On**: STORY-001 (Engine Service Lifecycle + Auth Middleware)
**Estimate**: 1.5 days

> **Scope Note**: Basic auth middleware and token generation moved to STORY-001.
> This story covers: rate limiting, CLI commands, rotation, advanced key management.

---

## User Story

**As a** user running Red Letters on a shared machine,
**I want** CLI tools to manage my auth token and rate limiting protection,
**So that** I can reset compromised tokens and prevent brute-force attacks.

---

## Acceptance Criteria

> **Note**: AC-1 and AC-2 from original story moved to STORY-001.
> STORY-001 now covers: token generation, storage, basic validation, middleware.

### AC-1: Rate Limiting
- [ ] After 10 failed auth attempts in 60 seconds, block for 60 seconds
- [ ] Return 429 with `Retry-After` header
- [ ] Rate limit keyed by client IP (for localhost, use connection ID)
- [ ] Counter resets on successful authentication

### AC-2: Token CLI Commands
- [ ] `redletters auth show` displays token (masked: `rl_a3f8...****`)
- [ ] `redletters auth show --reveal` displays full token
- [ ] `redletters auth reset` generates new token, updates keychain
- [ ] `redletters auth rotate` rotates with 60-second transition period

### AC-3: Token Rotation
- [ ] Rotation accepts both old and new tokens for 60 seconds
- [ ] After transition, old token is invalidated
- [ ] Engine emits `engine.token_rotated` event
- [ ] GUI receives event and updates stored token

---

## Technical Design

### Token Generation

```python
import secrets

def generate_auth_token() -> str:
    """Generate 256-bit token, base64url encoded with prefix."""
    raw = secrets.token_urlsafe(32)  # 43 chars
    return f"rl_{raw}"
```

### Keychain Storage (macOS)

```python
import keyring

def store_token(token: str):
    keyring.set_password(
        "com.redletters.engine",
        "auth_token",
        token
    )

def get_token() -> str | None:
    return keyring.get_password(
        "com.redletters.engine",
        "auth_token"
    )
```

### Auth Middleware

```python
from fastapi import Depends, HTTPException, Header
import secrets

async def require_auth(authorization: str = Header(None)):
    if authorization is None:
        raise HTTPException(401, detail={
            "error_code": "E_AUTH_MISSING",
            "message": "Authorization header required"
        })

    if not authorization.startswith("Bearer "):
        raise HTTPException(401, detail={
            "error_code": "E_AUTH_INVALID",
            "message": "Invalid authorization format"
        })

    token = authorization[7:]
    expected = get_stored_token()

    # Constant-time comparison
    if not secrets.compare_digest(token, expected):
        record_failed_attempt()
        raise HTTPException(401, detail={
            "error_code": "E_AUTH_INVALID",
            "message": "Invalid token"
        })
```

### Files Changed/Created

- `src/redletters/engine/auth.py` — Token generation, storage, validation
- `src/redletters/engine/middleware.py` — FastAPI auth dependency
- `src/redletters/cli/auth.py` — CLI commands
- `pyproject.toml` — Add `keyring` dependency

---

## Test Plan

| Test | Type | Description |
|------|------|-------------|
| `test_token_generation_entropy` | Unit | Verify 256-bit randomness |
| `test_missing_auth_returns_401` | Integration | No header |
| `test_invalid_token_returns_401` | Integration | Wrong token |
| `test_valid_token_allows_access` | Integration | Correct token |
| `test_rate_limiting_blocks_after_10` | Integration | Brute force prevention |
| `test_status_works_without_auth` | Integration | Public endpoint |
| `test_cli_auth_show_masked` | CLI | Token display |
| `test_cli_auth_reset_generates_new` | CLI | Token rotation |

---

## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Tests written and passing
- [ ] Token stored in OS keychain (verified on macOS and Linux)
- [ ] Fallback file storage works when keychain unavailable
- [ ] CLI commands work
- [ ] API documentation updated
