# Visual Polish Sprint — Release Report

**Sprint**: Visual Polish (Scholarly Dark)
**Date**: 2026-02-08
**Status**: COMPLETE
**Tests**: 334/334 passing | TSC: 0 errors

---

## Summary

Upgraded the Red Letters GUI from "functional admin tool" to "premium scholarly app" through 7 stories (P1-P7) covering design tokens, surface hierarchy, typography, color discipline, sidebar navigation, empty states, and motion.

**Scope**: GUI only. No backend/engine changes. No new UX flows or components (except sidebar section labels + icons). All changes are visual/presentational.

---

## Stories Completed (7/7)

| Story | Title | Files Changed | Key Metric |
|-------|-------|--------------|------------|
| P1 | Design Tokens Foundation | 3 (index.html, theme.ts, App.tsx) | 8/8 CSS vars verified |
| P2 | Surface Hierarchy (3-layer) | 30+ .tsx files | 393 hardcoded hex -> CSS vars |
| P3 | Typography Hierarchy | 31 .tsx files + theme.ts | 426 fontSize + 16 fontFamily migrated |
| P4 | Color Discipline + Brand Accent | App.tsx, PassageWorkspace.tsx | Ember red accent CTA + nav rail |
| P5 | Sidebar & Navigation Polish | App.tsx | 3 sections, 6 icons, section labels |
| P6 | Empty State Composition | PassageWorkspace.tsx | 480px constraint, AO glyph, mini-card chips |
| P7 | Motion Micro-Polish | Verified existing | reduced-motion compliance confirmed |

---

## Design Token Architecture

### CSS Custom Properties (`:root` in index.html)

**Surfaces** (3-layer depth):
- `--rl-bg-app`: #12121f (deepest)
- `--rl-bg-panel`: #1a1a2e (sidebar, headers)
- `--rl-bg-card`: #242440 (cards, elevated)

**Brand Colors**:
- `--rl-primary`: #3b82f6 (info/links)
- `--rl-accent`: #d4513b (ember red CTA)
- `--rl-accent-subtle`: rgba(212, 81, 59, 0.12)
- `--rl-success`: #22c55e (health/status only)
- `--rl-warning`: #eab308
- `--rl-error`: #ef4444

**Typography** (6 sizes + 4 families):
- `--rl-fs-xs` through `--rl-fs-xl`: 11px to 24px
- `--rl-font-ui`, `--rl-font-reading`, `--rl-font-mono`, `--rl-font-greek`

**Motion** (reduced-motion aware):
- `--rl-transition-fast`: 120ms (0ms in prefers-reduced-motion)
- `--rl-transition-normal`: 180ms (0ms in prefers-reduced-motion)

---

## Visual Evidence (Puppeteer MCP Screenshots)

### BASELINE-AFTER (final state, all viewports)
| Screen | 1280x800 | 768x900 | 390x844 |
|--------|----------|---------|---------|
| Dashboard | S1-dashboard-1280 | S1-dashboard-768 | S1-dashboard-390 |
| Explore | S2-explore-1280 | S2-explore-768 | S2-explore-390 |

### Per-Story Evidence
- P1: POLISH-P1-after-dashboard-1280, POLISH-P1-after-explore-1280
- P2: P2-after-dashboard-1280, P2-after-explore-1280
- P3: P3-after-dashboard-1280, P3-after-explore-1280
- P4: P4-after-dashboard-1280, P4-after-explore-1280
- P5: P5-after-dashboard-1280, P5-after-sidebar-390, P5-after-sidebar-mobile-open-390
- P6: P6-after-explore-empty-1280, P6-after-explore-empty-390
- P7: Verified via computed style assertions (headless resolves transition vars to 0ms)

---

## Quality Assertions

| Assertion | Result |
|-----------|--------|
| CSS vars readable (8 core tokens) | PASS |
| 3-layer surface hierarchy (allDistinct) | PASS |
| Font size tokens (6/6 defined) | PASS |
| Font family tokens (4/4 defined) | PASS |
| Active nav: accent left rail | PASS |
| Empty state maxWidth: 480px | PASS |
| Reduced-motion: transitions = 0ms | PASS |
| TSC --noEmit | PASS (0 errors) |
| Vitest | PASS (334/334) |

---

## Remaining Work (Future Sprint)

**Secondary screen token migration** (~124 hardcoded hex remaining):
- `Sources.tsx`: Error/info alert containers, blue accent links
- `Gate.tsx`: Warning/error/info containers, status colors
- `Translate.tsx`: Blue accent text
- `App.tsx`: Connection error/warning banners

These are mostly semantic status colors (error reds, warning ambers) in alert containers on secondary screens. The core Explore workspace, Dashboard, and all shared components are fully tokenized.

**Potential P8 candidates**:
- Migrate remaining secondary screen colors to CSS vars
- Add `--rl-error-bg`, `--rl-warning-bg`, `--rl-info-bg` surface tokens for alert containers
- Typography audit on secondary screens (35 hardcoded fontSize remaining)

---

## Files Modified (Primary)

| File | Changes |
|------|---------|
| `gui/index.html` | CSS custom properties, reduced-motion media query |
| `gui/src/theme.ts` | Token references (fontSize, fontFamily, shadows, transitions) |
| `gui/src/App.tsx` | Sidebar sections + icons, nav styles, accent colors, responsive |
| `gui/src/screens/PassageWorkspace.tsx` | Tokens, empty state, accent CTA, chips |
| `gui/src/screens/Dashboard.tsx` | Card surfaces, borders, shadows |
| `gui/src/utils/renderingDiff.ts` | CSS var colors for change types |
| `gui/src/utils/renderingDiff.test.ts` | Updated expectations |
| `gui/src/components/*.tsx` | All: hex -> CSS vars, px -> CSS vars |
| `gui/src/screens/*.tsx` | All primary: hex -> CSS vars, px -> CSS vars |
| `_bmad-output/ux-changelog.md` | 7 story entries added |
