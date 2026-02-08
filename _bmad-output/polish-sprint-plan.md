# Visual Polish Sprint — Sprint Plan

## Sprint Goal
Ship a consistent design system feel that upgrades Red Letters from "functional admin tool" to "premium scholarly app."

## Stories (ordered by dependency)

### P1 — Design Tokens Foundation (CSS variables)
**Priority:** CRITICAL (all other stories depend on this)
**Points:** 3
**Depends on:** Baseline screenshots captured

**Problem:** Styles are scattered across inline style objects with hardcoded hex values. Polish requires a single source of truth.

**Deliverables:**
1. Add CSS custom properties to `gui/index.html` `<style>` block under `:root`
2. Define all tokens from polish-quick-spec.md (colors, typography, radius, spacing, shadows, transitions)
3. Update `gui/src/theme.ts` to reference CSS variables via `var(--rl-*)` syntax where used in inline styles
4. Update `App.tsx` root div to use `var(--rl-bg-app)` instead of hardcoded `#1a1a2e`
5. Update sidebar, header to use appropriate surface tokens

**AC:**
- All tokens exist in one place (`:root` block in index.html)
- `document.documentElement.style.getPropertyValue('--rl-bg-app')` returns expected value in browser console
- No visual regressions on S1+S2 baseline states (layout matches, possibly improved contrast)
- `npx vitest run` passes
- `npx tsc --noEmit` passes

**MCP:** Re-capture S1+S2 baselines after; DOM assertion: CSS variable readable

---

### P2 — Surface Hierarchy Upgrade (3-layer system)
**Priority:** HIGH
**Points:** 3
**Depends on:** P1

**Problem:** Too much same-value dark (`#2d2d44` everywhere); low visual hierarchy between app bg, panels, and cards.

**Deliverables:**
1. Set app shell background to `var(--rl-bg-app)` (darker than current)
2. Sidebar and panel containers use `var(--rl-bg-panel)`
3. Cards, controls, elevated surfaces use `var(--rl-bg-card)`
4. Add subtle `var(--rl-border)` borders to panels
5. Add minimal `var(--rl-shadow-sm)` to cards

**AC:**
- Panels visually distinct from app background
- Cards visually distinct from panels
- Borders consistent (1px, same token color)
- No overflow or layout regressions at 390px

**MCP:** Screenshots of Dashboard + Explore; assert 3 distinct background values

---

### P3 — Typography Hierarchy + Reading Mode Font
**Priority:** HIGH
**Points:** 2
**Depends on:** P1

**Problem:** Text hierarchy is weak; everything at similar sizes/weights. Readable mode uses UI font.

**Deliverables:**
1. Page titles (Dashboard, Explore, etc.) use `--rl-fs-xl` + `--rl-font-ui` + weight 600
2. Section headings (panel headers) use `--rl-fs-sm` + uppercase + `--rl-text-muted`
3. Body text uses `--rl-fs-base`
4. Values/stats use `--rl-fs-lg` + weight 600
5. Readable rendering mode: apply `--rl-font-reading` with `line-height: 1.7`

**AC:**
- Titles/headers/labels clearly differentiated in screenshots
- Readable text uses serif font and comfortable line-height
- No overflow regressions at 390px

**MCP:** Screenshot Explore readable view; assert readable container references reading font

---

### P4 — Color Discipline + Brand Accent Alignment
**Priority:** HIGH
**Points:** 2
**Depends on:** P1

**Problem:** "Red Letters" brand reads as blue UI. Red only in logo. Primary CTA blends with toggles.

**Deliverables:**
1. Translate button uses `--rl-accent` (ember red) as background, not blue
2. Active nav indicator uses `--rl-accent` (left rail bar, not full bg fill)
3. Orientation strip chips use accent sparingly for mode indicator
4. Reserve `--rl-success` (green) exclusively for connection/health status
5. Remove blue from active nav link background

**AC:**
- Accent appears in <= 3 component categories (nav indicator, primary CTA, key chips)
- Dashboard connected badge remains green
- Success/warn/error are semantically consistent
- No brand-color confusion between red and blue

**MCP:** Screenshot Dashboard + Explore; assert Translate button has accent color; assert active nav has accent indicator

---

### P5 — Sidebar & Navigation Polish (icons + grouping)
**Priority:** MEDIUM
**Points:** 3
**Depends on:** P2, P4

