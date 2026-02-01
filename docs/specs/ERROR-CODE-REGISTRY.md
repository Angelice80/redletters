# Error Code Registry

**Status**: Living Document
**Purpose**: Prevent stringly-typed error handling entropy. All error codes are reserved here.

---

## Rules

1. **All error codes start with `E_`** — Easy to grep, impossible to confuse with data
2. **Codes are SCREAMING_SNAKE_CASE** — Consistent, readable
3. **Codes are stable** — Once shipped, never rename (deprecate instead)
4. **Codes are documented here before use** — No ad-hoc invention
5. **Each code has one meaning** — No overloading

---

## Registry

### Authentication Errors (E_AUTH_*)

| Code | HTTP | Message | When |
|------|------|---------|------|
| `E_AUTH_MISSING` | 401 | Authorization header required | No `Authorization` header |
| `E_AUTH_INVALID` | 401 | Invalid token | Token doesn't match |
| `E_AUTH_MALFORMED` | 401 | Invalid authorization format | Not `Bearer <token>` |
| `E_AUTH_RATE_LIMITED` | 429 | Too many authentication failures | >10 failures in 60s |
| `E_AUTH_TOKEN_EXPIRED` | 401 | Token has expired | During rotation transition |

### Engine Errors (E_ENGINE_*)

| Code | HTTP | Message | When |
|------|------|---------|------|
| `E_ENGINE_STARTING` | 503 | Engine is starting | Request during boot |
| `E_ENGINE_SHUTTING_DOWN` | 503 | Engine is shutting down | Request during shutdown |
| `E_ENGINE_CRASH` | 500 | Engine terminated unexpectedly | Recovery after crash |
| `E_ENGINE_SAFE_MODE` | 503 | Engine in safe mode. Jobs disabled. | `--safe-mode` active |
| `E_ENGINE_VERSION_MISMATCH` | 409 | Client/engine version incompatible | API version drift |
| `E_ENGINE_DB_LOCKED` | 503 | Database is locked | SQLite contention |
| `E_ENGINE_DB_CORRUPT` | 500 | Database corruption detected | PRAGMA check failed |

### Job Errors (E_JOB_*)

| Code | HTTP | Message | When |
|------|------|---------|------|
| `E_JOB_NOT_FOUND` | 404 | Job not found | Invalid job_id |
| `E_JOB_INVALID_STATE` | 409 | Invalid state transition | Illegal state change |
| `E_JOB_ALREADY_CANCELLED` | 409 | Job already cancelled | Cancel on cancelled job |
| `E_JOB_ALREADY_COMPLETED` | 409 | Job already completed | Action on completed job |
| `E_JOB_STUCK_CLAIM_TIMEOUT` | 500 | Job stuck in claim | Worker failed to start |
| `E_JOB_EXECUTION_FAILED` | 500 | Job execution failed | Runtime error |
| `E_JOB_CANCELLED_BY_USER` | 200 | Job cancelled by user | User-initiated cancel |

### Validation Errors (E_VALIDATION_*)

| Code | HTTP | Message | When |
|------|------|---------|------|
| `E_VALIDATION_FAILED` | 422 | Validation failed | Generic validation error |
| `E_VALIDATION_MISSING_FIELD` | 422 | Required field missing | Missing required param |
| `E_VALIDATION_INVALID_FORMAT` | 422 | Invalid format | Malformed input |
| `E_VALIDATION_OUT_OF_RANGE` | 422 | Value out of range | Numeric bounds violated |

### Path/Security Errors (E_PATH_*)

| Code | HTTP | Message | When |
|------|------|---------|------|
| `E_PATH_NOT_ALLOWED` | 403 | Path not in allowed directories | Allowlist violation |
| `E_PATH_TRAVERSAL` | 403 | Directory traversal detected | `../` attack attempt |
| `E_PATH_NOT_FOUND` | 404 | Path does not exist | File/dir missing |
| `E_PATH_NOT_READABLE` | 403 | Path is not readable | Permission denied |
| `E_PATH_NOT_WRITABLE` | 403 | Path is not writable | Permission denied |

