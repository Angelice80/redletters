# UX Sprint 4 Plan: Orientation + Sensemaking

**Sprint Duration:** 1 session | **Stories:** 5 (UX4.6 dropped - low ROI)
**Priority Method:** Impact x Frequency x Confidence

---

## Story Priority Matrix

| Story | Impact | Freq | Confidence | Score | Order |
|-------|--------|------|-----------|-------|-------|
| UX4.1 Orientation Strip | 9 | 10 | 9 | 810 | 1 |
| UX4.3 Unified Evidence Panel | 8 | 8 | 8 | 512 | 2 |
| UX4.5 Study Mode Presets | 8 | 9 | 7 | 504 | 3 |
| UX4.4 Evidence Next Action | 7 | 7 | 8 | 392 | 4 |
| UX4.2 Context Preview | 6 | 6 | 7 | 252 | 5 |

**Rationale:**
- UX4.1 scored highest because orientation is needed on *every* translate (freq=10) and directly addresses the #1 user confusion point.
- UX4.3 before UX4.4 because the unified panel is the container that Next Action lives inside.
- UX4.5 before UX4.2 because presets reduce setup friction on every session start (higher frequency).
- UX4.2 lowest because it requires translation data to be useful (conditional value).

---

## Story Definitions

### UX4.1 - Reference Orientation Strip (Score: 810)
**Problem:** Users lose their place after translating, especially with ranges.
**Deliver:**
- Horizontal strip below toolbar, above workspace panels
- Shows: canonical ref (e.g., "John 3:16-18"), mode badge, translator badge
- "Recent" button opens dropdown of last 5 refs (from RECENT_REFS_KEY)
- Selecting recent ref updates input + URL
- Strip only visible when `result` is non-null
**Files:** `PassageWorkspace.tsx`
**Testids:** `orientation-strip`, `orientation-ref`, `orientation-mode`, `recent-refs-btn`, `recent-refs-menu`, `recent-refs-item-{i}`
**AC:**
- [ ] After translate, strip shows exact ref and mode
- [ ] Range ref shows "John 3:16-18" (not just first verse)
- [ ] Recent dropdown shows recent refs; selecting updates ref-input
- [ ] Keyboard accessible (Tab to Recent button, Enter to open, Arrow to navigate)

### UX4.3 - Unified Evidence Panel (Score: 512)
**Problem:** Evidence is split across center (confidence) and right (receipts/variants) panels with no unifying concept.
**Deliver:**
- Rename right panel from "Inspector" to "Evidence"
- Add 3 sub-tabs: Confidence | Receipts | Variants
- Move confidence display into Evidence panel as the Confidence sub-tab content
- Keep existing components (LedgerList, DossierPanel); recompose only
- Shared empty state language
**Files:** `PassageWorkspace.tsx`
**Testids:** `evidence-panel`, `evidence-tab-confidence`, `evidence-tab-receipts`, `evidence-tab-variants`
**AC:**
- [ ] Evidence panel accessible in one click
- [ ] Sub-tabs switch without layout jump
- [ ] Confidence tab shows composite + layer breakdown (same content as before, moved)
- [ ] Existing receipts and variants content preserved

### UX4.5 - Study Mode Presets (Score: 504)
**Problem:** Users repeatedly configure density/view/panels each session.
**Deliver:**
- Dropdown selector in toolbar area: Reader | Translator | Text Critic
- **Reader:** Readable view, Comfortable density, Evidence tab = Confidence
- **Translator:** Traceable view, Comfortable density, Evidence tab = Receipts
- **Text Critic:** Traceable view, Compact density, Evidence tab = Variants
- Persist via new `STUDY_MODE_KEY` in storageKeys.ts
- Switching mode updates UI state immediately (no retranslate)
**Files:** `PassageWorkspace.tsx`, `storageKeys.ts`
**Testids:** `study-mode-select`, `study-mode-reader`, `study-mode-translator`, `study-mode-text-critic`
**AC:**
- [ ] Modes change visible UI state deterministically
- [ ] Persistence works across reload
- [ ] Mode selector visible in toolbar

### UX4.4 - Evidence Next Action Guidance (Score: 392)
**Problem:** Users hit empty evidence states and stall.
**Deliver:**
- Small "Next Action" box at top of Evidence panel (inside the active sub-tab)
- Adapts based on current state:
  - Receipts empty + mode=readable: "Re-translate in Traceable for per-token receipts"
  - Variants empty + sources exist: "No variants at this reference"
  - Variants empty + no sources: "Install source packs for variant data"
- Only one primary action at a time, unobtrusive
**Files:** `PassageWorkspace.tsx`
**Testids:** `evidence-next-action`, `evidence-next-action-btn`
**AC:**
- [ ] Box present but unobtrusive
- [ ] Actions truthful based on current state
- [ ] Primary action button functional

### UX4.2 - Context Preview for Prev/Next (Score: 252)
**Problem:** Users hesitate to navigate because they don't know what's next.
**Deliver:**
- Hover/focus Prev/Next shows enhanced tooltip with preview:
  - "Previous: John 3:15" (or "Next: John 3:17")
  - If result exists and is single verse, show first ~60 chars of translation text as preview hint
- Honest fallback: "Preview requires a translation result"
**Files:** `PassageWorkspace.tsx`
**Testids:** `nav-preview`, `prev-preview`, `next-preview`
**AC:**
- [ ] In translated state, hover Prev/Next shows destination ref
- [ ] Preview never blocks clicks
- [ ] Keyboard focus triggers preview (via existing Tooltip)

---

## Implementation Order & Dependencies

```
UX4.1 (Orientation Strip) ── no deps, pure additive
    │
    ├── UX4.3 (Unified Evidence Panel) ── depends on understanding current right panel
    │       │
    │       ├── UX4.4 (Evidence Next Action) ── lives INSIDE Evidence panel
    │       │
    │       └── UX4.5 (Study Mode Presets) ── sets Evidence tab state
    │
    └── UX4.2 (Context Preview) ── no deps, enhances existing Tooltip
```

**Execution order:** UX4.1 -> UX4.3 -> UX4.5 -> UX4.4 -> UX4.2

---

## Quality Gates (Per Story)

```bash
cd gui && npx vitest run          # All 334+ tests pass
cd gui && npx tsc --noEmit        # Zero TS errors
# MCP: before/after screenshots + 3+ DOM assertions
```

## End of Sprint

- Full RELEASE lane with MANIFEST
- Evidence pack at `gui/_mcp_artifacts/releases/<slug>/`
- Updated `_bmad-output/ux-changelog.md`
