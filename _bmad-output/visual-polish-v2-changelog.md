# Visual Polish v2 — Changelog

## STORY P8 — Background Depth System

**What changed**:
- `gui/index.html`: Added two layered radial gradients to `body`:
  - Bottom-center: warm ember glow (accent red, 13% opacity, ellipse 90%x50%)
  - Top-right: cool blue tint (primary blue, 7% opacity, ellipse 60%x50%)
- `gui/index.html`: Added new tokens: `--rl-shadow-glow`, `--rl-lh-tight/normal/relaxed`
- `gui/index.html`: Increased `--rl-shadow-md` and `--rl-shadow-lg` opacity for dark theme visibility
- `gui/src/App.tsx`: Removed `backgroundColor: "var(--rl-bg-app)"` from root div so body gradient shows through
- `gui/index.html`: Added `background-attachment: fixed; min-height: 100vh` to body

**Puppeteer assertions**:
- `getComputedStyle(document.body).backgroundImage` contains `radial-gradient` (PASS)
- Gradient visible in bottom region of viewport (warm tone) and top-right (cool tone)

**Tests**: 334 pass, 0 type errors

---

## STORY P9 — Surface & Border Hierarchy

**What changed**:
- `gui/index.html`: Added `--rl-border-subtle: rgba(255,255,255,0.04)` token
- `gui/index.html`: Increased `--rl-shadow-md` spread and added `--rl-shadow-glow`
- `Dashboard.tsx`: All 6 status cards + API info -> `shadow-md` + border + border-top subtle highlight
- `Settings.tsx`: All 6 sections -> `shadow-md` + border + subtle highlight
- `Sources.tsx`: `sourceCardStyle` -> shadow-md + border
- `Jobs.tsx`: Job list cards -> shadow-sm + border
- `ExportView.tsx`: `sectionStyle` -> shadow-md + border
- `theme.ts`: `commonStyles.card` -> shadow-md + border-top subtle

**Puppeteer assertions**:
- Settings section `boxShadow` = `rgba(0,0,0,0.55) 0px 4px 16px` (PASS)
- Cards visually float above canvas in screenshots

**Tests**: 334 pass, 0 type errors

---

## STORY P10 — Typography Rhythm Upgrade

**What changed**:
- `gui/index.html`: Added global typography rules for `h1`, `h2`, `h3`, and `p/span/div`
  - h1: `--rl-fs-xl`, weight 700, `--rl-lh-tight`, letter-spacing -0.01em
  - h2: `--rl-fs-md`, weight 600, `--rl-lh-tight`, letter-spacing -0.005em
  - h3: `--rl-fs-base`, weight 600, `--rl-lh-tight`
  - p/span/div: `--rl-lh-normal`
- `Dashboard.tsx`, `Jobs.tsx`, `Settings.tsx`: Simplified h1 elements (rely on global rules)

**Puppeteer assertions**: h1 computed fontSize=24px, fontWeight=700 (PASS)

**Tests**: 334 pass, 0 type errors

---

## STORY P11 — Sidebar Designed Pass

**What changed**:
- `gui/src/App.tsx`: Enhanced sidebar navigation:
  - `navLinkStyle`: padding 8->9px, `fontWeight: 500`
  - `navLinkActiveStyle`: `fontWeight: 600`, inner glow boxShadow
  - `sidebarSectionStyle` constant (xs uppercase, 0.08em letter-spacing)
  - Sidebar nav: `borderRight: "1px solid var(--rl-border)"`
  - Section headers: top border separators with spacing
  - Status footer: semi-transparent bg with border outline
  - Mobile sidebar: `borderRight: "none"` for overlay

**Puppeteer assertions**: Sidebar has borderRight (PASS)

**Tests**: 334 pass, 0 type errors

---

## STORY P12 — Dashboard Composition

**What changed**:
- `gui/src/screens/Dashboard.tsx`: Major layout update:
  - Added `dashCardStyle` constant, imports for `useNavigate`, `selectJobs`, `RECENT_REFS_KEY`
  - Removed redundant "API Information" block
  - Added 3 new content blocks in 2-column grid:
    1. **Continue Studying** — recent refs or empty state with Explore link
    2. **System Overview** — API version, capabilities, health, heartbeat
    3. **Recent Activity** (full-width) — last 4 jobs with status chips

**Puppeteer assertions**: All 3 sections present (PASS), 9 elevated cards (PASS)

**Tests**: 334 pass, 0 type errors

---

## STORY P13 — Button & Chip Cohesion

**What changed**:
- `gui/index.html`: Added `:focus-visible` outline rule (2px solid primary, offset 2px) and button base reset (inherit font, radius, transitions)
- Replaced all `#4a4a6a` borders -> `var(--rl-border-strong)` across Settings, Jobs, JobDetail, LogViewer (7 instances)
- `Settings.tsx`: Converted 2 buttons from solid dim bg to ghost pattern (transparent + border)

**Puppeteer assertions**: focus-visible rule present (PASS), zero `#4a4a6a` remaining (PASS)

**Tests**: 334 pass, 0 type errors

---

## Sprint Summary

| Story | Files Changed | Key Metric |
|-------|--------------|------------|
| P8 Background Depth | 2 | Body gradient visible |
| P9 Surface Hierarchy | 7 | shadow-md on all cards |
| P10 Typography | 4 | Global h1/h2/h3 rules |
| P11 Sidebar | 1 | Border + active glow |
| P12 Dashboard | 1 | 3 new content blocks |
| P13 Buttons | 5 | 0 hardcoded borders, focus rings |

**Final**: 334 tests passing, 0 TypeScript errors, 0 hardcoded `#4a4a6a` borders
