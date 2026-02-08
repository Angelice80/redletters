# UX Changelog — Explore Screen

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
