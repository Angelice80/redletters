"""Apparatus dataset export for scholarly reproducibility.

v0.5.0: Export variant apparatus to JSONL format.

Each line contains a complete variant unit with:
- Stable identifiers
- All readings with support sets
- Provenance (source packs)
- Gate requirements
- Schema version

v0.8.0: Added export friction (check_pending_gates)
v0.9.0: Added minority_metadata and incentive_tags to readings
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, TYPE_CHECKING

from redletters.export import EXPORT_SCHEMA_VERSION
from redletters.export.identifiers import (
    variant_unit_id,
    reading_id,
    canonical_json,
)
from redletters.variants.store import VariantStore
from redletters.variants.models import VariantUnit, WitnessReading

if TYPE_CHECKING:
    from redletters.export import PendingGate


@dataclass
class ApparatusRow:
    """Single row in apparatus export (one variant unit)."""

    variant_unit_id: str
    verse_id: str
    position: int
    classification: str
    significance: str
    gate_requirement: str
    sblgnt_reading_index: int
    readings: list[dict]
    provenance_packs: list[str]
    reason_code: str
    reason_summary: str
    schema_version: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "variant_unit_id": self.variant_unit_id,
            "verse_id": self.verse_id,
            "position": self.position,
            "classification": self.classification,
            "significance": self.significance,
            "gate_requirement": self.gate_requirement,
            "sblgnt_reading_index": self.sblgnt_reading_index,
            "readings": self.readings,
            "provenance_packs": self.provenance_packs,
            "reason_code": self.reason_code,
            "reason_summary": self.reason_summary,
            "schema_version": self.schema_version,
        }

    def to_jsonl(self) -> str:
        """Convert to canonical JSONL line."""
        return canonical_json(self.to_dict())


def _build_reading_dict(
    unit_id: str,
    index: int,
    reading: WitnessReading,
    is_sblgnt: bool,
    minority_metadata: dict | None = None,
    incentive_tags: list[str] | None = None,
) -> dict:
    """Build reading dictionary with stable ID.

    v0.9.0: Added minority_metadata and incentive_tags.
    """
    # Generate stable reading ID
    rid = reading_id(unit_id, reading.normalized_text or reading.surface_text)

    # Collect support entries
    support_entries = []
    for support in reading.support_set:
        support_entries.append(
            {
                "witness_siglum": support.witness_siglum,
                "witness_type": support.witness_type.value,
                "century_range": list(support.century_range)
                if support.century_range
                else None,
                "source_pack_id": support.source_pack_id,
            }
        )

    result = {
        "reading_id": rid,
        "index": index,
        "surface_text": reading.surface_text,
        "normalized_text": reading.normalized_text,
        "is_sblgnt": is_sblgnt,
        "witness_summary": reading.witness_summary,
        "support_entries": support_entries,
        "source_packs": reading.get_source_packs(),
        # v0.9.0
        "incentive_tags": incentive_tags or [],
    }

    # v0.9.0: Include minority_metadata if present
    if minority_metadata:
        result["minority_metadata"] = minority_metadata

    return result


def _build_support_summary(reading: WitnessReading) -> dict:
    """Build a lightweight support summary for minority metadata derivation.

    v0.9.0: Helper for apparatus export.
    """
    total_count = len(reading.support_set)
    earliest_century = None

    for support in reading.support_set:
        if support.century_range:
            cent = support.century_range[0]
            if earliest_century is None or cent < earliest_century:
                earliest_century = cent

    # Also check legacy date_range
    if reading.date_range and reading.date_range[0]:
        if earliest_century is None or reading.date_range[0] < earliest_century:
            earliest_century = reading.date_range[0]

    return {
        "total_count": total_count,
        "earliest_century": earliest_century,
    }


def _derive_minority_metadata_dict(support_info: dict) -> dict | None:
    """Derive minority metadata from support info (v0.9.0).

    Returns dict or None if insufficient data.
    """
    total_count = support_info.get("total_count", 0)
    earliest_century = support_info.get("earliest_century")

    if total_count == 0:
        return {
            "attestation_strength": None,
            "historical_uptake": None,
            "ideological_usage": [],
        }

    # Strong: multiple witnesses or early attestation
    is_early = earliest_century is not None and earliest_century <= 3
    has_multiple = total_count >= 3

    if has_multiple or is_early:
        strength = "strong"
    elif (
        total_count >= 1 and earliest_century is not None and 4 <= earliest_century <= 6
    ):
        strength = "moderate"
    elif total_count == 1:
        strength = "weak"
    elif total_count == 2:
        strength = "moderate"
    else:
        strength = None

    return {
        "attestation_strength": strength,
        "historical_uptake": None,  # Not derived; must come from pack metadata
        "ideological_usage": [],  # Not derived; must come from pack metadata
    }


def _derive_incentive_tags_for_unit(
    readings: list[WitnessReading], support_infos: list[dict]
) -> list[str]:
    """Derive incentive tags for a variant unit (v0.9.0).

    Conservative rules:
    - brevity_preference_present: readings differ by >= 2 words
    - age_bias_risk: earliest centuries differ by >= 2
    """
    if len(readings) < 2:
        return []

    tags: list[str] = []

    # Check brevity
    word_counts = [len(r.surface_text.split()) for r in readings]
    if max(word_counts) - min(word_counts) >= 2:
        tags.append("brevity_preference_present")

    # Check age bias
    earliest_centuries = [
        info["earliest_century"]
        for info in support_infos
        if info.get("earliest_century") is not None
    ]
    if len(earliest_centuries) >= 2:
        spread = max(earliest_centuries) - min(earliest_centuries)
        if spread >= 2:
            tags.append("age_bias_risk")

    return tags


def _variant_to_row(variant: VariantUnit) -> ApparatusRow:
    """Convert VariantUnit to ApparatusRow.

    v0.9.0: Added minority_metadata and incentive_tags.
    """
    # Generate stable unit ID
    unit_id = variant_unit_id(variant.ref, variant.position)

    # v0.9.0: Build support info for each reading first
    support_infos = [_build_support_summary(r) for r in variant.readings]

    # v0.9.0: Derive incentive tags for the unit
    incentive_tags = _derive_incentive_tags_for_unit(variant.readings, support_infos)

    # Build readings with minority metadata and incentive tags
    readings = []
    for i, reading in enumerate(variant.readings):
        is_sblgnt = i == variant.sblgnt_reading_index
        minority_meta = _derive_minority_metadata_dict(support_infos[i])
        readings.append(
            _build_reading_dict(
                unit_id,
                i,
                reading,
                is_sblgnt,
                minority_metadata=minority_meta,
                incentive_tags=incentive_tags,
            )
        )

    # Determine gate requirement
    if variant.significance.value in ("significant", "major"):
        gate_req = "requires_acknowledgement"
    else:
        gate_req = "none"

    # Collect all provenance packs
    provenance_packs = sorted(variant.get_provenance_summary())

    return ApparatusRow(
        variant_unit_id=unit_id,
        verse_id=variant.ref,
        position=variant.position,
        classification=variant.classification.value,
        significance=variant.significance.value,
        gate_requirement=gate_req,
        sblgnt_reading_index=variant.sblgnt_reading_index,
        readings=readings,
        provenance_packs=provenance_packs,
        reason_code=variant.reason_code or "",
        reason_summary=variant.reason_summary or "",
        schema_version=EXPORT_SCHEMA_VERSION,
    )


class ApparatusExporter:
    """Export variant apparatus to JSONL format.

    Usage:
        exporter = ApparatusExporter(variant_store)
        exporter.export_to_file("John 1:1-18", "apparatus.jsonl")
    """

    def __init__(self, variant_store: VariantStore):
        """Initialize exporter.

        Args:
            variant_store: Store to query variants from
        """
        self._store = variant_store

    def get_variants_for_scope(
        self,
        reference: str,
    ) -> list[VariantUnit]:
        """Get variants for a reference scope.

        Handles:
        - Single verse: "John.1.18"
        - Verse range: "John.1.1-18" (parses start/end)
        - Chapter: "John.1" or "John 1"
        - Book: "John"

        Args:
            reference: Scripture reference

        Returns:
            List of VariantUnit objects
        """
        # Normalize reference
        ref = reference.replace(" ", ".").replace(":", ".")

        # Parse into parts
        parts = ref.split(".")
        if len(parts) == 1:
            # Book only (e.g., "John")
            return self._store.get_significant_variants(book=parts[0])

        book = parts[0]

        # Check for range (e.g., "John.1.1-18")
        if len(parts) >= 3 and "-" in parts[-1]:
            # Verse range
            chapter = int(parts[1])
            verse_range = parts[2].split("-")
            start_verse = int(verse_range[0])
            end_verse = int(verse_range[1]) if len(verse_range) > 1 else start_verse

            all_variants = []
            for v in range(start_verse, end_verse + 1):
                verse_ref = f"{book}.{chapter}.{v}"
                all_variants.extend(self._store.get_variants_for_verse(verse_ref))
            return all_variants

        if len(parts) == 2:
            # Chapter (e.g., "John.1")
            chapter = int(parts[1])
            return self._store.get_significant_variants(book=book, chapter=chapter)

        if len(parts) >= 3:
            # Single verse (e.g., "John.1.18")
            verse_ref = f"{parts[0]}.{parts[1]}.{parts[2]}"
            return self._store.get_variants_for_verse(verse_ref)

        return []

    def iter_rows(self, reference: str) -> Iterator[ApparatusRow]:
        """Iterate over apparatus rows for a reference.

        Args:
            reference: Scripture reference

        Yields:
            ApparatusRow objects
        """
        variants = self.get_variants_for_scope(reference)
        for variant in variants:
            yield _variant_to_row(variant)

    def export_to_file(
        self,
        reference: str,
        output_path: str | Path,
    ) -> dict:
        """Export apparatus to JSONL file.

        Args:
            reference: Scripture reference
            output_path: Output file path

        Returns:
            Export metadata dict
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        row_count = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for row in self.iter_rows(reference):
                f.write(row.to_jsonl() + "\n")
                row_count += 1

        return {
            "type": "apparatus",
            "reference": reference,
            "output_path": str(output_path),
            "row_count": row_count,
            "schema_version": EXPORT_SCHEMA_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

    def export_to_list(self, reference: str) -> list[dict]:
        """Export apparatus to list of dicts (for testing).

        Args:
            reference: Scripture reference

        Returns:
            List of row dictionaries
        """
        return [row.to_dict() for row in self.iter_rows(reference)]


# v0.8.0: Export friction - gate checking


def check_pending_gates(
    conn: "sqlite3.Connection",
    reference: str,
    session_id: str,
    variant_store: VariantStore,
) -> list["PendingGate"]:
    """Check for pending gates that would block export (v0.8.0).

    Args:
        conn: Database connection
        reference: Scripture reference to check
        session_id: Session ID for acknowledgement lookup
        variant_store: Store to query variants from

    Returns:
        List of PendingGate objects for unacknowledged significant variants
    """
    from redletters.export import PendingGate
    from redletters.gates.state import AcknowledgementStore
    from redletters.variants.models import SignificanceLevel

    # Load acknowledgement state
    ack_store = AcknowledgementStore(conn)
    ack_store.init_schema()
    acks = ack_store.get_session_acks(session_id)

    # Normalize reference and determine scope
    ref = reference.replace(" ", ".").replace(":", ".")
    parts = ref.split(".")

    # Get variants based on scope
    if len(parts) >= 3:
        # Verse or verse range
        if "-" in parts[-1]:
            # Range
            chapter = int(parts[1])
            verse_range = parts[2].split("-")
            start_verse = int(verse_range[0])
            end_verse = int(verse_range[1]) if len(verse_range) > 1 else start_verse

            variants = []
            for v in range(start_verse, end_verse + 1):
                verse_ref = f"{parts[0]}.{chapter}.{v}"
                variants.extend(variant_store.get_variants_for_verse(verse_ref))
        else:
            # Single verse
            variants = variant_store.get_variants_for_verse(ref)
    elif len(parts) == 2:
        # Chapter
        variants = variant_store.get_significant_variants(
            book=parts[0], chapter=int(parts[1])
        )
    else:
        # Book
        variants = variant_store.get_significant_variants(book=parts[0])

    # Find unacknowledged significant variants
    pending = []
    for v in variants:
        if v.significance in (SignificanceLevel.SIGNIFICANT, SignificanceLevel.MAJOR):
            if v.ref not in acks:
                spine_reading = (
                    v.sblgnt_reading.surface_text if v.sblgnt_reading else ""
                )
                pending.append(
                    PendingGate(
                        variant_ref=v.ref,
                        significance=v.significance.value,
                        spine_reading=spine_reading,
                        readings_count=len(v.readings),
                    )
                )

    return pending


def raise_if_pending_gates(
    conn: "sqlite3.Connection",
    reference: str,
    session_id: str,
    variant_store: VariantStore,
) -> None:
    """Raise PendingGatesError if there are unacknowledged gates (v0.8.0).

    Args:
        conn: Database connection
        reference: Scripture reference to check
        session_id: Session ID for acknowledgement lookup
        variant_store: Store to query variants from

    Raises:
        PendingGatesError: If there are pending gates
    """
    from redletters.export import PendingGatesError

    pending = check_pending_gates(conn, reference, session_id, variant_store)
    if pending:
        raise PendingGatesError(
            reference=reference,
            session_id=session_id,
            pending_gates=pending,
        )
