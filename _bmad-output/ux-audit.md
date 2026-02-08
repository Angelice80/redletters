# UX Audit — Explore Screen (Sprint 26)

**Date**: 2026-02-07
**Auditor**: Claude (MCP Puppeteer visual audit)
**Baseline screenshots**: `gui/_mcp_artifacts/latest/screenshots/UX-audit-*.png`
**States captured**: 14 screenshots across empty, demo, readable, traceable, token selection, confidence detail, compare modal, heatmap, variants, and 3 viewport widths (1280, 1024, 768).

---

## Top 10 Friction Points

### F1 — viewMode defaults to "readable" after URL navigation with traceable data
**Severity**: High | **Frequency**: Every URL-based nav
**Evidence**: Screenshot 12 (`UX-audit-12-after-nav`)
After navigating to `/explore?ref=John+3:16&mode=traceable&tr=traceable`, the view shows "readable" mode with three confusing chips: "traceable", "generated in: traceable", "viewing: readable". The user must manually click "Traceable" to see the interactive token view they likely wanted.
**Root cause**: `viewMode` state initializes to `"readable"` (line 448) regardless of URL params or result mode.
**Fix**: Initialize `viewMode` from URL params or sync it to the result mode when data loads.

### F2 — Three mode chips create cognitive overload
**Severity**: Medium-High | **Frequency**: Every translation
**Evidence**: Screenshots 03, 12
The rendering card shows up to three chips simultaneously: `[traceable]` `[generated in: readable]` `[viewing: traceable]`. Users must mentally parse the difference between "request mode", "generation mode", and "viewing mode" — three concepts that should be at most two. The orange "viewing: X" chip especially causes confusion when it appears alongside "generated in: Y".
**Fix**: Collapse to at most two indicators. Show "generated in: X" always, and only show a mismatch warning when viewing mode differs from generated mode. Remove the translator-type chip from inside the card (it's already in the panel header).

### F3 — Toolbar wraps awkwardly at medium widths (768px)
**Severity**: Medium-High | **Frequency**: Tablet / split-screen users
**Evidence**: Screenshot 11 (`UX-audit-11-narrow-768`)
At 768px, the toolbar wraps to two lines. The Translator dropdown + Translate button move to the second row. Compare/Heatmap buttons float far right disconnected from the controls they relate to. The overall toolbar looks unstructured.
**Fix**: Group controls into logical clusters with responsive breakpoints. At narrow widths, stack Reference on its own row, then controls + action on a second row.

### F4 — Receipts panel wastes space in Readable mode
**Severity**: Medium | **Frequency**: Every readable translation
**Evidence**: Screenshot 02 (`UX-audit-02-demo-readable`)
The right panel (1/4 of screen) shows only a grey "Token ledger is available in Traceable mode. Re-translate in Traceable" message. This is dead space that makes the app feel empty and broken.
**Fix**: In readable mode, collapse the right panel or show useful contextual info (passage context, cross-references, word frequency). At minimum, make the "Re-translate in Traceable" CTA prominent and reduce the empty visual weight.

### F5 — Translate button doesn't stand out as primary action
**Severity**: Medium | **Frequency**: First-time users
**Evidence**: Screenshot 01 (`UX-audit-01-empty-state`)
The Translate button uses `#3b82f6` (standard blue) — the same color used for active toggles, links, and the Explore nav highlight. It blends into the toolbar rather than commanding attention. Meanwhile, the "Try a demo" button is green and more visually prominent.
**Fix**: Make Translate larger, use a stronger visual weight (larger padding, bolder text, or a distinctive accent color). Consider adding an icon or making it the only fully-filled button in the toolbar.

### F6 — Greek panel shows "alignment not provided" even with traceable data
**Severity**: Medium | **Frequency**: Specific translator combos
**Evidence**: Screenshot 04 (`UX-audit-04-traceable-result`)
When using `mode=traceable` + `translator=literal`, the Greek panel shows italic grey text "Alignment not provided by backend for this result. Token-level data requires Traceable mode." — even though mode IS traceable. The issue is the literal translator doesn't produce ledger data, but the message blames the mode rather than the translator.
**Fix**: Distinguish between "mode doesn't support tokens" vs "translator doesn't produce tokens". Message should say "The literal translator does not produce token-level alignment. Try the traceable translator for per-token mapping."

### F7 — Confidence composite has no progress bar
**Severity**: Low-Medium | **Frequency**: Every result
**Evidence**: Screenshots 04, 05
The "Composite Confidence 87%" is displayed as plain text with no visual bar, while the individual layers below it have bars. The composite feels like a heading rather than a data point. The 87% text also runs directly into the label with no visual separation.
**Fix**: Add a composite progress bar matching the layer style. Add clear spacing between label and value.

### F8 — Receipts Ledger table clipped at narrow widths
**Severity**: Medium | **Frequency**: Narrow viewport users
**Evidence**: Screenshot 11 (`UX-audit-11-narrow-768`)
At 768px, the right panel shows `#`, then Surface column is truncated to 2-3 chars, and Lemma column is invisible. The core scholarly data becomes unreadable.
**Fix**: Make the ledger table horizontally scrollable within its panel, or switch to a stacked card layout at narrow widths.

### F9 — Compare modal A-side is visually empty
**Severity**: Low-Medium | **Frequency**: Every compare
**Evidence**: Screenshot 08 (`UX-audit-08-compare-modal`)
The A—CURRENT card shows just two small chips with vast whitespace, while B—COMPARE WITH has interactive selectors. The visual imbalance makes A look broken. After results load, A and B are fine — the issue is only in the config phase.
**Fix**: Show a preview of A's translation text in the config area, or balance the layout by making both sides show read-only summaries of their settings.

### F10 — CSS shorthand conflict warning in console
**Severity**: Low | **Frequency**: Every render
**Evidence**: Console output during screenshot capture
React warns: "Removing borderColor when conflicting border property set" — caused by inline style objects that mix `border` and `borderColor`. Not user-visible but indicates styling fragility.
**Fix**: Clean up inline styles in button components (especially in the toolbar toggle buttons) to avoid mixing shorthand and longhand CSS properties.

---

## Additional Observations

### Positive UX patterns already in place:
- **Token popover** (Screenshot 06): Rich, well-organized with morphology, gloss, confidence bars, risk assessment. Good progressive disclosure.
- **Confidence layer detail** (Screenshot 07): Clickable layers expanding to show weak tokens is excellent scholarly UX.
- **Heatmap mode** (Screenshot 13): Underline-based risk visualization is subtle and non-disruptive.
- **Empty state** (Screenshot 01): Demo button + example chips + recent refs is a solid onboarding flow.
- **Tooltip system**: Comprehensive accessibility with portal rendering, keyboard support, and delay.
- **Variants empty state** (Screenshot 14): Good contextual explanation of why no variants exist.

### Minor notes:
- The "x" close button on the compare modal (line 220 of CompareModal.tsx) uses a lowercase letter "x" instead of a proper × or icon.
- Heatmap legend uses "High confidence" / "Medium" / "Low confidence" / "Very low" — inconsistent labeling (some have "confidence", some don't).
- At 1024px (Screenshot 10b), the layout still works but feels cramped — the 1:2:1 grid ratio could benefit from adjusting at this breakpoint.

---

## Screenshot Reference Index

| # | File | State | Key observation |
|---|------|-------|----------------|
| 01 | UX-audit-01-empty-state | Empty explore, connected | Good onboarding but Translate button blends in |
| 02 | UX-audit-02-demo-readable | Demo result, readable | Right panel is dead space |
| 03 | UX-audit-03-traceable-view | Switched to traceable view (no token data) | Three chips confusion, stale data warning |
| 04 | UX-audit-04-traceable-result | Traceable mode + literal translator | No ledger despite traceable mode |
| 05 | UX-audit-05-traceable-translator | Traceable mode + traceable translator | Full experience, tokens visible |
| 06 | UX-audit-06-token-selected | Greek token selected, popover | Good popover UX, alignment works |
| 07 | UX-audit-07-confidence-detail | Textual layer expanded | Detail panel functional |
| 08 | UX-audit-08-compare-modal | Compare modal, pre-run | A-side visually empty |
| 09 | UX-audit-09-compare-results | Compare modal, post-run | Results display clean |
| 10b | UX-audit-10b-narrow-1024 | 1024px viewport | Slightly cramped but functional |
| 11 | UX-audit-11-narrow-768 | 768px viewport | Toolbar wraps, ledger clipped |
| 12 | UX-audit-12-after-nav | URL navigation result | viewMode mismatch |
| 13 | UX-audit-13-heatmap | Heatmap mode active | Underlines visible, legend present |
| 14 | UX-audit-14-variants-tab | Variants tab, no variants | Good empty state explanation |
