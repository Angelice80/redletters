# ADR-007: Canonical Spine — SBLGNT as Hub + Default

**Status**: Accepted
**Date**: 2026-01-30
**Deciders**: Project maintainers
**Supersedes**: None

## Context

A forensic linguistics engine for Koine Greek scripture requires a canonical text spine to anchor all operations. The choice of base text determines:

1. **Token identity**: Which surface forms are "canonical" positions
2. **Morphological alignment**: Which parse tags are authoritative defaults
3. **Variant representation**: What counts as a "divergence" from baseline
4. **Reproducibility**: Whether queries return consistent results

Multiple Greek New Testament editions exist with varying degrees of accessibility:

| Edition | License | Morphology Available | Notes |
|---------|---------|---------------------|-------|
| NA28/UBS5 | Proprietary (© German Bible Society) | NA27 morphology available separately | Cannot legally redistribute |
| SBLGNT | SBLGNT License (free, attribution required) | MorphGNT aligned (CC-BY-SA) | Freely redistributable |
| Westcott-Hort | Public domain | Multiple alignments available | 1881, superseded by manuscript discoveries |
| Byzantine/TR | Public domain | Robinson-Pierpont morphology | Different textual tradition |

## Decision

**SBLGNT (SBL Greek New Testament) is the canonical hub and default text spine.**

All token positions, morphological tags, and query results default to SBLGNT unless explicitly overridden. Variant readings from other textual traditions are represented as divergences from the SBLGNT baseline.

### Implementation Details

1. **Token Identity**: Every token has a canonical position defined by SBLGNT book/chapter/verse/word-position
2. **Morphology Source**: MorphGNT (James Tauber's alignment) provides POS and parse codes
3. **Variant Layer**: Non-SBLGNT readings stored in `variant_units` table with witness attestation
4. **Default View**: Readable view shows SBLGNT text; variants surfaced on demand or when creating claims

### Pinned Source

```yaml
# In sources_catalog.yaml
morphgnt-sblgnt:
  name: "MorphGNT (SBLGNT)"
  url: "https://github.com/morphgnt/sblgnt"
  commit: "b4d1e66a22c389aae24fe6e4e80db34e1e5c0b11"
  version: "6.12"
  license: "CC-BY-SA-3.0"
  license_url: "https://creativecommons.org/licenses/by-sa/3.0/"
  role: "canonical_spine"
```

## Consequences

### Positive

1. **License Clarity**: SBLGNT is freely redistributable with attribution; no legal risk
2. **MorphGNT Alignment**: High-quality morphological tagging already exists and is maintained
3. **Reproducibility**: Git-pinned commits ensure identical builds
4. **Scholarly Acceptance**: SBLGNT is the product of SBL's editorial committee and Michael Holmes
5. **Variant Surfacing**: Clear baseline makes divergences explicit and measurable

### Negative

1. **Not NA28**: Academic publications often cite NA28/UBS5; SBLGNT differs in ~540 variants
2. **No Apparatus Integration**: SBLGNT lacks inline critical apparatus (we must source separately)
3. **Update Lag**: MorphGNT updates may lag behind SBLGNT releases

### Mitigations

- **NA28 Comparison**: Variant layer will eventually include NA28 readings where legally permissible (manual entry or apparatus extraction)
- **Apparatus Sources**: ECM (Editio Critica Maior) and open-source collations provide witness data
- **Versioning**: Pinned commits prevent surprise updates; upgrades are explicit PRs

## Alternatives Considered

### Alternative 1: Westcott-Hort as Spine

**Rejected because**: While public domain, W-H is outdated (1881). Post-W-H manuscript discoveries (P66, P75, Sinaiticus corrections) are not reflected. Using W-H would require constant variant annotation to reach modern scholarly consensus.

### Alternative 2: NA28 as Spine

**Rejected because**: NA28 text is under copyright (Deutsche Bibelgesellschaft). We cannot legally redistribute the text. Additionally, NA28 morphology is separately licensed and restricted.

### Alternative 3: Byzantine/TR as Spine

**Rejected because**: While freely available, Byzantine text represents a later textual tradition. For forensic work prioritizing earliest attestation, Alexandrian-weighted texts (like SBLGNT) are preferred. Byzantine can be a variant layer.

## Compliance

This decision enforces:

- **Traceability**: All tokens trace to SBLGNT position + MorphGNT morphology + sources table provenance
- **License Safety**: No proprietary corpus ingestion
- **Reproducibility**: Pinned commits, checksums required

## References

- [SBLGNT Official Page](https://sblgnt.com/)
- [MorphGNT Repository](https://github.com/morphgnt/sblgnt)
- [SBLGNT License](https://sblgnt.com/license/)
- Holmes, Michael W. *The Greek New Testament: SBL Edition*. SBL Press, 2010.
