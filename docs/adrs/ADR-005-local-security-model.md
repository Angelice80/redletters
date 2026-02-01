# ADR-005: Local Security Model

**Status**: Accepted
**Date**: 2026-01-27
**Context**: Desktop GUI Architecture (Phase 5)
**Supersedes**: None
**Related**: ADR-003 (Transport), ADR-004 (Persistence), ADR-006 (Packaging)

---

## Context

Red Letters runs as a local desktop application with two processes:
- **GUI** (Tauri): User interface
- **Engine** (FastAPI): Processing daemon

Both run on the same machine, communicating via HTTP on localhost. However, "local" does not mean "safe":

### Why Local Isn't Safe

| Threat | Attack Vector | Consequence |
|--------|---------------|-------------|
| **Malicious local apps** | Any process can connect to localhost:47200 | Data exfiltration, job injection |
| **Browser-based attacks** | JavaScript from any website can fetch localhost | CSRF, data theft |
| **Shared machine** | Other users on same machine | Unauthorized access to jobs |
| **Malware** | Keyloggers, screen capture | Credential theft |
| **Debug endpoints** | Exposed diagnostic APIs | Information disclosure |

This ADR defines the security model that makes "local" reasonably safe without enterprise-grade complexity.

## Decision

### Three-Layer Security

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1: Network Binding                                     │
│ • 127.0.0.1 only (no 0.0.0.0)                               │
│ • Blocks all external network access                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2: Authentication                                      │
│ • Per-install auth token (256-bit)                          │
│ • Bearer token in Authorization header                       │
│ • Token stored in OS keychain                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3: Path Allowlisting                                   │
│ • Engine only reads/writes approved directories             │
│ • User configures allowed paths explicitly                   │
│ • No arbitrary file system access                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Local-Only Bind

### Implementation

```python
# Engine startup
import uvicorn

uvicorn.run(
    app,
    host="127.0.0.1",  # NEVER "0.0.0.0"
    port=47200,
    log_level="info"
)
```

### Verification

On startup, engine verifies it cannot be reached externally:
```python
def verify_local_only():
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 47200))

    # Attempt external connection should fail
    try:
        external_sock = socket.socket()
        external_sock.settimeout(1)
        external_sock.connect((get_external_ip(), 47200))
        raise SecurityError("Engine accessible from external IP!")
    except (ConnectionRefusedError, TimeoutError):
        pass  # Expected - not reachable externally
```

### Port Selection

- **Default**: 47200 (arbitrary high port, unlikely to conflict)
- **Configurable**: Via `~/.greek2english/config.toml`
- **Fallback**: If 47200 busy, try 47201-47210, then fail

---

## Layer 2: Per-Install Auth Token

### Token Generation

On first install, generate a cryptographically secure token:

```python
import secrets

def generate_auth_token() -> str:
    """Generate 256-bit token, base64url encoded."""
    return secrets.token_urlsafe(32)  # 43 characters
```

### Token Storage (EXPLICIT DECISION)

**Primary Storage: OS Credential Manager** (REQUIRED IMPLEMENTATION)

| Platform | Backend | Why |
|----------|---------|-----|
| macOS | Keychain Services | Encrypted, hardware-backed, OS-managed |
| Windows | Credential Manager | Encrypted, per-user isolation |
| Linux | Secret Service (GNOME/KDE) | D-Bus secured, keyring integration |

```python
import keyring

# All platforms - keyring library abstracts the backend
keyring.set_password(
    "com.redletters.engine",  # Service name (consistent across platforms)
    "auth_token",              # Account
    token                      # Secret
)

def get_stored_token() -> str:
    return keyring.get_password("com.redletters.engine", "auth_token")
```

**Fallback Storage: File with Permissions** (ACCEPTED RISK)

If OS keychain is unavailable (headless Linux, WSL, broken keyring):

```
Location: ~/.greek2english/.auth_token
Mode: 0600 (chmod: owner read/write only)
Format: Plain text (just the token, no wrapper)
```

**Why File Fallback is Accepted (Not Ideal)**:

| Factor | Keychain | File (0600) |
|--------|----------|-------------|
| Encryption at rest | ✓ OS-managed | ✗ Plaintext |
| Protection from root | ✓ Partial | ✗ None |
| Cross-process isolation | ✓ Requires unlock | ✗ Any process as user |
| Headless/SSH support | ✗ May fail | ✓ Always works |

**Decision**: File fallback is acceptable because:
1. Defense in depth — token is one of three layers
2. Local threat model — if attacker has file access, they likely have keylogger too
3. Practicality — headless servers, CI/CD, and some Linux desktops need it

