# MCP Visual Gate Artifacts

This directory stores evidence from Puppeteer MCP visual gate runs.

## Structure

```
_mcp_artifacts/
  README.md              ← You are here
  index.json             ← Index of all runs (appended per run)
  latest/                ← Most recent run (always overwritten)
    report.md            ← Human-readable pass/fail summary
    report.json          ← Machine-readable results
    screenshots/         ← PNG screenshots from the run
  releases/              ← Immutable evidence packs
    YYYY-MM-DD_HHMM_<sha>/
      report.md
      report.json
      screenshots/
  sprint-24/             ← Legacy placeholder
```

## Retention Policy

- **latest/**: Overwritten on every run. Not versioned.
- **releases/**: Never deleted automatically. One directory per run.
  Naming: `YYYY-MM-DD_HHMM_shortsha` (e.g., `2026-02-07_1430_d767359`).
- **index.json**: Append-only. Each entry is a run summary with paths and pass/fail.

## How Runs Are Triggered

Visual gate runs are performed by Claude using the Puppeteer MCP tools during sprint
reviews or release preparation. The run follows the procedure defined in
`_bmad-output/templates/visual-gate-run.md`.

Results are written by `gui/src/utils/visualGateReport.ts` (or directly by Claude
into the artifact files).

## What Gets Checked

See `gui/docs/visual-gate.md` for the full gate specification.
See `gui/docs/visual-gate-selectors.md` for the selector contract.

## Git Policy

- `_mcp_artifacts/` is listed in `.gitignore` — artifacts are local-only evidence.
- To archive a release evidence pack, copy it out before cleanup.
