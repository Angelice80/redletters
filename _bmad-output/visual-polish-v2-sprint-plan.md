# Visual Polish v2 — Sprint Plan

## Overview
6 stories targeting the 10 flatness drivers identified in the audit.
All changes are CSS-only or inline-style-only (no new dependencies).

---

## STORY P8 — Background Depth System

**Intent**: Eliminate flat solid background. Add environmental depth to every screen.

**Scope**: `gui/index.html` (`:root` + `body` styles only)

**Changes**:
- Add a subtle radial gradient to `body` background: dark center-bottom glow using `--rl-accent` at very low opacity
- Add a secondary radial glow top-right for asymmetric depth
- Keep `--rl-bg-app` as the base; gradients layer on top

**Acceptance Criteria**:
1. Puppeteer: `getComputedStyle(document.body).backgroundImage` is NOT `"none"` (contains `radial-gradient`)
2. Puppeteer: Screenshot of `/` at 1280x800 shows visible gradient (not flat)
3. All existing CSS vars unchanged; no new vars required

**Risk**: Gradient too subtle = invisible. Too strong = distracting. Target ~5-8% opacity accent glow.

---

## STORY P9 — Surface & Border Hierarchy

**Intent**: Make cards float above canvas. Create 3 clear surface levels.

**Scope**: `gui/index.html` (add new token vars), `gui/src/theme.ts` (optional)

**Changes**:
- Add `--rl-surface-1`, `--rl-surface-2`, `--rl-surface-3` as aliases for panel/card/elevated
- Add `--rl-border-subtle` (lower opacity than `--rl-border`)
- Ensure cards use `box-shadow: var(--rl-shadow-md)` (currently sm or none)
- Increase shadow opacity slightly for dark theme visibility

**Acceptance Criteria**:
1. Puppeteer: Dashboard status card `boxShadow` computed style is NOT `"none"`
2. Puppeteer: Settings section cards have visible shadow (compare shadow-md value)
3. Screenshot of `/settings` shows clear card-over-canvas separation

**Risk**: Shadows on dark backgrounds need higher opacity to be visible. Test at 0.5-0.7 black opacity.

---

## STORY P10 — Typography Rhythm Upgrade

**Intent**: Make headings read as headings. Establish clear size/weight/spacing hierarchy.

**Scope**: `gui/index.html` (add line-height tokens), screen components (Dashboard, Settings, Sources, Export, Jobs)

**Changes**:
- Add `--rl-lh-tight: 1.2`, `--rl-lh-normal: 1.5`, `--rl-lh-relaxed: 1.65`
- Page titles (`h1`): `--rl-fs-xl` (24px), weight 700, `--rl-lh-tight`, `letter-spacing: -0.01em`
- Section headers (card titles): `--rl-fs-md` (16px), weight 600, `--rl-lh-tight`
- Labels (field labels): `--rl-fs-xs` (11px), uppercase, weight 500, `letter-spacing: 0.06em`
- Body text: `--rl-fs-base` (14px), `--rl-lh-normal`

**Acceptance Criteria**:
1. Puppeteer: Page `h1` computed `fontSize` >= 22px, `fontWeight` >= 700
2. Puppeteer: Sidebar section label computed `letterSpacing` matches `0.06em`
3. Screenshot of `/settings` shows clear heading > section > label > body hierarchy

**Risk**: Minimal — additive changes to existing font-size tokens. No layout shifts expected.

---

## STORY P11 — Sidebar "Designed" Pass

**Intent**: Make the sidebar feel intentional. Strengthen active state, hover, section rhythm.

**Scope**: `gui/src/App.tsx` (sidebar section only)

**Changes**:
- Active nav item: Add left accent bar glow (box-shadow inset) + stronger background
- Hover state: Visible background shift to `--rl-bg-hover`
- Section headers: Add top border separator + more vertical spacing (margin-top 16px)
- Sidebar bottom status panel: Subtle top border separator
- Sidebar right edge: Add `1px solid var(--rl-border)` divider

**Acceptance Criteria**:
1. Puppeteer: Active nav link has `borderLeft` containing `--rl-accent` color (already present, verify)
2. Puppeteer: Sidebar `nav` element has `borderRight` style
3. Screenshot of `/explore` shows clear sidebar separation from main content

**Risk**: Must not break mobile sidebar overlay. Test 390px viewport after changes.

---

## STORY P12 — Dashboard Composition (Make it Feel Alive)

**Intent**: Replace 400px of dead space with useful content blocks.

**Scope**: `gui/src/screens/Dashboard.tsx`, `gui/src/store.ts` (read recent refs from localStorage)

**Changes**:
Add 3 info blocks below existing status cards:
1. **"Continue Studying"** — Show last 3-5 recent scripture refs from localStorage (`RECENT_REFS_KEY`). Links to `/explore?ref=X`.
2. **"System Overview"** — Compact summary: data root path, source count, spine status (read from engine status).
3. **"Recent Activity"** — Show last 3 jobs with status chips. Link to `/jobs`.

**Acceptance Criteria**:
1. Puppeteer: Dashboard has >= 3 `section` or card-like containers below status grid
2. Puppeteer: "Continue Studying" section exists (text content check)
3. Screenshot of `/` at 1280x800 shows content filling previously empty space

**Risk**: Needs to handle empty state gracefully (no recent refs, no jobs). Show helpful empty text, not blank cards.

---

## STORY P13 — Button & Chip Cohesion

**Intent**: Make primary actions unmistakable. Unify chip design language.

**Scope**: `gui/index.html` (button/chip token additions), `gui/src/theme.ts` (commonStyles), component-level updates

**Changes**:
- Primary buttons: Increase padding, add subtle gradient, stronger shadow
- Secondary buttons: Clear outline style (border + transparent bg)
- Ghost buttons: No border, just text + hover bg
- Chips: Define a consistent chip style (small radius, 1px border, muted bg) for all status/type chips
- Focus rings: `2px solid var(--rl-accent)` with `2px offset` (visible on dark bg)

**Acceptance Criteria**:
1. Puppeteer: Primary button ("Translate", "Start Demo Job") has visually distinct background from secondary
2. Puppeteer: Focus ring visible on tabbing to a button (outline-offset computed check)
3. Screenshot of `/sources` shows consistent chip styling across all packs

**Risk**: Many components use chips differently. Need to update Sources, Jobs, and Explore screens. Scope carefully.

---

## Implementation Order

P8 → P9 → P10 → P11 → P12 → P13

P8 and P9 are pure CSS/token changes (fastest, highest visual ROI).
P10-P11 are style prop updates across a few components.
P12 is the largest (new JSX in Dashboard).
P13 touches the most files but each change is small.

## Validation After Each Story

1. `npx vitest run` — all tests pass
2. `npx tsc --noEmit` — zero type errors
3. Puppeteer assertions for that story's ACs
4. Screenshots saved to `AFTER/<viewport>/<route>.png`
5. Entry in `visual-polish-v2-changelog.md`
