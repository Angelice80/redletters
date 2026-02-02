# Sprint 6 Receipt: GUI Source Management

## Summary

Sprint 6 adds GUI source management capabilities to the Red Letters system, allowing non-terminal users to install/uninstall data sources with proper EULA enforcement.

## Definition of Done ✅

- [x] User can launch GUI, go to Sources screen
- [x] User can install the canonical spine source
- [x] User can translate passages (e.g., "John 1:18")
- [x] Gate screen appears for MAJOR/SIGNIFICANT variants
- [x] After acknowledging variants, translation completes
- [x] All new tests pass
- [x] Full test suite passes (606 tests)

## Files Changed

### Backend (Python)

| File | Change | Purpose |
|------|--------|---------|
| `src/redletters/api/routes.py` | Modified | Added 5 `/sources/*` endpoints |
| `src/redletters/api/models.py` | Modified | Added Pydantic models for source API, fixed Python 3.8 compatibility |

### GUI (TypeScript/React)

| File | Change | Purpose |
|------|--------|---------|
| `gui/src/api/types.ts` | Modified | Added TypeScript types for source management |
| `gui/src/api/client.ts` | Modified | Added API client methods for sources |
| `gui/src/screens/Sources.tsx` | **Created** | New Sources management screen with EULA modal |
| `gui/src/screens/Translate.tsx` | Modified | Added spine-missing error CTA linking to Sources |
| `gui/src/App.tsx` | Modified | Added `/sources` route and nav link |

### Tests

| File | Change | Purpose |
|------|--------|---------|
| `tests/integration/test_source_api.py` | **Created** | 13 integration tests for source management API |

## New API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/sources` | List all configured sources from catalog |
| `GET` | `/sources/status` | Get installation status (includes spine info) |
| `POST` | `/sources/install` | Install a source with EULA enforcement |
| `POST` | `/sources/uninstall` | Uninstall an installed source |
| `GET` | `/sources/license` | Get license info for EULA modal |

## New Tests

1. `test_can_list_sources` - Verifies sources listing works
2. `test_sources_include_role_and_license` - Validates response structure
3. `test_status_shows_spine_info` - Checks spine detection
4. `test_install_spine_requires_no_eula_when_open_license` - Open license auto-install
5. `test_install_eula_source_requires_accept_eula` - EULA enforcement
6. `test_install_eula_source_succeeds_with_accept_eula` - EULA acceptance
7. `test_install_nonexistent_source_returns_404` - Error handling
8. `test_uninstall_source_updates_status` - Uninstall workflow
9. `test_uninstall_not_installed_returns_400` - Error handling
10. `test_license_info_returns_source_details` - License info endpoint
11. `test_license_info_nonexistent_returns_404` - Error handling
12. `test_full_flow_fresh_db_install_then_translate_then_gate_then_ack_then_translate` - E2E flow
13. `test_real_catalog_loads` - Real catalog integration

## ADR Confirmations

| ADR | Status | Notes |
|-----|--------|-------|
| ADR-007 | ✅ Preserved | SBLGNT remains canonical spine and default reading |
| ADR-008 | ✅ Preserved | Variants surfaced side-by-side; gates for major/significant |
| ADR-009 | ✅ Preserved | Readable (TYPE0-4) vs traceable (TYPE0-7) unchanged |
| ADR-010 | ✅ Preserved | Layered confidence always visible, never opaque |

## EULA Acceptance Contract

**Principle**: Server enforces, UI assists.

- **Open licenses** (CC-*, MIT, Apache-*, BSD-*, Public Domain): Install immediately
- **Restricted licenses** (EULA, Proprietary, Academic): Require `accept_eula: true`
- UI shows modal with license info + checkbox before calling install

## Commands Executed

```bash
# Linting
ruff check src/redletters/api/ tests/integration/test_source_api.py
# Output: All checks passed!

# Formatting
ruff format --check src/redletters/api/ tests/integration/test_source_api.py
# Output: 5 files already formatted

# Tests
python -m pytest -q
# Output: 606 passed, 531 warnings in 23.47s
```

## Manual Runbook

### API Testing

```bash
# List sources
curl http://localhost:8000/sources

# Get status
curl http://localhost:8000/sources/status

# Install spine (open license)
curl -X POST http://localhost:8000/sources/install \
  -H "Content-Type: application/json" \
  -d '{"source_id": "morphgnt-sblgnt"}'

# Install EULA source
curl -X POST http://localhost:8000/sources/install \
  -H "Content-Type: application/json" \
  -d '{"source_id": "sblgnt-apparatus", "accept_eula": true}'

# Get license info
curl "http://localhost:8000/sources/license?source_id=morphgnt-sblgnt"

# Uninstall
curl -X POST http://localhost:8000/sources/uninstall \
  -H "Content-Type: application/json" \
  -d '{"source_id": "morphgnt-sblgnt"}'
```

### GUI Testing

1. Start backend: `uvicorn src.redletters.api.main:app --reload`
2. Start GUI: `cd gui && npm run dev`
3. Navigate to http://localhost:5173
4. Click "Sources" in sidebar
5. Verify spine not installed (if fresh)
6. Click "Install" on morphgnt-sblgnt
7. Verify installation completes
8. Navigate to "Translate"
9. Enter "John 1:18" and click Translate
10. If gate appears, acknowledge variant
11. Verify translation completes

## Known Limitations

- No progress bar during installation (just "Installing..." status)
- Real installations require git to be available
- Python 3.8 compatibility required typing workarounds

## Python 3.8 Compatibility Fixes

The codebase had Python 3.10+ syntax (`str | None`, `list[T]`) that broke on Python 3.8. Fixed by:
- Using `Optional[str]` instead of `str | None`
- Using `List[T]` instead of `list[T]`
- Adding `typing_extensions` fallback for `Annotated`, `Literal`
- Keeping typing imports in namespace for Pydantic annotation evaluation

---

**Sprint 6 Complete** - Source management is operational for non-terminal use.