**Implementation MUST**:
1. Try keychain first, always
2. Log warning when falling back to file
3. Verify file permissions on read (refuse if world-readable)
4. Prompt user on first fallback: "Secure storage unavailable. Token will be stored in file."

```python
def store_token(token: str):
    """Store token, preferring keychain."""
    try:
        keyring.set_password("com.redletters.engine", "auth_token", token)
        log.info("Token stored in OS keychain")
    except keyring.errors.NoKeyringError:
        log.warning("OS keychain unavailable, falling back to file storage")
        _store_token_file(token)

def _store_token_file(token: str):
    path = Path("~/.greek2english/.auth_token").expanduser()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(token)
    path.chmod(0o600)

def get_stored_token() -> str:
    """Retrieve token, checking keychain first."""
    try:
        token = keyring.get_password("com.redletters.engine", "auth_token")
        if token:
            return token
    except keyring.errors.NoKeyringError:
        pass

    # Fallback to file
    path = Path("~/.greek2english/.auth_token").expanduser()
    if path.exists():
        # Verify permissions before reading
        mode = path.stat().st_mode & 0o777
        if mode != 0o600:
            raise SecurityError(f"Token file has unsafe permissions: {oct(mode)}")
        return path.read_text().strip()

    raise SecurityError("No auth token found")
```

### Token Usage

Every API request includes the token:

```http
GET /v1/engine/status HTTP/1.1
Host: 127.0.0.1:47200
Authorization: Bearer rl_a3f8c21e9b4d7f6e5a4b3c2d1e0f9g8h7i6j5k4l3m2n1o0p
```

### Token Validation

```python
from fastapi import Depends, HTTPException, Header

async def validate_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header")

    token = authorization[7:]
    expected = get_stored_token()

    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(token, expected):
        raise HTTPException(401, "Invalid token")

@app.get("/v1/engine/status")
async def get_status(_: None = Depends(validate_token)):
    return {"health": "healthy", ...}
```

### Token Prefix

Tokens are prefixed for easy identification:
- `rl_` — Red Letters token (production)
- `rl_test_` — Test token (development)
- `rl_demo_` — Demo mode (no actual processing)

---

## Layer 3: Path Allowlisting

### Principle

Engine ONLY accesses:
1. Its own data directory (`~/.greek2english/`)
2. User-configured input directories
3. User-configured output directories

NO arbitrary file system traversal.

### Configuration

```toml
# ~/.greek2english/config.toml

[paths]
# Directories engine can read from
allowed_input_dirs = [
    "~/Documents/Greek2English/sources",
    "~/Downloads"
]

# Directories engine can write to
allowed_output_dirs = [
    "~/Documents/Greek2English/output"
]

# Always allowed (engine data)
data_dir = "~/.greek2english"
```

### Implicit Allowlist (Always Permitted)

Per ADR-002 (Provenance-First Data Model), the engine fetches data at install time. The following directories are **implicitly allowed** without user configuration:

| Directory | Purpose | Permissions |
|-----------|---------|-------------|
| `~/.greek2english/` | Engine database, config, workspaces | Read/Write |
| `~/Library/Caches/Greek2English/` (macOS) | Downloaded sources (MorphGNT, lexicons) | Read/Write |
| `%LOCALAPPDATA%\Greek2English\` (Windows) | Downloaded sources | Read/Write |
| App bundle `data/` directory | Bundled demo corpus | Read-only |

These paths support the `redletters data fetch` workflow without requiring user allowlist configuration.

### Validation

```python
from pathlib import Path

class PathValidator:
    def __init__(self, config: Config):
        self.allowed_input = [Path(p).expanduser().resolve()
                              for p in config.allowed_input_dirs]
        self.allowed_output = [Path(p).expanduser().resolve()
                               for p in config.allowed_output_dirs]
        self.data_dir = Path(config.data_dir).expanduser().resolve()

    def validate_input_path(self, path: str) -> Path:
        resolved = Path(path).expanduser().resolve()

        # Check against allowlist
        for allowed in self.allowed_input:
            try:
                resolved.relative_to(allowed)
                return resolved
            except ValueError:
                continue

        raise SecurityError(f"Path not in allowed input directories: {path}")

    def validate_output_path(self, path: str) -> Path:
        resolved = Path(path).expanduser().resolve()

        for allowed in self.allowed_output:
            try:
                resolved.relative_to(allowed)
                return resolved
            except ValueError:
                continue

        raise SecurityError(f"Path not in allowed output directories: {path}")
