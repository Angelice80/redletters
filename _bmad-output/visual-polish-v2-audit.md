# Visual Polish v2 — Audit Report

## Baseline CSS Custom Properties

| Variable | Value | Notes |
|----------|-------|-------|
| `--rl-bg-app` | `#12121f` | Darkest — app shell |
| `--rl-bg-panel` | `#1a1a2e` | Sidebar/header |
| `--rl-bg-card` | `#242440` | Cards/elevated |
| `--rl-bg-hover` | `#2d2d50` | Hover state |
| `--rl-border` | `#2f2f4a` | Light border |
| `--rl-border-strong` | `#3d3d5c` | Strong border |
| `--rl-text` | `#e8e8f0` | Primary text |
| `--rl-text-muted` | `#9ca3af` | Muted text |
| `--rl-text-dim` | `#6b7280` | Dim/disabled text |
| `--rl-accent` | `#d4513b` | Ember red brand |
| body.background | `rgb(18,18,31)` flat solid | **No gradient** |

## 10 Flatness Drivers

1. **Flat solid background** — `body` is a single `#12121f`. No gradient, radial glow, or texture. The app shell looks like a flat rectangle with no environmental depth.

2. **Same-gray-everywhere cards** — Dashboard cards, settings sections, export form, and job list items all use `--rl-bg-card` (`#242440`) with identical `1px solid --rl-border-strong` borders. Nothing separates "hero" content from secondary content.

3. **No shadow hierarchy** — Despite having `--rl-shadow-sm/md/lg` tokens defined, cards and panels show no visible box-shadow in the baseline. All surfaces sit at the same visual depth.

4. **Sidebar blends with shell** — The sidebar (`--rl-bg-panel` = `#1a1a2e`) is only 8 lightness units above the app background (`#12121f`). The left edge has no visible divider. The sidebar "exists" but doesn't feel like a designed surface.

5. **Section headers are invisible** — "STUDY", "DATA", "SYSTEM" in the sidebar are dim (`--rl-text-dim` = `#6b7280`) uppercase labels at 11px. They function as labels but read as noise — no vertical spacing rhythm separates them from nav items.

6. **Dashboard is 60% dead space** — Below the 6 status cards and API info block, the remaining ~400px of the viewport is empty `#12121f`. The screen feels abandoned after the fold.

7. **Typography has no rhythm** — Page titles ("Dashboard", "Settings") and card labels ("Version", "Mode") use similar size/weight. There's no clear visual hierarchy: title > section header > label > body. Line-heights are default.

8. **Brand motif is a single word** — "Red Letters" in the sidebar is the only use of `--rl-accent` as a brand element. The app has no visual "signature" — no subtle accent line, no glow, nothing that says "this is Red Letters."

9. **Buttons are visually same-weight** — "Reconnect" (primary blue), "Update Token" (secondary gray), "Check Gates & Continue" (blue), "Explore Passage" (blue) all appear as similar-weight rectangles. No clear primary vs secondary vs ghost distinction.

10. **Chips lack visual cohesion** — Source pack chips ("SPINE", "Installed", "comparative layer", "Not installed") use completely different color systems (red bg, green bg, gray bg, gray outline) without a unifying chip design language.

## Top 5 Screens for Improvement

1. **Dashboard (/)** — Most visible screen. 60% dead space. Cards are uniform. Needs composition + density.
2. **Explore (/explore) empty state** — Large empty center panel with faint AΩ. The hero area could be warmer/more inviting.
3. **Settings (/settings)** — All sections look identical. No visual grouping hierarchy.
4. **Sources (/sources)** — Chip inconsistency most visible here. Cards are stacked but visually flat.
5. **Sidebar (all routes)** — Present on every screen. Small improvements compound across every page.

## If We Change Only 3 Things

1. **Background depth system** — Replace flat `#12121f` body with a subtle radial gradient (center glow) + the existing color. Immediately adds "environment" to every screen. Highest visual ROI for one CSS change.

2. **Surface elevation differentiation** — Give cards visible box-shadows (using existing tokens) and slightly adjust border opacity between elevation levels. Makes cards "float" above the canvas.

3. **Dashboard composition** — Replace the 400px of dead space with 2-3 useful information blocks (recent translations, system health summary). Transforms the most-visited screen from "status dump" to "home base."
