"""Witness overlay plugin stub (future Syriac support)."""

from redletters.plugins.base import WitnessReading


class SyriacPeshittaOverlay:
    """
    Stub implementation for Peshitta Syriac overlay.

    TODO: Implement with:
    - Peshitta text database
    - Syriac-Greek alignment data
    - Retroversion mappings
    """

    def get_parallel(
        self, book: str, chapter: int, verse: int
    ) -> WitnessReading | None:
        """Return None (no data in stub)."""
        return None

    @property
    def tradition_name(self) -> str:
        return "Peshitta"


class OldSyriacOverlay:
    """
    Stub implementation for Old Syriac witnesses.

    TODO: Implement with Sinaitic and Curetonian manuscript data.
    """

    def get_parallel(
        self, book: str, chapter: int, verse: int
    ) -> WitnessReading | None:
        return None

    @property
    def tradition_name(self) -> str:
        return "Old Syriac"
