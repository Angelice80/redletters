# Sprint 24: Sprint Plan

## Sprint: Explore Screen Enhancement
**Duration:** 1 sprint (4 stories)
**Theme:** Transform Explore into a real translation explorer

## Stories

| ID | Title | Size | Dependencies |
|----|-------|------|-------------|
| S5 | Greek/Render Alignment Highlight + Token Popover | M | None |
| S6 | Confidence Click-Through to Weak Tokens | S | S5 (shares selection state) |
| S7 | Variants + Compare Purposeful Flow | M | None |
| S8 | Onboarding Demo Path | S | None |

## Implementation Order
S5 → S6 → S7 → S8

S5 and S6 share token selection state so S6 builds on S5.
S7 and S8 are independent but ordered for logical flow.

## Files Changed Per Story

### S5
- `gui/src/screens/PassageWorkspace.tsx` — add data-testids, Greek token rendering, selection state
- `gui/src/components/GreekTokenDisplay.tsx` — NEW: individual Greek token component
- Tests: unit test for alignment logic

### S6
- `gui/src/screens/PassageWorkspace.tsx` — make layers clickable
- `gui/src/components/ConfidenceDetailPanel.tsx` — NEW: weak token list panel
- Tests: unit test for token sorting by layer

### S7
- `gui/src/screens/PassageWorkspace.tsx` — wire compare button
- `gui/src/components/CompareModal.tsx` — NEW: A/B comparison dialog
- `gui/src/components/DossierPanel.tsx` — improve empty state
- Tests: unit test for compare state machine

### S8
- `gui/src/screens/PassageWorkspace.tsx` — demo button + nudge
- Tests: unit test for localStorage nudge logic

## Verification Per Story
1. `npx vitest run` — all tests pass
2. `npx tsc --noEmit` — zero type errors
3. Puppeteer MCP visual checks + screenshots

## Hard Constraints
- No new dependencies
- No fabricated data — if backend doesn't provide it, say so
- Reuse existing Tooltip component
- Additive backend fields only (no breaking changes)
- data-testid on every interactive element for MCP reliability
