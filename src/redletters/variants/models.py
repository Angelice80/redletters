"""Variant data models.

Implements ADR-008 variant representation with witness attestation.
Sprint 9: Enhanced with WitnessSupportType and WitnessSupport for multi-pack aggregation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class WitnessSupportType(str, Enum):
    """Types of witness support for attestation (Sprint 9: B1).

    Distinguishes between:
    - EDITION: Critical editions (WH, NA28, SBLGNT)
    - MANUSCRIPT: Specific manuscripts (P66, 01, 03)
    - TRADITION: Tradition aggregates (Byz, f1, f13)
    - OTHER: Fathers, versions, etc.
    """

    EDITION = "edition"
    """Critical editions like Westcott-Hort, NA28, SBLGNT."""

    MANUSCRIPT = "manuscript"
    """Specific manuscript witnesses (papyri, uncials, minuscules)."""

    TRADITION = "tradition"
    """Tradition aggregates like Byzantine, f1, f13."""

    OTHER = "other"
    """Church fathers, versions, and other witness types."""


@dataclass
class WitnessSupport:
    """Individual witness attestation for a reading (Sprint 9: B1).

    Tracks a single witness's support for a reading with provenance
    information for multi-pack aggregation.
    """

    witness_siglum: str
    """Witness siglum (e.g., 'P66', '01', 'WH', 'Byz')."""

    witness_type: WitnessSupportType
    """Type of witness (edition, manuscript, tradition, other)."""

    source_pack_id: str
    """ID of the pack that contributed this support."""

    century_range: tuple[int, int] | None = None
    """Century range (earliest, latest) of attestation."""

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "witness_siglum": self.witness_siglum,
            "witness_type": self.witness_type.value,
            "source_pack_id": self.source_pack_id,
            "century_range": list(self.century_range) if self.century_range else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WitnessSupport":
        """Deserialize from dictionary."""
        century = data.get("century_range")
        return cls(
            witness_siglum=data["witness_siglum"],
            witness_type=WitnessSupportType(data["witness_type"]),
            source_pack_id=data["source_pack_id"],
            century_range=tuple(century) if century else None,
        )


class WitnessType(Enum):
    """Types of manuscript witnesses."""

    PAPYRUS = "papyrus"
    """Early papyrus manuscripts (e.g., P66, P75)."""

    UNCIAL = "uncial"
    """Major uncial codices (e.g., Sinaiticus, Vaticanus)."""

    MINUSCULE = "minuscule"
    """Later minuscule manuscripts."""

    VERSION = "version"
    """Ancient translations (Syriac, Latin, Coptic)."""

    FATHER = "father"
    """Church father quotations."""


class VariantClassification(Enum):
    """Classification of variant types."""

    SPELLING = "spelling"
    """Orthographic differences (itacism, etc.)."""

    WORD_ORDER = "word_order"
    """Different arrangement of same words."""

    OMISSION = "omission"
    """Text present in some witnesses, absent in others."""

    ADDITION = "addition"
    """Extra text in some witnesses."""

    SUBSTITUTION = "substitution"
    """Different word(s) in the same position."""

    CONFLATION = "conflation"
    """Combination of two or more readings."""


class SignificanceLevel(Enum):
    """Significance level for variants."""

    TRIVIAL = "trivial"
    """No impact on meaning (spelling, movable nu)."""

    MINOR = "minor"
    """Small impact, easily resolved by context."""

    SIGNIFICANT = "significant"
    """Affects interpretation, requires acknowledgement."""

    MAJOR = "major"
    """Substantially affects meaning or doctrine."""


@dataclass
class WitnessReading:
    """A single reading with its witness support.

    Represents one option in a variant unit, with the witnesses
    that attest to this reading.

    Sprint 9: Enhanced with support_set for multi-pack aggregation.
    """

    surface_text: str
    """The Greek text of this reading."""

    witnesses: list[str] = field(default_factory=list)
    """Witness sigla (e.g., 'P66', 'א', 'B', 'D'). Legacy field."""

    witness_types: list[WitnessType] = field(default_factory=list)
    """Types of witnesses supporting this reading. Legacy field."""

    date_range: tuple[int, int] | None = None
    """Century range (earliest, latest) of witnesses."""

    normalized_text: str | None = None
    """Normalized form for comparison."""

    notes: str = ""
    """Additional notes about this reading."""

    # Sprint 8: Provenance tracking (B3)
    source_pack_id: str | None = None
    """ID of the pack that contributed this reading."""

    # Sprint 9: Structured support set (B1)
    support_set: list[WitnessSupport] = field(default_factory=list)
    """Structured witness support entries with provenance."""

    @property
    def has_papyri(self) -> bool:
        """True if supported by papyrus witnesses."""
        # Check both legacy and new support_set
        if WitnessType.PAPYRUS in self.witness_types:
            return True
        for support in self.support_set:
            if support.witness_type == WitnessSupportType.MANUSCRIPT:
                if support.witness_siglum.startswith("P"):
                    return True
        return False

    @property
    def has_primary_uncials(self) -> bool:
        """True if supported by primary uncials (aleph, B)."""
        primary = {"א", "B", "A", "C", "D", "01", "02", "03", "04", "05"}
        if bool(primary & set(self.witnesses)):
            return True
        for support in self.support_set:
            if support.witness_siglum in primary:
                return True
        return False

    @property
    def earliest_century(self) -> int | None:
        """Earliest century of attestation."""
        # Check legacy date_range
        earliest = self.date_range[0] if self.date_range else None
        # Check support_set
        for support in self.support_set:
            if support.century_range:
                cent = support.century_range[0]
                if earliest is None or cent < earliest:
                    earliest = cent
        return earliest

    @property
    def witness_summary(self) -> str:
        """Human-readable witness summary."""
        # Combine legacy and support_set witnesses
        all_witnesses = list(self.witnesses)
        for support in self.support_set:
            if support.witness_siglum not in all_witnesses:
                all_witnesses.append(support.witness_siglum)

        if not all_witnesses:
            return "No witnesses recorded"
        return ", ".join(all_witnesses[:5]) + (
            f" (+{len(all_witnesses) - 5} more)" if len(all_witnesses) > 5 else ""
        )

    def get_support_by_type(self) -> dict[WitnessSupportType, list[WitnessSupport]]:
        """Group support entries by witness type (Sprint 9: B3)."""
        result: dict[WitnessSupportType, list[WitnessSupport]] = {}
        for support in self.support_set:
            if support.witness_type not in result:
                result[support.witness_type] = []
            result[support.witness_type].append(support)
        return result

    def get_source_packs(self) -> list[str]:
        """Get unique source_pack_ids from support set (Sprint 9: B3)."""
        packs: set[str] = set()
        if self.source_pack_id:
            packs.add(self.source_pack_id)
        for support in self.support_set:
            packs.add(support.source_pack_id)
        return sorted(packs)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "surface_text": self.surface_text,
            "witnesses": self.witnesses,
            "witness_types": [wt.value for wt in self.witness_types],
            "date_range": self.date_range,
            "normalized_text": self.normalized_text,
            "notes": self.notes,
            "has_papyri": self.has_papyri,
            "has_primary_uncials": self.has_primary_uncials,
            "witness_summary": self.witness_summary,
            "source_pack_id": self.source_pack_id,
            # Sprint 9: Include support_set
            "support_set": [s.to_dict() for s in self.support_set],
        }


@dataclass
class VariantUnit:
    """A unit of textual variation.

    Represents a single point where manuscripts diverge,
    with multiple reading options and their attestation.
    """

    ref: str
    """Scripture reference (e.g., 'John.1.18')."""

    position: int
    """Word position within the verse (0-indexed)."""

    readings: list[WitnessReading]
    """All known readings at this position."""

    sblgnt_reading_index: int = 0
    """Index of the SBLGNT (default) reading."""

    classification: VariantClassification = VariantClassification.SUBSTITUTION
    """Type of variant."""

    significance: SignificanceLevel = SignificanceLevel.MINOR
    """How significant is this variant."""

    notes: str = ""
    """Additional notes about this variant unit."""

    source_id: int | None = None
    """Foreign key to sources table (provenance)."""

    # Sprint 7: Reason classification (B4)
    reason_code: str = ""
    """Reason code: theological_keyword, article_particle, word_order, etc."""

    reason_summary: str = ""
    """Human-readable reason summary."""

    reason_detail: str | None = None
    """Additional detail about the reason."""

    @property
    def sblgnt_reading(self) -> WitnessReading | None:
        """The SBLGNT (canonical spine) reading."""
        if 0 <= self.sblgnt_reading_index < len(self.readings):
            return self.readings[self.sblgnt_reading_index]
        return None

    @property
    def reading_count(self) -> int:
        """Number of distinct readings."""
        return len(self.readings)

    @property
    def is_significant(self) -> bool:
        """True if variant is significant or major."""
        return self.significance in (
            SignificanceLevel.SIGNIFICANT,
            SignificanceLevel.MAJOR,
        )

    @property
    def requires_acknowledgement(self) -> bool:
        """True if this variant requires user acknowledgement.

        Per ADR-008, significant and major variants must be
        acknowledged before proceeding with claims that depend on them.
        """
        return self.is_significant

    def get_reading(self, index: int) -> WitnessReading | None:
        """Get reading by index."""
        if 0 <= index < len(self.readings):
            return self.readings[index]
        return None

    def get_non_sblgnt_readings(self) -> list[tuple[int, WitnessReading]]:
        """Get all non-SBLGNT readings with their indices."""
        return [
            (i, r)
            for i, r in enumerate(self.readings)
            if i != self.sblgnt_reading_index
        ]

    # Sprint 8: Provenance helpers (B3)
    def get_witness_summary_by_type(self) -> dict[WitnessType, list[str]]:
        """Group all witnesses by type across all readings."""
        result: dict[WitnessType, list[str]] = {}
        for reading in self.readings:
            for witness, wtype in zip(reading.witnesses, reading.witness_types):
                if wtype not in result:
                    result[wtype] = []
                if witness not in result[wtype]:
                    result[wtype].append(witness)
        return result

    def get_provenance_summary(self) -> list[str]:
        """Get list of source pack IDs that contributed readings."""
        packs: set[str] = set()
        for reading in self.readings:
            if reading.source_pack_id:
                packs.add(reading.source_pack_id)
        return sorted(packs)

    def get_witness_density_note(self) -> str | None:
        """Generate a witness density observation (not a truth claim).

        Returns a note about the distribution of witness support.
        This is informational only, not a claim of textual priority.
        """
        by_type = self.get_witness_summary_by_type()

        notes = []
        if WitnessType.PAPYRUS in by_type:
            notes.append(
                f"Early papyri support: {', '.join(by_type[WitnessType.PAPYRUS])}"
            )
        if WitnessType.UNCIAL in by_type:
            notes.append(f"Major uncials: {', '.join(by_type[WitnessType.UNCIAL])}")

        # Check for edition-only support
        editions_only = (
            set(by_type.keys()) == {WitnessType.VERSION}
            or set(by_type.keys()) == {WitnessType.UNCIAL}
            and all("SBLGNT" in w for w in by_type.get(WitnessType.UNCIAL, []))
        )
        if editions_only:
            notes.append("Support limited to critical editions")

        return "; ".join(notes) if notes else None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "ref": self.ref,
            "position": self.position,
            "readings": [r.to_dict() for r in self.readings],
            "sblgnt_reading_index": self.sblgnt_reading_index,
            "classification": self.classification.value,
            "significance": self.significance.value,
            "notes": self.notes,
            "reading_count": self.reading_count,
            "is_significant": self.is_significant,
            "requires_acknowledgement": self.requires_acknowledgement,
            # Sprint 7: Reason fields
            "reason_code": self.reason_code,
            "reason_summary": self.reason_summary,
            "reason_detail": self.reason_detail,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VariantUnit":
        """Deserialize from dictionary."""
        readings = []
        for r_data in data.get("readings", []):
            readings.append(
                WitnessReading(
                    surface_text=r_data["surface_text"],
                    witnesses=r_data.get("witnesses", []),
                    witness_types=[
                        WitnessType(wt) for wt in r_data.get("witness_types", [])
                    ],
                    date_range=tuple(r_data["date_range"])
                    if r_data.get("date_range")
                    else None,
                    normalized_text=r_data.get("normalized_text"),
                    notes=r_data.get("notes", ""),
                )
            )

        return cls(
            ref=data["ref"],
            position=data["position"],
            readings=readings,
            sblgnt_reading_index=data.get("sblgnt_reading_index", 0),
            classification=VariantClassification(
                data.get("classification", "substitution")
            ),
            significance=SignificanceLevel(data.get("significance", "minor")),
            notes=data.get("notes", ""),
            # Sprint 7: Reason fields
            reason_code=data.get("reason_code", ""),
            reason_summary=data.get("reason_summary", ""),
            reason_detail=data.get("reason_detail"),
        )
