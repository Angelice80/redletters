"""Variant provider plugin stub (future implementation)."""

from redletters.plugins.base import TextualVariant


class StubVariantProvider:
    """
    Stub implementation for future variant support.

    TODO: Implement with actual variant data sources:
    - CNTTS apparatus
    - NA28 apparatus
    - Open-source variant databases
    """

    def get_variants(self, book: str, chapter: int, verse: int) -> list[TextualVariant]:
        """Return empty list (no variants in stub)."""
        return []

    def get_variant_weight(self, variant_id: str) -> float:
        """Return default weight."""
        return 0.5
