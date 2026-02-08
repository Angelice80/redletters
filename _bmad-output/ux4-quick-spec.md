# UX Sprint 4 Quick Spec: Orientation + Sensemaking

**Sprint Goal:** Make Explore feel like a study instrument where users always know where they are, evidence feels unified and guided, and study presets reduce setup friction.

---

## Top 8 Friction Points

### Orientation Friction
1. **F1: No canonical ref display after translate** - After translating "John 3:16", the only ref indicator is the text input. Users lose context when scrolling in the center panel. (Screenshot: `UX4-baseline-demo-result-1280.png`)
2. **F2: Range display invisible** - When translating "Matt 5:3-12", no visible range indicator ("vX-vY") appears in the workspace. Users forget what range they're viewing.
3. **F3: Prev/Next blind navigation** - Users can't preview what's next/previous before navigating. They hesitate because clicking Prev/Next might lose their current study position. (Screenshot: `UX4-baseline-demo-result-1280.png`)
4. **F4: Recent refs buried** - The recent refs dropdown only appears when focusing the input field. No persistent "recent" affordance in the results view.

### Evidence Friction
5. **F5: Evidence split across unrelated tabs** - Receipts and Variants are in the right inspector panel; Confidence is in the center panel. Users must mentally connect these separate evidence streams. (Screenshot: `UX4-baseline-variants-tab-1280.png`)
6. **F6: Empty evidence states are dead ends** - When Variants show "No textual variants", the CTA is "Manage Sources" - but users wanted evidence, not administration. No progressive guidance.
7. **F7: No unified evidence entry point** - Users must know to look at Receipts tab, then Variants tab, then Confidence card separately. No "Evidence" concept ties them together.

### Setup Friction
8. **F8: Manual mode/density/view configuration every session** - Users who always want "Traceable + Compact + Inspector Dock" must configure this every time. No presets for common study workflows.

---

## UX Principles (max 5)

1. **P1: Always-visible orientation** - The canonical reference, mode, and range should be visible at all times in the results view without scrolling to the toolbar.
2. **P2: Evidence as unified concept** - Confidence, Receipts, and Variants are all "evidence" - present them as one tool with sub-views, not three separate features.
3. **P3: Progressive deepening, not dead ends** - Every empty state must offer exactly one clear next step that's truthful about what it will achieve.
4. **P4: Reduce setup friction** - Common study workflows should be one-click presets, not 3-4 manual configurations.
5. **P5: Honest previews** - Show users what they'll get before they commit (nav preview, mode descriptions, evidence availability).

---

## Target Outcomes

| Outcome | Metric | Target |
|---------|--------|--------|
| **O1: Fewer navigation mistakes** | Clicks to verify current position | From 2 (scroll to toolbar) to 0 (always visible strip) |
| **O2: Fewer clicks to evidence** | Clicks from results to seeing all evidence types | From 3 (scroll + tab + tab) to 1 (open Evidence panel) |
| **O3: Faster re-entry** | Actions to restore previous study session | From 4+ (pick ref, set mode, set density, set view) to 1 (select preset + pick recent ref) |

---

## UI Consistency Checklist

| Element | Standard | Applied In |
|---------|----------|-----------|
| Panel headers | 12px uppercase, `#9ca3af`, bottom border `#4b5563` | All panels |
| Chips/badges | 10px bold, rounded 3px, `#374151` bg | Rendering chips, mode chips |
| Sub-tabs | 12px, `#9ca3af` inactive, `#60a5fa` active, 2px bottom border | Inspector tabs |
| Buttons: primary | `#2563eb` bg, white text, 14px 600wt, 6px radius | Translate |
| Buttons: secondary | `#374151` bg, `#9ca3af` text, 12px, 4px radius | Compare, Heatmap, toggles |
| Buttons: CTA inline | transparent bg, `#60a5fa` text, 1px blue border, 12px, 4px radius | Empty state actions |
| Empty states | 13px, `#6b7280`, centered, with one primary next-step | All panels |
| Panel background | `#2d2d44` | All panels |
| Card background | `#1a1a2e` | Rendering card, confidence card |
| Spacing | Panel gaps: 16px (desktop), 8px (mobile) | Workspace grid |

---

## MCP Verification Plan

### Per-Story SMOKE Tests
Each story produces:
- 2+ "before" screenshots (baseline state before change)
- 2+ "after" screenshots (state with change active)
- 3+ DOM assertions tied to UX intent
- Testid stability verification

### End-of-Sprint RELEASE Journey
| Journey | Steps | Key Assertions |
|---------|-------|----------------|
| J7 - Orientation + Range | Enter "John 3:16-18" -> translate -> verify strip -> use recent | orientation-strip contains "John 3:16-18", recent refs populated |
| J8 - Evidence Guided Deepening | Start readable -> open evidence -> follow Next Action -> get receipts OR sources | evidence-panel visible, next-action-btn triggers correct flow |

---

## Testid Registry (UX4)

```
orientation-strip, orientation-ref, orientation-mode
recent-refs-btn, recent-refs-menu, recent-refs-item-{i}
nav-preview, prev-preview, next-preview
evidence-panel, evidence-tab-confidence, evidence-tab-receipts, evidence-tab-variants
evidence-next-action, evidence-next-action-btn
study-mode-select, study-mode-reader, study-mode-translator, study-mode-text-critic
```
