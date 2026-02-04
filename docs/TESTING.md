# Testing Policy

## Verification Gate

Before merging any PR, run the verification gate:

```bash
# From project root
make verify

# Or from gui directory
cd gui && npm run verify
```

This runs:
1. **Python backend tests** (`pytest tests/`)
2. **GUI unit tests** (`vitest`)
3. **Playwright mocked E2E** (no backend required)

All three must pass. No exceptions.

## Playwright Policy

### Mocked Suite (15 tests)

**Location**: `gui/e2e/gui-flow.spec.ts`

**Rule**: Mocked suite must be **100% pass** or we fix/remove tests before merging.

If anyone wants to merge with failures, they must:
1. Delete or `test.skip()` the failing test
2. Add an issue link in the skip reason
3. Add an expiry date (max 2 weeks)

Example:
```typescript
// SKIP: https://github.com/org/repo/issues/123 - expires 2026-02-18
test.skip("broken test", async ({ page }) => {
  // ...
});
```

Otherwise it becomes permanent trash that erodes trust in the suite.

### Real-Backend Smoke (1 test)

**Location**: `gui/e2e/real-backend-smoke.spec.ts`

**Purpose**: Proves the golden path works against a real backend:
1. Auth token injection works (reads from `~/.greek2english/.auth_token`)
2. Capabilities are fetched and contract resolves endpoints
3. A real translation request works end-to-end
4. Output renders correctly (Greek + English)

**Running**:
```bash
# Terminal 1: Start backend
make dev-backend

# Terminal 2: Run smoke test
make test-e2e-real

# Or auto-boot mode (CI)
make test-e2e-real-boot
```

**Rule**: Keep it ONE golden-path test. If it grows, it becomes flaky.
Split into separate focused tests only if they test genuinely different paths.

## Test Commands Reference

| Command | What it runs | Backend required? |
|---------|--------------|-------------------|
| `make verify` | All gates (backend + GUI + E2E mocked) | No |
| `make test` | Python backend tests | No |
| `make test-gui` | GUI vitest unit tests | No |
| `make test-e2e` | Playwright mocked tests | No |
| `make test-e2e-real` | Playwright real smoke | Yes |
| `make test-e2e-real-boot` | Real smoke with auto-boot | No (auto-starts) |

## Coverage Expectations

- **Backend**: No minimum, but critical paths must be tested
- **GUI unit**: 80%+ for new code
- **E2E mocked**: One test per major user journey
- **E2E real**: ONE golden-path test only

## When Tests Fail

1. **Don't skip without tracking**: Every skip needs an issue link
2. **Fix forward, not backward**: Don't revert code to make tests pass unless the code is wrong
3. **Flaky tests are bugs**: If a test is flaky, fix it or delete it
4. **Green is mandatory**: `make verify` must pass before merge
