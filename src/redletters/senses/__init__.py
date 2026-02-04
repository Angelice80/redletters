"""Sense explainability module for v0.7.0.

Provides:
- Lemma normalization for consistent lookups across sense packs
- Sense resolution explanation (why this sense was chosen)
- Cross-pack conflict detection (all matches across installed packs)
"""

from __future__ import annotations

import unicodedata

# Export schema version for citations
SENSES_SCHEMA_VERSION = "1.0.0"


def normalize_lemma(lemma: str, *, preserve_case: bool = False) -> str:
    """Normalize Greek lemma for consistent lookup across sense packs.

    This is the canonical normalization function used by:
    - SensePackDB lookups
    - explain command output
    - conflicts command output

    Normalization steps:
    1. Unicode NFC normalization
    2. Strip leading/trailing whitespace
    3. Remove diacritical marks (accents, breathing marks)
    4. Optionally lowercase

    Args:
        lemma: Greek lemma with or without diacriticals
        preserve_case: If True, do not lowercase (default: False)

    Returns:
        Normalized lemma string

    Examples:
        >>> normalize_lemma("μετανοέω")
        'μετανοεω'
        >>> normalize_lemma("Ἰησοῦς")
        'ιησους'
        >>> normalize_lemma("λόγος", preserve_case=True)
        'λογος'
    """
    # Step 1: NFC normalize
    text = unicodedata.normalize("NFC", lemma)

    # Step 2: Strip whitespace
    text = text.strip()

    # Step 3: NFD decompose to separate base chars from diacritics
    nfd = unicodedata.normalize("NFD", text)

    # Step 4: Remove diacritical marks (category Mn = Mark, nonspacing)
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")

    # Step 5: Normalize back to NFC
    result = unicodedata.normalize("NFC", stripped)

    # Step 6: Optionally lowercase
    if not preserve_case:
        result = result.lower()

    return result


def lemma_matches(lemma1: str, lemma2: str) -> bool:
    """Check if two lemmas match after normalization.

    Args:
        lemma1: First lemma
        lemma2: Second lemma

    Returns:
        True if normalized forms match
    """
    return normalize_lemma(lemma1) == normalize_lemma(lemma2)


# Lazy imports for submodules
def __getattr__(name):
    if name == "SenseExplainer":
        from redletters.senses.explain import SenseExplainer

        return SenseExplainer
    elif name == "SenseConflictDetector":
        from redletters.senses.conflicts import SenseConflictDetector

        return SenseConflictDetector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "SENSES_SCHEMA_VERSION",
    "normalize_lemma",
    "lemma_matches",
    "SenseExplainer",
    "SenseConflictDetector",
]
