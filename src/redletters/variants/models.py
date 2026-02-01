"""Variant data models.

Implements ADR-008 variant representation with witness attestation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


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
    """

    surface_text: str
    """The Greek text of this reading."""

    witnesses: list[str]
    """Witness sigla (e.g., 'P66', 'א', 'B', 'D')."""

    witness_types: list[WitnessType] = field(default_factory=list)
    """Types of witnesses supporting this reading."""

    date_range: tuple[int, int] | None = None
    """Century range (earliest, latest) of witnesses."""

    normalized_text: str | None = None
    """Normalized form for comparison."""

    notes: str = ""
    """Additional notes about this reading."""

    @property
    def has_papyri(self) -> bool:
        """True if supported by papyrus witnesses."""
        return WitnessType.PAPYRUS in self.witness_types

    @property
    def has_primary_uncials(self) -> bool:
        """True if supported by primary uncials (aleph, B)."""
        primary = {"א", "B", "A", "C", "D"}
        return bool(primary & set(self.witnesses))

    @property
    def earliest_century(self) -> int | None:
        """Earliest century of attestation."""
        return self.date_range[0] if self.date_range else None

    @property
    def witness_summary(self) -> str:
        """Human-readable witness summary."""
        if not self.witnesses:
            return "No witnesses recorded"
        return ", ".join(self.witnesses[:5]) + (
            f" (+{len(self.witnesses) - 5} more)" if len(self.witnesses) > 5 else ""
        )

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
        )
