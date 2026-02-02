"""Centralized schema version constants for all export artifacts.

v0.10.0: Schema Contracts + Validation

This module provides a single source of truth for all schema versions
used in export artifacts. Version policy:
- Minor bump: additive optional fields
- Major bump: breaking changes (field removal, type changes)

All schema versions should be in semantic versioning format: "X.Y.Z"
"""

from __future__ import annotations


# Export format version (apparatus, translation, snapshot)
EXPORT_SCHEMA_VERSION = "1.0.0"

# Citations export schema version (CSL-JSON wrapper)
CITATIONS_SCHEMA_VERSION = "1.0.0"

# Quote output schema version
QUOTE_SCHEMA_VERSION = "1.0.0"

# Dossier output schema version
DOSSIER_SCHEMA_VERSION = "1.0.0"

# Senses explain/conflicts schema version
SENSES_SCHEMA_VERSION = "1.0.0"

# Confidence bucketing algorithm version (for reproducibility)
CONFIDENCE_BUCKETING_VERSION = "1.0.0"


def get_all_schema_versions():
    """Return all schema versions as a dictionary.

    Useful for snapshot generation and validation.

    Returns:
        Dict mapping artifact type to schema version
    """
    return {
        "apparatus": EXPORT_SCHEMA_VERSION,
        "translation": EXPORT_SCHEMA_VERSION,
        "snapshot": EXPORT_SCHEMA_VERSION,
        "citations": CITATIONS_SCHEMA_VERSION,
        "quote": QUOTE_SCHEMA_VERSION,
        "dossier": DOSSIER_SCHEMA_VERSION,
        "senses_explain": SENSES_SCHEMA_VERSION,
        "senses_conflicts": SENSES_SCHEMA_VERSION,
        "confidence_bucketing": CONFIDENCE_BUCKETING_VERSION,
    }
