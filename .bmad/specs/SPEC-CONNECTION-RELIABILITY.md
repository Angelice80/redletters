# Tech Spec: GUI Connection Reliability Fix

**Version**: 1.0
**Status**: Draft
**Sprint**: 22
**Author**: BMAD Orchestrator
**Date**: 2026-02-05

---

## 1. Problem Statement

### Current Issue
Users cannot reliably connect the GUI to the backend because:

1. **Command Mismatch**: The ConnectionPanel "Quick Fix" hints show `redletters serve --port 47200` but the correct command is `redletters engine start --port 47200`
2. **Port Confusion**: Two different commands exist with different default ports:
   - `redletters serve` (old API mode) defaults to port **8000**
   - `redletters engine start` (new engine spine) defaults to port **47200**
3. **Documentation Inconsistency**: Older docs reference port 8000, newer docs reference 47200
4. **No Auto-Detection**: When the GUI cannot connect, it offers no help finding the backend on alternate ports

### Root Cause Analysis

| Component | Default Port | Command |
|-----------|-------------|---------|
| `redletters serve` (old) | 8000 | `redletters serve --port 8000` |
| `redletters engine start` (new) | 47200 | `redletters engine start --port 47200` |
| `python -m redletters` (module) | 8000 | Uses old serve path |
| GUI defaults | 47200 | Correct for engine spine |
| Makefile `make dev` | 47200 | Correct |

**Key Finding**: The GUI's ConnectionPanel.tsx line 281 shows:
```jsx
<code style={codeStyle}>redletters serve --port {localPort}</code>
```
This should be:
```jsx
<code style={codeStyle}>redletters engine start --port {localPort}</code>
```

---

## 2. Acceptance Criteria

### AC1: Correct Command in Quick Fix Steps
- [ ] ConnectionPanel shows `redletters engine start --port 47200` (not `serve`)
- [ ] ConnectionSettingsModal help text is consistent
- [ ] All user-facing hints show the correct command

### AC2: Health Check Improvements
- [ ] Unauthenticated health check tries root `/` endpoint first (already done per ADR-005)
- [ ] Clear distinction between: "unreachable" vs "auth required" vs "wrong backend mode"
- [ ] Show attempted URL in error messages

### AC3: Auto-Detect Backend
- [ ] "Auto-detect backend" button tries ports [47200, 8000, 5000] with fast timeout (2s each)
- [ ] On detection, show: "Backend found on port X. Switch to detected port?"
- [ ] Update port field and reconnect on confirmation

### AC4: Connection Settings Modal Polish
- [ ] Show/hide token toggle (already exists, verify it works)
- [ ] Show attempted URL in error messages
- [ ] Add copy-to-clipboard for token field
- [ ] Fix any broken icons/entities (audit unicode chars)

### AC5: Visual Polish
- [ ] Reduce "panic red" of disconnected state to a calmer warning style
- [ ] Consistent button styling between panels
- [ ] Subtle transitions for state changes
- [ ] Better spacing and typography

### AC6: Documentation Alignment
- [ ] Update docs/troubleshooting.md to use port 47200 and `engine start`
- [ ] Update docs/cli.md to clarify `serve` vs `engine start`
- [ ] Update docs/API.md port references
- [ ] Update docs/index.md with correct port

### AC7: Tests
- [ ] Unit test for URL builder with various port configurations
- [ ] Unit test for error classification (unreachable vs auth vs mismatch)
- [ ] E2E test for auto-detect flow (optional)

---

## 3. Technical Design

### 3.1 Single Source of Truth for Port

Create a shared constants file:
```typescript
// gui/src/api/constants.ts
export const DEFAULT_PORT = 47200;
export const FALLBACK_PORTS = [47200, 8000, 5000];
export const CORRECT_START_COMMAND = "redletters engine start";
export const CONNECTION_TIMEOUT_MS = 2000;
```

### 3.2 Auto-Detect Backend Logic

```typescript
// gui/src/api/client.ts
export async function detectBackendPort(
  ports: number[] = FALLBACK_PORTS,
  timeoutMs: number = CONNECTION_TIMEOUT_MS
): Promise<{ port: number; requiresAuth: boolean } | null> {
  for (const port of ports) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(`http://127.0.0.1:${port}/`, {
        method: "GET",
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (response.ok) {
        return { port, requiresAuth: false };
      }
      if (response.status === 401) {
        return { port, requiresAuth: true };
      }
    } catch {
      clearTimeout(timeout);
      // Continue to next port
    }
  }
  return null;
}
```

### 3.3 Error Classification Enhancement

Enhance `normalizeApiError` to include:
- Attempted URL in all error messages
- Clearer distinction between error types
- Suggested port switch when detecting mismatch

### 3.4 Visual Design Updates

**Current (panic red)**:
```css
backgroundColor: "#7f1d1d" /* Dark red */
border: "1px solid #991b1b" /* Red border */
```

**Proposed (calmer warning)**:
```css
backgroundColor: theme.colors.bgSecondary /* Dark gray */
border: `1px solid ${theme.colors.warning}` /* Amber border */
```

---

## 4. Stories

### S1: Unify Backend URL/Port Config
- Fix ConnectionPanel quick fix command to `redletters engine start`
- Create shared constants for port/command
- Update Makefile comments if needed

### S2: Health Check Improvements
- Show attempted URL in error messages
- Clearer error classification UI
- Better messages for auth vs unreachable vs mismatch

### S3: Auto-Detect Backend
- Add `detectBackendPort()` function
- Add "Auto-detect" button to ConnectionPanel
- Show detection results with one-click switch

### S4: Connection Settings Modal Polish
- Verify show/hide token works
- Add copy-to-clipboard affordance
- Show attempted URL on test failure
- Audit unicode icons for rendering issues

### S5: Visual Polish Pass
- Reduce severity of disconnected state colors
- Consistent button styling
- Add subtle transitions (opacity, background-color)
- Better spacing/typography

### S6: Update Documentation
- Fix port references in troubleshooting.md, cli.md, API.md, index.md
- Clarify `serve` vs `engine start` commands

### S7: Add Tests
- Unit tests for URL builder
- Unit tests for error classification
- Optional E2E for connection flow

---

## 5. Implementation Order

1. **S1**: Fix the immediate wrong-command bug
2. **S2**: Improve error messages (quick win)
3. **S6**: Fix documentation (quick win)
4. **S3**: Add auto-detect feature
5. **S4**: Modal polish
6. **S5**: Visual polish
7. **S7**: Tests

---

## 6. Verification Plan

### Manual Testing
1. Start backend with `redletters engine start --port 47200`
2. Open GUI - should connect without manual intervention
3. Stop backend - should show calmer disconnected state
4. Start on wrong port (8000) - should offer auto-detect
5. Click auto-detect - should find correct port

### Automated Testing
```bash
# Run unit tests
cd gui && npm test

# Run E2E tests (mocked)
npm run test:e2e

# Run real backend smoke test
npm run test:e2e:real

# Full verification
make verify
```

---

## 7. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing connections | High | Keep 47200 as default, only add features |
| Auto-detect hitting wrong service | Medium | Check response shape, not just 200 |
| Unicode icons not rendering | Low | Use common symbols or SVG fallbacks |

---

## 8. Definition of Done

- [ ] Backend on 47200 connects without manual port hunting
- [ ] Wrong port triggers auto-detect suggestion
- [ ] Quick Fix steps show correct `engine start` command
- [ ] All docs reference port 47200 for engine spine
- [ ] UI feels calmer (no panic-red for normal dev disconnect)
- [ ] `make dev` works end-to-end
- [ ] Tests pass