```

### Path Traversal Prevention

```python
def safe_join(base: Path, user_path: str) -> Path:
    """Safely join paths, preventing traversal attacks."""
    # Normalize and resolve
    result = (base / user_path).resolve()

    # Verify still under base
    try:
        result.relative_to(base.resolve())
    except ValueError:
        raise SecurityError(f"Path traversal detected: {user_path}")

    return result
```

### GUI Path Selection

When user selects paths in GUI:
1. Native file picker (Tauri) returns absolute path
2. GUI sends path to engine for validation
3. Engine checks against allowlist
4. If not in allowlist, GUI prompts: "Add this directory to allowed locations?"
5. User confirms → path added to config

---

## Token Rotation & Reset

### When to Rotate

| Scenario | Action |
|----------|--------|
| Scheduled (annual) | Prompt user to rotate |
| Suspected compromise | User-initiated reset |
| GUI uninstall/reinstall | Generate new token |
| Engine reinstall | Generate new token |

### Rotation Process

```python
async def rotate_token():
    # 1. Generate new token
    new_token = generate_auth_token()

    # 2. Store new token
    store_token(new_token)

    # 3. Accept both old and new for 60 seconds
    old_token = get_current_token()
    set_transition_period(old_token, new_token, duration=60)

    # 4. After transition, invalidate old
    await asyncio.sleep(60)
    invalidate_token(old_token)

    # 5. Notify GUI to update
    emit_event("engine.token_rotated")
```

### Reset (Emergency)

If token is compromised:
1. `redletters auth reset` CLI command
2. Or: Delete keychain entry + restart engine
3. Engine generates new token on startup
4. GUI detects 401, prompts for new token

---

## Threat Model

### In-Scope Threats (We Defend Against)

| Threat | Mitigation |
|--------|------------|
| **Rogue localhost apps** | Auth token required |
| **Browser CSRF** | Auth token not in cookies |
| **Path traversal** | Strict allowlisting |
| **Credential theft via logs** | Tokens never logged |
| **Token guessing** | 256-bit entropy, rate limiting |
| **Stale token reuse** | Rotation support |

### Out-of-Scope Threats (User Responsibility)

| Threat | Why Out of Scope |
|--------|------------------|
| **Keylogger** | OS-level compromise; we can't defend |
| **Memory dumping** | Requires admin access; out of scope |
| **Physical access** | Full disk access defeats all software security |
| **Root/admin malware** | Can bypass any userspace protection |

### Threat Matrix

```
                    │ No Token │ Wrong Token │ Correct Token
────────────────────┼──────────┼─────────────┼───────────────
External network    │ BLOCKED  │ BLOCKED     │ BLOCKED (Layer 1)
Other local user    │ 401      │ 401         │ ACCESS (if token stolen)
Same user, browser  │ 401      │ 401         │ 401 (no cookie auth)
Same user, malware  │ 401      │ 401         │ ACCESS (if token stolen)
Authorized GUI      │ ACCESS   │ 401         │ ACCESS
```

---

## Why This Isn't Overkill

### "It's Just Local, Why Bother?"

Common misconception. Here's why we need security:

1. **Browser Attack Surface**: Any website can attempt `fetch('http://localhost:47200')`. Without auth, they'd succeed.

2. **Multi-User Machines**: Shared workstations exist. Other users shouldn't access your biblical scholarship.

3. **Defense in Depth**: If one layer fails, others protect. Binding alone isn't enough.

4. **Compliance Readiness**: If users want to process licensed lexicon data, we shouldn't be the weak link.

5. **User Trust**: Users should feel confident their work is protected.

### "Isn't This Enterprise Overkill?"

No. We're NOT implementing:
- TLS/certificates (localhost doesn't need it)
- User accounts/roles (single user)
- OAuth/OIDC (no external identity provider)
- Audit logging to SIEM (no enterprise compliance)
- Hardware security modules (overkill)

We ARE implementing:
- One secret (auth token)
- One check (allowlist)
- One bind (localhost)

This is the minimum viable security for a local desktop app.

---

## Token Safety: Logging & Diagnostics

### Tokens MUST NOT Appear In:

| Location | Risk | Mitigation |
|----------|------|------------|
| Engine logs | Log aggregation exposes token | Mask all `Authorization` headers |
| Diagnostic bundles | Support bundles shared externally | Scrub before export |
| Error messages | Stack traces may include request data | Sanitize before display |
| Config files | May be version-controlled | Token in keychain, not config |
| GUI console | Browser devtools visible | Mask in network tab |

### Log Masking Implementation

```python
import re

