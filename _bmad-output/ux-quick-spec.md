# UX Quick Spec — Explore Screen (Sprint 26)

## UX Principles

1. **Clarity > Clever** — Every control label, chip, and message must be immediately understandable. No jargon without explanation. If a state is unusual (e.g., viewing mode ≠ generation mode), explain it once, clearly.
2. **Progressive disclosure** — Show the minimum needed; reveal details on interaction. Token popover, confidence layers, and compare are already good examples. Apply the same pattern to the toolbar and panel states.
3. **Explain empty states** — When a panel has no content, explain WHY and WHAT TO DO NEXT. Never show blank space without context.
4. **Consistent controls** — Buttons, toggles, selectors, and chips should follow a visual hierarchy: primary action (Translate) > secondary actions (Compare, Heatmap) > state indicators (chips). Spacing, sizing, and color must be predictable.
5. **Minimum cognitive load** — Reduce the number of concepts the user must hold in working memory. Merge or hide redundant mode indicators. Auto-set sensible defaults.

## Core User Journeys

### J1: Look up a passage
1. User lands on Explore (empty state)
2. Types reference in input (or clicks example chip / demo button)
3. Presses Enter or clicks Translate
4. Sees Greek text (left), English rendering (center), and Receipts/Variants (right)
**Friction**: Translate button doesn't stand out; need to understand mode/translator first.

### J2: Switch to Traceable view
1. User has a readable result
2. Clicks "Traceable" view toggle (or accepts demo nudge)
3. Sees interactive tokens with hover/click behavior
**Friction**: If data was generated as readable, switching view shows a confusing stale-data warning with three chips.

### J3: Inspect a token
1. User clicks a Greek or English token
2. Popover shows morphology, gloss, confidence, risk
3. User can click "View Full Ledger" to see all tokens in receipts
**Friction**: Minimal — this flow works well. Minor: no keyboard shortcut to cycle tokens.

### J4: Understand confidence
1. User sees Composite Confidence score
2. Clicks a layer bar (e.g., Textual 55%)
3. Sees expanded detail panel with weak tokens listed
4. Can click a weak token to highlight it
**Friction**: Composite has no visual bar; layer click affordance is subtle.

### J5: Compare two renderings
1. User clicks Compare button
2. Configures B-side translator/mode
3. Clicks "Run Comparison"
4. Sees A/B side-by-side
**Friction**: A-side config area looks empty; no "swap A/B" option.

## UX Problem Inventory (Ranked by Impact × Frequency)

| Rank | ID | Problem | Impact | Freq | Score |
|------|-----|---------|--------|------|-------|
| 1 | F1 | viewMode defaults to readable after URL nav | High | High | 9 |
| 2 | F2 | Three mode chips cognitive overload | Med-Hi | High | 8 |
| 3 | F3 | Toolbar wraps awkwardly at 768px | Med-Hi | Med | 7 |
| 4 | F5 | Translate button blends into toolbar | Med | High | 7 |
| 5 | F4 | Receipts panel dead space in readable mode | Med | Med | 6 |
| 6 | F6 | Greek panel misleading "alignment not provided" | Med | Med | 6 |
| 7 | F7 | Confidence composite lacks progress bar | Low-Med | High | 5 |
| 8 | F8 | Ledger table clipped at narrow widths | Med | Low | 4 |
| 9 | F9 | Compare A-side visually empty | Low-Med | Low | 3 |
| 10 | F10 | CSS shorthand conflict console warning | Low | High | 2 |

## UI Consistency Plan

### Spacing tokens
- **Panel padding**: 16px (existing, keep)
- **Panel header**: 12px 16px padding, 12px font, 600 weight, uppercase (existing, keep)
- **Toolbar gap**: 12px between groups (existing, keep)
- **Card padding**: 16px (existing, keep)
- **Chip padding**: 2px 8px (existing, keep)

### Typography
- **Greek text**: 18px, serif family (SBL Greek/Cardo/Gentium Plus) — keep
- **Rendering text**: 16px, system font — keep
- **Labels**: 11px, #9ca3af, uppercase — keep
- **Body text**: 13-14px, #eaeaea — keep

### Color hierarchy
- **Primary action**: Should be distinct — propose `#2563eb` (blue-600) with larger padding
- **Secondary action**: `#374151` bg with `#9ca3af` text (existing toggle style)
- **Active toggle**: `#3b82f6` bg, white text (existing)
- **Disabled**: `#2d2d44` bg, `#4b5563` text, 0.5 opacity (existing)
- **Success/generated chip**: `#22c55e` (existing)
- **Warning chip**: `#f59e0b` (existing)
- **Danger/error**: `#ef4444` (existing)

### Chip styles (to standardize)
- **Info chip**: `#374151` bg, `#9ca3af` text (translator type, mode)
- **Status chip**: colored bg per semantic meaning
- **Rule**: Maximum 2 chips per rendering card. Merge redundant info.

## MCP Visual Review Plan

### Per-story SMOKE (minimum 4 screenshots, 3 assertions)
1. Navigate to Explore
2. Trigger the relevant interaction
3. Screenshot "before" state
4. Apply the UX change
5. Screenshot "after" state
6. Assert DOM state matches acceptance criteria (aria attributes, visible text, data-testid presence)
7. Save screenshots to `gui/_mcp_artifacts/latest/screenshots/UX-<story-id>-*.png`

### Sprint-end RELEASE (full evidence pack)
1. Navigate through all 5 user journeys (J1-J5)
2. Capture 15 screenshots (3 per journey)
3. Assert key DOM invariants at each step
4. Generate report.json + MANIFEST.json
5. Copy to `gui/_mcp_artifacts/releases/<timestamp>_<sha>/`
