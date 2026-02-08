# UX Sprint 3 Plan — Effortless Deep Study

## Story Prioritization (Impact x Frequency x Confidence)

| Story | Friction | Impact | Freq | Conf | Score | Effort |
|-------|----------|--------|------|------|-------|--------|
| UX3.0 | Evidence pack gaps | 10 | 10 | 10 | 1000 | S |
| UX3.1 | F1: Token Inspector Dock | 9 | 9 | 8 | 648 | L |
| UX3.2 | F2+F3: Mobile 390px+768px | 8 | 7 | 7 | 392 | L |
| UX3.5 | F6+F7: Focus+ARIA | 5 | 8 | 9 | 360 | M |

**Selected stories**: UX3.0 (done), UX3.1, UX3.2, UX3.5
**Deferred**: UX3.3 (Guided CTAs - already partially exists), UX3.4 (Compare diff - nice-to-have)

## Story Details

### UX3.0 — Evidence Pack Completeness (DONE)
**Status**: Complete. Added `copyScreenshotsToRelease()` and `verifyReleasePackCompleteness()` to `visualGateScreenshots.ts`. 7 new tests. 334 total tests passing.

### UX3.1 — Token Inspector Dock
**Problem**: Popovers are transient; users lose context; hard to compare token details.

**Acceptance Criteria**:
- [ ] Dock panel below the Rendering card shows selected token details
- [ ] Details include: position #, Greek surface, lemma, English gloss, confidence score
- [ ] Click Greek token -> dock populates with that token's data
- [ ] Click rendering token -> dock populates with aligned token's data
- [ ] Empty state: "Select a token to inspect" with subtle prompt
- [ ] Esc clears dock selection and returns focus to previously focused token
- [ ] Dock works in both Comfortable and Compact density modes

**Implementation Plan**:
1. Create `TokenInspectorDock` component (~80 lines)
2. Add `selectedTokenPosition` state to PassageWorkspace
3. Wire Greek token clicks and rendering token clicks to update dock
4. Add "generated in: traceable" chip styling for dock header
5. Add keyboard: Esc clears, focus returns to token list

**MCP Verification**:
- Before: screenshot of current traceable view (no dock)
- After: click token -> dock populated screenshot
- After: Esc -> dock cleared screenshot
- DOM: assert dock element visible, assert token data displayed, assert focus return

### UX3.2 — Mobile Layout (390px + 768px)
**Problem**: 3-column layout unusable below 900px. Sidebar covers content at 390px.

**Acceptance Criteria**:
- [ ] At <= 640px: sidebar collapses to hamburger menu; panels stack vertically
- [ ] At 641-900px: 2-column layout (Greek+Rendering stacked left, Inspector right)
- [ ] At > 900px: current 3-column layout preserved
- [ ] Toolbar wraps cleanly at all widths; Translate button always visible
- [ ] Token display remains usable at 390px
- [ ] Density toggle accessible at all widths

**Implementation Plan**:
1. Add CSS media queries / responsive breakpoints to PassageWorkspace
2. Create collapsible sidebar with hamburger toggle at <=640px
3. Rearrange grid template for 2-column and 1-column layouts
4. Ensure toolbar flex-wrap handles narrow widths
5. Test at 390x844, 768x1024, 1280x800

**MCP Verification**:
- Before: 390px cramped screenshot, 768px cramped screenshot
- After: 390px stacked layout, 768px 2-column layout
- DOM: assert translate-btn visible at 390px; assert no horizontal overflow

### UX3.5 — Accessibility Pass (Focus + ARIA + Escape)
**Problem**: Tab order jumps unexpectedly; toggle buttons lack aria-labels; Esc behavior inconsistent.

**Acceptance Criteria**:
- [ ] Tab order: ref input -> mode select -> translator select -> Translate btn -> Compare -> Heatmap -> panel content
- [ ] All toolbar buttons have aria-label (Prev, Next, Compare, Heatmap, density toggles)
- [ ] View toggle buttons (Compact/Comfortable/Readable/Traceable) have aria-label + aria-pressed
- [ ] Esc from Compare modal returns focus to Compare button
- [ ] Esc from Token dock returns focus to last selected token
- [ ] Dock panel has role="region" and aria-label="Token Inspector"

**Implementation Plan**:
1. Add aria-label to all toolbar interactive elements in PassageWorkspace
2. Add aria-pressed to toggle buttons (density, view mode)
3. Track "opener" element for modals/dock; restore focus on Esc
4. Add role="region" + aria-label to major sections (Greek panel, Rendering, Inspector, Dock)
5. Test focus order via puppeteer Tab key simulation

**MCP Verification**:
- DOM: assert aria-label on all toolbar buttons
- DOM: assert aria-pressed on active toggle
- Evaluate: Tab sequence check via `document.activeElement`
- Evaluate: Esc focus return test

## Execution Order

1. **UX3.0**: Evidence pack completeness (DONE)
2. **UX3.1**: Token Inspector Dock (builds on current receipts panel)
3. **UX3.5**: Accessibility pass (applies to all existing + new dock component)
4. **UX3.2**: Mobile layout (most invasive change, benefits from dock + a11y being settled)
5. **RELEASE**: Full evidence pack generation + MANIFEST verification

## Risk Mitigation

- **UX3.1 scope creep**: Dock shows ONLY position/surface/lemma/gloss/confidence. No drill-down, no comparison table. Keep it simple.
- **UX3.2 layout thrash**: Use CSS-only media queries where possible. Avoid JavaScript-based breakpoint detection to minimize re-render cost.
- **UX3.5 over-testing**: Focus on toolbar + dock + modal. Don't audit every element in the app.
