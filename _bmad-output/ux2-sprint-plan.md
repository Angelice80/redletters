# UX Sprint 2 — Sprint Plan

## Prioritization Matrix (Impact x Frequency x Confidence)

| Story | Friction | Impact | Frequency | Confidence | Score | Priority |
|-------|----------|--------|-----------|------------|-------|----------|
| UX2.1 | F1 Token Soup | 9 | 10 | 8 | 720 | P1 |
| UX2.4 | F2+F3 Empty States | 7 | 8 | 9 | 504 | P2 |
| UX2.3 | F4 Compare UX | 6 | 6 | 8 | 288 | P3 |
| UX2.5 | F5 Keyboard Flow | 5 | 7 | 9 | 315 | P4 |
| UX2.6 | F6+F8 Visual Rhythm | 4 | 10 | 9 | 360 | P5 |

**Note**: UX2.2 (Inspector Dock) is descoped from this sprint. It requires significant layout changes and has moderate impact (F7). The popover is functional. We'll revisit in UX Sprint 3.

## Story Details

### UX2.1 — Token Display Density Control (P1)
**Friction**: F1 — Token soup in traceable view
**Scope**: PassageWorkspace.tsx rendering tokens
**AC**:
1. Remove bracket wrapping from token glosses in traceable view
2. Add subtle visual boundaries: increased spacing between tokens + hover highlight
3. Add density toggle (Compact/Comfortable) to rendering panel header
4. Default: Comfortable (current spacing); Compact: tighter spacing, smaller font
5. Persist choice in localStorage (`redletters_token_density`)
6. data-testid: `density-toggle`, `density-compact-btn`, `density-comfortable-btn`

**MCP Plan**:
- Before: Screenshot current bracket-heavy traceable view
- After: Screenshot both density modes
- Assert: No bracket characters `[` or `]` in token display
- Assert: `density-toggle` element exists
- Assert: Token container class changes between modes

**Estimated effort**: Medium

---

### UX2.4 — Empty State CTAs (P2)
**Friction**: F2 + F3 — Receipts and Variants empty states lack guided actions
**Scope**: PassageWorkspace.tsx (receipts/variants sections)
**AC**:
1. Receipts empty (no ledger, readable mode): Show "Re-translate in Traceable" **button** (not just text link)
2. Receipts empty (no ledger, traceable mode): Show "Try the traceable translator" **button** that switches translator select
3. Variants empty: Show "Manage Sources" **button** linking to /sources
4. All CTAs: styled as secondary buttons (border + text color, not primary blue)
5. data-testid: `receipts-cta-btn`, `variants-cta-btn`

**MCP Plan**:
- Before: Screenshot empty receipts + variants
- After: Screenshot with CTA buttons visible
- Assert: `receipts-cta-btn` exists and is visible
- Assert: `variants-cta-btn` exists and is visible
- Assert: CTA text matches expected action

**Estimated effort**: Small

---

### UX2.3 — Compare UX: Swap + Sticky Headers (P3)
**Friction**: F4 — Compare modal missing swap and sticky headers
**Scope**: CompareModal.tsx
**AC**:
1. Add "Swap A/B" button between the A/B config columns
2. Swap exchanges: current A becomes the new B config, B result becomes A
3. A/B result labels sticky (position: sticky, top: 0) when scrolling
4. data-testid: `compare-swap-btn`, `compare-label-a`, `compare-label-b`

**MCP Plan**:
- Before: Screenshot compare modal pre-run
- After: Run comparison, screenshot with results, click swap, screenshot after swap
- Assert: `compare-swap-btn` exists
- Assert: After swap, A label shows B's previous translator
- Assert: Result labels visible (sticky check via scroll)

**Estimated effort**: Medium

---

### UX2.5 — Keyboard & Focus Flow (P4)
**Friction**: F5 — Power navigation requires mouse
**Scope**: PassageWorkspace.tsx
**AC**:
1. `/` key focuses ref-input (when no modal open)
2. Enter in ref-input triggers translate
3. Esc closes: compare modal, token popover; returns focus to triggering element
4. Tab order: ref-input -> mode select -> translator select -> translate btn -> compare -> heatmap
5. data-testid attributes already exist on all controls

**MCP Plan**:
- Before: Screenshot showing ref-input not focused
- After: Use puppeteer_evaluate to dispatch `/` key, assert ref-input focused
- Assert: Esc closes compare modal
- Assert: Tab moves through toolbar in expected order

**Estimated effort**: Small

---

### UX2.6 — Visual Rhythm & Style Fixes (P5)
**Friction**: F6 + F8 — Style conflicts, chip inconsistency, responsive cramping
**Scope**: PassageWorkspace.tsx, CompareModal.tsx, Tooltip.tsx
**AC**:
1. Fix tab style conflict: use `borderBottom` only (no mix with `borderBottomColor`)
2. Normalize chip padding to 2px 8px in compare modal
3. Normalize token padding to 2px 4px for Greek tokens (was 2px 3px)
4. At 768px: Variants tab shows full "Variants" label (not truncated "Varia")
5. No layout regressions at 1280/768

**MCP Plan**:
- Before: Screenshot at 768px showing truncated tab
- After: Screenshot at 768px showing full tab labels
- Assert: No console style conflict warnings (check via getConsoleLogs)
- Assert: Tab label text is "Variants" not truncated
- Assert: Key controls visible at both widths

**Estimated effort**: Small

---

## Execution Order

1. **UX2.1** (Token Density) — highest impact, foundational UX change
2. **UX2.4** (Empty State CTAs) — quick wins, high visibility
3. **UX2.5** (Keyboard Flow) — enables faster testing of remaining stories
4. **UX2.3** (Compare UX) — medium effort, clear AC
5. **UX2.6** (Visual Rhythm) — polish pass, do last

## Journey Verification (End of Sprint)

| Journey | Description | Stories Involved |
|---------|-------------|-----------------|
| J1 | Empty -> translate -> traceable -> token click | UX2.1 |
| J2 | Readable -> switch traceable -> receipts | UX2.4 |
| J3 | Compare -> run -> results side-by-side | UX2.3 |
| J4 | Variants tab -> empty -> CTA | UX2.4 |
| J5 | Heatmap toggle -> legend -> colors | (existing) |
| J6 | Compare + Swap: results -> swap A/B -> labels update | UX2.3 |

## Definition of Done

- [ ] All 5 stories implemented with before/after MCP evidence
- [ ] `npx vitest run` — all tests pass
- [ ] `npx tsc --noEmit` — zero TypeScript errors
- [ ] Journey J1-J6 verified via MCP
- [ ] RELEASE gate: report.json PASS, screenshots >= 8, MANIFEST verified
- [ ] `_bmad-output/ux-changelog.md` updated with all 5 stories
- [ ] Evidence pack under `gui/_mcp_artifacts/releases/<slug>/`
