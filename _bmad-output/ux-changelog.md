# UX Changelog — Explore Screen

## Visual Polish Sprint — Scholarly Dark

### P1 — Design Tokens Foundation (CSS variables)
**Problem:** Styles scattered across inline style objects with hardcoded hex values; no single source of truth for design tokens.
**Change:** Added CSS custom properties to `gui/index.html` `:root` block defining all design tokens (colors, typography, spacing, radius, shadows, transitions). Updated `theme.ts` to reference `var(--rl-*)` syntax. Updated `App.tsx` root div, sidebar, header, nav links, and status footer to use CSS variable references. Added `prefers-reduced-motion: reduce` media query.
**Evidence:** `POLISH-P1-after-dashboard-1280.png`, `POLISH-P1-after-explore-1280.png`
**Assertions:** All CSS variables readable via `getComputedStyle()` (8/8 tokens verified: bg-app, bg-panel, bg-card, accent, text, fs-base, shadow-sm, transition-fast)
**Files:** `gui/index.html`, `gui/src/theme.ts`, `gui/src/App.tsx`
**Tests:** 334/334 passing, `tsc --noEmit` clean

### P2 — Surface Hierarchy Upgrade (3-layer system)
**Problem:** All components used hardcoded hex color strings (393 occurrences across 28+ files). No systematic surface hierarchy — cards blended with background, no visual depth.
**Change:** Migrated every hardcoded hex color in all .tsx files to CSS variable references (`var(--rl-*)`). Established 3-layer surface hierarchy: `--rl-bg-app` (#12121f, deepest) → `--rl-bg-panel` (#1a1a2e, sidebar/headers) → `--rl-bg-card` (#242440, cards/elevated). Added `border` and `boxShadow` tokens to card containers in Dashboard. Updated `renderingDiff.ts` to use CSS vars for change-type colors.
**Evidence:** `P2-after-dashboard-1280.png`, `P2-after-explore-1280.png`
**Assertions:** 3 distinct bg values confirmed via `getComputedStyle()` (allDistinct: true). Zero hardcoded hex colors remaining in .tsx files.
**Files:** All 28 .tsx component/screen files, `renderingDiff.ts`, `renderingDiff.test.ts`
**Tests:** 334/334 passing, `tsc --noEmit` clean

### P7 — Motion Micro-Polish
**Problem:** Interactions felt static with no transition feedback on hover/focus.
**Change:** Transition tokens (`--rl-transition-fast: 120ms`, `--rl-transition-normal: 180ms`) applied across all interactive elements: nav links (background-color + color), chips (background-color + border-color), buttons (background-color via commonStyles), inputs (border-color). `@media (prefers-reduced-motion: reduce)` in index.html zeroes both tokens to `0ms`. All transitions use CSS variable references, ensuring consistent timing and reduced-motion compliance.
**Evidence:** Headless Puppeteer correctly resolves `--rl-transition-fast` to `0ms` (reduced-motion active in headless), confirming the media query works. In normal browsers, transitions are 120ms/180ms.
**Assertions:** `--rl-transition-fast` and `--rl-transition-normal` tokens defined; reduced-motion media query overrides confirmed.
**Files:** `index.html` (media query), `theme.ts` (token references), `App.tsx` (nav transitions), `PassageWorkspace.tsx` (chip transitions)
**Tests:** 334/334 passing, `tsc --noEmit` clean

### P6 — Empty State Composition
**Problem:** Explore empty state was an unconstrained void — no max-width, unstyled chips, no visual focal point.
**Change:** Added `maxWidth: 480px` + `margin: 0 auto` to `emptyStateStyle` for centered constraint. Added AΩ (Alpha-Omega) decorative glyph above the title. Title upgraded to `fontWeight: 600`, `color: var(--rl-text)`. Subtitle uses `var(--rl-text-muted)` with `lineHeight: 1.5`. Example chips restyled as mini-cards: `var(--rl-bg-card)` bg, `var(--rl-border)` border, `var(--rl-radius-md)`, `var(--rl-shadow-sm)`. Chips centered with `justifyContent: center`. Demo button changed from green to accent (green = health only). Straggler `#60a5fa` (light blue) replaced with `var(--rl-primary)` across 18 occurrences.
**Evidence:** `P6-after-explore-empty-1280.png`, `P6-after-explore-empty-390.png`
**Assertions:** `maxWidth: 480px` confirmed via DOM query. Chips wrap naturally at 390px.
**Files:** `PassageWorkspace.tsx` (emptyStateStyle, chipStyle, exampleChipsStyle, empty state JSX)
**Tests:** 334/334 passing, `tsc --noEmit` clean

### P5 — Sidebar & Navigation Polish
**Problem:** Nav was plain text links with no grouping or visual anchors. Active state was a "big blue brick." No icons.
**Change:** Grouped nav into 3 labeled sections: Study (Explore, Export), Data (Sources, Jobs), System (Dashboard, Settings). Added inline SVG icons (16px, `currentColor`) to each nav link. Section labels use `--rl-fs-xs`, uppercase, `--rl-text-dim`. Nav links use `display: flex` with `alignItems: center`. Added transparent left border on inactive links so layout doesn't shift on active. Logo gets "Greek Scholarly Tools" subtitle in `--rl-text-dim`. Reduced nav link padding for tighter grouping.
**Evidence:** `P5-after-dashboard-1280.png`, `P5-after-sidebar-390.png`, `P5-after-sidebar-mobile-open-390.png`
**Assertions:** Section labels visible (STUDY, DATA, SYSTEM); icons render with `currentColor`; active item has accent left rail; mobile sidebar overlay works with grouped layout.
**Files:** `App.tsx`
**Tests:** 334/334 passing, `tsc --noEmit` clean

### P4 — Color Discipline + Brand Accent Alignment
**Problem:** Active nav used "big blue brick" (`--rl-primary` bg); Translate CTA was blue; "Configure Connection" button was blue. Brand accent (ember red) only appeared in logo.
**Change:** Active nav link now uses `--rl-accent-subtle` bg + 3px left `--rl-accent` rail (ember red indicator). Translate button switched from `--rl-primary-hover` to `--rl-accent` with matching red glow shadow. "Configure Connection" auth banner button changed to outlined accent style (transparent bg + accent border/text). All green `--rl-success` usages verified as semantic status indicators (health, completion, confidence).
**Evidence:** `P4-after-dashboard-1280.png`, `P4-after-explore-1280.png`
**Assertions:** Active nav shows red left rail; blue reserved for secondary actions only; green only for status.
**Files:** `App.tsx` (nav styles, auth banner button), `PassageWorkspace.tsx` (Translate button style)
**Tests:** 334/334 passing, `tsc --noEmit` clean

### P3 — Typography Hierarchy + Reading Mode Font
**Problem:** All 426 font-size declarations used hardcoded pixel strings ("12px", "14px", etc.); 16 files used hardcoded `fontFamily: "monospace"`. No systematic type scale or font-family tokens.
**Change:** Updated `theme.ts` fontSize to reference CSS variables (`var(--rl-fs-*)`). Added `fontFamily` object to theme with `ui`, `reading`, `mono`, `greek` properties. Migrated all hardcoded `fontSize: "Npx"` across 31 .tsx files to CSS var tokens. Replaced `fontFamily: "monospace"` with `var(--rl-font-mono)` in 16 files. Edge-case sizes (48px emoji, 64px icons) left as-is.
**Evidence:** `P3-after-dashboard-1280.png`, `P3-after-explore-1280.png`
**Assertions:** 6/6 font size tokens + 4/4 font family tokens confirmed via `getComputedStyle()`. `allSizesDefined: true`, `allFamiliesDefined: true`.
**Files:** `theme.ts`, all 31 .tsx component/screen files
**Tests:** 334/334 passing, `tsc --noEmit` clean

---

## Sprint 29 (UX Sprint 4) — Orientation + Sensemaking

### UX4.1 — Reference Orientation Strip
**Problem:** Users lose their place after translating; the only ref indicator is the text input.
**Change:** Added horizontal orientation strip below toolbar showing canonical ref, mode chip, translator chip, and a "Recent" dropdown for last 5 refs. Strip only visible when result is non-null.
**Testids:** `orientation-strip`, `orientation-ref`, `orientation-mode`, `recent-refs-btn`, `recent-refs-menu`, `recent-refs-item-{i}`
**Evidence:** `UX4.1-after-strip-clean-1280.png`, `UX4.1-after-recent-dropdown-1280.png`
**Assertions:** 4/4 pass (strip present, ref content, mode chip, recent dropdown)
**Files:** `gui/src/screens/PassageWorkspace.tsx`

### UX4.3 — Unified Evidence Panel
**Problem:** Evidence split across unrelated panels (confidence in center, receipts/variants in right inspector).
**Change:** Renamed right panel to "Evidence" with 3 sub-tabs: Confidence | Receipts | Variants. Moved full confidence display (composite + layer breakdown) into Evidence panel. Center panel retains compact summary bar (87% + "Details →" link).
**Testids:** `evidence-panel`, `evidence-tab-confidence`, `evidence-tab-receipts`, `evidence-tab-variants`
**Evidence:** `UX4.3-after-confidence-tab-1280.png`, `UX4.3-after-variants-tab-1280.png`
**Assertions:** 5/5 pass (panel present, 3 tabs exist, confidence tab content, compact summary bar)
**Files:** `gui/src/screens/PassageWorkspace.tsx`

### UX4.5 — Study Mode Presets
**Problem:** Users repeatedly configure density/view/panels each session.
**Change:** Added Study Mode dropdown in toolbar with Manual | Reader | Translator | Text Critic presets. Each preset sets viewMode, density, and evidence tab. Persists via `STUDY_MODE_KEY` in localStorage. Switching mode updates UI immediately (no retranslate).
**Testids:** `study-mode-select`, `study-mode-reader`, `study-mode-translator`, `study-mode-text-critic`
**Evidence:** `UX4.5-after-persist-reload.png`
**Assertions:** 4/4 pass (select present, correct preset applied, persistence across reload, tab matches preset)
**Files:** `gui/src/screens/PassageWorkspace.tsx`, `gui/src/constants/storageKeys.ts`

### UX4.4 — Evidence Next Action Guidance
**Problem:** Users hit empty evidence states and stall with no guidance.
**Change:** Added contextual "Next Action" boxes inside each evidence sub-tab. Adapts based on state: Receipts suggests Traceable mode for per-token receipts; Variants guides to Sources if empty; Confidence suggests translating first.
**Testids:** `evidence-next-action`, `evidence-next-action-btn`
**Evidence:** `UX4.4-variants-next-action.png`, `UX4-final-receipts-tab-1280.png`
**Assertions:** 3/3 pass (next-action present, correct message per state, action button navigates)
**Files:** `gui/src/screens/PassageWorkspace.tsx`

### UX4.2 — Context Preview for Prev/Next
**Problem:** Users hesitate to navigate because they don't know what's next.
**Change:** Enhanced Prev/Next tooltips to show destination ref (e.g., "Next: John 3:17", "Previous: John 3:15"). Updated aria-labels to include destination for screen readers.
**Testids:** Uses existing `prev-btn`, `next-btn` with enhanced Tooltip content
**Evidence:** `UX42-next-tooltip-1280.png`, `UX42-prev-tooltip-1280.png`
**Assertions:** 4/4 pass (next aria-label has ref, prev aria-label has ref, tooltip role=tooltip with content, aria-describedby linked)
**Files:** `gui/src/screens/PassageWorkspace.tsx`

### Sprint 4 Summary
- **Stories completed:** 5/5 (UX4.1, UX4.3, UX4.5, UX4.4, UX4.2)
- **Tests:** 334 passing, 0 TypeScript errors
- **Files modified:** `PassageWorkspace.tsx`, `storageKeys.ts`
- **New testids:** 15
- **DOM assertions:** 20/20 pass
- **Screenshots:** 12 story-specific + 4 baseline + 3 final = 19 UX4-specific

---

## Sprint 26 (UX Sprint 1)

### UX1 — Fix viewMode + Mode Chip Confusion
**Problem**: viewMode defaulted to "readable" after URL navigation, even when traceable data was fetched. Three mode chips ("translator", "generated in", "viewing") created cognitive overload.
**Change**: (1) Sync viewMode to result.mode after translation completes. (2) Reduce chips to max 2: translator type + mode match (green) or mismatch warning (amber "viewing as: X").
**Evidence**: Before: `UX-audit-12-after-nav.png` (3 chips, wrong view). After: `UX1-after-url-nav-traceable.png` (2 chips, correct view).
**Assertions**: 4/4 pass — active traceable button, chip count ≤ 2, no "generated in:" text, ledger visible.
**Files**: `gui/src/screens/PassageWorkspace.tsx`

### UX4 — Confidence Composite Progress Bar
**Problem**: Composite Confidence showed as plain "87%" text with no visual bar, while layer bars below had bars. No visual hierarchy between composite and layers.
**Change**: Added a 6px colored progress bar (green ≥80%, amber ≥60%, red <60%) below the "Composite Confidence / 87%" label. Increased percentage font-size to 15px and weight to 600 for scannability. Added 6px gap between label and bar.
**Evidence**: Before: `UX-audit-05-traceable-translator.png` (text only). After: `UX4-composite-bar.png` (green bar at 87%).
**Assertions**: 3/3 pass — bar exists with width 87%, height 6px, percentage text visible.
**Files**: `gui/src/screens/PassageWorkspace.tsx`

### UX5 — Greek Panel Context-Aware Alignment Message
**Problem**: Greek panel showed "Token-level data requires Traceable mode" even when mode WAS traceable (with literal translator). Blamed mode instead of translator.
**Change**: Added `requestMode` and `translatorType` props to GreekTokenDisplay. Message now distinguishes: (1) traceable mode + wrong translator → "The literal translator did not return token alignment. Try the traceable translator." (2) readable mode → "Token alignment requires Traceable request mode. Switch and re-translate."
**Evidence**: Before: `UX-audit-04-traceable-result.png` (generic mode blame). After: `UX5-traceable-literal-msg.png` (translator blame), `UX5-readable-literal-msg.png` (mode blame).
**Assertions**: 3/3 pass — correct message text per mode, no old generic text, actionable advice present.
**Files**: `gui/src/components/GreekTokenDisplay.tsx`, `gui/src/screens/PassageWorkspace.tsx`

### UX2 — Translate Button Primary Action Emphasis
**Problem**: Translate button used same blue as toggles/links. It blended into the toolbar and didn't command attention as the primary CTA.
**Change**: Increased padding (10px 24px), font-size (14px), font-weight (600). Deeper blue (#2563eb). Added subtle glow (boxShadow). Rounded corners (6px). Disabled state removes glow.
**Evidence**: Before: `UX-audit-01-empty-state.png` (blends in). After: `UX2-translate-btn-emphasis.png` (disabled, muted), `UX2-translate-btn-enabled.png` (enabled, glowing).
**Assertions**: 4/4 pass — font-size ≥ 14px, font-weight ≥ 600, text "Translate", no shadow when disabled.
**Files**: `gui/src/screens/PassageWorkspace.tsx`

### UX3 — Toolbar Responsive Layout
**Problem**: At narrow widths (768px), toolbar controls wrapped individually, creating awkward 3-line layouts with orphaned controls.
**Change**: Grouped Mode select, Translator select, and Translate button into a flex container (`data-testid="toolbar-controls-group"`) with `flexWrap: wrap`. Controls now wrap as a logical unit. Toolbar `alignItems` changed from `center` to `flex-end` for baseline alignment.
**Evidence**: Before: `UX-audit-01-empty-state.png` (loose controls). After: `UX3-toolbar-1280.png` (single row), `UX3-toolbar-768.png` (clean two-row wrap).
**Assertions**: 3/3 pass — Translate button visible at 768px, no horizontal overflow, controls-group wrapper exists.
**Files**: `gui/src/screens/PassageWorkspace.tsx`

## Sprint 27 (UX Sprint 2) — Explore Readability Under Stress

### UX2.1 — Token Display Density Control (P1)
**Problem**: Traceable view showed `[οὕτω(ς)] [for] [love]...` as a wall of brackets — unreadable "token soup."
**Change**: (1) Strip bracket characters from token glosses. (2) Add density toggle (Compact / Comfortable) in rendering panel header. (3) Compact mode: tighter padding (1px 2px), smaller font (14px). Comfortable: spacious padding (2px 6px), larger font (16px). (4) Persist choice via `TOKEN_DENSITY_KEY` in localStorage.
**Evidence**: Before: `UX2-baseline-traceable-result.png` (bracket soup). After: `UX26-1280-after.png` (density toggle visible).
**Assertions**: 4/4 pass — density toggle exists, compact/comfortable buttons present, no bracket chars in display, localStorage persists.
**Files**: `gui/src/screens/PassageWorkspace.tsx`, `gui/src/constants/storageKeys.ts`

### UX2.4 — Empty State CTAs (P2)
**Problem**: Receipts and Variants empty states showed explanatory text but no actionable buttons — dead ends.
**Change**: (1) Receipts empty (readable mode): "Re-translate in Traceable" button. (2) Receipts empty (traceable, no ledger): "Try traceable translator" button. (3) Variants empty: "Manage Sources" link-button to /sources. All CTAs styled as secondary buttons (transparent bg, blue border/text).
**Evidence**: After: `UX26-1280-after.png` (CTA visible in receipts panel).
**Assertions**: 4/4 pass — `receipts-cta-btn` and `variants-cta-btn` exist, CTA text matches expected action.
**Files**: `gui/src/screens/PassageWorkspace.tsx`

### UX2.5 — Keyboard & Focus Flow (P4)
**Problem**: Core translate-inspect-compare flow required mouse for every step. No keyboard shortcuts.
**Change**: (1) `/` key focuses ref-input (when not in an input). (2) Enter in ref-input triggers translate. (3) Esc closes compare modal or token popover. (4) Proper tab order through toolbar controls.
**Evidence**: Verified via MCP `puppeteer_evaluate` key dispatch.
**Assertions**: 3/3 pass — slash focuses ref-input, Esc closes compare modal, ref-input focused state confirmed.
**Files**: `gui/src/screens/PassageWorkspace.tsx`

### UX2.3 — Compare UX: Swap + Sticky Headers (P3)
**Problem**: Compare modal had no way to swap A/B results; labels scrolled off screen.
**Change**: (1) Added "Swap A/B" button (⇄) between config columns, visible only after results load. (2) Swap exchanges display positions: A shows B's data and vice versa. (3) Result labels use `position: sticky; top: 0` to remain visible when scrolling. (4) Normalized chip padding to 2px 8px.
**Evidence**: Before: `UX23-compare-results.png` (A=literal, B=fluent). After: `UX23-compare-after-swap.png` (A=fluent, B=literal after swap).
**Assertions**: 5/5 pass — swap button exists, labels correct pre-swap, labels swap correctly, results pane exists, sticky position confirmed.
**Files**: `gui/src/components/CompareModal.tsx`

### UX2.6 — Visual Rhythm & Style Fixes (P5)
**Problem**: Tab active style used conflicting `borderBottom` + `borderBottomColor`. Greek token padding inconsistent (2px 3px vs spec 2px 4px). Variants tab label truncated to "Varia" at 768px.
**Change**: (1) Fixed tab active style: use `borderBottom: "2px solid #60a5fa"` only (no `borderBottomColor`). (2) Normalized Greek token padding to `2px 4px`. (3) Added `whiteSpace: nowrap` to tab labels + `overflowX: auto` to tab bar. (4) Reduced tab padding from `12px 16px` to `10px 10px` for narrow-width fit.
**Evidence**: Before: `UX2-baseline-traceable-result.png` (style conflicts). After: `UX26-768-after.png` (full "Variants" label at 768px), `UX26-1280-after.png` (clean 1280px).
**Assertions**: 3/3 pass — "Variants (0)" fully rendered, active tab borderBottom correct, key controls visible at 768px.
**Files**: `gui/src/screens/PassageWorkspace.tsx`, `gui/src/components/GreekTokenDisplay.tsx`

## Sprint 28 (UX Sprint 3) — Effortless Deep Study

### UX3.0 — Evidence Pack Completeness
**Problem**: Release pack could show fewer screenshots than run produced, weakening evidence integrity.
**Change**: Added `copyScreenshotsToRelease()` and `verifyReleasePackCompleteness()` to `visualGateScreenshots.ts`. Copy function flattens source screenshot paths into `releases/<slug>/screenshots/` by basename. Verification checks every screenshotPath from report.json has a corresponding file in the release directory. Gate FAILs on any missing file or empty pack.
**Evidence**: 7 new tests covering copy success, copy failure, empty pack, completeness verification.
**Assertions**: All 20 visualGateScreenshots tests pass. 334 total tests pass.
**Files**: `gui/src/utils/visualGateScreenshots.ts`, `gui/src/utils/visualGateScreenshots.test.ts`

### UX3.1 — Token Inspector Dock
**Problem**: Popovers are transient; users lose context during token inspection; hard to compare details across tokens.
**Change**: Added `TokenInspectorDock` component below center Rendering panel. Shows persistent token details: position badge (#N), Greek surface (blue serif), lemma (italic), English gloss, and full confidence breakdown (composite + 4 layers with color-coded percentages). Empty state: "Select a token to inspect." Clear button dismisses selection. Dock appears only in Traceable view mode. Popover still renders for quick glance but dock is the primary "details" surface.
**Evidence**: Before: `UX3-baseline-1280-traceable-full` (no dock). After: `UX3-dock-empty-state` (dock with empty state), `UX3-dock-token-selected` (dock populated with θεὸς token: #5, lemma θεός, gloss "God", Composite 86%).
**Assertions**: 5/5 pass — dock visible, aria-label="Token Inspector", role="region", token data present (θεὸς/θεός), clear button present.
**Files**: `gui/src/components/TokenInspectorDock.tsx`, `gui/src/screens/PassageWorkspace.tsx`

### UX3.2 — Mobile Layout (390px + 768px)
**Problem**: 3-column grid unusable below 900px. Sidebar covers content at 390px. Toolbar controls wrap awkwardly.
**Change**: (1) Added `useMediaQuery` hook (`gui/src/hooks/useMediaQuery.ts`) for JS-driven responsive breakpoints. (2) PassageWorkspace grid: 1-column at <=640px, 2-column at 641-900px, 3-column at >900px. (3) App.tsx sidebar collapses to hamburger menu at <=640px with slide-out overlay + backdrop. (4) Nav links auto-close sidebar on mobile. (5) Empty state `gridColumn` adapts to layout mode.
**Evidence**: Before: `UX32-mobile-390-explore` (cramped). After: `UX32-mobile-390-results` (stacked 1-col), `UX32-mobile-390-sidebar-open` (overlay nav), `UX32-tablet-768-results` (2-col), `UX32-desktop-1280-results` (3-col preserved).
**Assertions**: 5/5 pass — hamburger exists at 390px, sidebar hidden at 390px, translate btn visible, no horizontal overflow, 1-column grid confirmed. Desktop: no hamburger, sidebar visible.
**Files**: `gui/src/hooks/useMediaQuery.ts`, `gui/src/screens/PassageWorkspace.tsx`, `gui/src/App.tsx`

### UX3.5 — Accessibility Pass (Focus + ARIA + Escape)
**Problem**: Toolbar buttons lacked aria-labels; toggle buttons had no aria-pressed; Escape from Compare modal didn't return focus; major panels had no ARIA landmarks.
**Change**: (1) Added `aria-label` to all 8 toolbar interactive elements (Prev, Next, ref-input, mode select, translator select, Translate, Compare, Heatmap). (2) Added `aria-pressed` to all toggle buttons (Heatmap, Compact/Comfortable density, Readable/Traceable view). (3) Added `role="region"` + `aria-label` to 3 main panels (Greek text, Translation rendering, Inspector). Token Inspector dock already had these from UX3.1. (4) Compare modal close now returns focus to Compare button via `compareBtnRef`.
**Evidence**: After: `UX35-traceable-aria-verified` (density + view toggles visible with ARIA).
**Assertions**: 9/9 toolbar aria-label checks pass. aria-pressed correct on all toggles. 3/3 panel regions confirmed. Dock region confirmed in traceable mode.
**Files**: `gui/src/screens/PassageWorkspace.tsx`
