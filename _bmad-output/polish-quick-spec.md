# Visual Polish Sprint — Quick Spec

## Visual Direction: Scholarly Dark

A refined, scholarly dark theme that feels intentional and premium — not "admin dashboard." The existing `#1a1a2e` / `#2d2d44` palette is retained but gains depth through a 3-layer surface system, tighter color discipline, and typographic hierarchy. The brand color ("Red Letters" = ember red) is elevated from logo-only to a deliberate accent across nav and primary CTA.

## Design Tokens Plan

### Colors (CSS custom properties on `:root`)

| Token | Value | Purpose |
|---|---|---|
| `--rl-bg-app` | `#12121f` | Deepest background (app shell) |
| `--rl-bg-panel` | `#1a1a2e` | Panel/sidebar surface |
| `--rl-bg-card` | `#242440` | Cards, controls, elevated surface |
| `--rl-bg-hover` | `#2d2d50` | Hover on cards/controls |
| `--rl-border` | `#2f2f4a` | Subtle panel/card borders |
| `--rl-border-strong` | `#3d3d5c` | Input borders, dividers |
| `--rl-text` | `#e8e8f0` | Primary text |
| `--rl-text-muted` | `#9ca3af` | Secondary/muted text |
| `--rl-text-dim` | `#6b7280` | Disabled/tertiary text |
| `--rl-accent` | `#d4513b` | Brand accent (ember red) |
| `--rl-accent-hover` | `#c0402e` | Accent hover |
| `--rl-accent-subtle` | `rgba(212,81,59,0.12)` | Accent backgrounds |
| `--rl-primary` | `#3b82f6` | Blue action (secondary CTA) |
| `--rl-primary-hover` | `#2563eb` | Blue hover |
| `--rl-success` | `#22c55e` | Connected/health only |
| `--rl-warning` | `#f59e0b` | Degraded/caution |
| `--rl-error` | `#ef4444` | Error states |

### Typography

| Token | Value | Usage |
|---|---|---|
| `--rl-font-ui` | `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif` | UI chrome |
| `--rl-font-reading` | `'Georgia', 'Cambria', 'Times New Roman', serif` | Readable rendering |
| `--rl-font-mono` | `'SF Mono', 'Fira Code', 'Consolas', monospace` | Code, tokens |
| `--rl-font-greek` | `'SBL Greek', 'Cardo', 'Gentium Plus', serif` | Greek text |
| `--rl-fs-xs` | `0.6875rem` (11px) | Micro labels |
| `--rl-fs-sm` | `0.75rem` (12px) | Secondary text |
| `--rl-fs-base` | `0.875rem` (14px) | Standard UI |
| `--rl-fs-md` | `1rem` (16px) | Emphasized text |
| `--rl-fs-lg` | `1.25rem` (20px) | Section headings |
| `--rl-fs-xl` | `1.5rem` (24px) | Page titles |

### Radius

| Token | Value |
|---|---|
| `--rl-radius-sm` | `4px` |
| `--rl-radius-md` | `6px` |
| `--rl-radius-lg` | `8px` |
| `--rl-radius-xl` | `12px` |

### Spacing

| Token | Value |
|---|---|
| `--rl-space-1` | `4px` |
| `--rl-space-2` | `8px` |
| `--rl-space-3` | `12px` |
| `--rl-space-4` | `16px` |
| `--rl-space-5` | `20px` |
| `--rl-space-6` | `24px` |
| `--rl-space-8` | `32px` |

### Shadows

| Token | Value |
|---|---|
| `--rl-shadow-sm` | `0 1px 3px rgba(0,0,0,0.4)` |
| `--rl-shadow-md` | `0 4px 12px rgba(0,0,0,0.5)` |
| `--rl-shadow-lg` | `0 8px 24px rgba(0,0,0,0.6)` |

### Transitions

| Token | Value |
|---|---|
| `--rl-transition-fast` | `120ms ease` |
| `--rl-transition-normal` | `180ms ease` |

## Component Coverage

