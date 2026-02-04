"""Run module for end-to-end scholarly workflows (v0.13.0).

Provides deterministic orchestration of the complete scholarly pipeline:
- Lockfile generation
- Variant building
- Translation
- Export (apparatus, translation, citations, quote)
- Snapshot creation
- Bundle packaging
- Full verification

Design principles:
- Single entry point for reproducible scholarly runs
- Deterministic run logging with provenance
- Gate enforcement (refusal unless --force)
- Reuses existing primitives (no duplication)
"""

from redletters.run.scholarly import (
    ScholarlyRunner,
    RunLog,
    RunLogFile,
    RunLogValidation,
    RunLogGates,
    RunLogPacksSummary,
    RunLogPackSummary,
    RunLogCommand,
    ScholarlyRunResult,
)

__all__ = [
    "ScholarlyRunner",
    "RunLog",
    "RunLogFile",
    "RunLogValidation",
    "RunLogGates",
    "RunLogPacksSummary",
    "RunLogPackSummary",
    "RunLogCommand",
    "ScholarlyRunResult",
]
