# Visual Gate Selectors Contract

This document is the **source of truth** for all `data-testid` attributes used by the
Visual Gate smoke lane. Components MUST maintain these selectors. Renaming or removing
a selector listed here is a breaking change to the release gate.

## Gate-Critical Selectors

These selectors are directly referenced by the Visual Gate checks.

### Explore Layout & State

| Selector | Component | Description |
|----------|-----------|-------------|
| `explore-ready` | PassageWorkspace | Wrapper div for 3-column result layout |
| `ref-input` | PassageWorkspace | Scripture reference text input |
| `translate-btn` | PassageWorkspace | Main translate action button |

### Navigation

| Selector | Component | Description |
|----------|-----------|-------------|
| `prev-btn` | PassageWorkspace | Previous verse button |
| `next-btn` | PassageWorkspace | Next verse button |

### View Mode

| Selector | Component | Description |
|----------|-----------|-------------|
| `view-readable-btn` | PassageWorkspace | Switch to Readable view |
| `view-traceable-btn` | PassageWorkspace | Switch to Traceable view |

### Inspector Tabs

| Selector | Component | Description |
|----------|-----------|-------------|
| `receipts-tab` | PassageWorkspace | Receipts/ledger tab |
| `variants-tab` | PassageWorkspace | Textual variants tab |

### Confidence

| Selector | Component | Description |
|----------|-----------|-------------|
| `confidence-layer-{name}` | PassageWorkspace | Per-layer score (textual, grammatical, lexical, interpretive) |
| `confidence-detail-panel` | ConfidenceDetailPanel | Layer drill-down panel |

### Compare

| Selector | Component | Description |
|----------|-----------|-------------|
| `compare-btn` | PassageWorkspace | Open compare modal button |
| `compare-modal` | CompareModal | Modal overlay container |
| `compare-run-btn` | CompareModal | Run comparison button |

### Demo / Onboarding

| Selector | Component | Description |
|----------|-----------|-------------|
| `demo-btn` | PassageWorkspace | Try Demo button |
| `demo-nudge` | PassageWorkspace | Post-demo nudge notification |
| `demo-nudge-accept` | PassageWorkspace | Accept nudge (switch to Traceable) |
| `demo-nudge-dismiss` | PassageWorkspace | Dismiss nudge |

### Token Display

| Selector | Component | Description |
|----------|-----------|-------------|
| `greek-token-{i}` | GreekTokenDisplay | Greek source token at position i |
| `render-token-{i}` | PassageWorkspace | Rendered gloss token at position i |
| `token-popover` | PassageWorkspace | Token receipt popover container |

## Non-Gate Selectors (Informational)

These exist in the codebase but are NOT required by the Visual Gate.

| Selector | Component | Description |
|----------|-----------|-------------|
| `request-mode-select` | PassageWorkspace | Mode dropdown |
| `translator-select` | PassageWorkspace | Translator dropdown |
| `heatmap-btn` | PassageWorkspace | Confidence heatmap toggle |
| `confidence-composite` | PassageWorkspace | Composite score display |
| `confidence-token-{i}` | ConfidenceDetailPanel | Token row in detail |
| `no-reasons-msg` | ConfidenceDetailPanel | No explanations message |
| `alignment-disabled-msg` | GreekTokenDisplay | No alignment data message |
| `compare-translator-b` | CompareModal | Translator B selector |
| `compare-mode-b` | CompareModal | Mode B selector |
| `compare-results` | CompareModal | Results pane |
| `connection-badge` | ConnectionBadge | Connection status indicator |
| `export-reference` | ExportView | Export reference input |
| `export-mode` | ExportView | Export mode selector |
| `export-check-gates` | ExportView | Check gates button |
| `export-run` | ExportView | Run export button |

## Rules

1. **Never rename** a gate-critical selector without updating `gui/docs/visual-gate.md`.
2. **Dynamic selectors** use pattern `{base}-{variable}` (e.g., `confidence-layer-textual`).
3. **New components** that are part of a gate check MUST register their selector here before the gate runs.
4. All selectors use the `data-testid` attribute (not `id`, not `class`).