def mask_sensitive(text: str) -> str:
    """Mask tokens in log output."""
    # Mask Authorization headers
    text = re.sub(
        r'(Authorization:\s*Bearer\s+)rl_[A-Za-z0-9_-]+',
        r'\1rl_****MASKED****',
        text,
        flags=re.IGNORECASE
    )
    # Mask token values directly
    text = re.sub(
        r'rl_[A-Za-z0-9_-]{20,}',
        'rl_****MASKED****',
        text
    )
    return text

# Apply to all log handlers
class MaskingFormatter(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        return mask_sensitive(message)
```

### Diagnostic Bundle Scrubbing

```python
def create_diagnostic_bundle(output_path: Path):
    """Create support bundle with secrets scrubbed."""
    bundle = {
        "engine_status": get_status(),
        "recent_logs": get_recent_logs(masked=True),
        "config": get_config(exclude=["auth_token"]),
        "system_info": get_system_info(),
    }

    # Double-check: scan for token patterns
    bundle_str = json.dumps(bundle)
    if "rl_" in bundle_str and len(re.findall(r'rl_[A-Za-z0-9_-]{20,}', bundle_str)) > 0:
        raise SecurityError("Token detected in diagnostic bundle - aborting")

    write_bundle(output_path, bundle)
```

### GUI Token Handling

```typescript
// Never log the actual token
const maskedToken = token.slice(0, 6) + "****";
console.log(`Using token: ${maskedToken}`);

// In network requests, mark as sensitive
fetch(url, {
  headers: {
    "Authorization": `Bearer ${token}`,
    // Browser devtools will still show this, but at least we tried
  },
});
```

---

## Implementation Checklist

### Engine

- [ ] Bind to `127.0.0.1` only, reject `0.0.0.0`
- [ ] Generate token on first run
- [ ] Store token in OS keychain (with fallback)
- [ ] Validate token on every request (constant-time compare)
- [ ] Implement path allowlist validation
- [ ] **Never log tokens** — apply MaskingFormatter to all handlers
- [ ] **Scrub diagnostic bundles** — verify no tokens before export
- [ ] Rate limit failed auth attempts (10/minute)

### GUI

- [ ] Read token from keychain on startup
- [ ] Include token in all API requests
- [ ] Handle 401 gracefully (prompt for new token)
- [ ] Use native file picker for path selection
- [ ] Display current allowed paths in Settings
- [ ] Allow adding/removing allowed paths

### CLI

- [ ] `redletters auth show` — Display token (masked)
- [ ] `redletters auth reset` — Generate new token
- [ ] `redletters auth rotate` — Rotate with transition period
- [ ] `redletters paths list` — Show allowed paths
- [ ] `redletters paths add <path>` — Add to allowlist
- [ ] `redletters paths remove <path>` — Remove from allowlist

---

## Error Messages

```python
ERROR_MESSAGES = {
    "E_AUTH_MISSING":
        "Authorization header required. "
        "Include 'Authorization: Bearer <token>' in your request.",

    "E_AUTH_INVALID":
        "Invalid authentication token. "
        "Run 'redletters auth show' to view your token, "
        "or 'redletters auth reset' to generate a new one.",

    "E_AUTH_RATE_LIMITED":
        "Too many authentication failures. "
        "Wait 60 seconds before retrying.",

    "E_PATH_NOT_ALLOWED":
        "Path '{path}' is not in the allowed directories. "
        "Add it via Settings > Allowed Paths, or run: "
        "'redletters paths add \"{path}\"'",

    "E_PATH_TRAVERSAL":
        "Invalid path: directory traversal detected. "
        "Paths must stay within allowed directories.",
}
```

---

## Consequences

### Positive
- Defends against browser-based attacks
- Prevents unauthorized local access
- Simple model (one token, one allowlist)
- Uses OS-native secure storage
- Clear threat model with explicit scope

### Negative
- Token management adds user friction (minimal)
- Path allowlist requires configuration
- No protection against admin-level compromise (by design)

### Risks
- Token could be stolen by local malware (accepted risk)
- Allowlist misconfiguration could block legitimate access (recoverable)

---

## Related Documents

- [ADR-003](./ADR-003-ui-engine-transport-streaming.md) — Transport layer
- [ADR-004](./ADR-004-job-system-persistence.md) — Data persistence
- [ADR-006](./ADR-006-packaging-updates.md) — Packaging & secure distribution
- [Desktop App UX Spec](../specs/desktop-app-ux-architecture-spec.md) — Settings UI for path management