### Stream Errors (E_STREAM_*)

| Code | HTTP | Message | When |
|------|------|---------|------|
| `E_STREAM_INVALID_SEQUENCE` | 400 | Invalid sequence number | resume_from in future |
| `E_STREAM_GAP_TOO_LARGE` | 400 | Sequence gap too large | >10000 events behind |
| `E_STREAM_OVERFLOW` | 503 | Client buffer overflow | Ring buffer full |

### Receipt Errors (E_RECEIPT_*)

| Code | HTTP | Message | When |
|------|------|---------|------|
| `E_RECEIPT_NOT_FOUND` | 404 | Receipt not found | Job has no receipt yet |
| `E_RECEIPT_NOT_READY` | 409 | Receipt not yet available | Job still running |
| `E_RECEIPT_IMMUTABLE` | 409 | Receipt cannot be modified | Attempt to change receipt |

### Artifact Errors (E_ARTIFACT_*)

| Code | HTTP | Message | When |
|------|------|---------|------|
| `E_ARTIFACT_NOT_FOUND` | 404 | Artifact not found | Invalid artifact ID |
| `E_ARTIFACT_HASH_MISMATCH` | 409 | Artifact hash mismatch | Corruption detected |
| `E_ARTIFACT_SIZE_MISMATCH` | 409 | Artifact size mismatch | Truncation detected |

---

## Response Format

All errors follow this structure:

```json
{
  "error_code": "E_AUTH_INVALID",
  "message": "Invalid authentication token.",
  "details": {
    "hint": "Run 'redletters auth show' to view your token."
  }
}
```

**Required fields**: `error_code`, `message`
**Optional fields**: `details` (object with additional context)

---

## Adding New Codes

1. **Check this registry** — Code may already exist
2. **Pick the right prefix** — Match the domain (AUTH, JOB, PATH, etc.)
3. **Add to this document first** — Before writing code
4. **Include HTTP status** — Map to appropriate status code
5. **Write actionable message** — User should know what to do

---

## Deprecation

To deprecate a code:

1. Add `[DEPRECATED]` prefix in this document
2. Add deprecation notice in message: "This error code is deprecated. See E_NEW_CODE."
3. Keep returning the old code for 2 major versions
4. Remove after deprecation period

---

## Implementation

```python
# src/redletters/engine/errors.py

from enum import Enum
from dataclasses import dataclass

class ErrorCode(str, Enum):
    # Auth
    AUTH_MISSING = "E_AUTH_MISSING"
    AUTH_INVALID = "E_AUTH_INVALID"
    AUTH_MALFORMED = "E_AUTH_MALFORMED"
    AUTH_RATE_LIMITED = "E_AUTH_RATE_LIMITED"

    # Engine
    ENGINE_STARTING = "E_ENGINE_STARTING"
    ENGINE_SHUTTING_DOWN = "E_ENGINE_SHUTTING_DOWN"
    ENGINE_CRASH = "E_ENGINE_CRASH"
    ENGINE_SAFE_MODE = "E_ENGINE_SAFE_MODE"

    # Job
    JOB_NOT_FOUND = "E_JOB_NOT_FOUND"
    JOB_INVALID_STATE = "E_JOB_INVALID_STATE"
    JOB_STUCK_CLAIM_TIMEOUT = "E_JOB_STUCK_CLAIM_TIMEOUT"

    # ... etc


@dataclass
class AppError(Exception):
    code: ErrorCode
    message: str
    details: dict | None = None
    http_status: int = 500

    def to_response(self) -> dict:
        resp = {
            "error_code": self.code.value,
            "message": self.message,
        }
        if self.details:
            resp["details"] = self.details
        return resp


# Usage
raise AppError(
    code=ErrorCode.JOB_NOT_FOUND,
    message=f"Job not found: {job_id}",
    http_status=404
)
```

---

*Error codes are the API contract. Treat them like public functions: stable, documented, versioned.*
