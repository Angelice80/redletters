# Project Goals and Principles

This document defines the enforceable goals, non-goals, and epistemic principles
that govern Red Letters Source Reader development.

## Core Objectives

### 1. Operationalize Uncertainty

Uncertainty is not hidden or minimized. It is exposed, measured, and propagated:

- **Confidence gradient propagation**: Every claim carries layered confidence
  (textual, grammatical, lexical, interpretive) that flows to downstream outputs.
- **Confidence bucketing**: Scores map to "high", "medium", "low" buckets with
  explicit thresholds (>= 0.8, >= 0.6, < 0.6).
- **No collapsed scores**: Component confidence always visible alongside composite.

### 2. Preserve Minority and Fringe Readings

Variant readings are preserved with metadata, not discarded:

- **Attestation strength**: Each reading carries explicit support classification
  (strong, moderate, weak) derived from witness count and age.
- **No false equivalence**: Metadata describes attestation objectively without
  claiming all readings are equally likely original.
- **Historical uptake**: Where known, note whether a reading was widely adopted
  or remained marginal.
- **Ideological usage**: Where metadata exists, note documented historical
  associations without editorial commentary.

### 3. Expose Incentive Logic

Textual criticism involves reasoning patterns that carry implicit biases.
These are exposed as neutral tags, not hidden:

- **Brevity preference**: Tag when shorter and longer readings compete.
- **Age bias risk**: Tag when earlier-attested reading competes with later-only.
- **Smoothing risk**: Tag only when pack metadata explicitly flags it.
- **No commentary**: Tags are labels, not arguments. Users draw their own conclusions.

### 4. Multi-Posture Output

The same underlying data supports multiple output modes:

- **Readable mode**: Produces flowing English with claims restricted to TYPE0-4.
- **Traceable mode**: Token-level ledger with full provenance and all claim types.
- **Export mode**: Machine-readable JSONL for external tooling.

### 5. Acknowledgement Before Export or Quote

Users must acknowledge significant variants before:

- Exporting apparatus or translation data
- Generating quotable citations

This is implemented as **gate friction**:

- Commands fail with `PendingGatesError` when unacknowledged gates exist
- `--force` flag bypasses checks but marks output with `forced_responsibility: true`
- Gates track session-level acknowledgement with audit trail

### 6. Friction Is Intentional

Friction exists to prevent casual certainty claims:

- Export commands require gate clearance
- Quote commands require acknowledgement or forced responsibility marking
- No silent smoothing of uncertainty

### 7. Silence and Absence as Data

Missing data is meaningful:

- **PackCoverage** records which packs have/lack data for a scope
- **No data ≠ no variant**: Absence is explicitly tracked
- Exports include coverage summary showing pack participation

### 8. Reversible Theology

Claims that depend on scripture carry their textual uncertainty:

- **Dependency tracing**: Claims link to source references
- **Claims analyzer**: Reports uncertainty in theological claim dependencies
- **No hidden theology**: Every translation choice documented with rationale

## Non-Goals

### What This Project Does NOT Do

1. **No originality scoring**: We do not claim which reading is "original"
2. **No ranking by likelihood**: Readings are presented without probability claims
3. **No ideology inference**: We do not infer ideological associations from thin air
4. **No cross-book harmonization detection**: Out of scope for v0.x
5. **No consensus optimization**: Not designed to find agreement; designed to show disagreement
6. **No editorial commentary**: Labels and tags are descriptive, not persuasive
7. **No UI work**: CLI and API only for v0.x

## Enforceable Constraints

These are tested automatically:

| Constraint | Test Coverage |
|------------|---------------|
| No epistemic inflation phrases | `test_dossier_epistemic.py` |
| Confidence buckets deterministic | `test_confidence_bucketing.py` |
| Export friction blocks unacknowledged | `test_export_friction.py` |
| ConsequenceSummary is neutral | `test_consequence_summary.py` |
| Absence tracked as data | `test_coverage_summary.py` |
| Quote requires acknowledgement or force | `test_quote_friction.py` |

## Version History

- **v0.8.0**: Initial confidence bucketing, consequence summary, export friction
- **v0.9.0**: Minority metadata, incentive tags, quote friction