**Problem:** Nav is functional but bland — plain text links, no grouping, active state is a big blue brick.

**Deliverables:**
1. Add inline SVG icons (simple, 16px) next to each nav link
2. Group nav into sections: **Study** (Explore, Export), **Data** (Sources, Jobs), **System** (Dashboard, Settings)
3. Section labels: `--rl-fs-xs`, uppercase, `--rl-text-dim`, `--rl-space-3` margin-top
4. Active nav: 3px left border `--rl-accent`, `--rl-accent-subtle` bg, `--rl-text` color
5. Hover nav: `--rl-bg-hover` bg
6. Logo: add small subtitle "Greek Scholarly Tools" in `--rl-text-dim` at `--rl-fs-xs`

**AC:**
- Navigation scanning is faster; icons provide visual anchors
- Active item obvious without "big blue block"
- Keyboard focus visible and unclipped
- Grouping visible at all viewports

**MCP:** Screenshot sidebar at all 3 viewports; assert active item has left border; assert section labels exist

---

### P6 — Empty State Composition (intentional, not vacant)
**Priority:** MEDIUM
**Points:** 2
**Depends on:** P3

**Problem:** Explore empty state is a large void — feels unfinished, example chips unstyled.

**Deliverables:**
1. Constrain empty-state content to `max-width: 480px`, centered
2. Title "Begin Exploring" in `--rl-fs-lg`, weight 600
3. Subtitle text in `--rl-text-muted`, `--rl-fs-base`
4. Example ref chips styled as mini-cards: `--rl-bg-card`, `--rl-border`, `--rl-radius-md`, padding `--rl-space-2 --rl-space-3`
5. Add subtle icon/glyph above title (decorative, using Unicode or inline SVG)
6. Recent refs section clearly separated with label

**AC:**
- Empty state feels designed; examples look like deliberate cards
- No distracting noise; contrast preserved
- Content centered with max-width constraint
- Responsive at 390px (chips wrap naturally)

**MCP:** Screenshot Explore empty at 1280+390; assert empty container has max-width style

---

### P7 — Motion Micro-Polish (optional)
**Priority:** LOW
**Points:** 1
**Depends on:** P2

**Problem:** Interactions feel static — no transition feedback on hover/focus.

**Deliverables:**
1. Nav links: `transition: background-color var(--rl-transition-fast), border-color var(--rl-transition-fast)`
2. Cards/chips: `transition: background-color var(--rl-transition-fast), box-shadow var(--rl-transition-fast)`
3. Chip hover: slight `box-shadow` elevation
4. Respect `prefers-reduced-motion: reduce` — set `--rl-transition-fast: 0ms` and `--rl-transition-normal: 0ms`
5. Add `@media (prefers-reduced-motion: reduce)` override in CSS

**AC:**
- Transitions subtle and consistent (120-180ms)
- No jitter or layout shift during transitions
- `prefers-reduced-motion` zeroes out transition durations

**MCP:** Hover a chip; verify transition property set; verify reduced-motion media query exists

---

## Sprint Summary

| Story | Points | Depends | Status |
|---|---|---|---|
| P1 Tokens | 3 | Baselines | Pending |
| P2 Surfaces | 3 | P1 | Pending |
| P3 Typography | 2 | P1 | Pending |
| P4 Color | 2 | P1 | Pending |
| P5 Nav | 3 | P2, P4 | Pending |
| P6 Empty | 2 | P3 | Pending |
| P7 Motion | 1 | P2 | Optional |
| **Total** | **16** | | |

## Execution Order
1. P1 (foundation for everything)
2. P2 + P3 + P4 (can be implemented sequentially, all depend only on P1)
3. P5 (depends on P2 + P4)
4. P6 (depends on P3)
5. P7 (optional, depends on P2)
6. RELEASE lane

## Definition of Done (per story)
- [ ] MCP "before" screenshots (>=2)
- [ ] Implementation complete
- [ ] `cd gui && npx vitest run` passes
- [ ] `cd gui && npx tsc --noEmit` passes
- [ ] MCP "after" screenshots (>=2) + >=3 DOM assertions
- [ ] `_bmad-output/ux-changelog.md` entry added

## Sprint End
- Full BASELINE-AFTER captures
- RELEASE evidence pack with MANIFEST
- Before/after comparison screenshots in release directory