| Component | Token integration | Surface layer |
|---|---|---|
| App shell (root div) | `--rl-bg-app` | Layer 0 |
| Sidebar nav | `--rl-bg-panel` | Layer 1 |
| Header bar | `--rl-bg-panel` | Layer 1 |
| Panel containers (Greek/Rendering/Evidence) | `--rl-bg-panel` + `--rl-border` | Layer 1 |
| Cards (dashboard stats, empty state chips) | `--rl-bg-card` + `--rl-border` | Layer 2 |
| Inputs, selects | `--rl-bg-card` + `--rl-border-strong` | Layer 2 |
| Toolbar | `--rl-bg-panel` | Layer 1 |
| Orientation strip | `--rl-bg-card` | Layer 2 |
| Token Inspector Dock | `--rl-bg-card` | Layer 2 |
| Tooltip | `--rl-bg-card` + `--rl-shadow-md` | Layer 2 |
| Modal overlay | `rgba(0,0,0,0.6)` | Overlay |
| Modal content | `--rl-bg-panel` + `--rl-shadow-lg` | Layer 1 |
| Nav link (active) | `--rl-accent-subtle` + left `--rl-accent` indicator | Layer 1 |
| Primary CTA (Translate) | `--rl-accent` background | N/A |
| Empty state container | Centered, `max-width: 480px` | Layer 1 |

## Visual Acceptance Criteria

1. **Surface hierarchy visible**: A screenshot at 1280px shows 3 distinct brightness levels (app < panel < card)
2. **Brand accent present**: Active nav link has ember-red left indicator; Translate button uses `--rl-accent`
3. **Typography differentiated**: Page title (e.g., "Dashboard") uses `--rl-fs-xl`; section labels use `--rl-fs-xs` uppercase; body uses `--rl-fs-base`
4. **Sidebar grouped**: Nav items organized into labeled sections; active item has left rail + subtle bg, not "big blue brick"
5. **Empty state constrained**: Explore empty state has `max-width` on content wrapper; example chips styled as cards
6. **Green = health only**: Only connection status dot/badge uses green; no green elsewhere
7. **Contrast preserved**: All text/bg combinations meet WCAG AA (4.5:1 for normal text)
8. **Focus rings intact**: Tab-navigating through sidebar and toolbar shows visible focus indicators
9. **No visual regressions at 390px**: Mobile layout still works (hamburger, 1-col grid, sidebar overlay)
10. **CSS variables used**: `document.documentElement.style.getPropertyValue('--rl-bg-app')` returns expected value

## MCP Baseline Capture Plan

### States
| ID | State | URL/Action |
|---|---|---|
| S1 | Dashboard | Navigate to `/` |
| S2 | Explore Empty | Navigate to `/explore` |
| S3 | Explore Traceable Result + Dock | Translate John 3:16 in traceable mode, select token |
| S4 | Evidence Panel | Evidence panel, Receipts then Variants tabs |
| S5 | Compare Modal | Open compare modal |

### Viewports
- Desktop: 1280x800
- Tablet: 768x900
- Mobile: 390x844

### Naming Convention
- Before: `POLISH-BASELINE-BEFORE-<state>-<viewport>.png`
- After: `POLISH-BASELINE-AFTER-<state>-<viewport>.png`
- Story-specific: `POLISH-P<N>-before-<desc>-<viewport>.png` / `POLISH-P<N>-after-<desc>-<viewport>.png`

### Capture Timing
- **Before all changes**: S1+S2 at all 3 viewports (6 screenshots) -- DONE
- **After P1 (tokens)**: Re-capture S1+S2 to verify no regression
- **After P2 (surfaces)**: Re-capture S1+S2 to verify hierarchy visible
- **After P4 (color)**: Re-capture S1+S2 to verify accent placement
- **After P5 (nav)**: Re-capture sidebar at all 3 viewports
- **After P6 (empty)**: Re-capture S2 at 1280+390
- **Sprint end**: Full BASELINE-AFTER capture of S1+S2 at all viewports (6+ screenshots)
