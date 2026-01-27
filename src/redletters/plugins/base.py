"""Base classes and protocols for plugins."""

from typing import Protocol, runtime_checkable
from dataclasses import dataclass


@dataclass
class TokenContext:
    """Context for a token in its passage."""

    book: str
    chapter: int
    verse: int
    position: int
    adjacent_lemmas: list[str]
    passage_lemmas: list[str]


@dataclass
class TextualVariant:
    """A textual variant reading."""

    variant_id: str
    reading: str
    witnesses: list[str]
    classification: str  # e.g., "alexandrian", "byzantine", "western"


@dataclass
class WitnessReading:
    """A reading from a non-Greek witness."""

    tradition: str
    text: str
    retroversion: str | None  # Greek back-translation if available
    notes: str | None


@runtime_checkable
class SenseProvider(Protocol):
    """Plugin interface for lexical sense data."""

    def get_senses(self, lemma: str) -> list:
        """Return all known senses for a lemma."""
        ...

    def get_sense_weight(
        self, lemma: str, sense_id: str, context: TokenContext
    ) -> float:
        """Return contextual weight for a specific sense."""
        ...

    @property
    def source_name(self) -> str:
        """Provenance identifier for receipts."""
        ...


@runtime_checkable
class VariantProvider(Protocol):
    """Plugin interface for textual variant data."""

    def get_variants(self, book: str, chapter: int, verse: int) -> list[TextualVariant]:
        """Return known variants for a verse."""
        ...

    def get_variant_weight(self, variant_id: str) -> float:
        """Return scholarly confidence weight."""
        ...


@runtime_checkable
class WitnessOverlay(Protocol):
    """Plugin interface for non-Greek witness data."""

    def get_parallel(
        self, book: str, chapter: int, verse: int
    ) -> WitnessReading | None:
        """Return parallel reading from this witness tradition."""
        ...

    @property
    def tradition_name(self) -> str:
        """e.g., 'Peshitta', 'Old Syriac'"""
        ...
