# Sprint 24: Explore Screen Enhancement — Quick Spec

## Goal
Transform Explore from a translation form into a real "translation explorer" with alignment, confidence drill-down, purposeful compare, and onboarding.

## Data Availability Audit

| Data Point | Available? | Source | Notes |
|---|---|---|---|
| Greek tokens (surface) | YES | `VerseLedger.tokens[].surface` | Only in traceable mode with ledger |
| Token positions | YES | `TokenLedger.position` | Integer index per verse |
| Lemma | PARTIAL | `TokenLedger.lemma` | Nullable — not all translators provide |
| Morph | PARTIAL | `TokenLedger.morph` | Nullable — same caveat |
| Gloss | YES | `TokenLedger.gloss` | Always present when ledger exists |
| Token-level confidence | YES | `TokenConfidence.{textual,grammatical,lexical,interpretive}` | Per-token scores |
| Explanations/reasons | PARTIAL | `TokenConfidence.explanations: Record<string,string>` | May be empty object |
| Alignment segments | YES | `SegmentLedger.token_range, greek_phrase, english_phrase` | Phrase-level grouping |
| Alignment type | YES | `SegmentLedger.alignment_type` | e.g. "word-for-word" |
| Variants | YES | `TranslateResponse.variants: VariantDisplay[]` | Also via dossier API |
| Composite confidence | YES | `ConfidenceResult.composite` | Passage-level |
| Layer scores | YES | `ConfidenceResult.layers.{textual,grammatical,lexical,interpretive}` | Passage-level |
| Weakest layer | YES | `ConfidenceResult.weakest_layer` | String identifier |

### Key Constraint
All alignment/token data requires `mode: "traceable"` + a translator that produces ledger output. In readable mode or with no ledger, UI must honestly disable features and explain why.

## Stories

### S5 — Greek/Render Alignment Highlight + Token Popover
- Render Greek tokens individually from `VerseLedger.tokens[].surface`
- Click/keyboard-select Greek token → highlight rendering token at same position (and vice versa)
- Use `SegmentLedger` for phrase-level group highlighting
- Popover shows surface/lemma/morph/gloss (reuse TokenReceiptPopover)
- Missing alignment: disable with "Alignment not provided by backend for this result."

### S6 — Confidence Click-Through to Weak Tokens
- Make confidence layer bars clickable
- Show ConfidenceDetailPanel listing tokens sorted by that layer's score (weakest first)
- Show `TokenConfidence.explanations[layer]` if available
- If no explanations: "Token-level reasons not provided by backend."
- If no ledger: "Token data requires Traceable mode."

### S7 — Variants + Compare Purposeful Flow
- Variants tab: Better empty state explaining why 0 variants (source set info)
- Compare button: Opens CompareModal with A/B settings (translator + mode)
- Runs second translation, shows side-by-side
- Missing requirements stated plainly (e.g., "Traceable mode needed for token comparison")

### S8 — Onboarding Demo Path
- "Try a demo" button in empty state loads John 3:16 and auto-translates readable
- One-time nudge appears after demo: "Switch to Traceable to see token mapping"
- Nudge stored in localStorage; does not repeat after dismissal/accept

## Puppeteer MCP Visual Check Plan

### Stable Selectors Strategy
All interactive elements get `data-testid` attributes. No fragile CSS selectors.

### Required testids (minimum):
- `explore-ready` — on workspace container when result is loaded
- `ref-input` — reference text input
- `prev-btn`, `next-btn` — verse nav buttons
- `translate-btn` — main translate button
- `request-mode-select`, `translator-select` — dropdowns
- `view-readable-btn`, `view-traceable-btn` — view toggle
- `greek-token-{i}` — individual Greek tokens in left panel
- `render-token-{i}` — individual rendering tokens in center panel
- `token-popover` — the popover element
- `confidence-composite` — composite score display
- `confidence-layer-{name}` — clickable layer bars
- `confidence-detail-panel` — the drill-down panel
- `variants-tab`, `receipts-tab` — inspector tabs
- `compare-btn`, `compare-modal` — compare feature
- `demo-btn`, `demo-nudge` — onboarding

### Per-Story Interaction Steps

**S5:**
1. Navigate to `http://localhost:1420/explore`
2. Wait for page load
3. Enter reference, translate
4. Click `[data-testid="greek-token-0"]`
5. Assert `[data-testid="render-token-0"]` has highlight
6. Assert `[data-testid="token-popover"]` visible
7. Screenshots: loaded, after-translate, greek-selected, popover

**S6:**
1. After translate, find confidence section
2. Click `[data-testid^="confidence-layer-"]`
3. Assert `[data-testid="confidence-detail-panel"]` visible
4. Assert content (token rows OR "not provided" message)
5. Screenshots: before, panel-open

**S7:**
1. Click `[data-testid="variants-tab"]`
2. Assert variants content or empty state visible
3. Click `[data-testid="compare-btn"]`
4. Assert `[data-testid="compare-modal"]` visible
5. Screenshots: variants, compare-modal, compare-results

**S8:**
1. Clear localStorage
2. Click `[data-testid="demo-btn"]`
3. Assert results visible
4. Assert `[data-testid="demo-nudge"]` visible
5. Click nudge → assert view switches
6. Reload → assert nudge NOT visible
7. Screenshots: demo-loaded, nudge, traceable, reload-no-nudge
