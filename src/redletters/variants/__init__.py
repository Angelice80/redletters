"""Variants module: Textual variant representation and storage.

This module implements ADR-008 (Variant Surfacing & Acknowledgement Gating).

Key concepts:
- VariantUnit: A point of textual variation (e.g., John 1:18)
- WitnessReading: A specific reading at a variant unit with witness attestation
- VariantClassification: Type of variant (spelling, substitution, etc.)
- SignificanceLevel: Impact level (trivial, minor, significant, major)

Variants are stored with full witness data and surfaced side-by-side,
not buried in footnotes.
"""

from redletters.variants.models import (
    VariantClassification,
    SignificanceLevel,
    WitnessType,
    WitnessReading,
    VariantUnit,
)
from redletters.variants.store import VariantStore

__all__ = [
    # Enums
    "VariantClassification",
    "SignificanceLevel",
    "WitnessType",
    # Models
    "WitnessReading",
    "VariantUnit",
    # Storage
    "VariantStore",
]
