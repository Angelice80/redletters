# UX Sprint 3 Quick Spec — Effortless Deep Study

## UX Principles (max 5)

1. **Pinned Context**: Token details should persist in a dock, not vanish with popovers. Users should never chase disappearing UI during study.
2. **Responsive-First Layout**: The same Explore screen must work from 390px (mobile) to 1440px (desktop) without clipping, overlap, or loss of functionality.
3. **Guided Recovery**: Every empty state or dead-end provides a direct CTA to fix it. After taking action, the user returns to their original context intact.
4. **Logical Focus Flow**: Tab order mirrors visual layout (toolbar -> panels -> tabs). Esc always returns focus to the opener. No focus traps.
5. **Minimal Context Switches**: Compare diff highlighting, inspector dock, and inline CTAs keep users in flow without navigating away.

## Target Outcomes (3 measurable behaviors)

1. **Fewer Clicks**: Token inspection via dock removes popover-close-reopen cycle; average clicks to compare 3 tokens: 3 (was ~9 with popovers).
2. **Fewer Dead Ends**: 0 empty states without a direct CTA. Variants "Manage Sources" + Receipts "Try traceable" both navigate and preserve Explore context.
3. **Faster Scanning**: At 390px, all content is readable without horizontal scrolling. At 768px, 2-column layout replaces cramped 3-column.

## Friction Inventory (Top 8)

### F1: Token Inspection Requires Chasing Popovers (HIGH)
- **Evidence**: `UX3-baseline-1280-traceable-full` — ledger table shows tokens but no persistent detail view for selected token. Popovers close on outside click.
- **Impact**: 9/10 — every traceable study session requires repeated click-read-lose cycles.
- **Hypothesis**: A bottom dock panel that pins the currently selected token's details (Greek surface, lemma, gloss, confidence, alignment) will eliminate the chase.

### F2: 390px Mobile Layout Completely Broken (HIGH)
- **Evidence**: `UX3-baseline-390-traceable` — sidebar takes ~40% width, 3-column grid clips all panels, text unreadable, toolbar overflows.
- **Impact**: 8/10 — mobile users cannot use the app at all. Sidebar covers content area.
- **Hypothesis**: At <640px, hide sidebar behind hamburger menu, stack panels vertically, make toolbar wrap cleanly.

### F3: 768px Tablet Layout Severely Cramped (HIGH)
- **Evidence**: `UX3-baseline-768-traceable` — columns all truncated, receipts panel shows only "#" and "S" column headers.
- **Impact**: 7/10 — tablet/small-laptop users get a broken experience.
- **Hypothesis**: At <900px, switch to 2-column layout (Greek+Rendering stacked, Inspector as collapsible panel). At <640px, fully stacked.

### F4: Variants "No Variants" Dead-End (MEDIUM-HIGH)
- **Evidence**: `UX3-baseline-1280-variants-empty` — "Manage Sources" link exists but doesn't preserve Explore state on return.
- **Impact**: 6/10 — user leaves Explore context, goes to Sources, then must re-navigate back and re-translate.
- **Hypothesis**: CTA should open Sources as modal or side-panel, or use browser history so Back returns to same Explore state.

### F5: Compare Modal Lacks Diff Emphasis (MEDIUM)
- **Evidence**: `UX3-baseline-1280-compare-results` — A/B panes show plain text side by side. User must manually spot differences.
- **Impact**: 5/10 — compare is functional but high-effort for long passages.
- **Hypothesis**: A "Show Differences" toggle that highlights word-level differences between A and B.

### F6: Focus Order Inconsistencies (MEDIUM)
- **Evidence**: Tab key from toolbar skips to sidebar instead of flowing into content panels. Compare modal doesn't trap focus.
- **Impact**: 5/10 — keyboard and screen reader users hit unexpected focus jumps.
- **Hypothesis**: Set tabindex order: toolbar -> active panel -> tabs -> tab content. Modal focus trap with Esc return.

### F7: Missing ARIA Labels on Interactive Elements (MEDIUM)
- **Evidence**: Compact/Comfortable/Readable/Traceable toggle buttons lack aria-labels. Prev/Next arrows have no accessible names.
- **Impact**: 4/10 — screen readers announce "button" without context.
- **Hypothesis**: Add aria-label to all toolbar controls, view toggles, and navigation arrows.

### F8: Token Dock Empty State Not Discoverable (LOW-MEDIUM)
- **Evidence**: New users won't know to click tokens. Current receipts panel jumps straight to ledger table with no guidance.
- **Impact**: 3/10 — solvable with clear empty state: "Select a token to inspect."
- **Hypothesis**: Token dock shows invitation text + subtle token highlight animation on first load.

## MCP Verification Plan

### Per-Story SMOKE Verification
- **Before**: 2+ MCP screenshots saved to `gui/_mcp_artifacts/latest/screenshots/UX3-<story>-before-*.png`
- **After**: 2+ MCP screenshots saved to `gui/_mcp_artifacts/latest/screenshots/UX3-<story>-after-*.png`
- **DOM Assertions**: 3+ per story via `puppeteer_evaluate`
- **Tests**: `npx vitest run` + `npx tsc --noEmit` must pass after each story

### End-of-Sprint RELEASE Verification
- Minimum 8 screenshots on disk in `gui/_mcp_artifacts/releases/<slug>/screenshots/`
- report.json with gate=PASS
- MANIFEST.json with verified hashes
- All screenshotPaths from report.json present in release directory (UX3.0 enforcement)
- Evidence pack completeness: `verifyReleasePackCompleteness()` returns `complete: true`
