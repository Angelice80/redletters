"""Export module for reproducible scholar datasets.

v0.5.0: Reproducible Scholar Exports

Provides:
- Stable deterministic IDs for variant units, readings, and tokens
- Canonical JSON serialization for reproducible hashing
- JSONL export of apparatus and translation datasets
- Snapshot generation and verification for reproducibility

v0.8.0: Export friction (gate enforcement before export)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from redletters.export.identifiers import (
    canonical_json,
    content_hash,
    reading_id,
    token_id,
    variant_unit_id,
    verse_id,
)

# Import schema versions from centralized module (v0.10.0)
from redletters.export.schema_versions import (
    EXPORT_SCHEMA_VERSION,
    CITATIONS_SCHEMA_VERSION,
    QUOTE_SCHEMA_VERSION,
    DOSSIER_SCHEMA_VERSION,
    get_all_schema_versions,
)


# v0.8.0: Export friction error


@dataclass
class PendingGate:
    """Information about a single pending gate."""

    variant_ref: str
    significance: str
    spine_reading: str
    readings_count: int


@dataclass
class PendingGatesError(Exception):
    """Error raised when export is blocked by pending gates (v0.8.0).

    Contains information about which gates need acknowledgement before
    export can proceed.
    """

    reference: str
    """Reference being exported."""

    session_id: str
    """Session ID used for gate check."""

    pending_gates: list[PendingGate] = field(default_factory=list)
    """List of pending gates that block export."""

    def __str__(self) -> str:
        count = len(self.pending_gates)
        refs = ", ".join(g.variant_ref for g in self.pending_gates[:3])
        more = f" (+{count - 3} more)" if count > 3 else ""
        return (
            f"Export blocked: {count} pending gate(s) for {self.reference}. "
            f"Acknowledge variants first: {refs}{more}. "
            f"Or use --force to export anyway."
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            "error": "pending_gates",
            "reference": self.reference,
            "session_id": self.session_id,
            "pending_count": len(self.pending_gates),
            "pending_gates": [
                {
                    "variant_ref": g.variant_ref,
                    "significance": g.significance,
                    "spine_reading": g.spine_reading,
                    "readings_count": g.readings_count,
                }
                for g in self.pending_gates
            ],
            "instructions": [
                "Acknowledge each pending variant before export:",
                f"  redletters gates acknowledge <variant_ref> --session {self.session_id}",
                "Or use --force to export with metadata noting pending gates.",
            ],
        }


# Lazy imports for exporters to avoid circular dependencies
def __getattr__(name):
    if name == "ApparatusExporter":
        from redletters.export.apparatus import ApparatusExporter

        return ApparatusExporter
    elif name == "TranslationExporter":
        from redletters.export.translation import TranslationExporter

        return TranslationExporter
    elif name == "SnapshotGenerator":
        from redletters.export.snapshot import SnapshotGenerator

        return SnapshotGenerator
    elif name == "SnapshotVerifier":
        from redletters.export.snapshot import SnapshotVerifier

        return SnapshotVerifier
    # v0.12.0: Bundle exports
    elif name == "BundleCreator":
        from redletters.export.bundle import BundleCreator

        return BundleCreator
    elif name == "BundleVerifier":
        from redletters.export.bundle import BundleVerifier

        return BundleVerifier
    elif name == "create_bundle":
        from redletters.export.bundle import create_bundle

        return create_bundle
    elif name == "verify_bundle":
        from redletters.export.bundle import verify_bundle

        return verify_bundle
    elif name == "BUNDLE_SCHEMA_VERSION":
        from redletters.export.bundle import BUNDLE_SCHEMA_VERSION

        return BUNDLE_SCHEMA_VERSION
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Constants (v0.10.0: centralized in schema_versions.py)
    "EXPORT_SCHEMA_VERSION",
    "CITATIONS_SCHEMA_VERSION",
    "QUOTE_SCHEMA_VERSION",
    "DOSSIER_SCHEMA_VERSION",
    "get_all_schema_versions",
    # ID helpers
    "verse_id",
    "variant_unit_id",
    "reading_id",
    "token_id",
    "canonical_json",
    "content_hash",
    # Exporters (lazy loaded)
    "ApparatusExporter",
    "TranslationExporter",
    # Snapshot (lazy loaded)
    "SnapshotGenerator",
    "SnapshotVerifier",
    # v0.8.0: Export friction
    "PendingGatesError",
    "PendingGate",
    # v0.12.0: Bundle exports
    "BundleCreator",
    "BundleVerifier",
    "create_bundle",
    "verify_bundle",
    "BUNDLE_SCHEMA_VERSION",
]
