# UX Sprint 2 Quick Spec — Explore Readability Under Stress

## UX Principles (max 5)

1. **Progressive Disclosure**: Show essentials first; reveal detail on demand. Token inspection should not require leaving context.
2. **Spatial Anchoring**: The user should always know "where am I?" — sticky headers, persistent labels, clear panel identity.
3. **Actionable Empty States**: Every empty panel must offer a single primary next step, not just an explanation.
4. **Keyboard-First Navigation**: Power users should never need a mouse for core Explore workflows.
5. **Visual Rhythm Consistency**: Uniform spacing, typography scale, and chip/button hierarchy across all three panels.

## Target Outcomes

1. **Faster Scanning**: Users can identify token glosses, confidence, and alignment status within 2 seconds (vs current ~5s token soup).
2. **Fewer Dead Ends**: Every empty state (receipts, variants, alignment disabled) provides exactly one actionable CTA button — not just text.
3. **Keyboard Speed**: Core translate-inspect-compare flow achievable entirely via keyboard (`/` to focus, Enter to translate, Tab to navigate, Esc to close).

## Friction Inventory (Top 8)

### F1: Token Soup in Traceable View (HIGH)
- **Evidence**: `UX2-baseline-02b-traceable-result` — rendering shows `[οὕτω(ς)] [for] [love] [the] [God]...` as a wall of brackets.
- **Impact**: 9/10 — every traceable translation produces this. Users must mentally parse brackets to find structure.
- **Hypothesis**: Removing brackets, adding subtle token boundaries (spacing + hover highlight), and offering a compact/comfortable density toggle will cut scan time in half.

### F2: Receipts Panel Empty — No Clear Action (HIGH)
- **Evidence**: `UX2-baseline-07-receipts-empty` — "No token ledger returned for this translation... if the translator type does not support..."
- **Impact**: 7/10 — users with literal translator get a wall of text explaining why receipts are empty, but no button to fix it.
- **Hypothesis**: Replace explanation text with a single primary CTA: "Re-translate in Traceable mode" button. Keep explanation as secondary text.

### F3: Variants Panel Empty — No Guided Action (MEDIUM-HIGH)
- **Evidence**: `UX2-baseline-03-variants-tab` — "No textual variants at this reference..." with explanation but no CTA.
- **Impact**: 6/10 — users expecting variant data hit a dead end. Should guide to Sources screen or suggest different reference.
- **Hypothesis**: Add a CTA button: "Manage Sources" linking to /sources, with secondary text suggesting references known to have variants.

### F4: Compare Modal Missing Swap + Sticky Headers (MEDIUM)
- **Evidence**: `UX2-baseline-04-compare-modal` — A/B panels scroll off screen; no way to swap A/B; no visual diff emphasis.
- **Impact**: 6/10 — compare is functional but requires cognitive load to track which side is which after scrolling.
- **Hypothesis**: Add sticky A/B labels, a "Swap A/B" button, and a lightweight diff emphasis toggle.

### F5: Keyboard Flow Requires Mouse (MEDIUM)
- **Evidence**: No keyboard shortcut to focus ref input. Tab order through toolbar is inconsistent. Esc doesn't always return focus.
- **Impact**: 5/10 — power users moving between references must click, type, click, type.
- **Hypothesis**: `/` focuses ref input, Enter translates, Esc closes modals/popovers and returns focus, Tab order is logical.

### F6: Visual Rhythm Inconsistencies (LOW-MEDIUM)
- **Evidence**: Console warnings about `borderBottom` vs `borderBottomColor` conflicts in Tooltip/tab styles. Panel header padding varies (12px vs 16px). Chip sizing differs between rendering card and compare modal.
- **Impact**: 4/10 — doesn't break functionality but creates "prototype vibe."
- **Hypothesis**: Normalize panel headers to consistent padding/font-size. Fix style conflicts in tab components.

### F7: Token Inspection Context Switching (MEDIUM)
- **Evidence**: Token receipt popover overlays text and is fragile (closes on any click outside). No persistent inspection area.
- **Impact**: 5/10 — users wanting to compare multiple tokens must click, read, close, click next token.
- **Hypothesis**: Add an optional inspector dock (bottom or right) that pins selected token details. Popover remains for quick glance.

### F8: 768px Responsive Cramping (LOW-MEDIUM)
- **Evidence**: `UX2-baseline-06-responsive-768` — three columns at 768px are very narrow. Greek text wraps to single words per line. Variants tab label truncated to "Varia".
- **Impact**: 4/10 — rare use case (most users on desktop) but looks broken.
- **Hypothesis**: At <900px, collapse to 2-column or stacked layout. Tab labels should not truncate.

## UI Consistency Checklist

| Element | Current | Target |
|---------|---------|--------|
| Panel header padding | 12px 16px | 12px 16px (keep) |
| Panel header font | 12px/600 uppercase | 12px/600 uppercase (keep) |
| Tab padding | 12px 16px | 12px 16px (keep) |
| Tab active color | #60a5fa | #60a5fa (keep) |
| Chip padding | 2px 8px (rendering) vs 2px 6px (compare) | Normalize to 2px 8px |
| Button hierarchy | Primary: #2563eb / Toggle: #374151 / Disabled: #2d2d44 | Keep, ensure consistent |
| Token spacing | 2px 4px padding (rendering) / 2px 3px (Greek) | Normalize to 2px 4px |
| Empty state text | 13px #6b7280 | 13px #6b7280 (keep) |
| Card background | #1a1a2e | #1a1a2e (keep) |
| Panel background | #2d2d44 | #2d2d44 (keep) |
| Border color | #4b5563 | #4b5563 (keep) |
| Style conflicts | borderBottom vs borderBottomColor in tabs | Fix: use only borderBottom |

## MCP Verification Plan

### Per-Story Verification
- **Before**: 2+ MCP screenshots saved to `gui/_mcp_artifacts/latest/screenshots/UX2-<story>-before-*.png`
- **After**: 2+ MCP screenshots saved to `gui/_mcp_artifacts/latest/screenshots/UX2-<story>-after-*.png`
- **DOM Assertions**: 3+ per story, aligned to UX intent (not just element existence)
- **Tests**: `npx vitest run` + `npx tsc --noEmit` must pass after each story

### Per-Journey Verification (End of Sprint)
- J1: Empty state -> translate -> traceable view -> token click -> popover
- J2: Readable view -> switch to traceable -> receipts populated
- J3: Compare -> run comparison -> side-by-side results
- J4: Variants tab -> empty state -> CTA action
- J5: Heatmap toggle -> legend visible -> risk colors applied
- **J6 (NEW)**: Compare + Inspect: Compare results -> click token in A -> inspector updates -> swap A/B -> inspector remains coherent

### Sprint RELEASE Lane
- Minimum 8 screenshots on disk
- report.json with PASS gate
- MANIFEST hash verified
- Evidence pack under `gui/_mcp_artifacts/releases/<slug>/`
