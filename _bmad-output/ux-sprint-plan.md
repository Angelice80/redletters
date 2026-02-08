# UX Sprint 1 Plan — Explore Screen Polish

**Sprint goal**: Fix the top 5 UX friction points in Explore, measured by before/after screenshots and DOM assertions.
**Stories**: 5 (ordered by Impact × Frequency score)
**Approach**: Each story follows the UX Iteration Loop (baseline → implement → verify → record).

---

## UX1 — Fix viewMode + Mode Chip Confusion (F1 + F2)
**Problem**: viewMode defaults to "readable" after URL navigation even when traceable data is loaded. Three mode chips ("translator", "generated in", "viewing") create cognitive overload.
**Changes**:
- Initialize `viewMode` from result mode when auto-translating from URL params.
- Reduce chips to maximum 2: show `[translator_type]` and a mismatch warning only when viewMode ≠ result.mode. Remove the redundant "generated in" chip when it matches viewMode.
- When viewMode matches result.mode, show only one chip: `[translator_type]`.

**Acceptance criteria**:
- After navigating to `/explore?ref=John+3:16&mode=traceable&tr=traceable`, viewMode is "traceable" and only 1-2 chips visible.
- When viewMode differs from result.mode, a single amber "viewing as: X" chip appears with a tooltip explaining the mismatch.
- No "generated in" chip when it matches viewMode.

**MCP verification**:
- Navigate to URL with mode=traceable; screenshot; assert `[data-testid="view-traceable-btn"]` has active style.
- Assert chip count ≤ 2 via `querySelectorAll` on chip container.
- Screenshot before/after comparison.

**Files**: `gui/src/screens/PassageWorkspace.tsx`

---

## UX2 — Translate Button Primary Action Emphasis (F5)
**Problem**: Translate button uses the same blue as toggles and links. It doesn't stand out as THE primary action.
**Changes**:
- Increase Translate button padding to `10px 24px`, font-size to `14px`, font-weight to `600`.
- Add a subtle glow/shadow: `boxShadow: '0 0 12px rgba(59,130,246,0.3)'`.
- Self-align it vertically with the input fields (currently floating due to label offset).
- Add `data-testid="translate-btn"` (already exists).

**Acceptance criteria**:
- Translate button is visually the most prominent element in the toolbar.
- Button vertically aligns with input baselines.
- At 768px, button doesn't wrap to a separate line from the ref input.

**MCP verification**:
- Screenshot toolbar at 1280px; assert translate-btn is visible.
- Screenshot toolbar at 768px; assert translate-btn is in same visual row as ref-input.
- Evaluate: confirm computed font-size ≥ 14px on translate-btn.

**Files**: `gui/src/screens/PassageWorkspace.tsx` (buttonStyle)

---

## UX3 — Toolbar Responsive Layout (F3)
**Problem**: At 768px, toolbar wraps to 2 lines with awkward control placement.
**Changes**:
- Wrap toolbar controls in a CSS flex layout with explicit `flex-wrap` breakpoints.
- Group 1 (row 1): Reference input with nav buttons (takes full width at narrow).
- Group 2 (row 2 at narrow): Mode + Translator selects + Translate button.
- Group 3 (right-aligned): Compare + Heatmap (stay on row 2 at narrow).
- Add `min-width: 0` on flex children to prevent overflow.

**Acceptance criteria**:
- At 1280px: single row, all controls visible.
- At 1024px: single row, slightly tighter spacing.
- At 768px: two neat rows — ref on top, controls + action on bottom. No overlapping.

**MCP verification**:
- Screenshot at 1280, 1024, 768; assert `[data-testid="translate-btn"]` visible at all 3.
- Assert no horizontal overflow via `document.body.scrollWidth <= window.innerWidth`.

**Files**: `gui/src/screens/PassageWorkspace.tsx` (toolbarStyle, inputGroupStyle)

---

## UX4 — Confidence Composite Progress Bar + Spacing (F7)
**Problem**: Composite Confidence shows as plain "87%" text with no visual bar, while layer bars below have bars. The "87%" runs directly into the label.
**Changes**:
- Add a progress bar for Composite Confidence matching the layer bar style (same height, same color logic).
- Add clear spacing between "Composite Confidence" label and the percentage.
- Make the percentage value slightly larger/bolder for scannability.

**Acceptance criteria**:
- Composite Confidence shows a colored progress bar.
- Visual hierarchy: composite bar is slightly taller (6px vs 4px) to indicate it's the summary.
- Label and value are visually separated (flexbox justify-between).

**MCP verification**:
- Screenshot confidence section; assert `[data-testid="confidence-composite"]` contains a child div with width > 0%.
- Assert composite bar height is ≥ 6px.

**Files**: `gui/src/screens/PassageWorkspace.tsx` (ConfidenceSummary / confidence section)

---

## UX5 — Greek Panel Misleading Alignment Message (F6)
**Problem**: Greek panel shows "Alignment not provided by backend. Token-level data requires Traceable mode." even when mode IS traceable (with literal translator). The message blames mode instead of translator.
**Changes**:
- Make the GreekTokenDisplay "no data" message context-aware: accept the current mode and translator as props.
- When mode is traceable but no ledger: "The [translator] translator did not return token alignment. Try the 'traceable' translator for per-token mapping."
- When mode is readable: "Token alignment requires Traceable mode. Switch Request Mode to Traceable and re-translate."

**Acceptance criteria**:
- With mode=traceable + translator=literal: message mentions translator, not mode.
- With mode=readable: message mentions mode.
- Message includes an actionable suggestion in both cases.

**MCP verification**:
- Navigate with mode=traceable&tr=literal; screenshot; assert `[data-testid="alignment-disabled-msg"]` text does NOT contain "requires Traceable mode".
- Navigate with mode=readable; screenshot; assert text contains "Traceable mode".

**Files**: `gui/src/components/GreekTokenDisplay.tsx`, `gui/src/screens/PassageWorkspace.tsx`

---

## Execution Order

| Order | Story | Estimated effort | Dependencies |
|-------|-------|-----------------|--------------|
| 1 | UX1 | Medium | None — fixes the most impactful bug |
| 2 | UX5 | Small | None — quick message fix |
| 3 | UX2 | Small | None — CSS-only |
| 4 | UX4 | Small | None — additive UI |
| 5 | UX3 | Medium | After UX2 (button sizing affects layout) |

## Definition of Done (per story)
- [ ] `cd gui && npx vitest run` — all tests pass
- [ ] `cd gui && npx tsc --noEmit` — zero type errors
- [ ] MCP screenshots saved to `gui/_mcp_artifacts/latest/screenshots/`
- [ ] At least 3 DOM assertions per story
- [ ] Entry in `_bmad-output/ux-changelog.md`

## Definition of Done (sprint)
- [ ] All 5 stories complete with evidence
- [ ] RELEASE evidence pack in `gui/_mcp_artifacts/releases/`
- [ ] Updated `_bmad-output/ux-changelog.md` with all 5 entries
