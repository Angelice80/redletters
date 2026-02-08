# Sprint 25 Quick Spec: Visual Gate & Repeatable Release Evidence

## Visual Gate Definition

A **Visual Gate** is a set of automated Puppeteer MCP checks that must pass before
any release. Each check produces durable on-disk evidence (screenshots + assertion
results) that a human can review in under 60 seconds.

### What Must Be Proven Visually

| # | Gate Check | Assertion | Evidence |
|---|-----------|-----------|----------|
| 1 | Explore loads | `[data-testid="explore-ready"]` OR toolbar visible | Screenshot |
| 2 | Reference input functional | `[data-testid="ref-input"]` exists and accepts text | Screenshot |
| 3 | Translation executes | Readable result visible after translate/demo | Screenshot |
| 4 | Traceable view works | `[data-testid="view-traceable-btn"]` active after switch | Screenshot |
| 5 | Receipts tab accessible | `[data-testid="receipts-tab"]` content visible | Screenshot |
| 6 | Confidence panel opens | `[data-testid="confidence-detail-panel"]` visible | Screenshot |
| 7 | Compare modal opens | `[data-testid="compare-modal"]` visible | Screenshot |
| 8 | Demo path works | Demo loads John 3:16 successfully | Screenshot |

### MCP Tool Discovery

**Namespace**: `mcp__puppeteer__`
**Available tools** (confirmed):
- `mcp__puppeteer__puppeteer_navigate` — Navigate to URL
- `mcp__puppeteer__puppeteer_screenshot` — Capture screenshot (name, selector, width, height, encoded)
- `mcp__puppeteer__puppeteer_click` — Click element by CSS selector
- `mcp__puppeteer__puppeteer_fill` — Fill input field
- `mcp__puppeteer__puppeteer_select` — Select dropdown option
- `mcp__puppeteer__puppeteer_hover` — Hover element
- `mcp__puppeteer__puppeteer_evaluate` — Execute JS in browser console

### Artifact Layout

```
gui/_mcp_artifacts/
  README.md                         # Explains structure and retention
  latest/                           # Always overwritten on each run
    report.md                       # Human-readable pass/fail
    report.json                     # Machine-readable results
    screenshots/                    # PNGs from latest run
      01-explore-load.png
      02-ref-input.png
      ...
  releases/                         # Immutable evidence packs
    <YYYY-MM-DD_HHMM>_<shortsha>/
      report.md
      report.json
      screenshots/
        ...
  sprint-24/                        # Legacy (existing)
  index.json                        # Index of all runs
```

### Selectors Contract

All gate checks use `[data-testid="..."]` selectors exclusively.
Full list maintained in `gui/docs/visual-gate-selectors.md`.

### Base URL Convention

- Environment variable: `VISUAL_GATE_URL` (default: `http://localhost:1420`)
- Explore route: `${base}/explore`
