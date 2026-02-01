# STORY-006: Path Allowlist System

**Epic**: Desktop App Architecture
**ADRs**: ADR-005
**Priority**: P1 (Security)
**Depends On**: STORY-001 (Engine Service Lifecycle)
**Estimate**: 1 day

---

## User Story

**As a** security-conscious user,
**I want** the engine to only access directories I explicitly allow,
**So that** malicious requests cannot read or write arbitrary files.

---

## Acceptance Criteria

### AC-1: Configuration File
- [ ] `~/.greek2english/config.toml` stores allowed paths
- [ ] Separate lists for input and output directories
- [ ] Paths expanded (~ → home directory)
- [ ] Paths resolved to absolute form

### AC-2: Implicit Allowlist
- [ ] Engine data directory always allowed
- [ ] Cache directory always allowed
- [ ] App bundle data directory (read-only) always allowed

### AC-3: Validation on API Calls
- [ ] Job creation validates input paths against allowlist
- [ ] Job creation validates output path against allowlist
- [ ] Clear error message when path not allowed
- [ ] Suggest CLI command to add path

### AC-4: Path Traversal Prevention
- [ ] Reject paths containing `..` that escape allowed directories
- [ ] Resolve symlinks and verify final path
- [ ] Log blocked attempts

### AC-5: CLI Commands
- [ ] `redletters paths list` shows current allowlist
- [ ] `redletters paths add <path>` adds to allowlist
- [ ] `redletters paths remove <path>` removes from allowlist

---

## Technical Design

### Configuration Schema

```toml
# ~/.greek2english/config.toml

[paths]
allowed_input_dirs = [
    "~/Documents/Greek2English/sources",
    "~/Downloads"
]
allowed_output_dirs = [
    "~/Documents/Greek2English/output"
]
```

### Path Validator

```python
from pathlib import Path

class PathValidator:
    def __init__(self, config: Config):
        self.allowed_input = self._resolve_paths(config.allowed_input_dirs)
        self.allowed_output = self._resolve_paths(config.allowed_output_dirs)
        self.data_dir = Path(config.data_dir).expanduser().resolve()
        self.cache_dir = self._get_cache_dir().resolve()

    def _resolve_paths(self, paths: list[str]) -> list[Path]:
        return [Path(p).expanduser().resolve() for p in paths]

    def validate_input(self, path: str) -> Path:
        resolved = Path(path).expanduser().resolve()

        # Check implicit allowlist
        if self._is_under(resolved, self.data_dir):
            return resolved

        # Check user allowlist
        for allowed in self.allowed_input:
            if self._is_under(resolved, allowed):
                return resolved

        raise PathNotAllowedError(
            f"Path not in allowed input directories: {path}. "
            f"Run: redletters paths add \"{path}\""
        )

    def validate_output(self, path: str) -> Path:
        resolved = Path(path).expanduser().resolve()

        if self._is_under(resolved, self.data_dir):
            return resolved

        for allowed in self.allowed_output:
            if self._is_under(resolved, allowed):
                return resolved

        raise PathNotAllowedError(
            f"Path not in allowed output directories: {path}. "
            f"Run: redletters paths add \"{path}\""
        )

    def _is_under(self, path: Path, base: Path) -> bool:
        try:
            path.relative_to(base)
            return True
        except ValueError:
            return False
```

### Files Changed/Created

- `src/redletters/engine/config.py` — Config loading with paths
- `src/redletters/engine/paths.py` — Path validation
- `src/redletters/cli/paths.py` — CLI commands

---

## Test Plan

| Test | Type | Description |
|------|------|-------------|
| `test_allowed_path_accepted` | Unit | Valid path |
| `test_disallowed_path_rejected` | Unit | Path outside allowlist |
| `test_implicit_data_dir_allowed` | Unit | Engine data dir |
| `test_path_traversal_blocked` | Unit | `../../etc/passwd` |
| `test_symlink_resolved` | Unit | Symlink to disallowed dir |
| `test_cli_paths_list` | CLI | Shows current config |
| `test_cli_paths_add` | CLI | Updates config file |
| `test_cli_paths_remove` | CLI | Updates config file |

---

## Definition of Done

- [ ] All acceptance criteria pass
- [ ] Tests written and passing
- [ ] Config file created on first run with sensible defaults
- [ ] Error messages actionable (include fix command)
- [ ] CLI commands update config file correctly
