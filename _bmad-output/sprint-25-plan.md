# Sprint 25 Plan: Visual Gate & Release Evidence

**Sprint Goal**: Turn ad-hoc visual checks into a repeatable, evidence-producing release gate.

**Duration**: 1 sprint (4 stories)
**Priority**: Repeatability + Evidence Durability

## Stories

### S25.0 — Visual Gate Spec + Artifact Index Format
**Type**: Documentation
**Priority**: P0 (everything else depends on this)
**Files**: gui/docs/visual-gate.md, gui/docs/visual-gate-selectors.md, gui/_mcp_artifacts/README.md
**Estimate**: Small

### S25.1 — Stable Selector Contract
**Type**: Code + Documentation
**Priority**: P0
**Depends on**: S25.0
**Files**: gui/src/screens/PassageWorkspace.tsx, gui/src/components/*.tsx, gui/docs/visual-gate-selectors.md
**Estimate**: Small (most selectors already exist)

### S25.2 — Puppeteer MCP Smoke Lane
**Type**: Infrastructure + Code + Execution
**Priority**: P0
**Depends on**: S25.0, S25.1
**Files**: _bmad-output/templates/visual-gate-run.md, gui/src/utils/visualGateReport.ts, gui/_mcp_artifacts/
**Estimate**: Medium (includes actual MCP run)

### S25.3 — Release Gate Checklist
**Type**: Documentation
**Priority**: P1
**Depends on**: S25.2
**Files**: _bmad-output/release-gate.md
**Estimate**: Small

## Sequence

```
S25.0 (docs) → S25.1 (selectors) → S25.2 (smoke lane + run) → S25.3 (checklist)
```

## Verification Per Story

| Story | vitest | tsc | MCP Run |
|-------|--------|-----|---------|
| S25.0 | N/A    | N/A | N/A     |
| S25.1 | Yes    | Yes | N/A     |
| S25.2 | Yes    | Yes | Yes (full) |
| S25.3 | N/A    | N/A | N/A     |
